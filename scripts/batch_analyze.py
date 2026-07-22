#!/usr/bin/env python3
"""
Análise em lote: vários ZIPs → planilha consolidada (+ histórico).

Uso:
  python scripts/batch_analyze.py --zips-dir ./pacotes --tipo associacao --out consolidado.xlsx
  python scripts/batch_analyze.py zip1.zip zip2.zip --tipo prefeitura
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conformidade.batch import analyze_zip_batch
from conformidade.checklist import TipoEntidade
from conformidade.config import load_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Análise consolidada em lote")
    parser.add_argument("zips", nargs="*", type=Path, help="Arquivos ZIP")
    parser.add_argument("--zips-dir", type=Path, help="Pasta com vários ZIPs")
    parser.add_argument(
        "--tipo",
        choices=["prefeitura", "associacao"],
        default="associacao",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data" / "history" / "consolidado_lote.xlsx",
    )
    parser.add_argument("--no-history", action="store_true")
    args = parser.parse_args()

    paths: list[Path] = list(args.zips)
    if args.zips_dir:
        paths.extend(sorted(args.zips_dir.glob("*.zip")))
    paths = [p for p in paths if p.is_file()]
    if not paths:
        raise SystemExit("Nenhum ZIP informado.")

    tipo = (
        TipoEntidade.PREFEITURA
        if args.tipo == "prefeitura"
        else TipoEntidade.ASSOCIACAO
    )
    settings = load_settings()

    def _prog(msg: str) -> None:
        print(msg)

    result = analyze_zip_batch(
        settings,
        paths,
        tipo,
        save_history=not args.no_history,
        on_progress=_prog,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(result.to_xlsx_bytes())
    print(f"Planilha: {args.out} ({len(result.rows)} pacotes)")


if __name__ == "__main__":
    main()
