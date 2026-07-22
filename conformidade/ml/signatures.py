"""
Detecção leve de assinatura/carimbo (heurística texto + tinta na faixa inferior).
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
)
_CARIMBO_KW = ("carimbo", "selo", "autentic", "reconheciment")


@dataclass
class SignatureProbe:
    has_signature_hint: bool
    has_stamp_hint: bool
    ink_ratio_bottom: float | None
    confidence: float
    reason: str

    @property
    def seems_unsigned(self) -> bool:
        if self.has_signature_hint or self.has_stamp_hint:
            return False
        if self.ink_ratio_bottom is not None and self.ink_ratio_bottom < 0.012:
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
    has_sig = any(re.search(rf"\b{re.escape(k)}\b", body) for k in _ASSIN_KW)
    has_stamp = any(re.search(rf"\b{re.escape(k)}\b", body) for k in _CARIMBO_KW)
    if re.search(r"sem\s+assinatura|nao\s+assinad", body):
        has_sig = False
    return has_sig, has_stamp


def probe_signature(
    *,
    text: str = "",
    image=None,
    file_path: Path | None = None,
) -> SignatureProbe:
    has_sig, has_stamp = probe_signature_text(text)
    ink = None
    img = image

    if img is None and file_path is not None:
        suffix = file_path.suffix.lower()
        try:
            if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
                from PIL import Image

                with Image.open(file_path) as im:
                    img = im.convert("RGB")
            elif suffix == ".pdf":
                import fitz
                from PIL import Image

                doc = fitz.open(str(file_path))
                try:
                    if len(doc):
                        page = doc[-1]
                        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                finally:
                    doc.close()
        except Exception:
            img = None

    if img is not None:
        try:
            ink = _ink_ratio_bottom(img)
        except Exception:
            ink = None

    text_len = len((text or "").strip())
    expect = min(0.9, 0.3 + text_len / 2000)

    if has_sig or has_stamp:
        return SignatureProbe(
            True,
            has_stamp,
            ink,
            0.85,
            "Menção a assinatura/carimbo ou certificado digital no texto.",
        )
    if ink is not None and ink >= 0.025:
        return SignatureProbe(
            True,
            False,
            ink,
            0.65,
            f"Faixa inferior com tinta (razão={ink:.3f}) — possível assinatura/carimbo.",
        )
    if ink is not None and ink < 0.012 and text_len > 200:
        return SignatureProbe(
            False,
            False,
            ink,
            expect,
            f"Pouca tinta na faixa inferior (razão={ink:.3f}) e sem menção a assinatura.",
        )
    if text_len > 400 and not has_sig:
        return SignatureProbe(
            False,
            False,
            ink,
            expect,
            "Documento longo sem indício textual de assinatura/carimbo.",
        )
    return SignatureProbe(
        has_sig,
        has_stamp,
        ink,
        0.3,
        "Indícios insuficientes para afirmar ausência de assinatura.",
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
