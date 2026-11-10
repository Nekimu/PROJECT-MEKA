"""Punto de entrada de Project MEKA.

python run.py            # MEKA Core + los canales activados (por defecto)
python run.py core       # Solo el servidor local (REST + WebSocket)
python run.py telegram   # Solo el bot (MEKA Core debe estar en marcha)
python run.py mcp        # Servidor MCP por stdio para Claude, Gemini CLI...
"""

import argparse
import asyncio
import contextlib

from core.config import settings
from core.logger import configure_logging, log_to_stderr, setup_logger

logger = setup_logger("Run")


async def _serve(config: dict, *, with_channels: bool):
    from server.app import build_server

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
        log_to_stderr()  # stdout es del protocolo MCP
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
