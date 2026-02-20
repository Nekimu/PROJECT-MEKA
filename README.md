# Compañera Telegram - Marin Kitagawa AI Bot

Este proyecto es un bot de Telegram avanzado que simula una compañera virtual con la personalidad de Marin Kitagawa. Utiliza inteligencia artificial local para generar respuestas, clonación de voz para enviar audios, y tiene capacidades multimodales para entender imágenes y documentos.

## 🚀 Características Principales

*   **Personalidad Definida**: Marin Kitagawa (anime *Sono Bisque Doll wa Koi wo Suru*), configurada para ser cariñosa, entusiasta y atenta.
*   **Inteligencia Artificial Local**: Utiliza modelos LLM (como Gemma 3:12b) ejecutados localmente a través de Ollama.
*   **Clonación de Voz (TTS)**: 
    *   Integración con **Qwen-TTS** para clonación de voz de alta calidad (requiere GPU/CPU potente).
    *   Soporte alternativo para **Edge-TTS** (más ligero).
*   **Capacidad Multimodal**: Puede recibir y analizar fotos y documentos (PDF, TXT, etc.) para comentar sobre ellos.
*   **Memoria Contextual**: Mantiene el contexto de la conversación para respuestas coherentes.
*   **Comandos de Voz**: Puede recibir notas de voz, transcribirlas con Whisper (STT) y responder.

## 📋 Requisitos Previos

*   **Python 3.10+**
*   **Ollama**: Debe estar instalado y ejecutándose con el modelo deseado (ej. `ollama run gemma3:12b`).
*   **Telegram Bot Token**: Obtén uno a través de [@BotFather](https://t.me/BotFather).
*   **FFmpeg**: Necesario para el procesamiento de audio.
*   **Recursos de Hardware**: 
    *   Recomendado GPU con al menos 8GB VRAM para Qwen-TTS y LLM fluido.
    *   Funciona en CPU pero con latencia mayor.

## 🛠️ Instalación

1.  **Clonar el repositorio**:
    ```bash
    git clone https://github.com/tu-usuario/companera-telegram.git
    cd companera-telegram
    ```

2.  **Crear un entorno virtual** (recomendado):
    ```bash
    python -m venv venv
    # En Windows:
    .\venv\Scripts\activate
    # En Linux/Mac:
    source venv/bin/activate
    ```

3.  **Instalar dependencias**:
    ```bash
    pip install -r requirements.txt
    ```
    *Nota: Para soporte de GPU con PyTorch, verifica la instalación correcta según tu tarjeta gráfica en [pytorch.org](https://pytorch.org).*

4.  **Configuración**:
    *   Copia el archivo de ejemplo:
        ```bash
        cp .env.example .env
        ```
    *   Edita `.env` y pega tu **Token de Telegram**:
        ```
        TELEGRAM_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
        ```
    *   Revisa `config.yml` para ajustar el modelo de Ollama, parámetros de voz y rutas.

## ▶️ Ejecución

Asegúrate de que Ollama esté corriendo:
```bash
ollama serve
```

Inicia el bot:
```bash
python run.py
```

## 📂 Estructura del Proyecto

*   `run.py`: Punto de entrada principal.
*   `bot/`: Lógica del bot de Telegram (handlers, comandos).
*   `ai/`: Servicios de IA (Ollama, STT Whisper, TTS).
*   `core/`: Configuración, logger y utilidades.
*   `audio/`: Archivos de referencia para clonación de voz.
*   `temp_audio/`: Almacenamiento temporal de notas de voz (ignorado en git).

## ⚠️ Notas de Seguridad

*   Nunca subas tu archivo `.env` al repositorio público.
*   El archivo `.gitignore` ya está configurado para excluir información sensible.

## 🤝 Contribución

Si deseas contribuir, por favor abre un Pull Request o crea un Issue para discutir cambios mayores.

## 📄 Licencia

Este proyecto está bajo la licencia MIT.
