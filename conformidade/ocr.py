"""
OCR de PDFs escaneados e imagens (Tesseract + fallback opcional EasyOCR).

Melhorias em relação ao fluxo antigo:
- DPI alto (350), idioma ``por+eng``
- Pré-processamento (cinza, contraste, nitidez, binarização adaptativa leve)
- Correção de orientação (OSD) e tentativas de deskew
- Múltiplos PSM do Tesseract, escolhendo o melhor resultado
- OCR **por página** (só páginas com texto nativo pobre)
- Fallback EasyOCR se instalado e o Tesseract extrair pouco texto

Variáveis de ambiente:
  OCR_DPI, OCR_MAX_PAGES, OCR_LANG, OCR_PSM, OCR_ENGINE (tesseract|easyocr|auto),
  OCR_MIN_CHARS (limiar de qualidade), TESSERACT_CMD
"""

from __future__ import annotations

import io
import os
import re
import shutil
from functools import lru_cache
from pathlib import Path

# Abaixo deste limiar de caracteres por página → página precisa de OCR
PDF_PAGE_OCR_CHAR_THRESHOLD = 40
# Limite de páginas processadas por arquivo
OCR_MAX_PAGES = int(os.getenv("OCR_MAX_PAGES", "40"))
OCR_DPI = int(os.getenv("OCR_DPI", "350"))
OCR_LANG = os.getenv("OCR_LANG", "por+eng")
OCR_PSM = os.getenv("OCR_PSM", "6")  # bloco uniforme de texto
OCR_ENGINE = os.getenv("OCR_ENGINE", "tesseract").strip().lower()  # tesseract | easyocr | auto
# Se Tesseract extrair menos que isto (página/imagem), tenta EasyOCR no modo auto
OCR_MIN_CHARS = int(os.getenv("OCR_MIN_CHARS", "50"))
OCR_PREPROCESS = os.getenv("OCR_PREPROCESS", "1").strip() not in {"0", "false", "False", "no"}
# OSD/orientação: útil, mas lento — ligado por padrão só se OCR_OSD=1
OCR_OSD = os.getenv("OCR_OSD", "0").strip() not in {"0", "false", "False", "no"}
# EasyOCR no modo auto exige OCR_ALLOW_EASYOCR=1 (pesado; evita cold start no Space)
OCR_ALLOW_EASYOCR = os.getenv("OCR_ALLOW_EASYOCR", "0").strip() not in {
    "0",
    "false",
    "False",
    "no",
}


def _apply_yaml_ocr_defaults() -> None:
    """Aplica defaults de config.yaml se a variável de ambiente correspondente não existir."""
    global OCR_MAX_PAGES, OCR_DPI, OCR_LANG, OCR_ENGINE, OCR_PREPROCESS, OCR_OSD, OCR_ALLOW_EASYOCR
    try:
        import yaml
    except ImportError:
        return
    cfg_path = Path(__file__).resolve().parent.parent / "config.yaml"
    if not cfg_path.is_file():
        return
    try:
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return
    ocr_cfg = data.get("ocr") or {}
    if "OCR_DPI" not in os.environ and ocr_cfg.get("dpi") is not None:
        OCR_DPI = int(ocr_cfg["dpi"])
    if "OCR_MAX_PAGES" not in os.environ and ocr_cfg.get("max_pages") is not None:
        OCR_MAX_PAGES = int(ocr_cfg["max_pages"])
    if "OCR_LANG" not in os.environ and ocr_cfg.get("lang"):
        OCR_LANG = str(ocr_cfg["lang"])
    if "OCR_ENGINE" not in os.environ and ocr_cfg.get("engine"):
        OCR_ENGINE = str(ocr_cfg["engine"]).strip().lower()
    if "OCR_PREPROCESS" not in os.environ and "preprocess" in ocr_cfg:
        OCR_PREPROCESS = bool(ocr_cfg["preprocess"])
    if "OCR_OSD" not in os.environ and "osd" in ocr_cfg:
        OCR_OSD = bool(ocr_cfg["osd"])
    if "OCR_ALLOW_EASYOCR" not in os.environ and "allow_easyocr" in ocr_cfg:
        OCR_ALLOW_EASYOCR = bool(ocr_cfg["allow_easyocr"])


