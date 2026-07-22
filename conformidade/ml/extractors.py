"""
Extratores determinísticos + leves (CNPJ, CPF, datas, validade).

Não usam LLM — regex e parsing de datas em português.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

_CNPJ_RE = re.compile(
    r"\b(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})\b"
)
_CPF_RE = re.compile(r"\b(\d{3}\.?\d{3}\.?\d{3}-?\d{2})\b")
_DATE_RE = re.compile(
    r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})\b"
)
_VALIDADE_CTX = re.compile(
    r"(valida(?:de)?|válida(?:de)?|vencimento|válido\s+até|valido\s+ate|"
    r"com\s+validade|emitida?\s+em|data\s+de\s+emiss)",
    re.IGNORECASE,
)


@dataclass
class ExtractedFields:
    cnpjs: list[str]
    cpfs: list[str]
    datas: list[date]
    validade: date | None
    emitida_em: date | None

    @property
    def cnpj(self) -> str | None:
        return self.cnpjs[0] if self.cnpjs else None

    @property
    def cpf(self) -> str | None:
        return self.cpfs[0] if self.cpfs else None


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def _valid_cnpj(num: str) -> bool:
    n = _digits(num)
    if len(n) != 14 or n == n[0] * 14:
        return False
    # Validação módulo 11 (simplificada)
    def _dv(base: str, weights: Iterable[int]) -> str:
        total = sum(int(d) * w for d, w in zip(base, weights))
        r = total % 11
        return "0" if r < 2 else str(11 - r)

    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    d1 = _dv(n[:12], w1)
    d2 = _dv(n[:12] + d1, w2)
    return n[-2:] == d1 + d2


def _valid_cpf(num: str) -> bool:
    n = _digits(num)
    if len(n) != 11 or n == n[0] * 11:
        return False

    def _dv(base: str) -> str:
        s = sum(int(d) * w for d, w in zip(base, range(len(base) + 1, 1, -1)))
        r = (s * 10) % 11
        return "0" if r == 10 else str(r)

    return n[-2:] == _dv(n[:9]) + _dv(n[:10])


def _parse_date(d: str, m: str, y: str) -> date | None:
    try:
        day, month, year = int(d), int(m), int(y)
        if year < 100:
            year += 2000 if year < 70 else 1900
        return date(year, month, day)
    except ValueError:
        return None


def format_cnpj(num: str) -> str:
    n = _digits(num)
    if len(n) != 14:
        return num
    return f"{n[:2]}.{n[2:5]}.{n[5:8]}/{n[8:12]}-{n[12:]}"


def extract_fields(text: str) -> ExtractedFields:
    text = text or ""
    cnpjs: list[str] = []
    for m in _CNPJ_RE.finditer(text):
        raw = m.group(1)
        if _valid_cnpj(raw):
            fmt = format_cnpj(raw)
            if fmt not in cnpjs:
                cnpjs.append(fmt)

    cpfs: list[str] = []
    for m in _CPF_RE.finditer(text):
        raw = m.group(1)
        # Evita capturar pedaço de CNPJ
        if _valid_cpf(raw):
            n = _digits(raw)
            fmt = f"{n[:3]}.{n[3:6]}.{n[6:9]}-{n[9:]}"
            if fmt not in cpfs:
                cpfs.append(fmt)

    datas: list[date] = []
    for m in _DATE_RE.finditer(text):
        parsed = _parse_date(m.group(1), m.group(2), m.group(3))
        if parsed and date(1990, 1, 1) <= parsed <= date.today() + timedelta(days=365 * 5):
            if parsed not in datas:
                datas.append(parsed)

    validade = None
    emitida = None
    # Procura data perto de palavras de validade / emissão
    for m in _DATE_RE.finditer(text):
        start = max(0, m.start() - 40)
        ctx = text[start : m.end() + 10]
        parsed = _parse_date(m.group(1), m.group(2), m.group(3))
        if not parsed:
            continue
        if _VALIDADE_CTX.search(ctx):
            low = ctx.lower()
            if any(k in low for k in ("emit", "emiss")):
                if emitida is None or parsed > emitida:
                    emitida = parsed
            else:
                if validade is None or parsed > validade:
                    validade = parsed

    # Fallback: maior data futura ou mais recente no texto
    if validade is None and datas:
        futuras = [d for d in datas if d >= date.today()]
        validade = max(futuras) if futuras else max(datas)

    return ExtractedFields(
        cnpjs=cnpjs,
        cpfs=cpfs,
        datas=datas,
        validade=validade,
        emitida_em=emitida,
    )


def validade_status(
    text: str,
    *,
    referencia: date | None = None,
    margem_dias: int = 0,
    alerta_dias: int | None = None,
) -> tuple[str, date | None, str]:
    """
    Retorna (status, data, motivo) com status em:
      ok | a_vencer | vencida | sem_data | duvida

    ``alerta_dias``: se a validade cair dentro desta janela, status = a_vencer.
    Padrão: variável VALIDADE_ALERTA_DIAS ou 30.
    """
    import os

    ref = referencia or date.today()
    if alerta_dias is None:
        alerta_dias = int(os.getenv("VALIDADE_ALERTA_DIAS", "30"))

    fields = extract_fields(text)
    if fields.validade is None:
        return "sem_data", None, "Não foi possível extrair data de validade no texto."
    limite = fields.validade + timedelta(days=margem_dias)
    dias = (limite - ref).days
    data_fmt = fields.validade.strftime("%d/%m/%Y")
    if dias < 0:
        return (
            "vencida",
            fields.validade,
            f"Validade {data_fmt} está vencida há {abs(dias)} dia(s).",
        )
    if dias <= alerta_dias:
        return (
            "a_vencer",
            fields.validade,
            f"Validade {data_fmt}: faltam {dias} dia(s) (alerta ≤ {alerta_dias}d).",
        )
    return (
        "ok",
        fields.validade,
        f"Validade {data_fmt}: vigente, faltam {dias} dia(s).",
    )
