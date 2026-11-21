//go:build windows

package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime/debug"
	"strconv"
	"sync"
	"sync/atomic"
	"syscall"
	"time"
	"unsafe"

	"github.com/jchv/go-webview2"
)

const (
	jobObjectExtendedLimitInfo    = 9
	jobObjectLimitKillOnJobClose  = 0x00002000
	processTerminateAndSetQuota   = 0x0101 // PROCESS_TERMINATE | PROCESS_SET_QUOTA
	maxDesktopLogBytes            = 1024 * 1024
	coreCircuitWindow             = 60 * time.Second
	coreCircuitThreshold          = 5
	hardShutdownTimeout           = 4 * time.Second
	uiReadinessFirstTimeout       = 10 * time.Second
	uiReadinessRecoveryWaitWindow = 8 * time.Second
)

var (
	procCreateJobObjectW         = kernel32.NewProc("CreateJobObjectW")
	procSetInformationJobObject  = kernel32.NewProc("SetInformationJobObject")
	procAssignProcessToJobObject = kernel32.NewProc("AssignProcessToJobObject")

	desktopLogMu sync.Mutex
)

type jobObjectBasicLimitInformation struct {
	PerProcessUserTimeLimit int64
	PerJobUserTimeLimit     int64
	LimitFlags              uint32
	MinimumWorkingSetSize   uintptr
	MaximumWorkingSetSize   uintptr
	ActiveProcessLimit      uint32
	Affinity                uintptr
	PriorityClass           uint32
	SchedulingClass         uint32
}

type ioCounters struct {
	ReadOperationCount  uint64
	WriteOperationCount uint64
	OtherOperationCount uint64
	ReadTransferCount   uint64
	WriteTransferCount  uint64
	OtherTransferCount  uint64
}

type jobObjectExtendedLimitInformation struct {
	BasicLimitInformation jobObjectBasicLimitInformation
	IoInfo                ioCounters
	ProcessMemoryLimit    uintptr
	JobMemoryLimit        uintptr
	PeakProcessMemoryUsed uintptr
	PeakJobMemoryUsed     uintptr
}

func resolveDesktopLogPath() string {
	localApp := os.Getenv("LOCALAPPDATA")
	if localApp == "" {
		localApp = os.TempDir()
	}
	return filepath.Join(localApp, "MEKA", "desktop.log")
}

func rotateLogIfNeeded(logPath string, maxBytes int64) {
	info, err := os.Stat(logPath)
	if err != nil || info.Size() < maxBytes {
		return
	}
	oldPath := logPath + ".old"
	_ = os.Remove(oldPath)
	_ = os.Rename(logPath, oldPath)
}

func logDesktopEventTo(logPath, level, component, msg string) {
	if logPath == "" {
		return
	}
	desktopLogMu.Lock()
	defer desktopLogMu.Unlock()

	if err := os.MkdirAll(filepath.Dir(logPath), 0755); err != nil {
		return
	}
	rotateLogIfNeeded(logPath, maxDesktopLogBytes)

	f, err := os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		return
	}
	defer f.Close()

	line := fmt.Sprintf("%s [%s] [%s] %s\n",
		time.Now().Format("2006-01-02T15:04:05.000-07:00"),
		level,
		component,
		msg,
	)
	_, _ = f.WriteString(line)
}

func logDesktopEvent(level, component, msg string) {
	logDesktopEventTo(resolveDesktopLogPath(), level, component, msg)
}

func recoverAndLog(component string) {
	if r := recover(); r != nil {
		stack := string(debug.Stack())
		logDesktopEvent("ERROR", component, fmt.Sprintf("panic recuperado: %v\n%s", r, stack))
	}
}

type processJob struct {
	mu     sync.Mutex
	handle uintptr
}

func createKillOnCloseJob() (*processJob, error) {
	if !procAvailable(procCreateJobObjectW) || !procAvailable(procSetInformationJobObject) {
		return nil, fmt.Errorf("Job Objects de Win32 no disponibles")
	}

	hJob, _, lastErr := procCreateJobObjectW.Call(0, 0)
	if hJob == 0 {
		return nil, fmt.Errorf("CreateJobObjectW falló: %w", lastErr)
	}

	var info jobObjectExtendedLimitInformation
	info.BasicLimitInformation.LimitFlags = jobObjectLimitKillOnJobClose

	ret, _, setErr := procSetInformationJobObject.Call(
		hJob,
		jobObjectExtendedLimitInfo,
		uintptr(unsafe.Pointer(&info)),
		unsafe.Sizeof(info),
	)
	if ret == 0 {
		_, _, _ = procCloseHandle.Call(hJob)
		return nil, fmt.Errorf("SetInformationJobObject falló: %w", setErr)
	}

	return &processJob{handle: hJob}, nil
}