_apply_yaml_ocr_defaults()


def _configure_tesseract() -> str | None:
    """Localiza o binário do Tesseract e configura pytesseract."""
    import pytesseract

    candidates = [
        os.environ.get("TESSERACT_CMD"),
        shutil.which("tesseract"),
        "/home/gab/miniconda3/bin/tesseract",
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            pytesseract.pytesseract.tesseract_cmd = candidate
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
            "(apt install tesseract-ocr tesseract-ocr-por tesseract-ocr-eng)"
        )

    try:
        version = pytesseract.get_tesseract_version()
    except Exception as exc:
        return False, f"Tesseract encontrado em {cmd}, mas falhou ao iniciar: {exc}"

    langs_note = ""
    try:
        langs = set(pytesseract.get_languages(config=""))
        missing = [x for x in ("por", "eng") if x not in langs]
        if "por" not in langs:
            return True, (
                f"Tesseract {version} OK, mas idioma 'por' ausente (tesseract-ocr-por)"
            )
        if missing:
            langs_note = f", faltando: {', '.join(missing)}"
        else:
            langs_note = ", por+eng"
    except Exception:
        langs_note = ""

    easy = " + EasyOCR" if _easyocr_importable() else ""
    return True, f"OCR disponível (Tesseract {version}{langs_note}{easy}; DPI={OCR_DPI})"


def _easyocr_importable() -> bool:
    try:
        import easyocr  # noqa: F401

        return True
    except ImportError:
        return False


@lru_cache(maxsize=1)
def _easyocr_reader():
    """Lazy-load EasyOCR (pesado). Só português + inglês."""
    import easyocr

    # gpu=False: compatível com CPU / Spaces sem GPU dedicada ao OCR
    return easyocr.Reader(["pt", "en"], gpu=False, verbose=False)


def _resolve_lang(preferred: str | None = None) -> str:
    """Escolhe idioma disponível: por+eng → por → eng."""
    import pytesseract

    preferred = preferred or OCR_LANG
    try:
        langs = set(pytesseract.get_languages(config=""))
    except Exception:
        return "por" if preferred.startswith("por") else preferred.split("+")[0]

    candidates = [preferred, "por+eng", "por", "eng"]
    seen: set[str] = set()
    for cand in candidates:
        if cand in seen:
            continue
        seen.add(cand)
        parts = cand.split("+")
        if all(p in langs for p in parts):
            return cand
    return "por"


def _preprocess_image(img):
    """Melhora contraste/legibilidade para Tesseract (Pillow puro)."""
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Escala mínima: imagens muito pequenas (foto de celular baixa) → upscale
    w, h = img.size
    min_side = min(w, h)
    if min_side < 1000:
        scale = 1000 / min_side
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    gray = ImageOps.grayscale(img)
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = ImageEnhance.Contrast(gray).enhance(1.4)
    gray = ImageEnhance.Sharpness(gray).enhance(1.3)
    # Suaviza ruído de scan antes do limiar
    gray = gray.filter(ImageFilter.MedianFilter(size=3))

    # Binarização leve (pontos médios) — ajuda documentos escuros
    try:
        bw = gray.point(lambda x: 255 if x > 160 else 0, mode="1").convert("L")
        # Se a página ficar quase toda preta/branca, descarta e usa cinza
        hist = bw.histogram()
        black = sum(hist[:20])
        white = sum(hist[235:])
        total = max(sum(hist), 1)
        if 0.02 < black / total < 0.85 and 0.02 < white / total < 0.95:
            return bw
    except Exception:
        pass
    return gray


