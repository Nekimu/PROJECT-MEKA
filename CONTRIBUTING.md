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
- Los canales (Telegram, MCP...) **solo hablan con MEKA Core** a través de `channels/client.py`: nunca importan `ai/` ni cargan modelos.
- Todo valor ajustable va en `config.yml`, nunca fijo en el código. Los secretos, en `.env`.
- Nunca subas tokens, `data/` (la base de datos de memoria), logs ni archivos enviados por usuarios.
- Un proveedor de IA nuevo implementa el protocolo `Provider` de `ai/providers/base.py` (`chat`, `check_health`, `unload`) y se registra en `build_provider`.

## Estructura

| Carpeta | Responsabilidad |
|---|---|
| `server/` | MEKA Core: API REST + WebSocket (FastAPI), token y control de origen |
| `core/` | Motor (`engine.py`), bus de eventos, configuración, logging, memoria, documentos y personajes |
| `ai/` | Proveedores de IA (`ai/providers/`: Ollama, Claude, Gemini), STT, TTS, prompts y utilidades de texto |
| `channels/` | Clientes del núcleo: `client.py` (HTTP), `telegram/` y `mcp/` |
| `personas/` | Paquetes de personaje |
| `scripts/` | Herramientas manuales de diagnóstico |
| `tests/` | Tests automatizados (pytest) |
