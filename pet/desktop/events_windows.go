//go:build windows

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"sync"
	"sync/atomic"
	"syscall"
	"time"
	"unsafe"

	"github.com/jchv/go-webview2"
)

var (
	wtsapi32 = syscall.NewLazyDLL("wtsapi32.dll")
	winmm    = syscall.NewLazyDLL("winmm.dll")
	shell32  = syscall.NewLazyDLL("shell32.dll")
	wininet  = syscall.NewLazyDLL("wininet.dll")
	ole32    = syscall.NewLazyDLL("ole32.dll")

	procGetLastInputInfo              = user32.NewProc("GetLastInputInfo")
	procRegisterClassExW              = user32.NewProc("RegisterClassExW")
	procUnregisterClassW              = user32.NewProc("UnregisterClassW")
	procCreateWindowExW               = user32.NewProc("CreateWindowExW")
	procDestroyWindow                 = user32.NewProc("DestroyWindow")
	procDefWindowProcW                = user32.NewProc("DefWindowProcW")
	procGetMessageW                   = user32.NewProc("GetMessageW")
	procTranslateMessage              = user32.NewProc("TranslateMessage")
	procDispatchMessageW              = user32.NewProc("DispatchMessageW")
	procPostMessageW                  = user32.NewProc("PostMessageW")
	procPostQuitMessage               = user32.NewProc("PostQuitMessage")
	procAddClipboardFormatListener    = user32.NewProc("AddClipboardFormatListener")
	procRemoveClipboardFormatListener = user32.NewProc("RemoveClipboardFormatListener")
	procIsClipboardFormatAvailable    = user32.NewProc("IsClipboardFormatAvailable")
	procRegisterDeviceNotificationW   = user32.NewProc("RegisterDeviceNotificationW")
	procUnregisterDeviceNotification  = user32.NewProc("UnregisterDeviceNotification")
	procGetForegroundWindow           = user32.NewProc("GetForegroundWindow")
	procGetWindowThreadProcessId      = user32.NewProc("GetWindowThreadProcessId")
	procGetWindowTextW                = user32.NewProc("GetWindowTextW")

	procGetTickCount               = kernel32.NewProc("GetTickCount")
	procGetSystemPowerStatus       = kernel32.NewProc("GetSystemPowerStatus")
	procOpenProcess                = kernel32.NewProc("OpenProcess")
	procQueryFullProcessImageNameW = kernel32.NewProc("QueryFullProcessImageNameW")

	procWTSRegisterSessionNotification   = wtsapi32.NewProc("WTSRegisterSessionNotification")
	procWTSUnRegisterSessionNotification = wtsapi32.NewProc("WTSUnRegisterSessionNotification")

	procWaveOutGetNumDevs = winmm.NewProc("waveOutGetNumDevs")

	procSHQueryUserNotificationState = shell32.NewProc("SHQueryUserNotificationState")
	procInternetGetConnectedState    = wininet.NewProc("InternetGetConnectedState")

	procCoInitializeEx   = ole32.NewProc("CoInitializeEx")
	procCoUninitialize   = ole32.NewProc("CoUninitialize")
	procCoCreateInstance = ole32.NewProc("CoCreateInstance")
)

const (
	hwndMessage = ^uintptr(2) // HWND_MESSAGE (-3), referencia Win32

	wmDestroy          = 0x0002
	wmClose            = 0x0010
	wmPowerBroadcast   = 0x0218
	wmDeviceChange     = 0x0219
	wmWtsSessionChange = 0x02B1
	wmClipboardUpdate  = 0x031D

	wtsSessionLock       = 0x7
	wtsSessionUnlock     = 0x8
	notifyForThisSession = 0

	pbtApmSuspend           = 0x0004
	pbtApmResumeSuspend     = 0x0007
	pbtApmPowerStatusChange = 0x000A
	pbtApmResumeAutomatic   = 0x0012

	dbtDeviceArrival          = 0x8000
	dbtDeviceRemoveComplete   = 0x8004
	dbtDevtypDeviceInterface  = 0x00000005
	deviceNotifyWindowHandle  = 0x00000000
	deviceNotifyAllInterfaces = 0x00000004

	cfBitmap = 2
	cfDIB    = 8

	processQueryLimitedInformation = 0x1000

	qunsBusy                 = 2
	qunsRunningD3DFullScreen = 3
	qunsPresentationMode     = 4

	coinitMultithreaded = 0x0
	clsctxAll           = 0x17
	eRender             = 0
	eConsole            = 0
	rpcEChangedMode     = 0x80010106

	idleYawnSeconds            = 56
	idleSleepSeconds           = 60
	idleActiveThresholdSeconds = 2
	idlePollInterval           = 1 * time.Second
	idleHeartbeatInterval      = 15 * time.Second
	powerPollInterval          = 5 * time.Second
	contextPollInterval        = 1500 * time.Millisecond
	networkPollInterval        = 3 * time.Second
	volumePollInterval         = 750 * time.Millisecond
	screenshotCooldown         = 1200 * time.Millisecond
	deviceDebounceDelay        = 350 * time.Millisecond
)

type nativeEventEnvelope struct {
	Type string `json:"type"`
	Data any    `json:"data"`
}

type winIdleData struct {
	Phase   string `json:"phase"`
	Idle    bool   `json:"idle"`
	Seconds int    `json:"seconds"`
}

type winPowerData struct {
	Plugged bool `json:"plugged"`
	Percent int  `json:"percent"`
	Low     bool `json:"low"`
	Saver   bool `json:"saver"`
}

type winSessionData struct {
	State string `json:"state"`
}

type winDeviceData struct {
	State string `json:"state"`
	Kind  string `json:"kind"`
}

type winScreenshotData struct {
	Source string `json:"source"`
}

