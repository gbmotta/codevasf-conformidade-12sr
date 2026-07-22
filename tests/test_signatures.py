"""Testes da detecção de assinatura (digital vs tinta)."""

from __future__ import annotations

from pathlib import Path

import pytest

from conformidade.ml.signatures import (
    probe_pdf_digital_signature,
    probe_signature,
    probe_signature_text,
)

JUNDIA = Path(
    r"C:\Users\gabriel.camara\Documents\Analises_Conformidade\03_Processos"
    r"\213 - Prefeitura Jundia"
)


def test_texto_assinado_de_forma_digital():
    ok, _ = probe_signature_text(
        "CARLOS ANTONIO DE SOUZA:76270572487 Assinado de forma digital por CARLOS"
    )
    assert ok is True


def test_jundia_contrapartida_digital(tmp_path_factory):
    if not JUNDIA.is_dir():
        pytest.skip("Pacote Jundiá ausente neste ambiente")
    pdf = next(JUNDIA.glob("*CONTRAPARTIDA*"), None)
    assert pdf is not None
    crypto, reason = probe_pdf_digital_signature(pdf)
    assert crypto, reason
    # Conteúdo típico do pypdf (sem o carimbo) não deve gerar falso positivo
    pypdf_like = (
        "DECLARAÇÃO DE CONTRAPARTIDA O Município de Jundiá declara "
        "aceitação à modalidade de Doação Onerosa. CARLOS ANTONIO DE SOUZA "
        "Prefeito Municipal"
    )
    probe = probe_signature(text=pypdf_like, file_path=pdf, extraction_method="texto")
    assert probe.digital_crypto or probe.has_signature_hint
    assert not probe.seems_unsigned
    assert "digital" in probe.reason.lower() or "sigflags" in probe.reason.lower()


def test_born_digital_sem_crypto_nao_usa_tinta(tmp_path):
    # Sem arquivo PDF real: só texto longo → não marca unsigned por tinta
    probe = probe_signature(
        text="Ofício formal longo. " * 40,
        file_path=None,
        extraction_method="texto",
    )
    # Sem path, ink não aplicável da mesma forma; seems_unsigned não deve
    # depender de razão=0.000 inventada
    assert probe.ink_ratio_bottom is None or not probe.seems_unsigned or probe.confidence < 0.9
