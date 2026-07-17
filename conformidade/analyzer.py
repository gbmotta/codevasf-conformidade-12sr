"""Análise de conformidade: regras determinísticas + LLM nos casos dúbios."""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from conformidade.checklist import Checklist, ChecklistItem, label_tipo
from conformidade.config import Settings
from conformidade.llm import ChatMessage, chat_completion
from conformidade.loaders import LoadedDocument
from conformidade.models import (
    ItemResultado,
    RelatorioConformidade,
    StatusConformidade,
    normalize_status,
)
from conformidade.rules import evaluate_item_rules, select_relevant_docs

# Reexporta para imports existentes
__all__ = [
    "StatusConformidade",
    "ItemResultado",
    "RelatorioConformidade",
    "analisar_conformidade",
]


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
            status=normalize_status(str(raw.get("status", "nao_atendido"))),
            motivo=str(raw.get("motivo") or raw.get("justificativa") or "").strip()
            or "Sem justificativa fornecida pelo modelo.",
            documentos_relacionados=[str(d) for d in docs_rel if d],
            fonte="ia",
        )
    return results


def _analyze_batch(
    settings: Settings,
    checklist: Checklist,
    batch: list[ChecklistItem],
    documents: list[LoadedDocument],
    inventory: str,
) -> tuple[dict[int, ItemResultado], str]:
    selected: dict[str, LoadedDocument] = {}
    for item in batch:
        for doc in select_relevant_docs(item, documents):
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
            parsed.update(_parse_batch_items(data_retry, batch))
            raw = raw + "\n\n--- RETRY ---\n\n" + raw_retry
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass

    for item in batch:
        if item.numero in parsed:
            continue
        decision = evaluate_item_rules(item, documents)
        if decision.resolved and decision.resultado:
            parsed[item.numero] = decision.resultado
        else:
            parsed[item.numero] = ItemResultado(
                numero=item.numero,
                descricao=item.descricao,
                status=StatusConformidade.NAO_ATENDIDO,
                motivo="IA não concluiu a avaliação deste item.",
                documentos_relacionados=[],
                fonte="ia",
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
    pending_llm: list[ChecklistItem] = []

    items = list(checklist.itens)
    if on_progress:
        on_progress("Aplicando regras determinísticas (nome/conteúdo)...")

    for item in items:
        decision = evaluate_item_rules(item, documents)
        if decision.resolved and decision.resultado is not None:
            all_results[item.numero] = decision.resultado
        else:
            pending_llm.append(item)

    if on_progress:
        on_progress(
            f"Regras resolveram {len(all_results)} item(ns); "
            f"{len(pending_llm)} vão para a IA..."
        )

    if pending_llm:
        total_batches = (len(pending_llm) + batch_size - 1) // batch_size
        for index, start in enumerate(range(0, len(pending_llm), batch_size), start=1):
            batch = pending_llm[start : start + batch_size]
            nums = ", ".join(str(item.numero) for item in batch)
            if on_progress:
                on_progress(
                    f"IA — lote {index}/{total_batches} (itens {nums})..."
                )
            parsed, raw = _analyze_batch(
                settings, checklist, batch, documents, inventory
            )
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
    n_regra = sum(1 for i in ordered if i.fonte == "regra")
    n_ia = sum(1 for i in ordered if i.fonte == "ia")
    resumo = (
        f"Análise para {label_tipo(checklist.tipo)} ({entidade}): "
        f"{counts['atendido']} atendido(s), {counts['parcial']} parcial(is), "
        f"{counts['nao_atendido']} não atendido(s), em {len(documents)} arquivo(s). "
        f"({n_regra} por regra, {n_ia} por IA)"
    )

    return RelatorioConformidade(
        tipo=checklist.tipo,
        entidade_detectada=entidade,
        resumo=resumo,
        itens=ordered,
        documentos_analisados=[doc.relative_path for doc in documents],
        resposta_bruta="\n\n===== LOTE =====\n\n".join(raw_parts),
        revisado=False,
    )