type winContextData struct {
	Mode string `json:"mode"`
	App  string `json:"app"`
}

type winNetworkData struct {
	Online bool `json:"online"`
}

type winVolumeData struct {
	Percent int  `json:"percent"`
	Muted   bool `json:"muted"`
}

type lastInputInfo struct {
	cbSize uint32
	dwTime uint32
}

type systemPowerStatus struct {
	ACLineStatus        byte
	BatteryFlag         byte
	BatteryLifePercent  byte
	SystemStatusFlag    byte
	BatteryLifeTime     uint32
	BatteryFullLifeTime uint32
}

type wndClassExW struct {
	cbSize        uint32
	style         uint32
	lpfnWndProc   uintptr
	cbClsExtra    int32
	cbWndExtra    int32
	hInstance     uintptr
	hIcon         uintptr
	hCursor       uintptr
	hbrBackground uintptr
	lpszMenuName  *uint16
	lpszClassName *uint16
	hIconSm       uintptr
}

type winMsg struct {
	hwnd    uintptr
	message uint32
	wParam  uintptr
	lParam  uintptr
	time    uint32
	pt      point
}

type guid struct {
	Data1 uint32
	Data2 uint16
	Data3 uint16
	Data4 [8]byte
}

type devBroadcastDeviceInterface struct {
	size       uint32
	deviceType uint32
	reserved   uint32
	classGUID  guid
	name       [1]uint16
}

var (
	clsidMMDeviceEnumerator = guid{
		Data1: 0xBCDE0395,
		Data2: 0xE52F,
		Data3: 0x467C,
		Data4: [8]byte{0x8E, 0x3D, 0xC4, 0x57, 0x92, 0x91, 0x69, 0x2E},
	}
	iidIMMDeviceEnumerator = guid{
		Data1: 0xA95664D2,
		Data2: 0x9614,
		Data3: 0x4F35,
		Data4: [8]byte{0xA7, 0x46, 0xDE, 0x8D, 0xB6, 0x36, 0x17, 0xE6},
	}
	iidIAudioEndpointVolume = guid{
		Data1: 0x5CDF2C82,
		Data2: 0x841E,
		Data3: 0x4546,
		Data4: [8]byte{0x97, 0x22, 0x0C, 0xF7, 0x40, 0x78, 0x22, 0x9A},
	}
)

var (
	snippingToolActive     atomic.Bool
	lastSnippingClosedNano atomic.Int64

	msgWindowClassSeq   atomic.Uint64
	msgWindowCallback   uintptr
	msgWindowCallbackMu sync.Once

	eventWindowMu       sync.RWMutex
	eventWindowRegistry = make(map[uintptr]*messageSinkState)
)

func markSnippingToolClosed() {
	lastSnippingClosedNano.Store(time.Now().UnixNano())
}

func procAvailable(p *syscall.LazyProc) bool {
	return p != nil && p.Find() == nil
}

type nativeDispatcher interface {
	Dispatch(f func())
	Eval(js string)
}

func isNilDispatcher(d nativeDispatcher) bool {
	if d == nil {
		return true
	}
	rv := reflect.ValueOf(d)
	switch rv.Kind() {
	case reflect.Ptr, reflect.Interface, reflect.Func, reflect.Map, reflect.Slice, reflect.Chan:
		return rv.IsNil()
	default:
		return false
	}
}

type nativeEventEmitter struct {
	ctx  context.Context
	disp nativeDispatcher
	mu   sync.Mutex
}

func newNativeEventEmitter(ctx context.Context, disp nativeDispatcher) *nativeEventEmitter {
	return &nativeEventEmitter{
		ctx:  ctx,
		disp: disp,
	}
}

func marshalNativeEvent(eventType string, data any) (string, error) {
	raw, err := json.Marshal(nativeEventEnvelope{
		Type: eventType,
		Data: data,
	})
	if err != nil {
		return "", err
	}
	return string(raw), nil
}

func (e *nativeEventEmitter) emit(eventType string, data any) {
	if e == nil || isNilDispatcher(e.disp) || e.ctx == nil || e.ctx.Err() != nil {
		return
	}
	raw, err := marshalNativeEvent(eventType, data)
	if err != nil {
		return
	}
	script := "window.MEKA?.emitNativeEvent(" + raw + ")"

	e.mu.Lock()
	defer e.mu.Unlock()
	if e.ctx.Err() != nil {
		return
	}
	e.disp.Dispatch(func() {
		if e.ctx.Err() != nil {
			return
		}
		e.disp.Eval(script)
	})
}

// startWindowsEventMonitor lanza en segundo plano los monitores nativos de los 8 eventos
// de Windows (`win.idle`, `win.power`, `win.session`, `win.device`, `win.screenshot`,
// `win.context`, `win.network`, `win.volume`) cancelables limpiamente mediante `ctx`.
func startWindowsEventMonitor(ctx context.Context, w webview2.WebView, hwnd uintptr) {
	if ctx == nil || w == nil {
		return
	}
	_ = runWindowsEventMonitors(ctx, w, hwnd)
}

func runWindowsEventMonitors(ctx context.Context, disp nativeDispatcher, ownerHwnd uintptr) *sync.WaitGroup {
	var wg sync.WaitGroup
	if ctx == nil || isNilDispatcher(disp) {
		return &wg
	}

	emitter := newNativeEventEmitter(ctx, disp)
	powerWakeCh := make(chan struct{}, 1)

	launch := func(fn func()) {
		wg.Add(1)
		go func() {
			defer recoverAndLog("win-events")
			defer wg.Done()
			fn()
		}()
	}

	launch(func() {
		runIdleMonitor(ctx, emitter.emit)
	})
	launch(func() {
		runPowerMonitor(ctx, emitter.emit, powerWakeCh)
	})
	launch(func() {
		runMessageSinkMonitor(ctx, emitter.emit, powerWakeCh)
	})
	launch(func() {
		runContextMonitor(ctx, emitter.emit, ownerHwnd)
	})
	launch(func() {
		runNetworkMonitor(ctx, emitter.emit)
	})
	launch(func() {
		runVolumeMonitor(ctx, emitter.emit)
	})

	return &wg
}