def _fix_orientation(img):
    """Gira conforme OSD do Tesseract (opcional; OCR_OSD=1)."""
    if not OCR_OSD:
        return img
    import pytesseract

    try:
        osd = pytesseract.image_to_osd(img)
        match = re.search(r"Rotate:\s*(\d+)", osd)
        if match:
            angle = int(match.group(1)) % 360
            if angle:
                return img.rotate(-angle, expand=True, fillcolor=255)
    except Exception:
        pass
    return img


def _score_ocr_text(text: str) -> float:
    """Pontua qualidade aproximada do texto OCR (mais letras/números = melhor)."""
    text = (text or "").strip()
    if not text:
        return 0.0
    alnum = sum(1 for c in text if c.isalnum())
    spaces = text.count(" ")
    # Penaliza lixo de símbolos
    junk = sum(1 for c in text if c in "|[]{}<>~`^")
    return alnum + 0.3 * spaces - 2.0 * junk


def _tesseract_once(img, lang: str, psm: str) -> str:
    import pytesseract

    config = f"--oem 3 --psm {psm}"
    return pytesseract.image_to_string(img, lang=lang, config=config) or ""


def _ocr_tesseract(img, idioma: str | None = None) -> str:
    """Tesseract com pré-processamento, orientação e vários PSM."""
    from PIL import Image

    if not _configure_tesseract():
        return ""
    lang = _resolve_lang(idioma)

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    work = _fix_orientation(img)
    primary = _preprocess_image(work) if OCR_PREPROCESS else work
    best_text = ""
    best_score = -1.0

    def _try(cand, psm: str) -> bool:
        """Atualiza best; retorna True se já está bom o bastante."""
        nonlocal best_text, best_score
        try:
            text = _tesseract_once(cand, lang, psm).strip()
        except Exception:
            if "+" not in lang:
                return False
            try:
                text = _tesseract_once(cand, "por", psm).strip()
            except Exception:
                return False
        score = _score_ocr_text(text)
        if score > best_score:
            best_score = score
            best_text = text
        return len(best_text) >= max(OCR_MIN_CHARS * 3, 180) and best_score > 70

    # 1) caminho rápido: preprocess + PSM principal
    if _try(primary, OCR_PSM or "6"):
        return best_text

    # 2) imagem original (às vezes binarização piora)
    if OCR_PREPROCESS and _try(work, OCR_PSM or "6"):
        return best_text

    # 3) outros PSM
    for psm in ("4", "3"):
        if psm == (OCR_PSM or "6"):
            continue
        if _try(primary, psm):
            return best_text

    # 4) deskew leve só se ainda fraco
    if OCR_PREPROCESS and len(best_text) < OCR_MIN_CHARS * 2:
        for angle in (-2.5, 2.5):
            try:
                skewed = primary.rotate(
                    angle,
                    expand=True,
                    fillcolor=255,
                    resample=Image.Resampling.BICUBIC,
                )
            except Exception:
                continue
            if _try(skewed, OCR_PSM or "6"):
                return best_text

    return best_text


def page_native_texts(path: Path) -> list[str]:
    """Texto nativo por página (PyMuPDF)."""
    return _page_native_texts_fitz(path)


def page_needs_ocr(native: str) -> bool:
    return _page_needs_ocr(native)


def _ocr_easyocr(img) -> str:
    """Fallback EasyOCR (opcional)."""
    import numpy as np

    reader = _easyocr_reader()
    if img.mode != "RGB":
        img = img.convert("RGB")
    arr = np.asarray(img)
    lines = reader.readtext(arr, detail=0, paragraph=True)
    if isinstance(lines, list):
        return "\n".join(str(x) for x in lines if str(x).strip())
    return str(lines or "")


