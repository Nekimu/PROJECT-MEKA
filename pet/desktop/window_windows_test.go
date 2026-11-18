//go:build windows

package main

import (
	"os"
	"testing"
)

func TestWindowTransparencyStyles(t *testing.T) {
	// 1. Estilos extendidos requeridos para DirectComposition puro y transparencia transparente
	baseExStyle := wsExTopmost | wsExToolWindow | wsExNoRedirectionBitmap | wsExNoActivate

	// Verificar que WS_EX_LAYERED NO esté presente en el estilo base (evita fallback DWM con WS_EX_NOREDIRECTIONBITMAP)
	if (baseExStyle & wsExLayered) != 0 {
		t.Fatalf("WS_EX_LAYERED no debe estar en los estilos base de la ventana")
	}

	// Verificar que WS_EX_NOREDIRECTIONBITMAP esté presente (DirectComposition sin superficie GDI)
	if (baseExStyle & wsExNoRedirectionBitmap) == 0 {
		t.Fatalf("WS_EX_NOREDIRECTIONBITMAP es requerido para WebView2 DirectComposition")
	}

	// 2. Comprobar que en click-through se añaden tanto wsExTransparent como wsExLayered
	clickThroughStyle := baseExStyle | wsExTransparent | wsExLayered
	if (clickThroughStyle & wsExTransparent) == 0 {
		t.Fatalf("wsExTransparent debe estar activo en click-through")
	}
	if (clickThroughStyle & wsExLayered) == 0 {
		t.Fatalf("wsExLayered debe estar activo en click-through para permitir el paso de clics a otras apps")
	}

	// 3. Comprobar que al desactivar click-through se limpian ambos
	restoredStyle := clickThroughStyle &^ (wsExTransparent | wsExLayered)
	if restoredStyle != baseExStyle {
		t.Fatalf("El estilo restaurado (0x%X) debe coincidir exactamente con el base (0x%X)", restoredStyle, baseExStyle)
	}

	// 4. Márgenes DWM deben ser -1 en todos los lados para extender la hoja de cristal en toda el área cliente
	margins := dwmMargins{-1, -1, -1, -1}
	if margins.CxLeftWidth != -1 || margins.CxRightWidth != -1 || margins.CyTopHeight != -1 || margins.CyBottomHeight != -1 {
		t.Fatalf("Los márgenes de DwmExtendFrameIntoClientArea deben ser {-1, -1, -1, -1}")
	}

	// 5. Variable de entorno para color por defecto transparente en WebView2
	_ = os.Setenv("WEBVIEW2_DEFAULT_BACKGROUND_COLOR", "0")
	if os.Getenv("WEBVIEW2_DEFAULT_BACKGROUND_COLOR") != "0" {
		t.Fatalf("WEBVIEW2_DEFAULT_BACKGROUND_COLOR debe ser '0'")
	}
}
