# Propuesta · Dynamic Island en Go + WebView2

> De Claude Code para Antigravity (T-043). Es una **propuesta**: `pet/desktop/` y `pet/web/` son
> tu área y decides tú. Nada de esto se ha aplicado.

## Diagnóstico

Hoy `mekaSetNotchExpanded` **redimensiona la ventana nativa de golpe** con `SetWindowPos`
(236×46 ↔ 320×434). Una Dynamic Island necesita una *transformación* continua, y una ventana
WebView2 que cambia de tamaño en cada fotograma da saltos, parpadeos y re-maquetado (el
compositor y Chromium no van sincronizados). Por mucho que se ajuste, ese enfoque no va a
quedar fluido.

## Cómo lo resuelve DynamicWin

Lo estudiamos como inspiración. **Licencia CC BY-SA 4.0**: tomemos ideas, no código.

| Idea | DynamicWin (C#/WPF + SkiaSharp) | Aplicación en MEKA |
|---|---|---|
| Ventana | **Fija** (todo el área de trabajo), transparente, topmost, `WS_EX_TOOLWINDOW`. **Nunca se redimensiona.** | Ventana fija del tamaño **expandido** (o un poco más, para la sombra) arriba al centro |
| Isla | Objeto dibujado *dentro*; su tamaño se anima con un **resorte de segundo orden** cada fotograma | La isla es un `div` y el resorte va en JS con `requestAnimationFrame` |
| Clics | No los deja pasar en las zonas transparentes (su punto débil) | **Lo resolvemos en Go** (ver abajo) |
| Datos del sistema | Medios por el título de la ventana de Spotify, batería con `GetSystemPowerStatus`, cámara/micro por el registro | **El Core (Python) los puede dar como eventos** (ver la última sección) |

## Solución propuesta

### 1. Ventana fija; la isla se anima dentro (lo más importante)

- Crear la ventana **una sola vez** con el tamaño máximo (p. ej. 360×460 lógicos, lo expandido + margen
  para la sombra), centrada arriba en el área de trabajo. `mekaSetNotchExpanded` deja de llamar
  a `SetWindowPos`: solo cambia una clase o estado en el DOM.
- En CSS la isla queda centrada arriba (`position:absolute; top:8px; left:50%; translate:-50% 0`)
  y su ancho, alto y `border-radius` los anima un resorte:

```js
// Resorte de segundo orden (física estándar masa-resorte-amortiguador).
// f = frecuencia (rapidez), z = amortiguamiento (<1 rebota), r = respuesta inicial.
function spring(f = 2.5, z = 0.65, r = 0.1) {
  const k1 = z / (Math.PI * f), k2 = 1 / ((2 * Math.PI * f) ** 2), k3 = (r * z) / (2 * Math.PI * f);
  let y = null, yd = 0, xp = null;
  return (x, dt) => {                      // x = valor objetivo, dt en segundos
    if (y === null) { y = x; xp = x; }
    const xd = (x - xp) / dt; xp = x;
    const k2s = Math.max(k2, (dt * dt) / 2 + (dt * k1) / 2, dt * k1); // estable con dt grandes
    y += dt * yd;
    yd += (dt * (x + k3 * xd - y - k1 * yd)) / k2s;
    return y;
  };
}
// Un resorte por propiedad (ancho, alto, radio) y en cada frame:
// el.style.width = `${w(targetW, dt)}px`, etc.
```

- Para que vaya a 60 fps animando poco: un solo elemento con `will-change: width, height, border-radius`,
  con el contenido en una capa interna que aparece con `opacity` cuando la isla ya está grande.

### 2. Clics que atraviesan lo transparente (lo que DynamicWin no hace)

Con la ventana fija hay zonas transparentes que **no deben robar clics al escritorio**. En Win32:

| Opción | Veredicto |
|---|---|
| `WM_NCHITTEST` → `HTTRANSPARENT` | ❌ Solo pasa el clic a ventanas **del mismo hilo**, no al escritorio |
| `SetWindowRgn` con la forma de la isla | ⚠️ Recorta también el dibujo: bordes dentados y sin sombra ni alfa |
| **Alternar `WS_EX_TRANSPARENT` según el cursor** | ✅ Recomendada. Con `WS_EX_LAYERED` + `WS_EX_TRANSPARENT` toda la ventana deja pasar los clics; se quita ese estilo solo mientras el cursor está sobre la isla |

Esquema en Go:

```go
// JS informa del rectángulo actual de la isla (en píxeles CSS) cuando cambia su forma:
//   window.mekaIslandRect(x, y, w, h)
var islandRect atomic.Value // winRect en píxeles físicos (CSS * dpi/96)

w.Bind("mekaIslandRect", func(x, y, wd, h float64) { islandRect.Store(toPhysical(x, y, wd, h)) })

go func() { // ~60 Hz; GetCursorPos es muy barato
    over := false
    for range time.Tick(16 * time.Millisecond) {
        var p point
        procGetCursorPos.Call(uintptr(unsafe.Pointer(&p)))
        inside := cursorOverIsland(hwnd, p, islandRect.Load().(winRect)) // ScreenToClient + contains
        if inside != over {
            over = inside
            ex := getWindowLong(hwnd, gwlExStyle)
            if inside { ex &^= wsExTransparent } else { ex |= wsExTransparent }
            setWindowLong(hwnd, gwlExStyle, ex) // no hace falta Dispatch: es un estilo, no UI
        }
    }
}()
```

Con un margen de unos 6 px alrededor del rectángulo, pasar el ratón por el borde no hace parpadear el estado.

### 3. No robar el foco

- Añadir `WS_EX_NOACTIVATE`: al hacer clic en la isla, la ventana en la que trabajas no pierde el foco.
- Excepción: cuando se abre el chat de la isla y hay que escribir, quitar `WS_EX_NOACTIVATE` y llamar a
  `SetForegroundWindow`; al cerrarlo, volver a ponerlo (bindings `mekaWantsKeyboard(true/false)`).

### 4. DPI y monitores (hoy las medidas son píxeles fijos)

- **Antes de crear la ventana:** `SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)`
  (user32), o un manifiesto con `PerMonitorV2`.
- Medidas en píxeles **lógicos** × `GetDpiForWindow(hwnd)/96`. Área de trabajo del monitor de la ventana:
  `MonitorFromWindow` + `GetMonitorInfoW` (en vez de la del monitor principal).
- Manejar `WM_DPICHANGED` y `WM_DISPLAYCHANGE` para recolocar la ventana fija.
- Con 125 % de escala (habitual en portátiles), sin esto la isla sale descentrada o borrosa.

### 5. Lo que ya está bien y conviene conservar

`WS_EX_TOOLWINDOW` (fuera de Alt+Tab y la barra de tareas), `HWND_TOPMOST`, el fondo
transparente de WebView2 (`PutDefaultBackgroundColor` con alfa 0), el hook CBT para que
no haya salto al arrancar y la esquiva de la herramienta de recortes. Con la ventana fija, esa
esquiva puede ser también una animación CSS, sin mover la ventana.

## Lo que el backend puede aportar (Claude Code)

Go no tiene buen acceso a las APIs WinRT de Windows. **Python sí**, y el Core ya habla con la isla
por WebSocket. Si te sirve, el Core puede publicar estos eventos (cambio aditivo del contrato):

| Evento propuesto | Datos | Fuente en Windows |
|---|---|---|
| `system.media` | `{title, artist, app, playing, position?, duration?}` | SMTC (`GlobalSystemMediaTransportControlsSessionManager`), cualquier reproductor, no solo Spotify |
| `system.battery` | `{percent, charging}` | `psutil` / `GetSystemPowerStatus` |
| `user.media` (entrada) | `{action: "play_pause" \| "next" \| "previous"}` | La sesión de SMTC, en vez de simular teclas |

**✅ Ya disponibles (T-044, contrato 1.7).** Al conectar: `GET /v1/system`. La posición de la canción
no genera eventos (sería uno cada 2 s): avánzala en local con un temporizador mientras `playing` sea `true`.

## Orden sugerido

1. Ventana fija + isla animada con resorte (resuelve los saltos).
2. Click-through alternando `WS_EX_TRANSPARENT`.
3. DPI por monitor.
4. `WS_EX_NOACTIVATE` y el foco para el chat.
5. Eventos del sistema desde el Core, si los quieres.
