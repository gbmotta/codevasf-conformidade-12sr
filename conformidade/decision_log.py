"""
Log de decisão por item (regra / ML / LLM / pós-processamento).

Permite auditar por que um item ficou atendido/parcial/não atendido.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from conformidade.models import ItemResultado, StatusConformidade


@dataclass
class DecisionStep:
    """Um passo na trilha de decisão do item."""

    etapa: str  # regra | ml | llm | pos | humano
    detalhe: str
    status_apos: str | None = None
    documentos: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    ts: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> DecisionStep:
        return cls(
            etapa=str(data.get("etapa", "")),
            detalhe=str(data.get("detalhe", "")),
            status_apos=data.get("status_apos"),
            documentos=list(data.get("documentos") or []),
            meta=dict(data.get("meta") or {}),
            ts=str(data.get("ts") or ""),
        )


def step(
    etapa: str,
    detalhe: str,
    *,
    status: StatusConformidade | str | None = None,
    documentos: list[str] | None = None,
    **meta: Any,
) -> DecisionStep:
    status_val = None
    if status is not None:
        status_val = status.value if isinstance(status, StatusConformidade) else str(status)
    return DecisionStep(
        etapa=etapa,
        detalhe=detalhe,
        status_apos=status_val,
        documentos=list(documentos or []),
        meta={k: v for k, v in meta.items() if v is not None},
    )


def append_step(item: ItemResultado, s: DecisionStep) -> ItemResultado:
    """Anexa passo ao log do item (mutável)."""
    if not hasattr(item, "log_decisao") or item.log_decisao is None:
        item.log_decisao = []
    item.log_decisao.append(s.to_dict())
    return item


def with_steps(item: ItemResultado, *steps: DecisionStep) -> ItemResultado:
    for s in steps:
        append_step(item, s)
    return item


def format_log_markdown(item: ItemResultado) -> str:
    logs = getattr(item, "log_decisao", None) or []
    if not logs:
        return f"- (sem log) fonte={item.fonte}"
    lines = []
    for i, raw in enumerate(logs, start=1):
        s = DecisionStep.from_dict(raw) if isinstance(raw, dict) else raw
        st = f" → {s.status_apos}" if s.status_apos else ""
        docs = f" [{', '.join(s.documentos)}]" if s.documentos else ""
        lines.append(f"  {i}. **{s.etapa}**{st}{docs}: {s.detalhe}")
    return "\n".join(lines)


def relatorio_decision_log(itens: list[ItemResultado]) -> list[dict]:
    """Lista plana para auditoria / export JSON."""
    rows = []
    for item in itens:
        for raw in getattr(item, "log_decisao", None) or []:
            s = DecisionStep.from_dict(raw) if isinstance(raw, dict) else raw
            rows.append(
                {
                    "numero": item.numero,
                    "descricao": item.descricao[:120],
                    "status_final": item.status.value,
                    "fonte_final": item.fonte,
                    **s.to_dict(),
                }
            )
    return rows
