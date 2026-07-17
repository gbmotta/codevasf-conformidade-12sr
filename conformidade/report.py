"""Geração de relatório textual e Excel para download."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from conformidade.analyzer import RelatorioConformidade, StatusConformidade
from conformidade.checklist import label_tipo


STATUS_LABEL = {
    StatusConformidade.ATENDIDO: "ATENDIDO",
    StatusConformidade.PARCIAL: "PARCIAL",
    StatusConformidade.NAO_ATENDIDO: "NAO ATENDIDO",
}

STATUS_FILL = {
    StatusConformidade.ATENDIDO: PatternFill("solid", fgColor="C6EFCE"),
    StatusConformidade.PARCIAL: PatternFill("solid", fgColor="FFEB9C"),
    StatusConformidade.NAO_ATENDIDO: PatternFill("solid", fgColor="FFC7CE"),
}


def relatorio_para_markdown(relatorio: RelatorioConformidade) -> str:
    counts = relatorio.contagem
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    lines = [
        "# CODEVASF 12ª SR — Relatório de Conformidade Documental",
        "",
        f"- **Data:** {agora}",
        f"- **Tipo:** {label_tipo(relatorio.tipo)}",
        f"- **Entidade / município:** {relatorio.entidade_detectada}",
        f"- **Resumo:** {relatorio.resumo}",
        f"- **Atendidos:** {counts['atendido']}",
        f"- **Parciais:** {counts['parcial']}",
        f"- **Não atendidos:** {counts['nao_atendido']}",
        f"- **Versão:** {'revisada (ajuste humano)' if relatorio.revisado else 'automática'}",
        "",
        "## Itens do checklist",
        "",
    ]
    for item in relatorio.itens:
        lines.append(
            f"### {item.numero}. [{STATUS_LABEL[item.status]}] "
            f"({item.fonte}) {item.descricao}"
        )
        lines.append("")
        lines.append(f"**Motivo:** {item.motivo}")
        if item.documentos_relacionados:
            lines.append("")
            lines.append("**Arquivos:** " + ", ".join(item.documentos_relacionados))
        lines.append("")

    lines.extend(
        [
            "## Documentos analisados",
            "",
        ]
    )
    for name in relatorio.documentos_analisados:
        lines.append(f"- `{name}`")

    lines.extend(
        [
            "",
            "---",
            "_Relatório assistivo gerado no servidor interno da 12ª SR. "
            "A decisão final permanece com a equipe técnica._",
        ]
    )
    return "\n".join(lines)


def relatorio_para_xlsx(relatorio: RelatorioConformidade) -> bytes:
    """Gera planilha Excel com resumo, itens e documentos analisados."""
    counts = relatorio.contagem
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    wb = Workbook()
    ws_resumo = wb.active
    ws_resumo.title = "Resumo"

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="006633")
    label_font = Font(bold=True)
    thin = Border(
        left=Side(style="thin", color="B7C9BE"),
        right=Side(style="thin", color="B7C9BE"),
        top=Side(style="thin", color="B7C9BE"),
        bottom=Side(style="thin", color="B7C9BE"),
    )
    wrap = Alignment(wrap_text=True, vertical="top")

    ws_resumo["A1"] = "CODEVASF 12ª SR — Relatório de Conformidade Documental"
    ws_resumo["A1"].font = Font(bold=True, size=14, color="006633")
    ws_resumo.merge_cells("A1:B1")

    resumo_rows = [
        ("Data", agora),
        ("Tipo", label_tipo(relatorio.tipo)),
        ("Entidade / município", relatorio.entidade_detectada),
        ("Resumo", relatorio.resumo),
        ("Itens do checklist", len(relatorio.itens)),
        ("Atendidos", counts["atendido"]),
        ("Parciais", counts["parcial"]),
        ("Não atendidos", counts["nao_atendido"]),
        ("Versão", "Revisada (humano)" if relatorio.revisado else "Automática"),
    ]
    for row_idx, (label, value) in enumerate(resumo_rows, start=3):
        cell_a = ws_resumo.cell(row=row_idx, column=1, value=label)
        cell_b = ws_resumo.cell(row=row_idx, column=2, value=value)
        cell_a.font = label_font
        cell_a.border = thin
        cell_b.border = thin
        cell_b.alignment = wrap

    ws_resumo.column_dimensions["A"].width = 28
    ws_resumo.column_dimensions["B"].width = 80
    ws_resumo.row_dimensions[6].height = 60

    # Aba de itens
    ws_itens = wb.create_sheet("Itens")
    headers = ["Nº", "Status", "Fonte", "Descrição do item", "Motivo", "Arquivos relacionados"]
    for col, title in enumerate(headers, start=1):
        cell = ws_itens.cell(row=1, column=col, value=title)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center")
        cell.border = thin

    for row_idx, item in enumerate(relatorio.itens, start=2):
        values = [
            item.numero,
            STATUS_LABEL[item.status],
            item.fonte,
            item.descricao,
            item.motivo,
            ", ".join(item.documentos_relacionados),
        ]
        for col, value in enumerate(values, start=1):
            cell = ws_itens.cell(row=row_idx, column=col, value=value)
            cell.border = thin
            cell.alignment = wrap
            if col == 2:
                cell.fill = STATUS_FILL[item.status]
                cell.font = Font(bold=True)
        ws_itens.row_dimensions[row_idx].height = 45

    widths = [6, 14, 10, 50, 50, 35]
    for idx, width in enumerate(widths, start=1):
        ws_itens.column_dimensions[get_column_letter(idx)].width = width
    ws_itens.auto_filter.ref = f"A1:F{max(1, len(relatorio.itens) + 1)}"
    ws_itens.freeze_panes = "A2"

    # Aba de documentos
    ws_docs = wb.create_sheet("Documentos")
    cell = ws_docs.cell(row=1, column=1, value="Arquivo analisado")
    cell.font = header_font
    cell.fill = header_fill
    cell.border = thin
    for row_idx, name in enumerate(relatorio.documentos_analisados, start=2):
        cell = ws_docs.cell(row=row_idx, column=1, value=name)
        cell.border = thin
    ws_docs.column_dimensions["A"].width = 70

    ws_resumo["A12"] = (
        "Relatório assistivo gerado no servidor interno da 12ª SR. "
        "A decisão final permanece com a equipe técnica."
    )
    ws_resumo["A12"].font = Font(italic=True, color="666666", size=9)
    ws_resumo.merge_cells("A12:B12")

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
