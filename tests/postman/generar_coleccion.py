"""Genera la colección y el entorno de Postman de MEKA Core.

    python tests/postman/generar_coleccion.py

Edita este archivo (no el JSON) para añadir pruebas: así la colección queda revisable en git.
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
AUTH = [{"key": "Authorization", "value": "Bearer {{token}}"}]
MEMORIES = "/v1/users/{{testUser}}/memories"


def request(name, method, path, tests, *, body=None, query=None, headers=None):
    url = {
        "raw": "{{baseUrl}}" + path,
        "host": ["{{baseUrl}}"],
        "path": path.strip("/").split("/"),
    }
    if query:
        url["query"] = [{"key": key, "value": value} for key, value in query]
        url["raw"] += "?" + "&".join(f"{key}={value}" for key, value in query)
    item = {
        "name": name,
        "request": {"method": method, "header": AUTH if headers is None else headers, "url": url},
        "event": [
            {
                "listen": "test",
                "script": {"type": "text/javascript", "exec": tests.strip().splitlines()},
            }
        ],
    }
    if body is not None:
        item["request"]["body"] = {
            "mode": "raw",
            "raw": json.dumps(body, ensure_ascii=False, indent=2),
            "options": {"raw": {"language": "json"}},
        }
    return item


def chat(text, session="{{session}}", **extra):
    return {"session": session, "user": "{{testUser}}", "text": text, "audio": False, **extra}


ESTADO = [
    request(
        "Health (público)",
        "GET",
        "/v1/health",
        """
pm.test("200 y status ok", () => { pm.response.to.have.status(200); pm.expect(pm.response.json().status).to.eql("ok"); });
pm.test("Incluye la versión del contrato", () => pm.expect(pm.response.json().contract).to.match(/^\\d+\\.\\d+$/));
pm.collectionVariables.set("contractVersion", pm.response.json().contract);
""",
        headers=[],
    ),
    request(
        "Contrato (público)",
        "GET",
        "/v1/contract",
        """
const c = pm.response.json();
pm.test("200", () => pm.response.to.have.status(200));
pm.test("Misma versión que /v1/health", () => pm.expect(c.version).to.eql(pm.collectionVariables.get("contractVersion")));
pm.test("Versión mayor 1 (la que entiende esta colección)", () => pm.expect(c.version.split(".")[0]).to.eql("1"));
pm.test("Eventos y emociones", () => {
  pm.expect(c.events.outbound).to.have.property("agent.confirm");
  pm.expect(c.events.inbound).to.have.property("user.confirm");
  pm.expect(c.emotions).to.include.members(["idle", "happy", "error", "thinking"]);
});
pm.test("Lista las rutas REST", () => pm.expect(c.rest.map(r => r.method + " " + r.path)).to.include("POST /v1/chat"));
""",
        headers=[],
    ),
    request(
        "Personaje",
        "GET",
        "/v1/persona",
        """
pm.test("200", () => pm.response.to.have.status(200));
pm.test("Tiene nombre y nunca expone el prompt", () => {
  const p = pm.response.json();
  pm.expect(p.name).to.be.a("string");
  pm.expect(p).to.not.have.property("prompt");
});
""",
    ),
]

MEMORIA = [
    request(
        "Limpiar usuario de pruebas",
        "DELETE",
        MEMORIES,
        'pm.test("200", () => pm.response.to.have.status(200));',
    ),
    request(
        "Guardar recuerdo público",
        "POST",
        MEMORIES,
        'pm.test("Guardado", () => pm.expect(pm.response.json().added).to.be.true);',
        body={"fact": "Mi perro se llama Toby"},
    ),
    request(
        "Guardar recuerdo privado",
        "POST",
        MEMORIES,
        'pm.test("Guardado", () => pm.expect(pm.response.json().added).to.be.true);',
        body={"fact": "Mi cita médica es el jueves", "private": True},
    ),
    request(
        "Listar todos (API local)",
        "GET",
        MEMORIES,
        'pm.test("Incluye el privado", () => pm.expect(pm.response.json().memories).to.have.members(["Mi perro se llama Toby", "Mi cita médica es el jueves"]));',
    ),
    request(
        "Listar sin privados (como MCP y Telegram)",
        "GET",
        MEMORIES,
        'pm.test("Oculta el privado", () => pm.expect(pm.response.json().memories).to.eql(["Mi perro se llama Toby"]));',
        query=[("include_private", "false")],
    ),
    request(
        "Buscar sin privados",
        "GET",
        MEMORIES,
        'pm.test("Nunca aparece el privado", () => pm.expect(JSON.stringify(pm.response.json().memories)).to.not.include("cita"));',
        query=[("q", "cita"), ("include_private", "false")],
    ),
]

CONVERSACION = [
    request(
        "Chat normal",
        "POST",
        "/v1/chat",
        """
