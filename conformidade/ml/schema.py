"""
Schema de rótulos de documentos (ML sem LLM).

Alinhado às chaves de ``conformidade.rules`` + tipos especiais
(impedimento FOR-198, outros, ilegível).
"""

from __future__ import annotations

from enum import Enum


class DocLabel(str, Enum):
    OFICIO = "oficio"
    CNPJ = "cnpj"
    FEDERAL = "federal"
    FGTS = "fgts"
    CNDT = "cndt"
    POSSE = "posse"
    DIPLOMA = "diploma"
    RG_CPF = "rg_cpf"
    ELEITORAL = "eleitoral"
    RESIDENCIA = "residencia"
    DOACAO_ONEROSA = "doacao_onerosa"
    IMPEDIMENTO = "impedimento"  # FOR-198 — NÃO é onerosa
    PLANO_USO = "plano_uso"
    ESTATUTO = "estatuto"
    ATA_DIRETORIA = "ata_diretoria"
    OUTRO = "outro"
    ILEGIVEL = "ilegivel"


# Descrição curta para UI / CSV / revisão humana
LABEL_DESCRIPTIONS: dict[DocLabel, str] = {
    DocLabel.OFICIO: "Ofício / requerimento à CODEVASF",
    DocLabel.CNPJ: "Cartão / comprovante de CNPJ",
    DocLabel.FEDERAL: "Certidão conjunta RFB / Dívida Ativa",
    DocLabel.FGTS: "Certificado de Regularidade do FGTS (CRF)",
    DocLabel.CNDT: "Certidão Negativa de Débitos Trabalhistas",
    DocLabel.POSSE: "Ata de posse / termo de transmissão",
    DocLabel.DIPLOMA: "Diploma de eleição (prefeito)",
    DocLabel.RG_CPF: "RG / CPF / CNH / identidade",
    DocLabel.ELEITORAL: "Quitação / título eleitoral",
    DocLabel.RESIDENCIA: "Comprovante de residência / endereço",
    DocLabel.DOACAO_ONEROSA: "Aceitação Doação/Cessão Onerosa (contrapartida)",
    DocLabel.IMPEDIMENTO: "FOR-198 / Declaração de não ocorrência de impedimentos",
    DocLabel.PLANO_USO: "Plano de uso do bem (FOR-195/196)",
    DocLabel.ESTATUTO: "Estatuto / contrato social",
    DocLabel.ATA_DIRETORIA: "Ata de eleição / diretoria",
    DocLabel.OUTRO: "Documento não classificado / outro tipo",
    DocLabel.ILEGIVEL: "Texto insuficiente / OCR falhou",
}

# Checklist item hint → rótulo esperado do documento
HINT_TO_LABEL: dict[str, DocLabel] = {
    "oficio": DocLabel.OFICIO,
    "cnpj": DocLabel.CNPJ,
    "federal": DocLabel.FEDERAL,
    "fgts": DocLabel.FGTS,
    "cndt": DocLabel.CNDT,
    "posse": DocLabel.POSSE,
    "diploma": DocLabel.DIPLOMA,
    "rg_cpf": DocLabel.RG_CPF,
    "eleitoral": DocLabel.ELEITORAL,
    "residencia": DocLabel.RESIDENCIA,
    "doacao_onerosa": DocLabel.DOACAO_ONEROSA,
    "plano_uso": DocLabel.PLANO_USO,
    "estatuto": DocLabel.ESTATUTO,
    "ata_diretoria": DocLabel.ATA_DIRETORIA,
}

# Pares que NÃO devem atender o item (falso positivo clássico)
INCOMPATIBLE: dict[DocLabel, frozenset[DocLabel]] = {
    DocLabel.DOACAO_ONEROSA: frozenset({DocLabel.IMPEDIMENTO, DocLabel.OFICIO, DocLabel.CNPJ}),
    DocLabel.POSSE: frozenset({DocLabel.RG_CPF, DocLabel.DIPLOMA, DocLabel.OFICIO}),
    DocLabel.DIPLOMA: frozenset({DocLabel.RG_CPF, DocLabel.OFICIO}),
    DocLabel.FEDERAL: frozenset({DocLabel.CNDT, DocLabel.FGTS}),
    DocLabel.FGTS: frozenset({DocLabel.FEDERAL, DocLabel.CNDT}),
    DocLabel.CNDT: frozenset({DocLabel.FEDERAL, DocLabel.FGTS}),
}


def all_label_values() -> list[str]:
    return [x.value for x in DocLabel]


def parse_label(raw: str) -> DocLabel:
    key = (raw or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "for198": DocLabel.IMPEDIMENTO.value,
        "for_198": DocLabel.IMPEDIMENTO.value,
        "impedimentos": DocLabel.IMPEDIMENTO.value,
        "onerosa": DocLabel.DOACAO_ONEROSA.value,
        "cessao_onerosa": DocLabel.DOACAO_ONEROSA.value,
        "doacao": DocLabel.DOACAO_ONEROSA.value,
        "crf": DocLabel.FGTS.value,
        "receita": DocLabel.FEDERAL.value,
        "cnd": DocLabel.FEDERAL.value,
        "identidade": DocLabel.RG_CPF.value,
        "cnh": DocLabel.RG_CPF.value,
    }
    key = aliases.get(key, key)
    try:
        return DocLabel(key)
    except ValueError:
        return DocLabel.OUTRO
