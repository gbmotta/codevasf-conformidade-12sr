"""
Modelos de dados do relatório de conformidade.

Inclui ``StatusConformidade``, ``ItemResultado``, ``RelatorioConformidade``
e ``aplicar_revisao_humana`` (override de status/motivo pela equipe).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum

from conformidade.checklist import TipoEntidade


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


def normalize_status(raw: str) -> StatusConformidade:
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


@dataclass
class ItemResultado:
    numero: int
    descricao: str
    status: StatusConformidade
    motivo: str
    documentos_relacionados: list[str] = field(default_factory=list)
    fonte: str = "ia"  # regra | ia | humano

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> ItemResultado:
        return cls(
            numero=int(data["numero"]),
            descricao=str(data["descricao"]),
            status=normalize_status(str(data.get("status", "nao_atendido"))),
            motivo=str(data.get("motivo", "")),
            documentos_relacionados=list(data.get("documentos_relacionados") or []),
            fonte=str(data.get("fonte", "ia")),
        )


@dataclass
class RelatorioConformidade:
    tipo: TipoEntidade
    entidade_detectada: str
    resumo: str
    itens: list[ItemResultado]
    documentos_analisados: list[str]
    resposta_bruta: str = ""
    revisado: bool = False

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

    def to_dict(self) -> dict:
        return {
            "tipo": self.tipo.value,
            "entidade_detectada": self.entidade_detectada,
            "resumo": self.resumo,
            "itens": [item.to_dict() for item in self.itens],
            "documentos_analisados": list(self.documentos_analisados),
            "resposta_bruta": self.resposta_bruta,
            "revisado": self.revisado,
        }

    @classmethod
    def from_dict(cls, data: dict) -> RelatorioConformidade:
        return cls(
            tipo=TipoEntidade(data["tipo"]),
            entidade_detectada=str(data.get("entidade_detectada", "")),
            resumo=str(data.get("resumo", "")),
            itens=[ItemResultado.from_dict(i) for i in data.get("itens", [])],
            documentos_analisados=list(data.get("documentos_analisados") or []),
            resposta_bruta=str(data.get("resposta_bruta", "")),
            revisado=bool(data.get("revisado", False)),
        )


def aplicar_revisao_humana(
    relatorio: RelatorioConformidade,
    overrides: list[dict],
) -> RelatorioConformidade:
    """Aplica ajustes humanos (status/motivo) e marca o relatório como revisado."""
    by_num = {item.numero: item for item in relatorio.itens}
    for row in overrides:
        try:
            numero = int(row.get("numero"))
        except (TypeError, ValueError):
            continue
        item = by_num.get(numero)
        if item is None:
            continue
        new_status = normalize_status(str(row.get("status", item.status.value)))
        new_motivo = str(row.get("motivo") or item.motivo).strip() or item.motivo
        if new_status != item.status or new_motivo != item.motivo:
            item.status = new_status
            item.motivo = new_motivo
            item.fonte = "humano"

    counts = relatorio.contagem
    base = relatorio.resumo.split(":")[0] if ":" in relatorio.resumo else relatorio.resumo
    relatorio.resumo = (
        f"{base}: {counts['atendido']} atendido(s), {counts['parcial']} parcial(is), "
        f"{counts['nao_atendido']} não atendido(s) — versão revisada."
    )
    relatorio.revisado = True
    return relatorio
