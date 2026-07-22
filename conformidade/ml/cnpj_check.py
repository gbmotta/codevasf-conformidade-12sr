"""
Conferência cruzada de CNPJ entre documentos do pacote.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from conformidade.loaders import LoadedDocument
from conformidade.ml.extractors import extract_fields, format_cnpj, _digits
from conformidade.ml.heuristics import weak_label_document
from conformidade.ml.schema import DocLabel


# Documentos onde esperamos o CNPJ da entidade
_LABELS_COM_CNPJ = {
    DocLabel.OFICIO,
    DocLabel.CNPJ,
    DocLabel.FEDERAL,
    DocLabel.FGTS,
    DocLabel.CNDT,
    DocLabel.ESTATUTO,
    DocLabel.PLANO_USO,
    DocLabel.DOACAO_ONEROSA,
}


@dataclass
class DocCnpjHit:
    file_name: str
    label: str
    cnpjs: list[str]


@dataclass
class CnpjCrossCheck:
    principal: str | None
    hits: list[DocCnpjHit] = field(default_factory=list)
    divergentes: list[DocCnpjHit] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.divergentes and bool(self.principal)


def cross_check_cnpj(documents: list[LoadedDocument]) -> CnpjCrossCheck:
    hits: list[DocCnpjHit] = []
    all_cnpjs: list[str] = []

    for doc in documents:
        fields = extract_fields(doc.content or "")
        if not fields.cnpjs:
            continue
        label, _ = weak_label_document(doc)
        # Prioriza docs típicos; ainda assim coleta todos
        hit = DocCnpjHit(doc.file_name, label.value, list(fields.cnpjs))
        hits.append(hit)
        if label in _LABELS_COM_CNPJ or label == DocLabel.OUTRO:
            all_cnpjs.extend(fields.cnpjs)

    if not all_cnpjs:
        # fallback: qualquer CNPJ encontrado
        all_cnpjs = [c for h in hits for c in h.cnpjs]

    if not all_cnpjs:
        return CnpjCrossCheck(
            principal=None,
            hits=hits,
            alertas=["Nenhum CNPJ válido extraído nos documentos do pacote."],
        )

    # Normaliza por dígitos para votação
    by_digits: Counter[str] = Counter(_digits(c) for c in all_cnpjs)
    principal_digits, _ = by_digits.most_common(1)[0]
    principal = format_cnpj(principal_digits)

    divergentes: list[DocCnpjHit] = []
    alertas: list[str] = []
    for hit in hits:
        digs = {_digits(c) for c in hit.cnpjs}
        if principal_digits not in digs and digs:
            # Só alerta se o doc for de tipo relevante
            if hit.label in {x.value for x in _LABELS_COM_CNPJ}:
                divergentes.append(hit)
                alertas.append(
                    f"CNPJ divergente em {hit.file_name} ({hit.label}): "
                    f"{', '.join(hit.cnpjs)} ≠ principal {principal}."
                )

    if divergentes:
        alertas.insert(
            0,
            f"CNPJ principal do pacote: {principal}. "
            f"{len(divergentes)} documento(s) com CNPJ diferente.",
        )
    else:
        alertas.append(f"CNPJ consistente no pacote: {principal}.")

    return CnpjCrossCheck(
        principal=principal,
        hits=hits,
        divergentes=divergentes,
        alertas=alertas,
    )
