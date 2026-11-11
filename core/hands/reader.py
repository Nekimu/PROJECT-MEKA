"""Lectura dentro de una carpeta autorizada: listar, leer y buscar (nunca escribir)."""

import os
import time
from pathlib import Path, PurePosixPath

from core.documents import DOCUMENT_EXTENSIONS, extract_text
from core.hands.policy import SKIPPED_DIRS, Folder, HandsError, inside, is_denied, resolve

# Se leen como texto aunque no sean "documentos"
TEXT_LIKE = frozenset({
    ".txt", ".md", ".csv", ".json", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".log", ".xml",
    ".html", ".css", ".js", ".ts", ".py", ".go", ".rs", ".java", ".c", ".h", ".cpp", ".sql",
    ".sh", ".bat", ".ps1",
})  # fmt: skip


def _entry(path: Path, folder: Folder) -> dict:
    stat = path.stat()
    return {
        "name": path.name,
        "path": path.relative_to(folder.root).as_posix(),
        "type": "dir" if path.is_dir() else "file",
        "size": None if path.is_dir() else stat.st_size,
        "modified": stat.st_mtime,
    }


def list_dir(folder: Folder, path: str, *, pattern: str | None, limit: int, denied=()) -> dict:
    target, relative = resolve(folder, path, denied)
    if not target.is_dir():
        raise HandsError("No es una carpeta", 404)
    entries = []
    for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        rel = PurePosixPath(child.relative_to(folder.root).as_posix())
        if is_denied(rel, denied) or (pattern and not child.match(pattern)):
            continue
        if not inside(folder, child):  # Enlace simbólico que apunta fuera: ni se muestra
            continue
        entries.append(_entry(child, folder))
        if len(entries) >= limit:
            break
    return {
        "folder": folder.name,
        "path": relative,
        "entries": entries,
        "truncated": len(entries) >= limit,
    }


def read_file(folder: Folder, path: str, *, max_chars: int, denied=()) -> dict:
    target, relative = resolve(folder, path, denied)
    if not target.is_file():
        raise HandsError("No existe o no es un archivo", 404)
    ext = target.suffix.lower()
    if ext in DOCUMENT_EXTENSIONS and ext not in TEXT_LIKE:  # PDF, DOCX, XLSX
        extracted = extract_text(target, max_chars)
        text, truncated = extracted.text, extracted.truncated
    else:
        with target.open("rb") as handle:
            raw = handle.read(max_chars * 4 + 1)
        if ext not in TEXT_LIKE and b"\0" in raw[:4096]:
            raise HandsError("Es un archivo binario: no se puede leer como texto", 415)
        text = raw.decode("utf-8", errors="replace")
        truncated = len(text) > max_chars or target.stat().st_size > len(raw)
        text = text[:max_chars]
    return {"folder": folder.name, "path": relative, "text": text, "truncated": truncated}


def search(
    folder: Folder, query: str, *, content: bool, limit: int, max_files: int, denied=()
) -> dict:
    """Busca por nombre y, con `content`, también dentro de los archivos de texto."""
    needle = query.lower().strip()
    if not needle:
        raise HandsError("La búsqueda está vacía", 400)
    matches, scanned, started = [], 0, time.monotonic()
    for dirpath, dirnames, filenames in os.walk(folder.root):
        base = Path(dirpath)
        rel_dir = PurePosixPath(base.relative_to(folder.root).as_posix())
        dirnames[:] = [
            d for d in dirnames if d not in SKIPPED_DIRS and not is_denied(rel_dir / d, denied)
        ]
        for name in filenames:
            rel = rel_dir / name
            if is_denied(rel, denied) or not inside(folder, base / name):
                continue  # Protegido, o enlace simbólico que apunta fuera de la carpeta
            scanned += 1
            hit = {"path": str(rel).removeprefix("./"), "line": None}
            if needle in name.lower():
                matches.append(hit)
            elif content and Path(name).suffix.lower() in TEXT_LIKE:
                line = _first_line_with(base / name, needle)
                if line is not None:
                    matches.append({**hit, "line": line})
            if len(matches) >= limit or scanned >= max_files:
                return _result(folder, query, matches, scanned, started, truncated=True)
    return _result(folder, query, matches, scanned, started, truncated=False)


def _first_line_with(path: Path, needle: str, max_bytes: int = 1_000_000) -> str | None:
    try:
        if path.stat().st_size > max_bytes:
            return None
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if needle in line.lower():
                    return line.strip()[:200]
    except OSError:
        return None
    return None


def _result(folder, query, matches, scanned, started, *, truncated) -> dict:
    return {
        "folder": folder.name,
        "query": query,
        "matches": matches,
        "scanned": scanned,
        "truncated": truncated,
        "elapsed_ms": int((time.monotonic() - started) * 1000),
    }
