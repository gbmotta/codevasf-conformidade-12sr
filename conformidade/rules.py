"""
Regras determinísticas de conformidade (sem LLM).

Avalia itens do checklist por nome de arquivo e trechos de conteúdo.
Decisões fortes (atendido / não atendido) evitam chamada à IA;
casos dúbios seguem para ``analyzer`` + LLM.

Funções-chave: ``evaluate_item_rules``, ``select_relevant_docs``.
"""

from __future__ import annotations

from dataclasses import dataclass

from conformidade.checklist import ChecklistItem
from conformidade.loaders import LoadedDocument
from conformidade.models import ItemResultado, StatusConformidade


def _normalize(text: str) -> str:
    text = text.lower()
    for src, dst in (
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
        text = text.replace(src, dst)
    return text


# chave → tokens no NOME do arquivo
FILENAME_HINTS: dict[str, tuple[str, ...]] = {
    "oficio": ("oficio", "ofício", "requerimento"),
    "cnpj": ("cnpj",),
    "federal": ("certidao conjunta", "rfb", "receita", "divida ativa", "dívida ativa"),
    "fgts": ("fgts", "crf"),
    "cndt": ("trabalhista", "cndt"),
    "posse": ("ata de posse", "posse", "transmissao", "transmissão"),
    "diploma": ("diploma",),
    "rg_cpf": ("rg", "cpf", "cnh", "identidade"),
    "eleitoral": ("votacao", "votação", "quitacao", "quitação", "titulo eleitoral", "título"),
    "residencia": ("residencia", "residência", "comp residencia", "comprovante de endereco"),
    # NÃO incluir FOR-198 / impedimentos — são documentos distintos da Doação Onerosa
    "doacao_onerosa": (
        "doacao onerosa",
        "doação onerosa",
        "cessao onerosa",
        "cessão onerosa",
        "aceitacao onerosa",
        "aceitação onerosa",
        "declaracao onerosa",
        "declaração onerosa",
    ),
    "plano_uso": ("plano de uso", "plano.uso", "plano_de_uso", "for.195", "for.196", "for-195", "for-196"),
    "estatuto": ("estatuto", "contrato social"),
    "ata_diretoria": ("ata de eleicao", "ata de eleição", "ata de criacao", "diretoria"),
}

# chave → tokens no CONTEÚDO (confirmação)
CONTENT_HINTS: dict[str, tuple[str, ...]] = {
    "oficio": ("oficio", "superintendente", "requer", "doacao", "doação", "codevasf"),
    "cnpj": ("cnpj", "cadastro nacional", "inscricao", "inscrição"),
    "federal": ("receita federal", "divida ativa", "dívida ativa", "certidao conjunta", "tributos federais"),
    "fgts": ("fgts", "fundo de garantia", "caixa economica", "caixa econômica", "crf"),
    "cndt": ("trabalhista", "cndt", "tribunal superior do trabalho"),
    "posse": ("posse", "termo de transmissao", "transmito o cargo", "empossado"),
    "diploma": ("diploma", "eleito", "prefeito"),
    "rg_cpf": ("cpf", "identidade", "registro geral", "carteira nacional"),
    "eleitoral": ("quitacao eleitoral", "quitação eleitoral", "titulo eleitoral", "justica eleitoral"),
    "residencia": ("residencia", "consumo", "água", "agua", "energia", "endereco", "endereço"),
    # Exige linguagem de aceitação à modalidade onerosa (não basta "1%" solto)
    "doacao_onerosa": (
        "doacao onerosa",
        "doação onerosa",
        "cessao onerosa",
        "cessão onerosa",
        "aceitacao a modalidade",
        "aceitação à modalidade",
        "modalidade de doacao onerosa",
        "modalidade de doação onerosa",
        "contrapartida de 1%",
        "contrapartida de 1,5%",
        "contrapartida de 1.5%",
    ),
    "plano_uso": ("plano de uso", "uso do bem", "destinacao", "destinação"),
    "estatuto": ("estatuto", "contrato social", "associacao", "cooperativa"),
    "ata_diretoria": ("diretoria", "eleicao", "eleição", "assembleia", "presidencia"),
}

# Sinais de FOR-198 / impedimentos (NÃO atendem o item de Doação Onerosa)
_IMPEDIMENTO_NAME_HINTS = (
    "for.198",
    "for-198",
    "for 198",
    "for_198",
    "impedimento",
    "nao ocorrencia",
    "não ocorrência",
)
_IMPEDIMENTO_CONTENT_HINTS = (
    "declaracao de nao ocorrencia de impedimentos",
    "declaração de não ocorrência de impedimentos",
    "nao ocorrencia de impedimentos",
    "não ocorrência de impedimentos",
    "art. 39 da lei",
    "art 39 da lei n",
    "lei no 13.019",
    "lei nº 13.019",
    "for – 198",
    "for - 198",
    "for 198",
)


def hints_for_item(descricao: str) -> list[str]:
    desc = _normalize(descricao)
    mapping = [
        (("oficio", "oficio em documento"), "oficio"),
        (("cnpj",), "cnpj"),
        (("tributos federais", "divida ativa", "certidao conjunta"), "federal"),
        (("fgts",), "fgts"),
        (("trabalhista", "cndt"), "cndt"),
        (("ata de posse", "termo de transmissao"), "posse"),
        (("diploma",), "diploma"),
        (("cedula de identidade", "rg", "cpf do prefeito", "documentos pessoais"), "rg_cpf"),
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


def score_filename(doc: LoadedDocument, hint_keys: list[str]) -> int:
    hay = _normalize(f"{doc.file_name} {doc.relative_path}")
    score = 0
    for key in hint_keys:
        for token in FILENAME_HINTS.get(key, ()):
            if _normalize(token) in hay:
                score += 3
    return score


def score_content(doc: LoadedDocument, hint_keys: list[str]) -> int:
    body = _normalize(doc.content[:4000])
    score = 0
    for key in hint_keys:
        for token in CONTENT_HINTS.get(key, ()):
            if _normalize(token) in body:
                score += 2
    return score


def is_impedimento_doc(doc: LoadedDocument) -> bool:
    """True se o arquivo parece FOR-198 / declaração de impedimentos."""
    hay = _normalize(f"{doc.file_name} {doc.relative_path}")
    body = _normalize(doc.content[:5000])
    name_hit = any(_normalize(t) in hay for t in _IMPEDIMENTO_NAME_HINTS)
    content_hit = any(_normalize(t) in body for t in _IMPEDIMENTO_CONTENT_HINTS)
    return name_hit or content_hit


def has_onerosa_evidence(doc: LoadedDocument) -> bool:
    """True só com evidência explícita de Doação/Cessão Onerosa (não FOR-198)."""
    if is_impedimento_doc(doc) and not (
        score_filename(doc, ["doacao_onerosa"]) > 0
        or score_content(doc, ["doacao_onerosa"]) > 0
    ):
        return False
    return (
        score_filename(doc, ["doacao_onerosa"]) > 0
        or score_content(doc, ["doacao_onerosa"]) > 0
    )


def _evaluate_doacao_onerosa(
    item: ChecklistItem,
    documents: list[LoadedDocument],
) -> RuleDecision:
    """
    Regra específica: FOR-198 (impedimentos) NÃO atende Doação Onerosa.
    Só marca atendido com linguagem explícita de aceitação à modalidade onerosa.
    """
    onerosa_docs = [d for d in documents if has_onerosa_evidence(d)]
    impedimento_docs = [
        d for d in documents if is_impedimento_doc(d) and not has_onerosa_evidence(d)
    ]

    if onerosa_docs:
        ranked = sorted(
            onerosa_docs,
            key=lambda d: (
                score_filename(d, ["doacao_onerosa"]) + score_content(d, ["doacao_onerosa"]),
                len(d.content),
            ),
            reverse=True,
        )
        best = ranked[0]
        names = [d.file_name for d in ranked[:3]]
        weak = len(best.content.strip()) < 80 or best.extraction_method in {"vazio", "erro"}
        if weak:
            return RuleDecision(
                resolved=True,
                resultado=ItemResultado(
                    numero=item.numero,
                    descricao=item.descricao,
                    status=StatusConformidade.PARCIAL,
                    motivo=(
                        f"Há indício de Doação/Cessão Onerosa em {best.file_name}, "
                        "mas o texto está escasso ou ilegível. Revisar manualmente."
                    ),
                    documentos_relacionados=names,
                    fonte="regra",
                ),
            )
        return RuleDecision(
            resolved=True,
            resultado=ItemResultado(
                numero=item.numero,
                descricao=item.descricao,
                status=StatusConformidade.ATENDIDO,
                motivo=(
                    f"Declaração de Doação/Cessão Onerosa identificada em {best.file_name} "
                    "(aceitação à modalidade / contrapartida)."
                ),
                documentos_relacionados=names,
                fonte="regra",
            ),
        )

    if impedimento_docs:
        names = [d.file_name for d in impedimento_docs[:3]]
        return RuleDecision(
            resolved=True,
            resultado=ItemResultado(
                numero=item.numero,
                descricao=item.descricao,
                status=StatusConformidade.NAO_ATENDIDO,
                motivo=(
                    "Encontrada apenas Declaração de Não Ocorrência de Impedimentos "
                    f"(FOR-198: {', '.join(names)}). Esse documento NÃO substitui a "
                    "Declaração de aceitação à Doação/Cessão Onerosa (contrapartida "
                    "de 1% ou 1,5% no ano eleitoral)."
                ),
                documentos_relacionados=names,
                fonte="regra",
            ),
        )

    return RuleDecision(
        resolved=True,
        resultado=ItemResultado(
            numero=item.numero,
            descricao=item.descricao,
            status=StatusConformidade.NAO_ATENDIDO,
            motivo=(
                "Declaração de Doação/Cessão Onerosa ausente. "
                "Não há arquivo com aceitação à modalidade onerosa / contrapartida percentual."
            ),
            documentos_relacionados=[],
            fonte="regra",
        ),
    )


@dataclass
class RuleDecision:
    """Decisão da regra ou pedido de avaliação por IA."""

    resolved: bool
    resultado: ItemResultado | None = None


def evaluate_item_rules(
    item: ChecklistItem,
    documents: list[LoadedDocument],
) -> RuleDecision:
    hints = hints_for_item(item.descricao)
    if not hints:
        # Sem mapeamento conhecido → deixa para a IA
        return RuleDecision(resolved=False)

    # Item crítico do ano eleitoral: nunca confundir com FOR-198
    if "doacao_onerosa" in hints:
        return _evaluate_doacao_onerosa(item, documents)

    ranked: list[tuple[int, int, LoadedDocument]] = []
    for doc in documents:
        fn = score_filename(doc, hints)
        ct = score_content(doc, hints)
        if fn > 0 or ct > 0:
            ranked.append((fn, ct, doc))
    ranked.sort(key=lambda x: (x[0] + x[1], x[0], len(x[2].content)), reverse=True)

    if not ranked:
        return RuleDecision(
            resolved=True,
            resultado=ItemResultado(
                numero=item.numero,
                descricao=item.descricao,
                status=StatusConformidade.NAO_ATENDIDO,
                motivo="Nenhum arquivo com nome/conteúdo compatível com este item (regra automática).",
                documentos_relacionados=[],
                fonte="regra",
            ),
        )

    best_fn, best_ct, best_doc = ranked[0]
    total = best_fn + best_ct
    docs_names = [d.file_name for _, _, d in ranked[:3]]
    text_len = len(best_doc.content.strip())
    weak_text = text_len < 80 or best_doc.extraction_method in {"vazio", "erro"}

    # Match forte de nome + conteúdo → atendido
    if best_fn >= 3 and best_ct >= 2 and not weak_text:
        return RuleDecision(
            resolved=True,
            resultado=ItemResultado(
                numero=item.numero,
                descricao=item.descricao,
                status=StatusConformidade.ATENDIDO,
                motivo=(
                    f"Arquivo compatível por regra automática ({best_doc.file_name}): "
                    "nome e conteúdo indicam atendimento ao item."
                ),
                documentos_relacionados=docs_names,
                fonte="regra",
            ),
        )

    # Nome forte, texto fraco/OCR ruim → parcial sem IA
    if best_fn >= 3 and weak_text:
        return RuleDecision(
            resolved=True,
            resultado=ItemResultado(
                numero=item.numero,
                descricao=item.descricao,
                status=StatusConformidade.PARCIAL,
                motivo=(
                    f"Arquivo com nome compatível ({best_doc.file_name}), mas texto "
                    "escasso ou OCR insuficiente. Revisar manualmente."
                ),
                documentos_relacionados=docs_names,
                fonte="regra",
            ),
        )

    # Match médio/ambíguo → IA
    if total >= 2:
        return RuleDecision(resolved=False)

    return RuleDecision(
        resolved=True,
        resultado=ItemResultado(
            numero=item.numero,
            descricao=item.descricao,
            status=StatusConformidade.NAO_ATENDIDO,
            motivo="Evidência insuficiente por regra automática; nenhum documento adequado.",
            documentos_relacionados=docs_names[:1],
            fonte="regra",
        ),
    )


def select_relevant_docs(
    item: ChecklistItem,
    documents: list[LoadedDocument],
    limit: int = 4,
) -> list[LoadedDocument]:
    hints = hints_for_item(item.descricao)

    # Para Doação Onerosa: prioriza docs com evidência real; se só houver FOR-198,
    # ainda envia (para a IA ver e marcar nao_atendido), mas não mistura com falso positivo.
    if "doacao_onerosa" in hints:
        onerosa = [d for d in documents if has_onerosa_evidence(d)]
        if onerosa:
            return sorted(
                onerosa,
                key=lambda d: (
                    score_filename(d, ["doacao_onerosa"])
                    + score_content(d, ["doacao_onerosa"]),
                    len(d.content),
                ),
                reverse=True,
            )[:limit]
        imped = [d for d in documents if is_impedimento_doc(d)]
        if imped:
            return imped[:limit]

    ranked = sorted(
        documents,
        key=lambda d: (score_filename(d, hints) + score_content(d, hints), len(d.content)),
        reverse=True,
    )
    relevant = [
        d
        for d in ranked
        if score_filename(d, hints) + score_content(d, hints) > 0
    ][:limit]
    if relevant:
        return relevant
    return sorted(documents, key=lambda d: len(d.content), reverse=True)[:2]
