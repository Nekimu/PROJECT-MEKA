//go:build windows

package main

import (
	"context"
	"errors"
	"fmt"
	"net"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"syscall"
	"time"
	"unsafe"

	"github.com/jchv/go-webview2"
	"github.com/jchv/go-webview2/pkg/edge"
)

var (
	user32                            = syscall.NewLazyDLL("user32.dll")
	dwmapi                            = syscall.NewLazyDLL("dwmapi.dll")
	gdi32                             = syscall.NewLazyDLL("gdi32.dll")
	kernel32                          = syscall.NewLazyDLL("kernel32.dll")
	procGetCurrentThreadId            = kernel32.NewProc("GetCurrentThreadId")
	procAttachConsole                 = kernel32.NewProc("AttachConsole")
	procGetStdHandle                  = kernel32.NewProc("GetStdHandle")
	procGetFileType                   = kernel32.NewProc("GetFileType")
	procCreateMutexW                  = kernel32.NewProc("CreateMutexW")
	procCloseHandle                   = kernel32.NewProc("CloseHandle")
	procGetModuleHandleW              = kernel32.NewProc("GetModuleHandleW")
	procSetWindowsHookExW             = user32.NewProc("SetWindowsHookExW")
	procUnhookWindowsHookEx           = user32.NewProc("UnhookWindowsHookEx")
	procCallNextHookEx                = user32.NewProc("CallNextHookEx")
	procSetWindowLongPtrW             = user32.NewProc("SetWindowLongPtrW")
	procGetWindowLongPtrW             = user32.NewProc("GetWindowLongPtrW")
	procSetClassLongPtrW              = user32.NewProc("SetClassLongPtrW")
	procSetWindowPos                  = user32.NewProc("SetWindowPos")
	procGetWindowRect                 = user32.NewProc("GetWindowRect")
	procReleaseCapture                = user32.NewProc("ReleaseCapture")
	procSendMessageW                  = user32.NewProc("SendMessageW")
	procSystemParametersInfoW         = user32.NewProc("SystemParametersInfoW")
	procFindWindowW                   = user32.NewProc("FindWindowW")
	procShowWindow                    = user32.NewProc("ShowWindow")
	procIsWindowVisible               = user32.NewProc("IsWindowVisible")
	procGetCursorPos                  = user32.NewProc("GetCursorPos")
	procScreenToClient                = user32.NewProc("ScreenToClient")
	procGetDpiForWindow               = user32.NewProc("GetDpiForWindow")
	procGetDpiForSystem               = user32.NewProc("GetDpiForSystem")
	procSetProcessDpiAwarenessContext = user32.NewProc("SetProcessDpiAwarenessContext")
	procSetForegroundWindow           = user32.NewProc("SetForegroundWindow")
	procLoadIconW                     = user32.NewProc("LoadIconW")
	procLoadImageW                    = user32.NewProc("LoadImageW")
	procMessageBoxW                   = user32.NewProc("MessageBoxW")
	procDwmExtendFrameIntoClient      = dwmapi.NewProc("DwmExtendFrameIntoClientArea")
	procDwmSetWindowAttribute         = dwmapi.NewProc("DwmSetWindowAttribute")
	procCreateSolidBrush              = gdi32.NewProc("CreateSolidBrush")
)

const (
	gwlStyle                = ^uintptr(15) // -16
	gwlExStyle              = ^uintptr(19) // -20
	gclpHbrBackground       = ^uintptr(9)  // -10
	wsPopup                 = 0x80000000
	wsVisible               = 0x10000000
	wsExTopmost             = 0x00000008
	wsExToolWindow          = 0x00000080
	wsExLayered             = 0x00080000
	wsExNoRedirectionBitmap = 0x00200000
	wsExTransparent         = 0x00000020
	wsExNoActivate          = 0x08000000
	hwndTopmost             = ^uintptr(0) // -1 (HWND_TOPMOST)
	swpNoSize               = 0x0001
	swpNoMove               = 0x0002
	swpFrameChanged         = 0x0020
	swpShowWindow           = 0x0040
	wmNCLButtonDown         = 0x00A1
	wmSetIcon               = 0x0080
	iconSmall               = 0
	iconBig                 = 1
	imageIcon               = 1
	lrLoadFromFile          = 0x0010
	lrDefaultSize           = 0x0040
	htCaption               = 2
	spiGetWorkArea          = 0x0030
	dwmwaSystemBackdropType = 38
	dwmwaBorderColor        = 34
	dwmwaCornerPreference   = 33
	dwmwaNcRenderingPolicy  = 2
	dwmwaColorNone          = 0xFFFFFFFE
	dwmwcpDoNotRound        = 1
	dwmncrpDisabled         = 1
	dwmsbtNone              = 1
	swHide                  = 0
	swShow                  = 5
	whCBT                   = 5
	hcbtCreateWnd           = 3
	stdOutputHandle         = ^uintptr(10) // -11
	mbOk                    = 0x00000000
	mbYesNo                 = 0x00000004
	mbIconError             = 0x00000010
	mbIconInfo              = 0x00000040
	idYes                   = 6
	errorAlreadyExists      = syscall.Errno(183)
)

type point struct {
	X int32
	Y int32
}

type rectF struct {
	Left   float64
	Top    float64
	Right  float64
	Bottom float64
}

var (
	currentIslandRect  atomic.Value // almacena rectF en píxeles CSS
	interactiveOverlay atomic.Bool  // true si el Drawer o menú contextual están abiertos
)

type cbtCreateWnd struct {
	lpcs            *createStruct
	hwndInsertAfter uintptr
}

type createStruct struct {
	lpCreateParams uintptr
	hInstance      uintptr
	hMenu          uintptr
	hwndParent     uintptr
	cy             int32
	cx             int32
	y              int32
	x              int32
	style          uint32
	lpszName       uintptr
	lpszClass      uintptr
	dwExStyle      uint32
}

type winRect struct {
	Left   int32
	Top    int32
	Right  int32
	Bottom int32
}

type dwmMargins struct {
	CxLeftWidth    int32
	CxRightWidth   int32
	CyTopHeight    int32
	CyBottomHeight int32
}

func getDesktopWorkArea() winRect {
	var rc winRect
	ret, _, _ := procSystemParametersInfoW.Call(
		spiGetWorkArea,
		0,
		uintptr(unsafe.Pointer(&rc)),
		0,
	)
	if ret == 0 || rc.Right <= rc.Left {
		return winRect{Left: 0, Top: 0, Right: 1920, Bottom: 1040}
	}
	return rc
}

