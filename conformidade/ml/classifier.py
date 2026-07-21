"""
Classificador de tipo de documento (TF-IDF + LogisticRegression).

Sem LLM. Se scikit-learn/joblib indisponíveis ou modelo ausente,
cai na heurística (``weak_label_document``).
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from conformidade.loaders import LoadedDocument
from conformidade.ml.features import document_feature_text, feature_text_from_parts
from conformidade.ml.heuristics import weak_label_document, weak_label_parts
from conformidade.ml.schema import DocLabel, parse_label

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
DEFAULT_MODEL_PATH = ARTIFACTS_DIR / "doc_classifier.joblib"
DEFAULT_META_PATH = ARTIFACTS_DIR / "doc_classifier_meta.json"


@dataclass
class Classification:
    label: DocLabel
    confidence: float
    source: str  # modelo | heuristica
    probabilities: dict[str, float] | None = None


class DocumentClassifier:
    """Wrapper treino/inferência. Thread-safe para leitura após load."""

    def __init__(self) -> None:
        self._pipeline = None
        self._labels: list[str] = []
        self._loaded_from: Path | None = None

    @property
    def ready(self) -> bool:
        return self._pipeline is not None

    def load(self, path: Path | None = None) -> bool:
        path = path or DEFAULT_MODEL_PATH
        try:
            import joblib
        except ImportError:
            return False
        if not path.is_file():
            return False
        try:
            obj = joblib.load(path)
            self._pipeline = obj["pipeline"]
            self._labels = list(obj.get("labels") or [])
            self._loaded_from = path
            return True
        except Exception:
            self._pipeline = None
            return False

    def save(self, path: Path | None = None, meta: dict | None = None) -> Path:
        import joblib

        path = path or DEFAULT_MODEL_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"pipeline": self._pipeline, "labels": self._labels}, path)
        meta_path = path.with_name(path.stem + "_meta.json")
        payload = {
            "labels": self._labels,
            "model_path": str(path),
            **(meta or {}),
        }
        meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._loaded_from = path
        return path

    def train(
        self,
        texts: list[str],
        labels: list[str],
        *,
        min_df: int = 1,
    ) -> dict:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        from sklearn.model_selection import cross_val_score
        import numpy as np

        if len(texts) < 2 or len(set(labels)) < 2:
            raise ValueError("Treino precisa de pelo menos 2 exemplos e 2 classes.")

        pipe = Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        ngram_range=(1, 2),
                        min_df=min_df,
                        max_features=12000,
                        sublinear_tf=True,
                    ),
                ),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        solver="lbfgs",
                    ),
                ),
            ]
        )
        pipe.fit(texts, labels)
        self._pipeline = pipe
        self._labels = sorted(set(labels))

        metrics: dict = {"n_samples": len(texts), "n_classes": len(self._labels)}
        # CV só se houver amostras suficientes por classe
        try:
            from collections import Counter

            counts = Counter(labels)
            if len(texts) >= 8 and min(counts.values()) >= 2:
                scores = cross_val_score(pipe, texts, labels, cv=min(3, min(counts.values())))
                metrics["cv_accuracy_mean"] = float(np.mean(scores))
                metrics["cv_accuracy_std"] = float(np.std(scores))
        except Exception:
            pass
        return metrics

    def predict_text(self, text: str, file_name: str = "") -> Classification:
        feat = feature_text_from_parts(file_name, text) if file_name else text
        if self._pipeline is not None:
            try:
                proba = self._pipeline.predict_proba([feat])[0]
                classes = list(self._pipeline.classes_)
                idx = int(proba.argmax())
                label = parse_label(str(classes[idx]))
                conf = float(proba[idx])
                probs = {str(c): float(p) for c, p in zip(classes, proba)}
                return Classification(label, conf, "modelo", probs)
            except Exception:
                pass
        # Fallback: monta LoadedDocument mínimo
        doc = LoadedDocument(
            source=file_name or "x",
            content=text,
            file_name=file_name or "doc.txt",
            relative_path=file_name or "doc.txt",
        )
        label, conf = weak_label_document(doc)
        return Classification(label, conf, "heuristica")

    def predict_document(self, doc: LoadedDocument) -> Classification:
        if self._pipeline is not None:
            feat = document_feature_text(doc)
            try:
                proba = self._pipeline.predict_proba([feat])[0]
                classes = list(self._pipeline.classes_)
                idx = int(proba.argmax())
                label = parse_label(str(classes[idx]))
                conf = float(proba[idx])
                probs = {str(c): float(p) for c, p in zip(classes, proba)}
                weak_label, weak_conf = weak_label_document(doc)
                # FOR-198 nunca vira onerosa
                if (
                    weak_label == DocLabel.IMPEDIMENTO
                    and weak_conf >= 0.8
                    and label == DocLabel.DOACAO_ONEROSA
                ):
                    return Classification(DocLabel.IMPEDIMENTO, weak_conf, "heuristica")
                # Modelo e heurística concordam → aceita (confiança calibrada)
                if label == weak_label:
                    return Classification(
                        label,
                        max(conf, 0.5 * conf + 0.5 * weak_conf),
                        "modelo",
                        probs,
                    )
                # Modelo inseguro → heurística forte
                if conf < 0.35 and weak_conf >= 0.55:
                    return Classification(weak_label, weak_conf, "heuristica")
                return Classification(label, conf, "modelo", probs)
            except Exception:
                pass
        label, conf = weak_label_document(doc)
        return Classification(label, conf, "heuristica")

    def probability_for(self, doc: LoadedDocument, label: DocLabel) -> float:
        pred = self.predict_document(doc)
        if pred.probabilities and label.value in pred.probabilities:
            return pred.probabilities[label.value]
        if pred.label == label:
            return pred.confidence
        return 0.0


_CLASSIFIER: DocumentClassifier | None = None


def get_classifier(load: bool = True) -> DocumentClassifier:
    global _CLASSIFIER
    if _CLASSIFIER is None:
        _CLASSIFIER = DocumentClassifier()
        if load:
            _CLASSIFIER.load()
    return _CLASSIFIER


def classify_document(doc: LoadedDocument) -> Classification:
    return get_classifier().predict_document(doc)


def load_training_csv(path: Path) -> tuple[list[str], list[str]]:
    """CSV com colunas: file_name, content, label (ou text, label). Ignora label vazio."""
    texts: list[str] = []
    labels: list[str] = []
    skipped = 0
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            raw_label = (row.get("label") or row.get("rotulo") or "").strip()
            if not raw_label:
                skipped += 1
                continue
            label = parse_label(raw_label).value
            if "text" in row and row["text"]:
                texts.append(row["text"])
            else:
                texts.append(
                    feature_text_from_parts(
                        row.get("file_name") or row.get("arquivo") or "",
                        row.get("content") or row.get("conteudo") or "",
                    )
                )
            labels.append(label)
    if skipped:
        print(f"(ignoradas {skipped} linhas sem label)")
    return texts, labels
