# PROJECT MEKA
## Actualización de filosofía y evolución híbrida

**Documento de evolución:** integración progresiva de Google Home, Gemini, Meta Muse y procesamiento local  
**Versión del documento:** 0.3 — propuesta incremental, con la sección 2.4 revisada contra el repositorio  
**Fecha:** 9 de noviembre de 2026  
**Estado:** propuesta para orientar la siguiente iteración del proyecto

---

## 1. Propósito de esta actualización

Project MEKA nació como un asistente digital personal inspirado en la experiencia de Alexa y Google Home, pero con una identidad más personal y creativa: dar vida al Funko Pop del Meka de D.Va mediante voz, interacción física y una representación virtual de D.Va en una pantalla secundaria o, en una etapa posterior, en un efecto holográfico.

Esta actualización **no propone rehacer el proyecto ni sustituir su arquitectura existente**. Su objetivo es ajustar la dirección técnica para aprovechar los servicios que ya están disponibles —en particular el Google Home que ya utiliza el usuario— mientras se conserva el procesamiento local como filosofía y destino de largo plazo.

La nueva decisión central es:

> **MEKA será híbrido y agnóstico al proveedor: conservará una identidad, una memoria y una interfaz propias, aunque cambie el modelo de IA que ejecuta cada tarea.**

El proyecto puede utilizar Gemini, Muse u otros servicios comerciales durante la etapa de experimentación y, posteriormente, incorporar o priorizar modelos locales sin reconstruir la experiencia, el avatar, la memoria ni el hardware.

## 2. Filosofía y principios que se conservan

### 2.1 Identidad independiente del modelo

D.Va/MEKA no debe ser sinónimo de Gemini, Muse, Grok, Claude, Ollama ni de un proveedor concreto. El modelo es un motor intercambiable; la identidad del asistente pertenece al proyecto.

La personalidad, el historial, las preferencias, los objetivos, la configuración del avatar y las reglas de comportamiento deben almacenarse fuera del proveedor de IA.

### 2.2 Híbrido por diseño, local-first como objetivo

El uso de servicios cloud no contradice el objetivo de privacidad. Es una etapa práctica para probar la experiencia y avanzar sin esperar a adquirir una GPU o un servidor dedicado.

La arquitectura debe permitir elegir, por tarea:

- **Cloud:** mayor capacidad o servicios ya disponibles, cuando el usuario lo autorice.
- **Local:** operaciones privadas, memoria sensible y tareas que puedan ejecutarse en el hardware propio.
- **Externo/manual:** agentes comerciales que se utilizan desde su propia aplicación y entregan resultados al repositorio compartido, sin asumir que existe una API pública para controlarlos.

### 2.3 No depender de políticas comerciales permanentes

Las políticas de uso, filtros, precios, límites, disponibilidad y capacidades de los proveedores pueden cambiar. MEKA debe poder reemplazar un proveedor sin perder:

- La personalidad configurada.
- La memoria y el contexto acumulado.
- La interfaz de voz y avatar.
- Las automatizaciones propias.
- Los conectores y herramientas que no dependan del modelo.

Esto no implica intentar eliminar las políticas de seguridad de los proveedores. Significa evitar que la experiencia completa de MEKA dependa de una única política o plataforma.

### 2.4 Mantener la arquitectura existente

Revisión del repositorio (noviembre de 2026). Esto es lo que **existe hoy** y se conserva:

| Pieza | Implementación actual |
|---|---|
| MEKA Core | Servidor local FastAPI (`server/`, `core/engine.py`): API REST + WebSocket de eventos, con token y solo en 127.0.0.1 por defecto |
| Canales | Telegram (`channels/telegram/`) y MCP (`channels/mcp/`), ambos clientes de MEKA Core; la mascota se conecta por WebSocket |
| Personalidad | **Paquetes de personaje** en `personas/` (D.Va/MEKA, Marin, Yotsuba), seleccionables por configuración |
| Inferencia | Ollama (`ai/service.py`), con Gemma 3 12B por defecto |
| Voz a texto | `openai-whisper` (`ai/stt.py`) |
| Texto a voz | Edge-TTS por defecto; Qwen3-TTS y Piper opcionales (`ai/tts.py`) |
| Memoria | Historial por chat y recuerdos persistentes por usuario en `memory.json` (`core/memory.py`) |
| Avatar | Mascota de escritorio propia en `pet/` (web + Tauri), que ya implementa el contrato de eventos por WebSocket |

