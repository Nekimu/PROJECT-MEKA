# Cómo contribuir

¡Gracias por tu interés en Project MEKA! 💖

## Entorno de desarrollo

```bash
git clone https://github.com/Nekimu/PROJECT-MEKA.git
cd PROJECT-MEKA
python -m venv venv && source venv/bin/activate   # Windows: .\venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Antes de abrir un Pull Request

```bash
ruff check .          # lint
ruff format .         # formato
pytest                # tests
```

El CI ejecuta lo mismo en Python 3.11, 3.12 y 3.13.

## Convenciones

- **Commits** en español siguiendo [Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/): `feat:`, `fix:`, `docs:`, `refactor:`, `test:`...
- La lógica pura (texto, memoria, documentos) va en módulos sin dependencias de Telegram para poder testearla.
- Todo valor ajustable va en `config.yml`, nunca fijo en el código. Los secretos, en `.env`.
- Nunca subas tokens, `memory.json`, logs ni archivos enviados por usuarios.

## Estructura

| Carpeta | Responsabilidad |
|---|---|
| `bot/` | Integración con Telegram: manejadores y arranque |
| `ai/` | LLM (Ollama), STT, TTS, prompts y utilidades de texto |
| `core/` | Configuración, logging, memoria persistente y extracción de documentos |
| `scripts/` | Herramientas manuales de diagnóstico |
| `tests/` | Tests automatizados (pytest) |
