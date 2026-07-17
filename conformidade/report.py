"""Geração de relatório em Markdown, Excel, DOCX e PDF."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from conformidade.checklist import label_tipo
from conformidade.models import RelatorioConformidade, StatusConformidade


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

STATUS_RGB = {
    StatusConformidade.ATENDIDO: "006100",
    StatusConformidade.PARCIAL: "9C5700",
    StatusConformidade.NAO_ATENDIDO: "9C0006",
}


def _meta_rows(relatorio: RelatorioConformidade) -> list[tuple[str, str]]:
    counts = relatorio.contagem
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    return [
        ("Data", agora),
        ("Tipo", label_tipo(relatorio.tipo)),
        ("Entidade / município", relatorio.entidade_detectada),
        ("Resumo", relatorio.resumo),
        ("Atendidos", str(counts["atendido"])),
        ("Parciais", str(counts["parcial"])),
        ("Não atendidos", str(counts["nao_atendido"])),
        ("Versão", "Revisada (humano)" if relatorio.revisado else "Automática"),
    ]


def _find_unicode_font() -> str | None:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        str(Path.home() / "miniconda3/fonts/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if Path(path).is_file():
            return path
    return None


def relatorio_para_markdown(relatorio: RelatorioConformidade) -> str:
    lines = [
        "# CODEVASF 12ª SR — Relatório de Conformidade Documental",
        "",
    ]
    for label, value in _meta_rows(relatorio):
        lines.append(f"- **{label}:** {value}")
    lines.extend(["", "## Itens do checklist", ""])
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


def relatorio_para_docx(relatorio: RelatorioConformidade) -> bytes:
    """Gera documento Word (.docx) com resumo e itens coloridos por status."""
    from docx import Document
    from docx.shared import Pt, RGBColor

    doc = Document()
    title = doc.add_heading("CODEVASF 12ª SR — Relatório de Conformidade Documental", level=1)
    for run in title.runs:
        run.font.color.rgb = RGBColor(0x00, 0x66, 0x33)

    for label, value in _meta_rows(relatorio):
        p = doc.add_paragraph()
        run_l = p.add_run(f"{label}: ")
        run_l.bold = True
        p.add_run(value)

    doc.add_heading("Itens do checklist", level=2)
    for item in relatorio.itens:
        heading = doc.add_paragraph()
        run_n = heading.add_run(f"{item.numero}. [{STATUS_LABEL[item.status]}] ")
        run_n.bold = True
        hex_color = STATUS_RGB[item.status]
        run_n.font.color.rgb = RGBColor(
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )
        heading.add_run(f"({item.fonte}) {item.descricao}")

        p_motivo = doc.add_paragraph()
        r = p_motivo.add_run("Motivo: ")
        r.bold = True
        p_motivo.add_run(item.motivo)
        if item.documentos_relacionados:
            p_arq = doc.add_paragraph()
            r2 = p_arq.add_run("Arquivos: ")
            r2.bold = True
            p_arq.add_run(", ".join(item.documentos_relacionados))

    doc.add_heading("Documentos analisados", level=2)
    for name in relatorio.documentos_analisados:
        doc.add_paragraph(name, style="List Bullet")

    footnote = doc.add_paragraph()
    run_f = footnote.add_run(
        "Relatório assistivo gerado na 12ª SR. A decisão final permanece com a equipe técnica."
    )
    run_f.italic = True
    run_f.font.size = Pt(9)

    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def relatorio_para_pdf(relatorio: RelatorioConformidade) -> bytes:
    """Gera PDF com fpdf2 (UTF-8 via fonte DejaVu quando disponível)."""
    from fpdf import FPDF

    class RelatorioPDF(FPDF):
        def footer(self) -> None:
            self.set_y(-15)
            self.set_font(self._body_font, size=8)
            self.set_text_color(100, 100, 100)
            self.cell(
                0,
                8,
                "CODEVASF 12ª SR — relatório assistivo — decisão final da equipe técnica",
                align="C",
            )

    pdf = RelatorioPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    font_path = _find_unicode_font()
    if font_path:
        pdf.add_font("Body", "", font_path)
        # Tenta variante bold; se não houver, reutiliza a regular
        bold_path = font_path.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
        if Path(bold_path).is_file():
            pdf.add_font("Body", "B", bold_path)
        else:
            pdf.add_font("Body", "B", font_path)
        pdf._body_font = "Body"  # type: ignore[attr-defined]
    else:
        pdf._body_font = "Helvetica"  # type: ignore[attr-defined]

    body = pdf._body_font  # type: ignore[attr-defined]
    pdf.add_page()
    pdf.set_font(body, "B", 14)
    pdf.set_text_color(0, 102, 51)
    pdf.multi_cell(0, 8, "CODEVASF 12ª SR — Relatório de Conformidade Documental")
    pdf.ln(2)

    pdf.set_text_color(0, 0, 0)
    for label, value in _meta_rows(relatorio):
        pdf.set_x(pdf.l_margin)
        pdf.set_font(body, "B", 10)
        pdf.multi_cell(0, 5, f"{label}: {value}")
        pdf.ln(0.5)

    pdf.ln(2)
    pdf.set_x(pdf.l_margin)
    pdf.set_font(body, "B", 12)
    pdf.set_text_color(0, 102, 51)
    pdf.multi_cell(0, 8, "Itens do checklist")
    pdf.ln(1)

    for item in relatorio.itens:
        hex_color = STATUS_RGB[item.status]
        r, g, b = (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )
        pdf.set_x(pdf.l_margin)
        pdf.set_font(body, "B", 10)
        pdf.set_text_color(r, g, b)
        pdf.multi_cell(
            0,
            5,
            f"{item.numero}. [{STATUS_LABEL[item.status]}] ({item.fonte})",
        )
        pdf.set_text_color(0, 0, 0)
        pdf.set_font(body, "", 10)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 5, item.descricao)
        pdf.set_x(pdf.l_margin)
        pdf.set_font(body, "", 9)
        pdf.multi_cell(0, 5, f"Motivo: {item.motivo}")
        if item.documentos_relacionados:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 5, "Arquivos: " + ", ".join(item.documentos_relacionados))
        pdf.ln(2)

    pdf.set_x(pdf.l_margin)
    pdf.set_font(body, "B", 12)
    pdf.set_text_color(0, 102, 51)
    pdf.multi_cell(0, 8, "Documentos analisados")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(body, "", 10)
    for name in relatorio.documentos_analisados:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 5, f"- {name}")

    return bytes(pdf.output())
