//go:build windows

package main

import (
	"context"
	"fmt"
	"os/exec"
	"path/filepath"
	"runtime"
	"sync"
	"sync/atomic"
	"syscall"
	"unsafe"
)

const (
	nimAdd    = 0x00000000
	nimModify = 0x00000001
	nimDelete = 0x00000002

	nifMessage = 0x00000001
	nifIcon    = 0x00000002
	nifTip     = 0x00000004
	nifInfo    = 0x00000010

	niifInfo = 0x00000001

	wmNull            = 0x0000
	wmQueryEndSession = 0x0011
	wmEndSession      = 0x0016
	wmAppTray         = 0x8001

	wmLButtonUp     = 0x0202
	wmLButtonDblClk = 0x0203
	wmRButtonUp     = 0x0205
	wmContextMenu   = 0x007B

	mfString  = 0x00000000
	mfChecked = 0x00000008
	mfSep     = 0x00000800

	tpmRightButton = 0x0002
	tpmBottomAlign = 0x0020
	tpmReturnCmd   = 0x0100

	trayMenuToggleVisibility = 1000
	trayMenuShowCenter       = 1001
	trayMenuToggleExpand     = 1002
	trayMenuAutoStart        = 1003
	trayMenuRestartCore      = 1004
	trayMenuOpenLogs         = 1005
	trayMenuExit             = 1006
)

var (
	procShellNotifyIconW      = shell32.NewProc("Shell_NotifyIconW")
	procRegisterWindowMsgW    = user32.NewProc("RegisterWindowMessageW")
	procCreatePopupMenu       = user32.NewProc("CreatePopupMenu")
	procDestroyMenu           = user32.NewProc("DestroyMenu")
	procAppendMenuW           = user32.NewProc("AppendMenuW")
	procTrackPopupMenu        = user32.NewProc("TrackPopupMenu")
	procDestroyIcon           = user32.NewProc("DestroyIcon")

	trayClassSeq  atomic.Uint64
	trayProcOnce  sync.Once
	trayProcPtr   uintptr
	trayWinMu     sync.RWMutex
	trayWinStates = make(map[uintptr]*trayController)

	activeTrayMu sync.RWMutex
	activeTray   *trayController
)

type notifyIconDataW struct {
	cbSize            uint32
	hWnd              uintptr
	uID               uint32
	uFlags            uint32
	uCallbackMessage  uint32
	hIcon             uintptr
	szTip             [128]uint16
	dwState           uint32
	dwStateMask       uint32
	szInfo            [256]uint16
	uTimeoutOrVersion uint32
	szInfoTitle       [64]uint16
	dwInfoFlags       uint32
	guidItem          guid
	hBalloonIcon      uintptr
}

type trayActions struct {
	IsVisible          func() bool
	OnToggleVisibility func()
	OnShowCenter       func()
	OnToggleExpand     func()
	OnToggleAuto       func()
	OnRestartCore      func()
	OnOpenLogs         func()
	OnExit             func(reason string)
}

type trayController struct {
	webDir            string
	actions           trayActions
	hwnd              uintptr
	hIcon             uintptr
	iconLoadedOwned   bool
	taskbarCreatedMsg uint32
	showIslandMsg     uint32
	iconAdded         bool
	mu                sync.Mutex
	closed            bool
}

func copyUTF16Fixed(dst []uint16, text string) {
	if len(dst) == 0 {
		return
	}
	for i := range dst {
		dst[i] = 0
	}
	u16, err := syscall.UTF16FromString(text)
	if err != nil {
		return
	}
	limit := len(dst) - 1
	if len(u16) < limit {
		limit = len(u16)
	}
	copy(dst[:limit], u16[:limit])
	dst[limit] = 0
}

