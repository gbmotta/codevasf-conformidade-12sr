"""
Rotulagem fraca (heurística) — pseudo-labels sem revisão humana.

Independente de ``rules`` para evitar import circular.
"""

from __future__ import annotations

from conformidade.loaders import LoadedDocument
from conformidade.ml.features import normalize_text
from conformidade.ml.schema import DocLabel

_FILENAME: dict[str, tuple[str, ...]] = {
    "oficio": ("oficio", "requerimento"),
    "cnpj": ("cnpj",),
    "federal": ("certidao conjunta", "rfb", "receita", "divida ativa"),
    "fgts": ("fgts", "crf"),
    "cndt": ("trabalhista", "cndt"),
    "posse": ("ata de posse", "posse", "transmissao"),
    "diploma": ("diploma",),
    "rg_cpf": ("rg", "cpf", "cnh", "identidade"),
    "eleitoral": ("votacao", "quitacao", "titulo eleitoral"),
    "residencia": ("residencia", "comp residencia", "comprovante de endereco"),
    "doacao_onerosa": (
        "doacao onerosa",
        "cessao onerosa",
        "aceitacao onerosa",
        "declaracao onerosa",
    ),
    "plano_uso": ("plano de uso", "plano.uso", "for.195", "for.196", "for-195", "for-196"),
    "estatuto": ("estatuto", "contrato social"),
    "ata_diretoria": ("ata de eleicao", "ata de criacao", "diretoria"),
}

_CONTENT: dict[str, tuple[str, ...]] = {
    "oficio": ("oficio", "superintendente", "requer", "codevasf"),
    "cnpj": ("cnpj", "cadastro nacional"),
    "federal": ("receita federal", "divida ativa", "tributos federais", "certidao conjunta"),
    "fgts": ("fgts", "fundo de garantia", "caixa economica", "crf"),
    "cndt": ("trabalhista", "cndt", "tribunal superior do trabalho"),
    "posse": ("posse", "termo de transmissao", "empossado"),
    "diploma": ("diploma", "eleito", "prefeito"),
    "rg_cpf": ("cpf", "identidade", "registro geral", "carteira nacional"),
    "eleitoral": ("quitacao eleitoral", "titulo eleitoral", "justica eleitoral"),
    "residencia": ("residencia", "consumo", "energia", "endereco"),
    "doacao_onerosa": (
        "doacao onerosa",
        "cessao onerosa",
        "aceitacao a modalidade",
        "modalidade de doacao onerosa",
        "contrapartida de 1%",
        "contrapartida de 1,5%",
    ),
    "plano_uso": ("plano de uso", "uso do bem", "destinacao"),
    "estatuto": ("estatuto", "contrato social", "associacao", "cooperativa"),
    "ata_diretoria": ("diretoria", "eleicao", "assembleia", "presidencia"),
}

_IMP_NAME = ("for.198", "for-198", "for 198", "impedimento", "nao ocorrencia")
_IMP_CONTENT = (
    "declaracao de nao ocorrencia de impedimentos",
    "nao ocorrencia de impedimentos",
    "art. 39 da lei",
    "lei no 13.019",
    "lei n 13.019",
    "for 198",
)


def _score(hay: str, tokens: tuple[str, ...], weight: int) -> int:
    return sum(weight for t in tokens if normalize_text(t) in hay)


def _is_impedimento(file_name: str, content: str) -> bool:
    hay = normalize_text(file_name)
    body = normalize_text(content[:5000])
    return any(t in hay for t in _IMP_NAME) or any(t in body for t in _IMP_CONTENT)


def weak_label_document(doc: LoadedDocument) -> tuple[DocLabel, float]:
    """Retorna (rótulo, confiança 0–1) por heurística."""
    if len((doc.content or "").strip()) < 40 and doc.extraction_method in {
        "vazio",
        "erro",
    }:
        return DocLabel.ILEGIVEL, 0.7

    name = f"{doc.file_name} {doc.relative_path}"
    content = doc.content or ""

    if _is_impedimento(name, content):
        on_hay = normalize_text(name)
        on_body = normalize_text(content[:4000])
        on_score = _score(on_hay, _FILENAME["doacao_onerosa"], 3) + _score(
            on_body, _CONTENT["doacao_onerosa"], 2
        )
        if on_score < 4:
            return DocLabel.IMPEDIMENTO, 0.9

    best_label = DocLabel.OUTRO
    best_score = 0
    name_n = normalize_text(name)
    body_n = normalize_text(content[:4000])
    for key, tokens in _FILENAME.items():
        total = _score(name_n, tokens, 3) + _score(body_n, _CONTENT.get(key, ()), 2)
        if total > best_score:
            best_score = total
            best_label = DocLabel(key)

    if best_score >= 5:
        return best_label, min(0.95, 0.55 + 0.05 * best_score)
    if best_score >= 3:
        return best_label, 0.55
    if best_score >= 2:
        return best_label, 0.4
    return DocLabel.OUTRO, 0.2


def weak_label_parts(file_name: str, content: str) -> tuple[DocLabel, float]:
    doc = LoadedDocument(
        source=file_name,
        content=content or "",
        file_name=file_name,
        relative_path=file_name,
        extraction_method="texto",
    )
    return weak_label_document(doc)