func (j *processJob) assignPID(pid int) error {
	if j == nil || pid <= 0 {
		return nil
	}
	j.mu.Lock()
	hJob := j.handle
	j.mu.Unlock()
	if hJob == 0 {
		return nil
	}
	if !procAvailable(procOpenProcess) || !procAvailable(procAssignProcessToJobObject) {
		return fmt.Errorf("AssignProcessToJobObject no disponible")
	}

	hProc, _, openErr := procOpenProcess.Call(processTerminateAndSetQuota, 0, uintptr(pid))
	if hProc == 0 {
		return fmt.Errorf("OpenProcess(%d) falló: %w", pid, openErr)
	}
	defer procCloseHandle.Call(hProc)

	ret, _, assignErr := procAssignProcessToJobObject.Call(hJob, hProc)
	if ret == 0 {
		return fmt.Errorf("AssignProcessToJobObject(%d) falló: %w", pid, assignErr)
	}
	return nil
}

func (j *processJob) close() {
	if j == nil {
		return
	}
	j.mu.Lock()
	h := j.handle
	j.handle = 0
	j.mu.Unlock()
	if h != 0 && procAvailable(procCloseHandle) {
		_, _, _ = procCloseHandle.Call(h)
	}
}

func killProcessTreeByPID(pid int) {
	if pid <= 0 {
		return
	}
	cmd := exec.Command("taskkill", "/T", "/F", "/PID", strconv.Itoa(pid))
	cmd.SysProcAttr = &syscall.SysProcAttr{
		HideWindow:    true,
		CreationFlags: 0x08000000, // CREATE_NO_WINDOW
	}
	_ = cmd.Run()
}

type coreRestartTracker struct {
	mu       sync.Mutex
	attempts []time.Time
	backoff  time.Duration
}

func (c *coreRestartTracker) recordAttempt(now time.Time) (time.Duration, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()

	cutoff := now.Add(-coreCircuitWindow)
	pruned := c.attempts[:0]
	for _, ts := range c.attempts {
		if ts.After(cutoff) || ts.Equal(cutoff) {
			pruned = append(pruned, ts)
		}
	}
	pruned = append(pruned, now)
	c.attempts = pruned

	if len(c.attempts) >= coreCircuitThreshold {
		shift := len(c.attempts) - coreCircuitThreshold
		if shift > 4 {
			shift = 4
		}
		delay := (4 * time.Second) << shift
		if delay > 60*time.Second {
			delay = 60 * time.Second
		}
		c.backoff = delay
		return delay, true
	}

	c.backoff = 0
	return 0, false
}

func (c *coreRestartTracker) reset() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.attempts = nil
	c.backoff = 0
}

func isCoreHealthy(hostPort string) bool {
	if hostPort == "" {
		return false
	}
	client := &http.Client{Timeout: 600 * time.Millisecond}
	resp, err := client.Get("http://" + hostPort + "/v1/health")
	if err != nil {
		return false
	}
	_ = resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}

func verifyLocalWebServer(addr string) error {
	if addr == "" {
		return fmt.Errorf("dirección HTTP local vacía")
	}
	client := &http.Client{Timeout: 500 * time.Millisecond}
	url := "http://" + addr + "/healthz"
	var lastErr error
	for attempt := 0; attempt < 5; attempt++ {
		resp, err := client.Get(url)
		if err == nil {
			_ = resp.Body.Close()
			if resp.StatusCode == http.StatusOK {
				return nil
			}
			lastErr = fmt.Errorf("/healthz devolvió HTTP %d", resp.StatusCode)
		} else {
			lastErr = err
		}
		time.Sleep(100 * time.Millisecond)
	}
	return fmt.Errorf("verificador local /healthz falló: %w", lastErr)
}