func loadTrayIconHandle(webDir string) (uintptr, bool) {
	if iconPath := resolveAppIconPath(webDir); iconPath != "" && procAvailable(procLoadImageW) {
		if ptr, err := syscall.UTF16PtrFromString(iconPath); err == nil {
			h, _, _ := procLoadImageW.Call(0, uintptr(unsafe.Pointer(ptr)), imageIcon, 32, 32, lrLoadFromFile)
			if h != 0 {
				return h, true
			}
		}
	}
	if procAvailable(procGetModuleHandleW) && procAvailable(procLoadIconW) {
		if hMod, _, _ := procGetModuleHandleW.Call(0); hMod != 0 {
			h, _, _ := procLoadIconW.Call(hMod, uintptr(1))
			if h != 0 {
				return h, false
			}
		}
	}
	return 0, false
}

func (t *trayController) addOrUpdateIcon(modify bool) {
	if t == nil || !procAvailable(procShellNotifyIconW) {
		return
	}
	t.mu.Lock()
	defer t.mu.Unlock()
	if t.closed || t.hwnd == 0 {
		return
	}

	var nid notifyIconDataW
	nid.cbSize = uint32(unsafe.Sizeof(nid))
	nid.hWnd = t.hwnd
	nid.uID = 1
	nid.uFlags = nifMessage | nifTip
	nid.uCallbackMessage = wmAppTray
	if t.hIcon != 0 {
		nid.hIcon = t.hIcon
		nid.uFlags |= nifIcon
	}
	copyUTF16Fixed(nid.szTip[:], "MEKA · En segundo plano (clic para mostrar/ocultar)")

	action := uintptr(nimAdd)
	if modify && t.iconAdded {
		action = nimModify
	}
	ret, _, _ := procShellNotifyIconW.Call(action, uintptr(unsafe.Pointer(&nid)))
	if ret == 0 && modify {
		// Si Explorer reinició el área de notificaciones, reintentar con NIM_ADD
		ret, _, _ = procShellNotifyIconW.Call(nimAdd, uintptr(unsafe.Pointer(&nid)))
	}
	if ret != 0 {
		t.iconAdded = true
	}
}

func (t *trayController) showBalloon(title, body string) {
	if t == nil || !procAvailable(procShellNotifyIconW) {
		return
	}
	t.mu.Lock()
	defer t.mu.Unlock()
	if t.closed || t.hwnd == 0 {
		return
	}

	var nid notifyIconDataW
	nid.cbSize = uint32(unsafe.Sizeof(nid))
	nid.hWnd = t.hwnd
	nid.uID = 1
	nid.uFlags = nifInfo | nifMessage | nifTip
	nid.uCallbackMessage = wmAppTray
	if t.hIcon != 0 {
		nid.hIcon = t.hIcon
		nid.uFlags |= nifIcon
	}
	nid.dwInfoFlags = niifInfo
	nid.uTimeoutOrVersion = 4500
	copyUTF16Fixed(nid.szTip[:], "MEKA · Compañera de Escritorio")
	copyUTF16Fixed(nid.szInfoTitle[:], title)
	copyUTF16Fixed(nid.szInfo[:], body)

	if !t.iconAdded {
		if ret, _, _ := procShellNotifyIconW.Call(nimAdd, uintptr(unsafe.Pointer(&nid))); ret != 0 {
			t.iconAdded = true
		}
		return
	}
	_, _, _ = procShellNotifyIconW.Call(nimModify, uintptr(unsafe.Pointer(&nid)))
}

