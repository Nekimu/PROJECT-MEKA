//go:build windows

package main

import (
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"
	"unsafe"
)

var (
	procSHGetKnownFolderPath = shell32.NewProc("SHGetKnownFolderPath")
	procCoTaskMemFree        = ole32.NewProc("CoTaskMemFree")

	folderIDDesktop = guid{
		Data1: 0xB4BFCC3A,
		Data2: 0xDB2C,
		Data3: 0x424C,
		Data4: [8]byte{0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41},
	}
)

type InstallPaths struct {
	InstallDir    string
	InstalledExe  string
	InstalledIcon string
	RootMarker    string
	DesktopExe    string
	DesktopLnk    string
	StartMenuLnk  string
}

func resolveInstallPaths(localAppData, appData, userProfile string) InstallPaths {
	if localAppData == "" {
		localAppData = os.TempDir()
	}
	if appData == "" {
		appData = localAppData
	}
	if userProfile == "" {
		userProfile = os.Getenv("USERPROFILE")
	}
	installDir := filepath.Join(localAppData, "Programs", "MEKA")
	desktopDir := filepath.Join(userProfile, "Desktop")
	startMenuDir := filepath.Join(appData, "Microsoft", "Windows", "Start Menu", "Programs")

	return InstallPaths{
		InstallDir:    installDir,
		InstalledExe:  filepath.Join(installDir, "MEKA.exe"),
		InstalledIcon: filepath.Join(installDir, "icon.ico"),
		RootMarker:    filepath.Join(installDir, "meka-root.txt"),
		DesktopExe:    filepath.Join(desktopDir, "MEKA.exe"),
		DesktopLnk:    filepath.Join(desktopDir, "MEKA.lnk"),
		StartMenuLnk:  filepath.Join(startMenuDir, "MEKA.lnk"),
	}
}

func utf16PtrToString(ptr uintptr) string {
	if ptr == 0 {
		return ""
	}
	for i := 0; i < 4096; i++ {
		if *(*uint16)(unsafe.Pointer(ptr + uintptr(i)*2)) == 0 {
			return syscall.UTF16ToString(unsafe.Slice((*uint16)(unsafe.Pointer(ptr)), i))
		}
	}
	return ""
}

func resolveDesktopDir(userProfile string) string {
	if procAvailable(procSHGetKnownFolderPath) && procAvailable(procCoTaskMemFree) {
		var pathPtr uintptr
		hr, _, _ := procSHGetKnownFolderPath.Call(
			uintptr(unsafe.Pointer(&folderIDDesktop)),
			0,
			0,
			uintptr(unsafe.Pointer(&pathPtr)),
		)
		if pathPtr != 0 {
			defer procCoTaskMemFree.Call(pathPtr)
		}
		if hr == 0 && pathPtr != 0 {
			if p := strings.TrimSpace(utf16PtrToString(pathPtr)); p != "" {
				return p
			}
		}
	}
	if userProfile != "" {
		return filepath.Join(userProfile, "Desktop")
	}
	return ""
}

func currentInstallPaths() InstallPaths {
	userProfile := os.Getenv("USERPROFILE")
	paths := resolveInstallPaths(
		os.Getenv("LOCALAPPDATA"),
		os.Getenv("APPDATA"),
		userProfile,
	)
	if desktopDir := resolveDesktopDir(userProfile); desktopDir != "" {
		paths.DesktopExe = filepath.Join(desktopDir, "MEKA.exe")
		paths.DesktopLnk = filepath.Join(desktopDir, "MEKA.lnk")
	}
	return paths
}

func sameFilePath(a, b string) bool {
	absA, errA := filepath.Abs(a)
	absB, errB := filepath.Abs(b)
	if errA != nil || errB != nil {
		return strings.EqualFold(filepath.Clean(a), filepath.Clean(b))
	}
	return strings.EqualFold(filepath.Clean(absA), filepath.Clean(absB))
}

func copyFileOverwrite(src, dst string) error {
	if sameFilePath(src, dst) {
		return nil
	}
	if err := os.MkdirAll(filepath.Dir(dst), 0755); err != nil {
		return err
	}
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	tmp := dst + ".tmp"
	out, err := os.OpenFile(tmp, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0755)
	if err != nil {
		return err
	}
	if _, err := io.Copy(out, in); err != nil {
		_ = out.Close()
		_ = os.Remove(tmp)
		return err
	}
	if err := out.Close(); err != nil {
		_ = os.Remove(tmp)
		return err
	}
	if err := os.Rename(tmp, dst); err != nil {
		_ = os.Remove(tmp)
		return err
	}
	return nil
}

