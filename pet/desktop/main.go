// MEKA · Compañera de Escritorio en Go (Ventana Nativa Transparente + Pixel Art + Drawer)
//
// Sirve la interfaz minimalista de `pet/web` en un servidor loopback efímero (127.0.0.1:0)
// y abre una ventana nativa sin bordes, transparente y siempre visible mediante WebView2
// (sin depender de Rust/Tauri ni de interfaces en Python).
package main

import (
	"errors"
	"flag"
	"fmt"
	"mime"
	"net"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"runtime"
)

const (
	NotchWidth        = 236
	NotchHeight       = 46
	ExpandedWidth     = 330
	ExpandedHeight    = 434
	FixedWindowWidth  = 380
	FixedWindowHeight = 480
)

type Config struct {
	CoreURL   string
	Token     string
	Skin      string
	WebDir    string
	Debug     bool
	SelfTest  bool
	ServeOnly string
}

func parseFlags() Config {
	var cfg Config
	defaultCore := os.Getenv("MEKA_CORE_URL")
	if defaultCore == "" {
		defaultCore = "ws://127.0.0.1:8765/v1/events"
	}
	defaultToken := os.Getenv("MEKA_API_TOKEN")

	flag.StringVar(&cfg.CoreURL, "core", defaultCore, "URL WebSocket de MEKA Core")
	flag.StringVar(&cfg.Token, "token", defaultToken, "Token opcional MEKA_API_TOKEN")
	flag.StringVar(&cfg.Skin, "skin", "", "ID del personaje inicial (ej. hana, 2b, kiriko, marin, yotsuba)")
	flag.StringVar(&cfg.WebDir, "web-dir", "", "Ruta a la carpeta pet/web (autodetectada si se omite)")
	flag.BoolVar(&cfg.Debug, "debug", false, "Habilitar herramientas de desarrollo (DevTools)")
	flag.BoolVar(&cfg.SelfTest, "self-test", false, "Verificar servidor de assets Chibi y salir")
	flag.StringVar(&cfg.ServeOnly, "serve", "", "Solo servir en la dirección indicada (ej. 127.0.0.1:8080)")
	flag.Parse()
	return cfg
}

// resolveWebDir localiza `pet/web` buscando primero respecto al binario, luego el directorio
// de trabajo actual y finalmente la ruta del código fuente.
func resolveWebDir(explicit string) (string, error) {
	var candidates []string
	if explicit != "" {
		candidates = append(candidates, explicit)
	}

	if exe, err := os.Executable(); err == nil {
		exeDir := filepath.Dir(exe)
		candidates = append(candidates,
			filepath.Join(exeDir, "web"),
			filepath.Join(exeDir, "..", "web"),
			filepath.Join(exeDir, "pet", "web"),
			filepath.Join(exeDir, "..", "pet", "web"),
			filepath.Join(exeDir, "PROJECT-MEKA", "pet", "web"),
			filepath.Join(exeDir, "Project MEKA", "PROJECT-MEKA", "pet", "web"),
		)
	}

	if cwd, err := os.Getwd(); err == nil {
		candidates = append(candidates,
			filepath.Join(cwd, "web"),
			filepath.Join(cwd, "..", "web"),
			filepath.Join(cwd, "pet", "web"),
		)
	}

	if _, file, _, ok := runtime.Caller(0); ok {
		srcDir := filepath.Dir(file)
		candidates = append(candidates, filepath.Join(srcDir, "..", "web"))
	}

	for _, dir := range candidates {
		abs, err := filepath.Abs(dir)
		if err != nil {
			continue
		}
		manifestPath := filepath.Join(abs, "skins", "manifest.js")
		indexPath := filepath.Join(abs, "index.html")
		if fileExists(indexPath) && fileExists(manifestPath) {
			return abs, nil
		}
	}
	return "", errors.New("no se encontró la carpeta pet/web (index.html + skins/manifest.js)")
}

func fileExists(path string) bool {
	info, err := os.Stat(path)
	return err == nil && !info.IsDir()
}

