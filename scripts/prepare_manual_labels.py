#!/usr/bin/env python3
"""
Prepara CSV para rotulagem MANUAL (tipo 3).

Lê uma pasta (ou ZIP) de documentos, extrai texto e gera CSV com:
  file_name, content, label
Você só preenche a coluna ``label`` no Excel / LibreOffice.

Uso:
  python scripts/prepare_manual_labels.py --docs-dir "C:\\pacote\\entidade"
  python scripts/prepare_manual_labels.py --zip "C:\\envio.zip" --out data/ml/para_rotular.csv

Labels válidos (copie exatamente):
  oficio, cnpj, federal, fgts, cndt, posse, diploma, rg_cpf, eleitoral,
  residencia, doacao_onerosa, impedimento, plano_uso, estatuto,
  ata_diretoria, outro, ilegivel
"""

from __future__ import annotations

import argparse
import csv
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conformidade.loaders import extract_zip, scan_folder
from conformidade.ml.heuristics import weak_label_document
from conformidade.ml.schema import LABEL_DESCRIPTIONS, DocLabel

VALID_LABELS = [x.value for x in DocLabel]


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepara CSV para rotulagem manual")
    parser.add_argument("--docs-dir", type=Path, help="Pasta com PDFs/imagens")
    parser.add_argument("--zip", type=Path, help="ZIP do requerimento")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data" / "ml" / "para_rotular.csv",
        help="CSV de saída",
    )
    parser.add_argument(
        "--suggest",
        action="store_true",
        help="Preenche label com sugestão heurística (revise no Excel!)",
    )
    parser.add_argument(
        "--content-chars",
        type=int,
        default=4000,
        help="Máximo de caracteres de conteúdo por linha",
    )
    args = parser.parse_args()

    if not args.docs_dir and not args.zip:
        raise SystemExit("Informe --docs-dir ou --zip")

    work = Path(tempfile.mkdtemp(prefix="labels_manual_"))
    if args.zip:
        docs_dir = extract_zip(args.zip, work)
    else:
        docs_dir = args.docs_dir

    documents = scan_folder(docs_dir)
    if not documents:
        raise SystemExit(f"Nenhum documento encontrado em {docs_dir}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["file_name", "content", "label", "sugestao", "descricao_sugestao"]
    with args.out.open("w", encoding="utf-8-sig", newline="") as fh:
        # utf-8-sig = Excel no Windows abre acentos corretamente
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for doc in documents:
            suggested, conf = weak_label_document(doc)
            label = suggested.value if args.suggest else ""
            writer.writerow(
                {
                    "file_name": doc.relative_path or doc.file_name,
                    "content": (doc.content or "")[: args.content_chars],
                    "label": label,
                    "sugestao": f"{suggested.value} ({conf:.2f})",
                    "descricao_sugestao": LABEL_DESCRIPTIONS.get(suggested, ""),
                }
            )

    legend = args.out.with_name("ROTULOS_VALIDOS.txt")
    lines = [
        "Preencha a coluna label com UM destes valores (sem acento, minúsculo):",
        "",
    ]
    for lab in DocLabel:
        lines.append(f"  {lab.value:18}  {LABEL_DESCRIPTIONS[lab]}")
    lines.extend(
        [
            "",
            "Dicas:",
            "  - FOR-198 / impedimentos  →  impedimento  (NÃO use doacao_onerosa)",
            "  - Aceitação 1% ou 1,5%    →  doacao_onerosa",
            "  - CRF / Caixa FGTS        →  fgts",
            "  - CND Receita / Dívida    →  federal",
            "  - CNDT trabalhista        →  cndt",
            "  - OCR ilegível            →  ilegivel",
            "  - Não encaixa             →  outro",
            "",
            "Depois de rotular:",
            "  python scripts/train_doc_classifier.py --csv " + str(args.out),
        ]
    )
    legend.write_text("\n".join(lines), encoding="utf-8")

    print(f"CSV gerado: {args.out}")
    print(f"Legenda:    {legend}")
    print(f"Arquivos:   {len(documents)}")
    print("Abra no Excel, preencha a coluna label e salve (CSV UTF-8).")
    if args.suggest:
        print("ATENÇÃO: labels já vieram com sugestão — revise um a um.")


if __name__ == "__main__":
    main()
