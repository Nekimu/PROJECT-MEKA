# MEKA · Compañera de Escritorio (Go + WebView2 + Pixel Art)

Una compañera animada en **Pixel Art** que flota sobre tu escritorio en una ventana nativa **sin bordes, siempre visible y con fondo 100 % transparente** escrita en **Go** (`pet/desktop/`). Se conecta en tiempo real a **MEKA Core** (`ws://127.0.0.1:8765/v1/events`) y permite cambiar libremente de avatar/personaje desde su barra lateral oculta desplegable, siguiendo la [Filosofía Híbrida](../docs/FILOSOFIA_HIBRIDA.md) e inspirada en [Soul-of-Waifu](https://github.com/jofizcd/Soul-of-Waifu).

| Escritorio nativo en Go (ventana transparente sin bordes) | Navegador / Ventana emergente (`?desktop=1`) |
|---|---|
| `pet/desktop/meka-desktop.exe` (o `go run .` en `pet/desktop/`) | Abre `pet/web/index.html` |

---

## 1. Aplicación de Escritorio Nativa en Go (`pet/desktop/`)

El envoltorio nativo en Go utiliza **Microsoft Edge WebView2** (`github.com/jchv/go-webview2`) y llamadas nativas a Win32/DWM (`WS_POPUP`, `WS_EX_TOPMOST`, `DwmExtendFrameIntoClientArea` y `WEBVIEW2_DEFAULT_BACKGROUND_COLOR=0`) sin requerir CGo ni Rust/Tauri.

### Ejecutar o compilar

```powershell
cd pet/desktop

# Ejecutar directamente:
go run .

# Elegir personaje inicial o URL de MEKA Core:
go run . --skin dva_pixel
go run . --skin clawd_pixel --core ws://127.0.0.1:8765/v1/events

# Compilar binario nativo (.exe):
go build -o meka-desktop.exe .

# Compilar versión de distribución sin ventana de consola en Windows:
go build -ldflags="-H=windowsgui -s -w" -o meka-desktop.exe .
```

### Controles y Estados de la Dynamic Island (`pet/desktop/`)
| Acción | Cómo |
|---|---|
| **Modo Notch (En reposo)** | Píldora compacta de `230×44 px` en negro profundo (`#000000`) pegada al borde superior central de la pantalla, con retroiluminación tenue morada difusa que emana desde el fondo. Cero estorbo para el resto de aplicaciones. |
| **Desplegar hacia abajo** | Pasa el cursor sobre el notch (`hover`) o haz clic en él. La ventana se expande elásticamente hacia abajo hasta `320×430 px`, revelando el avatar completo, el bocadillo y el chat. |
| **Replegar al notch** | Retira el mouse del notch (cuenta con ~450 ms de gracia) o presiona `Escape`. |
| **Saludar / Reaccionar** | Clic izquierdo sobre el personaje (activa animación elástica *Squash & Stretch*). |
| **Barra lateral oculta desplegable** | Botón `☰` en la píldora superior o clic derecho → *⚙️ Configuración y avatares* (se despliega de forma fluida dentro del escenario sin salirse de la pantalla). |
| **Hablar con el agente (Spotlight)** | Campo inferior de mensaje rápido (`user.message`). Mantiene el notch expandido mientras escribes. |
| **Confirmar herramientas (`agent.confirm`)** | El notch se expande automáticamente y muestra los botones **Permitir** / **Cancelar** en el bocadillo de diálogo. |
| **Cerrar aplicación** | Clic derecho → *✖ Cerrar aplicación*. |

---

## 2. Modo Estudio en Navegador (`pet/web/`)

Para probar todos los estados de MEKA Core con el panel de simulación:

```powershell
cd pet/desktop
go run . --serve 127.0.0.1:8080
# Abre http://127.0.0.1:8080/index.html
```

---

## Estructura de Archivos

```
pet/
├── desktop/
│   ├── main.go             # Servidor loopback efímero (127.0.0.1:0) + CLI
│   ├── window_windows.go   # Ventana nativa transparente sin bordes (Win32 + DWM + WebView2)
│   ├── window_other.go     # Lanzador multiplataforma
│   ├── main_test.go        # Pruebas unitarias en Go (go test ./...)
│   ├── go.mod / go.sum     # Módulo Go (sin CGo, cero dependencias de Rust)
│   └── icons/              # Iconos de la aplicación
├── web/
│   ├── index.html          # Escenario, barra lateral desplegable (Drawer popover) y estudio
│   ├── pet.css             # Estética minimalista Apple, materiales translúcidos y animaciones
│   ├── pet.js              # Máquina de estados, puente Go (mekaStartDrag/mekaSetDrawerExpanded) y WebSocket
│   └── skins/
│       ├── manifest.js     # Catálogo de avatares (todos desbloqueados desde el inicio)
│       ├── dva_pixel/      # Pixel Art animado 64×64 (Hana · Pixel)
│       ├── clawd_pixel/    # Pixel Art animado 64×64 (Clawd · Pixel)
│       └── <personaje>/*.webp
└── tools/
    ├── pixelize.py         # Conversor de stickers/GIFs a Pixel Art 64×64 WebP animado
    └── stickerize.py       # Recorte de fondo para stickers ilustrados
```

## Pruebas Automatizadas

```powershell
# Pruebas del cliente de escritorio en Go:
cd pet/desktop
go test -v ./...

# Pruebas del catálogo de skins y sprites Pixel Art:
.\venv\Scripts\python.exe -m pytest tests/test_pet_skins.py -v
```