// resolveProjectRoot obtiene el directorio raíz de PROJECT-MEKA (donde viven run.py y venv/)
// a partir de la ruta resuelta de `pet/web`.
func resolveProjectRoot(webDir string) string {
	if webDir == "" {
		return ""
	}
	candidates := []string{
		filepath.Clean(filepath.Join(webDir, "..", "..")),
		filepath.Clean(filepath.Join(webDir, "..")),
	}
	for _, root := range candidates {
		if fileExists(filepath.Join(root, "run.py")) {
			return root
		}
	}
	return ""
}

// newWebHandler construye el servidor HTTP local para `pet/web` con tipos MIME correctos
// para sprites WebP animados y módulos JS/CSS.
func newWebHandler(webDir string) http.Handler {
	_ = mime.AddExtensionType(".webp", "image/webp")
	_ = mime.AddExtensionType(".js", "application/javascript; charset=utf-8")
	_ = mime.AddExtensionType(".css", "text/css; charset=utf-8")

	fs := http.FileServer(http.Dir(webDir))
	mux := http.NewServeMux()

	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		_, _ = w.Write([]byte(`{"ok":true,"host":"meka-go-desktop"}`))
	})

	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
		w.Header().Set("Pragma", "no-cache")
		w.Header().Set("Expires", "0")
		fs.ServeHTTP(w, r)
	})

	return mux
}

func buildCompanionURL(baseAddr string, cfg Config) string {
	u := url.URL{
		Scheme: "http",
		Host:   baseAddr,
		Path:   "/index.html",
	}
	q := u.Query()
	q.Set("desktop", "1")
	if cfg.CoreURL != "" {
		q.Set("core", cfg.CoreURL)
	}
	if cfg.Token != "" {
		q.Set("token", cfg.Token)
	}
	if cfg.Skin != "" {
		q.Set("skin", cfg.Skin)
	}
	u.RawQuery = q.Encode()
	return u.String()
}

func runSelfTest(webDir string) error {
	required := []string{
		"index.html",
		"pet.css",
		"pet.js",
		filepath.Join("skins", "manifest.js"),
		filepath.Join("skins", "hana", "idle.webp"),
		filepath.Join("skins", "2b", "idle.webp"),
	}
	for _, rel := range required {
		full := filepath.Join(webDir, rel)
		info, err := os.Stat(full)
		if err != nil || info.Size() == 0 {
			return fmt.Errorf("asset requerido ausente o vacío: %s", rel)
		}
		fmt.Printf("OK %-32s (%d bytes)\n", rel, info.Size())
	}
	return nil
}

func main() {
	cfg := parseFlags()

	webDir, err := resolveWebDir(cfg.WebDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	cfg.WebDir = webDir

	if cfg.SelfTest {
		if err := runSelfTest(webDir); err != nil {
			fmt.Fprintf(os.Stderr, "Fallo en self-test: %v\n", err)
			os.Exit(1)
		}
		fmt.Printf("OK MEKA Go Desktop listo (webDir=%s)\n", webDir)
		return
	}

	listenAddr := "127.0.0.1:0"
	if cfg.ServeOnly != "" {
		listenAddr = cfg.ServeOnly
	}

	ln, err := net.Listen("tcp", listenAddr)
	if err != nil {
		fmt.Fprintf(os.Stderr, "No se pudo abrir puerto local (%s): %v\n", listenAddr, err)
		os.Exit(1)
	}
	defer ln.Close()

	srv := &http.Server{Handler: newWebHandler(webDir)}
	targetURL := buildCompanionURL(ln.Addr().String(), cfg)

	if cfg.ServeOnly != "" {
		fmt.Printf("MEKA Companion sirviendo en %s\n", targetURL)
		if err := srv.Serve(ln); err != nil && !errors.Is(err, http.ErrServerClosed) {
			fmt.Fprintf(os.Stderr, "Error HTTP: %v\n", err)
			os.Exit(1)
		}
		return
	}

	go func() {
		_ = srv.Serve(ln)
	}()

	if err := runNativeWindow(cfg, targetURL); err != nil {
		fmt.Fprintf(os.Stderr, "Error en ventana nativa: %v\n", err)
		os.Exit(1)
	}
}

