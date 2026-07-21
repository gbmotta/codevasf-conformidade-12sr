"""
ML clássico para conformidade documental (sem LLM).

- Classificação de tipo de documento (TF-IDF + logistic / heurística)
- Extração de CNPJ/CPF/datas/validade
- Matching item↔documento por similaridade
"""

from conformidade.ml.classifier import Classification, DocumentClassifier, classify_document, get_classifier
from conformidade.ml.extractors import ExtractedFields, extract_fields, validade_status
from conformidade.ml.schema import DocLabel, LABEL_DESCRIPTIONS, parse_label

__all__ = [
    "Classification",
    "DocLabel",
    "DocumentClassifier",
    "ExtractedFields",
    "LABEL_DESCRIPTIONS",
    "classify_document",
    "extract_fields",
    "get_classifier",
    "parse_label",
    "validade_status",
]
