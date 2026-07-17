"""Interface Gradio para Hugging Face Spaces — Conformidade Documental CODEVASF 12ª SR."""

from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path

import gradio as gr
import spaces

from conformidade.analyzer import analisar_conformidade
from conformidade.checklist import TipoEntidade, label_tipo, load_checklist
from conformidade.config import load_settings
from conformidade.llm import OllamaError, check_llm_health, resolve_backend
from conformidade.loaders import load_from_zip, ocr_available, scan_folder
from conformidade.models import (
    RelatorioConformidade,
    StatusConformidade,
    aplicar_revisao_humana,
)
from conformidade.report import (
    relatorio_para_docx,
    relatorio_para_markdown,
    relatorio_para_pdf,
    relatorio_para_xlsx,
)

STATUS_BADGE = {
    StatusConformidade.ATENDIDO: (
        '<span style="display:inline-block;padding:2px 10px;border-radius:999px;'
        'background:#c6efce;color:#006100;font-weight:700;font-size:0.85em;">ATENDIDO</span>'
    ),
    StatusConformidade.PARCIAL: (
        '<span style="display:inline-block;padding:2px 10px;border-radius:999px;'
        'background:#ffeb9c;color:#9c5700;font-weight:700;font-size:0.85em;">PARCIAL</span>'
    ),
    StatusConformidade.NAO_ATENDIDO: (
        '<span style="display:inline-block;padding:2px 10px;border-radius:999px;'
        'background:#ffc7ce;color:#9c0006;font-weight:700;font-size:0.85em;">NÃO ATENDIDO</span>'
    ),
}

STATUS_CHOICES = ["atendido", "parcial", "nao_atendido"]


def _system_status() -> str:
    settings = load_settings()
    backend = resolve_backend(settings)
    ok, msg = check_llm_health(settings)
    ocr_ok, ocr_msg = ocr_available()
    return (
        f"**LLM:** `{backend}` — {'OK' if ok else 'FALHA'} ({msg})\n\n"
        f"**OCR:** {'OK' if ocr_ok else 'FALHA'} ({ocr_msg})\n\n"
        f"**Modelo HF:** `{settings.hf_model}`"
    )


@spaces.GPU(duration=60)
def _zerogpu_ping() -> str:
    return "ok"


def _format_relatorio_md(relatorio: RelatorioConformidade) -> str:
    counts = relatorio.contagem
    versao = "revisada" if relatorio.revisado else "automática"
    lines = [
        f"## Resultado — {label_tipo(relatorio.tipo)} ({versao})",
        f"**Entidade:** {relatorio.entidade_detectada}",
        "",
        relatorio.resumo,
        "",
        (
            f'- <span style="color:#006100;font-weight:700;">Atendidos: {counts["atendido"]}</span> · '
            f'<span style="color:#9c5700;font-weight:700;">Parciais: {counts["parcial"]}</span> · '
            f'<span style="color:#9c0006;font-weight:700;">Não atendidos: {counts["nao_atendido"]}</span>'
        ),
        "",
        "---",
        "",
    ]
    for item in relatorio.itens:
        badge = STATUS_BADGE[item.status]
        lines.append(
            f"### {item.numero}. {badge} "
            f"<small style='color:#666'>({item.fonte})</small> {item.descricao}"
        )
        lines.append(f"**Motivo:** {item.motivo}")
        if item.documentos_relacionados:
            lines.append("**Arquivos:** " + ", ".join(item.documentos_relacionados))
        lines.append("")
    return "\n".join(lines)


def _relatorio_to_editor_rows(relatorio: RelatorioConformidade) -> list[list]:
    rows = []
    for item in relatorio.itens:
        rows.append(
            [
                item.numero,
                item.status.value,
                item.fonte,
                item.descricao[:120] + ("…" if len(item.descricao) > 120 else ""),
                item.motivo,
                ", ".join(item.documentos_relacionados),
            ]
        )
    return rows


def _export_files(
    relatorio: RelatorioConformidade, work: Path | None = None
) -> tuple[str, str, str, str]:
    out_dir = (work or Path(tempfile.mkdtemp(prefix="conf_out_"))) / "saida"
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "_revisado" if relatorio.revisado else ""
    md_path = out_dir / f"relatorio_conformidade{suffix}.md"
    xlsx_path = out_dir / f"relatorio_conformidade{suffix}.xlsx"
    docx_path = out_dir / f"relatorio_conformidade{suffix}.docx"
    pdf_path = out_dir / f"relatorio_conformidade{suffix}.pdf"
    md_path.write_text(relatorio_para_markdown(relatorio), encoding="utf-8")
    xlsx_path.write_bytes(relatorio_para_xlsx(relatorio))
    docx_path.write_bytes(relatorio_para_docx(relatorio))
    pdf_path.write_bytes(relatorio_para_pdf(relatorio))
    return str(md_path), str(xlsx_path), str(docx_path), str(pdf_path)


