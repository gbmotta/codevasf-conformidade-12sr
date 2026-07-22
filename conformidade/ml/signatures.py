"""
Detecção leve de assinatura/carimbo.

Prioridade:
  1. Assinatura digital criptográfica no PDF (sigflags / widget / PKCS#7)
  2. Menções textuais (incl. texto do carimbo via PyMuPDF)
  3. Heurística de tinta na faixa inferior — só em PDF/imagem escaneados

PDFs nativos (Word etc.) com assinatura ICP-Brasil costumam ter tinta≈0
e o pypdf omite o texto \"Assinado de forma digital…\" — daí o falso positivo.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path

_ASSIN_KW = (
    "assinatura",
    "assinado",
    "assinei",
    "firma",
    "rubrica",
    "eletronicamente",
    "certificado digital",
    "gov.br",
    "assinado de forma digital",
    "assinado digitalmente",
    "forma digital por",
    "documento assinado digitalmente",
    "icp-brasil",
    "icp brasil",
)
_CARIMBO_KW = ("carimbo", "selo", "autentic", "reconheciment")

_BORN_DIGITAL_MARKERS = (
    "word",
    "excel",
    "powerpoint",
    "libreoffice",
    "openoffice",
    "writer",
    "microsoft®",
    "microsoft office",
    "onlyoffice",
    "google docs",
)


@dataclass
class SignatureProbe:
    has_signature_hint: bool
    has_stamp_hint: bool
    ink_ratio_bottom: float | None
    confidence: float
    reason: str
    ink_applicable: bool = True
    digital_crypto: bool = False

    @property
    def seems_unsigned(self) -> bool:
        if self.has_signature_hint or self.has_stamp_hint or self.digital_crypto:
            return False
        # Tinta só vale para escaneados; PDF nativo sem carimbo de tinta ≠ sem assinatura.
        if (
            self.ink_applicable
            and self.ink_ratio_bottom is not None
            and self.ink_ratio_bottom < 0.012
        ):
            return True
        if self.ink_ratio_bottom is None and not self.has_signature_hint:
            return self.confidence >= 0.55
        return False


def _normalize(text: str) -> str:
    text = (text or "").lower()
    for a, b in (
        ("á", "a"),
        ("à", "a"),
        ("ã", "a"),
        ("â", "a"),
        ("é", "e"),
        ("ê", "e"),
        ("í", "i"),
        ("ó", "o"),
        ("ô", "o"),
        ("õ", "o"),
        ("ú", "u"),
        ("ç", "c"),
    ):
        text = text.replace(a, b)
    return text


def _ink_ratio_bottom(img, fraction: float = 0.28) -> float:
    from PIL import ImageOps

    gray = ImageOps.grayscale(img)
    w, h = gray.size
    if h < 40 or w < 40:
        return 0.0
    top = int(h * (1.0 - fraction))
    crop = gray.crop((0, top, w, h))
    hist = crop.histogram()
    dark = sum(hist[:110])
    total = max(sum(hist), 1)
    return dark / total


def probe_signature_text(text: str) -> tuple[bool, bool]:
    body = _normalize(text)
    has_sig = False
    for k in _ASSIN_KW:
        if " " in k:
            if k in body:
                has_sig = True
                break
        elif re.search(rf"\b{re.escape(k)}\b", body):
            has_sig = True
            break
    has_stamp = any(re.search(rf"\b{re.escape(k)}\b", body) for k in _CARIMBO_KW)
    if re.search(r"sem\s+assinatura|nao\s+assinad", body):
        has_sig = False
    # Padrão comum do Adobe/ICP: NOME:CPF na aparência da assinatura
    if re.search(r"\b[a-z][a-z\s]{3,80}:\d{11}\b", body) and (
        "digital" in body or "assinad" in body
    ):
        has_sig = True
    return has_sig, has_stamp


def _fitz_page_text(file_path: Path) -> str:
    try:
        import fitz
    except ImportError:
        return ""
    try:
        doc = fitz.open(str(file_path))
        try:
            return "\n".join(page.get_text() for page in doc)
        finally:
            doc.close()
    except Exception:
        return ""


def probe_pdf_digital_signature(file_path: Path | None) -> tuple[bool, str]:
    """Detecta assinatura digital embutida no PDF (não depende de OCR/tinta)."""
    if file_path is None or file_path.suffix.lower() != ".pdf" or not file_path.is_file():
        return False, ""
    try:
        import fitz
    except ImportError:
        fitz = None  # type: ignore

    if fitz is not None:
        try:
            doc = fitz.open(str(file_path))
            try:
                flags = doc.get_sigflags()
                if isinstance(flags, int) and flags > 0:
                    return True, f"Assinatura digital no PDF (sigflags={flags})."
                for page in doc:
                    for widget in page.widgets() or []:
                        ftype = getattr(widget, "field_type_string", "") or ""
                        if ftype.lower() == "signature" or getattr(widget, "field_type", None) == 6:
                            name = getattr(widget, "field_name", "") or "Signature"
                            signed = getattr(widget, "is_signed", None)
                            if signed is False:
                                continue
                            return True, f"Campo de assinatura digital assinado ({name})."
            finally:
                doc.close()
        except Exception:
            pass

    try:
        raw = file_path.read_bytes()
    except Exception:
        return False, ""
    if b"/ByteRange" in raw and (
        b"adbe.pkcs7" in raw
        or b"/Type /Sig" in raw
        or b"/Filter /Adobe.PPKLite" in raw
        or b"/Filter/Adobe.PPKLite" in raw
    ):
        return True, "Assinatura digital embutida no PDF (PKCS#7 / ByteRange)."
    return False, ""


def _pdf_is_born_digital(file_path: Path | None) -> bool:
    if file_path is None or file_path.suffix.lower() != ".pdf":
        return False
    try:
        import fitz

        doc = fitz.open(str(file_path))
        try:
            meta = doc.metadata or {}
            blob = _normalize(
                " ".join(str(meta.get(k) or "") for k in ("creator", "producer", "title"))
            )
            if any(m in blob for m in _BORN_DIGITAL_MARKERS):
                return True
        finally:
            doc.close()
    except Exception:
        pass
    return False


def probe_signature(
    *,
    text: str = "",
    image=None,
    file_path: Path | None = None,
    extraction_method: str | None = None,
) -> SignatureProbe:
    path = Path(file_path) if file_path else None

    # 1) Criptografia / widget PDF
    crypto_ok, crypto_reason = probe_pdf_digital_signature(path)
    if crypto_ok:
        return SignatureProbe(
            True,
            False,
            None,
            0.95,
            crypto_reason,
            ink_applicable=False,
            digital_crypto=True,
        )

    # 2) Texto (loader + PyMuPDF — pypdf omite aparência da assinatura)
    merged = text or ""
    if path is not None and path.suffix.lower() == ".pdf":
        fitz_text = _fitz_page_text(path)
        if fitz_text and len(fitz_text) > len(merged):
            merged = f"{merged}\n{fitz_text}"

    has_sig, has_stamp = probe_signature_text(merged)
    ink = None
    img = image
    born_digital = _pdf_is_born_digital(path)
    scanned = (extraction_method or "").lower() in {"ocr", "hibrido"}

    if img is None and path is not None:
        suffix = path.suffix.lower()
        try:
            if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
                from PIL import Image

                with Image.open(path) as im:
                    img = im.convert("RGB")
                scanned = True
            elif suffix == ".pdf" and (scanned or not born_digital):
                # Só renderiza para tinta se parecer escaneado (não Word nativo).
                if not born_digital:
                    import fitz
                    from PIL import Image

                    doc = fitz.open(str(path))
                    try:
                        if len(doc):
                            page = doc[-1]
                            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                    finally:
                        doc.close()
        except Exception:
            img = None

    ink_applicable = bool(scanned or (img is not None and not born_digital))
    if born_digital:
        ink_applicable = scanned  # OCR explícito sobre PDF Word é raro

    if img is not None and ink_applicable:
        try:
            ink = _ink_ratio_bottom(img)
        except Exception:
            ink = None

    text_len = len((merged or "").strip())
    expect = min(0.9, 0.3 + text_len / 2000)

    if has_sig or has_stamp:
        return SignatureProbe(
            True,
            has_stamp,
            ink,
            0.85,
            "Menção a assinatura/carimbo ou certificado digital no texto.",
            ink_applicable=ink_applicable,
        )
    if ink is not None and ink >= 0.025:
        return SignatureProbe(
            True,
            False,
            ink,
            0.65,
            f"Faixa inferior com tinta (razão={ink:.3f}) — possível assinatura/carimbo.",
            ink_applicable=True,
        )
    if ink_applicable and ink is not None and ink < 0.012 and text_len > 200:
        return SignatureProbe(
            False,
            False,
            ink,
            expect,
            f"Pouca tinta na faixa inferior (razão={ink:.3f}) e sem menção a assinatura.",
            ink_applicable=True,
        )
    if born_digital and text_len > 200 and not has_sig:
        return SignatureProbe(
            False,
            False,
            ink,
            0.35,
            "PDF nativo sem indício textual de assinatura (heurística de tinta não aplicável).",
            ink_applicable=False,
        )
    if text_len > 400 and not has_sig:
        return SignatureProbe(
            False,
            False,
            ink,
            expect if not born_digital else 0.4,
            "Documento longo sem indício textual de assinatura/carimbo.",
            ink_applicable=ink_applicable,
        )
    return SignatureProbe(
        has_sig,
        has_stamp,
        ink,
        0.3,
        "Indícios insuficientes para afirmar ausência de assinatura.",
        ink_applicable=ink_applicable,
    )


SIGNATURE_REQUIRED_HINTS = frozenset(
    {
        "oficio",
        "doacao_onerosa",
        "posse",
        "ata_diretoria",
        "estatuto",
        "plano_uso",
    }
)
