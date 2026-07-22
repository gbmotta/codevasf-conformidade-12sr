"""PaddleOCR opcional (intranet / Docker)."""

from __future__ import annotations

from functools import lru_cache


def paddle_importable() -> bool:
    try:
        import paddleocr  # noqa: F401

        return True
    except ImportError:
        return False


@lru_cache(maxsize=1)
def _paddle_reader():
    from paddleocr import PaddleOCR

    try:
        return PaddleOCR(use_angle_cls=True, lang="pt", show_log=False)
    except TypeError:
        return PaddleOCR(use_angle_cls=True, lang="pt")


def ocr_paddle(img) -> str:
    import numpy as np

    if img.mode != "RGB":
        img = img.convert("RGB")
    arr = np.asarray(img)
    reader = _paddle_reader()
    result = reader.ocr(arr, cls=True)
    lines: list[str] = []
    if not result:
        return ""
    for block in result:
        if not block:
            continue
        for item in block:
            try:
                text = item[1][0]
            except (IndexError, TypeError):
                continue
            if text and str(text).strip():
                lines.append(str(text).strip())
    return "\n".join(lines)
