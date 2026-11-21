package main

import (
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestResolveWebDir(t *testing.T) {
	dir, err := resolveWebDir("")
	if err != nil {
		t.Fatalf("resolveWebDir falló: %v", err)
	}
	if err := runSelfTest(dir); err != nil {
		t.Fatalf("runSelfTest falló en %s: %v", dir, err)
	}
}

func TestWebHandlerServesPixelArtAndManifest(t *testing.T) {
	dir, err := resolveWebDir("")
	if err != nil {
		t.Fatalf("resolveWebDir falló: %v", err)
	}

	ts := httptest.NewServer(newWebHandler(dir))
	defer ts.Close()

	cases := []struct {
		path        string
		contentType string
	}{
		{"/healthz", "application/json"},
		{"/index.html", "text/html"},
		{"/skins/manifest.js", "application/javascript"},
		{"/skins/hana/idle.webp", "image/webp"},
		{"/skins/2b/idle.webp", "image/webp"},
	}

	for _, tc := range cases {
		resp, err := http.Get(ts.URL + tc.path)
		if err != nil {
			t.Fatalf("GET %s falló: %v", tc.path, err)
		}
		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Fatalf("GET %s devolvió %d (esperado 200)", tc.path, resp.StatusCode)
		}
		if len(body) == 0 {
			t.Fatalf("GET %s devolvió cuerpo vacío", tc.path)
		}
		ct := resp.Header.Get("Content-Type")
		if !strings.Contains(ct, tc.contentType) {
			t.Errorf("GET %s Content-Type = %q; se esperaba que contuviera %q", tc.path, ct, tc.contentType)
		}
	}
}

func TestBuildCompanionURL(t *testing.T) {
	cfg := Config{
		CoreURL: "ws://127.0.0.1:8765/v1/events",
		Skin:    "hana",
	}
	got := buildCompanionURL("127.0.0.1:54321", cfg)
	if !strings.Contains(got, "desktop=1") || !strings.Contains(got, "skin=hana") {
		t.Fatalf("URL generada inesperada: %s", got)
	}
}

func TestFixedWindowConstants(t *testing.T) {
	if FixedWindowWidth <= 0 || FixedWindowHeight <= 0 {
		t.Fatalf("Dimensiones de ventana inválidas: %dx%d", FixedWindowWidth, FixedWindowHeight)
	}
	if FixedWindowWidth > 440 || FixedWindowHeight > 640 {
		t.Fatalf("Dimensiones excesivas para un compañero de escritorio: %dx%d", FixedWindowWidth, FixedWindowHeight)
	}
}

func TestNotchAndExpandedWindowConstants(t *testing.T) {
	if NotchWidth <= 0 || NotchHeight <= 0 {
		t.Fatalf("Dimensiones de notch inválidas: %dx%d", NotchWidth, NotchHeight)
	}
	if ExpandedWidth <= NotchWidth || ExpandedHeight <= NotchHeight {
		t.Fatalf("La ventana expandida debe ser mayor que el notch: (%dx%d) vs (%dx%d)",
			ExpandedWidth, ExpandedHeight, NotchWidth, NotchHeight)
	}
	if NotchHeight > 60 {
		t.Fatalf("El notch no debe exceder 60px para no estorbar en el borde superior: %d", NotchHeight)
	}
}

func TestConfigureTransparentNilGuard(t *testing.T) {
	err := configureTransparentWebView(nil)
	if err == nil {
		t.Fatal("se esperaba error al pasar webview nil")
	}
}

func TestComputeFixedWindowPosition(t *testing.T) {
	wa := winRect{Left: 0, Top: 0, Right: 1920, Bottom: 1040}

	// 1. 100% DPI (escala 1.0)
	x, y, w, h := computeFixedWindowPosition(wa, false, 1.0)
	if w != FixedWindowWidth || h != FixedWindowHeight {
		t.Fatalf("Esperado %dx%d a escala 1.0, obtenido %dx%d", FixedWindowWidth, FixedWindowHeight, w, h)
	}
	expectedX := (1920 - FixedWindowWidth) / 2
	if x != expectedX || y != 0 {
		t.Fatalf("Posición incorrecta a 1.0: got (%d,%d), want (%d,0)", x, y, expectedX)
	}

	// 2. 150% DPI (escala 1.5, común en pantallas de portátiles)
	x150, y150, w150, h150 := computeFixedWindowPosition(wa, false, 1.5)
	expectedW150 := int(float64(FixedWindowWidth) * 1.5)
	expectedH150 := int(float64(FixedWindowHeight) * 1.5)
	if w150 != expectedW150 || h150 != expectedH150 {
		t.Fatalf("Dimensiones incorrectas a escala 1.5: got %dx%d, want %dx%d", w150, h150, expectedW150, expectedH150)
	}
	expectedX150 := (1920 - expectedW150) / 2
	if x150 != expectedX150 || y150 != 0 {
		t.Fatalf("Posición incorrecta a 1.5: got (%d,%d), want (%d,0)", x150, y150, expectedX150)
	}

	// 3. Evasión de Snipping Tool con escala
	xDodge, yDodge, wDodge, hDodge := computeFixedWindowPosition(wa, true, 1.5)
	if xDodge <= (1920/2 + int(140.0*1.5)) {
		t.Fatalf("La evasión (%d) debe despejar la barra central", xDodge)
	}
	if xDodge+wDodge > 1920 {
		t.Fatalf("La ventana esquivada (%d + %d) no debe salir de la pantalla (1920)", xDodge, wDodge)
	}
	if yDodge != 0 || wDodge != expectedW150 || hDodge != expectedH150 {
		t.Fatalf("Dimensiones alteradas en evasión escalada: got (%d,%d)", wDodge, hDodge)
	}

	// 4. Monitor compacto o DPI alto: acotar altura al área de trabajo - 24*scale
	compactWA := winRect{Left: 0, Top: 0, Right: 1366, Bottom: 728}
	_, _, wCompact, hCompact := computeFixedWindowPosition(compactWA, false, 1.5)
	expectedMaxH := int(compactWA.Bottom-compactWA.Top) - int(24.0*1.5)
	if wCompact != expectedW150 {
		t.Fatalf("Ancho inesperado en monitor compacto: got %d, want %d", wCompact, expectedW150)
	}
	if hCompact != expectedMaxH {
		t.Fatalf("Altura no acotada en monitor compacto con 150%% DPI: got %d, want %d", hCompact, expectedMaxH)
	}
}