// --- 1. win.idle ---

func evalIdleTransition(prevPhase string, seconds int) (string, *winIdleData) {
	if prevPhase == "" {
		prevPhase = "active"
	}
	if seconds < 0 {
		seconds = 0
	}

	if seconds >= idleSleepSeconds {
		if prevPhase != "sleeping" {
			return "sleeping", &winIdleData{Phase: "sleeping", Idle: true, Seconds: seconds}
		}
		return "sleeping", nil
	}

	if seconds >= idleYawnSeconds {
		if prevPhase == "active" {
			return "yawn", &winIdleData{Phase: "yawn", Idle: false, Seconds: seconds}
		}
		return prevPhase, nil
	}

	if seconds < idleActiveThresholdSeconds && (prevPhase == "yawn" || prevPhase == "sleeping") {
		return "active", &winIdleData{Phase: "active", Idle: false, Seconds: seconds}
	}

	return prevPhase, nil
}

func readSystemIdleSeconds() (int, bool) {
	if !procAvailable(procGetLastInputInfo) || !procAvailable(procGetTickCount) {
		return 0, false
	}
	lii := lastInputInfo{cbSize: uint32(unsafe.Sizeof(lastInputInfo{}))}
	ret, _, _ := procGetLastInputInfo.Call(uintptr(unsafe.Pointer(&lii)))
	if ret == 0 {
		return 0, false
	}
	tick, _, _ := procGetTickCount.Call()
	diff := uint32(tick) - lii.dwTime
	// Si GetTickCount está unos ms por detrás de dwTime sin haber wraparound (~49.7 días), fijar en 0.
	if diff > 0xFFFF0000 {
		diff = 0
	}
	return int(diff / 1000), true
}

func runIdleMonitor(ctx context.Context, emit func(string, any)) {
	ticker := time.NewTicker(idlePollInterval)
	defer ticker.Stop()

	phase := "active"
	var lastHeartbeat time.Time

	check := func() {
		seconds, ok := readSystemIdleSeconds()
		if !ok {
			return
		}
		nextPhase, evt := evalIdleTransition(phase, seconds)
		phase = nextPhase
		if evt != nil {
			emit("win.idle", *evt)
			lastHeartbeat = time.Now()
			return
		}
		// Heartbeat periódico mientras haya actividad del SO para evitar falsos AFK del timer local web.
		if phase == "active" && seconds < 15 && (lastHeartbeat.IsZero() || time.Since(lastHeartbeat) >= idleHeartbeatInterval) {
			emit("win.idle", winIdleData{Phase: "active", Idle: false, Seconds: seconds})
			lastHeartbeat = time.Now()
		}
	}

	check()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			check()
		}
	}
}

// --- 2. win.power ---

func parseSystemPowerStatus(s systemPowerStatus) winPowerData {
	hasBattery := (s.BatteryFlag&128) == 0 && s.BatteryLifePercent <= 100
	plugged := s.ACLineStatus == 1 || (s.ACLineStatus == 255 && !hasBattery)
	percent := 100
	if s.BatteryLifePercent <= 100 {
		percent = int(s.BatteryLifePercent)
	}
	low := hasBattery && !plugged && percent <= 20
	saver := s.SystemStatusFlag != 0
	return winPowerData{
		Plugged: plugged,
		Percent: percent,
		Low:     low,
		Saver:   saver,
	}
}

func shouldEmitPowerChange(prev, curr winPowerData) bool {
	return prev.Plugged != curr.Plugged ||
		prev.Low != curr.Low ||
		prev.Saver != curr.Saver ||
		prev.Percent != curr.Percent
}

func readSystemPowerStatus() (winPowerData, bool) {
	if !procAvailable(procGetSystemPowerStatus) {
		return winPowerData{}, false
	}
	var s systemPowerStatus
	ret, _, _ := procGetSystemPowerStatus.Call(uintptr(unsafe.Pointer(&s)))
	if ret == 0 {
		return winPowerData{}, false
	}
	return parseSystemPowerStatus(s), true
}

func runPowerMonitor(ctx context.Context, emit func(string, any), wakeCh <-chan struct{}) {
	ticker := time.NewTicker(powerPollInterval)
	defer ticker.Stop()

	var initialized bool
	var prev winPowerData

	check := func() {
		curr, ok := readSystemPowerStatus()
		if !ok {
			return
		}
		if !initialized {
			prev = curr
			initialized = true
			return
		}
		if shouldEmitPowerChange(prev, curr) {
			prev = curr
			emit("win.power", curr)
		}
	}

	check()
	for {
		select {
		case <-ctx.Done():
			return
		case <-wakeCh:
			check()
		case <-ticker.C:
			check()
		}
	}
}

// --- 3. win.session, win.device y win.screenshot (Message Window) ---

func classifySessionMessage(msg uint32, wParam uintptr) (string, bool) {
	switch msg {
	case wmWtsSessionChange:
		switch wParam {
		case wtsSessionLock:
			return "locked", true
		case wtsSessionUnlock:
			return "unlocked", true
		}
	case wmPowerBroadcast:
		switch wParam {
		case pbtApmSuspend:
			return "suspend", true
		case pbtApmResumeSuspend, pbtApmResumeAutomatic:
			return "resume", true
		}
	}
	return "", false
}

