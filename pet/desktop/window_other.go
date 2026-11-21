//go:build !windows

package main

import (
	"errors"
	"fmt"
	"os/exec"
	"runtime"
)

func attachConsoleIfNeeded(_ Config) {}

func recoverAndLog(_ string) {}

func logDesktopEvent(_, _, _ string) {}

func verifyLocalWebServer(_ string) error { return nil }

func isAutoStartEnabled() bool { return false }

func setAutoStartEnabled(_ string, _ bool) error {
	return errors.New("el inicio automático solo está soportado en Windows")
}

func registerBackgroundNotificationApp(_, _ string) error { return nil }

func runInstaller(_ Config, _ string) error {
	return errors.New("el instalador de accesos directos solo está soportado en Windows")
}

func runUninstaller(_ Config, _ string) error {
	return errors.New("el desinstalador solo está soportado en Windows")
}

func runNativeWindowWithShutdown(cfg Config, targetURL string, _ func()) error {
	return runNativeWindow(cfg, targetURL)
}

func runNativeWindow(_ Config, targetURL string) error {
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "darwin":
		cmd = exec.Command("open", targetURL)
	default:
		cmd = exec.Command("xdg-open", targetURL)
	}
	fmt.Printf("MEKA Companion ejecutándose en %s\n", targetURL)
	if err := cmd.Start(); err != nil {
		return err
	}
	select {}
}

