//go:build windows

package main

import (
	"context"
	"encoding/json"
	"os"
	"strings"
	"sync"
	"testing"
	"time"
)

type mockNativeDispatcher struct {
	mu      sync.Mutex
	scripts []string
}

func (m *mockNativeDispatcher) Dispatch(f func()) {
	if f != nil {
		f()
	}
}

func (m *mockNativeDispatcher) Eval(js string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.scripts = append(m.scripts, js)
}

func (m *mockNativeDispatcher) Scripts() []string {
	m.mu.Lock()
	defer m.mu.Unlock()
	out := make([]string, len(m.scripts))
	copy(out, m.scripts)
	return out
}

func TestEvalIdleTransition(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		prevPhase string
		seconds   int
		wantPhase string
		wantEmit  bool
		wantIdle  bool
	}{
		{name: "active under 56s stays active", prevPhase: "active", seconds: 55, wantPhase: "active", wantEmit: false},
		{name: "active at 56s transitions to yawn", prevPhase: "active", seconds: 56, wantPhase: "yawn", wantEmit: true, wantIdle: false},
		{name: "yawn at 58s does not re-emit", prevPhase: "yawn", seconds: 58, wantPhase: "yawn", wantEmit: false},
		{name: "yawn at 60s transitions to sleeping", prevPhase: "yawn", seconds: 60, wantPhase: "sleeping", wantEmit: true, wantIdle: true},
		{name: "sleeping at 75s does not re-emit", prevPhase: "sleeping", seconds: 75, wantPhase: "sleeping", wantEmit: false},
		{name: "sleeping at 1s returns to active", prevPhase: "sleeping", seconds: 1, wantPhase: "active", wantEmit: true, wantIdle: false},
		{name: "yawn interrupted at 0s returns to active", prevPhase: "yawn", seconds: 0, wantPhase: "active", wantEmit: true, wantIdle: false},
		{name: "active at 0s does not emit transition", prevPhase: "active", seconds: 0, wantPhase: "active", wantEmit: false},
		{name: "empty prev phase jumps straight to sleeping at 65s", prevPhase: "", seconds: 65, wantPhase: "sleeping", wantEmit: true, wantIdle: true},
		{name: "negative seconds clamped to 0", prevPhase: "sleeping", seconds: -3, wantPhase: "active", wantEmit: true, wantIdle: false},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			gotPhase, gotEvt := evalIdleTransition(tc.prevPhase, tc.seconds)
			if gotPhase != tc.wantPhase {
				t.Fatalf("phase = %q, want %q", gotPhase, tc.wantPhase)
			}
			if (gotEvt != nil) != tc.wantEmit {
				t.Fatalf("emit = %v, want %v (evt=%+v)", gotEvt != nil, tc.wantEmit, gotEvt)
			}
			if gotEvt != nil {
				if gotEvt.Phase != tc.wantPhase {
					t.Errorf("evt.Phase = %q, want %q", gotEvt.Phase, tc.wantPhase)
				}
				if gotEvt.Idle != tc.wantIdle {
					t.Errorf("evt.Idle = %v, want %v", gotEvt.Idle, tc.wantIdle)
				}
			}
		})
	}
}

