#!/usr/bin/env python3
"""
Treina o classificador de documentos (TF-IDF + LogisticRegression).

Uso:
  python scripts/train_doc_classifier.py
  python scripts/train_doc_classifier.py --csv data/ml/labels.csv
  python scripts/train_doc_classifier.py --from-seed
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conformidade.ml.classifier import (
    DEFAULT_MODEL_PATH,
    DocumentClassifier,
    load_training_csv,
)
from conformidade.ml.features import feature_text_from_parts
from conformidade.ml.seed_data import SEED_EXAMPLES


def _from_seed() -> tuple[list[str], list[str]]:
    texts, labels = [], []
    for file_name, content, label in SEED_EXAMPLES:
        texts.append(feature_text_from_parts(file_name, content))
        labels.append(label)
        # Leve aumento: duplica com pequena variação de nome
        texts.append(feature_text_from_parts(file_name.replace("_", " "), content))
        labels.append(label)
    return texts, labels


def main() -> None:
    parser = argparse.ArgumentParser(description="Treina classificador de documentos")
    parser.add_argument("--csv", type=Path, help="CSV gerado por export_doc_labels.py")
    parser.add_argument("--from-seed", action="store_true", help="Treina só com seed")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help="Caminho do .joblib",
    )
    args = parser.parse_args()

    if args.csv:
        texts, labels = load_training_csv(args.csv)
    else:
        texts, labels = _from_seed()
        args.from_seed = True

    clf = DocumentClassifier()
    metrics = clf.train(texts, labels)
    path = clf.save(args.out, meta={"metrics": metrics, "from_seed": bool(args.from_seed)})
    print("Modelo salvo:", path)
    print("Métricas:", metrics)
    print("Classes:", clf._labels)


if __name__ == "__main__":
    main()
