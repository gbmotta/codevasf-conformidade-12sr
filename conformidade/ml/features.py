"""
Features de texto para o classificador de documentos (sem LLM).
"""

from __future__ import annotations

import re
import unicodedata

from conformidade.loaders import LoadedDocument


def normalize_text(text: str) -> str:
    text = (text or "").lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9\s%./-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def document_feature_text(doc: LoadedDocument, content_chars: int = 3500) -> str:
    """Concatena nome do arquivo + trecho do conteúdo para TF-IDF."""
    name = normalize_text(f"{doc.file_name} {doc.relative_path}")
    body = normalize_text(doc.content[:content_chars])
    # Nome repetido dá mais peso a tokens do filename
    return f"{name} {name} {body}"


def feature_text_from_parts(file_name: str, content: str, content_chars: int = 3500) -> str:
    name = normalize_text(file_name)
    body = normalize_text((content or "")[:content_chars])
    return f"{name} {name} {body}"