pm.test("200 con respuestas", () => { pm.response.to.have.status(200); pm.expect(pm.response.json().replies.length).to.be.above(0); });
pm.test("No es privado", () => pm.expect(pm.response.json().replies[0].private).to.be.false);
""",
        body=chat("Hola, ¿cómo estás?", session="{{session}}-normal"),
    ),
    request(
        "Chat privado",
        "POST",
        "/v1/chat",
        'pm.test("Marcado como privado", () => pm.expect(pm.response.json().replies[0].private).to.be.true);',
        body=chat("Esto es confidencial", private=True),
    ),
    request(
        "La sesión sigue privada",
        "POST",
        "/v1/chat",
        'pm.test("Privada hasta reiniciarla", () => pm.expect(pm.response.json().replies[0].private).to.be.true);',
        body=chat("¿Y qué opinas?"),
    ),
    request(
        "Dato sensible detectado",
        "POST",
        "/v1/chat",
        'pm.test("Pasa a privado solo", () => pm.expect(pm.response.json().replies[0].private).to.be.true);',
        body=chat("mi contraseña es Gato.2026", session="{{session}}-sensible"),
    ),
    request(
        "Reiniciar sesión privada",
        "POST",
        "/v1/sessions/{{session}}/reset",
        'pm.test("204", () => pm.response.to.have.status(204));',
    ),
]

EVENTOS = [
    request(
        "agent.working",
        "POST",
        "/v1/events",
        'pm.test("202", () => pm.response.to.have.status(202));',
        body={"type": "agent.working", "data": {"task": "Prueba de Postman"}},
    ),
    request(
        "agent.done",
        "POST",
        "/v1/events",
        'pm.test("202", () => pm.response.to.have.status(202));',
        body={"type": "agent.done", "data": {"summary": "Postman terminó"}},
    ),
    request(
        "Emoción no válida → 422",
        "POST",
        "/v1/events",
        'pm.test("422 con mensaje claro", () => { pm.response.to.have.status(422); pm.expect(pm.response.json().detail).to.include("emotion"); });',
        body={"type": "emotion", "data": {"emotion": "bailando"}},
    ),
    request(
        "agent.confirm a mano → 422",
        "POST",
        "/v1/events",
        'pm.test("Solo lo emite el núcleo", () => { pm.response.to.have.status(422); pm.expect(pm.response.json().detail).to.include("/v1/confirmations"); });',
        body={"type": "agent.confirm", "data": {"action": "x"}},
    ),
]

PERMISOS = [
    request(
        "Pendientes",
        "GET",
        "/v1/confirmations",
        'pm.test("Lista", () => pm.expect(pm.response.json().pending).to.be.an("array"));',
    ),
    request(
        "Responder uno inexistente → 404",
        "POST",
        "/v1/confirmations/no-existe",
        'pm.test("404", () => pm.response.to.have.status(404));',
        body={"approved": True},
    ),
    request(
        "Pedir permiso sin respuesta → denegado",
        "POST",
        "/v1/confirmations",
        'pm.test("Caduca y la respuesta es NO", () => { pm.response.to.have.status(200); pm.expect(pm.response.json().approved).to.be.false; });',
        body={"action": "Prueba de Postman (nadie responde)", "timeout": 2},
    ),
]

MANOS = [
    request(
        "Carpetas autorizadas",
        "GET",
        "/v1/hands",
        'pm.test("Lista (vacía si no autorizaste ninguna en config.yml)", () => pm.expect(pm.response.json().folders).to.be.an("array"));',
    ),
    request(
        "Carpeta no autorizada → 404",
        "GET",
        "/v1/hands/no-autorizada/list",
        'pm.test("404", () => pm.response.to.have.status(404));',
    ),
    request(
        "Escapar de una carpeta → nunca 200",
        "GET",
        "/v1/hands/no-autorizada/read",
        'pm.test("Rechazado", () => pm.expect(pm.response.code).to.be.oneOf([400, 403, 404]));',
        query=[("path", "../../.env")],
    ),
    request(
        "Escribir en carpeta no autorizada → nunca 200",
        "POST",
        "/v1/hands/no-autorizada/write",
        'pm.test("Rechazado sin pedir permiso", () => pm.expect(pm.response.code).to.be.oneOf([403, 404]));',
        body={"path": "prueba.txt", "content": "no debería escribirse"},
    ),
    request(
        "Historial de una carpeta no autorizada → 404",
        "GET",
        "/v1/hands/no-autorizada/history",
        'pm.test("404", () => pm.response.to.have.status(404));',
    ),
    request(
        "Ninguna carpeta admite cambios (escritura pospuesta)",
        "GET",
        "/v1/hands",
        'pm.test("writable es false en todas", () => pm.response.json().folders.forEach(f => pm.expect(f.writable).to.be.false));',
    ),
]

SISTEMA = [
    request(
        "Música y batería",
        "GET",
        "/v1/system",
        'pm.test("Tiene media y battery (pueden ser null)", () => { const s = pm.response.json(); pm.expect(s).to.have.property("media"); pm.expect(s).to.have.property("battery"); });',
    ),
    request(
        "Acción de música no válida → 422",
        "POST",
        "/v1/system/media",
        'pm.test("422", () => pm.response.to.have.status(422));',
        body={"action": "borrar_todo"},
    ),
    request(
        "system.battery a mano → 422",
        "POST",
        "/v1/events",
        'pm.test("Solo lo emite el núcleo", () => pm.response.to.have.status(422));',
        body={"type": "system.battery", "data": {"percent": 1, "charging": False}},
    ),
    request(
        "Notificaciones (privadas)",
        "GET",
        "/v1/system/notifications",
        """