func classifyDeviceEvent(wParam uintptr, prevAudioDevs, currAudioDevs uint32) (state string, kind string, ok bool) {
	switch wParam {
	case dbtDeviceArrival:
		state = "connected"
	case dbtDeviceRemoveComplete:
		state = "disconnected"
	default:
		return "", "", false
	}
	kind = "usb"
	if currAudioDevs != prevAudioDevs {
		kind = "audio"
	}
	return state, kind, true
}

func getWaveOutNumDevs() uint32 {
	if !procAvailable(procWaveOutGetNumDevs) {
		return 0
	}
	ret, _, _ := procWaveOutGetNumDevs.Call()
	return uint32(ret)
}

func hasClipboardImage() bool {
	if !procAvailable(procIsClipboardFormatAvailable) {
		return false
	}
	// Solo verifica disponibilidad de CF_DIB (8) o CF_BITMAP (2), sin leer contenido del portapapeles.
	if r, _, _ := procIsClipboardFormatAvailable.Call(cfDIB); r != 0 {
		return true
	}
	if r, _, _ := procIsClipboardFormatAvailable.Call(cfBitmap); r != 0 {
		return true
	}
	return false
}

type messageSinkState struct {
	ctx         context.Context
	emit        func(string, any)
	powerWakeCh chan<- struct{}

	hwnd             uintptr
	hasClipboardHook bool
	hasWtsHook       bool
	hDevNotify       uintptr

	mu                   sync.Mutex
	closed               bool
	lastSessionState     string
	lastSessionAt        time.Time
	lastScreenshotEmitAt time.Time
	screenshotTimer      *time.Timer
	prevAudioDevs        uint32
	pendingDeviceWParam  uintptr
	deviceTimer          *time.Timer
}

func (s *messageSinkState) cleanupHooks() {
	s.mu.Lock()
	if s.closed {
		s.mu.Unlock()
		return
	}
	s.closed = true
	if s.screenshotTimer != nil {
		s.screenshotTimer.Stop()
		s.screenshotTimer = nil
	}
	if s.deviceTimer != nil {
		s.deviceTimer.Stop()
		s.deviceTimer = nil
	}
	hwnd := s.hwnd
	clipHook := s.hasClipboardHook
	wtsHook := s.hasWtsHook
	devNotify := s.hDevNotify
	s.hasClipboardHook = false
	s.hasWtsHook = false
	s.hDevNotify = 0
	s.mu.Unlock()

	if clipHook && hwnd != 0 && procAvailable(procRemoveClipboardFormatListener) {
		_, _, _ = procRemoveClipboardFormatListener.Call(hwnd)
	}
	if wtsHook && hwnd != 0 && procAvailable(procWTSUnRegisterSessionNotification) {
		_, _, _ = procWTSUnRegisterSessionNotification.Call(hwnd)
	}
	if devNotify != 0 && procAvailable(procUnregisterDeviceNotification) {
		_, _, _ = procUnregisterDeviceNotification.Call(devNotify)
	}
}

func (s *messageSinkState) handleSessionOrPower(msg uint32, wParam uintptr) {
	if msg == wmPowerBroadcast && wParam == pbtApmPowerStatusChange && s.powerWakeCh != nil {
		select {
		case s.powerWakeCh <- struct{}{}:
		default:
		}
	}
	state, ok := classifySessionMessage(msg, wParam)
	if !ok {
		return
	}

	s.mu.Lock()
	if s.closed {
		s.mu.Unlock()
		return
	}
	now := time.Now()
	if state == "resume" && s.lastSessionState == "resume" && now.Sub(s.lastSessionAt) < 3*time.Second {
		s.mu.Unlock()
		return
	}
	s.lastSessionState = state
	s.lastSessionAt = now
	s.mu.Unlock()

	s.emit("win.session", winSessionData{State: state})
}

func (s *messageSinkState) handleDeviceChange(wParam uintptr) {
	if wParam != dbtDeviceArrival && wParam != dbtDeviceRemoveComplete {
		return
	}
	s.mu.Lock()
	if s.closed {
		s.mu.Unlock()
		return
	}
	s.pendingDeviceWParam = wParam
	if s.deviceTimer != nil {
		s.deviceTimer.Stop()
	}
	s.deviceTimer = time.AfterFunc(deviceDebounceDelay, func() {
		s.mu.Lock()
		if s.closed || s.ctx.Err() != nil {
			s.mu.Unlock()
			return
		}
		wp := s.pendingDeviceWParam
		prevDevs := s.prevAudioDevs
		currDevs := getWaveOutNumDevs()
		s.prevAudioDevs = currDevs
		s.mu.Unlock()

		if state, kind, ok := classifyDeviceEvent(wp, prevDevs, currDevs); ok {
			s.emit("win.device", winDeviceData{State: state, Kind: kind})
		}
	})
	s.mu.Unlock()
}

func (s *messageSinkState) handleClipboardUpdate() {
	if !hasClipboardImage() {
		return
	}

	settleDelay := 250 * time.Millisecond
	if snippingToolActive.Load() {
		settleDelay = 450 * time.Millisecond
	} else if closedAt := lastSnippingClosedNano.Load(); closedAt > 0 && time.Since(time.Unix(0, closedAt)) < 600*time.Millisecond {
		settleDelay = 300 * time.Millisecond
	}

	s.mu.Lock()
	if s.closed {
		s.mu.Unlock()
		return
	}
	if time.Since(s.lastScreenshotEmitAt) < screenshotCooldown && s.screenshotTimer == nil {
		s.mu.Unlock()
		return
	}
	if s.screenshotTimer != nil {
		s.screenshotTimer.Stop()
	}
	s.screenshotTimer = time.AfterFunc(settleDelay, func() {
		s.mu.Lock()
		if s.closed || s.ctx.Err() != nil {
			s.screenshotTimer = nil
			s.mu.Unlock()
			return
		}
		s.screenshotTimer = nil
		if time.Since(s.lastScreenshotEmitAt) < screenshotCooldown {
			s.mu.Unlock()
			return
		}
		s.lastScreenshotEmitAt = time.Now()
		s.mu.Unlock()

		s.emit("win.screenshot", winScreenshotData{Source: "clipboard"})
	})
	s.mu.Unlock()
}

