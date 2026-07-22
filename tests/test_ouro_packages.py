"""
Pacotes ouro: Equador, Acari (ZIPs) e Grossos (sintético).

Roda em modo ``rules_only`` (determinístico, sem LLM).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from conformidade.analyzer import analisar_conformidade
from conformidade.checklist import TipoEntidade, load_checklist
from conformidade.config import load_settings
from conformidade.loaders import LoadedDocument, load_from_zip
from conformidade.rules import hints_for_item

ROOT = Path(__file__).resolve().parents[1]
GOLD = Path(__file__).resolve().parent / "gold"


def _assert_item(relatorio, numero: int, expect: dict) -> None:
    by_num = {i.numero: i for i in relatorio.itens}
    assert numero in by_num, f"Item {numero} ausente no relatório"
    item = by_num[numero]
    hints = hints_for_item(item.descricao)

    if "hints_contains" in expect:
        for h in expect["hints_contains"]:
            assert h in hints, f"Item {numero}: hint {h} não mapeado ({hints})"

    if "status" in expect:
        assert item.status.value == expect["status"], (
            f"Item {numero}: status={item.status.value} esperado={expect['status']} "
            f"motivo={item.motivo!r}"
        )
    if "status_in" in expect:
        assert item.status.value in expect["status_in"], (
            f"Item {numero}: status={item.status.value} não em {expect['status_in']}"
        )

    if "motivo_contains" in expect:
        ok = any(tok.lower() in item.motivo.lower() for tok in expect["motivo_contains"])
        assert ok, f"Item {numero}: motivo sem tokens {expect['motivo_contains']}: {item.motivo}"

    if "log_etapas_contains" in expect:
        etapas = [
            (x.get("etapa") if isinstance(x, dict) else getattr(x, "etapa", None))
            for x in (item.log_decisao or [])
        ]
        for e in expect["log_etapas_contains"]:
            assert e in etapas, f"Item {numero}: log sem etapa {e} (tem {etapas})"

    assert item.log_decisao, f"Item {numero}: log_decisao vazio (fonte={item.fonte})"


def _run_zip_gold(spec: dict):
    zip_path = ROOT / spec["zip"]
    if not zip_path.is_file() or zip_path.stat().st_size < 1000:
        pytest.skip(f"ZIP ouro ausente ou LFS quebrado: {zip_path}")

    settings = load_settings()
    tipo = TipoEntidade(spec["tipo"])
    checklist = load_checklist(settings.checklists_path, tipo)
    work = Path(tempfile.mkdtemp(prefix=f"ouro_{spec['nome']}_"))
    docs = load_from_zip(zip_path, work)
    assert docs, "ZIP sem documentos"

    rel = analisar_conformidade(settings, checklist, docs, rules_only=True)
    for num_str, expect in spec["asserts"].items():
        _assert_item(rel, int(num_str), expect)
    return rel


def test_ouro_equador():
    spec = json.loads((GOLD / "equador_expected.json").read_text(encoding="utf-8"))
    rel = _run_zip_gold(spec)
    assert "equador" in rel.entidade_detectada.lower() or rel.entidade_detectada


def test_ouro_acari():
    spec = json.loads((GOLD / "acari_expected.json").read_text(encoding="utf-8"))
    rel = _run_zip_gold(spec)
    assert rel.itens


def _grossos_documents() -> list[LoadedDocument]:
    """Pacote mínimo espelhando Z-38 Grossos (FOR-198 + ata escaneada fraca)."""
    return [
        LoadedDocument(
            source="oficio.txt",
            content=(
                "Ofício ao Superintendente da CODEVASF. Colônia de Pescadores Z-38 "
                "Grossos requer doação de equipamentos de pesca. Assinado pelo presidente."
            ),
            file_name="OFICIO_Z38_GROSSOS.pdf",
            relative_path="OFICIO_Z38_GROSSOS.pdf",
        ),
        LoadedDocument(
            source="for198.txt",
            content=(
                "DECLARAÇÃO DE NÃO OCORRÊNCIA DE IMPEDIMENTOS. Declaro que a entidade "
                "não se enquadra nas vedações do art. 39 da Lei nº 13.019/2014. FOR – 198."
            ),
            file_name="FOR.198_DECLARACAO.DE.NAO.IMPEDIMENTO_GROSSOS_z38.pdf",
            relative_path="FOR.198_DECLARACAO.DE.NAO.IMPEDIMENTO_GROSSOS_z38.pdf",
        ),
        LoadedDocument(
            source="ata.txt",
            content="|||| ~~ scan ilegivel ~~",
            file_name="ATA_ELEICAO_DIRETORIA_Z38.pdf",
            relative_path="ATA_ELEICAO_DIRETORIA_Z38.pdf",
            extraction_method="ocr",
        ),
        LoadedDocument(
            source="cnpj.txt",
            content="Cadastro Nacional da Pessoa Jurídica CNPJ 04.252.011/0001-10 COLONIA Z-38",
            file_name="CNPJ_Z38.pdf",
            relative_path="CNPJ_Z38.pdf",
        ),
        LoadedDocument(
            source="plano.txt",
            content="Plano de uso do bem. Destinação social dos equipamentos de pesca. FOR-196.",
            file_name="FOR.196_PLANO_DE_USO.pdf",
            relative_path="FOR.196_PLANO_DE_USO.pdf",
        ),
    ]


def test_ouro_grossos_sintetico():
    spec = json.loads((GOLD / "grossos_expected.json").read_text(encoding="utf-8"))
    settings = load_settings()
    checklist = load_checklist(settings.checklists_path, TipoEntidade.ASSOCIACAO)
    docs = _grossos_documents()
    rel = analisar_conformidade(settings, checklist, docs, rules_only=True)

    # Item 9 = doacao onerosa na lista associação
    onerosa_nums = [
        i.numero
        for i in checklist.itens
        if "onerosa" in i.descricao.lower() or "contrapartida" in i.descricao.lower()
    ]
    assert onerosa_nums, "Checklist associação sem item onerosa"
    expect_onerosa = spec["asserts"]["9"]
    _assert_item(rel, onerosa_nums[0], expect_onerosa)

    ata_nums = [
        i.numero
        for i in checklist.itens
        if "diretoria" in i.descricao.lower() or "eleição" in i.descricao.lower() or "eleicao" in i.descricao.lower()
    ]
    if ata_nums and "3" in spec["asserts"]:
        _assert_item(rel, ata_nums[0], spec["asserts"]["3"])