Y esto **todavía no existe**, aunque la versión 0.2 de este documento lo daba por hecho:

- Open-LLM-VTuber: no está en el repositorio. La interfaz visual es `pet/`; Open-LLM-VTuber queda como referencia o alternativa.
- WebRTC (voz en tiempo real): no existe. El servidor FastAPI con WebSocket sí (`server/app.py`).
- faster-whisper, Coqui y Bark: no se usan.
- Módulo de planificación y herramientas: no existe.
- PostgreSQL o base vectorial: no se usan.

Antes de modificar el repositorio se debe revisar qué módulos ya existen y reutilizarlos.

## 3. El papel del Google Home que ya se tiene

Google Home será el primer punto de experimentación por una razón simple: ya forma parte de la rutina del usuario, ya está conectado a su entorno de Google y permite probar interacciones por voz sin comprar hardware adicional.

Es necesario separar tres posibilidades distintas.

### 3.1 Prueba inmediata: Gemini para Home con personalidad temporal

La primera prueba no requiere instalar software ni adquirir componentes. Consiste en hablar directamente con el Google Home y darle una instrucción de estilo para la conversación actual.

En México, Google documenta el acceso anticipado de Gemini para Home en español. La disponibilidad concreta depende de que la casa y el dispositivo hayan recibido la actualización. En la aplicación se puede revisar en **Configuración de la casa → Asistente de voz de Gemini para Home**. Desde allí se pueden configurar voz, idioma, sensibilidad de “Hey Google”, Voice Match y resultados personales.

**Límite importante:** los ajustes oficiales documentados permiten personalizar voz, idioma y otros aspectos de la experiencia, pero no ofrecen un campo general para instalar un prompt de sistema permanente con una personalidad completamente personalizada. La instrucción de D.Va debe tratarse como un experimento conversacional, no como una personalización persistente garantizada.

**Precaución antes de actualizar:** Google indica que, una vez que se cambia una casa al asistente de voz Gemini para Home, no se puede volver al Asistente de Google anterior. Antes de aceptar el cambio, conviene revisar las funciones actuales y decidir si se desea hacer la migración.

#### Prompt de prueba para decir en voz alta

> Quiero que durante esta conversación adoptes una personalidad inspirada en D.Va, Hanna Song, de Overwatch. Habla en español latino de México. Sé energética, segura, competitiva, bromista y muy gamer; utiliza referencias a videojuegos, tecnología y cultura de internet cuando tengan sentido. Sé cercana y espontánea, pero no exageradamente cariñosa ni infantil. Puedes bromear conmigo, celebrar mis logros y retarme cuando me distraiga. Cuando hablemos de trabajo, estudios, programación o decisiones importantes, cambia a un tono inteligente, claro y analítico sin perder tu personalidad. No afirmes ser la D.Va oficial ni inventes recuerdos. Mantén este estilo durante esta conversación mientras sea posible.

Después se recomienda probar estas preguntas y anotar el resultado:

1. “D.Va, ¿qué tenemos pendiente hoy?”
2. “Estoy trabajando en Project MEKA. ¿Qué avance me recomendarías priorizar?”
3. “Explícame qué es una API como si estuviéramos en el lobby de Overwatch.”
4. “Hoy no tengo motivación para avanzar. Dame un empujón, pero sin frases motivacionales genéricas.”
5. “Ahora necesito una respuesta seria: compara dos opciones y explícame sus riesgos.”
6. “¿Puedes mantener esta personalidad en nuestra siguiente conversación?”