func TestClassifyForegroundContext(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name     string
		procName string
		title    string
		quns     uint32
		wantMode string
		wantApp  string
	}{
		{name: "vscode coding", procName: "Code.exe", title: "events_windows.go - Visual Studio Code", quns: 5, wantMode: "coding", wantApp: "Code"},
		{name: "windows terminal coding", procName: "WindowsTerminal.exe", title: "PowerShell", quns: 5, wantMode: "coding", wantApp: "WindowsTerminal"},
		{name: "vscode web in browser", procName: "msedge.exe", title: "app.js - vscode.dev", quns: 5, wantMode: "coding", wantApp: "msedge"},
		{name: "zoom meeting", procName: "Zoom.exe", title: "Zoom Meeting", quns: 5, wantMode: "meeting", wantApp: "Zoom"},
		{name: "google meet in chrome", procName: "chrome.exe", title: "Meet - abc-defg-hij - Google Chrome", quns: 5, wantMode: "meeting", wantApp: "chrome"},
		{name: "discord voice call", procName: "Discord.exe", title: "Voice Connected - General", quns: 5, wantMode: "meeting", wantApp: "Discord"},
		{name: "discord text chat stays normal", procName: "Discord.exe", title: "#general - Discord", quns: 5, wantMode: "normal", wantApp: "Discord"},
		{name: "youtube fullscreen in chrome", procName: "chrome.exe", title: "Lo-fi Radio - YouTube", quns: qunsBusy, wantMode: "media_fullscreen", wantApp: "chrome"},
		{name: "vlc fullscreen", procName: "vlc.exe", title: "Movie.mkv - VLC media player", quns: qunsRunningD3DFullScreen, wantMode: "media_fullscreen", wantApp: "vlc"},
		{name: "known game process", procName: "VALORANT-Win64-Shipping.exe", title: "VALORANT", quns: 5, wantMode: "gaming", wantApp: "VALORANT-Win64-Shipping"},
		{name: "d3d fullscreen unknown game", procName: "MyIndieGame.exe", title: "Adventure", quns: qunsRunningD3DFullScreen, wantMode: "gaming", wantApp: "MyIndieGame"},
		{name: "quns busy non-game fullscreen stays normal", procName: "FullScreenReader.exe", title: "Documento", quns: qunsBusy, wantMode: "normal", wantApp: "FullScreenReader"},
		{name: "explorer fullscreen not gaming", procName: "explorer.exe", title: "Explorador de archivos", quns: qunsBusy, wantMode: "normal", wantApp: "explorer"},
		{name: "normal browser", procName: "chrome.exe", title: "Wikipedia", quns: 5, wantMode: "normal", wantApp: "chrome"},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			gotMode, gotApp := classifyForegroundContext(tc.procName, tc.title, tc.quns)
			if gotMode != tc.wantMode || gotApp != tc.wantApp {
				t.Errorf("classifyForegroundContext(%q, %q, %d) = (%q, %q), want (%q, %q)",
					tc.procName, tc.title, tc.quns, gotMode, gotApp, tc.wantMode, tc.wantApp)
			}
		})
	}
}

func TestContextDebounce(t *testing.T) {
	t.Parallel()

	d := newContextDebounce()
	if _, emit := d.update("normal", "chrome"); emit {
		t.Fatal("no debería emitir normal -> normal")
	}
	if _, emit := d.update("coding", "Code"); emit {
		t.Fatal("primera muestra coding no debe emitir sin debounce")
	}
	evt, emit := d.update("coding", "Code")
	if !emit || evt.Mode != "coding" || evt.App != "Code" {
		t.Fatalf("segunda muestra coding debe emitir; got (%+v, %v)", evt, emit)
	}
	if _, emit := d.update("coding", "Code"); emit {
		t.Fatal("no debe re-emitir el mismo modo/app")
	}
	if _, emit := d.update("normal", "chrome"); emit {
		t.Fatal("primera muestra normal no debe emitir sin debounce")
	}
	evt, emit = d.update("normal", "chrome")
	if !emit || evt.Mode != "normal" {
		t.Fatalf("segunda muestra normal tras coding debe emitir; got (%+v, %v)", evt, emit)
	}
}

func TestPowerParsingAndComparison(t *testing.T) {
	t.Parallel()

	laptopLow := parseSystemPowerStatus(systemPowerStatus{
		ACLineStatus:       0,
		BatteryFlag:        2,
		BatteryLifePercent: 18,
		SystemStatusFlag:   1,
	})
	if laptopLow.Plugged || laptopLow.Percent != 18 || !laptopLow.Low || !laptopLow.Saver {
		t.Fatalf("parseSystemPowerStatus(laptopLow) inesperado: %+v", laptopLow)
	}

	laptopChargingLow := parseSystemPowerStatus(systemPowerStatus{
		ACLineStatus:       1,
		BatteryFlag:        8,
		BatteryLifePercent: 18,
		SystemStatusFlag:   0,
	})
	if !laptopChargingLow.Plugged || laptopChargingLow.Low || laptopChargingLow.Saver {
		t.Fatalf("cargando al 18%% no debe marcar low/saver: %+v", laptopChargingLow)
	}

	desktopNoBattery := parseSystemPowerStatus(systemPowerStatus{
		ACLineStatus:       1,
		BatteryFlag:        128,
		BatteryLifePercent: 255,
		SystemStatusFlag:   0,
	})
	if !desktopNoBattery.Plugged || desktopNoBattery.Percent != 100 || desktopNoBattery.Low {
		t.Fatalf("PC de escritorio sin batería inesperado: %+v", desktopNoBattery)
	}

	if shouldEmitPowerChange(laptopLow, laptopLow) {
		t.Fatal("sin cambios no debe emitir win.power")
	}
	laptopDrop := laptopLow
	laptopDrop.Percent = 17
	if !shouldEmitPowerChange(laptopLow, laptopDrop) {
		t.Fatal("cambio de porcentaje debe emitir win.power")
	}
	if !shouldEmitPowerChange(laptopLow, laptopChargingLow) {
		t.Fatal("cambio de cargador debe emitir win.power")
	}
}

