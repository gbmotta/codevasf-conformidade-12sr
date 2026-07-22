"""
Histórico / fila de análises salvas em disco.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from conformidade.models import RelatorioConformidade

DEFAULT_HISTORY_ROOT = Path(__file__).resolve().parent.parent / "data" / "history"


@dataclass
class HistoryMeta:
    id: str
    created_at: str
    entidade: str
    tipo: str
    zip_name: str
    atendidos: int
    parciais: int
    nao_atendidos: int
    revisado: bool
    cnpj: str | None = None
    alertas: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> HistoryMeta:
        return cls(
            id=str(data["id"]),
            created_at=str(data.get("created_at", "")),
            entidade=str(data.get("entidade", "")),
            tipo=str(data.get("tipo", "")),
            zip_name=str(data.get("zip_name", "")),
            atendidos=int(data.get("atendidos") or 0),
            parciais=int(data.get("parciais") or 0),
            nao_atendidos=int(data.get("nao_atendidos") or 0),
            revisado=bool(data.get("revisado", False)),
            cnpj=data.get("cnpj"),
            alertas=list(data.get("alertas") or []),
            notes=str(data.get("notes") or ""),
        )


def history_root(path: Path | None = None) -> Path:
    root = path or Path(
        __import__("os").environ.get("HISTORY_PATH", str(DEFAULT_HISTORY_ROOT))
    )
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_analysis(
    relatorio: RelatorioConformidade,
    *,
    zip_name: str = "",
    alertas: list[str] | None = None,
    cnpj: str | None = None,
    inventory: list[dict] | None = None,
    root: Path | None = None,
) -> HistoryMeta:
    root = history_root(root)
    hid = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    folder = root / hid
    folder.mkdir(parents=True, exist_ok=True)
    counts = relatorio.contagem
    meta = HistoryMeta(
        id=hid,
        created_at=datetime.now().isoformat(timespec="seconds"),
        entidade=relatorio.entidade_detectada,
        tipo=relatorio.tipo.value,
        zip_name=zip_name,
        atendidos=counts["atendido"],
        parciais=counts["parcial"],
        nao_atendidos=counts["nao_atendido"],
        revisado=relatorio.revisado,
        cnpj=cnpj,
        alertas=list(alertas or getattr(relatorio, "alertas", []) or []),
    )
    (folder / "meta.json").write_text(
        json.dumps(meta.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (folder / "relatorio.json").write_text(
        json.dumps(relatorio.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if inventory is not None:
        (folder / "inventory.json").write_text(
            json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return meta


def list_history(root: Path | None = None, limit: int = 100) -> list[HistoryMeta]:
    root = history_root(root)
    metas: list[HistoryMeta] = []
    for folder in sorted(root.iterdir(), reverse=True):
        if not folder.is_dir():
            continue
        meta_path = folder / "meta.json"
        if not meta_path.is_file():
            continue
        try:
            metas.append(HistoryMeta.from_dict(json.loads(meta_path.read_text(encoding="utf-8"))))
        except Exception:
            continue
        if len(metas) >= limit:
            break
    return metas


def load_history(history_id: str, root: Path | None = None) -> tuple[HistoryMeta, RelatorioConformidade]:
    root = history_root(root)
    folder = root / history_id
    meta = HistoryMeta.from_dict(
        json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    )
    rel = RelatorioConformidade.from_dict(
        json.loads((folder / "relatorio.json").read_text(encoding="utf-8"))
    )
    return meta, rel


def compare_history(
    id_a: str,
    id_b: str,
    root: Path | None = None,
) -> list[dict]:
    """Compara status item a item entre duas análises."""
    _, rel_a = load_history(id_a, root)
    _, rel_b = load_history(id_b, root)
    by_b = {i.numero: i for i in rel_b.itens}
    rows = []
    for item in rel_a.itens:
        other = by_b.get(item.numero)
        rows.append(
            {
                "numero": item.numero,
                "descricao": item.descricao[:80],
                "status_a": item.status.value,
                "status_b": other.status.value if other else "(ausente)",
                "mudou": (other is None) or (other.status != item.status),
            }
        )
    return rows