def ocr_pil_image(img, idioma: str | None = None) -> str:
    """OCR de uma imagem PIL: Tesseract e, se habilitado, EasyOCR."""
    engine = OCR_ENGINE
    tess_text = ""

    if engine in {"tesseract", "auto"}:
        try:
            tess_text = _ocr_tesseract(img, idioma).strip()
        except Exception:
            tess_text = ""

    allow_easy = engine == "easyocr" or (
        engine == "auto" and OCR_ALLOW_EASYOCR and _easyocr_importable()
    )
    use_easy = allow_easy and (
        engine == "easyocr" or len(tess_text) < OCR_MIN_CHARS
    )
    if use_easy:
        try:
            easy_text = _ocr_easyocr(img).strip()
            if _score_ocr_text(easy_text) > _score_ocr_text(tess_text):
                return easy_text
        except Exception:
            pass

    return tess_text


def _page_native_texts_fitz(path: Path) -> list[str]:
    import fitz

    doc = fitz.open(str(path))
    try:
        return [(doc[i].get_text("text") or "").strip() for i in range(len(doc))]
    finally:
        doc.close()


def _page_needs_ocr(native: str) -> bool:
    text = (native or "").strip()
    if not text:
        return True
    return len(text) < PDF_PAGE_OCR_CHAR_THRESHOLD


def ocr_pdf(path: Path, idioma: str | None = None, dpi: int | None = None) -> tuple[str, str]:
    """
    Extrai texto de PDF com OCR por página quando necessário.

    Retorna (conteúdo, método) com método em {texto, ocr, hibrido, vazio}.
    """
    import fitz
    from PIL import Image

    dpi = dpi or OCR_DPI
    escala = dpi / 72
    mat = fitz.Matrix(escala, escala)

    try:
        native_pages = _page_native_texts_fitz(path)
    except Exception:
        native_pages = []

    doc = fitz.open(str(path))
    try:
        n_pages = len(doc)
        if not native_pages:
            native_pages = [""] * n_pages

        total = min(n_pages, OCR_MAX_PAGES)
        parts: list[str] = []
        used_ocr = False
        used_native = False

        for i in range(total):
            native = native_pages[i] if i < len(native_pages) else ""
            if not _page_needs_ocr(native):
                parts.append(f"[Página {i + 1}]\n{native}")
                used_native = True
                continue

            pix = doc[i].get_pixmap(matrix=mat, alpha=False)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = ocr_pil_image(img, idioma).strip()
            if text:
                parts.append(f"[Página {i + 1} — OCR]\n{text}")
                used_ocr = True
            elif native:
                parts.append(f"[Página {i + 1}]\n{native}")
                used_native = True

        if n_pages > OCR_MAX_PAGES:
            # Anexa texto nativo das páginas restantes, se houver
            rest_native = []
            for i in range(OCR_MAX_PAGES, n_pages):
                native = native_pages[i] if i < len(native_pages) else ""
                if native:
                    rest_native.append(f"[Página {i + 1}]\n{native}")
                    used_native = True
            if rest_native:
                parts.append(
                    f"[OCR limitado às primeiras {OCR_MAX_PAGES} de {n_pages} páginas; "
                    "demais com texto nativo quando existir.]"
                )
                parts.extend(rest_native)
            else:
                parts.append(
                    f"[OCR limitado às primeiras {OCR_MAX_PAGES} de {n_pages} páginas.]"
                )

        content = "\n\n".join(parts).strip()
        if used_ocr and used_native:
            method = "hibrido"
        elif used_ocr:
            method = "ocr"
        elif used_native:
            method = "texto"
        else:
            method = "vazio"
        return content, method
    finally:
        doc.close()


def ocr_image_file(path: Path, idioma: str | None = None) -> str:
    from PIL import Image

    with Image.open(path) as img:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        # Cópia: arquivo pode fechar
        return ocr_pil_image(img.copy(), idioma).strip()


def pdf_needs_any_ocr(native_text: str, page_count_hint: int | None = None) -> bool:
    """Decisão rápida: PDF inteiro parece precisar de OCR."""
    text = (native_text or "").strip()
    if not text:
        return True
    pages = max(page_count_hint or 1, 1)
    return len(text) < PDF_PAGE_OCR_CHAR_THRESHOLD * min(pages, 3)