func getMessageWindowProc() uintptr {
	msgWindowCallbackMu.Do(func() {
		msgWindowCallback = syscall.NewCallback(func(hwnd uintptr, msg uint32, wParam, lParam uintptr) uintptr {
			eventWindowMu.RLock()
			state := eventWindowRegistry[hwnd]
			eventWindowMu.RUnlock()

			if state != nil {
				switch msg {
				case wmWtsSessionChange, wmPowerBroadcast:
					state.handleSessionOrPower(msg, wParam)
					return 0
				case wmDeviceChange:
					state.handleDeviceChange(wParam)
					return 1
				case wmClipboardUpdate:
					state.handleClipboardUpdate()
					return 0
				case wmClose:
					state.cleanupHooks()
					if procAvailable(procDestroyWindow) {
						_, _, _ = procDestroyWindow.Call(hwnd)
					}
					return 0
				case wmDestroy:
					state.cleanupHooks()
					if procAvailable(procPostQuitMessage) {
						_, _, _ = procPostQuitMessage.Call(0)
					}
					return 0
				}
			}

			if procAvailable(procDefWindowProcW) {
				ret, _, _ := procDefWindowProcW.Call(hwnd, uintptr(msg), wParam, lParam)
				return ret
			}
			return 0
		})
	})
	return msgWindowCallback
}

func runMessageSinkMonitor(ctx context.Context, emit func(string, any), powerWakeCh chan<- struct{}) {
	if !procAvailable(procRegisterClassExW) || !procAvailable(procCreateWindowExW) || !procAvailable(procGetMessageW) {
		return
	}

	runtime.LockOSThread()
	defer runtime.UnlockOSThread()

	var hInst uintptr
	if procAvailable(procGetModuleHandleW) {
		hInst, _, _ = procGetModuleHandleW.Call(0)
	}

	classNameStr := fmt.Sprintf("MEKAEventSink_%d", msgWindowClassSeq.Add(1))
	classPtr, err := syscall.UTF16PtrFromString(classNameStr)
	if err != nil {
		return
	}
	titlePtr, _ := syscall.UTF16PtrFromString("MEKA Event Sink")

	wc := wndClassExW{
		cbSize:        uint32(unsafe.Sizeof(wndClassExW{})),
		lpfnWndProc:   getMessageWindowProc(),
		hInstance:     hInst,
		lpszClassName: classPtr,
	}
	atom, _, _ := procRegisterClassExW.Call(uintptr(unsafe.Pointer(&wc)))
	if atom == 0 {
		return
	}
	defer func() {
		if procAvailable(procUnregisterClassW) {
			_, _, _ = procUnregisterClassW.Call(uintptr(unsafe.Pointer(classPtr)), hInst)
		}
	}()

	// Ventana oculta top-level (sin WS_VISIBLE, con WS_EX_TOOLWINDOW|WS_EX_NOACTIVATE) en lugar de
	// HWND_MESSAGE únicamente porque Windows no entrega broadcasts WM_POWERBROADCAST a ventanas HWND_MESSAGE.
	_ = hwndMessage
	hwnd, _, _ := procCreateWindowExW.Call(
		wsExToolWindow|wsExNoActivate,
		uintptr(unsafe.Pointer(classPtr)),
		uintptr(unsafe.Pointer(titlePtr)),
		0,
		0, 0, 0, 0,
		0, 0, hInst, 0,
	)
	if hwnd == 0 {
		return
	}

	state := &messageSinkState{
		ctx:           ctx,
		emit:          emit,
		powerWakeCh:   powerWakeCh,
		hwnd:          hwnd,
		prevAudioDevs: getWaveOutNumDevs(),
	}

	eventWindowMu.Lock()
	eventWindowRegistry[hwnd] = state
	eventWindowMu.Unlock()
	defer func() {
		state.cleanupHooks()
		eventWindowMu.Lock()
		delete(eventWindowRegistry, hwnd)
		eventWindowMu.Unlock()
	}()

	if procAvailable(procAddClipboardFormatListener) {
		if ret, _, _ := procAddClipboardFormatListener.Call(hwnd); ret != 0 {
			state.hasClipboardHook = true
		}
	}
	if procAvailable(procWTSRegisterSessionNotification) {
		if ret, _, _ := procWTSRegisterSessionNotification.Call(hwnd, notifyForThisSession); ret != 0 {
			state.hasWtsHook = true
		}
	}
	if procAvailable(procRegisterDeviceNotificationW) {
		filter := devBroadcastDeviceInterface{
			size:       uint32(unsafe.Sizeof(devBroadcastDeviceInterface{})),
			deviceType: dbtDevtypDeviceInterface,
		}
		if hDev, _, _ := procRegisterDeviceNotificationW.Call(
			hwnd,
			uintptr(unsafe.Pointer(&filter)),
			deviceNotifyWindowHandle|deviceNotifyAllInterfaces,
		); hDev != 0 {
			state.hDevNotify = hDev
		}
	}

	loopDone := make(chan struct{})
	defer close(loopDone)
	go func() {
		select {
		case <-ctx.Done():
			if procAvailable(procPostMessageW) {
				_, _, _ = procPostMessageW.Call(hwnd, wmClose, 0, 0)
			}
		case <-loopDone:
		}
	}()

	var msg winMsg
	for {
		ret, _, _ := procGetMessageW.Call(uintptr(unsafe.Pointer(&msg)), 0, 0, 0)
		if int32(ret) <= 0 {
			break
		}
		if procAvailable(procTranslateMessage) {
			_, _, _ = procTranslateMessage.Call(uintptr(unsafe.Pointer(&msg)))
		}
		if procAvailable(procDispatchMessageW) {
			_, _, _ = procDispatchMessageW.Call(uintptr(unsafe.Pointer(&msg)))
		}
	}
}