func TestVolumeComparison(t *testing.T) {
	t.Parallel()

	base := winVolumeData{Percent: 50, Muted: false}
	if shouldEmitVolumeChange(base, winVolumeData{Percent: 51, Muted: false}) {
		t.Fatal("delta de 1% sin cambio de mute no debe emitir")
	}
	if !shouldEmitVolumeChange(base, winVolumeData{Percent: 52, Muted: false}) {
		t.Fatal("delta >= 2% debe emitir")
	}
	if !shouldEmitVolumeChange(base, winVolumeData{Percent: 48, Muted: false}) {
		t.Fatal("delta -2% debe emitir")
	}
	if !shouldEmitVolumeChange(base, winVolumeData{Percent: 50, Muted: true}) {
		t.Fatal("cambio de mute debe emitir aunque delta sea 0%")
	}
}

func TestSessionDeviceAndNetworkHelpers(t *testing.T) {
	t.Parallel()

	if st, ok := classifySessionMessage(wmWtsSessionChange, wtsSessionLock); !ok || st != "locked" {
		t.Fatalf("lock = (%q, %v), want (locked, true)", st, ok)
	}
	if st, ok := classifySessionMessage(wmWtsSessionChange, wtsSessionUnlock); !ok || st != "unlocked" {
		t.Fatalf("unlock = (%q, %v), want (unlocked, true)", st, ok)
	}
	if st, ok := classifySessionMessage(wmPowerBroadcast, pbtApmSuspend); !ok || st != "suspend" {
		t.Fatalf("suspend = (%q, %v), want (suspend, true)", st, ok)
	}
	if st, ok := classifySessionMessage(wmPowerBroadcast, pbtApmResumeAutomatic); !ok || st != "resume" {
		t.Fatalf("resume = (%q, %v), want (resume, true)", st, ok)
	}

	if st, kind, ok := classifyDeviceEvent(dbtDeviceArrival, 1, 2); !ok || st != "connected" || kind != "audio" {
		t.Fatalf("audio connect = (%q, %q, %v)", st, kind, ok)
	}
	if st, kind, ok := classifyDeviceEvent(dbtDeviceRemoveComplete, 2, 2); !ok || st != "disconnected" || kind != "usb" {
		t.Fatalf("usb disconnect = (%q, %q, %v)", st, kind, ok)
	}

	var netDeb networkDebounce
	if _, emit := netDeb.update(true); emit {
		t.Fatal("baseline inicial de red no debe emitir")
	}
	if _, emit := netDeb.update(false); emit {
		t.Fatal("primera caída de red debe esperar debounce")
	}
	evt, emit := netDeb.update(false)
	if !emit || evt.Online {
		t.Fatalf("segunda caída de red debe emitir offline=false; got (%+v, %v)", evt, emit)
	}

	// Deduplicación de PBT_APMRESUMEAUTOMATIC + PBT_APMRESUMESUSPEND cercanos en win.session
	var emitted []string
	sink := &messageSinkState{
		ctx: context.Background(),
		emit: func(evType string, data any) {
			if evType == "win.session" {
				if sd, ok := data.(winSessionData); ok {
					emitted = append(emitted, sd.State)
				}
			}
		},
	}
	sink.handleSessionOrPower(wmPowerBroadcast, pbtApmResumeAutomatic)
	sink.handleSessionOrPower(wmPowerBroadcast, pbtApmResumeSuspend)
	sink.handleSessionOrPower(wmWtsSessionChange, wtsSessionLock)
	if len(emitted) != 2 || emitted[0] != "resume" || emitted[1] != "locked" {
		t.Fatalf("secuencia win.session inesperada: %v", emitted)
	}
}