func stopRunningMekaProcesses(currentExe string) {
	// Primero intenta cierre ordenado vía WM_CLOSE para que la instancia anterior apague su árbol de Core.
	if procAvailable(procFindWindowW) && procAvailable(procPostMessageW) {
		if titlePtr, err := syscall.UTF16PtrFromString("MEKA Dynamic Island"); err == nil {
			if existing, _, _ := procFindWindowW.Call(0, uintptr(unsafe.Pointer(titlePtr))); existing != 0 {
				_, _, _ = procPostMessageW.Call(existing, wmClose, 0, 0)
				deadline := time.Now().Add(1200 * time.Millisecond)
				for time.Now().Before(deadline) {
					time.Sleep(100 * time.Millisecond)
					again, _, _ := procFindWindowW.Call(0, uintptr(unsafe.Pointer(titlePtr)))
					if again == 0 {
						break
					}
				}
			}
		}
	}

	targets := []string{"MEKA.exe", "meka-desktop.exe", "desktop.exe"}
	curBase := filepath.Base(currentExe)
	for _, image := range targets {
		if strings.EqualFold(curBase, image) {
			continue
		}
		cmd := exec.Command("taskkill", "/T", "/F", "/IM", image)
		cmd.SysProcAttr = &syscall.SysProcAttr{
			HideWindow:    true,
			CreationFlags: 0x08000000, // CREATE_NO_WINDOW
		}
		_ = cmd.Run()
	}
}

func escapePSSingleQuote(s string) string {
	return strings.ReplaceAll(s, "'", "''")
}

func createWindowsShortcut(lnkPath, targetPath, workDir, iconPath, description string) error {
	if err := os.MkdirAll(filepath.Dir(lnkPath), 0755); err != nil {
		return err
	}
	iconLoc := targetPath + ",0"
	if iconPath != "" && fileExists(iconPath) {
		iconLoc = iconPath + ",0"
	}
	script := fmt.Sprintf(
		"$ws = New-Object -ComObject WScript.Shell; "+
			"$s = $ws.CreateShortcut('%s'); "+
			"$s.TargetPath = '%s'; "+
			"$s.WorkingDirectory = '%s'; "+
			"$s.IconLocation = '%s'; "+
			"$s.Description = '%s'; "+
			"$s.Save()",
		escapePSSingleQuote(lnkPath),
		escapePSSingleQuote(targetPath),
		escapePSSingleQuote(workDir),
		escapePSSingleQuote(iconLoc),
		escapePSSingleQuote(description),
	)
	cmd := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", script)
	cmd.SysProcAttr = &syscall.SysProcAttr{
		HideWindow:    true,
		CreationFlags: 0x08000000, // CREATE_NO_WINDOW
	}
	if out, err := cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("error creando acceso directo %s: %w (%s)", lnkPath, err, strings.TrimSpace(string(out)))
	}
	return nil
}