// --- 4. win.context ---

var (
	codingProcesses = map[string]struct{}{
		"code.exe":            {},
		"code - insiders.exe": {},
		"cursor.exe":          {},
		"windsurf.exe":        {},
		"antigravity.exe":     {},
		"zed.exe":             {},
		"devenv.exe":          {},
		"rider64.exe":         {},
		"goland64.exe":        {},
		"pycharm64.exe":       {},
		"idea64.exe":          {},
		"webstorm64.exe":      {},
		"clion64.exe":         {},
		"phpstorm64.exe":      {},
		"datagrip64.exe":      {},
		"sublime_text.exe":    {},
		"nvim.exe":            {},
		"neovide.exe":         {},
		"gvim.exe":            {},
		"emacs.exe":           {},
		"notepad++.exe":       {},
		"windowsterminal.exe": {},
		"wt.exe":              {},
		"powershell.exe":      {},
		"pwsh.exe":            {},
		"cmd.exe":             {},
		"alacritty.exe":       {},
		"wezterm-gui.exe":     {},
		"mintty.exe":          {},
		"git-bash.exe":        {},
		"postman.exe":         {},
		"insomnia.exe":        {},
		"dbeaver.exe":         {},
		"studio64.exe":        {},
		"eclipse.exe":         {},
	}

	meetingProcesses = map[string]struct{}{
		"zoom.exe":            {},
		"teams.exe":           {},
		"ms-teams.exe":        {},
		"webex.exe":           {},
		"ciscowebexstart.exe": {},
		"skype.exe":           {},
		"obs64.exe":           {},
		"obs32.exe":           {},
		"loom.exe":            {},
	}

	browserProcesses = map[string]struct{}{
		"chrome.exe":  {},
		"msedge.exe":  {},
		"firefox.exe": {},
		"brave.exe":   {},
		"opera.exe":   {},
		"vivaldi.exe": {},
		"arc.exe":     {},
	}

	mediaProcesses = map[string]struct{}{
		"vlc.exe":             {},
		"mpv.exe":             {},
		"mpc-hc64.exe":        {},
		"mpc-hc.exe":          {},
		"potplayermini64.exe": {},
		"potplayermini.exe":   {},
		"wmplayer.exe":        {},
		"kodi.exe":            {},
		"plex.exe":            {},
		"netflix.exe":         {},
		"spotify.exe":         {},
	}

	gamingProcesses = map[string]struct{}{
		"valorant.exe":                      {},
		"valorant-win64-shipping.exe":       {},
		"league of legends.exe":             {},
		"leagueclientux.exe":                {},
		"cs2.exe":                           {},
		"csgo.exe":                          {},
		"dota2.exe":                         {},
		"overwatch.exe":                     {},
		"fortniteclient-win64-shipping.exe": {},
		"minecraft.exe":                     {},
		"genshinimpact.exe":                 {},
		"starrail.exe":                      {},
		"zenlesszonezero.exe":               {},
		"eldenring.exe":                     {},
		"cyberpunk2077.exe":                 {},
		"robloxplayerbeta.exe":              {},
		"gta5.exe":                          {},
		"r5apex.exe":                        {},
		"rocketleague.exe":                  {},
		"retroarch.exe":                     {},
		"dolphin.exe":                       {},
		"yuzu.exe":                          {},
		"ryujinx.exe":                       {},
		"terraria.exe":                      {},
		"stardew valley.exe":                {},
		"hollow_knight.exe":                 {},
		"celeste.exe":                       {},
		"hades.exe":                         {},
		"bg3.exe":                           {},
		"bg3_dx11.exe":                      {},
		"palworld-win64-shipping.exe":       {},
		"helldivers2.exe":                   {},
		"warframe.x64.exe":                  {},
		"destiny2.exe":                      {},
		"tslgame.exe":                       {},
		"witcher3.exe":                      {},
		"skyrimse.exe":                      {},
		"fallout4.exe":                      {},
		"factorio.exe":                      {},
		"rimworldwin64.exe":                 {},
		"osu!.exe":                          {},
	}
)

func cleanAppDisplayName(procName, windowTitle string) string {
	base := strings.TrimSpace(filepath.Base(procName))
	if base != "" && base != "." {
		ext := filepath.Ext(base)
		if strings.EqualFold(ext, ".exe") {
			base = strings.TrimSuffix(base, ext)
		}
		if base != "" {
			return base
		}
	}
	title := strings.TrimSpace(windowTitle)
	if title != "" {
		return title
	}
	return "Windows"
}

func containsAny(haystack string, needles ...string) bool {
	for _, n := range needles {
		if strings.Contains(haystack, n) {
			return true
		}
	}
	return false
}

