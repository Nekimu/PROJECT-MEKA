# Personajes de MEKA

MEKA es una sola identidad técnica con **personajes intercambiables**. Cada carpeta de aquí es un paquete con la personalidad, el nombre, la voz y las frases de un personaje. El código no menciona a ninguno: cambiar de personaje es cambiar una línea de configuración.

| Carpeta | Nombre | Inspiración | Estilo |
|---|---|---|---|
| `dva/` | MEKA | D.Va / Hanna Song (*Overwatch*) | Gamer, segura y competitiva; rigurosa en lo serio. **Por defecto.** |
| `marin/` | Marin | Marin Kitagawa (*Sono Bisque Doll wa Koi wo Suru*) | Gyaru, otaku del cosplay, cariñosa |
| `yotsuba/` | Yotsuba | Yotsuba Nakano (*Go-Tōbun no Hanayome*) | Optimista, servicial y deportista |

Todos son **interpretaciones originales inspiradas** en esos personajes: no afirman ser los oficiales ni imitan sus voces.

## Cambiar de personaje

En `config.yml`:

```yaml
persona: "yotsuba"
```

O sin tocar el archivo, en `.env` o en la terminal:

```bash
MEKA_PERSONA=marin python run.py
```

Si el nombre no existe, el bot avisa en la consola y arranca con `dva`.

## Crear un personaje nuevo

1. Copia una carpeta existente: `cp -r personas/dva personas/mi_personaje`.
2. Escribe su personalidad en **`persona.md`**: idioma, estilo, comportamiento y límites. No hace falta explicar el formato de los mensajes ni las etiquetas `[AUDIO]`, `[STICKER]` y `[GIF]`: MEKA añade esas reglas a todos los personajes.
3. Ajusta **`persona.yml`**:

```yaml
name: Mi Personaje          # Cómo se llama en el bot y en los registros
inspiration: "..."          # De dónde viene la idea
description: "..."          # Una línea
avatar: meka                # Personaje de la mascota de escritorio (pet/web/skins)

voice:                      # Voz de edge-tts; sustituye a la de config.yml
  voice: "es-MX-DaliaNeural"   # Lista de voces: python -m scripts.list_edge_voices es-MX
  rate: "+0%"
  pitch: "+0Hz"

lines:                      # Frases fijas del bot. Puede haber varias: se elige una al azar
  greet: ["¡Hola, {user}!"]  # {user} = nombre del usuario
  forget_done: ["Borré {count} recuerdo(s)."]  # {count} = cantidad
  # ...el resto de claves, ver la tabla
```

4. Comprueba que esté completo con `pytest tests/test_persona.py`.

### Frases obligatorias

| Clave | Cuándo se usa |
|---|---|
| `greet` | `/start` (admite `{user}`) |
| `reset` | `/reset` |
| `memories_empty` · `memories_header` | `/recuerdos` sin recuerdos y con ellos |
| `forget_done` · `forget_none` | `/olvidar` (`forget_done` admite `{count}`) |
| `voice_ack` · `voice_fail` | Al recibir una nota de voz y si no se entiende |
| `media_error` · `unsupported_file` · `file_too_big` | Problemas con fotos y documentos |
| `sticker_reply` | Cuando le envías un sticker |
| `error` · `vision_error` · `empty_reply` | Fallos o respuestas vacías del modelo de IA |
| `analyze_document` · `analyze_image` | Petición por defecto si envías un archivo sin texto |

Todas admiten también `{name}`, el nombre del personaje.

## Voz

Por defecto cada personaje usa una voz de **edge-tts**, configurada en su `persona.yml`. Si quieres clonar una voz con Qwen3-TTS, usa **solo tu propia voz o una con permiso**, guárdala en `voices/` (ignorada por git) y apúntala en `tts.qwen.ref_audio` de `config.yml`. No clones voces de actrices o actores de doblaje.
