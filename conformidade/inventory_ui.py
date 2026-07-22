"""
Helpers de UI: inventário tipado, alertas de validade e export de rótulos CSV.

Usado por Gradio (app.py) e Streamlit (app/streamlit_app.py).
"""

from __future__ import annotations

import csv
import io
import os
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from conformidade.loaders import LoadedDocument
from conformidade.ml.extractors import validade_status
from conformidade.ml.schema import LABEL_DESCRIPTIONS, DocLabel
from conformidade.models import RelatorioConformidade

# Certidões com checagem de validade
_VALIDADE_LABELS = {
    DocLabel.FEDERAL.value,
    DocLabel.FGTS.value,
    DocLabel.CNDT.value,
}

VALIDADE_ALERTA_DIAS = int(os.getenv("VALIDADE_ALERTA_DIAS", "30"))


@dataclass
class InventoryEntry:
    relative_path: str
    file_name: str
    label: str
    label_desc: str
    confidence: float
    source: str
    method: str
    chars: int
    validade_status: str | None = None
    validade_dias: int | None = None
    validade_data: str | None = None
    validade_msg: str | None = None
    content: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> InventoryEntry:
        return cls(
            relative_path=str(data.get("relative_path", "")),
            file_name=str(data.get("file_name", "")),
            label=str(data.get("label", "outro")),
            label_desc=str(data.get("label_desc", "")),
            confidence=float(data.get("confidence") or 0),
            source=str(data.get("source", "")),
            method=str(data.get("method", "texto")),
            chars=int(data.get("chars") or 0),
            validade_status=data.get("validade_status"),
            validade_dias=data.get("validade_dias"),
            validade_data=data.get("validade_data"),
            validade_msg=data.get("validade_msg"),
            content=str(data.get("content") or ""),
        )


def build_inventory(documents: list[LoadedDocument]) -> list[InventoryEntry]:
    """Classifica cada arquivo e anexa info de validade quando couber."""
    from conformidade.ml.classifier import get_classifier

    clf = get_classifier()
    entries: list[InventoryEntry] = []
    for doc in documents:
        pred = clf.predict_document(doc)
        label = pred.label.value
        v_status = v_dias = v_data = v_msg = None
        if label in _VALIDADE_LABELS or any(
            k in (doc.file_name + " " + doc.content[:800]).lower()
            for k in ("fgts", "crf", "cndt", "receita federal", "divida ativa", "dívida ativa")
        ):
            st, dt, msg = validade_status(
                doc.content,
                alerta_dias=VALIDADE_ALERTA_DIAS,
            )
            v_status = st
            v_msg = msg
            if dt is not None:
                v_data = dt.strftime("%d/%m/%Y")
                v_dias = (dt - date.today()).days
        entries.append(
            InventoryEntry(
                relative_path=doc.relative_path,
                file_name=doc.file_name,
                label=label,
                label_desc=LABEL_DESCRIPTIONS.get(pred.label, label),
                confidence=round(float(pred.confidence), 3),
                source=pred.source,
                method=doc.extraction_method or "texto",
                chars=len(doc.content or ""),
                validade_status=v_status,
                validade_dias=v_dias,
                validade_data=v_data,
                validade_msg=v_msg,
                content=(doc.content or "")[:4000],
            )
        )
    return entries


def collect_validade_alerts(entries: list[InventoryEntry]) -> list[InventoryEntry]:
    """Entradas com certidão vencida ou a vencer."""
    out = []
    for e in entries:
        if e.validade_status in {"vencida", "a_vencer"}:
            out.append(e)
    return out


def validade_alerts_html(entries: list[InventoryEntry]) -> str:
    alerts = collect_validade_alerts(entries)
    if not alerts:
        return ""
    parts = ['<div class="cv-validade-alerts"><h3>Alertas de validade</h3><ul>']
    for e in alerts:
        cls = "vencida" if e.validade_status == "vencida" else "a-vencer"
        dias = e.validade_dias
        if e.validade_status == "vencida":
            extra = f"vencida há {abs(dias)} dia(s)" if dias is not None else "vencida"
        else:
            extra = f"faltam {dias} dia(s)" if dias is not None else "a vencer"
        parts.append(
            f'<li class="cv-validade-{cls}">'
            f"<strong>{e.file_name}</strong> "
            f'<span class="cv-inv-badge type-{e.label}">{e.label}</span> '
            f"— {extra}"
            f'{f" (até {e.validade_data})" if e.validade_data else ""}'
            f"{f': {e.validade_msg}' if e.validade_msg else ''}"
            "</li>"
        )
    parts.append("</ul></div>")
    return "".join(parts)