func (t *trayController) removeIconAndClose() {
	if t == nil {
		return
	}
	t.mu.Lock()
	alreadyClosed := t.closed
	t.closed = true
	hwnd := t.hwnd
	hadIcon := t.iconAdded
	hIcon := t.hIcon
	ownedIcon := t.iconLoadedOwned
	t.iconAdded = false
	t.hIcon = 0
	t.mu.Unlock()

	if alreadyClosed {
		return
	}
	if hadIcon && hwnd != 0 && procAvailable(procShellNotifyIconW) {
		var nid notifyIconDataW
		nid.cbSize = uint32(unsafe.Sizeof(nid))
		nid.hWnd = hwnd
		nid.uID = 1
		_, _, _ = procShellNotifyIconW.Call(nimDelete, uintptr(unsafe.Pointer(&nid)))
	}
	if ownedIcon && hIcon != 0 && procAvailable(procDestroyIcon) {
		_, _, _ = procDestroyIcon.Call(hIcon)
	}
	if hwnd != 0 && procAvailable(procPostMessageW) {
		_, _, _ = procPostMessageW.Call(hwnd, wmClose, 0, 0)
	}
}

func (t *trayController) showContextMenu() {
	if t == nil || t.hwnd == 0 || !procAvailable(procCreatePopupMenu) || !procAvailable(procAppendMenuW) || !procAvailable(procTrackPopupMenu) {
		return
	}
	hMenu, _, _ := procCreatePopupMenu.Call()
	if hMenu == 0 {
		return
	}
	defer func() {
		if procAvailable(procDestroyMenu) {
			_, _, _ = procDestroyMenu.Call(hMenu)
		}
	}()

	addItem := func(flags uintptr, id uintptr, label string) {
		if label == "" {
			_, _, _ = procAppendMenuW.Call(hMenu, flags, id, 0)
			return
		}
		ptr, _ := syscall.UTF16PtrFromString(label)
		_, _, _ = procAppendMenuW.Call(hMenu, flags, id, uintptr(unsafe.Pointer(ptr)))
	}

	toggleLabel := "Mostrar MEKA"
	if t.actions.IsVisible != nil && t.actions.IsVisible() {
		toggleLabel = "Ocultar en la bandeja"
	}

	autoFlags := uintptr(mfString)
	if isAutoStartEnabled() {
		autoFlags |= mfChecked
	}

	addItem(mfString, trayMenuToggleVisibility, toggleLabel)
	addItem(mfString, trayMenuShowCenter, "Centrar MEKA")
	addItem(mfString, trayMenuToggleExpand, "Expandir / Colapsar Dynamic Island")
	addItem(mfSep, 0, "")
	addItem(autoFlags, trayMenuAutoStart, "Iniciar con Windows")
	addItem(mfString, trayMenuRestartCore, "Reiniciar MEKA Core")
	addItem(mfString, trayMenuOpenLogs, "Abrir carpeta de logs")
	addItem(mfSep, 0, "")
	addItem(mfString, trayMenuExit, "Salir de MEKA")

	var pt point
	if procAvailable(procGetCursorPos) {
		_, _, _ = procGetCursorPos.Call(uintptr(unsafe.Pointer(&pt)))
	}
	if procAvailable(procSetForegroundWindow) {
		_, _, _ = procSetForegroundWindow.Call(t.hwnd)
	}

	cmdID, _, _ := procTrackPopupMenu.Call(
		hMenu,
		tpmRightButton|tpmBottomAlign|tpmReturnCmd,
		uintptr(pt.X),
		uintptr(pt.Y),
		0,
		t.hwnd,
		0,
	)
	if procAvailable(procPostMessageW) {
		_, _, _ = procPostMessageW.Call(t.hwnd, wmNull, 0, 0)
	}

	switch cmdID {
	case trayMenuToggleVisibility:
		if t.actions.OnToggleVisibility != nil {
			go func() { defer recoverAndLog("tray-toggle-visibility"); t.actions.OnToggleVisibility() }()
		}
	case trayMenuShowCenter:
		if t.actions.OnShowCenter != nil {
			go func() { defer recoverAndLog("tray-show"); t.actions.OnShowCenter() }()
		}
	case trayMenuToggleExpand:
		if t.actions.OnToggleExpand != nil {
			go func() { defer recoverAndLog("tray-expand"); t.actions.OnToggleExpand() }()
		}
	case trayMenuAutoStart:
		if t.actions.OnToggleAuto != nil {
			go func() {
				defer recoverAndLog("tray-autostart")
				t.actions.OnToggleAuto()
			}()
		}
	case trayMenuRestartCore:
		if t.actions.OnRestartCore != nil {
			go func() { defer recoverAndLog("tray-restart-core"); t.actions.OnRestartCore() }()
		}
	case trayMenuOpenLogs:
		if t.actions.OnOpenLogs != nil {
			go func() { defer recoverAndLog("tray-open-logs"); t.actions.OnOpenLogs() }()
		}
	case trayMenuExit:
		if t.actions.OnExit != nil {
			go func() { defer recoverAndLog("tray-exit"); t.actions.OnExit("menu-tray") }()
		}
	}
}

