"""Análise de conformidade documental via LLM local (Ollama)."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from conformidade.checklist import (
    Checklist,
    ChecklistItem,
    TipoEntidade,
    label_tipo,
)
from conformidade.config import Settings
from conformidade.llm import ChatMessage, chat_completion
from conformidade.loaders import LoadedDocument


class StatusConformidade(str, Enum):
    ATENDIDO = "atendido"
    PARCIAL = "parcial"
    NAO_ATENDIDO = "nao_atendido"


STATUS_ALIASES = {
    "atendido": StatusConformidade.ATENDIDO,
    "atendida": StatusConformidade.ATENDIDO,
    "ok": StatusConformidade.ATENDIDO,
    "conforme": StatusConformidade.ATENDIDO,
    "parcial": StatusConformidade.PARCIAL,
    "parcialmente": StatusConformidade.PARCIAL,
    "parcialmente_atendido": StatusConformidade.PARCIAL,
    "parcialmente atendido": StatusConformidade.PARCIAL,
    "nao_atendido": StatusConformidade.NAO_ATENDIDO,
    "não_atendido": StatusConformidade.NAO_ATENDIDO,
    "nao atendido": StatusConformidade.NAO_ATENDIDO,
    "não atendido": StatusConformidade.NAO_ATENDIDO,
    "ausente": StatusConformidade.NAO_ATENDIDO,
    "faltando": StatusConformidade.NAO_ATENDIDO,
}

# Palavras-chave por tipo de documento → ajuda a pré-selecionar arquivos relevantes
KEYWORD_HINTS: dict[str, tuple[str, ...]] = {
    "oficio": ("oficio", "ofício", "requerimento", "solicitacao", "solicitação"),
    "cnpj": ("cnpj", "cartao cnpj", "comprovante de inscricao"),
    "federal": ("certidao conjunta", "rfb", "receita", "divida ativa", "dívida ativa", "tributos federais"),
    "fgts": ("fgts", "regularidade do fgts", "crf"),
    "cndt": ("trabalhista", "cndt", "debito trabalhista", "débito trabalhista"),
    "posse": ("ata de posse", "posse", "transmissao de cargo", "transmissão de cargo"),
    "diploma": ("diploma",),
    "rg_cpf": ("rg", "cpf", "identidade", "cnh", "documento pessoal"),
    "eleitoral": ("votacao", "votação", "quitacao eleitoral", "quitação eleitoral", "titulo eleitoral", "título eleitoral"),
    "residencia": ("residencia", "residência", "comprovante de endereco", "comprovante de endereço", "comp residencia"),
    "doacao_onerosa": ("doacao onerosa", "doação onerosa", "contrapartida", "nao impedimento", "não impedimento", "declaracao", "declaração"),
    "plano_uso": ("plano de uso", "plano.uso", "plano_de_uso", "for.195"),
    "estatuto": ("estatuto", "contrato social"),
    "ata_diretoria": ("ata de criacao", "ata de criação", "eleicao", "eleição", "diretoria"),
}


@dataclass
class ItemResultado:
    numero: int
    descricao: str
    status: StatusConformidade
    motivo: str
    documentos_relacionados: list[str] = field(default_factory=list)


@dataclass
class RelatorioConformidade:
    tipo: TipoEntidade
    entidade_detectada: str
    resumo: str
    itens: list[ItemResultado]
    documentos_analisados: list[str]
    resposta_bruta: str = ""

    @property
    def contagem(self) -> dict[str, int]:
        counts = {
            StatusConformidade.ATENDIDO.value: 0,
            StatusConformidade.PARCIAL.value: 0,
            StatusConformidade.NAO_ATENDIDO.value: 0,
        }
        for item in self.itens:
            counts[item.status.value] += 1
        return counts


SYSTEM_PROMPT = """Você é um analista documental da CODEVASF (12ª Superintendência Regional — Natal/RN).
Verifique se os documentos apresentados atendem itens específicos da Lista de Documentos
para concessão/doação de bens móveis.

Regras obrigatórias:
1. Avalie APENAS os itens numerados pedidos nesta mensagem.
2. Use somente evidências dos arquivos (nome + conteúdo).
3. status deve ser exatamente um de: "atendido", "parcial", "nao_atendido".
4. "atendido" = documento presente e aparenta cumprir o requisito.
5. "parcial" = há arquivo relacionado, mas incompleto, ilegível, sem assinatura, sem texto extraível ou com dúvida.
6. "nao_atendido" = documento ausente ou claramente inadequado ao item.
7. Explique o motivo objetivamente e cite arquivos em documentos_relacionados.
8. Não atribua um arquivo a um item se o nome/conteúdo for claramente de outro tipo
   (ex.: CNH não serve como Ata de Posse; Diploma não serve como Ofício).
