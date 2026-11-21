//go:build windows

package main

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"sync/atomic"
	"testing"
	"time"
	"unsafe"
)

func TestWin32ABIStructSizes(t *testing.T) {
	t.Parallel()
	if runtime.GOARCH == "amd64" {
		if got := unsafe.Sizeof(jobObjectExtendedLimitInformation{}); got != 144 {
			t.Fatalf("sizeof(jobObjectExtendedLimitInformation) = %d, se esperaba 144 en amd64", got)
		}
		if got := unsafe.Sizeof(notifyIconDataW{}); got != 976 {
			t.Fatalf("sizeof(notifyIconDataW) = %d, se esperaba 976 en amd64", got)
		}
	}
}

func TestCreateKillOnCloseJob(t *testing.T) {
	job, err := createKillOnCloseJob()
	if err != nil {
		t.Fatalf("createKillOnCloseJob falló: %v", err)
	}
	if job == nil || job.handle == 0 {
		t.Fatal("se esperaba un handle válido de Job Object")
	}
	job.close()
	job.close() // idempotente
}

func TestResolveDesktopDir(t *testing.T) {
	t.Parallel()
	got := resolveDesktopDir(`C:\Users\FallbackUser`)
	if strings.TrimSpace(got) == "" {
		t.Fatal("resolveDesktopDir devolvió cadena vacía")
	}
}

func TestBuildAutoStartCommand(t *testing.T) {
	t.Parallel()
	if got := buildAutoStartCommand(`C:\Users\Test\AppData\Local\Programs\MEKA\MEKA.exe`); got != `"C:\Users\Test\AppData\Local\Programs\MEKA\MEKA.exe" --startup` {
		t.Fatalf("buildAutoStartCommand inesperado: %q", got)
	}
	if got := buildAutoStartCommand("   "); got != "" {
		t.Fatalf("entrada vacía debía devolver '', obtuvo %q", got)
	}
}

func TestComputeClickThroughInterval(t *testing.T) {
	t.Parallel()
	r := rectF{Left: 72, Top: 8, Right: 308, Bottom: 54}

	nearMoved := computeClickThroughInterval(point{X: 150, Y: 30}, r, 1.0, true)
	if nearMoved != 16*time.Millisecond {
		t.Fatalf("nearMoved = %s, want 16ms", nearMoved)
	}

	nearIdle := computeClickThroughInterval(point{X: 150, Y: 30}, r, 1.0, false)
	if nearIdle != 32*time.Millisecond {
		t.Fatalf("nearIdle = %s, want 32ms", nearIdle)
	}

	farMoved := computeClickThroughInterval(point{X: 900, Y: 700}, r, 1.0, true)
	if farMoved != 48*time.Millisecond {
		t.Fatalf("farMoved = %s, want 48ms", farMoved)
	}

	farIdle := computeClickThroughInterval(point{X: 900, Y: 700}, r, 1.0, false)
	if farIdle != 80*time.Millisecond {
		t.Fatalf("farIdle = %s, want 80ms", farIdle)
	}
}

func TestCoreRestartTracker(t *testing.T) {
	t.Parallel()
	var tr coreRestartTracker
	t0 := time.Now()

	for i := 0; i < 4; i++ {
		delay, tripped := tr.recordAttempt(t0.Add(time.Duration(i) * time.Second))
		if tripped || delay != 0 {
			t.Fatalf("intento %d no debía disparar circuit breaker: tripped=%v delay=%s", i+1, tripped, delay)
		}
	}

	delay5, tripped5 := tr.recordAttempt(t0.Add(5 * time.Second))
	if !tripped5 || delay5 != 4*time.Second {
		t.Fatalf("intento 5 = (%s, %v), want (4s, true)", delay5, tripped5)
	}

	delay6, tripped6 := tr.recordAttempt(t0.Add(10 * time.Second))
	if !tripped6 || delay6 != 8*time.Second {
		t.Fatalf("intento 6 = (%s, %v), want (8s, true)", delay6, tripped6)
	}

	tr.reset()
	if delayAfter, trippedAfter := tr.recordAttempt(t0.Add(15 * time.Second)); trippedAfter || delayAfter != 0 {
		t.Fatalf("tras reset no debía disparar circuit breaker: (%s, %v)", delayAfter, trippedAfter)
	}
}

func TestShutdownCoordinatorIdempotent(t *testing.T) {
	t.Parallel()
	var calls atomic.Int32
	s := newShutdownCoordinator(shutdownCoordinator{
		cancel:     func() { calls.Add(1) },
		stopTray:   func() { calls.Add(1) },
		stopHTTP:   func() { calls.Add(1) },
		stopCore:   func() { calls.Add(1) },
		closeJob:   func() { calls.Add(1) },
		closeMutex: func() { calls.Add(1) },
		terminateUI: func() {
			calls.Add(1)
		},
		exitProcess: func(int) {},
		hardTimeout: 2 * time.Second,
	})

	s.trigger("test-1")
	s.trigger("test-2")
	s.markFinished()

	if got := calls.Load(); got != 7 {
		t.Fatalf("callbacks ejecutados = %d, want 7 (idempotente)", got)
	}
}

func TestLogRotation(t *testing.T) {
	t.Parallel()
	dir := t.TempDir()
	logPath := filepath.Join(dir, "desktop.log")

	if err := os.WriteFile(logPath, []byte(strings.Repeat("x", 256)), 0644); err != nil {
		t.Fatalf("no se pudo crear log de prueba: %v", err)
	}
	rotateLogIfNeeded(logPath, 100)

	if _, err := os.Stat(logPath + ".old"); err != nil {
		t.Fatalf("se esperaba desktop.log.old tras rotación: %v", err)
	}
	logDesktopEventTo(logPath, "INFO", "test", "nueva entrada")
	content, err := os.ReadFile(logPath)
	if err != nil || !strings.Contains(string(content), "[INFO] [test] nueva entrada") {
		t.Fatalf("log tras rotación inesperado: err=%v content=%q", err, string(content))
	}
}