func showTrayBalloon(title, body string) {
	activeTrayMu.RLock()
	ctrl := activeTray
	activeTrayMu.RUnlock()
	if ctrl != nil {
		ctrl.showBalloon(title, body)
	}
}

func getTrayWindowProc() uintptr {
	trayProcOnce.Do(func() {
		trayProcPtr = syscall.NewCallback(func(hwnd uintptr, msg uint32, wParam, lParam uintptr) uintptr {
			trayWinMu.RLock()
			ctrl := trayWinStates[hwnd]
			trayWinMu.RUnlock()

			if ctrl != nil {
				if ctrl.taskbarCreatedMsg != 0 && msg == ctrl.taskbarCreatedMsg {
					ctrl.addOrUpdateIcon(false)
					return 0
				}
				if ctrl.showIslandMsg != 0 && msg == ctrl.showIslandMsg {
					if ctrl.actions.OnShowCenter != nil {
						go func() { defer recoverAndLog("tray-show-island"); ctrl.actions.OnShowCenter() }()
					}
					return 0
				}
				switch msg {
				case wmAppTray:
					switch lParam {
					case wmLButtonUp:
						if ctrl.actions.OnToggleVisibility != nil {
							go func() { defer recoverAndLog("tray-click"); ctrl.actions.OnToggleVisibility() }()
						} else if ctrl.actions.OnShowCenter != nil {
							go func() { defer recoverAndLog("tray-click"); ctrl.actions.OnShowCenter() }()
						}
					case wmRButtonUp, wmContextMenu:
						ctrl.showContextMenu()
					}
					return 0
				case wmQueryEndSession:
					logDesktopEvent("INFO", "session-end", "Windows notificó WM_QUERYENDSESSION")
					return 1
				case wmEndSession:
					if wParam != 0 {
						logDesktopEvent("INFO", "session-end", "Windows notificó WM_ENDSESSION; cerrando MEKA limpiamente")
						if ctrl.actions.OnExit != nil {
							ctrl.actions.OnExit("windows-endsession")
						}
					}
					return 0
				case wmClose:
					if procAvailable(procDestroyWindow) {
						_, _, _ = procDestroyWindow.Call(hwnd)
					}
					return 0
				case wmDestroy:
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
	return trayProcPtr
}

func openMekaLogsDirectory() {
	dir := filepath.Dir(resolveDesktopLogPath())
	cmd := exec.Command("explorer.exe", dir)
	cmd.SysProcAttr = &syscall.SysProcAttr{
		HideWindow:    true,
		CreationFlags: 0x08000000,
	}
	_ = cmd.Start()
}

func startTrayController(ctx context.Context, webDir string, actions trayActions) func() {
	if ctx == nil || !procAvailable(procRegisterClassExW) || !procAvailable(procCreateWindowExW) || !procAvailable(procGetMessageW) {
		return func() {}
	}

	ctrl := &trayController{
		webDir:  webDir,
		actions: actions,
	}
	readyCh := make(chan struct{})

	go func() {
		defer recoverAndLog("tray-loop")
		runtime.LockOSThread()
		defer runtime.UnlockOSThread()

		var hInst uintptr
		if procAvailable(procGetModuleHandleW) {
			hInst, _, _ = procGetModuleHandleW.Call(0)
		}

		if procAvailable(procRegisterWindowMsgW) {
			if msgPtr, err := syscall.UTF16PtrFromString("TaskbarCreated"); err == nil {
				id, _, _ := procRegisterWindowMsgW.Call(uintptr(unsafe.Pointer(msgPtr)))
				ctrl.taskbarCreatedMsg = uint32(id)
			}
			if msgPtr, err := syscall.UTF16PtrFromString("MEKA_SHOW_ISLAND"); err == nil {
				id, _, _ := procRegisterWindowMsgW.Call(uintptr(unsafe.Pointer(msgPtr)))
				ctrl.showIslandMsg = uint32(id)
			}
		}

		className := fmt.Sprintf("MEKATrayWindow_%d", trayClassSeq.Add(1))
		classPtr, err := syscall.UTF16PtrFromString(className)
		if err != nil {
			close(readyCh)
			return
		}
		titlePtr, _ := syscall.UTF16PtrFromString("MEKA Tray Host")

		wc := wndClassExW{
			cbSize:        uint32(unsafe.Sizeof(wndClassExW{})),
			lpfnWndProc:   getTrayWindowProc(),
			hInstance:     hInst,
			lpszClassName: classPtr,
		}
		atom, _, _ := procRegisterClassExW.Call(uintptr(unsafe.Pointer(&wc)))
		if atom == 0 {
			close(readyCh)
			return
		}
		defer func() {
			if procAvailable(procUnregisterClassW) {
				_, _, _ = procUnregisterClassW.Call(uintptr(unsafe.Pointer(classPtr)), hInst)
			}
		}()

		// Ventana oculta top-level (no HWND_MESSAGE) para recibir WM_QUERYENDSESSION, WM_ENDSESSION y TaskbarCreated.
		hwnd, _, _ := procCreateWindowExW.Call(
			wsExToolWindow,
			uintptr(unsafe.Pointer(classPtr)),
			uintptr(unsafe.Pointer(titlePtr)),
			wsPopup,
			0, 0, 0, 0,
			0,
			0,
			hInst,
			0,
		)
		if hwnd == 0 {
			close(readyCh)
			return
		}

		hIcon, owned := loadTrayIconHandle(webDir)
		ctrl.hwnd = hwnd
		ctrl.hIcon = hIcon
		ctrl.iconLoadedOwned = owned

		trayWinMu.Lock()
		trayWinStates[hwnd] = ctrl
		trayWinMu.Unlock()

		activeTrayMu.Lock()
		activeTray = ctrl
		activeTrayMu.Unlock()

		ctrl.addOrUpdateIcon(false)
		close(readyCh)

		stopDone := make(chan struct{})
		go func() {
			defer close(stopDone)
			<-ctx.Done()
			ctrl.removeIconAndClose()
		}()

		var m winMsg
		for {
			r, _, _ := procGetMessageW.Call(uintptr(unsafe.Pointer(&m)), 0, 0, 0)
			if int32(r) <= 0 {
				break
			}
			if procAvailable(procTranslateMessage) {
				_, _, _ = procTranslateMessage.Call(uintptr(unsafe.Pointer(&m)))
			}
			if procAvailable(procDispatchMessageW) {
				_, _, _ = procDispatchMessageW.Call(uintptr(unsafe.Pointer(&m)))
			}
		}

		ctrl.removeIconAndClose()

		trayWinMu.Lock()
		delete(trayWinStates, hwnd)
		trayWinMu.Unlock()

		activeTrayMu.Lock()
		if activeTray == ctrl {
			activeTray = nil
		}
		activeTrayMu.Unlock()

		<-stopDone
	}()

	<-readyCh
	return func() {
		ctrl.removeIconAndClose()
	}
}
