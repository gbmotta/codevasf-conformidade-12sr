#!/usr/bin/env python3
"""
Exporta CSV de rótulos para treino do classificador de documentos.

Fontes:
  1. Relatórios JSON (RelatorioConformidade.to_dict) — item atendido + arquivos
  2. Pasta de documentos — pseudo-rótulo heurístico (weak labels)
  3. Mescla com seed sintético embutido

Uso:
  python scripts/export_doc_labels.py --reports-dir ./data/reports --out data/ml/labels.csv
  python scripts/export_doc_labels.py --docs-dir ./pacote_extraido --out data/ml/labels.csv
  python scripts/export_doc_labels.py --seed-only --out data/ml/labels.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conformidade.loaders import load_file, scan_folder
from conformidade.ml.features import feature_text_from_parts
from conformidade.ml.heuristics import weak_label_document
from conformidade.ml.schema import HINT_TO_LABEL, LABEL_DESCRIPTIONS, DocLabel, parse_label
from conformidade.ml.seed_data import SEED_EXAMPLES
from conformidade.rules import hints_for_item


def _rows_from_seed() -> list[dict]:
    rows = []
    for file_name, content, label in SEED_EXAMPLES:
        rows.append(
            {
                "file_name": file_name,
                "content": content,
                "text": feature_text_from_parts(file_name, content),
                "label": parse_label(label).value,
                "source": "seed",
                "confidence": "1.0",
            }
        )
    return rows


def _rows_from_docs_dir(docs_dir: Path) -> list[dict]:
    rows = []
    documents = scan_folder(docs_dir)
    for doc in documents:
        label, conf = weak_label_document(doc)
        rows.append(
            {
                "file_name": doc.file_name,
                "content": (doc.content or "")[:4000],
                "text": feature_text_from_parts(doc.file_name, doc.content or ""),
                "label": label.value,
                "source": "heuristica",
                "confidence": f"{conf:.2f}",
            }
        )
    return rows


def _item_to_label(descricao: str, motivo: str) -> DocLabel | None:
    motivo_l = (motivo or "").lower()
    if "for-198" in motivo_l or "impedimento" in motivo_l:
        return DocLabel.IMPEDIMENTO
    hints = hints_for_item(descricao)
    if not hints:
        return None
    return HINT_TO_LABEL.get(hints[0])


def _rows_from_reports(reports_dir: Path, docs_root: Path | None) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(reports_dir.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        itens = data.get("itens") or []
        for item in itens:
            status = str(item.get("status", "")).lower()
            if status not in {"atendido", "parcial"}:
                continue
            label = _item_to_label(str(item.get("descricao", "")), str(item.get("motivo", "")))
            if label is None:
                continue
            for rel in item.get("documentos_relacionados") or []:
                content = ""
                file_name = Path(str(rel)).name
                if docs_root and docs_root.exists():
                    # tenta achar o arquivo pelo nome
                    matches = list(docs_root.rglob(file_name))
                    if matches:
                        loaded = load_file(matches[0], root=docs_root)
                        if loaded:
                            content = loaded.content[:4000]
                rows.append(
                    {
                        "file_name": file_name,
                        "content": content,
                        "text": feature_text_from_parts(file_name, content),
                        "label": label.value,
                        "source": f"relatorio:{path.name}",
                        "confidence": "0.85" if status == "atendido" else "0.6",
                    }
                )
    return rows


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["file_name", "content", "text", "label", "source", "confidence"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})

    # Schema auxiliar
    schema_path = path.with_name("labels_schema.json")
    schema = {
        label.value: LABEL_DESCRIPTIONS[label]
        for label in DocLabel
    }
    schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta CSV de rótulos de documentos")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "ml" / "labels.csv")
    parser.add_argument("--reports-dir", type=Path, help="Pasta com JSON de RelatorioConformidade")
    parser.add_argument("--docs-dir", type=Path, help="Pasta com PDFs para weak labels")
    parser.add_argument("--docs-root", type=Path, help="Raiz dos arquivos citados nos relatórios")
    parser.add_argument("--seed-only", action="store_true", help="Somente exemplos sintéticos")
    parser.add_argument("--no-seed", action="store_true", help="Não incluir seed")
    args = parser.parse_args()

    rows: list[dict] = []
    if not args.no_seed or args.seed_only:
        rows.extend(_rows_from_seed())
    if args.seed_only:
        _write_csv(args.out, rows)
        print(f"Exportados {len(rows)} exemplos (seed) → {args.out}")
        return

    if args.reports_dir:
        rows.extend(_rows_from_reports(args.reports_dir, args.docs_root))
    if args.docs_dir:
        rows.extend(_rows_from_docs_dir(args.docs_dir))

    if not rows:
        rows.extend(_rows_from_seed())
        print("Nenhuma fonte informada — usando seed sintético.")

    _write_csv(args.out, rows)
    from collections import Counter

    counts = Counter(r["label"] for r in rows)
    print(f"Exportados {len(rows)} exemplos → {args.out}")
    print("Por classe:", dict(counts))


if __name__ == "__main__":
    main()
