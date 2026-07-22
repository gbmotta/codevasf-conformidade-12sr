"""Testes do log de decisão (regra / ML / LLM / pós)."""

from __future__ import annotations

from conformidade.analyzer import analisar_conformidade
from conformidade.checklist import TipoEntidade, load_checklist
from conformidade.config import load_settings
from conformidade.decision_log import format_log_markdown, relatorio_decision_log, step
from conformidade.loaders import LoadedDocument
from conformidade.models import ItemResultado, StatusConformidade, aplicar_revisao_humana
from conformidade.rules import evaluate_item_rules


def test_regra_onerosa_gera_log():
    item = load_checklist(load_settings().checklists_path, TipoEntidade.ASSOCIACAO).itens
    onerosa = next(i for i in item if "onerosa" in i.descricao.lower())
    docs = [
        LoadedDocument(
            "x",
            "Declaração de Não Ocorrência de Impedimentos art. 39 Lei 13.019 FOR 198",
            "FOR.198.pdf",
            "FOR.198.pdf",
        )
    ]
    dec = evaluate_item_rules(onerosa, docs)
    assert dec.resolved and dec.resultado
    assert dec.resultado.log_decisao
    assert any(s.get("etapa") == "regra" for s in dec.resultado.log_decisao)


def test_rules_only_marca_llm_pulado(monkeypatch):
    """Com pending LLM + rules_only, cada item pendente registra etapa llm pulado."""
    from conformidade import analyzer as az
    from conformidade.rules import RuleDecision

    settings = load_settings()
    checklist = load_checklist(settings.checklists_path, TipoEntidade.PREFEITURA)
    docs = [
        LoadedDocument(
            "x",
            "Comprovante CNPJ 04.252.011/0001-10 Prefeitura Municipal de Teste",
            "cnpj.pdf",
            "cnpj.pdf",
        )
    ]

    original = az.evaluate_item_rules

    def _fake(item, documents):
        # Força um item à fila LLM para exercitar o ramo rules_only
        if item.numero == 1:
            return RuleDecision(resolved=False)
        return original(item, documents)

    monkeypatch.setattr(az, "evaluate_item_rules", _fake)
    rel = analisar_conformidade(settings, checklist, docs, rules_only=True)
    item1 = next(i for i in rel.itens if i.numero == 1)
    assert any(
        s.get("etapa") == "llm" and "Pulado" in s.get("detalhe", "")
        for s in (item1.log_decisao or [])
    )
    flat = relatorio_decision_log(rel.itens)
    assert flat
    assert item1.status.value == "nao_atendido"


def test_revisao_humana_loga():
    from conformidade.models import RelatorioConformidade

    item = ItemResultado(
        1,
        "Ofício",
        StatusConformidade.NAO_ATENDIDO,
        "ausente",
        fonte="regra",
        log_decisao=[step("regra", "ausente", status="nao_atendido").to_dict()],
    )
    rel = RelatorioConformidade(
        TipoEntidade.PREFEITURA,
        "X",
        "r",
        [item],
        ["a.pdf"],
    )
    aplicar_revisao_humana(rel, [{"numero": 1, "status": "atendido", "motivo": "Conferido"}])
    assert item.fonte == "humano"
    assert any(s.get("etapa") == "humano" for s in item.log_decisao)
    md = format_log_markdown(item)
    assert "humano" in md
