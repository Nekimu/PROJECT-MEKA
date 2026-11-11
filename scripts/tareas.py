"""Tablero compartido de tareas entre Claude Code (backend) y Antigravity (frontend).

La fuente de verdad es `coordinacion/tareas.json`; `coordinacion/TABLERO.md` se genera solo.
La lógica vive en `scripts/tablero/`; este archivo es solo la línea de comandos.

    python scripts/tareas.py tablero                      # Regenera TABLERO.md y muestra el resumen
    python scripts/tareas.py lista --agente claude        # Tareas de un agente
    python scripts/tareas.py nueva --agente antigravity --titulo "..." [--prioridad alta]
                                   [--archivos pet/web/pet.js,pet/web/pet.css] [--depende T-003]
    python scripts/tareas.py estado T-003 en_progreso --agente claude [--nota "..."]
    python scripts/tareas.py sync                         # Actualiza estados a partir de los commits
    python scripts/tareas.py propietario pet/web/pet.js   # ¿De quién es este archivo?
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Se ejecuta como script (python scripts/tareas.py) y se importa en los tests (scripts.tareas)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tablero import datos, gitsync, hooks, vista
from tablero.datos import ESTADOS, ICONOS, PRIORIDADES

__all__ = ["datos", "gitsync", "hooks", "main", "vista"]


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Tablero de tareas Claude Code ↔ Antigravity")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tablero")
    sub.add_parser("sync")
    sub.add_parser("hook-session")
    s = sub.add_parser("lista")
    s.add_argument("--agente")
    s.add_argument("--estado", choices=ESTADOS)
    s = sub.add_parser("nueva")
    s.add_argument("--agente", required=True)
    s.add_argument("--titulo", required=True)
    s.add_argument("--descripcion", default="")
    s.add_argument("--prioridad", choices=PRIORIDADES, default="media")
    s.add_argument("--archivos", default="")
    s.add_argument("--depende", default="")
    s.add_argument("--por", default="")
    s = sub.add_parser("estado")
    s.add_argument("id")
    s.add_argument("estado", choices=ESTADOS)
    s.add_argument("--agente", required=True)
    s.add_argument("--nota", default="")
    s = sub.add_parser("propietario")
    s.add_argument("rutas", nargs="+")
    s = sub.add_parser("hook-pretooluse")
    s.add_argument("--agente", required=True)
    s = sub.add_parser("check-commit")
    s.add_argument("msg_file")
    return p


def _split(value: str, upper: bool = False) -> list[str]:
    items = [v.strip() for v in value.split(",") if v.strip()]
    return [v.upper() for v in items] if upper else items


def _read_only(args, db: dict) -> int:
    """Órdenes que solo leen: no toman el bloqueo."""
    if args.cmd == "hook-pretooluse":
        hooks.pretooluse(db, args.agente)
    elif args.cmd == "hook-session":
        hooks.session(db)
    elif args.cmd == "check-commit":
        return gitsync.check_commit(db, args.msg_file)
    elif args.cmd == "propietario":
        for ruta in args.rutas:
            print(f"{datos.owner(db, ruta):12} {ruta}")
    else:  # lista
        for t in db["tareas"]:
            if (args.agente and t["responsable"] != args.agente) or (
                args.estado and t["estado"] != args.estado
            ):
                continue
            print(
                f"{ICONOS[t['estado']]} {t['id']} [{t['responsable']}/{t['prioridad']}] {t['titulo']}"
            )
    return 0


def _write(args, db: dict):
    """Órdenes que modifican el tablero (dentro del bloqueo)."""
    if args.cmd == "sync":
        print("\n".join(gitsync.sync(db)) or "Sin cambios de estado.")
    elif args.cmd == "nueva":
        task = datos.new_task(
            db,
            args.agente,
            args.titulo,
            prioridad=args.prioridad,
            descripcion=args.descripcion,
            archivos=_split(args.archivos),
            depende_de=_split(args.depende, upper=True),
            por=args.por,
        )
        print(f"Creada {task['id']}: {task['titulo']}")
    elif args.cmd == "estado":
        task = datos.find(db, args.id)
        if args.agente != task["responsable"]:
            print(
                f"⚠️  {task['id']} es de {task['responsable']}; se registra el cambio de {args.agente}."
            )
        datos.set_state(task, args.estado, args.agente, args.nota)
        print(f"{task['id']} -> {args.estado}")
    else:  # tablero
        print(vista.summary(db))
    datos.save(db)
    vista.render(db)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = _parser().parse_args(argv)
    if args.cmd in ("hook-pretooluse", "hook-session", "propietario", "check-commit", "lista"):
        return _read_only(args, datos.load())
    with datos.locked():
        _write(args, datos.load())
    return 0


if __name__ == "__main__":
    sys.exit(main())