const n = pm.response.json().notifications;
pm.test("Lista", () => pm.expect(n).to.be.an("array"));
pm.test("Nunca sale el identificador interno de la app", () => n.forEach(x => pm.expect(x).to.not.have.property("aumid")));
""",
    ),
    request(
        "Acción de notificación no válida → 422",
        "POST",
        "/v1/system/notifications/1",
        'pm.test("422", () => pm.response.to.have.status(422));',
        body={"action": "responder"},
    ),
]

REGISTRO_Y_SEGURIDAD = [
    request(
        "Registro de ejecución (sin contenido)",
        "GET",
        "/v1/runs",
        """
const r = pm.response.json();
pm.test("200 con resumen por proveedor", () => { pm.response.to.have.status(200); pm.expect(r.summary).to.be.an("object"); });
pm.test("Nunca incluye texto de las conversaciones", () => pm.expect(JSON.stringify(r)).to.not.include("confidencial"));
""",
        query=[("limit", "5")],
    ),
    request(
        "Web ajena (Origin) → 403",
        "GET",
        "/v1/health",
        'pm.test("403", () => pm.response.to.have.status(403));',
        headers=[{"key": "Origin", "value": "https://malicioso.example"}],
    ),
    request(
        "Limpiar usuario de pruebas",
        "DELETE",
        MEMORIES,
        'pm.test("200", () => pm.response.to.have.status(200));',
    ),
]


def folder(name, description, items):
    return {"name": name, "description": description, "item": items}


COLLECTION = {
    "info": {
        "name": "MEKA Core API",
        "description": (
            "Pruebas de la API local de MEKA Core. Contrato en GET /v1/contract.\n"
            "Usa el usuario de memoria `{{testUser}}` y lo borra al final: no toca tus recuerdos.\n"
            "El chat llama al cerebro configurado (Ollama): puede tardar unos segundos."
        ),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "variable": [
        {"key": "testUser", "value": "postman-test"},
        {"key": "session", "value": "postman-session"},
    ],
    "item": [
        folder("1 · Estado", "Salud, contrato y personaje.", ESTADO),
        folder("2 · Memoria", "Recuerdos públicos y privados del usuario de pruebas.", MEMORIA),
        folder("3 · Conversación y privacidad", "Llama al cerebro configurado.", CONVERSACION),
        folder("4 · Eventos", "Publicación validada contra el contrato.", EVENTOS),
        folder("5 · Permisos", "agent.confirm / user.confirm. Sin respuesta = no.", PERMISOS),
        folder("6 · Manos (solo lectura)", "Carpetas autorizadas en hands.folders.", MANOS),
        folder("7 · Sistema (Dynamic Island)", "Música y batería.", SISTEMA),
        folder("8 · Registro y seguridad", "", REGISTRO_Y_SEGURIDAD),
    ],
}

ENVIRONMENT = {
    "name": "MEKA local",
    "values": [
        {"key": "baseUrl", "value": "http://127.0.0.1:8765", "type": "default", "enabled": True},
        # Vacío si MEKA_API_TOKEN no está configurado; si lo está, ponlo en Postman, no aquí
        {"key": "token", "value": "", "type": "secret", "enabled": True},
    ],
}


def write(name: str, data: dict):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write("meka-core.postman_collection.json", COLLECTION)
    write("local.postman_environment.json", ENVIRONMENT)
    print(f"Colección y entorno escritos en {OUT}")