9. Responda SOMENTE JSON válido, sem markdown e sem texto fora do JSON.
"""


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 20].rstrip() + "\n...[texto truncado]..."


def _normalize(text: str) -> str:
    text = text.lower()
    replacements = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ç": "c",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def _hints_for_item(descricao: str) -> list[str]:
    desc = _normalize(descricao)
    keys: list[str] = []
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
    for needles, key in mapping:
        if any(n in desc for n in needles):
            keys.append(key)
    return keys


def _score_document(doc: LoadedDocument, hint_keys: list[str]) -> int:
    hay = _normalize(f"{doc.file_name} {doc.relative_path}")
    score = 0
    for key in hint_keys:
        for token in KEYWORD_HINTS.get(key, ()):
            if _normalize(token) in hay:
                score += 2
    return score


def _select_relevant_docs(
    item: ChecklistItem,
    documents: list[LoadedDocument],
    limit: int = 4,
) -> list[LoadedDocument]:
    hints = _hints_for_item(item.descricao)
    ranked = sorted(
        documents,
        key=lambda d: (_score_document(d, hints), len(d.content)),
        reverse=True,
    )
    relevant = [d for d in ranked if _score_document(d, hints) > 0][:limit]
    if relevant:
        return relevant
    # Sem match por nome: envia os mais "textuais" como contexto auxiliar
    return sorted(documents, key=lambda d: len(d.content), reverse=True)[:2]


def _build_documents_block(
    documents: list[LoadedDocument],
    max_chars_per_document: int,
    max_total: int,
) -> str:
    parts: list[str] = []
    used = 0
    for doc in documents:
        remaining = max_total - used
        if remaining <= 200:
            parts.append(
                f"\n### {doc.relative_path}\n[Conteúdo omitido por limite de contexto.]"
            )
            continue
        budget = min(max_chars_per_document, remaining)
        body = _truncate(doc.content, budget)
        block = f"\n### Arquivo: {doc.relative_path}\n{body}\n"
        parts.append(block)
        used += len(block)
    return "".join(parts)


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _normalize_status(raw: str) -> StatusConformidade:
    key = (raw or "").strip().lower()
    if key in STATUS_ALIASES:
        return STATUS_ALIASES[key]
    if "parcial" in key:
        return StatusConformidade.PARCIAL
    if "não" in key or "nao" in key or "ausent" in key or "falt" in key:
        return StatusConformidade.NAO_ATENDIDO
    if "atend" in key or "conforme" in key or key == "ok":
        return StatusConformidade.ATENDIDO
    return StatusConformidade.NAO_ATENDIDO


def _parse_batch_items(
    data: dict,
    batch: list[ChecklistItem],
) -> dict[int, ItemResultado]:
    by_numero = {item.numero: item for item in batch}
    raw_items = data.get("itens") or data.get("items") or []
    results: dict[int, ItemResultado] = {}

    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        try:
            numero = int(raw.get("numero") or raw.get("item") or raw.get("n") or 0)
        except (TypeError, ValueError):
            continue
        if numero not in by_numero:
            continue
        base = by_numero[numero]
        docs_rel = raw.get("documentos_relacionados") or raw.get("arquivos") or []
        if isinstance(docs_rel, str):
            docs_rel = [docs_rel]
        results[numero] = ItemResultado(
            numero=numero,
            descricao=base.descricao,
            status=_normalize_status(str(raw.get("status", "nao_atendido"))),
            motivo=str(raw.get("motivo") or raw.get("justificativa") or "").strip()
            or "Sem justificativa fornecida pelo modelo.",
            documentos_relacionados=[str(d) for d in docs_rel if d],
        )
    return results


def _analyze_batch(
    settings: Settings,
    checklist: Checklist,
    batch: list[ChecklistItem],
    documents: list[LoadedDocument],
    inventory: str,
) -> tuple[dict[int, ItemResultado], str]:
    # Junta documentos relevantes de todos os itens do lote (sem duplicar)
    selected: dict[str, LoadedDocument] = {}
    for item in batch:
        for doc in _select_relevant_docs(item, documents):
            selected[doc.relative_path] = doc

    docs_block = _build_documents_block(
        list(selected.values()) or documents[:5],
        max_chars_per_document=min(settings.max_chars_per_document, 2500),
        max_total=min(settings.max_total_document_chars, 14000),
    )
    checklist_block = "\n".join(f"{item.numero}. {item.descricao}" for item in batch)
    expected = ", ".join(str(item.numero) for item in batch)

    user_prompt = f"""Tipo de solicitante: {label_tipo(checklist.tipo)}

ITENS A AVALIAR (obrigatório retornar TODOS: {expected}):
{checklist_block}

INVENTÁRIO COMPLETO DOS ARQUIVOS ENVIADOS:
{inventory}

TRECHOS DOS ARQUIVOS MAIS RELEVANTES PARA ESTES ITENS:
{docs_block}

