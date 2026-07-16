"""Carrega e interpreta as Listas de Documentos (checklists) em PDF."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from conformidade.loaders import _read_pdf


class TipoEntidade(str, Enum):
    PREFEITURA = "prefeitura"
    ASSOCIACAO = "associacao"


def label_tipo(tipo: TipoEntidade) -> str:
    if tipo is TipoEntidade.PREFEITURA:
        return "Prefeitura"
    return "Associação / Cooperativa / Instituição pública"


CHECKLIST_FILES = {
    TipoEntidade.PREFEITURA: "lista_prefeituras.pdf",
    TipoEntidade.ASSOCIACAO: "lista_associacoes.pdf",
}

# Fallback caso a extração do PDF falhe
FALLBACK_ITEMS: dict[TipoEntidade, list[str]] = {
    TipoEntidade.PREFEITURA: [
        "Ofício em documento timbrado da Prefeitura, contendo endereço e telefone(s) de contato, requerendo a doação (informando o(s) bem(s) pleiteado(s) e qual será seu uso), dirigido ao Superintendente da 12ª Superintendência Regional da Codevasf (Sr. Leonlene de Sousa Aguiar), devidamente assinado pelo gestor do município",
        "Comprovante de inscrição no CNPJ",
        "Certidão conjunta negativa de débitos relativos aos tributos federais e à dívida ativa da união — pessoa jurídica",
        "Certificado de Regularidade do Fundo de Garantia por Tempo de Serviço (FGTS)",
        "Certidão negativa de débitos trabalhistas (CNDT)",
        "Ata de posse do prefeito ou Termo de transmissão de cargo",
        "Diploma de nomeação do Prefeito(a)",
        "Cópia da cédula de identidade e CPF do Prefeito(a)",
        "Comprovante de votação do Prefeito(a) referente à última eleição ou Certidão de Quitação Eleitoral",
        "Comprovante de Residência do Prefeito(a)",
        "Declaração de aceitação à modalidade de Doação Onerosa (contrapartida de 1,5% do valor total da doação — anos eleitorais)",
        "Plano de Uso do Bem",
    ],
    TipoEntidade.ASSOCIACAO: [
        "Ofício em documento timbrado da entidade, contendo endereço e telefone(s) de contato, requerendo a doação e indicando expressamente que o bem adquirido atenderá exclusivamente fins e uso de interesse social, dirigido ao Superintendente da 12ª Superintendência Regional da Codevasf (Sr. Leonlene de Sousa Aguiar)",
        "Contrato ou Estatuto Social em vigor",
        "Ata de Criação ou Eleição da Diretoria/Presidência (Registrado em cartório)",
        "Comprovante de inscrição no CNPJ",
        "Certidão Conjunta Negativa de Débitos Relativos aos Tributos Federais e à Dívida Ativa da União — pessoa jurídica",
        "Certificado de Regularidade do Fundo de Garantia por Tempo de Serviço (FGTS)",
        "Certidão negativa de débitos trabalhistas (CNDT)",
        "Documentos Pessoais do responsável pela entidade/instituição: RG, CPF, Título Eleitoral e Comprovante de endereço",
        "Declaração de aceitação à modalidade de Doação Onerosa (contrapartida de 1% do valor total da doação — anos eleitorais)",
        "Plano de uso do bem",
    ],
}


@dataclass
class ChecklistItem:
    numero: int
    descricao: str


@dataclass
class Checklist:
    tipo: TipoEntidade
    titulo: str
    itens: list[ChecklistItem]
    fonte: str


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_checklist_text(text: str) -> list[ChecklistItem]:
    """Extrai itens numerados (1. ... 2. ...) do texto da lista de documentos."""
    text = _normalize_whitespace(text)
    pattern = re.compile(
        r"(?m)^\s*(\d{1,2})\.\s+(.+?)(?=(?:^\s*\d{1,2}\.\s+)|\Z)",
        re.DOTALL,
    )
    items: list[ChecklistItem] = []
    for match in pattern.finditer(text):
        numero = int(match.group(1))
        raw_desc = match.group(2)
        # Remove bloco OBS./observações colado ao último item
        raw_desc = re.split(r"(?i)\bOBS\.?\s*:", raw_desc, maxsplit=1)[0]
        descricao = re.sub(r"\s+", " ", raw_desc).strip(" ;.")
        if descricao.upper().startswith("OBS"):
            continue
        if len(descricao) < 8:
            continue
        items.append(ChecklistItem(numero=numero, descricao=descricao))

    seen: set[int] = set()
    unique: list[ChecklistItem] = []
    for item in items:
        if item.numero in seen:
            continue
        seen.add(item.numero)
        unique.append(item)
    return unique


def load_checklist_from_pdf(pdf_path: Path, tipo: TipoEntidade) -> Checklist:
    text = _read_pdf(pdf_path)
    items = parse_checklist_text(text)
    if not items:
        items = [
            ChecklistItem(numero=i, descricao=desc)
            for i, desc in enumerate(FALLBACK_ITEMS[tipo], start=1)
        ]
        fonte = f"{pdf_path.name} (fallback — texto do PDF não parseado)"
    else:
        fonte = str(pdf_path)

    titulo = (
        "Documentação necessária — Prefeituras"
        if tipo is TipoEntidade.PREFEITURA
        else "Documentação necessária — Associações, Cooperativas e Instituições públicas"
    )
    return Checklist(tipo=tipo, titulo=titulo, itens=items, fonte=fonte)


def load_checklist(checklists_path: Path, tipo: TipoEntidade) -> Checklist:
    file_name = CHECKLIST_FILES[tipo]
    pdf_path = checklists_path / file_name
    if pdf_path.exists():
        return load_checklist_from_pdf(pdf_path, tipo)

    items = [
        ChecklistItem(numero=i, descricao=desc)
        for i, desc in enumerate(FALLBACK_ITEMS[tipo], start=1)
    ]
    titulo = (
        "Documentação necessária — Prefeituras"
        if tipo is TipoEntidade.PREFEITURA
        else "Documentação necessária — Associações, Cooperativas e Instituições públicas"
    )
    return Checklist(
        tipo=tipo,
        titulo=titulo,
        itens=items,
        fonte="checklist embutido (PDF ausente)",
    )


def infer_tipo_from_names(file_names: list[str]) -> TipoEntidade | None:
    """Sugere o tipo de entidade com base nos nomes dos arquivos."""
    joined = " ".join(file_names).lower()
    score_pref = 0
    score_assoc = 0

    pref_tokens = (
        "prefeitura",
        "prefeito",
        "município",
        "municipio",
        "diploma",
        "ata de posse",
        "posse",
        "cnh prefeito",
        "quitação eleitoral",
        "quitacao eleitoral",
    )
    assoc_tokens = (
        "associação",
        "associacao",
        "cooperativa",
        "estatuto",
        "ata de eleição",
        "ata de eleicao",
        "diretoria",
        "instituição",
        "instituicao",
    )
    for token in pref_tokens:
        if token in joined:
            score_pref += 1
    for token in assoc_tokens:
        if token in joined:
            score_assoc += 1

    if score_pref == 0 and score_assoc == 0:
        return None
    return TipoEntidade.PREFEITURA if score_pref >= score_assoc else TipoEntidade.ASSOCIACAO


def format_checklist_for_prompt(checklist: Checklist) -> str:
    return "\n".join(f"{item.numero}. {item.descricao}" for item in checklist.itens)
