"""Extracción de texto de documentos enviados por el usuario (PDF, DOCX, XLSX, texto plano)."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp"})
TEXT_EXTENSIONS = frozenset({".txt", ".md", ".csv"})


class UnsupportedDocumentError(ValueError):
    """El formato del archivo no está soportado."""


@dataclass(frozen=True)
class ExtractedText:
    text: str
    truncated: bool


def _iter_pdf(path: Path) -> Iterator[str]:
    try:
        import pymupdf
    except ImportError:  # PyMuPDF < 1.24.3 solo expone el nombre antiguo
        import fitz as pymupdf

    with pymupdf.open(path) as doc:
        for page in doc:
            yield page.get_text()


def _iter_docx(path: Path) -> Iterator[str]:
    from docx import Document

    doc = Document(str(path))
    for paragraph in doc.paragraphs:
        yield paragraph.text
    for table in doc.tables:
        for row in table.rows:
            yield " | ".join(cell.text.strip() for cell in row.cells)


def _iter_xlsx(path: Path) -> Iterator[str]:
    from openpyxl import load_workbook

    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        for sheet in workbook.worksheets:
            yield f"# Hoja: {sheet.title}"
            for row in sheet.iter_rows(values_only=True):
                if any(value is not None for value in row):
                    yield "\t".join("" if value is None else str(value) for value in row)
    finally:
        workbook.close()


def _iter_text(path: Path) -> Iterator[str]:
    with path.open("r", encoding="utf-8", errors="replace") as f:
        while chunk := f.read(64 * 1024):
            yield chunk


EXTRACTORS: dict[str, Callable[[Path], Iterator[str]]] = {
    ".pdf": _iter_pdf,
    ".docx": _iter_docx,
    ".xlsx": _iter_xlsx,
    **{ext: _iter_text for ext in TEXT_EXTENSIONS},
}
DOCUMENT_EXTENSIONS = frozenset(EXTRACTORS)


def extract_text(path: str | Path, max_chars: int = 4000) -> ExtractedText:
    """
    Extrae el texto de un documento. Deja de leer en cuanto supera `max_chars`
    para no recorrer completo un PDF de cientos de páginas.
    """
    path = Path(path)
    extractor = EXTRACTORS.get(path.suffix.lower())
    if extractor is None:
        raise UnsupportedDocumentError(path.suffix)

    parts: list[str] = []
    total = 0
    for chunk in extractor(path):
        parts.append(chunk)
        total += len(chunk) + 1  # +1 por el salto de línea al unir
        if total - 1 > max_chars:
            break

    text = "\n".join(parts).strip()
    return ExtractedText(text=text[:max_chars], truncated=len(text) > max_chars)
