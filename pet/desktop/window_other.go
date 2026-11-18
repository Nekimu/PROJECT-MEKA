//go:build !windows

package main

import (
	"fmt"
	"os/exec"
	"runtime"
)

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

