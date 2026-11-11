import asyncio

import pytest

from channels.mcp.server import MekaTools


class FakeCore:
    def __init__(self):
        self.events = []
        self.facts = []

    async def chat(self, session, user, text, **options):
        assert options == {"audio": False}
        return [{"text": f"{session}/{user}: {text}"}, {"text": ""}]

    async def publish(self, type_, **data):
        self.events.append((type_, data))
        return 1

    async def remember(self, user, fact):
        if fact in self.facts:
            return False
        self.facts.append(fact)
        return True

    async def memories(self, user, query=None, include_private=True):
        assert include_private is False  # El MCP nunca pide recuerdos privados
        return list(self.facts)


def run(coro):
    return asyncio.run(coro)


def make_tools():
    core = FakeCore()
    return core, MekaTools(core, session="mcp", user="42")


def test_chat_uses_its_own_session():
    _, tools = make_tools()
    assert run(tools.chat("hola")) == "mcp/42: hola"


def test_pet_status_maps_to_event_contract():
    core, tools = make_tools()
    run(tools.pet_status("working", "Ordenar Descargas"))
    run(tools.pet_status("done", "Listo"))
    run(tools.pet_status("error"))
    assert core.events == [
        ("agent.working", {"task": "Ordenar Descargas"}),
        ("agent.done", {"summary": "Listo"}),
        ("agent.error", {}),
    ]
    with pytest.raises(ValueError):
        run(tools.pet_status("bailando"))


def test_emotion_is_validated():
    core, tools = make_tools()
    run(tools.pet_emotion("celebrate"))
    assert core.events == [("emotion", {"emotion": "celebrate"})]
    with pytest.raises(ValueError):
        run(tools.pet_emotion("furiosa"))


def test_memory_tools():
    _, tools = make_tools()
    assert run(tools.remember("le gusta el ramen")) == "Guardado."
    assert run(tools.remember("le gusta el ramen")) == "Ya lo sabía."
    assert run(tools.memories()) == ["le gusta el ramen"]


def test_mcp_server_registers_tools():
    pytest.importorskip("mcp")
    from channels.mcp.server import build_mcp

    server = build_mcp({"mcp": {"user": "42"}}, core=FakeCore())
    names = {tool.name for tool in run(server.list_tools())}
    assert names == {
        "chat",
        "pet_status",
        "pet_emotion",
        "remember",
        "memories",
        "ask_permission",
    }


def test_mcp_reports_expected_errors_to_the_agent():
    pytest.importorskip("mcp")
    from mcp import Client

    from channels.mcp.server import build_mcp

    async def scenario():
        async with Client(build_mcp({}, core=FakeCore())) as client:
            ok = await client.call_tool("pet_status", {"state": "done", "text": "Listo"})
            bad = await client.call_tool("pet_emotion", {"emotion": "furiosa"})
            return ok, bad

    ok, bad = run(scenario())
    assert not ok.is_error
    assert bad.is_error and "furiosa" in bad.content[0].text


def test_stdout_is_reserved_for_the_protocol(tmp_path):
    """`python run.py mcp` no puede escribir nada en stdout que no sea JSON-RPC: un log
    al importar la configuración rompía el protocolo en clientes estrictos."""
    import json
    import subprocess
    import sys
    from pathlib import Path

    pytest.importorskip("mcp")
    root = Path(__file__).resolve().parent.parent
    # Un config_local.yml provoca un log al importar core.config (el caso que fallaba)
    hello = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1"},
        },
    }
    result = subprocess.run(
        [sys.executable, str(root / "run.py"), "mcp"],
        input=json.dumps(hello) + "\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=root,
        timeout=60,
        check=False,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert lines, f"El servidor no respondió. stderr:\n{result.stderr[-2000:]}"
    for line in lines:
        message = json.loads(line)  # Falla si se cuela un log u otro texto
        assert message.get("jsonrpc") == "2.0"
    assert json.loads(lines[0])["result"]["serverInfo"]["name"] == "MEKA"


def test_ask_permission_tool():
    class PermissionCore(FakeCore):
        def __init__(self, approved):
            super().__init__()
            self.approved = approved
            self.asked = []

        async def ask_permission(self, action, *, timeout=120, details=None):
            self.asked.append((action, timeout))
            return self.approved

    yes, no = PermissionCore(True), PermissionCore(False)
    assert run(MekaTools(yes, "mcp", "42").ask_permission("borrar logs", 9999)).startswith(
        "APROBADO"
    )
    assert yes.asked == [("borrar logs", 600)]  # Nunca más de 10 minutos
    assert run(MekaTools(no, "mcp", "42").ask_permission("borrar logs")).startswith("DENEGADO")