func initDpiAwareness() {
	if procSetProcessDpiAwarenessContext.Find() == nil {
		// DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4 (^uintptr(3))
		_, _, _ = procSetProcessDpiAwarenessContext.Call(^uintptr(3))
	}
}

// getDpiScaleForWindow obtiene el factor de escalado DPI (1.0 = 96 DPI / 100%)
// para la ventana específica, o para el sistema principal si la ventana aún no existe.
func getDpiScaleForWindow(hwnd uintptr) float64 {
	if hwnd != 0 && procGetDpiForWindow.Find() == nil {
		dpi, _, _ := procGetDpiForWindow.Call(hwnd)
		if dpi > 0 {
			return float64(dpi) / 96.0
		}
	}
	if procGetDpiForSystem.Find() == nil {
		dpi, _, _ := procGetDpiForSystem.Call()
		if dpi > 0 {
			return float64(dpi) / 96.0
		}
	}
	return 1.0
}

// computeFixedWindowPosition calcula las coordenadas de la ventana física fija (400x600 CSS escalados por DPI),
// centrada horizontalmente arriba en el área de trabajo del escritorio (acotada al monitor), o desplazada si esquiva Snipping Tool.
func computeFixedWindowPosition(wa winRect, dodged bool, scale float64) (x, y, w, h int) {
	if scale <= 0 {
		scale = 1.0
	}
	screenWidth := int(wa.Right - wa.Left)
	w = int(float64(FixedWindowWidth) * scale)
	h = int(float64(FixedWindowHeight) * scale)
	if maxH := int(wa.Bottom-wa.Top) - int(24.0*scale); maxH > 0 && h > maxH {
		h = maxH
	}
	y = int(wa.Top)
	centerX := int(wa.Left) + (screenWidth-w)/2

	if dodged {
		dodgeX := int(wa.Left) + (screenWidth / 2) + int(180.0*scale)
		maxX := int(wa.Right) - w - int(16.0*scale)
		if dodgeX > maxX {
			dodgeX = maxX
		}
		x = dodgeX
	} else {
		x = centerX
	}
	return x, y, w, h
}

func computeClickThroughInterval(pt point, r rectF, scale float64, moved bool) time.Duration {
	if scale <= 0 {
		scale = 1.0
	}
	nearLeft := int32((r.Left - 48) * scale)
	nearRight := int32((r.Right + 48) * scale)
	nearTop := int32((r.Top - 24) * scale)
	nearBottom := int32((r.Bottom + 96) * scale)

	inNearZone := pt.X >= nearLeft && pt.X <= nearRight && pt.Y >= nearTop && pt.Y <= nearBottom
	if inNearZone {
		if moved {
			return 16 * time.Millisecond
		}
		return 32 * time.Millisecond
	}
	if moved {
		return 48 * time.Millisecond
	}
	return 80 * time.Millisecond
}

// startClickThroughMonitor alterna el estilo WS_EX_TRANSPARENT con frecuencia adaptativa
// (~60 Hz cerca de la isla, 20 Hz lejos en movimiento, 12.5 Hz con cursor quieto) y sale al cancelar ctx.
func startClickThroughMonitor(ctx context.Context, hwnd uintptr) {
	go func() {
		defer recoverAndLog("click-through-monitor")

		var isInteractive bool
		var lastPt point
		var hasLastPt bool
		setWindowClickThrough(hwnd, true)

		timer := time.NewTimer(16 * time.Millisecond)
		defer timer.Stop()

		for {
			select {
			case <-ctx.Done():
				return
			case <-timer.C:
			}

			nextInterval := 48 * time.Millisecond
			if interactiveOverlay.Load() {
				if !isInteractive {
					isInteractive = true
					setWindowClickThrough(hwnd, false)
				}
				nextInterval = 32 * time.Millisecond
				timer.Reset(nextInterval)
				continue
			}

			val := currentIslandRect.Load()
			if val == nil {
				timer.Reset(nextInterval)
				continue
			}
			r := val.(rectF)

			var pt point
			ret, _, _ := procGetCursorPos.Call(uintptr(unsafe.Pointer(&pt)))
			if ret == 0 {
				timer.Reset(nextInterval)
				continue
			}

			ret, _, _ = procScreenToClient.Call(hwnd, uintptr(unsafe.Pointer(&pt)))
			if ret == 0 {
				timer.Reset(nextInterval)
				continue
			}

			moved := !hasLastPt || pt.X != lastPt.X || pt.Y != lastPt.Y
			lastPt = pt
			hasLastPt = true

			scale := getDpiScaleForWindow(hwnd)

			// Margen de tolerancia de 8 px para evitar parpadeos en los límites de interacción
			physLeft := int32((r.Left - 8) * scale)
			physRight := int32((r.Right + 8) * scale)
			physTop := int32((r.Top - 6) * scale)
			physBottom := int32((r.Bottom + 8) * scale)

			inside := pt.X >= physLeft && pt.X <= physRight && pt.Y >= physTop && pt.Y <= physBottom

			if inside != isInteractive {
				isInteractive = inside
				setWindowClickThrough(hwnd, !inside)
			}

			nextInterval = computeClickThroughInterval(pt, r, scale, moved)
			timer.Reset(nextInterval)
		}
	}()
}

func setWindowClickThrough(hwnd uintptr, clickThrough bool) {
	exStyle, _, _ := procGetWindowLongPtrW.Call(hwnd, gwlExStyle)
	newStyle := exStyle
	if clickThrough {
		newStyle |= (wsExTransparent | wsExLayered)
	} else {
		newStyle &^= (wsExTransparent | wsExLayered)
	}
	if newStyle != exStyle {
		_, _, _ = procSetWindowLongPtrW.Call(hwnd, gwlExStyle, newStyle)
		_, _, _ = procSetWindowPos.Call(hwnd, 0, 0, 0, 0, 0, swpNoMove|swpNoSize|swpFrameChanged)
	}
}

