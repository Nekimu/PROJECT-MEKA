# MEKA · Mascota de escritorio (prototipo)

Una compañera animada que flota sobre tu escritorio, reacciona a lo que hace MEKA y vive como un Tamagotchi moderno. Este prototipo es la **fase 2** de la [visión del proyecto](../docs/VISION.md).

| Navegador (con panel de pruebas) | Escritorio (ventana transparente) |
|---|---|
| Abre `web/index.html` | `cargo run` dentro de `src-tauri/` |

## Pruébala en 10 segundos

Abre [`web/index.html`](web/index.html) con doble clic. No necesita instalar nada.

Para ver también el **estilo pixel art con paleta reducida**, sírvela con un servidor local (el navegador no deja leer píxeles de archivos abiertos con `file://`):

```bash
python -m http.server 8000 --directory pet/web
# y abre http://localhost:8000
```

| Acción | Cómo |
|---|---|
| Acariciar | Clic sobre la mascota |
| Moverla | Arrastrar |
| Menú (comer, jugar, dormir, hablar, personaje, estilo) | Clic derecho o pulsación larga |
| Simular a MEKA Core | Botones del panel de pruebas |
| Ver el paso del tiempo | "Velocidad del tiempo" → 600× |

## Versión de escritorio (Tauri 2)

La misma web dentro de una ventana **transparente, sin bordes y siempre visible**. Tauri usa el navegador del sistema, así que la app pesa mucho menos que una de Electron.

**Requisitos:** [Rust](https://www.rust-lang.org/tools/install) y, en Windows, las *C++ Build Tools* de Visual Studio. WebView2 ya viene con Windows 10 y 11. En Linux necesitas además `libwebkit2gtk-4.1-dev` (ver la [guía de Tauri](https://v2.tauri.app/start/prerequisites/)).

```bash
cd pet/src-tauri
cargo run                      # abrir la mascota
cargo install tauri-cli        # una sola vez, para crear el instalador
cargo tauri build              # instalador .msi/.exe en target/release/bundle
```

En escritorio, arrastrar a la mascota **mueve la ventana** y el menú incluye "Cerrar". Además intenta conectarse sola a MEKA Core en `ws://127.0.0.1:8765/events` y reintenta en silencio mientras no exista.

## Cómo funciona

```
web/
├── index.html          # Escenario + panel de pruebas (solo navegador)
├── pet.css             # Animaciones por estado, bocadillo, menú
├── pet.js              # Máquina de estados, Tamagotchi, eventos, WebSocket
└── skins/
    ├── manifest.js     # Personajes: sprites por estado y frases
    └── <personaje>/*.webp
src-tauri/              # Envoltorio de escritorio (ventana transparente)
tools/stickerize.py     # Quita el fondo a stickers y los convierte a WebP
```

- **Estados:** `idle`, `happy`, `working`, `thinking`, `sleeping`, `eating`, `error`, `celebrate`, `sad`. Cada uno tiene su movimiento, sus partículas y su duración en `pet.js` (`FX`).
- **Tamagotchi:** energía, saciedad, ánimo y afecto evolucionan con el tiempo, también con la app cerrada (hasta 48 h). **Nunca baja de 5**: no muere ni castiga. Duerme sola si está agotada o es de madrugada y no le haces caso.
- **Desbloqueos:** la Espadachina aparece con afecto 50 y la Kitsune con 70.
- **Eventos:** acepta los eventos de MEKA Core descritos en [VISION.md](../docs/VISION.md#contrato-de-eventos). Desde la consola del navegador: `MEKA.emit({type: "agent.done", data: {summary: "¡Listo!"}})`.

## Añadir un personaje

1. Genera los stickers del personaje, idealmente uno por estado y con el mismo encuadre (ver la [guía de arte](../docs/VISION.md#guía-de-arte-para-los-personajes)).
2. Quítales el fondo y conviértelos:
   ```bash
   pip install pillow numpy
   python pet/tools/stickerize.py sticker.jpg pet/web/skins/mi_personaje/idle.webp
   ```
3. Añade el personaje a `web/skins/manifest.js`. Basta con tener `idle`: los estados sin arte pueden reutilizar ese sprite.
4. Ejecuta `pytest tests/test_pet_skins.py`, que comprueba que no falten estados, frases ni archivos.

> [!NOTE]
> El modo "pixel art" del menú es un pixelado automático para comparar estilos. Un pixel art de verdad se dibuja a mano, por ejemplo con [Pixelorama](https://orama-interactive.itch.io/pixelorama) (gratis) o Aseprite.