func TestResolveProjectRootAndLocalCoreURL(t *testing.T) {
	dir, err := resolveWebDir("")
	if err != nil {
		t.Fatalf("resolveWebDir falló: %v", err)
	}
	root := resolveProjectRoot(dir)
	if root == "" || !fileExists(filepath.Join(root, "run.py")) {
		t.Fatalf("resolveProjectRoot(%q) no encontró run.py: %q", dir, root)
	}

	host, local := isLocalCoreURL("ws://127.0.0.1:8765/v1/events")
	if !local || host != "127.0.0.1:8765" {
		t.Fatalf("isLocalCoreURL inesperado: host=%q local=%v", host, local)
	}
	if _, remoteLocal := isLocalCoreURL("wss://example.com/v1/events"); remoteLocal {
		t.Fatal("no debería tratar un host remoto como Core local")
	}
}

func TestInstallerExecutableNameDetection(t *testing.T) {
	if !isInstallerExecutableName(`C:\Temp\MEKA-Setup.exe`) {
		t.Fatal("MEKA-Setup.exe debe detectarse como instalador")
	}
	if !isInstallerExecutableName(`C:\Temp\meka-instalador.exe`) {
		t.Fatal("meka-instalador.exe debe detectarse como instalador")
	}
	if isInstallerExecutableName(`C:\Desktop\MEKA.exe`) {
		t.Fatal("MEKA.exe no debe tratarse como instalador")
	}
	if isInstallerExecutableName(`C:\Desktop\meka-desktop.exe`) {
		t.Fatal("meka-desktop.exe no debe tratarse como instalador")
	}
}

func TestResolveInstallPathsAndAppIcon(t *testing.T) {
	dir, err := resolveWebDir("")
	if err != nil {
		t.Fatalf("resolveWebDir falló: %v", err)
	}
	root := resolveProjectRoot(dir)

	iconPath := resolveAppIconPath(dir)
	if iconPath == "" || !fileExists(iconPath) {
		t.Fatalf("resolveAppIconPath no encontró icon.ico: %q", iconPath)
	}
	for _, asset := range []string{
		filepath.Join(root, "pet", "desktop", "icons", "icon.png"),
		filepath.Join(root, "pet", "desktop", "icons", "icon.ico"),
		filepath.Join(root, "pet", "web", "favicon.ico"),
		filepath.Join(root, "pet", "desktop", "rsrc_windows_amd64.syso"),
	} {
		if !fileExists(asset) {
			t.Fatalf("falta recurso esperado: %s", asset)
		}
	}

	tmp := t.TempDir()
	if err := os.WriteFile(filepath.Join(tmp, "meka-root.txt"), []byte(root+"\r\n"), 0644); err != nil {
		t.Fatalf("no se pudo escribir marcador temporal: %v", err)
	}
	if got := readRootMarker(tmp); got != root {
		t.Fatalf("readRootMarker = %q, want %q", got, root)
	}

	paths := resolveInstallPaths(`C:\LocalApp`, `C:\Roaming`, `C:\Users\Test`)
	if !strings.HasSuffix(paths.InstalledExe, filepath.Join("Programs", "MEKA", "MEKA.exe")) {
		t.Fatalf("InstalledExe inesperado: %s", paths.InstalledExe)
	}
	if !strings.HasSuffix(paths.DesktopLnk, filepath.Join("Desktop", "MEKA.lnk")) {
		t.Fatalf("DesktopLnk inesperado: %s", paths.DesktopLnk)
	}
	if !strings.HasSuffix(paths.StartMenuLnk, filepath.Join("Start Menu", "Programs", "MEKA.lnk")) {
		t.Fatalf("StartMenuLnk inesperado: %s", paths.StartMenuLnk)
	}
}
