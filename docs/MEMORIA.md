# Memoria de MEKA: JSON, SQLite o PostgreSQL

Evaluación hecha en noviembre de 2026 para elegir dónde guarda MEKA sus recuerdos y el historial de cada conversación. **Decisión: SQLite**, ya implementado en [`core/memory.py`](../core/memory.py).

## Qué necesita guardar MEKA

| Dato | Volumen esperado | Acceso |
|---|---|---|
| Recuerdos por usuario ("recuerda esto: …") | Cientos o miles de frases | Búsqueda por palabras en cada mensaje que pregunta por el pasado |
| Historial por conversación | Los últimos 20 mensajes de cada chat | Lectura en cada respuesta, escritura tras cada respuesta |
| Más adelante: memoria semántica | Un vector por recuerdo | Búsqueda por significado |

Hay un solo proceso que escribe (MEKA Core) y uno o pocos usuarios. Todo corre en un PC doméstico, a veces con 16 GB de RAM compartidos con Ollama.

## Comparativa

| | JSON (antes) | **SQLite (elegido)** | PostgreSQL |
|---|---|---|---|
| Instalación | Nada | **Nada**: `sqlite3` viene con Python | Un servidor aparte (o Docker), usuario, contraseña y copias |
| RAM en reposo | El archivo entero cargado | **~1 MB** | 30–100 MB por el servidor |
| Escritura | Reescribe el archivo entero en cada recuerdo | **Una fila**, transaccional (WAL) | Una fila, transaccional |
| Seguridad ante cortes | Escritura atómica a mano | **ACID** de serie | ACID |
| Búsqueda | Recorre todos los recuerdos en Python | **FTS5**: índice de texto completo, ignora tildes, ordena por relevancia (BM25) | `tsvector` con diccionario español, muy completo |
| Historial persistente | No (se perdía al reiniciar) | **Sí** | Sí |
| Varios procesos escribiendo a la vez | No | Un escritor cada vez (suficiente: solo escribe MEKA Core) | Sí, sin límite práctico |
| Memoria semántica | No | Extensión `sqlite-vec` | Extensión `pgvector` (la más madura) |
| Copia de seguridad | Copiar el archivo | **Copiar el archivo** (o `.backup`) | `pg_dump` |
| Privacidad | Local | **Local, un archivo** | Local si lo instalas tú; si es gestionado, en la nube |

## Por qué SQLite

1. **Encaja con "local primero".** Un archivo (`data/meka.db`) que puedes copiar, cifrar o borrar. Sin puertos abiertos ni contraseñas.
2. **Cero instalación.** Funciona igual en Windows, macOS y Linux, también en la Raspberry Pi o el ESP32-S3 + PC de la figura del Meka.
3. **El cuello de botella es la IA, no la base de datos.** Una respuesta de Ollama tarda segundos; una consulta en SQLite tarda microsegundos. PostgreSQL no aportaría velocidad perceptible.
4. **La búsqueda mejora.** FTS5 ignora tildes ("cancion" encuentra "canción"), busca por prefijo ("color" encuentra "colores") y ordena por relevancia, sin cargar todos los recuerdos en memoria.
5. **El historial sobrevive a los reinicios.** Antes, reiniciar el bot borraba el contexto de todas las conversaciones.

## Cuándo pasar a PostgreSQL

- Varios equipos escriben a la vez en la misma memoria (por ejemplo, un MEKA Core por dispositivo que comparte recuerdos con los demás).
- MEKA pasa a ser un servicio para muchas personas.
- La memoria semántica crece a cientos de miles de vectores y conviene `pgvector` con índices HNSW (hoy la búsqueda recorre los vectores del usuario, de sobra para miles).

El cambio está acotado: todo el acceso pasa por la clase `MemoryStore` (`add_fact`, `get_facts`, `search`, `clear`, `add_messages`, `recent_messages`...). Un `PostgresMemoryStore` con los mismos métodos bastaría, sin tocar el motor ni los canales.

## Cómo está implementado

- **Tablas:** `facts` (recuerdos, únicos por usuario), `facts_fts` (índice FTS5 que mantienen unos *triggers*) y `messages` (historial por sesión, recortado a `ai.history_size`).
- **Versión del esquema:** `PRAGMA user_version`, para migraciones futuras.
- **Concurrencia:** modo WAL y un *lock* por conexión. El servidor es asíncrono, pero las operaciones duran microsegundos.
- **Migración automática:** al arrancar, si existe el antiguo `memory.json`, MEKA importa sus recuerdos y lo renombra a `memory.json.migrated`. Los recuerdos del formato más antiguo, sin dueño, se asignan al primer ID de `ALLOWED_USER_IDS`; sin ese ID, el archivo se deja intacto hasta que lo configures.
- **Sin FTS5** (un SQLite compilado sin él, muy raro): se usa una búsqueda simple por palabras clave.
- **Configuración:** `paths.memory_db` (ruta), `memory.persist_history` (historial en disco o solo en RAM) y `memory.semantic.*` (ver abajo).

## Memoria semántica

MEKA recuerda también **por significado**: "¿qué te conté de mi mascota?" encuentra "mi perro se llama Toby" aunque no compartan ninguna palabra.

| Pieza | Elección | Por qué |
|---|---|---|
| Embeddings | [`embeddinggemma`](https://ollama.com/library/embeddinggemma) en Ollama | Local, multilingüe y ligero (~600 MB); se descarga de la RAM tras usarlo (`keep_alive: 0`) |
| Almacén | Tabla `fact_vectors` en la misma `meka.db` | Sin otra base de datos; los vectores se borran con su recuerdo |
| Similitud | [`sqlite-vec`](https://github.com/asg017/sqlite-vec) (`vec_distance_cosine`, en C) | Si no está instalado o Python no admite extensiones, se calcula en Python |

**Cómo funciona:**

1. Cada recuerdo se convierte en un vector la primera vez que hace falta buscar. Así se indexan solos los recuerdos nuevos, los migrados del JSON y los de un modelo anterior si cambias `memory.semantic.model`.
2. **Si preguntas** ("¿te acuerdas…?", "¿recuerdas…?"), MEKA junta los recuerdos con similitud ≥ `min_similarity` (0,35) y los que coinciden por palabras (FTS5).
3. **Si no preguntas**, añade al contexto solo los recuerdos muy relacionados (similitud ≥ `auto_recall_similarity`, 0,6). Si le cuentas "hoy saqué a pasear al perro", ya sabe que se llama Toby. Con `0` se desactiva y se ahorra una llamada a Ollama por mensaje.
4. **Si Ollama no responde o falta el modelo**, avisa una vez en la consola y sigue buscando por palabras. Nada se rompe.

**Calibrar los umbrales.** Dependen del modelo. Para ver las similitudes reales con tus recuerdos:

```bash
ollama pull embeddinggemma
python -m scripts.semantic_check "¿qué te conté de mi mascota?"                    # frases de ejemplo
python -m scripts.semantic_check "¿qué te conté de mi mascota?" --user 123456789   # tus recuerdos
```

Sube `min_similarity` si aparecen recuerdos que no vienen al caso y bájalo si se le escapan. Haz lo mismo con `auto_recall_similarity`.

**Otros modelos.** `nomic-embed-text` (inglés sobre todo) o `bge-m3` (multilingüe, más pesado) también funcionan. Cambia `memory.semantic.model` y sus prefijos (`query_prefix` y `document_prefix`; los de `nomic-embed-text` son `search_query: ` y `search_document: `). Los vectores se recalculan solos.
