"""
Matching item do checklist ↔ documentos via TF-IDF (sem LLM).
"""

from __future__ import annotations

from conformidade.checklist import ChecklistItem
from conformidade.loaders import LoadedDocument
from conformidade.ml.features import document_feature_text, normalize_text
from conformidade.ml.schema import HINT_TO_LABEL, INCOMPATIBLE, DocLabel


def _hints_for_item(descricao: str) -> list[str]:
    desc = normalize_text(descricao)
    mapping = [
        (("oficio",), "oficio"),
        (("cnpj",), "cnpj"),
        (("tributos federais", "divida ativa", "certidao conjunta"), "federal"),
        (("fgts",), "fgts"),
        (("trabalhista", "cndt"), "cndt"),
        (("ata de posse", "termo de transmissao"), "posse"),
        (("diploma",), "diploma"),
        (("cedula de identidade", "documentos pessoais", "cpf do prefeito"), "rg_cpf"),
        (("votacao", "quitacao eleitoral", "titulo eleitoral"), "eleitoral"),
        (("comprovante de residencia", "comprovante de endereco"), "residencia"),
        (("doacao onerosa", "contrapartida"), "doacao_onerosa"),
        (("plano de uso",), "plano_uso"),
        (("estatuto", "contrato social"), "estatuto"),
        (("ata de criacao", "eleicao da diretoria", "diretoria/presidencia"), "ata_diretoria"),
    ]
    keys: list[str] = []
    for needles, key in mapping:
        if any(n in desc for n in needles):
            keys.append(key)
    return keys


def rank_documents_for_item(
    item: ChecklistItem,
    documents: list[LoadedDocument],
    *,
    limit: int = 4,
) -> list[tuple[LoadedDocument, float]]:
    """
    Ranqueia documentos por similaridade TF-IDF com a descrição do item
    + boost do classificador/heurística para o rótulo esperado.
    """
    if not documents:
        return []

    hints = _hints_for_item(item.descricao)
    expected: DocLabel | None = HINT_TO_LABEL.get(hints[0]) if hints else None

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer

        query = normalize_text(item.descricao)
        corpus = [document_feature_text(d) for d in documents]
        vect = TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=8000)
        mat = vect.fit_transform([query] + corpus)
        q = mat[0]
        docs_m = mat[1:]
        sims = (docs_m @ q.T).toarray().ravel()
    except Exception:
        sims = [0.0] * len(documents)

    from conformidade.ml.classifier import get_classifier

    clf = get_classifier()
    scored: list[tuple[LoadedDocument, float]] = []
    for doc, sim in zip(documents, sims):
        score = float(sim)
        if expected is not None:
            score += 0.35 * clf.probability_for(doc, expected)
            pred = clf.predict_document(doc)
            if pred.label == expected:
                score += 0.15 * pred.confidence
            if expected in INCOMPATIBLE and pred.label in INCOMPATIBLE[expected]:
                if pred.confidence >= 0.55:
                    score -= 0.5
        scored.append((doc, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]
