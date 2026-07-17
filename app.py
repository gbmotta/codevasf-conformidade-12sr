#!/usr/bin/env python3
"""
Interface Gradio — Análise de Conformidade Documental (Codevasf 12ª SR).

Uso principal:
  - Hugging Face Spaces (Gradio + ZeroGPU)
  - Execução local: ``python app.py`` → http://localhost:7860

Fluxo da UI:
  1. Usuário escolhe tipo (Prefeitura / Associação) e envia ZIP
  2. Regras determinísticas + LLM avaliam a Lista de Documentos
  3. Ajuste humano opcional e download (Texto / Excel / Word / PDF)

Backends de IA (env ``LLM_BACKEND``):
  - ``ollama``   — intranet / local
  - ``zerogpu``  — Space HF (padrão no Space)
  - ``hf``       — Inference Providers (créditos)
  - ``auto``     — Ollama se disponível; senão HF/ZeroGPU

Tema visual: ``app/styles.py`` (Manual de Identidade Visual Codevasf).
"""

from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path

import gradio as gr

try:
    import spaces
except ImportError:  # ambiente local sem pacote spaces (HF Spaces traz o real)
    class spaces:  # type: ignore[no-redef]
        @staticmethod
        def GPU(duration=None, **_kwargs):
            def decorator(fn):
                return fn

            return decorator

from app.styles import (
    GRADIO_CSS,
    gradio_theme,
    render_hero,
    render_side_left,
    render_side_right,
    render_steps,
)
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

# Badges HTML alinhados à paleta institucional (verde / amarelo / vermelho)
STATUS_BADGE = {
    StatusConformidade.ATENDIDO: (
        '<span class="cv-badge cv-badge-ok" style="display:inline-block;padding:0.2rem 0.55rem;'
        'border-radius:999px;background:#d9f2e3;color:#0b6b3a;font-weight:700;'
        'font-size:0.78rem;">ATENDIDO</span>'
    ),
    StatusConformidade.PARCIAL: (
        '<span class="cv-badge cv-badge-parcial" style="display:inline-block;padding:0.2rem 0.55rem;'
        'border-radius:999px;background:#fff1d6;color:#8a5a00;font-weight:700;'
        'font-size:0.78rem;">PARCIAL</span>'
    ),
    StatusConformidade.NAO_ATENDIDO: (
        '<span class="cv-badge cv-badge-nao" style="display:inline-block;padding:0.2rem 0.55rem;'
        'border-radius:999px;background:#fde2e2;color:#9b1c1c;font-weight:700;'
        'font-size:0.78rem;">NÃO ATENDIDO</span>'
    ),
}

STATUS_CHOICES = ["atendido", "parcial", "nao_atendido"]


def _system_status() -> str:
    """Resumo de saúde do LLM e do OCR para o acordeão da UI."""
    settings = load_settings()
    backend = resolve_backend(settings)
    ok, msg = check_llm_health(settings)
    ocr_ok, ocr_msg = ocr_available()
    model = (
        settings.zerogpu_model
        if backend == "zerogpu"
        else settings.hf_model
        if backend == "hf"
        else settings.ollama_chat_model
    )
    return (
        f"**LLM:** `{backend}` — {'OK' if ok else 'FALHA'} ({msg})\n\n"
        f"**OCR:** {'OK' if ocr_ok else 'FALHA'} ({ocr_msg})\n\n"
        f"**Modelo:** `{model}`"
    )


def _estimate_zerogpu_duration(_settings, _checklist, documents) -> int:
    """Estima duração da reserva ZeroGPU (menor = melhor fila/cota)."""
    n = len(documents) if documents else 1
    return 60 if n <= 25 else 90


@spaces.GPU(duration=_estimate_zerogpu_duration)
def _analisar_com_zerogpu(settings, checklist, documents):
    """Roda a análise inteira em uma única entrada GPU (Space HF)."""
    return analisar_conformidade(
        settings, checklist, documents, batch_size=10, on_progress=None
    )


def _format_relatorio_md(relatorio: RelatorioConformidade) -> str:
    """Monta o Markdown exibido na área de resultado (com badges HTML)."""
    counts = relatorio.contagem
    versao = "revisada" if relatorio.revisado else "automática"
    lines = [
        f"## Resultado — {label_tipo(relatorio.tipo)} ({versao})",
        f"**Entidade:** {relatorio.entidade_detectada}",
        "",
        relatorio.resumo,
        "",
        (
            f'- <span style="color:#0b6b3a;font-weight:700;">Atendidos: {counts["atendido"]}</span> · '
            f'<span style="color:#8a5a00;font-weight:700;">Parciais: {counts["parcial"]}</span> · '
            f'<span style="color:#9b1c1c;font-weight:700;">Não atendidos: {counts["nao_atendido"]}</span>'
        ),
        "",
        "---",
        "",
    ]
    for item in relatorio.itens:
        badge = STATUS_BADGE[item.status]
        lines.append(
            f"### {item.numero}. {badge} "
            f"<small style='color:#5a7264'>({item.fonte})</small> {item.descricao}"
        )
        lines.append(f"**Motivo:** {item.motivo}")
        if item.documentos_relacionados:
            lines.append("**Arquivos:** " + ", ".join(item.documentos_relacionados))
        lines.append("")
    return "\n".join(lines)