// applyFramelessTransparentWindow configura la ventana de Win32 para ser:
// 1. Tamaño fijo no redimensionable (sin WS_THICKFRAME ni WS_MAXIMIZEBOX).
// 2. Flotante siempre visible sobre otras aplicaciones (WS_EX_TOPMOST).
// 3. 100% transparente sin fondo blanco ni caja sólida/tinte opaco:
//   - WS_EX_NOREDIRECTIONBITMAP (DirectComposition puro sin asignar superficie de redirección GDI).
//   - Sin WS_EX_LAYERED en el estilo base (evita fallback de DWM por conflicto con WS_EX_NOREDIRECTIONBITMAP).
//   - Sin SetWindowCompositionAttribute (en Windows 11 ACCENT_ENABLE_TRANSPARENTGRADIENT aplica tinte de acento opaco RGB 178, 200, 216).
//   - DwmExtendFrameIntoClientArea con márgenes -1 (composición nativa de cristal DWM en toda el área cliente).
//   - DWMWA_SYSTEMBACKDROP_TYPE = DWMSBT_NONE, DWMWA_NCRENDERING_POLICY = DISABLED, brocha nula/negra.
//     (Enfoque estándar idéntico al de Wails v3 y Tauri para ventanas transparentes en Windows 11).
//
// 4. Con WS_EX_NOACTIVATE para no robar foco del editor al interactuar con la mascota.
func applyFramelessTransparentWindow(hwnd uintptr) {
	// Quitar borde, barra de título y decoraciones redimensionables
	_, _, _ = procSetWindowLongPtrW.Call(hwnd, gwlStyle, uintptr(wsPopup|wsVisible))

	// Estilos extendidos: flotante, toolwindow (sin Alt+Tab), DirectComposition sin superficie de redirección GDI,
	// sin robar foco inicial. Se asegura explícitamente de NO incluir WS_EX_LAYERED en los estilos base.
	exStyle, _, _ := procGetWindowLongPtrW.Call(hwnd, gwlExStyle)
	exStyle &^= wsExLayered
	exStyle |= wsExTopmost | wsExToolWindow | wsExNoRedirectionBitmap | wsExNoActivate
	_, _, _ = procSetWindowLongPtrW.Call(hwnd, gwlExStyle, exStyle)

	// Brocha de fondo negra/nula para que GDI/DWM interprete el área no pintada como 100% transparente
	blackBrush, _, _ := procCreateSolidBrush.Call(0)
	_, _, _ = procSetClassLongPtrW.Call(hwnd, gclpHbrBackground, blackBrush)

	// En Windows 11 (build >= 22000), desactivar explícitamente cualquier fondo/mica del sistema
	var backdropType uint32 = dwmsbtNone
	_, _, _ = procDwmSetWindowAttribute.Call(hwnd, dwmwaSystemBackdropType, uintptr(unsafe.Pointer(&backdropType)), 4)

	// Desactivar política de renderizado non-client de DWM (apaga bordes y sombras rectangulares del sistema)
	var ncPolicy uint32 = dwmncrpDisabled
	_, _, _ = procDwmSetWindowAttribute.Call(hwnd, dwmwaNcRenderingPolicy, uintptr(unsafe.Pointer(&ncPolicy)), 4)

	// Desactivar el borde de ventana perimetral que DWM 11 dibuja por defecto
	var borderColor uint32 = dwmwaColorNone
	_, _, _ = procDwmSetWindowAttribute.Call(hwnd, dwmwaBorderColor, uintptr(unsafe.Pointer(&borderColor)), 4)

	// Desactivar redondeo forzado del sistema DWM (las esquinas squircle las renderiza el CSS)
	var cornerPref uint32 = dwmwcpDoNotRound
	_, _, _ = procDwmSetWindowAttribute.Call(hwnd, dwmwaCornerPreference, uintptr(unsafe.Pointer(&cornerPref)), 4)

	// Extender composición DWM transparente a toda el área cliente
	margins := dwmMargins{-1, -1, -1, -1}
	_, _, _ = procDwmExtendFrameIntoClient.Call(hwnd, uintptr(unsafe.Pointer(&margins)))

	// Posicionar centrado en la parte superior del monitor con tamaño fijo (400x600 escalado por DPI)
	scale := getDpiScaleForWindow(hwnd)
	x, y, w, h := computeFixedWindowPosition(getDesktopWorkArea(), false, scale)

	_, _, _ = procSetWindowPos.Call(
		hwnd,
		hwndTopmost,
		uintptr(x),
		uintptr(y),
		uintptr(w),
		uintptr(h),
		swpFrameChanged|swpShowWindow,
	)
}

var (
	isExpandedState bool
	isDodgedState   bool
	manualDodge     bool
)

// computeWindowPositionForWorkArea calcula las coordenadas X, Y, W, H según si el notch está expandido
// y si debe esquivar la barra de recortes de Windows Snipping Tool.
func computeWindowPositionForWorkArea(wa winRect, expanded bool, dodged bool) (x, y, w, h int) {
	screenWidth := int(wa.Right - wa.Left)
	w = NotchWidth
	h = NotchHeight
	if expanded {
		w = ExpandedWidth
		h = ExpandedHeight
	}

	y = int(wa.Top)
	centerX := int(wa.Left) + (screenWidth-w)/2

	if dodged {
		// Esquivar hacia la derecha para despejar la barra de Snipping Tool
		// (barra de Windows centrada en screenWidth/2 de ancho ~270px).
		dodgeX := int(wa.Left) + (screenWidth / 2) + 180
		maxX := int(wa.Right) - w - 16
		if dodgeX > maxX {
			dodgeX = maxX
		}
		x = dodgeX
	} else {
		x = centerX
	}
	return x, y, w, h
}

func computeWindowPosition(expanded bool, dodged bool) (x, y, w, h int) {
	wa := getDesktopWorkArea()
	return computeWindowPositionForWorkArea(wa, expanded, dodged)
}

// isSnippingToolActive detecta si la herramienta de recortes de Windows (Snipping Tool / Screen Clipping)
// está activa y visible en pantalla, para esquivarla automáticamente y no estorbar en su barra de opciones.
// Se basa en comprobaciones O(1) de clases y títulos de ventana de User32, evitando la sobrecarga
// de CreateToolhelp32Snapshot en el ticker periódico.
func isSnippingToolActive() bool {
	classes := []string{
		"Microsoft-Windows-SnipperToolbar",
		"SnippingToolWindowClass",
	}
	for _, cls := range classes {
		cPtr := syscall.StringToUTF16Ptr(cls)
		ret, _, _ := procFindWindowW.Call(uintptr(unsafe.Pointer(cPtr)), 0)
		if ret != 0 {
			vis, _, _ := procIsWindowVisible.Call(ret)
			if vis != 0 {
				return true
			}
		}
	}

	titles := []string{
		"Screen Clipping",
		"Herramienta Recortes",
		"Snipping Tool",
	}
	for _, title := range titles {
		tPtr := syscall.StringToUTF16Ptr(title)
		ret, _, _ := procFindWindowW.Call(0, uintptr(unsafe.Pointer(tPtr)))
		if ret != 0 {
			vis, _, _ := procIsWindowVisible.Call(ret)
			if vis != 0 {
				return true
			}
		}
	}

	return false
}