func TestNativeEventJSONSerializationAndEmitterCancel(t *testing.T) {
	t.Parallel()

	cases := []struct {
		eventType string
		data      any
		wantKeys  []string
	}{
		{"win.idle", winIdleData{Phase: "yawn", Idle: false, Seconds: 56}, []string{`"type":"win.idle"`, `"phase":"yawn"`, `"idle":false`, `"seconds":56`}},
		{"win.power", winPowerData{Plugged: true, Percent: 85, Low: false, Saver: false}, []string{`"type":"win.power"`, `"plugged":true`, `"percent":85`}},
		{"win.session", winSessionData{State: "locked"}, []string{`"type":"win.session"`, `"state":"locked"`}},
		{"win.device", winDeviceData{State: "connected", Kind: "audio"}, []string{`"type":"win.device"`, `"state":"connected"`, `"kind":"audio"`}},
		{"win.screenshot", winScreenshotData{Source: "clipboard"}, []string{`"type":"win.screenshot"`, `"source":"clipboard"`}},
		{"win.context", winContextData{Mode: "coding", App: "Code"}, []string{`"type":"win.context"`, `"mode":"coding"`, `"app":"Code"`}},
		{"win.network", winNetworkData{Online: false}, []string{`"type":"win.network"`, `"online":false`}},
		{"win.volume", winVolumeData{Percent: 42, Muted: true}, []string{`"type":"win.volume"`, `"percent":42`, `"muted":true`}},
	}

	for _, tc := range cases {
		raw, err := marshalNativeEvent(tc.eventType, tc.data)
		if err != nil {
			t.Fatalf("marshalNativeEvent(%s) falló: %v", tc.eventType, err)
		}
		var parsed map[string]any
		if err := json.Unmarshal([]byte(raw), &parsed); err != nil {
			t.Fatalf("JSON inválido para %s: %v", tc.eventType, err)
		}
		for _, sub := range tc.wantKeys {
			if !strings.Contains(raw, sub) {
				t.Errorf("%s JSON %s no contiene %s", tc.eventType, raw, sub)
			}
		}
	}

	ctx, cancel := context.WithCancel(context.Background())
	disp := &mockNativeDispatcher{}
	emitter := newNativeEventEmitter(ctx, disp)

	emitter.emit("win.screenshot", winScreenshotData{Source: "clipboard"})
	if len(disp.Scripts()) != 1 {
		t.Fatalf("se esperaba 1 script despachado, obtenido %d", len(disp.Scripts()))
	}
	if !strings.HasPrefix(disp.Scripts()[0], "window.MEKA?.emitNativeEvent(") {
		t.Fatalf("script inesperado: %s", disp.Scripts()[0])
	}

	cancel()
	emitter.emit("win.network", winNetworkData{Online: true})
	if len(disp.Scripts()) != 1 {
		t.Fatalf("no debe despachar eventos tras cancelar ctx; scripts=%d", len(disp.Scripts()))
	}
}

func TestNativeEventEmitterConcurrentCancel(t *testing.T) {
	t.Parallel()

	ctx, cancel := context.WithCancel(context.Background())
	disp := &mockNativeDispatcher{}
	emitter := newNativeEventEmitter(ctx, disp)

	var wg sync.WaitGroup
	for i := 0; i < 16; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			for j := 0; j < 25; j++ {
				emitter.emit("win.volume", winVolumeData{Percent: (id + j) % 100, Muted: false})
			}
		}(i)
	}
	time.Sleep(2 * time.Millisecond)
	cancel()
	wg.Wait()
}

func TestWindowsNativeSensorsNoPanic(t *testing.T) {
	// Verifica que todas las llamadas Win32 y Core Audio COM operen de forma segura sin pánicos.
	_, _ = readSystemIdleSeconds()
	_, _ = readSystemPowerStatus()
	_, _, _ = readForegroundContext(uint32(os.Getpid()), 0)
	_, _ = readInternetConnectedState()
	_ = getWaveOutNumDevs()
	_ = hasClipboardImage()

	if _, ok := readSystemVolumeFromEnumerator(nil); ok {
		t.Fatal("readSystemVolumeFromEnumerator(nil) no debe reportar éxito")
	}

	enumPtr, cleanup, ok := initCoreAudioEnumerator()
	if ok {
		defer cleanup()
		if vol, readOK := readSystemVolumeFromEnumerator(enumPtr); readOK {
			if vol.Percent < 0 || vol.Percent > 100 {
				t.Fatalf("volumen fuera de rango [0,100]: %d", vol.Percent)
			}
		}
	}
}

func TestWindowsEventMonitorContextLifecycle(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	disp := &mockNativeDispatcher{}

	wg := runWindowsEventMonitors(ctx, disp, 0)
	time.Sleep(150 * time.Millisecond)
	cancel()

	done := make(chan struct{})
	go func() {
		wg.Wait()
		close(done)
	}()

	select {
	case <-done:
	case <-time.After(3 * time.Second):
		t.Fatal("timeout esperando cierre limpio de los monitores Win32 al cancelar context")
	}
}