La sexta pregunta es deliberada: permite comprobar si el dispositivo conserva realmente el contexto o si la personalidad debe volver a indicarse en otra sesión.

### 3.2 Segunda prueba: Gemini como agente personalizado dentro de Home Assistant

Si la prueba nativa resulta limitada, la siguiente iteración será crear un agente Gemini configurable dentro de Home Assistant.

La integración oficial de Home Assistant para Google Gemini puede proporcionar un agente de conversación, entidades de voz a texto y texto a voz, y acceso opcional a dispositivos expuestos de Home Assistant. La personalidad se configura mediante el campo **Instructions** de la integración.

Ruta de configuración de alto nivel:

1. Instalar Home Assistant en el equipo o entorno que ya se utilice para el proyecto. No comprar hardware dedicado todavía.
2. En Home Assistant, abrir **Settings → Devices & services → Add Integration → Google Gemini**.
3. Crear una API key de Gemini y configurarla como secreto; nunca escribirla en el repositorio ni en el documento de personalidad.
4. Introducir el prompt de personalidad de MEKA en **Instructions**.
5. Mantener desactivado el control de dispositivos al principio. Habilitar únicamente las entidades necesarias cuando se pruebe esa función.
6. Probar la conversación desde la aplicación de Home Assistant o desde una interfaz Assist compatible.
7. Enviar la salida de voz al Google Home mediante Google Cast cuando el dispositivo aparezca como destino compatible.

**Costos y privacidad:** Home Assistant no tiene costo de licencia por esta integración, pero la API puede tener límites o cargos según el plan de Google AI Studio/Google Cloud. La documentación de Home Assistant advierte que el plan gratuito está sujeto a límites y que los prompts y respuestas gratuitos pueden utilizarse para mejorar productos. No deben enviarse secretos, contraseñas ni datos sensibles en esta prueba sin revisar antes las condiciones vigentes del proveedor.

### 3.3 Qué puede y qué no puede hacer el Nest como periférico

El dispositivo Google Home puede conservar su función nativa y, cuando sea compatible, servir como **salida de audio** para MEKA mediante Google Cast.

Sin embargo, la integración oficial de Google Cast de Home Assistant documenta reproducción multimedia y visualización de paneles; no ofrece un flujo para extraer el audio bruto del micrófono del Nest y entregarlo a un agente externo. Tampoco debe asumirse que la API pública de Google Home convierte el micrófono del Nest en un micrófono genérico para Ollama o FastAPI.

Por tanto, en la ruta Home Assistant + Gemini:

- **Entrada de voz:** aplicación móvil de Home Assistant, navegador con Assist o, más adelante, un dispositivo de voz compatible.
- **Procesamiento:** Gemini API durante la etapa cloud o modelo local en la etapa local.
- **Salida:** Google Home/Nest mediante Cast, si la red y el dispositivo lo permiten.
- **Avatar:** monitor del equipo principal, usando la interfaz visual existente.

Así se aprovecha el altavoz actual sin atribuirle una integración de micrófono que no está documentada.

## 4. Meta Muse y otros agentes comerciales

Meta Muse se conserva como una herramienta externa de productividad y coordinación, especialmente útil porque el usuario ya utiliza WhatsApp como canal de comunicación y tiene un flujo de trabajo con agentes que comparten archivos mediante Google Drive.

**No se debe modelar Muse como si fuera automáticamente una API de inferencia disponible para MEKA Core.** Hasta que exista un conector o interfaz de integración pública y autorizada que cubra el caso requerido, Muse se mantiene como agente comercial operado desde WhatsApp y/o sus interfaces compatibles.

El intercambio de trabajo se realiza mediante el repositorio documental compartido:

1. MEKA o el usuario crea una tarea y deja el contexto necesario en Drive.
2. Muse u otro agente recibe la instrucción desde su canal disponible.
3. El agente consulta los documentos autorizados y deposita resultados en la ubicación acordada.
4. MEKA Core puede indexar o consultar esos resultados, con permisos explícitos.
5. El usuario revisa y aprueba acciones externas o irreversibles.

Este enfoque respeta el ecosistema multiagente ya iniciado. No obliga a unificar todos los modelos ni a sustituir Drive por otra plataforma.

## 5. MEKA Core: una capa pequeña de independencia

La evolución técnica recomendada es agregar una capa de selección de proveedor al backend existente, en lugar de reconstruirlo.

### 5.1 Responsabilidades

MEKA Core debe encargarse de:

- Recibir solicitudes desde la interfaz existente.
- Cargar la personalidad y el contexto pertinente.
- Elegir el proveedor según tarea, disponibilidad, costo y privacidad.
- Enviar la solicitud al adaptador correspondiente.
- Normalizar la respuesta para que el avatar y la capa de voz no dependan del proveedor.
- Registrar metadatos de ejecución y errores sin guardar secretos innecesarios.

### 5.2 Adaptadores previstos

| Adaptador | Uso inicial | Situación |
|---|---|---|
| `GeminiAdapter` | Conversación personalizada y pruebas con Home Assistant | Primera ruta cloud recomendada |
| `OllamaAdapter` | Inferencia local con Gemma/Qwen | Se conserva como ruta local futura o paralela |
| `MuseExternal` | Agente de tareas por WhatsApp y Drive | Flujo externo; no asumir API directa |
| `ClaudeAdapter` | Análisis y documentación, si se habilita una API autorizada | Opcional |
| `OtherProviderAdapter` | Probar proveedores futuros | Interfaz extensible |

La interfaz de proveedor debe ser pequeña y común. Ejemplo conceptual (no exige adoptar exactamente estos nombres):

```python
class ProviderAdapter:
    async def generate(self, messages, context, options=None):
        """Devuelve texto, metadatos y uso, normalizados para MEKA."""
        raise NotImplementedError
```

El avatar no debería saber si la respuesta viene de Gemini, Ollama o de otro motor. Solo recibe eventos normalizados como `thinking`, `speaking`, `tool_call`, `complete` o `error`.

### 5.3 Enrutamiento inicial

| Tipo de solicitud | Proveedor inicial | Regla |
|---|---|---|
| Charla casual / personalidad | Gemini | Cloud durante el prototipo; Ollama puede sustituirlo después |
| Calendario, alarmas y control doméstico | Google Home nativo o Home Assistant | Utilizar la integración adecuada, no duplicar funciones |
| Documentos compartidos y tareas empresariales | Muse u otro agente especializado | Delegación explícita mediante Drive/WhatsApp |
| Análisis privado o información sensible | Modelo local | No enviar a servicios cloud por defecto |
| Generación visual | Agente/herramienta especializada | Resultado se almacena en Drive y se revisa |
| Automatizaciones físicas | Home Assistant / MQTT / ESP32 | Reglas y permisos independientes del LLM |

## 6. Memoria: conservar Google Drive y complementarlo

Google Drive permanece como **repositorio de conocimiento y memoria documental compartida**. Es una decisión existente y no se reemplaza.

Se recomienda mantener una estructura sencilla, adaptada a las carpetas actuales y sin mover archivos si ya existe una organización estable:

- `MEKA/00_CONTEXT`: descripción del proyecto, personalidad y preferencias.
- `MEKA/01_MEMORY`: resúmenes aprobados y decisiones duraderas.
- `MEKA/02_TASKS`: tareas, responsables, estados y resultados.
- `MEKA/03_ASSETS`: imágenes, audio, modelos y recursos del avatar.
- `MEKA/04_LOGS`: bitácoras de pruebas y cambios.

Los nombres son sugerencias; se deben mapear a las carpetas actuales en vez de duplicar la estructura.

