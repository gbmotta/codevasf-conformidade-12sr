"""Carregamento de documentos a partir de ZIP, pasta ou arquivos avulsos.

Inclui OCR (Tesseract) para PDFs escaneados e imagens.
"""

from __future__ import annotations

import io
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_TEXT_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".doc"}
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
SUPPORTED_EXTENSIONS = SUPPORTED_TEXT_EXTENSIONS | SUPPORTED_IMAGE_EXTENSIONS

# Abaixo deste limiar de caracteres (média por página amostrada) aciona OCR
PDF_OCR_CHAR_THRESHOLD = 40
# Limite de páginas OCR por arquivo (evita travar em anexos enormes)
OCR_MAX_PAGES = 20
OCR_DPI = 200
OCR_LANG = "por"


@dataclass
class LoadedDocument:
    source: str
    content: str
    file_name: str
    relative_path: str
    extraction_method: str = "texto"  # texto | ocr | hibrido | vazio | erro


def _configure_tesseract() -> str | None:
    """Localiza o binário do Tesseract e configura pytesseract. Retorna o caminho ou None."""
    import os
    import shutil

    import pytesseract

    candidates = [
        os.environ.get("TESSERACT_CMD"),
        shutil.which("tesseract"),
        "/home/gab/miniconda3/bin/tesseract",
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            pytesseract.pytesseract.tesseract_cmd = candidate
            # tessdata ao lado da instalação conda, se existir
            tessdata = Path(candidate).resolve().parent.parent / "share" / "tessdata"
            if tessdata.is_dir() and not os.environ.get("TESSDATA_PREFIX"):
                os.environ["TESSDATA_PREFIX"] = str(tessdata)
            return candidate
    return None


def ocr_available() -> tuple[bool, str]:
    """Verifica se pymupdf + pytesseract + binário Tesseract estão utilizáveis."""
    try:
        import fitz  # noqa: F401
    except ImportError:
        return False, "pymupdf não instalado (pip install pymupdf)"

    try:
        import pytesseract
        from PIL import Image  # noqa: F401
    except ImportError:
        return False, "pytesseract/Pillow não instalados (pip install pytesseract pillow)"

    cmd = _configure_tesseract()
    if not cmd:
        return False, (
            "Tesseract não encontrado "
            "(apt install tesseract-ocr tesseract-ocr-por  ou  conda install -c conda-forge tesseract)"
        )

    try:
        version = pytesseract.get_tesseract_version()
    except Exception as exc:
        return False, f"Tesseract encontrado em {cmd}, mas falhou ao iniciar: {exc}"

    try:
        langs = pytesseract.get_languages(config="")
        if "por" not in langs:
            return True, f"Tesseract {version} OK, mas idioma 'por' ausente (tesseract-ocr-por)"
    except Exception:
        pass

    return True, f"OCR disponível (Tesseract {version}, idioma por)"


def _read_text_file(path: Path) -> str:
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _read_pdf_native(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)
    return "\n\n".join(pages)


def _pdf_needs_ocr(native_text: str, page_count_hint: int | None = None) -> bool:
    text = (native_text or "").strip()
    if not text:
        return True
    pages = max(page_count_hint or 1, 1)
    # Também considera OCR se o texto for muito pobre em relação ao nº de páginas
    return len(text) < PDF_OCR_CHAR_THRESHOLD * min(pages, 3)


def _ocr_image_pil(img, idioma: str = OCR_LANG) -> str:
    import pytesseract

    return pytesseract.image_to_string(img, lang=idioma) or ""


def _ocr_pdf(path: Path, idioma: str = OCR_LANG, dpi: int = OCR_DPI) -> str:
    import fitz
    from PIL import Image

    doc = fitz.open(str(path))
    try:
        escala = dpi / 72
        mat = fitz.Matrix(escala, escala)
        pages_text: list[str] = []
        total = min(len(doc), OCR_MAX_PAGES)
        for i in range(total):
            pix = doc[i].get_pixmap(matrix=mat, alpha=False)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = _ocr_image_pil(img, idioma).strip()
            if text:
                pages_text.append(f"[Página {i + 1} — OCR]\n{text}")
        if len(doc) > OCR_MAX_PAGES:
            pages_text.append(
                f"[OCR limitado às primeiras {OCR_MAX_PAGES} de {len(doc)} páginas.]"
            )
        return "\n\n".join(pages_text)
    finally:
        doc.close()


def _ocr_image_file(path: Path, idioma: str = OCR_LANG) -> str:
    from PIL import Image

    with Image.open(path) as img:
        # Converte para RGB quando necessário (ex.: PNG com alpha)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        return _ocr_image_pil(img, idioma).strip()


def _read_pdf(path: Path) -> tuple[str, str]:
    """Retorna (conteúdo, método). Método: texto | ocr | hibrido | vazio."""
    native = ""
    page_count = None
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        page_count = len(reader.pages)
        native = _read_pdf_native(path)
    except Exception:
        native = ""

    needs_ocr = _pdf_needs_ocr(native, page_count)
    if not needs_ocr:
        return native.strip(), "texto"

    ok, _msg = ocr_available()
    if not ok:
        if native.strip():
            return native.strip(), "texto"
        return (
            f"[Arquivo sem texto extraível e OCR indisponível: {path.name}. "
            "Instale: apt install tesseract-ocr tesseract-ocr-por && "
            "pip install pymupdf pytesseract pillow]",
            "vazio",
        )

    try:
        ocr_text = _ocr_pdf(path)
    except Exception as exc:
        if native.strip():
            return native.strip(), "texto"
        return f"[Falha no OCR de {path.name}: {exc}]", "erro"

    native_s = native.strip()
    ocr_s = (ocr_text or "").strip()
    if native_s and ocr_s and len(ocr_s) > len(native_s):
        # Mantém OCR como principal, anexa trecho nativo se ajudar
        return ocr_s, "ocr"
    if ocr_s:
        return ocr_s, "ocr"
    if native_s:
        return native_s, "texto"
    return f"[OCR não extraiu texto de {path.name}.]", "vazio"


def _read_docx(path: Path) -> str:
    from docx import Document

    document = Document(str(path))
    paragraphs = [
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]
    return "\n\n".join(paragraphs)


def load_file(path: Path, root: Path | None = None) -> LoadedDocument | None:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        return None

    method = "texto"
    try:
        if suffix == ".pdf":
            content, method = _read_pdf(path)
        elif suffix in SUPPORTED_IMAGE_EXTENSIONS:
            ok, msg = ocr_available()
            if not ok:
                content = f"[Imagem {path.name}: OCR indisponível — {msg}]"
                method = "vazio"
            else:
                content = _ocr_image_file(path)
                method = "ocr" if content.strip() else "vazio"
                if not content.strip():
                    content = f"[OCR não extraiu texto da imagem {path.name}.]"
        elif suffix in {".docx", ".doc"}:
            if suffix == ".doc":
                content = (
                    f"[Arquivo .doc binário: {path.name}. "
                    "Conteúdo não extraído automaticamente.]"
                )
                method = "vazio"
            else:
                content = _read_docx(path)
        else:
            content = _read_text_file(path)
    except Exception as exc:
        content = f"[Falha ao ler {path.name}: {exc}]"
        method = "erro"

    content = (content or "").strip()
    if not content:
        content = f"[Arquivo sem texto extraível: {path.name}.]"
        method = "vazio"

    rel = str(path.relative_to(root)) if root else path.name
    return LoadedDocument(
        source=str(path),
        content=content,
        file_name=path.name,
        relative_path=rel,
        extraction_method=method,
    )


def scan_folder(root: Path) -> list[LoadedDocument]:
    if not root.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Caminho não é uma pasta: {root}")

    documents: list[LoadedDocument] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name.startswith(".") or path.name.startswith("__MACOSX"):
            continue
        loaded = load_file(path, root=root)
        if loaded is not None:
            documents.append(loaded)
    return documents


def extract_zip(zip_path: Path, destination: Path) -> Path:
    """Extrai ZIP para destination e retorna a pasta raiz útil."""
    destination.mkdir(parents=True, exist_ok=True)
    extract_dir = destination / zip_path.stem
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(extract_dir)

    children = [p for p in extract_dir.iterdir() if not p.name.startswith("__MACOSX")]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return extract_dir


def load_from_zip(zip_path: Path, work_dir: Path) -> list[LoadedDocument]:
    if not zip_path.exists():
        raise FileNotFoundError(f"ZIP não encontrado: {zip_path}")
    root = extract_zip(zip_path, work_dir)
    return scan_folder(root)


def save_uploaded_bytes(file_name: str, data: bytes, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / file_name
    target.write_bytes(data)
    return target


def summarize_inventory(documents: list[LoadedDocument]) -> str:
    if not documents:
        return "(nenhum documento encontrado)"
    lines = []
    for doc in documents:
        lines.append(
            f"- {doc.relative_path} ({len(doc.content)} caracteres, método: {doc.extraction_method})"
        )
    ocr_count = sum(1 for d in documents if d.extraction_method == "ocr")
    if ocr_count:
        lines.append(f"\n({ocr_count} arquivo(s) lido(s) via OCR)")
    return "\n".join(lines)