func runInstaller(cfg Config, webDir string) error {
	curExe, err := os.Executable()
	if err != nil {
		if !cfg.Silent {
			showMessageBox("Instalador de MEKA", fmt.Sprintf("No se pudo ubicar el ejecutable: %v", err), mbOk|mbIconError)
		}
		return err
	}

	projectRoot := resolveProjectRoot(webDir)
	if projectRoot == "" {
		projectRoot = filepath.Dir(webDir)
	}
	paths := currentInstallPaths()

	stopRunningMekaProcesses(curExe)

	if err := os.MkdirAll(paths.InstallDir, 0755); err != nil {
		if !cfg.Silent {
			showMessageBox("Instalador de MEKA", fmt.Sprintf("No se pudo crear %s:\n%v", paths.InstallDir, err), mbOk|mbIconError)
		}
		return err
	}

	if err := copyFileOverwrite(curExe, paths.InstalledExe); err != nil {
		if !cfg.Silent {
			showMessageBox("Instalador de MEKA", fmt.Sprintf("No se pudo copiar MEKA.exe:\n%v", err), mbOk|mbIconError)
		}
		return err
	}

	if err := os.WriteFile(paths.RootMarker, []byte(projectRoot+"\n"), 0644); err != nil {
		if !cfg.Silent {
			showMessageBox("Instalador de MEKA", fmt.Sprintf("No se pudo guardar meka-root.txt:\n%v", err), mbOk|mbIconError)
		}
		return err
	}

	iconSrc := resolveAppIconPath(webDir)
	if iconSrc != "" {
		_ = copyFileOverwrite(iconSrc, paths.InstalledIcon)
	}

	if paths.DesktopExe != "" {
		if err := copyFileOverwrite(curExe, paths.DesktopExe); err != nil {
			if !cfg.Silent {
				showMessageBox("Instalador de MEKA", fmt.Sprintf("No se pudo copiar MEKA.exe al Escritorio:\n%v", err), mbOk|mbIconError)
			}
			return err
		}
		_ = os.Remove(filepath.Join(filepath.Dir(paths.DesktopExe), "MEKA-Setup.exe"))
	}
	if paths.DesktopLnk != "" {
		_ = os.Remove(paths.DesktopLnk)
	}

	desc := "MEKA · Compañera de Escritorio y Core Unificado"
	if err := createWindowsShortcut(paths.StartMenuLnk, paths.InstalledExe, projectRoot, paths.InstalledIcon, desc); err != nil {
		if !cfg.Silent {
			showMessageBox("Instalador de MEKA", err.Error(), mbOk|mbIconError)
		}
		return err
	}

	autoStartStatus := "activo"
	if err := setAutoStartEnabled(paths.InstalledExe, true); err != nil {
		autoStartStatus = fmt.Sprintf("aviso: %v", err)
		logDesktopEvent("WARN", "installer", fmt.Sprintf("No se pudo activar arranque automático: %v", err))
	}

	notifStatus := appUserModelID
	if err := registerBackgroundNotificationApp(paths.InstalledExe, paths.InstalledIcon); err != nil {
		notifStatus = fmt.Sprintf("aviso: %v", err)
		logDesktopEvent("WARN", "installer", fmt.Sprintf("No se pudo registrar en notificaciones en segundo plano: %v", err))
	}

	fmt.Printf("OK MEKA instalado correctamente\n")
	fmt.Printf("   App:        %s\n", paths.InstalledExe)
	fmt.Printf("   Icono:      %s\n", paths.InstalledIcon)
	fmt.Printf("   Proyecto:   %s\n", projectRoot)
	fmt.Printf("   Escritorio: %s\n", paths.DesktopExe)
	fmt.Printf("   Menú:       %s\n", paths.StartMenuLnk)
	fmt.Printf("   Arranque:   %s\n", autoStartStatus)
	fmt.Printf("   NotifApp:   %s\n", notifStatus)

	if !cfg.Silent {
		msg := fmt.Sprintf(
			"MEKA se instaló correctamente con un único ejecutable, inicio automático con Windows, notificaciones en segundo plano y Core unificado.\n\n"+
				"• Aplicación: %s\n"+
				"• Escritorio: %s\n"+
				"• Menú Inicio: %s\n"+
				"• Arranque Windows: %s\n"+
				"• Notificaciones: %s\n\n"+
				"¿Deseas iniciar MEKA ahora?",
			paths.InstalledExe,
			paths.DesktopExe,
			paths.StartMenuLnk,
			autoStartStatus,
			notifStatus,
		)
		if showMessageBox("Instalador de MEKA", msg, mbYesNo|mbIconInfo) == idYes {
			launchCmd := exec.Command(paths.InstalledExe)
			launchCmd.Dir = projectRoot
			launchCmd.SysProcAttr = &syscall.SysProcAttr{
				HideWindow:    true,
				CreationFlags: 0x08000000, // CREATE_NO_WINDOW
			}
			_ = launchCmd.Start()
		}
	}
	return nil
}

func removeFileIfExists(path string) error {
	if path == "" {
		return nil
	}
	err := os.Remove(path)
	if err == nil || errors.Is(err, os.ErrNotExist) {
		return nil
	}
	return err
}

func runUninstaller(cfg Config, _ string) error {
	curExe, _ := os.Executable()
	stopRunningMekaProcesses(curExe)

	_ = setAutoStartEnabled("", false)
	unregisterBackgroundNotificationApp()

	paths := currentInstallPaths()
	var errs []string
	if err := removeFileIfExists(paths.DesktopLnk); err != nil {
		errs = append(errs, err.Error())
	}
	if err := removeFileIfExists(paths.StartMenuLnk); err != nil {
		errs = append(errs, err.Error())
	}
	if !sameFilePath(curExe, paths.DesktopExe) {
		if err := removeFileIfExists(paths.DesktopExe); err != nil {
			errs = append(errs, err.Error())
		}
	}
	if !sameFilePath(curExe, paths.InstalledExe) && paths.InstallDir != "" {
		if err := os.RemoveAll(paths.InstallDir); err != nil && !errors.Is(err, os.ErrNotExist) {
			errs = append(errs, err.Error())
		}
	}

	if len(errs) > 0 {
		combined := strings.Join(errs, "; ")
		logDesktopEvent("ERROR", "uninstaller", "Error eliminando archivos: "+combined)
		if !cfg.Silent {
			showMessageBox("Desinstalador de MEKA", "No se pudieron eliminar algunos archivos de MEKA:\n"+combined, mbOk|mbIconError)
		}
		return fmt.Errorf("desinstalación incompleta: %s", combined)
	}

	fmt.Printf("OK MEKA desinstalado (%s)\n", paths.InstallDir)
	if !cfg.Silent {
		showMessageBox("Desinstalador de MEKA", "Se han eliminado los accesos directos, arranque automático y la instalación local de MEKA.", mbOk|mbIconInfo)
	}
	return nil
}