Drive no sustituye automáticamente la memoria conversacional activa. MEKA Core debe consultar los documentos necesarios, resumir contexto útil y registrar resultados estructurados. Si posteriormente se usa PostgreSQL o una base vectorial, será una capa de búsqueda e indexación adicional, no un reemplazo obligatorio de Drive.

## 7. Personalidad base de MEKA / D.Va

La personalidad se guarda como un archivo versionado e independiente del proveedor. **Implementado:** `personas/dva/persona.md`, junto a `personas/dva/persona.yml` (nombre, voz y frases del bot). Ver [`personas/README.md`](../personas/README.md).

### Prompt base

```text
Eres MEKA, el asistente personal del usuario, con una personalidad original inspirada en el arquetipo de D.Va / Hanna Song de Overwatch.

IDIOMA Y ESTILO
- Habla en español latino de México.
- Mantén una energía gamer, optimista, segura, ingeniosa y competitiva.
- Puedes usar expresiones de cultura gamer e internet de forma natural, sin saturar cada frase.
- Sé cercana y divertida, pero evita ser empalagosa, invasiva o infantil.
- Adapta la extensión al contexto: breve en comandos cotidianos y detallada en temas técnicos.

CONTEXTO
- El usuario desarrolla Project MEKA y quiere dar vida a una figura física del Meka de D.Va mediante voz, avatar y electrónica.
- El proyecto busca una arquitectura híbrida, intercambiable y progresivamente local.
- El usuario trabaja con distintos modelos y agentes. No asumas que tú eres el único agente ni que tienes acceso a todos sus archivos.

COMPORTAMIENTO
- En charla casual, sé espontánea, bromista y expresiva.
- En programación, hardware, IA y decisiones importantes, sé rigurosa, organizada y transparente.
- En tareas complejas, propone el siguiente paso práctico sin convertir cada conversación en una lista interminable.
- Reconoce incertidumbre y no inventes acciones, recuerdos ni integraciones.
- Pide autorización antes de publicar, comprar, borrar, enviar mensajes o ejecutar acciones externas sensibles.

IDENTIDAD Y CONTINUIDAD
- Conserva esta personalidad aunque cambie el proveedor de IA.
- Usa la memoria externa autorizada; no afirmes recordar algo que no esté disponible.
- No afirmes ser la D.Va oficial ni imites una grabación de voz protegida. Eres MEKA, una interpretación original inspirada en ese personaje.
```

El prompt debe poder evolucionar con pruebas reales. No se debe fijar una imitación exacta de voz; la voz se elegirá entre opciones autorizadas del proveedor o un TTS cuya licencia permita el uso previsto.

## 8. Seguridad, privacidad y control de acciones

La filosofía híbrida requiere clasificar la información y no tratar todos los datos como equivalentes.

| Nivel | Ejemplos | Política inicial |
|---|---|---|
| Público | Personalidad, preferencias de interacción, información pública | Puede utilizarse con cloud |
| Interno | Documentos de Project MEKA, contenido empresarial no sensible | Solo con proveedor y cuenta autorizados |
| Sensible | Credenciales, tokens, datos financieros privados, información personal delicada | Local o fuera del contexto del LLM; nunca incluir secretos en prompts |

Controles mínimos:

- API keys y tokens en variables de entorno o gestor de secretos, nunca en Drive compartido ni Git.
- No habilitar control de dispositivos de Home Assistant hasta definir qué entidades se exponen.
- Separar “preparar” de “ejecutar”: publicar, borrar, comprar, enviar o modificar sistemas requiere confirmación.
- Registrar proveedor, modelo, hora, tarea y resultado; evitar registrar conversaciones completas cuando no sea necesario.
- Mantener copias de seguridad de la personalidad, configuración, memoria y recursos visuales.
- En integraciones MCP, conceder solo permisos necesarios y revocar accesos que ya no se usen.

## 9. Ruta incremental: siguiente ciclo de trabajo

### Iteración 0 — Prueba nativa con Google Home