func startUIReadinessWatchdog(ctx context.Context, w webview2.WebView, targetURL string, uiReady *atomic.Bool, onRecover func()) {
	if ctx == nil || w == nil || uiReady == nil {
		return
	}
	go func() {
		defer recoverAndLog("ui-readiness-watchdog")

		t1 := time.NewTimer(uiReadinessFirstTimeout)
		defer t1.Stop()

		select {
		case <-ctx.Done():
			return
		case <-t1.C:
		}

		if uiReady.Load() {
			return
		}

		logDesktopEvent("WARN", "ui-watchdog", fmt.Sprintf("WebView2 no confirmó carga tras %s; ejecutando recuperación Navigate", uiReadinessFirstTimeout))
		if onRecover != nil {
			onRecover()
		}
		w.Dispatch(func() {
			if ctx.Err() == nil {
				w.Navigate(targetURL)
			}
		})

		t2 := time.NewTimer(uiReadinessRecoveryWaitWindow)
		defer t2.Stop()

		select {
		case <-ctx.Done():
			return
		case <-t2.C:
		}

		if !uiReady.Load() {
			logDesktopEvent("ERROR", "ui-watchdog", "La interfaz WebView2 no respondió tras el reintento de arranque")
			showTrayBalloon("MEKA · Aviso de arranque", "La interfaz tardó en responder; revisa desktop.log si persiste.")
		}
	}()
}

type shutdownCoordinator struct {
	once        sync.Once
	cancel      context.CancelFunc
	stopTray    func()
	stopHTTP    func()
	stopCore    func()
	closeJob    func()
	closeMutex  func()
	terminateUI func()
	exitProcess func(code int)
	hardTimeout time.Duration
	onDone      chan struct{}
	reasonMu    sync.Mutex
	lastReason  string
}

func newShutdownCoordinator(cfg shutdownCoordinator) *shutdownCoordinator {
	if cfg.hardTimeout <= 0 {
		cfg.hardTimeout = hardShutdownTimeout
	}
	if cfg.exitProcess == nil {
		cfg.exitProcess = os.Exit
	}
	cfg.onDone = make(chan struct{})
	return &cfg
}

func (s *shutdownCoordinator) trigger(reason string) {
	if s == nil {
		return
	}
	s.once.Do(func() {
		s.reasonMu.Lock()
		s.lastReason = reason
		s.reasonMu.Unlock()

		logDesktopEvent("INFO", "shutdown", fmt.Sprintf("Iniciando cierre limpio (%s)", reason))

		// Watchdog duro: garantiza que el proceso jamás quede colgado en WebView2/COM/Core
		hardTimer := time.AfterFunc(s.hardTimeout, func() {
			logDesktopEvent("WARN", "shutdown", fmt.Sprintf("Watchdog de cierre (%s) agotado; forzando salida limpia", s.hardTimeout))
			if s.stopTray != nil {
				func() { defer recoverAndLog("shutdown-tray-hard"); s.stopTray() }()
			}
			if s.closeJob != nil {
				func() { defer recoverAndLog("shutdown-job-hard"); s.closeJob() }()
			}
			if s.closeMutex != nil {
				func() { defer recoverAndLog("shutdown-mutex-hard"); s.closeMutex() }()
			}
			s.exitProcess(0)
		})

		if s.cancel != nil {
			s.cancel()
		}
		if s.stopTray != nil {
			func() { defer recoverAndLog("shutdown-tray"); s.stopTray() }()
		}
		if s.stopHTTP != nil {
			doneHTTP := make(chan struct{})
			go func() {
				defer close(doneHTTP)
				defer recoverAndLog("shutdown-http")
				s.stopHTTP()
			}()
			select {
			case <-doneHTTP:
			case <-time.After(1100 * time.Millisecond):
				logDesktopEvent("WARN", "shutdown", "Timeout deteniendo servidor HTTP local")
			}
		}
		if s.stopCore != nil {
			doneCore := make(chan struct{})
			go func() {
				defer close(doneCore)
				defer recoverAndLog("shutdown-core")
				s.stopCore()
			}()
			select {
			case <-doneCore:
			case <-time.After(2 * time.Second):
				logDesktopEvent("WARN", "shutdown", "Timeout deteniendo Core; cerrando Job Object")
			}
		}
		if s.closeJob != nil {
			func() { defer recoverAndLog("shutdown-job"); s.closeJob() }()
		}
		if s.closeMutex != nil {
			func() { defer recoverAndLog("shutdown-mutex"); s.closeMutex() }()
		}
		if s.terminateUI != nil {
			func() { defer recoverAndLog("shutdown-ui"); s.terminateUI() }()
		}

		// Si terminateUI vuelve rápido, el main terminará normal; si se bloquea el loop WebView2, hardTimer actúa.
		go func() {
			defer recoverAndLog("shutdown-timer-stop")
			<-s.onDone
			hardTimer.Stop()
		}()
	})
}

func (s *shutdownCoordinator) markFinished() {
	if s == nil || s.onDone == nil {
		return
	}
	select {
	case <-s.onDone:
	default:
		close(s.onDone)
	}
}
