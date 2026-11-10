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

    async def memories(self, user):
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
    assert names == {"chat", "pet_status", "pet_emotion", "remember", "memories"}


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