// startSnippingToolMonitor vigila si Snipping Tool se activa para esquivar automáticamente
// la barra superior de Windows sin tapar las opciones ni impedir recortes limpios.
func startSnippingToolMonitor(ctx context.Context, w webview2.WebView, hwnd uintptr) {
	go func() {
		defer recoverAndLog("snipping-monitor")

		ticker := time.NewTicker(400 * time.Millisecond)
		defer ticker.Stop()

		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
			}

			active := isSnippingToolActive()
			wasActive := snippingToolActive.Swap(active)
			if wasActive && !active {
				markSnippingToolClosed()
			}
			shouldDodge := active || manualDodge
			if shouldDodge != isDodgedState {
				isDodgedState = shouldDodge
				w.Dispatch(func() {
					if ctx.Err() != nil {
						return
					}
					scale := getDpiScaleForWindow(hwnd)
					x, y, targetW, targetH := computeFixedWindowPosition(getDesktopWorkArea(), isDodgedState, scale)
					_, _, _ = procSetWindowPos.Call(
						hwnd,
						hwndTopmost,
						uintptr(x),
						uintptr(y),
						uintptr(targetW),
						uintptr(targetH),
						swpFrameChanged|swpShowWindow,
					)
					_, _, _ = procSendMessageW.Call(hwnd, 0x0005, 0, 0) // WM_SIZE
				})
			}
		}
	}()
}

// configureTransparentWebView accede al controlador COM nativo de WebView2 para:
//  1. Asignar el color de fondo por defecto a 100% transparente (Alpha=0, R=0, G=0, B=0),
//     eliminando cualquier fondo blanco o sólido que WebView2 renderiza por defecto.
//  2. Desactivar controles de zoom para que el usuario no pueda alterar la escala visual ni el pixel art.
func configureTransparentWebView(w webview2.WebView) error {
	val := reflect.ValueOf(w)
	if val.Kind() != reflect.Ptr || val.IsNil() {
		return errors.New("puntero webview inválido")
	}
	elem := val.Elem()
	browserField := elem.FieldByName("browser")
	if !browserField.IsValid() {
		return errors.New("campo browser no encontrado")
	}

	fieldAddr := browserField.UnsafeAddr()
	dataPtr := *(*unsafe.Pointer)(unsafe.Pointer(fieldAddr + unsafe.Sizeof(uintptr(0))))
	if dataPtr == nil {
		return errors.New("puntero chromium nulo")
	}

	chromium := (*edge.Chromium)(dataPtr)
	ctrl := chromium.GetController()
	if ctrl == nil {
		return errors.New("controlador webview2 nulo")
	}

	ctrl2 := ctrl.GetICoreWebView2Controller2()
	if ctrl2 == nil {
		return errors.New("ICoreWebView2Controller2 no disponible")
	}

	if err := ctrl2.PutDefaultBackgroundColor(edge.COREWEBVIEW2_COLOR{A: 0, R: 0, G: 0, B: 0}); err != nil {
		return fmt.Errorf("error al asignar fondo transparente: %w", err)
	}

	// Desactivar controles de zoom
	if settings, err := chromium.GetSettings(); err == nil && settings != nil {
		_ = settings.PutIsZoomControlEnabled(false)
	}

	return nil
}

var (
	initialTargetX int
	initialTargetY int
	initialTargetW int
	initialTargetH int
)

// installPreCreationHook intercepta la creación nativa de la ventana en WebView2 mediante un hook CBT.
// Esto garantiza que CreateWindowExW reciba las coordenadas centradas superiores exactas y el estilo WS_POPUP
// antes de que Windows pinte el primer píxel, erradicando por completo cualquier salto visual o descentrado al arrancar.
func installPreCreationHook(x, y, w, h int) uintptr {
	initialTargetX = x
	initialTargetY = y
	initialTargetW = w
	initialTargetH = h

	threadID, _, _ := procGetCurrentThreadId.Call()
	cb := syscall.NewCallback(func(nCode int32, wParam uintptr, lParam uintptr) uintptr {
		if nCode == hcbtCreateWnd {
			cbt := (*cbtCreateWnd)(unsafe.Pointer(lParam))
			if cbt != nil && cbt.lpcs != nil && cbt.lpcs.hwndParent == 0 {
				cbt.lpcs.x = int32(initialTargetX)
				cbt.lpcs.y = int32(initialTargetY)
				cbt.lpcs.cx = int32(initialTargetW)
				cbt.lpcs.cy = int32(initialTargetH)
				cbt.lpcs.style = uint32(wsPopup | wsVisible)
				cbt.lpcs.dwExStyle |= uint32(wsExTopmost | wsExToolWindow | wsExNoRedirectionBitmap)
			}
		}
		ret, _, _ := procCallNextHookEx.Call(0, uintptr(nCode), wParam, lParam)
		return ret
	})

	hook, _, _ := procSetWindowsHookExW.Call(
		uintptr(whCBT),
		cb,
		0,
		threadID,
	)
	return hook
}

func isLocalCoreURL(coreWSURL string) (string, bool) {
	raw := strings.TrimSpace(coreWSURL)
	if raw == "" {
		return "127.0.0.1:8765", true
	}
	u, err := url.Parse(raw)
	if err != nil || u.Host == "" {
		return "", false
	}
	hostname := strings.ToLower(u.Hostname())
	if hostname != "127.0.0.1" && hostname != "localhost" {
		return "", false
	}
	if u.Port() == "" {
		return net.JoinHostPort(hostname, "8765"), true
	}
	return u.Host, true
}

func isCoreListening(hostPort string) bool {
	if hostPort == "" {
		return false
	}
	conn, err := net.DialTimeout("tcp", hostPort, 350*time.Millisecond)
	if err != nil {
		return false
	}
	_ = conn.Close()
	return true
}

