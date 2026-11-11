"""Vistas del tablero: TABLERO.md (generado) y el resumen de tareas abiertas."""

from __future__ import annotations

from . import datos
from .datos import ESTADOS, ICONOS, PRIORIDADES


def _resumen(db: dict) -> list[str]:
    lines = [
        "## Resumen",
        "",
        "| Agente | Rol | " + " | ".join(f"{ICONOS[e]} {e}" for e in ESTADOS) + " |",
        "|---|---|" + "---|" * len(ESTADOS),
    ]
    for key, agente in db["agentes"].items():
        mine = [t for t in db["tareas"] if t["responsable"] == key]
        counts = " | ".join(str(sum(t["estado"] == e for t in mine)) for e in ESTADOS)
        lines.append(f"| **{agente['nombre']}** | {agente['rol']} | {counts} |")
    return lines


def _por_agente(db: dict) -> list[str]:
    prio = {p: i for i, p in enumerate(PRIORIDADES)}
    lines = []
    for key, agente in db["agentes"].items():
        lines += ["", f"## {agente['nombre']}", ""]
        mine = [t for t in db["tareas"] if t["responsable"] == key]
        if not mine:
            lines.append("_Sin tareas todavía._")
            continue
        lines += [
            "| ID | Estado | Prioridad | Tarea | Depende de | Actualizada |",
            "|---|---|---|---|---|---|",
        ]
        # Abiertas primero (por prioridad), las hechas al final
        for t in sorted(
            mine, key=lambda t: (t["estado"] == "hecha", prio[t["prioridad"]], t["id"])
        ):
            deps = ", ".join(t.get("depende_de", [])) or "—"
            fecha = t.get("actualizada", "")[:16].replace("T", " ")
            lines.append(
                f"| {t['id']} | {ICONOS[t['estado']]} {t['estado']} | {t['prioridad']} "
                f"| {t['titulo']} | {deps} | {fecha} |"
            )
    return lines


def _detalle(db: dict) -> list[str]:
    lines = ["", "## Detalle", ""]
    for t in db["tareas"]:
        lines += [
            f"### {t['id']} · {t['titulo']}",
            "",
            f"**Responsable:** {db['agentes'][t['responsable']]['nombre']} · "
            f"**Estado:** {ICONOS[t['estado']]} {t['estado']} · **Prioridad:** {t['prioridad']}",
        ]
        if t.get("descripcion"):
            lines += ["", t["descripcion"]]
        if t.get("archivos"):
            lines += ["", "**Archivos:** " + ", ".join(f"`{a}`" for a in t["archivos"])]
        if t.get("depende_de"):
            lines += ["", "**Depende de:** " + ", ".join(t["depende_de"])]
        if t.get("commits"):
            lines += ["", "**Commits:** " + ", ".join(f"`{c[:7]}`" for c in t["commits"])]
        last = (t.get("historial") or [{}])[-1]
        if last.get("nota"):
            lines += ["", f"**Última nota ({last['por']}):** {last['nota']}"]
        lines.append("")
    return lines


def render(db: dict):
    """Regenera coordinacion/TABLERO.md a partir de tareas.json."""
    lines = [
        "# Tablero de tareas — Project MEKA",
        "",
        "> ⚠️ **Archivo generado automáticamente.** No lo edites a mano: usa "
        "`python scripts/tareas.py` (ver [README](README.md)). Fuente: `tareas.json`.",
        "",
        f"_Última actualización: {datos.now()}_",
        "",
        *_resumen(db),
        *_por_agente(db),
        *_detalle(db),
    ]
    datos.RUTAS.board.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def summary(db: dict) -> str:
    out = []
    for key, agente in db["agentes"].items():
        activas = [t for t in db["tareas"] if t["responsable"] == key and t["estado"] != "hecha"]
        out.append(f"{agente['nombre']} ({len(activas)} abiertas):")
        for t in activas:
            out.append(f"  {ICONOS[t['estado']]} {t['id']} [{t['prioridad']}] {t['titulo']}")
    return "\n".join(out)
