# Evaluación de Rendimiento, Estabilidad y Consumo en Segundo Plano · MEKA Desktop

Este documento resume la evaluación empírica de **MEKA Desktop (`MEKA.exe` + Microsoft Edge WebView2 + MEKA Core en Python)** ejecutándose en segundo plano sobre Windows, las medidas implementadas para arranque con el sistema, notificaciones, protección anti-cuelgues, la comparativa directa **Baseline vs. Post-Optimización** y su contraste frente a arquitecturas de referencia de la industria.

---

## 1. Arquitectura en Segundo Plano y Protecciones Implementadas

Para garantizar ejecución continua desde el inicio de sesión sin cuelgues ni procesos huérfanos, el cliente nativo en Go (`pet/desktop/`) integra:

| Componente | Archivo fuente | Comportamiento implementado |
|---|---|---|
| **Autoarranque con Windows** | [startup_windows.go](../pet/desktop/startup_windows.go) | Registra/consulta `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` (`MEKA` = `"<exe>" --startup`). Exposición en UI (`#autoStartToggleBtn`), CLI (`--enable-startup` / `--disable-startup`) y bandeja. |
| **App de Notificaciones en 2.º Plano** | [startup_windows.go](../pet/desktop/startup_windows.go) | Asigna `AppUserModelID` (`MEKA.Desktop.Companion`) al proceso vía `shell32.dll` (`SetCurrentProcessExplicitAppUserModelID`) y registra `HKCU\Software\Classes\AppUserModelId\MEKA.Desktop.Companion` + `HKCU\Software\Microsoft\Windows\CurrentVersion\Notifications\Settings\MEKA.Desktop.Companion` (`Enabled=1`, `ShowInActionCenter=1`). |
| **Bandeja del Sistema (System Tray)** | [tray_windows.go](../pet/desktop/tray_windows.go) | Ventana top-level oculta (`WS_POPUP` / `WS_EX_TOOLWINDOW`) con `Shell_NotifyIconW`, recuperación automática ante `TaskbarCreated`, respuesta limpia a `WM_QUERYENDSESSION`/`WM_ENDSESSION` y menú contextual (*Mostrar / Centrar MEKA*, *Expandir / Colapsar Dynamic Island*, *Iniciar con Windows*, *Reiniciar MEKA Core*, *Abrir carpeta de logs*, *Salir de MEKA*). |
| **Watchdogs Anti-Cuelgues (Arranque/Cierre)** | [watchdog_windows.go](../pet/desktop/watchdog_windows.go) | Verificación previa del servidor loopback (`/healthz`), recuperación de pánicos con log rotado (`%LOCALAPPDATA%\MEKA\desktop.log`, máx. 1 MB), **Windows Job Object** (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`) para matar automáticamente el árbol de `python.exe` si `MEKA.exe` cae, sonda periódica a `/v1/health` (3 fallos → reinicio de Core con backoff `4s..60s` y circuit breaker `>=5` en `60s`), watchdog de arranque WebView2 (`mekaNotifyReady` / 15 s) y `shutdownCoordinator` idempotente con límite duro de 4 s. |
| **Optimizaciones de CPU y Caché** | [window_windows.go](../pet/desktop/window_windows.go), [main.go](../pet/desktop/main.go) | Intervalo adaptativo del monitor de click-through (`16ms` activo / `32ms` reposo cerca del borde / `48ms` lejos / `80ms` en pantalla completa), conservación inteligente de `Cache`/`Code Cache` de WebView2 mediante huella (`webview-cache-stamp.txt`), y cambio de `--core-mode` por defecto de `all` a `core` (evita levantar bot de Telegram innecesario en escritorio). |

---

## 2. Metodología de Medición (Entorno Real)

Las mediciones se ejecutaron con un script reproducible en PowerShell (**20 muestras** a intervalos de **1 segundo** tras **2 segundos** de estabilización inicial después del lanzamiento) recorriendo todo el árbol de procesos (`Get-ProcessTreeIds` por `ParentProcessId`):

- **Equipo / SO**: Windows 11 (`Build 26100`), **8 núcleos lógicos**, ejecutable empaquetado único `MEKA.exe`.
- **Escenario activo simulado (ambas pruebas)**: Spotify ejecutándose con pista `"Write This Down (Instrumental)"`, batería al `37%`, `8` notificaciones en cola y **Ollama apagado** en `127.0.0.1:11434` (condición real más exigente para el arranque en frío de MEKA Core).
- **Nota sobre memoria en Windows**: se reporta tanto **Working Set (`WS`)** (páginas activas en RAM física, que pueden incluir memoria compartida con otros Chromium/Edge o bibliotecas del sistema) como **Memoria Privada (`Priv`)** (compromiso exclusivo del proceso, indicador más fiel del impacto real de memoria).

---

## 3. Resultados Comparativos: Baseline vs. Post-Optimización

### 3.1 Arranque, Binario y Cierre Anti-Huérfanos

| Métrica | Baseline (`MEKA.exe` previo) | Post-Optimización (`MEKA.exe` actual) | Cambio | Observación |
|---|---:|---:|---:|---|
| Tamaño ejecutable único (`MEKA.exe`) | `7,762,432 B` (`7.40 MiB`) | `8,391,168 B` (`8.00 MiB`) | `+628 KB` | Incluye Tray Win32, registro Startup/AUMID y watchdogs. |
| Spawn de procesos WebView2 | `4,610 ms` | **`3,620 ms`** | **`-21.5%` (`-990 ms`)** | Conservación de caché GPU/HTTP de WebView2 entre ejecuciones. |
| Carga DOM UI interactiva (`desktop.log`) | *No instrumentado* | **`443 ms`** | Instrumentado | Registrado por `[startup] Interfaz lista en 443ms`. |
| Core `/v1/health` `200 OK` (arranque frío) | `>15,000 ms` *(timeout sonda)* | **`15,076 ms`** | Capturado | Incluye ~8 s de espera por Ollama offline en `:11434`. |
| Método de cierre medido | `Stop-Process -Force` *(sin HWND taskbar)* | **`MainWindow.CloseMainWindow` (`WM_CLOSE`)** | Cierre elegante | Señal Win32 limpia + `shutdownCoordinator`. |
| Duración de cierre completo | `128 ms` *(forzado)* | **`351 ms`** *(elegante)* | Determinista | Limpia tray, WebView2 y árbol Python Core sin colgarse. |
| Procesos huérfanos tras cerrar | `0` | **`0`** | **`0` huérfanos** | Job Object `KILL_ON_JOB_CLOSE` + `taskkill /T /F` de respaldo. |

### 3.2 Consumo en Segundo Plano (Promedio 20 s y Régimen Estable s 10–20)

| Grupo de procesos | Métrica | Baseline | Post-Optimización | Delta |
|---|---|---:|---:|---:|
| **Árbol completo (`10` procs)** | Working Set (`WS`) promedio | `597.11 MB` | `592.64 MB` | `-4.47 MB` |
| **Árbol completo (`10` procs)** | Memoria Privada (`Priv`) promedio | `572.28 MB` | **`556.20 MB`** | **`-16.08 MB` (`-2.8%`)** |
| **Árbol completo (`10` procs)** | Memoria Privada pico (20 s) | `585.22 MB` | **`572.72 MB`** | **`-12.50 MB`** |
| **Árbol completo (`10` procs)** | CPU promedio 20 s *(8 núcleos)* | `6.61%` | `6.93%` *(incluye pico `s=2`)* | `+0.32 pp` |
| **Árbol completo (`10` procs)** | **CPU régimen estable (s 10–20)** *(8 núcleos)* | `7.11%` | **`6.09%`** | **`-1.02 pp` (`-14.3%`)** |
| **Árbol completo (`10` procs)** | Handles / Hilos promedio | `4547.55` / `210.75` | **`4532.55`** / **`209.20`** | `-15` handles / `-1.55` hilos |
| **`MEKA.exe` (Host Go, 1 proc)** | WS / Priv promedio | `46.90 MB` / `57.35 MB` | `48.07 MB` / `58.21 MB` | `+1.17 MB` / `+0.86 MB` |
| **`MEKA.exe` (Host Go, 1 proc)** | **CPU promedio (1 núcleo)** | `2.10%` | **`0.13%`** | **`-93.8%` CPU del host Go** |
| **`msedgewebview2.exe` (6 procs)** | WS / Priv promedio | `430.48 MB` / `212.05 MB` | `440.29 MB` / **`209.29 MB`** | `+9.81 MB` WS / `-2.76 MB` Priv |
| **`msedgewebview2.exe` (6 procs)** | CPU 20 s / **CPU estable s 10–20** *(1 núcleo)* | `48.98%` / `53.77%` | `52.94%` / **`46.51%`** | `-7.26 pp` en régimen estable |
| **`python.exe` Core (2 procs)** | **WS / Priv promedio** | `112.65 MB` / `301.72 MB` | **`96.66 MB` / `287.55 MB`** | **`-15.99 MB` (`-14.2%` WS)** / `-14.17 MB` Priv |
| **`python.exe` Core (2 procs)** | CPU promedio (1 núcleo) | `1.79%` | `2.36%` | `+0.57 pp` |

> [!NOTE]
> El pico puntual de CPU en la ejecución optimizada (`17.81%` total / `142.48%` de 1 núcleo en `s=2`) ocurrió exactamente al completarse la hidratación inicial de WebView2 con la música activa (`GET /v1/system`, `/v1/system/media/artwork` y WebSocket `/v1/events`); en los últimos 10 segundos medidos (**s 10–20**), el consumo bajó a **`6.09%` total** frente a **`7.11%`** en el baseline.

---

## 4. Comparativa frente a Estándares y Aplicaciones de Referencia

> [!IMPORTANT]
> Los rangos de esta tabla para terceros son **valores típicos de referencia publicados en la industria/documentación técnica** (no ejecutados localmente en la misma sesión de benchmark). Se comparan contra los datos **medidos directamente** de MEKA.

| Arquitectura / Aplicación | RAM típica en 2.º plano | CPU típica en reposo | Arranque en frío | Notas arquitectónicas |
|---|---:|---:|---:|---|
| **App Win32 / Go nativa pura** *(ej. PowerToys Run / bandejas C++ o Go sin navegador)* | `15 – 45 MB` | `< 0.2%` | `< 0.3 s` | Sin motor web ni runtime de Python. El propio binario Go de MEKA ya cae aquí (`58.2 MB` Priv, **`0.13%` de 1 núcleo**). |
| **Cliente Tauri / Go + WebView2 UI mínima** *(sin backend Python)* | `90 – 180 MB` | `0.2% – 1.5%` | `0.8 – 2.0 s` | Comparte Edge WebView2 del SO; solo paga ~4–6 procesos Chromium cuando hay animaciones GPU activas. |
| **Electron típico en reposo** *(ej. Discord, Slack, Spotify Desktop)* | `250 – 550 MB` *(por instancia)* | `0.5% – 3.0%` | `2.0 – 5.0 s` | Empaqueta Chromium + Node.js completo por cada app (~120+ MB solo en disco). |
| **MEKA Desktop completo medido** *(Go + WebView2 animando 60fps + FastAPI Python Core + embeddings/TTS)* | **`556 MB` Priv** (`209 MB` WebView2 + `288 MB` Python + `58 MB` Go) | **`6.09%`** *(8 núcleos, con Dynamic Island animando música)* | `3.62 s` UI / `15.08 s` Core | Integra **dos motores pesados** en paralelo: compositor transparente Chromium WebView2 con música activa + servidor Python con FastAPI/Uvicorn/TTS/STT/Ollama. |

---

## 5. Hallazgos Principales y Cuellos de Botella Identificados

El perfilado demuestra que **`MEKA.exe` ya NO es el cuello de botella** (`0.13%` CPU de 1 núcleo). Casi el **90% de los recursos** se dividen en tres puntos concretos:

1. **Compositor GPU + Render WebView2 (`~440 MB` WS, `46%–53%` de 1 núcleo)**:
   - Incluso estando replegada en modo pill/Dynamic Island, cuando hay música en reproducción activa (como Spotify en el benchmark), el frontend mantiene activas animaciones continuas CSS/DOM (`backdrop-filter: blur(...)`, halos RGB transicionales, ecualizador de barras y marquee de pista) sobre una ventana transparente `DwmExtendFrameIntoClientArea`, obligando al compositor DWM + GPU de Chromium a repintar a ~60 FPS continuos.
2. **Backend Python Core (`~288 MB` Priv, `~15 s` arranque en frío)**:
   - El servidor FastAPI (`run.py core`) importa stacks pesados al inicio (`uvicorn`, `edge-tts`, dependencias de `faster-whisper`/STT, memoria semántica) y realiza sondeo síncrono contra Ollama (`127.0.0.1:11434`), bloqueando la disponibilidad de `/v1/health` ~8 s cuando Ollama no está ejecutándose.
3. **Tráfico HTTP periódico UI ↔ Core (observado en `core-desktop.log`)**:
   - Durante el muestreo, además del `GET /v1/health` cada 5 s del watchdog de Go, el frontend realizó polling periódico cada ~2–3 s sobre `GET /v1/system` y `GET /v1/system/notifications` además del canal WebSocket `/v1/events`.

---

## 6. Hoja de Ruta Recomendada para Futuras Optimizaciones

Si se busca bajar el consumo de MEKA en segundo plano por debajo de `2%` CPU total y `~300 MB` Privados en reposo:

1. **Modo Reposado / Throttling visual en WebView2 cuando la píldora está colapsada (`>= 10 s` sin interacción)**:
   - Pausar `backdrop-filter` pesado, bajar el ritmo de actualización de barras de audio cuando la ventana no tiene hover ni notificaciones nuevas, o reducir sprites/marquees cuando el usuario entra en modo AFK/pantalla completa. *(Impacto estimado: reduciría el CPU de `msedgewebview2.exe` en reposo de ~46% a <5% de 1 núcleo).*
2. **Polling adaptativo del watchdog y frontend cuando WebSocket está conectado**:
   - Cuando `/v1/events` WebSocket está abierto y sano, espaciar `GET /v1/health` de Go de `5 s` a `15 s` y depender de push WebSocket antes que sondear `/v1/system` cada `2–3 s`.
3. **Diferir probing de Ollama / carga de servicios opcionales en MEKA Core** *(trabajo futuro coordinado en `core/` / `ai/`)*:
   - Levantar Uvicorn + `/v1/health` antes de probar `localhost:11434`, bajando el arranque en frío de Core de ~15 s a `< 3 s` cuando Ollama no se usa.
