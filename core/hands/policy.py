"""Política de las "manos": qué carpetas puede tocar MEKA y qué nunca, aunque esté dentro.

    hands:
      folders:
        descargas: "~/Downloads"                     # Nombre → ruta
        notas: {path: "~/Documents/Notas", private: true}  # private: el MCP no la ve
        orden: {path: "~/Ordenar", writable: true}         # Admite cambios (con permiso)

Reglas (VISION.md, «Seguridad de las manos»):
- Solo carpetas autorizadas. Cualquier ruta se resuelve (`..`, enlaces simbólicos) y si sale
  de la carpeta, se rechaza.
- Archivos sensibles siempre denegados (`.env`, llaves, `.git`, gestores de contraseñas...).
"""

import fnmatch
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

# Nunca se listan ni se leen, en ninguna carpeta (se comparan sin distinguir mayúsculas)
ALWAYS_DENIED = (
    ".git", ".svn", ".hg", ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "*.kdbx",
    "*.keychain*", "id_rsa*", "id_ed25519*", "id_ecdsa*", "*.ovpn", ".ssh", ".gnupg", ".aws",
    "credentials*", "*.sqlite", "*.db", "*.db-wal", "*.db-shm",
)  # fmt: skip
# Se saltan al recorrer (pesados y sin interés), pero se pueden abrir a propósito
SKIPPED_DIRS = frozenset(
    {"node_modules", "venv", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
)


class HandsError(Exception):
    """Acción no permitida o imposible. `status` sugiere el código HTTP."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Folder:
    name: str
    root: Path
    private: bool = False
    writable: bool = False  # Solo lectura por defecto

    def public(self) -> dict:
        return {
            "name": self.name,
            "private": self.private,
            "writable": self.writable,
            "exists": self.root.is_dir(),
        }


def parse_folders(config: dict) -> dict[str, Folder]:
    folders = {}
    for name, entry in ((config.get("hands") or {}).get("folders") or {}).items():
        entry = {"path": entry} if isinstance(entry, str) else dict(entry or {})
        if not entry.get("path"):
            continue
        root = Path(entry["path"]).expanduser().resolve()
        folders[str(name)] = Folder(
            str(name), root, bool(entry.get("private", False)), bool(entry.get("writable", False))
        )
    return folders


def inside(folder: Folder, path: Path) -> bool:
    """¿La ruta, siguiendo enlaces simbólicos, sigue dentro de la carpeta autorizada?"""
    try:
        target = path.resolve()
    except OSError:
        return False
    return target == folder.root or folder.root in target.parents


def is_denied(relative: PurePosixPath, extra: tuple[str, ...] = ()) -> bool:
    patterns = ALWAYS_DENIED + extra
    return any(
        fnmatch.fnmatch(part.lower(), pattern.lower())
        for part in relative.parts
        for pattern in patterns
    )


def resolve(folder: Folder, path: str, extra_denied: tuple[str, ...] = ()) -> tuple[Path, str]:
    """Ruta absoluta segura dentro de `folder` y su forma relativa (para mostrar)."""
    raw = (path or ".").replace("\\", "/").strip()
    if raw.startswith("/") or (len(raw) > 1 and raw[1] == ":"):
        raise HandsError("Usa rutas relativas a la carpeta autorizada", 400)
    target = (folder.root / raw).resolve()  # resolve() sigue enlaces: un enlace que escape se nota
    if target != folder.root and folder.root not in target.parents:
        raise HandsError("La ruta sale de la carpeta autorizada", 403)
    relative = PurePosixPath(target.relative_to(folder.root).as_posix())
    if is_denied(relative, extra_denied):
        raise HandsError("Ese archivo está protegido y MEKA nunca lo toca", 403)
    return target, "." if str(relative) == "." else str(relative)
