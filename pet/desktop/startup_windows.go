//go:build windows

package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"syscall"
	"unsafe"
)

const (
	appUserModelID      = "MEKA.Desktop.Companion"
	appDisplayName      = "MEKA Companion"
	appIconBGColor      = "FF141826"
	runRegistrySubkey   = `Software\Microsoft\Windows\CurrentVersion\Run`
	runRegistryValName  = "MEKA"
	aumidBaseSubkey     = `Software\Classes\AppUserModelId\` + appUserModelID
	notifSettingsSubkey = `Software\Microsoft\Windows\CurrentVersion\Notifications\Settings\` + appUserModelID

	regSZ         = 1
	regDWord      = 4
	keyQueryValue = 0x0001
	keySetValue   = 0x0002
	keyRead       = 0x20019
	errFileNotFnd = 2
)

var (
	advapi32                              = syscall.NewLazyDLL("advapi32.dll")
	procRegCreateKeyExW                   = advapi32.NewProc("RegCreateKeyExW")
	procRegSetValueExW                    = advapi32.NewProc("RegSetValueExW")
	procRegDeleteValueW                   = advapi32.NewProc("RegDeleteValueW")
	procRegDeleteTreeW                    = advapi32.NewProc("RegDeleteTreeW")
	procSetCurrentProcessExplicitAppUMID  = shell32.NewProc("SetCurrentProcessExplicitAppUserModelID")
)

func buildAutoStartCommand(exePath string) string {
	clean := strings.TrimSpace(exePath)
	if clean == "" {
		return ""
	}
	return fmt.Sprintf(`"%s" --startup`, clean)
}

func resolveAutoStartExePath(explicit string) string {
	if trimmed := strings.TrimSpace(explicit); trimmed != "" {
		if abs, err := filepath.Abs(trimmed); err == nil {
			return abs
		}
		return trimmed
	}
	paths := currentInstallPaths()
	if paths.InstalledExe != "" && fileExists(paths.InstalledExe) {
		return paths.InstalledExe
	}
	if cur, err := os.Executable(); err == nil && cur != "" {
		return cur
	}
	return paths.InstalledExe
}

func applyProcessAppUserModelID() {
	if !procAvailable(procSetCurrentProcessExplicitAppUMID) {
		return
	}
	ptr, err := syscall.UTF16PtrFromString(appUserModelID)
	if err != nil {
		return
	}
	_, _, _ = procSetCurrentProcessExplicitAppUMID.Call(uintptr(unsafe.Pointer(ptr)))
}

func regCreateKeyHKCU(subkey string) (syscall.Handle, error) {
	if !procAvailable(procRegCreateKeyExW) {
		return 0, fmt.Errorf("RegCreateKeyExW no disponible")
	}
	subPtr, err := syscall.UTF16PtrFromString(subkey)
	if err != nil {
		return 0, err
	}
	var handle syscall.Handle
	ret, _, _ := procRegCreateKeyExW.Call(
		uintptr(syscall.HKEY_CURRENT_USER),
		uintptr(unsafe.Pointer(subPtr)),
		0,
		0,
		0,
		keySetValue|keyQueryValue,
		0,
		uintptr(unsafe.Pointer(&handle)),
		0,
	)
	if ret != 0 {
		return 0, syscall.Errno(ret)
	}
	return handle, nil
}

func regSetString(h syscall.Handle, name, value string) error {
	if !procAvailable(procRegSetValueExW) {
		return fmt.Errorf("RegSetValueExW no disponible")
	}
	var namePtr uintptr
	if name != "" {
		p, err := syscall.UTF16PtrFromString(name)
		if err != nil {
			return err
		}
		namePtr = uintptr(unsafe.Pointer(p))
	}
	u16, err := syscall.UTF16FromString(value)
	if err != nil {
		return err
	}
	ret, _, _ := procRegSetValueExW.Call(
		uintptr(h),
		namePtr,
		0,
		regSZ,
		uintptr(unsafe.Pointer(&u16[0])),
		uintptr(len(u16)*2),
	)
	if ret != 0 {
		return syscall.Errno(ret)
	}
	return nil
}

func regSetDWord(h syscall.Handle, name string, value uint32) error {
	if !procAvailable(procRegSetValueExW) {
		return fmt.Errorf("RegSetValueExW no disponible")
	}
	p, err := syscall.UTF16PtrFromString(name)
	if err != nil {
		return err
	}
	v := value
	ret, _, _ := procRegSetValueExW.Call(
		uintptr(h),
		uintptr(unsafe.Pointer(p)),
		0,
		regDWord,
		uintptr(unsafe.Pointer(&v)),
		4,
	)
	if ret != 0 {
		return syscall.Errno(ret)
	}
	return nil
}

func isAutoStartEnabled() bool {
	subPtr, err := syscall.UTF16PtrFromString(runRegistrySubkey)
	if err != nil {
		return false
	}
	var h syscall.Handle
	if err := syscall.RegOpenKeyEx(syscall.HKEY_CURRENT_USER, subPtr, 0, keyRead, &h); err != nil {
		return false
	}
	defer syscall.RegCloseKey(h)

	valPtr, err := syscall.UTF16PtrFromString(runRegistryValName)
	if err != nil {
		return false
	}
	var typ uint32
	var bufLen uint32
	if err := syscall.RegQueryValueEx(h, valPtr, nil, &typ, nil, &bufLen); err != nil || bufLen < 2 {
		return false
	}
	buf := make([]uint16, bufLen/2+1)
	if err := syscall.RegQueryValueEx(h, valPtr, nil, &typ, (*byte)(unsafe.Pointer(&buf[0])), &bufLen); err != nil {
		return false
	}
	val := strings.TrimSpace(syscall.UTF16ToString(buf))
	return val != ""
}

func setAutoStartEnabled(exePath string, enabled bool) error {
	if enabled {
		resolved := resolveAutoStartExePath(exePath)
		cmdLine := buildAutoStartCommand(resolved)
		if cmdLine == "" {
			return fmt.Errorf("no se pudo determinar la ruta de MEKA.exe para arranque automático")
		}
		h, err := regCreateKeyHKCU(runRegistrySubkey)
		if err != nil {
			return fmt.Errorf("error abriendo clave Run de Windows: %w", err)
		}
		defer syscall.RegCloseKey(h)

		if err := regSetString(h, runRegistryValName, cmdLine); err != nil {
			return fmt.Errorf("error guardando entrada de arranque automático: %w", err)
		}
		return nil
	}

	subPtr, err := syscall.UTF16PtrFromString(runRegistrySubkey)
	if err != nil {
		return err
	}
	var h syscall.Handle
	if err := syscall.RegOpenKeyEx(syscall.HKEY_CURRENT_USER, subPtr, 0, keySetValue, &h); err != nil {
		return nil // Si la clave no existe, ya está desactivado
	}
	defer syscall.RegCloseKey(h)

	if !procAvailable(procRegDeleteValueW) {
		return nil
	}
	valPtr, err := syscall.UTF16PtrFromString(runRegistryValName)
	if err != nil {
		return err
	}
	ret, _, _ := procRegDeleteValueW.Call(uintptr(h), uintptr(unsafe.Pointer(valPtr)))
	if ret != 0 && ret != errFileNotFnd {
		return syscall.Errno(ret)
	}
	return nil
}

func registerBackgroundNotificationApp(exePath, iconPath string) error {
	iconURI := strings.TrimSpace(iconPath)
	if iconURI == "" || !fileExists(iconURI) {
		iconURI = resolveAutoStartExePath(exePath)
	}

	hAumid, err := regCreateKeyHKCU(aumidBaseSubkey)
	if err != nil {
		return fmt.Errorf("error registrando AppUserModelId: %w", err)
	}
	if err := regSetString(hAumid, "DisplayName", appDisplayName); err != nil {
		_ = syscall.RegCloseKey(hAumid)
		return err
	}
	if iconURI != "" {
		_ = regSetString(hAumid, "IconUri", iconURI)
	}
	_ = regSetString(hAumid, "IconBackgroundColor", appIconBGColor)
	_ = syscall.RegCloseKey(hAumid)

	hNotif, err := regCreateKeyHKCU(notifSettingsSubkey)
	if err != nil {
		return fmt.Errorf("error registrando preferencias de notificaciones en segundo plano: %w", err)
	}
	if err := regSetDWord(hNotif, "Enabled", 1); err != nil {
		_ = syscall.RegCloseKey(hNotif)
		return err
	}
	_ = regSetDWord(hNotif, "ShowInActionCenter", 1)
	_ = syscall.RegCloseKey(hNotif)
	return nil
}

func unregisterBackgroundNotificationApp() {
	if !procAvailable(procRegDeleteTreeW) {
		return
	}
	for _, subkey := range []string{aumidBaseSubkey, notifSettingsSubkey} {
		if ptr, err := syscall.UTF16PtrFromString(subkey); err == nil {
			_, _, _ = procRegDeleteTreeW.Call(uintptr(syscall.HKEY_CURRENT_USER), uintptr(unsafe.Pointer(ptr)))
		}
	}
}