// attachConsoleIfNeeded adjunta la consola del proceso padre cuando la app compilada con
// `-H=windowsgui` se invoca desde terminal con banderas CLI (--self-test, --install, etc.).
func attachConsoleIfNeeded(cfg Config) {
	if !cfg.SelfTest && !cfg.Install && !cfg.Uninstall && !cfg.EnableStartup && !cfg.DisableStartup && cfg.ServeOnly == "" {
		return
	}
	hOut, _, _ := procGetStdHandle.Call(stdOutputHandle)
	if hOut != 0 && hOut != ^uintptr(0) {
		if ft, _, _ := procGetFileType.Call(hOut); ft != 0 {
			return // stdout ya está redirigido (pipe o archivo)
		}
	}
	ret, _, _ := procAttachConsole.Call(^uintptr(0)) // ATTACH_PARENT_PROCESS
	if ret == 0 {
		return
	}
	if f, err := os.OpenFile("CONOUT$", os.O_WRONLY, 0); err == nil {
		os.Stdout = f
		os.Stderr = f
	}
}

// acquireSingleInstanceMutex evita abrir múltiples instancias de MEKA Dynamic Island a la vez.
func acquireSingleInstanceMutex() (uintptr, bool) {
	namePtr, err := syscall.UTF16PtrFromString("Local\\MekaDesktopCompanionMutex")
	if err != nil {
		return 0, true
	}
	handle, _, lastErr := procCreateMutexW.Call(0, 0, uintptr(unsafe.Pointer(namePtr)))
	if handle == 0 {
		return 0, true
	}
	if lastErr == errorAlreadyExists {
		_, _, _ = procCloseHandle.Call(handle)
		if titlePtr, tErr := syscall.UTF16PtrFromString("MEKA Dynamic Island"); tErr == nil {
			if existing, _, _ := procFindWindowW.Call(0, uintptr(unsafe.Pointer(titlePtr))); existing != 0 {
				_, _, _ = procShowWindow.Call(existing, swShow)
			}
		}
		return 0, false
	}
	return handle, true
}

// resolveAppIconPath busca `icon.ico` junto al binario o dentro de `pet/desktop/icons/`.
func resolveAppIconPath(webDir string) string {
	var candidates []string
	if exe, err := os.Executable(); err == nil {
		exeDir := filepath.Dir(exe)
		candidates = append(candidates,
			filepath.Join(exeDir, "icon.ico"),
			filepath.Join(exeDir, "icons", "icon.ico"),
		)
	}
	if root := resolveProjectRoot(webDir); root != "" {
		candidates = append(candidates, filepath.Join(root, "pet", "desktop", "icons", "icon.ico"))
	}
	if webDir != "" {
		candidates = append(candidates, filepath.Join(webDir, "..", "desktop", "icons", "icon.ico"))
	}
	for _, p := range candidates {
		if abs, err := filepath.Abs(p); err == nil && fileExists(abs) {
			return abs
		}
	}
	return ""
}

// applyWindowIcon asigna el icono oficial de MEKA a la ventana nativa (pequeño y grande).
func applyWindowIcon(hwnd uintptr, webDir string) {
	if hwnd == 0 {
		return
	}
	var hIcon uintptr
	if hMod, _, _ := procGetModuleHandleW.Call(0); hMod != 0 {
		hIcon, _, _ = procLoadIconW.Call(hMod, uintptr(1))
	}
	if iconPath := resolveAppIconPath(webDir); iconPath != "" {
		if ptr, err := syscall.UTF16PtrFromString(iconPath); err == nil {
			if loaded, _, _ := procLoadImageW.Call(
				0,
				uintptr(unsafe.Pointer(ptr)),
				imageIcon,
				0,
				0,
				lrLoadFromFile|lrDefaultSize,
			); loaded != 0 {
				hIcon = loaded
			}
		}
	}
	if hIcon != 0 {
		_, _, _ = procSendMessageW.Call(hwnd, wmSetIcon, iconSmall, hIcon)
		_, _, _ = procSendMessageW.Call(hwnd, wmSetIcon, iconBig, hIcon)
	}
}

func showMessageBox(title, body string, flags uint32) uintptr {
	tPtr, err1 := syscall.UTF16PtrFromString(title)
	bPtr, err2 := syscall.UTF16PtrFromString(body)
	if err1 != nil || err2 != nil {
		return 0
	}
	ret, _, _ := procMessageBoxW.Call(
		0,
		uintptr(unsafe.Pointer(bPtr)),
		uintptr(unsafe.Pointer(tPtr)),
		uintptr(flags),
	)
	return ret
}

func resolveAppIconPathIfAny(webDir string) string {
	return resolveAppIconPath(webDir)
}

func showStartupErrorDialog(title, body string) {
	_ = showMessageBox(title, body, mbOk|mbIconError)
}

func computeWebViewCacheStamp(webDir string) string {
	var parts []string
	if exe, err := os.Executable(); err == nil {
		if info, sErr := os.Stat(exe); sErr == nil {
			parts = append(parts, fmt.Sprintf("exe:%d:%d", info.Size(), info.ModTime().UnixNano()))
		}
	}
	for _, rel := range []string{"index.html", "pet.css", "pet.js", filepath.Join("skins", "manifest.js")} {
		p := filepath.Join(webDir, rel)
		if info, err := os.Stat(p); err == nil {
			parts = append(parts, fmt.Sprintf("%s:%d:%d", rel, info.Size(), info.ModTime().UnixNano()))
		}
	}
	return strings.Join(parts, "|")
}

func syncWebViewCache(dataPath, webDir string) {
	if dataPath == "" || webDir == "" {
		return
	}
	stampPath := filepath.Join(filepath.Dir(dataPath), "webview-cache-stamp.txt")
	currentStamp := computeWebViewCacheStamp(webDir)
	if currentStamp == "" {
		return
	}
	prevBytes, err := os.ReadFile(stampPath)
	if err == nil && strings.TrimSpace(string(prevBytes)) == currentStamp {
		return
	}
	// Solo purga Caché/Code Cache cuando cambia el binario o algún asset web principal
	_ = os.RemoveAll(filepath.Join(dataPath, "EBWebView", "Default", "Cache"))
	_ = os.RemoveAll(filepath.Join(dataPath, "EBWebView", "Default", "Code Cache"))
	_ = os.WriteFile(stampPath, []byte(currentStamp+"\n"), 0644)
}

