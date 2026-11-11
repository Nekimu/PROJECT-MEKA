# Pruebas de la API con Postman

Colección de pruebas de punta a punta contra un **MEKA Core en marcha** (`python run.py core`).
Complementa a `pytest`, que prueba el código con modelos simulados; esto prueba el servidor real
con el cerebro real (Ollama, Claude o Gemini, según `config.yml`).

| Archivo | Qué es |
|---|---|
| `meka-core.postman_collection.json` | La colección: 24 peticiones y 32 comprobaciones en 6 carpetas |
| `local.postman_environment.json` | Entorno `MEKA local`: `baseUrl` y `token` |
| `generar_coleccion.py` | Genera los dos JSON. **Edita este archivo**, no el JSON |

## Ejecutar

```bash
npm install -g postman-cli          # una sola vez
python run.py core                  # en otra terminal
cd tests/postman
postman collection run meka-core.postman_collection.json -e local.postman_environment.json
```

Con `MEKA_API_TOKEN` configurado, pásalo sin guardarlo en el archivo:
`--env-var token=TU_TOKEN`. También puedes importar ambos JSON en la app de Postman.

## Qué prueba

| Carpeta | Comprobaciones |
|---|---|
| 1 · Estado | `/v1/health` y `/v1/contract` públicos y con la misma versión; el personaje nunca expone su prompt |
| 2 · Memoria | Recuerdos públicos y privados; `include_private=false` (lo que ven MCP y Telegram) nunca los devuelve |
| 3 · Conversación y privacidad | Chat normal, `private`, sesión que sigue privada, dato sensible detectado, reinicio |
| 4 · Eventos | `POST /v1/events` validado contra el contrato; `agent.confirm` a mano se rechaza |
| 5 · Permisos | Pendientes, id inexistente (404) y permiso sin respuesta = **no** |
| 6 · Registro y seguridad | `/v1/runs` sin texto de conversaciones; una web ajena (Origin) recibe 403 |

Usa el usuario de memoria `postman-test` y lo borra al final: **no toca tus recuerdos**.
El chat con el modelo ligero de pruebas tarda unos segundos por petición (~1 minuto en total).

Al añadir una ruta o cambiar el contrato, añade aquí su prueba (`generar_coleccion.py`) y vuelve
a generar la colección.
