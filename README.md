# Project MEKA — Marin Kitagawa AI Bot 💖

Bot de Telegram que simula una compañera virtual con la personalidad de **Marin Kitagawa** (*Sono Bisque Doll wa Koi wo Suru*). Funciona con **IA local** (Ollama), **clonación de voz** y capacidades **multimodales** para entender imágenes y documentos — todo ejecutándose en tu propia máquina, sin enviar tus conversaciones a servicios externos.

> ⚠️ Proyecto personal con fines educativos y de entretenimiento. No está afiliado a los autores de la obra original.

---

## 🚀 Características

- **Personalidad definida**: Marin Kitagawa, configurada mediante un *system prompt* para ser cariñosa, entusiasta y atenta.
- **IA 100% local**: respuestas generadas con modelos LLM vía [Ollama](https://ollama.com) (por defecto `gemma3:12b`).
- **Clonación de voz (TTS)**: 
  - **Qwen-TTS** para clonar una voz de referencia (mayor calidad, requiere más recursos).
  - **Edge-TTS** como alternativa ligera (requiere conexión a internet).
- **Multimodal**: recibe y analiza **fotos** y **documentos** (PDF, DOCX, XLSX, TXT) y los comenta.
- **Comandos de voz (STT)**: transcribe notas de voz con [Whisper](https://github.com/openai/whisper) y responde.
- **Memoria contextual**: mantiene el historial reciente de la conversación.
- **Memoria persistente**: guarda hechos cuando le dices *"recuerda esto: …"* y los recupera al preguntarle.
- **Gestión estricta de RAM**: descarga modelos tras cada interacción para funcionar en hardware modesto.

---

## 📋 Requisitos previos

- **Python 3.10+**
- **[Ollama](https://ollama.com)** instalado y en ejecución con el modelo deseado (`ollama pull gemma3:12b`).
- **Token de Telegram** generado con [@BotFather](https://t.me/BotFather).
- **FFmpeg** disponible en el `PATH` (necesario para audio).
- **Hardware**: se recomienda GPU con ≥8 GB de VRAM para fluidez. Funciona en CPU con mayor latencia.

---

## 🛠️ Instalación

1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/Nekimu/PROJECT-MEKA.git
   cd PROJECT-MEKA
   ```

2. **Crear un entorno virtual** (recomendado):
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   ```

3. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```
   > Para soporte de GPU con PyTorch, instala la versión adecuada según tu tarjeta desde [pytorch.org](https://pytorch.org).
   >
   > El motor **Qwen-TTS** requiere además `torch` y el paquete `qwen-tts`, que no se incluyen por defecto al ser dependencias pesadas. Si no los necesitas, usa el motor `edge-tts` en `config.yml`.

4. **Configurar el token** (se carga desde `.env`, **nunca** se sube al repo):
   ```bash
   cp .env.example .env
   ```
   Edita `.env` y pega tu token:
   ```
   TELEGRAM_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

5. **Ajustar `config.yml`** (opcional): modelo de Ollama, motor de voz, audio de referencia, etc.

---

## ▶️ Ejecución

1. Asegúrate de que Ollama esté corriendo:
   ```bash
   ollama serve
   ```
2. Inicia el bot:
   ```bash
   python run.py
   ```

Al arrancar, el bot ejecuta un diagnóstico no bloqueante de Ollama, TTS y STT, y queda a la espera de mensajes en Telegram.

---

## 💬 Uso

| Acción | Cómo |
|--------|------|
| Iniciar | Envía `/start` al bot |
| Chatear | Escríbele cualquier mensaje de texto |
| Nota de voz | Envía un audio; lo transcribe y responde |
| Imagen | Envía una foto; la analiza y comenta |
| Documento | Envía un PDF, DOCX, XLSX o TXT; lo lee y comenta |
| Recordar un dato | *"recuerda esto: mi color favorito es el azul"* |
| Recuperar un dato | *"¿recuerdas mi color favorito?"* |

---

## ⚙️ Configuración (`config.yml`)

```yaml
ai:
  model: "gemma3:12b"        # Modelo de Ollama
  base_url: "http://localhost:11434"
  temperature: 0.8

tts:
  enabled: true
  engine: "qwen-tts"         # qwen-tts | edge-tts | piper
  qwen:
    ref_audio: "audio/YotsubaAudio.wav"  # Voz de referencia a clonar
    device: "cpu"
```

---

## 📂 Estructura del proyecto

```
PROJECT-MEKA/
├── run.py              # Punto de entrada
├── bot/                # Lógica de Telegram (main, handlers)
├── ai/                 # Servicios de IA (service, stt, tts, prompts)
├── core/               # Configuración, logger y memoria persistente
├── audio/              # Audios de referencia para clonación de voz
├── docs/screenshots/   # Capturas de pantalla del proyecto
├── tests/              # Scripts de prueba de TTS/STT/Ollama
├── config.yml          # Configuración general
├── .env.example        # Plantilla de variables de entorno
└── requirements.txt    # Dependencias
```

Carpetas generadas en tiempo de ejecución (ignoradas por git): `temp_audio/`, `temp_media/`, `logs/`, `memory.json`.

---

## 📸 Capturas de pantalla

Coloca tus capturas en `docs/screenshots/` y se mostrarán aquí:

| Conversación | Nota de voz | Análisis multimodal |
|:---:|:---:|:---:|
| ![Chat](docs/screenshots/chat.png) | ![Voz](docs/screenshots/voz.png) | ![Multimodal](docs/screenshots/multimodal.png) |

> Reemplaza `chat.png`, `voz.png` y `multimodal.png` por tus propias imágenes (PNG/JPG).

---

## 🔒 Seguridad y privacidad

- El **token** se carga desde `.env`, que está excluido por `.gitignore`. **Nunca lo subas al repositorio.**
- Los **archivos que los usuarios envían** (fotos/documentos) se guardan en `temp_media/` (ignorado por git) y se eliminan tras procesarse. **No se almacenan ni se versionan.**
- Las notas de voz se procesan en `temp_audio/` con nombres únicos y se borran al terminar.
- Toda la inferencia de IA ocurre **en local** vía Ollama; tus conversaciones no salen de tu máquina (salvo que uses `edge-tts`, que sintetiza voz en línea).

---

## 🤝 Contribución

¿Quieres aportar? Abre un *Issue* para discutir cambios mayores o envía un *Pull Request*.

## 📄 Licencia

Distribuido bajo la licencia MIT.