func recenterIslandWindow(hwnd uintptr, showWin bool) {
	manualDodge = false
	isDodgedState = isSnippingToolActive()
	scale := getDpiScaleForWindow(hwnd)
	x, y, targetW, targetH := computeFixedWindowPosition(getDesktopWorkArea(), isDodgedState, scale)
	flags := uintptr(swpFrameChanged)
	if showWin {
		flags |= swpShowWindow
		_, _, _ = procShowWindow.Call(hwnd, swShow)
	}
	_, _, _ = procSetWindowPos.Call(
		hwnd,
		hwndTopmost,
		uintptr(x),
		uintptr(y),
		uintptr(targetW),
		uintptr(targetH),
		flags,
	)
	_, _, _ = procSendMessageW.Call(hwnd, 0x0005, 0, 0)
}

// ensureCoreBackendRunning inicia MEKA Core (`venv\Scripts\python.exe run.py core` o `all`)
// unificado en segundo plano bajo un Job Object (KILL_ON_JOB_CLOSE), con verificador /v1/health
// y circuit breaker anti-bucle para evitar procesos huérfanos o cuelgues en reinicios.
func ensureCoreBackendRunning(ctx context.Context, projectRoot string, coreWSURL string, coreMode string) (stopFn func(), restartFn func(), closeJobFn func()) {
	noop := func() {}
	hostPort, isLocal := isLocalCoreURL(coreWSURL)
	if !isLocal || projectRoot == "" {
		return noop, noop, noop
	}

	pythonExe := filepath.Join(projectRoot, "venv", "Scripts", "python.exe")
	runPy := filepath.Join(projectRoot, "run.py")
	if !fileExists(runPy) {
		return noop, noop, noop
	}
	if !fileExists(pythonExe) {
		var err error
		pythonExe, err = exec.LookPath("python")
		if err != nil {
			return noop, noop, noop
		}
	}

	coreArgs := []string{"run.py", "core"}
	if strings.EqualFold(strings.TrimSpace(coreMode), "all") {
		coreArgs = []string{"run.py"}
	}

	job, jobErr := createKillOnCloseJob()
	if jobErr != nil {
		logDesktopEvent("WARN", "core-job", fmt.Sprintf("No se pudo crear Job Object: %v", jobErr))
	}

	var mu sync.Mutex
	var childCmd *exec.Cmd
	var lastSpawnAt time.Time
	var nextAllowedAt time.Time
	var stopWatchdog atomic.Bool
	tracker := &coreRestartTracker{}
	restartCh := make(chan struct{}, 1)

	localApp := os.Getenv("LOCALAPPDATA")
	if localApp == "" {
		localApp = os.TempDir()
	}
	logDir := filepath.Join(localApp, "MEKA")
	_ = os.MkdirAll(logDir, 0755)
	logPath := filepath.Join(logDir, "core-desktop.log")

	spawnIfNeeded := func(forceRespawn bool) bool {
		mu.Lock()
		defer mu.Unlock()
		if stopWatchdog.Load() || ctx.Err() != nil {
			return false
		}
		if !forceRespawn && (childCmd != nil || isCoreHealthy(hostPort) || isCoreListening(hostPort)) {
			return false
		}
		if !forceRespawn && !nextAllowedAt.IsZero() && time.Now().Before(nextAllowedAt) {
			return false
		}

		delay, tripped := tracker.recordAttempt(time.Now())
		if tripped {
			nextAllowedAt = time.Now().Add(delay)
			logDesktopEvent("WARN", "core-watchdog", fmt.Sprintf("Circuit breaker activo para MEKA Core; esperando %s antes del siguiente reintento", delay))
			showTrayBalloon("MEKA Core · Recuperación", fmt.Sprintf("Varios reinicios recientes detectados; reintento automático en %s.", delay))
			return false
		}

		rotateLogIfNeeded(logPath, 2*maxDesktopLogBytes)
		cmd := exec.Command(pythonExe, coreArgs...)
		cmd.Dir = projectRoot
		cmd.Env = append(os.Environ(), "PYTHONIOENCODING=utf-8")
		cmd.SysProcAttr = &syscall.SysProcAttr{
			HideWindow:    true,
			CreationFlags: 0x08000000, // CREATE_NO_WINDOW
		}
		var logFile *os.File
		if f, err := os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644); err == nil {
			logFile = f
			cmd.Stdout = f
			cmd.Stderr = f
		}
		if err := cmd.Start(); err != nil {
			if logFile != nil {
				_ = logFile.Close()
			}
			logDesktopEvent("ERROR", "core", fmt.Sprintf("Error iniciando Python Core: %v", err))
			return false
		}
		if job != nil && cmd.Process != nil {
			if err := job.assignPID(cmd.Process.Pid); err != nil {
				logDesktopEvent("WARN", "core-job", fmt.Sprintf("No se pudo asignar PID %d al Job Object: %v", cmd.Process.Pid, err))
			}
		}

		childCmd = cmd
		lastSpawnAt = time.Now()
		logDesktopEvent("INFO", "core", fmt.Sprintf("MEKA Core iniciado (pid=%d, args=%v)", cmd.Process.Pid, coreArgs))

		go func(c *exec.Cmd, f *os.File) {
			defer recoverAndLog("core-wait")
			_ = c.Wait()
			if f != nil {
				_ = f.Close()
			}
			mu.Lock()
			if childCmd == c {
				childCmd = nil
			}
			mu.Unlock()
		}(cmd, logFile)
		return true
	}

	if spawnIfNeeded(false) {
		deadline := time.Now().Add(2500 * time.Millisecond)
		for time.Now().Before(deadline) && ctx.Err() == nil {
			if isCoreHealthy(hostPort) {
				break
			}
			time.Sleep(120 * time.Millisecond)
		}
	}

	go func() {
		defer recoverAndLog("core-watchdog")
		ticker := time.NewTicker(4 * time.Second)
		defer ticker.Stop()

		unhealthyStreak := 0
		for {
			select {
			case <-ctx.Done():
				return
			case <-restartCh:
				unhealthyStreak = 0
				mu.Lock()
				cmd := childCmd
				childCmd = nil
				tracker.reset()
				nextAllowedAt = time.Time{}
				mu.Unlock()
				if cmd != nil && cmd.Process != nil {
					logDesktopEvent("INFO", "core-watchdog", fmt.Sprintf("Reinicio manual de MEKA Core solicitado (pid=%d)", cmd.Process.Pid))
					killProcessTreeByPID(cmd.Process.Pid)
					_ = cmd.Process.Kill()
				}
				time.Sleep(350 * time.Millisecond)
				_ = spawnIfNeeded(true)
			case <-ticker.C:
				if stopWatchdog.Load() {
					return
				}
				mu.Lock()
				cmd := childCmd
				spawnAge := time.Since(lastSpawnAt)
				mu.Unlock()

				if cmd == nil {
					unhealthyStreak = 0
					spawnIfNeeded(false)
					continue
				}

				// Dar margen de arranque inicial de 22s antes de exigir /v1/health
				if spawnAge > 22*time.Second {
					if isCoreHealthy(hostPort) {
						unhealthyStreak = 0
						if spawnAge > 65*time.Second {
							tracker.reset()
						}
					} else {
						unhealthyStreak++
						if unhealthyStreak >= 3 {
							pid := 0
							if cmd.Process != nil {
								pid = cmd.Process.Pid
							}
							logDesktopEvent("WARN", "core-watchdog", fmt.Sprintf("MEKA Core pid=%d no responde /v1/health tras %d chequeos; reiniciando", pid, unhealthyStreak))
							unhealthyStreak = 0
							mu.Lock()
							if childCmd == cmd {
								childCmd = nil
							}
							mu.Unlock()
							if pid > 0 {
								killProcessTreeByPID(pid)
								_ = cmd.Process.Kill()
							}
							_ = spawnIfNeeded(false)
						}
					}
				}
			}
		}
	}()

	stopFn = func() {
		stopWatchdog.Store(true)
		mu.Lock()
		cmd := childCmd
		childCmd = nil
		mu.Unlock()
		if cmd != nil && cmd.Process != nil {
			logDesktopEvent("INFO", "core", fmt.Sprintf("Deteniendo MEKA Core (pid=%d)", cmd.Process.Pid))
			killProcessTreeByPID(cmd.Process.Pid)
			_ = cmd.Process.Kill()
		}
		if job != nil {
			job.close()
		}
	}

	restartFn = func() {
		select {
		case restartCh <- struct{}{}:
		default:
		}
	}

	closeJobFn = func() {
		if job != nil {
			job.close()
		}
	}

	return stopFn, restartFn, closeJobFn
}