func classifyForegroundContext(procName, windowTitle string, quns uint32) (mode string, app string) {
	app = cleanAppDisplayName(procName, windowTitle)
	p := strings.ToLower(strings.TrimSpace(filepath.Base(procName)))
	t := strings.ToLower(strings.TrimSpace(windowTitle))
	isFullscreen := quns == qunsRunningD3DFullScreen || quns == qunsBusy

	// 1. Reuniones / llamadas
	if _, ok := meetingProcesses[p]; ok {
		return "meeting", app
	}
	if strings.HasPrefix(p, "discord") && containsAny(t, "voice", "call", "llamada", "voz", "huddle", "meeting") {
		return "meeting", app
	}
	_, isBrowser := browserProcesses[p]
	if isBrowser && (strings.HasPrefix(t, "meet - ") || containsAny(t, "google meet", "meet.google.com", "zoom meeting", "microsoft teams", "teams.microsoft.com", "jitsi", "webex", "slack huddle")) {
		return "meeting", app
	}

	// 2. Desarrollo / programación
	if _, ok := codingProcesses[p]; ok {
		return "coding", app
	}
	if isBrowser && containsAny(t, "vscode.dev", "github.dev", "codespaces", "visual studio code", "stackblitz", "codesandbox") {
		return "coding", app
	}

	// 3. Multimedia a pantalla completa
	_, isMedia := mediaProcesses[p]
	if isFullscreen && (isMedia || isBrowser || (p == "applicationframehost.exe" && containsAny(t, "netflix", "prime video", "disney", "youtube", "crunchyroll", "twitch", "películas", "movies"))) {
		return "media_fullscreen", app
	}

	// 4. Juegos
	if _, ok := gamingProcesses[p]; ok {
		return "gaming", app
	}
	if strings.HasSuffix(p, "-win64-shipping.exe") || (p == "javaw.exe" && strings.Contains(t, "minecraft")) {
		return "gaming", app
	}
	if quns == qunsRunningD3DFullScreen {
		return "gaming", app
	}

	return "normal", app
}

type contextDebounce struct {
	pendingMode  string
	pendingApp   string
	pendingCount int
	emittedMode  string
	emittedApp   string
}

func newContextDebounce() *contextDebounce {
	return &contextDebounce{emittedMode: "normal"}
}

func (c *contextDebounce) update(mode, app string) (winContextData, bool) {
	if mode == c.pendingMode && app == c.pendingApp {
		c.pendingCount++
	} else {
		c.pendingMode = mode
		c.pendingApp = app
		c.pendingCount = 1
	}

	// Requiere 2 lecturas consecutivas (~1.5s-3s) para evitar ruido al hacer Alt+Tab rápido.
	if c.pendingCount < 2 {
		return winContextData{}, false
	}

	if mode == "normal" && c.emittedMode == "normal" {
		return winContextData{}, false
	}
	if mode == c.emittedMode && app == c.emittedApp {
		return winContextData{}, false
	}

	c.emittedMode = mode
	c.emittedApp = app
	return winContextData{Mode: mode, App: app}, true
}

func readForegroundContext(ownPID uint32, ownHwnd uintptr) (mode string, app string, ok bool) {
	if !procAvailable(procGetForegroundWindow) || !procAvailable(procGetWindowThreadProcessId) {
		return "", "", false
	}
	fgHwnd, _, _ := procGetForegroundWindow.Call()
	if fgHwnd == 0 || (ownHwnd != 0 && fgHwnd == ownHwnd) {
		return "", "", false
	}

	var pid uint32
	_, _, _ = procGetWindowThreadProcessId.Call(fgHwnd, uintptr(unsafe.Pointer(&pid)))
	if pid == 0 || pid == ownPID {
		return "", "", false
	}

	var procName string
	if procAvailable(procOpenProcess) && procAvailable(procQueryFullProcessImageNameW) {
		hProc, _, _ := procOpenProcess.Call(processQueryLimitedInformation, 0, uintptr(pid))
		if hProc != 0 {
			buf := make([]uint16, 512)
			size := uint32(len(buf))
			ret, _, _ := procQueryFullProcessImageNameW.Call(
				hProc,
				0,
				uintptr(unsafe.Pointer(&buf[0])),
				uintptr(unsafe.Pointer(&size)),
			)
			_, _, _ = procCloseHandle.Call(hProc)
			if ret != 0 && size > 0 && int(size) <= len(buf) {
				procName = filepath.Base(syscall.UTF16ToString(buf[:size]))
			}
		}
	}

	var title string
	if procAvailable(procGetWindowTextW) {
		buf := make([]uint16, 256)
		n, _, _ := procGetWindowTextW.Call(fgHwnd, uintptr(unsafe.Pointer(&buf[0])), uintptr(len(buf)))
		if n > 0 && int(n) < len(buf) {
			title = syscall.UTF16ToString(buf[:n])
		}
	}

	var quns uint32
	if procAvailable(procSHQueryUserNotificationState) {
		hr, _, _ := procSHQueryUserNotificationState.Call(uintptr(unsafe.Pointer(&quns)))
		if int32(hr) < 0 {
			quns = 0
		}
	}

	m, a := classifyForegroundContext(procName, title, quns)
	return m, a, true
}

func runContextMonitor(ctx context.Context, emit func(string, any), ownerHwnd uintptr) {
	ticker := time.NewTicker(contextPollInterval)
	defer ticker.Stop()

	ownPID := uint32(os.Getpid())
	tracker := newContextDebounce()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			mode, app, ok := readForegroundContext(ownPID, ownerHwnd)
			if !ok {
				continue
			}
			if evt, emitNow := tracker.update(mode, app); emitNow {
				emit("win.context", evt)
			}
		}
	}
}

// --- 5. win.network ---

type networkDebounce struct {
	initialized   bool
	emittedOnline bool
	pendingOnline bool
	pendingCount  int
}

func (n *networkDebounce) update(online bool) (winNetworkData, bool) {
	if !n.initialized {
		n.initialized = true
		n.emittedOnline = online
		n.pendingOnline = online
		n.pendingCount = 0
		return winNetworkData{}, false
	}

	if online == n.emittedOnline {
		n.pendingOnline = online
		n.pendingCount = 0
		return winNetworkData{}, false
	}

	if online == n.pendingOnline {
		n.pendingCount++
	} else {
		n.pendingOnline = online
		n.pendingCount = 1
	}

	if n.pendingCount < 2 {
		return winNetworkData{}, false
	}

	n.emittedOnline = online
	n.pendingCount = 0
	return winNetworkData{Online: online}, true
}