def inventory_html(entries: list[InventoryEntry]) -> str:
    if not entries:
        return '<p class="cv-muted">Nenhum arquivo no inventário.</p>'
    rows = [
        '<div class="cv-inventory"><h3>Inventário tipado</h3>',
        "<p class=\"cv-muted\">Tipo sugerido pelo classificador (ML/heurística) "
        "e método de leitura.</p><ul>",
    ]
    for e in entries:
        ext = Path(e.file_name).suffix.lower()
        kind = {
            ".pdf": "PDF",
            ".docx": "Word",
            ".doc": "Word",
            ".png": "Img",
            ".jpg": "Img",
            ".jpeg": "Img",
        }.get(ext, (ext.replace(".", "") or "Arq").upper())
        ocr = e.method in {"ocr", "hibrido"}
        method_badge = (
            '<span class="cv-inv-badge ocr">OCR</span>'
            if ocr
            else '<span class="cv-inv-badge">Texto</span>'
        )
        conf_pct = f"{e.confidence * 100:.0f}%"
        type_badge = (
            f'<span class="cv-inv-badge type-{e.label}" title="{e.label_desc}">'
            f"{e.label}</span>"
        )
        conf_badge = f'<span class="cv-inv-meta">{conf_pct} · {e.source}</span>'
        val_badge = ""
        if e.validade_status == "vencida":
            val_badge = '<span class="cv-inv-badge val-vencida">Vencida</span>'
        elif e.validade_status == "a_vencer":
            dias = e.validade_dias if e.validade_dias is not None else "?"
            val_badge = f'<span class="cv-inv-badge val-avencer">Faltam {dias}d</span>'
        elif e.validade_status == "ok" and e.validade_dias is not None:
            val_badge = f'<span class="cv-inv-badge val-ok">{e.validade_dias}d</span>'
        chars = f"{e.chars:,}".replace(",", ".")
        rows.append(
            "<li>"
            f'<span class="cv-inv-kind">{kind}</span>'
            f'<span class="cv-inv-name">{e.relative_path}</span>'
            f"{type_badge}{method_badge}{val_badge}"
            f"{conf_badge}"
            f'<span class="cv-inv-meta">{chars} car.</span>'
            "</li>"
        )
    rows.append("</ul></div>")
    return "".join(rows)


def labels_csv_bytes(entries: list[InventoryEntry]) -> bytes:
    """CSV UTF-8 BOM para Excel — file_name, content, label (+ meta)."""
    buf = io.StringIO()
    fields = [
        "file_name",
        "content",
        "label",
        "confianca",
        "fonte",
        "validade_status",
        "validade_dias",
        "validade_data",
    ]
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    for e in entries:
        writer.writerow(
            {
                "file_name": e.relative_path or e.file_name,
                "content": e.content,
                "label": e.label,
                "confianca": f"{e.confidence:.3f}",
                "fonte": e.source,
                "validade_status": e.validade_status or "",
                "validade_dias": "" if e.validade_dias is None else e.validade_dias,
                "validade_data": e.validade_data or "",
            }
        )
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def write_labels_csv(entries: list[InventoryEntry], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(labels_csv_bytes(entries))
    return path


def pack_app_state(
    relatorio: RelatorioConformidade,
    entries: list[InventoryEntry],
) -> dict:
    return {
        "relatorio": relatorio.to_dict(),
        "inventory": [e.to_dict() for e in entries],
    }


def unpack_relatorio(state_dict: dict | None) -> RelatorioConformidade | None:
    if not state_dict:
        return None
    if "relatorio" in state_dict and isinstance(state_dict["relatorio"], dict):
        return RelatorioConformidade.from_dict(state_dict["relatorio"])
    if "itens" in state_dict:
        return RelatorioConformidade.from_dict(state_dict)
    return None


def unpack_inventory(state_dict: dict | None) -> list[InventoryEntry]:
    if not state_dict:
        return []
    raw = state_dict.get("inventory") or []
    return [InventoryEntry.from_dict(x) for x in raw if isinstance(x, dict)]


def replace_relatorio_in_state(
    state_dict: dict | None,
    relatorio: RelatorioConformidade,
) -> dict:
    inv = unpack_inventory(state_dict) if state_dict else []
    return pack_app_state(relatorio, inv)
