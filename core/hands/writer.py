"""Cambios dentro de una carpeta autorizada con `writable: true`.

Aquí solo se valida y se ejecuta. El permiso del usuario, el punto de restauración y los
eventos los pone `Hands` (core/hands/__init__.py), antes de llamar a estas funciones.
"""

from dataclasses import dataclass
from pathlib import Path

from core.hands.policy import Folder, HandsError, resolve


@dataclass
class Change:
    """Un cambio validado, listo para pedir permiso y ejecutarse."""

    op: str
    paths: list[str]  # Rutas relativas afectadas (para el punto de restauración)
    summary: str  # Lo que verá el usuario en el diálogo de permiso
    targets: tuple[Path, ...]
    content: str | None = None


def _writable(folder: Folder):
    if not folder.writable:
        raise HandsError(
            f"La carpeta {folder.name!r} es de solo lectura (añade writable: true en config.yml)",
            403,
        )


def plan_write(
    folder: Folder, path: str, content: str, *, overwrite: bool, max_chars: int, denied=()
):
    _writable(folder)
    target, rel = resolve(folder, path, denied)
    if len(content) > max_chars:
        raise HandsError(f"Contenido demasiado largo (máximo {max_chars} caracteres)", 413)
    if target.is_dir():
        raise HandsError("Ya existe una carpeta con ese nombre", 409)
    if target.exists() and not overwrite:
        raise HandsError("El archivo ya existe (usa overwrite para reemplazarlo)", 409)
    verb = "Reemplazar" if target.exists() else "Crear"
    return Change("write", [rel], f"{verb} {rel} en {folder.name}", (target,), content)


def plan_move(folder: Folder, src: str, dest: str, *, denied=()):
    _writable(folder)
    source, src_rel = resolve(folder, src, denied)
    target, dest_rel = resolve(folder, dest, denied)
    if not source.is_file():
        raise HandsError("Solo se mueven archivos que existen (no carpetas)", 404)
    if target.exists():
        raise HandsError("El destino ya existe: MEKA no sobrescribe al mover", 409)
    return Change(
        "move",
        [src_rel, dest_rel],
        f"Mover {src_rel} → {dest_rel} en {folder.name}",
        (source, target),
    )


def plan_delete(folder: Folder, path: str, *, denied=()):
    _writable(folder)
    target, rel = resolve(folder, path, denied)
    if target.is_dir():
        raise HandsError("MEKA no borra carpetas enteras: borra los archivos uno a uno", 400)
    if not target.is_file():
        raise HandsError("No existe ese archivo", 404)
    return Change("delete", [rel], f"Borrar {rel} en {folder.name}", (target,))


def plan_mkdir(folder: Folder, path: str, *, denied=()):
    _writable(folder)
    target, rel = resolve(folder, path, denied)
    if target.exists():
        raise HandsError("Ya existe", 409)
    return Change("mkdir", [rel], f"Crear la carpeta {rel} en {folder.name}", (target,))


def apply(change: Change):
    """Ejecuta un cambio ya aprobado y respaldado."""
    if change.op == "write":
        (target,) = change.targets
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(change.content or "", encoding="utf-8")
    elif change.op == "move":
        source, target = change.targets
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
    elif change.op == "delete":
        change.targets[0].unlink()
    elif change.op == "mkdir":
        change.targets[0].mkdir(parents=True)