func readInternetConnectedState() (bool, bool) {
	if !procAvailable(procInternetGetConnectedState) {
		return false, false
	}
	var flags uint32
	ret, _, _ := procInternetGetConnectedState.Call(uintptr(unsafe.Pointer(&flags)), 0)
	return ret != 0, true
}

func runNetworkMonitor(ctx context.Context, emit func(string, any)) {
	ticker := time.NewTicker(networkPollInterval)
	defer ticker.Stop()

	var tracker networkDebounce
	if online, ok := readInternetConnectedState(); ok {
		tracker.update(online)
	}

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			online, ok := readInternetConnectedState()
			if !ok {
				continue
			}
			if evt, emitNow := tracker.update(online); emitNow {
				emit("win.network", evt)
			}
		}
	}
}

// --- 6. win.volume (Core Audio COM) ---

func shouldEmitVolumeChange(prev, curr winVolumeData) bool {
	if prev.Muted != curr.Muted {
		return true
	}
	delta := curr.Percent - prev.Percent
	if delta < 0 {
		delta = -delta
	}
	return delta >= 2
}

func comVtblCall(obj unsafe.Pointer, slot int, args ...uintptr) uintptr {
	if obj == nil {
		return 0x80004003 // E_POINTER
	}
	vtblPtr := *(*unsafe.Pointer)(obj)
	if vtblPtr == nil {
		return 0x80004003
	}
	vtbl := (*[32]uintptr)(vtblPtr)
	callArgs := make([]uintptr, 0, 1+len(args))
	callArgs = append(callArgs, uintptr(obj))
	callArgs = append(callArgs, args...)
	ret, _, _ := syscall.SyscallN(vtbl[slot], callArgs...)
	return ret
}

func comRelease(obj unsafe.Pointer) {
	if obj != nil {
		_ = comVtblCall(obj, 2) // IUnknown::Release
	}
}

func readSystemVolumeFromEnumerator(enumerator unsafe.Pointer) (winVolumeData, bool) {
	if enumerator == nil {
		return winVolumeData{}, false
	}

	var device unsafe.Pointer
	// IMMDeviceEnumerator::GetDefaultAudioEndpoint (slot 4)
	hr := comVtblCall(enumerator, 4, eRender, eConsole, uintptr(unsafe.Pointer(&device)))
	if int32(hr) < 0 || device == nil {
		return winVolumeData{}, false
	}
	defer comRelease(device)

	var endpointVol unsafe.Pointer
	// IMMDevice::Activate (slot 3)
	hr = comVtblCall(
		device,
		3,
		uintptr(unsafe.Pointer(&iidIAudioEndpointVolume)),
		clsctxAll,
		0,
		uintptr(unsafe.Pointer(&endpointVol)),
	)
	if int32(hr) < 0 || endpointVol == nil {
		return winVolumeData{}, false
	}
	defer comRelease(endpointVol)

	var scalar float32
	// IAudioEndpointVolume::GetMasterVolumeLevelScalar (slot 9)
	hr = comVtblCall(endpointVol, 9, uintptr(unsafe.Pointer(&scalar)))
	if int32(hr) < 0 {
		return winVolumeData{}, false
	}

	var muteFlag int32
	// IAudioEndpointVolume::GetMute (slot 15)
	hr = comVtblCall(endpointVol, 15, uintptr(unsafe.Pointer(&muteFlag)))
	if int32(hr) < 0 {
		return winVolumeData{}, false
	}

	pct := int(math.Round(float64(scalar) * 100.0))
	if pct < 0 {
		pct = 0
	} else if pct > 100 {
		pct = 100
	}
	return winVolumeData{
		Percent: pct,
		Muted:   muteFlag != 0,
	}, true
}

func initCoreAudioEnumerator() (enumerator unsafe.Pointer, uninit func(), ok bool) {
	if !procAvailable(procCoInitializeEx) || !procAvailable(procCoCreateInstance) {
		return nil, func() {}, false
	}
	hrInit, _, _ := procCoInitializeEx.Call(0, coinitMultithreaded)
	shouldUninit := int32(hrInit) >= 0 // S_OK o S_FALSE
	if int32(hrInit) < 0 && uint32(hrInit) != rpcEChangedMode {
		return nil, func() {}, false
	}

	var enumPtr unsafe.Pointer
	hr := func() uintptr {
		r, _, _ := procCoCreateInstance.Call(
			uintptr(unsafe.Pointer(&clsidMMDeviceEnumerator)),
			0,
			clsctxAll,
			uintptr(unsafe.Pointer(&iidIMMDeviceEnumerator)),
			uintptr(unsafe.Pointer(&enumPtr)),
		)
		return r
	}()
	if int32(hr) < 0 || enumPtr == nil {
		if shouldUninit && procAvailable(procCoUninitialize) {
			_, _, _ = procCoUninitialize.Call()
		}
		return nil, func() {}, false
	}

	cleanup := func() {
		comRelease(enumPtr)
		if shouldUninit && procAvailable(procCoUninitialize) {
			_, _, _ = procCoUninitialize.Call()
		}
	}
	return enumPtr, cleanup, true
}

func runVolumeMonitor(ctx context.Context, emit func(string, any)) {
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()

	enumerator, cleanupCOM, ok := initCoreAudioEnumerator()
	if !ok {
		return
	}
	defer cleanupCOM()

	ticker := time.NewTicker(volumePollInterval)
	defer ticker.Stop()

	var initialized bool
	var prev winVolumeData

	check := func() {
		curr, readOK := readSystemVolumeFromEnumerator(enumerator)
		if !readOK {
			return
		}
		if !initialized {
			prev = curr
			initialized = true
			return
		}
		if shouldEmitVolumeChange(prev, curr) {
			prev = curr
			emit("win.volume", curr)
		}
	}

	check()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			check()
		}
	}
}
