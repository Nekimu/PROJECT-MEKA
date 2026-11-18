"""Punto de entrada de Project MEKA.

python run.py            # MEKA Core + los canales activados (por defecto)
python run.py core       # Solo el servidor local (REST + WebSocket)
python run.py telegram   # Solo el bot (MEKA Core debe estar en marcha)
python run.py mcp        # Servidor MCP por stdio para Claude, Gemini CLI...
"""

import argparse
import asyncio
import contextlib

from core.logger import configure_logging, log_to_stderr, setup_logger

logger = setup_logger("Run")


def _quiet_disconnects(loop: asyncio.AbstractEventLoop, context: dict):
    """En Windows, un cliente que cierra de golpe (la isla al recargarse) deja un
    ConnectionResetError (WinError 10054) inofensivo en el registro. Se ignora solo ese."""
    if isinstance(context.get("exception"), ConnectionResetError):
        return
    loop.default_exception_handler(context)


async def _serve(config: dict, *, with_channels: bool):
    from server.app import build_server

    asyncio.get_running_loop().set_exception_handler(_quiet_disconnects)

    server = build_server(config)
    channels = []
    if with_channels and config.get("telegram", {}).get("enabled", True):
        from channels.telegram.app import run_telegram

        channels.append(asyncio.create_task(run_telegram(config), name="telegram"))
    try:
        await server.serve()
    finally:
        for task in channels:
            task.cancel()
        for task in channels:
            with contextlib.suppress(asyncio.CancelledError):
                await task


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Project MEKA")
    parser.add_argument(
        "mode", nargs="?", default="all", choices=["all", "core", "telegram", "mcp"]
    )
    args = parser.parse_args(argv)

    if args.mode == "mcp":
        # stdout es del protocolo MCP: los logs van a stderr ANTES de importar nada que
        # pueda registrar algo al cargarse (core.config lo hace al leer la configuración)
        log_to_stderr()
    from core.config import settings

    configure_logging(settings.get("app", {}).get("log_level", "INFO"))

    with contextlib.suppress(KeyboardInterrupt):
        if args.mode == "mcp":
            from channels.mcp.server import run_mcp

            run_mcp(settings)
        elif args.mode == "telegram":
            from channels.telegram.app import run_telegram

            asyncio.run(run_telegram(settings))
        else:
            asyncio.run(_serve(settings, with_channels=args.mode == "all"))


if __name__ == "__main__":
    main()