func runNativeWindow(cfg Config, targetURL string) error {
	return runNativeWindowWithShutdown(cfg, targetURL, nil)
}

func runNativeWindowWithShutdown(cfg Config, targetURL string, stopHTTP func()) error {
	applyProcessAppUserModelID()
	_ = registerBackgroundNotificationApp("", resolveAppIconPath(cfg.WebDir))
	logDesktopEvent("INFO", "startup", fmt.Sprintf("Iniciando MEKA Desktop (startup=%v, coreMode=%s)", cfg.Startup, cfg.CoreMode))

	if cfg.Startup {
		// Breve pausa de estabilización cuando Windows arranca al iniciar sesión
		time.Sleep(800 * time.Millisecond)
	}

	mtx, ok := acquireSingleInstanceMutex()
	if !ok {
		logDesktopEvent("INFO", "startup", "Ya existía una instancia activa de MEKA; enfocando ventana previa")
		return nil
	}
	closeMutex := func() {
		if mtx != 0 {
			h := mtx
			mtx = 0
			_, _, _ = procCloseHandle.Call(h)
		}
	}
	defer closeMutex()

	initDpiAwareness()
	_ = os.Setenv("WEBVIEW2_DEFAULT_BACKGROUND_COLOR", "0")

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	stopCore, restartCore, closeJob := ensureCoreBackendRunning(ctx, resolveProjectRoot(cfg.WebDir), cfg.CoreURL, cfg.CoreMode)

	localApp := os.Getenv("LOCALAPPDATA")
	if localApp == "" {
		localApp = os.TempDir()
	}
	dataPath := filepath.Join(localApp, "MEKA", "webview2")
	_ = os.MkdirAll(dataPath, 0755)
	syncWebViewCache(dataPath, cfg.WebDir)

	initScale := getDpiScaleForWindow(0)
	initX, initY, initW, initH := computeFixedWindowPosition(getDesktopWorkArea(), false, initScale)
	hook := installPreCreationHook(initX, initY, initW, initH)

	w := webview2.NewWithOptions(webview2.WebViewOptions{
		DataPath:  dataPath,
		Debug:     cfg.Debug,
		AutoFocus: true,
		WindowOptions: webview2.WindowOptions{
			Title:  "MEKA Dynamic Island",
			Width:  uint(initW),
			Height: uint(initH),
			Center: false,
			IconId: 1,
		},
	})
	if hook != 0 {
		_, _, _ = procUnhookWindowsHookEx.Call(hook)
	}
	if w == nil {
		stopCore()
		closeJob()
		if stopHTTP != nil {
			stopHTTP()
		}
		return errors.New("no se pudo inicializar Microsoft Edge WebView2 Runtime")
	}
	defer w.Destroy()

	hwnd := uintptr(w.Window())
	applyFramelessTransparentWindow(hwnd)
	applyWindowIcon(hwnd, cfg.WebDir)

	// Iniciar monitor adaptativo de click-through para alternar WS_EX_TRANSPARENT según el cursor
	startClickThroughMonitor(ctx, hwnd)

	// Iniciar en modo notch y notificar tamaño al compositor
	_, _, _ = procSendMessageW.Call(hwnd, 0x0005, 0, 0) // WM_SIZE

	// Eliminar fondo blanco de WebView2 y desactivar zoom
	if err := configureTransparentWebView(w); err != nil {
		logDesktopEvent("WARN", "webview2", fmt.Sprintf("Aviso de transparencia: %v", err))
		if cfg.Debug {
			fmt.Printf("Aviso de transparencia: %v\n", err)
		}
	}

	// Iniciar monitor de auto-evasión para Snipping Tool
	startSnippingToolMonitor(ctx, w, hwnd)

	// Iniciar monitor nativo de los 8 eventos de Windows
	startWindowsEventMonitor(ctx, w, hwnd)

	var uiReady atomic.Bool
	bootAt := time.Now()

	var shutdown *shutdownCoordinator
	var stopTray func()
	stopTray = startTrayController(ctx, cfg.WebDir, trayActions{
		OnShowCenter: func() {
			w.Dispatch(func() {
				recenterIslandWindow(hwnd, true)
			})
		},
		OnToggleExpand: func() {
			w.Dispatch(func() {
				recenterIslandWindow(hwnd, true)
				w.Eval("window.MEKA?.toggleNotch?.()")
			})
		},
		OnToggleAuto: func() {
			next := !isAutoStartEnabled()
			if err := setAutoStartEnabled("", next); err != nil {
				logDesktopEvent("ERROR", "autostart", err.Error())
				showTrayBalloon("MEKA · Arranque", "No se pudo cambiar el inicio automático con Windows.")
				return
			}
			w.Dispatch(func() {
				w.Eval("window.MEKA?.syncAutoStartUI?.(" + strconv.FormatBool(next) + ")")
			})
			if next {
				showTrayBalloon("MEKA · Arranque automático", "MEKA se iniciará automáticamente al encender Windows.")
			} else {
				showTrayBalloon("MEKA · Arranque automático", "Inicio automático con Windows desactivado.")
			}
		},
		OnRestartCore: func() {
			restartCore()
			showTrayBalloon("MEKA Core", "Reiniciando servicio de MEKA Core en segundo plano...")
		},
		OnOpenLogs: openMekaLogsDirectory,
		OnExit: func(reason string) {
			if shutdown != nil {
				shutdown.trigger(reason)
			}
		},
	})

	shutdown = newShutdownCoordinator(shutdownCoordinator{
		cancel:     cancel,
		stopTray:   stopTray,
		stopHTTP:   stopHTTP,
		stopCore:   stopCore,
		closeJob:   closeJob,
		closeMutex: closeMutex,
		terminateUI: func() {
			w.Dispatch(func() {
				w.Terminate()
			})
		},
	})
	defer func() {
		shutdown.trigger("run-exit")
		shutdown.markFinished()
	}()

	startUIReadinessWatchdog(ctx, w, targetURL, &uiReady, nil)

	// Confirmación de carga de UI para verificador de arranque
	_ = w.Bind("mekaNotifyReady", func() {
		if uiReady.CompareAndSwap(false, true) {
			logDesktopEvent("INFO", "startup", fmt.Sprintf("Interfaz lista en %s", time.Since(bootAt).Round(time.Millisecond)))
		}
	})

	_ = w.Bind("mekaGetAutoStart", func() bool {
		return isAutoStartEnabled()
	})

	_ = w.Bind("mekaSetAutoStart", func(enabled bool) bool {
		if err := setAutoStartEnabled("", enabled); err != nil {
			logDesktopEvent("ERROR", "autostart", err.Error())
		}
		return isAutoStartEnabled()
	})

	// Informar al backend en Go de las coordenadas actuales de la isla (en píxeles CSS)
	_ = w.Bind("mekaIslandRect", func(left, top, right, bottom float64) {
		uiReady.Store(true)
		currentIslandRect.Store(rectF{Left: left, Top: top, Right: right, Bottom: bottom})
	})

	// Informar si el Drawer lateral o un menú contextual está desplegado (para deshabilitar click-through)
	_ = w.Bind("mekaSetInteractiveOverlay", func(open bool) {
		interactiveOverlay.Store(open)
	})

	// Gestión de foco de teclado (WS_EX_NOACTIVATE): activa la ventana solo cuando el chat tiene foco
	_ = w.Bind("mekaWantsKeyboard", func(wants bool) {
		w.Dispatch(func() {
			exStyle, _, _ := procGetWindowLongPtrW.Call(hwnd, gwlExStyle)
			if wants {
				exStyle &^= wsExNoActivate
				_, _, _ = procSetWindowLongPtrW.Call(hwnd, gwlExStyle, exStyle)
				_, _, _ = procSetForegroundWindow.Call(hwnd)
			} else {
				exStyle |= wsExNoActivate
				_, _, _ = procSetWindowLongPtrW.Call(hwnd, gwlExStyle, exStyle)
			}
			_, _, _ = procSetWindowPos.Call(hwnd, 0, 0, 0, 0, 0, swpNoMove|swpNoSize|swpFrameChanged)
		})
	})

	// Modo desplegado: con la ventana fija (400x600), la isla se expande internamente con un resorte JS
	// sin redimensionar la ventana nativa, erradicando saltos, parpadeos y cortes rectangulares.
	_ = w.Bind("mekaSetNotchExpanded", func(expanded bool) {
		isExpandedState = expanded
	})

	// Centrar notch en la parte superior central de la pantalla
	_ = w.Bind("mekaCenterNotch", func() {
		w.Dispatch(func() {
			recenterIslandWindow(hwnd, true)
		})
	})

	// Conmutar evasión manual hacia la derecha / volver al centro
	_ = w.Bind("mekaToggleDodge", func() {
		w.Dispatch(func() {
			manualDodge = !isDodgedState
			isDodgedState = manualDodge
			scale := getDpiScaleForWindow(hwnd)
			x, y, targetW, targetH := computeFixedWindowPosition(getDesktopWorkArea(), isDodgedState, scale)
			_, _, _ = procSetWindowPos.Call(
				hwnd,
				hwndTopmost,
				uintptr(x),
				uintptr(y),
				uintptr(targetW),
				uintptr(targetH),
				swpFrameChanged|swpShowWindow,
			)
			_, _, _ = procSendMessageW.Call(hwnd, 0x0005, 0, 0)
		})
	})

	// Mostrar u ocultar la ventana nativa (modo captura limpia de pantalla)
	_ = w.Bind("mekaSetWindowVisible", func(visible bool) {
		w.Dispatch(func() {
			cmd := uintptr(swShow)
			if !visible {
				cmd = uintptr(swHide)
			}
			_, _, _ = procShowWindow.Call(hwnd, cmd)
		})
	})

	// Arrastrar ventana flotante y reafirmar HWND_TOPMOST al soltar
	_ = w.Bind("mekaStartDrag", func() {
		w.Dispatch(func() {
			_, _, _ = procReleaseCapture.Call()
			_, _, _ = procSendMessageW.Call(hwnd, wmNCLButtonDown, htCaption, 0)
			_, _, _ = procSetWindowPos.Call(
				hwnd,
				hwndTopmost,
				0, 0, 0, 0,
				swpNoMove|swpNoSize|swpShowWindow,
			)
		})
	})

	// El cajón lateral ahora se despliega dentro de la ventana fija sin alterar sus dimensiones
	_ = w.Bind("mekaSetDrawerExpanded", func(expanded bool) {})

	// Cerrar la aplicación (con coordinador idempotente anti-cuelgue)
	_ = w.Bind("mekaCloseWindow", func() {
		go shutdown.trigger("js-close")
	})

	w.Init(`window.MEKA_NATIVE = true; document.documentElement.classList.add("desktop");`)
	w.Navigate(targetURL)
	w.Run()
	return nil
}
