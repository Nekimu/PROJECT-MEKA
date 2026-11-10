"""Prompts del sistema comunes a todos los personajes.

La personalidad no vive aquí: está en `personas/<id>/persona.md`. Este módulo solo
añade las reglas de formato que necesita MEKA (mensajes múltiples y etiquetas
multimedia) y las plantillas de visión, documentos y memoria.
"""

# Reglas que el bot necesita para dividir mensajes y enviar audio/stickers/GIFs.
# Se añaden después de la personalidad de cualquier personaje.
FORMAT_RULES = """
FORMATO DE RESPUESTA (reglas del sistema MEKA)
- Escribe bloques de 2 o 3 frases cortas; ni mensajes de una palabra ni párrafos gigantes.
- Usa el delimitador "---" para separar mensajes distintos o cambios de tema; no lo uses en cada frase.
- Puedes añadir [STICKER], [GIF] o [AUDIO] al final de una frase en momentos de impacto real. Nunca envíes la etiqueta sola.
- Si el usuario pide explícitamente que le hables por audio o en una nota de voz, añade [AUDIO] al final de cada frase de esa respuesta.
- Ejemplo: "¡Hola! Me parece buena idea... --- Te cuento cómo me fue hoy. [AUDIO]"
"""

# Para imágenes: análisis útil con el estilo del personaje, sin etiquetas de audio.
VISION_TEMPLATE = (
    "Eres {name}. El usuario te ha enviado una imagen para que la analices. "
    "Descríbela con tu personalidad, pero sé útil y precisa con la información. "
    "NO generes etiquetas como [AUDIO], solo texto."
)

DOCUMENT_PROMPT_TEMPLATE = (
    "Te envié el documento «{file_name}». Este es su contenido{truncated_note}:\n\n"
    "<<<DOCUMENTO\n{content}\nDOCUMENTO>>>\n\n{request}"
)

MEMORY_CONTEXT_TEMPLATE = (
    "\n\n[SISTEMA: Recuerdos relevantes encontrados en tu memoria persistente:\n{memories}]"
)


def build_system_prompt(persona_prompt: str) -> str:
    """Personalidad del personaje + reglas de formato comunes."""
    return f"{persona_prompt.strip()}\n{FORMAT_RULES}"


def build_vision_prompt(name: str) -> str:
    return VISION_TEMPLATE.format(name=name)


def build_document_prompt(file_name: str, content: str, request: str, truncated: bool) -> str:
    return DOCUMENT_PROMPT_TEMPLATE.format(
        file_name=file_name,
        content=content or "[No se pudo extraer texto del documento]",
        request=request,
        truncated_note=" (solo el principio, el documento es más largo)" if truncated else "",
    )