def _relatorio_to_editor_rows(relatorio: RelatorioConformidade) -> list[list]:
    """Converte o relatório em linhas editáveis do Dataframe de revisão."""
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
    """Gera os quatro arquivos de exportação e devolve os caminhos."""
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
    """Callback principal: ZIP → análise → relatório + arquivos para download."""
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
        backend = resolve_backend(settings)
        if backend == "zerogpu":
            progress(
                0.25,
                desc="IA no ZeroGPU (1ª execução pode baixar o modelo; ~1 min)...",
            )
            relatorio = _analisar_com_zerogpu(settings, checklist, documents)
        else:
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
    """Aplica overrides humanos da tabela e regenera os exports."""
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


def _gradio_major() -> int:
    """Major version do Gradio (5: theme no Blocks; 6+: theme no launch)."""
    return int(gr.__version__.split(".", 1)[0])


def build_ui() -> gr.Blocks:
    """Monta o layout: laterais institucionais + área central de análise."""
    hero_html = render_hero(
        "Compare o requerimento (ZIP) com a Lista de Documentos para doação de bens "
        "móveis — Prefeituras ou Associações — com regras automáticas + IA."
    )
    blocks_kwargs: dict = {"title": "Codevasf 12ª SR — Conformidade Documental"}
    if _gradio_major() < 6:
        blocks_kwargs["theme"] = gradio_theme()
        blocks_kwargs["css"] = GRADIO_CSS

    with gr.Blocks(**blocks_kwargs) as demo:
        state = gr.State(None)

        with gr.Row(elem_classes=["cv-layout"]):
            with gr.Column(scale=2, min_width=260, elem_classes=["cv-side"]):
                gr.HTML(render_side_left())

            with gr.Column(scale=5, elem_classes=["cv-main"]):
                gr.HTML(hero_html)
                gr.HTML(render_steps())

                with gr.Accordion("Status do sistema", open=False):
                    status = gr.Markdown(_system_status())
                    gr.Button("Atualizar status", size="sm").click(
                        fn=_system_status, outputs=status
                    )

                with gr.Row():
                    tipo = gr.Radio(
                        choices=[
                            "Prefeitura",
                            "Associação / Cooperativa / Instituição pública",
                        ],
                        value="Prefeitura",
                        label="Tipo de solicitante",
                    )
                    zip_in = gr.File(
                        label="ZIP com a documentação", file_types=[".zip"]
                    )

                btn = gr.Button("Analisar conformidade", variant="primary")

                resultado = gr.Markdown()
                inventario = gr.Textbox(label="Inventário dos arquivos", lines=5)

                gr.Markdown("### Ajuste humano (opcional)")
                editor = gr.Dataframe(
                    headers=["Nº", "Status", "Fonte", "Descrição", "Motivo", "Arquivos"],
                    datatype=["number", "str", "str", "str", "str", "str"],
                    col_count=(6, "fixed"),
                    interactive=True,
                    label="Edite Status (atendido | parcial | nao_atendido) e/ou Motivo",
                    wrap=True,
                )
                btn_revisar = gr.Button("Aplicar revisão e gerar relatório revisado")

                with gr.Row(elem_classes=["cv-downloads"]):
                    md_out = gr.File(label="Texto (.md)", elem_classes=["cv-download"])
                    xlsx_out = gr.File(
                        label="Excel (.xlsx)", elem_classes=["cv-download"]
                    )
                    docx_out = gr.File(
                        label="Word (.docx)", elem_classes=["cv-download"]
                    )
                    pdf_out = gr.File(label="PDF (.pdf)", elem_classes=["cv-download"])

                gr.HTML(
                    '<p class="cv-footer-note">Codevasf — 12ª Superintendência Regional '
                    "(Natal/RN) · Regras automáticas + IA · Ajuste humano opcional · "
                    "Identidade visual conforme manual institucional</p>"
                )

            with gr.Column(scale=2, min_width=260, elem_classes=["cv-side"]):
                gr.HTML(render_side_right())

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
    return demo


# Objeto esperado pelo runtime Gradio do Hugging Face Spaces
demo = build_ui()


def _launch_kwargs() -> dict:
    if _gradio_major() >= 6:
        return {"theme": gradio_theme(), "css": GRADIO_CSS}
    return {}


if __name__ == "__main__":
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=7860,
        **_launch_kwargs(),
    )