def analisar(tipo_label: str, zip_file, progress=gr.Progress(track_tqdm=False)):
    if zip_file is None:
        raise gr.Error("Envie um arquivo ZIP com a documentação.")

    settings = load_settings()
    healthy, llm_msg = check_llm_health(settings)
    if not healthy:
        raise gr.Error(f"IA indisponível: {llm_msg}")

    tipo = (
        TipoEntidade.PREFEITURA
        if tipo_label.startswith("Prefeitura")
        else TipoEntidade.ASSOCIACAO
    )
    checklist = load_checklist(settings.checklists_path, tipo)
    work = Path(tempfile.mkdtemp(prefix="conformidade_"))

    zip_path = Path(zip_file) if isinstance(zip_file, str) else Path(zip_file.name)
    local_zip = work / (zip_path.name or f"upload_{uuid.uuid4().hex}.zip")
    shutil.copy2(zip_path, local_zip)

    progress(0.08, desc="Extraindo e lendo documentos (OCR se necessário)...")
    documents = load_from_zip(local_zip, work / "extraidos")
    if not documents:
        documents = scan_folder(work)
    if not documents:
        raise gr.Error("Nenhum documento legível encontrado no ZIP.")

    def on_progress(msg: str) -> None:
        progress(0.2, desc=msg)

    try:
        relatorio = analisar_conformidade(
            settings, checklist, documents, on_progress=on_progress
        )
    except (OllamaError, ValueError) as exc:
        raise gr.Error(str(exc)) from exc

    inventory = "\n".join(
        f"- {d.relative_path} ({d.extraction_method}, {len(d.content)} chars)"
        for d in documents
    )
    md_path, xlsx_path, docx_path, pdf_path = _export_files(relatorio, work)
    progress(1.0, desc="Concluído — ajuste os status abaixo se necessário")
    return (
        _format_relatorio_md(relatorio),
        inventory,
        _relatorio_to_editor_rows(relatorio),
        relatorio.to_dict(),
        md_path,
        xlsx_path,
        docx_path,
        pdf_path,
    )


def aplicar_revisao(editor_rows, state_dict):
    if not state_dict:
        raise gr.Error("Execute a análise antes de revisar.")
    if not editor_rows:
        raise gr.Error("Tabela de revisão vazia.")

    relatorio = RelatorioConformidade.from_dict(state_dict)
    overrides = []
    for row in editor_rows:
        if not row or len(row) < 5:
            continue
        overrides.append(
            {
                "numero": row[0],
                "status": row[1],
                "motivo": row[4],
            }
        )
    revisado = aplicar_revisao_humana(relatorio, overrides)
    md_path, xlsx_path, docx_path, pdf_path = _export_files(revisado)
    return (
        _format_relatorio_md(revisado),
        _relatorio_to_editor_rows(revisado),
        revisado.to_dict(),
        md_path,
        xlsx_path,
        docx_path,
        pdf_path,
    )


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="CODEVASF 12ª SR — Conformidade Documental") as demo:
        state = gr.State(None)
        gr.Markdown(
            """
# CODEVASF 12ª SR — Análise de Conformidade Documental
1. Envie o ZIP · 2. Analise (regras + IA) · 3. Ajuste status se precisar · 4. Baixe o relatório
"""
        )
        with gr.Accordion("Status do sistema", open=False):
            status = gr.Markdown(_system_status())
            gr.Button("Atualizar status").click(fn=_system_status, outputs=status)

        tipo = gr.Radio(
            choices=[
                "Prefeitura",
                "Associação / Cooperativa / Instituição pública",
            ],
            value="Prefeitura",
            label="Tipo de solicitante",
        )
        zip_in = gr.File(label="ZIP com a documentação", file_types=[".zip"])
        btn = gr.Button("Analisar conformidade", variant="primary")

        resultado = gr.Markdown()
        inventario = gr.Textbox(label="Inventário dos arquivos", lines=6)

        gr.Markdown("### Ajuste humano (opcional)")
        editor = gr.Dataframe(
            headers=["Nº", "Status", "Fonte", "Descrição", "Motivo", "Arquivos"],
            datatype=["number", "str", "str", "str", "str", "str"],
            col_count=(6, "fixed"),
            interactive=True,
            label="Edite a coluna Status (atendido | parcial | nao_atendido) e/ou Motivo",
            wrap=True,
        )
        btn_revisar = gr.Button("Aplicar revisão e gerar relatório revisado")

        with gr.Row():
            md_out = gr.File(label="Relatório .md")
            xlsx_out = gr.File(label="Relatório .xlsx")
            docx_out = gr.File(label="Relatório .docx")
            pdf_out = gr.File(label="Relatório .pdf")

        btn.click(
            fn=analisar,
            inputs=[tipo, zip_in],
            outputs=[
                resultado,
                inventario,
                editor,
                state,
                md_out,
                xlsx_out,
                docx_out,
                pdf_out,
            ],
        )
        btn_revisar.click(
            fn=aplicar_revisao,
            inputs=[editor, state],
            outputs=[resultado, editor, state, md_out, xlsx_out, docx_out, pdf_out],
        )
        gr.Markdown(
            "CODEVASF — 12ª Superintendência Regional (Natal/RN) · "
            "Regras automáticas + IA · Ajuste humano opcional"
        )
    return demo


demo = build_ui()

if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=7860)