**Objetivo:** evaluar si Gemini para Home sostiene un estilo inspirado en D.Va sin instalar nada.

- Verificar en Google Home si el asistente ya muestra “Gemini para Home”.
- Revisar disponibilidad y ajustes de idioma, voz y sensibilidad.
- Si todavía se usa Google Assistant, comprobar la invitación de acceso anticipado antes de cambiar; el cambio de casa a Gemini para Home no es reversible al asistente anterior según la documentación actual.
- Ejecutar el prompt de personalidad de prueba y las seis preguntas de evaluación.
- Registrar qué conserva, qué olvida, qué tono funciona y qué limitaciones aparecen.

**Criterio de salida:** determinar si sirve como prueba de estilo o si se necesita una personalidad persistente fuera del Google Home nativo.

### Iteración 1 — Gemini personalizable en Home Assistant

**Objetivo:** lograr una conversación con instrucciones propias y reproducir la respuesta por el Nest.

- Añadir Gemini a Home Assistant con API key.
- Configurar las instrucciones base de MEKA.
- Probar voz de entrada con la app de Home Assistant o una interfaz Assist compatible.
- Detectar el Nest mediante Google Cast y probar salida TTS/media.
- No comprar micrófonos ni altavoces todavía.

**Criterio de salida:** conversación de ida y vuelta con personalidad constante, usando un micrófono compatible y el Nest como salida de audio.

### Iteración 2 — Reincorporación a la interfaz visual existente

**Objetivo:** conectar el backend de conversación al frontend/avatar que ya existe.

- Reutilizar la mascota de `pet/`, que ya implementa el contrato de eventos (Open-LLM-VTuber queda como alternativa).
- Adaptar el backend actual para que consuma la respuesta normalizada del proveedor.
- Activar estados del avatar: escuchando, pensando, hablando, inactivo y error.
- Sincronizar TTS con el avatar cuando la ruta de audio lo permita.

**Criterio de salida:** el avatar reacciona con la personalidad de MEKA independientemente del proveedor usado.

### Iteración 3 — MEKA Core y enrutamiento híbrido

**Objetivo:** añadir el adaptador de proveedores sin refactorizar todo el sistema.

- Implementar el adaptador de Gemini.
- Conservar el adaptador de Ollama o implementarlo donde corresponda dentro del backend existente.
- Añadir selección de proveedor por tarea y privacidad.
- Mantener Muse como flujo externo mediante WhatsApp y Drive hasta disponer de integración autorizada.

**Criterio de salida:** cambiar de Gemini a Ollama mediante configuración, sin modificar avatar, memoria ni interfaz.

### Iteración 4 — Integración opcional con Google Home MCP

Google publicó un servidor **Home MCP** en acceso anticipado. Permite a agentes compatibles descubrir dispositivos y espacios, consultar estados, ejecutar controles permitidos y consultar historial. Puede ser útil más adelante si se desea que MEKA u otro agente controle el entorno Google Home mediante herramientas MCP.

No es el motor de personalidad ni convierte el micrófono del Nest en entrada para MEKA. Es un conector de herramientas para el ecosistema doméstico.

La documentación actual exige Google Home Premium Advanced, un proyecto de Google Cloud, aprobación/acceso, configuración OAuth y un cliente compatible con MCP, por ejemplo OpenClaw o Claude Cowork. Por su configuración y requisitos, **no forma parte de la primera prueba**. Se evaluará después de validar el prototipo básico.

### Iteración 5 — Migración progresiva a local-first

- Mantener los mismos contratos de adaptador.
- Incorporar Ollama y modelos locales según el hardware real.
- Mover STT/TTS a motores locales cuando la calidad y latencia sean aceptables.
- Mantener Gemini u otros servicios como proveedor opcional, no obligatorio.
- Definir modo degradado sin Internet para las funciones locales esenciales.

## 10. Costos y compras durante esta etapa

La primera prueba debe tener **costo incremental cercano a cero**, aprovechando:

- El Google Home ya existente.
- El CPU actual.
- La aplicación de Home Assistant, si ya está instalada o puede ejecutarse en el equipo actual.
- El monitor y periféricos existentes.
- Google Home/Gemini nativo para la primera prueba de personalidad.

No comprar todavía:

- Raspberry Pi o mini PC dedicada.
- GPU para inferencia local.
- Micrófonos de matriz adicionales.
- Pantalla holográfica o acrílico Pepper’s Ghost.
- Nuevo altavoz.

La API de Gemini puede generar costos dependiendo del plan y uso. Home MCP requiere una suscripción y configuración adicionales; no se debe contratar solo para probar la personalidad.

## 11. Decisiones pendientes que deben resolverse con pruebas

1. Modelo exacto del Google Home/Nest que ya se tiene y si recibió Gemini para Home.
2. Si la personalidad nativa mantiene contexto durante una conversación suficientemente larga.
3. Si el usuario ya tiene Home Assistant instalado y dónde se ejecuta.
4. Si el Nest aparece como destino Google Cast desde Home Assistant.
5. Qué frontend/avatar está actualmente funcional en el repositorio y cuál es el contrato del backend existente.
6. Qué proveedor se utilizará para cada tipo de tarea, según costo, privacidad, latencia y calidad.

Estas preguntas no bloquean la prueba nativa inicial. Sirven para decidir el siguiente cambio mínimo en el proyecto.

## 12. Resultado esperado

Project MEKA evoluciona sin reiniciarse:

- El Funko Pop del Meka sigue siendo el objeto físico central.
- Google Home permite probar desde ahora la interacción por voz y las capacidades de Gemini para el hogar.
- Home Assistant puede actuar como puente y plataforma de experimentación, usando Gemini API con instrucciones propias y Google Cast como salida de audio.
- El avatar y el backend actuales se conservan y se conectan progresivamente al nuevo enrutamiento.
- Muse y otros agentes siguen aportando trabajo especializado a través del ecosistema compartido de Drive y sus canales disponibles.
- Ollama y el procesamiento local permanecen como ruta de independencia tecnológica, no como requisito para iniciar.

**Principio rector:** cambiar de motor no debe significar cambiar de asistente. MEKA conserva su identidad, memoria, interfaz y continuidad mientras los proveedores se convierten en componentes reemplazables.

---

## Referencias técnicas oficiales

1. Google Nest — [Información sobre el asistente de voz de Gemini para Home](https://support.google.com/googlehome/answer/16618650?hl=es). Disponibilidad, configuración, idiomas, funciones básicas y advertencia sobre el cambio irreversible desde el Asistente de Google.
2. Google Nest — [Novedades de Google Home](https://support.google.com/googlehome/answer/15962877?hl=es). Notas de lanzamiento y disponibilidad regional de Gemini para Home.
3. Home Assistant — [Google Gemini integration](https://www.home-assistant.io/integrations/google_generative_ai_conversation/). Agente conversacional, STT/TTS, instrucciones, API key, herramientas y controles expuestos.
4. Home Assistant — [Google Cast integration](https://www.home-assistant.io/integrations/cast/). Detección de dispositivos Cast, reproducción multimedia y requisitos de red.
5. Google Home Developers — [Home MCP](https://developers.home.google.com/mcp). Capacidades de MCP para agentes y ecosistema Google Home.
6. Google Home Developers — [Google Home MCP Server](https://developers.home.google.com/mcp/home). Requisitos de acceso, OAuth, Google Home Premium Advanced, cliente MCP y precauciones de seguridad.
7. Google Home Developers — [Home APIs](https://developers.home.google.com/apis). APIs para integrar dispositivos y automatizaciones de Google Home en aplicaciones.

*Documento de diseño y evolución. Aplicado hasta ahora: paquetes de personaje (sección 7) y retirada de las voces de referencia protegidas. El resto son propuestas.*
