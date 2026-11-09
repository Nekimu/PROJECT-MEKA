import pytest

from core.documents import UnsupportedDocumentError, extract_text


def test_txt(tmp_path):
    path = tmp_path / "nota.txt"
    path.write_text("Hola MEKA ✨", encoding="utf-8")
    result = extract_text(path)
    assert result.text == "Hola MEKA ✨" and not result.truncated


def test_truncates_and_flags(tmp_path):
    path = tmp_path / "largo.md"
    path.write_text("x" * 10_000, encoding="utf-8")
    result = extract_text(path, max_chars=100)
    assert len(result.text) == 100 and result.truncated


def test_docx_includes_tables(tmp_path):
    from docx import Document

    doc = Document()
    doc.add_paragraph("Lista de cosplays")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Shizuku"
    table.rows[0].cells[1].text = "Terminado"
    path = tmp_path / "plan.docx"
    doc.save(path)

    text = extract_text(path).text
    assert "Lista de cosplays" in text and "Shizuku | Terminado" in text


def test_xlsx_without_pandas(tmp_path):
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Gastos"
    sheet.append(["Tela", 25.5])
    sheet.append([None, None])
    path = tmp_path / "gastos.xlsx"
    workbook.save(path)

    assert extract_text(path).text == "# Hoja: Gastos\nTela\t25.5"


def test_pdf(tmp_path):
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Hola desde un PDF")
    path = tmp_path / "doc.pdf"
    doc.save(path)
    doc.close()

    assert "Hola desde un PDF" in extract_text(path).text


@pytest.mark.parametrize("name", ["viejo.doc", "viejo.xls", "binario.exe"])
def test_unsupported_formats(tmp_path, name):
    path = tmp_path / name
    path.write_bytes(b"\x00")
    with pytest.raises(UnsupportedDocumentError):
        extract_text(path)