Retorne JSON exatamente neste formato:
{{
  "itens": [
    {{
      "numero": {batch[0].numero},
      "status": "atendido",
      "motivo": "explicação objetiva",
      "documentos_relacionados": ["arquivo.pdf"]
    }}
  ]
}}
"""

    raw = chat_completion(
        settings,
        messages=[ChatMessage(role="user", content=user_prompt)],
        system_prompt=SYSTEM_PROMPT,
        temperature=0.0,
    )

    try:
        data = _extract_json(raw)
        parsed = _parse_batch_items(data, batch)
    except (json.JSONDecodeError, AttributeError, TypeError):
        parsed = {}

    # Retry único se faltar item
    missing = [item for item in batch if item.numero not in parsed]
    if missing:
        retry_prompt = (
            user_prompt
            + "\n\nATENÇÃO: sua resposta anterior estava incompleta ou inválida. "
            f"Avalie novamente TODOS os itens: {expected}. JSON apenas."
        )
        raw_retry = chat_completion(
            settings,
            messages=[ChatMessage(role="user", content=retry_prompt)],
            system_prompt=SYSTEM_PROMPT,
            temperature=0.0,
        )
        try:
            data_retry = _extract_json(raw_retry)
            parsed_retry = _parse_batch_items(data_retry, batch)
            parsed.update(parsed_retry)
            raw = raw + "\n\n--- RETRY ---\n\n" + raw_retry
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass

    # Preenche faltantes com heurística de nome de arquivo
    for item in batch:
        if item.numero in parsed:
            continue
        hints = _hints_for_item(item.descricao)
        matches = [d for d in documents if _score_document(d, hints) > 0]
        if matches:
            parsed[item.numero] = ItemResultado(
                numero=item.numero,
                descricao=item.descricao,
                status=StatusConformidade.PARCIAL,
                motivo=(
                    "Há arquivo(s) com nome compatível, mas o modelo não concluiu a "
                    "avaliação textual. Revisar manualmente."
                ),
                documentos_relacionados=[d.file_name for d in matches[:3]],
            )
        else:
            parsed[item.numero] = ItemResultado(
                numero=item.numero,
                descricao=item.descricao,
                status=StatusConformidade.NAO_ATENDIDO,
                motivo="Nenhum arquivo correspondente identificado no conjunto enviado.",
                documentos_relacionados=[],
            )

    return parsed, raw


def _detect_entity_name(documents: list[LoadedDocument]) -> str:
    sample = "\n".join(f"{d.file_name}\n{d.content[:800]}" for d in documents[:6])
    patterns = [
        r"Prefeitura Municipal de\s+([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç][\wÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç.]*(?:\s+[A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç][\wÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç.]*){0,4})",
        r"Munic[ií]pio de\s+([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç][\wÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç.]*(?:\s+[A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç][\wÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç.]*){0,4})",
        r"Associa[cç][aã]o\s+[A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç][\wÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç\s]{2,50}",
    ]
    for pattern in patterns:
        match = re.search(pattern, sample, re.IGNORECASE)
        if match:
            name = re.sub(r"\s+", " ", match.group(0)).strip(" .,\n\r\t")
            name = re.split(r"\b(?:CNPJ|CPF|Inscri|Cadastro)\b", name, maxsplit=1)[0]
            name = name.strip(" .,\n\r\t")
            if len(name) >= 8:
                return name.title()
    for doc in documents:
        m = re.search(r"munic[ií]pio\s+de\s+([a-zà-ÿ\s]+)", doc.source, re.IGNORECASE)
        if m:
            return ("Município de " + m.group(1).strip()).title()
    return "Não identificada"


def analisar_conformidade(
    settings: Settings,
    checklist: Checklist,
    documents: list[LoadedDocument],
    batch_size: int = 3,
    on_progress: Callable[[str], None] | None = None,
) -> RelatorioConformidade:
    if not documents:
        raise ValueError("Nenhum documento para analisar.")

    inventory = "\n".join(f"- {doc.relative_path}" for doc in documents)
    all_results: dict[int, ItemResultado] = {}
    raw_parts: list[str] = []

    items = list(checklist.itens)
    total_batches = (len(items) + batch_size - 1) // batch_size
    for index, start in enumerate(range(0, len(items), batch_size), start=1):
        batch = items[start : start + batch_size]
        nums = ", ".join(str(item.numero) for item in batch)
        if on_progress:
            on_progress(f"Analisando lote {index}/{total_batches} (itens {nums})...")
        parsed, raw = _analyze_batch(settings, checklist, batch, documents, inventory)
        all_results.update(parsed)
        raw_parts.append(raw)

    ordered = [all_results[item.numero] for item in items if item.numero in all_results]
    counts = {
        StatusConformidade.ATENDIDO.value: 0,
        StatusConformidade.PARCIAL.value: 0,
        StatusConformidade.NAO_ATENDIDO.value: 0,
    }
    for item in ordered:
        counts[item.status.value] += 1

    entidade = _detect_entity_name(documents)
    resumo = (
        f"Análise para {label_tipo(checklist.tipo)} ({entidade}): "
        f"{counts['atendido']} atendido(s), {counts['parcial']} parcial(is), "
        f"{counts['nao_atendido']} não atendido(s), em {len(documents)} arquivo(s)."
    )

    return RelatorioConformidade(
        tipo=checklist.tipo,
        entidade_detectada=entidade,
        resumo=resumo,
        itens=ordered,
        documentos_analisados=[doc.relative_path for doc in documents],
        resposta_bruta="\n\n===== LOTE =====\n\n".join(raw_parts),
    )
