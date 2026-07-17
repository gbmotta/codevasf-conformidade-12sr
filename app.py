#!/usr/bin/env python3
"""
Interface Gradio — Análise de Conformidade Documental (Codevasf 12ª SR).

Uso principal:
  - Hugging Face Spaces (Gradio + ZeroGPU)
  - Execução local: ``python app.py`` → http://localhost:7860

Melhorias de UX:
  - Fluxo pós-análise (oculta envio, destaca resultado)
  - Cards de resumo + progresso por etapas
  - Revisão com dropdown de status
  - Inventário HTML
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
    render_steps,
)
from conformidade.analyzer import analisar_conformidade
from conformidade.checklist import TipoEntidade, label_tipo, load_checklist
from conformidade.config import load_settings
from conformidade.llm import OllamaError, check_llm_health, resolve_backend
from conformidade.loaders import LoadedDocument, load_from_zip, ocr_available, scan_folder
from dataclasses import replace

from conformidade.models import (
    RelatorioConformidade,
    StatusConformidade,
    aplicar_revisao_humana,
    normalize_status,
)
from conformidade.report import (
    relatorio_para_docx,
    relatorio_para_markdown,
    relatorio_para_pdf,
    relatorio_para_xlsx,
)

STATUS_BADGE = {
    StatusConformidade.ATENDIDO: (
        '<span class="cv-badge cv-badge-ok">ATENDIDO</span>'
    ),
    StatusConformidade.PARCIAL: (
        '<span class="cv-badge cv-badge-parcial">PARCIAL</span>'
    ),
    StatusConformidade.NAO_ATENDIDO: (
        '<span class="cv-badge cv-badge-nao">NÃO ATENDIDO</span>'
    ),
}

STATUS_CHOICES = ["Atendido", "Parcial", "Não atendido"]

STATUS_DISPLAY = {
    StatusConformidade.ATENDIDO: "Atendido",
    StatusConformidade.PARCIAL: "Parcial",
    StatusConformidade.NAO_ATENDIDO: "Não atendido",
}


def _status_label(status: StatusConformidade | str) -> str:
    if isinstance(status, StatusConformidade):
        return STATUS_DISPLAY[status]
    try:
        return STATUS_DISPLAY[StatusConformidade(str(status))]
    except ValueError:
        return STATUS_DISPLAY[normalize_status(str(status))]


def _capitalize_sentence(text: str | None) -> str:
    """Garante inicial maiúscula em textos da revisão humana."""
    value = (text or "").strip()
    if not value:
        return ""
    return value[0].upper() + value[1:]


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
    n = len(documents) if documents else 1
    return 60 if n <= 25 else 90


@spaces.GPU(duration=_estimate_zerogpu_duration)
def _analisar_com_zerogpu(settings, checklist, documents):
    return analisar_conformidade(
        settings, checklist, documents, batch_size=10, on_progress=None
    )


def _progress_html(step: int) -> str:
    """Barra de etapas: 1 extração · 2 regras · 3 IA · 4 relatório."""
    labels = [
        (1, "Extração"),
        (2, "Regras"),
        (3, "IA"),
        (4, "Relatório"),
    ]
    parts = ['<div class="cv-progress" aria-label="Progresso da análise">']
    for num, label in labels:
        cls = "done" if num < step else ("active" if num == step else "todo")
        parts.append(
            f'<div class="cv-progress-step {cls}">'
            f'<span class="cv-progress-num">{num}</span>{label}</div>'
        )
        if num < 4:
            parts.append('<div class="cv-progress-sep"></div>')
    parts.append("</div>")
    return "".join(parts)


def _resumo_cards_html(relatorio: RelatorioConformidade) -> str:
    counts = relatorio.contagem
    versao = "revisada" if relatorio.revisado else "automática"
    return f"""
<div class="cv-resumo">
  <div class="cv-resumo-head">
    <strong>{label_tipo(relatorio.tipo)}</strong>
    <span>{relatorio.entidade_detectada} · análise {versao}</span>
  </div>
  <div class="cv-cards">
    <div class="cv-card-stat ok">
      <span class="cv-card-num">{counts["atendido"]}</span>
      <span class="cv-card-label">Atendidos</span>
    </div>
    <div class="cv-card-stat parcial">
      <span class="cv-card-num">{counts["parcial"]}</span>
      <span class="cv-card-label">Parciais</span>
    </div>
    <div class="cv-card-stat nao">
      <span class="cv-card-num">{counts["nao_atendido"]}</span>
      <span class="cv-card-label">Não atendidos</span>
    </div>
  </div>
</div>
"""


def _format_relatorio_md(relatorio: RelatorioConformidade) -> str:
    lines = [
        f"## Detalhamento dos itens",
        "",
        relatorio.resumo,
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


def _inventario_html(documents: list[LoadedDocument]) -> str:
    if not documents:
        return '<p class="cv-muted">Nenhum arquivo no inventário.</p>'
    rows = ['<div class="cv-inventory"><h3>Inventário dos arquivos</h3><ul>']
    for doc in documents:
        ext = Path(doc.file_name).suffix.lower() or "?"
        method = (doc.extraction_method or "texto").lower()
        ocr = method in {"ocr", "hibrido"}
        badge = (
            '<span class="cv-inv-badge ocr">OCR</span>'
            if ocr
            else '<span class="cv-inv-badge">Texto</span>'
        )
        kind = {
            ".pdf": "PDF",
            ".docx": "Word",
            ".doc": "Word",
            ".png": "Img",
            ".jpg": "Img",
            ".jpeg": "Img",
            ".tif": "Img",
            ".tiff": "Img",
        }.get(ext, ext.replace(".", "").upper() or "Arq")
        chars = f"{len(doc.content):,}".replace(",", ".")
        rows.append(
            "<li>"
            f'<span class="cv-inv-kind">{kind}</span>'
            f'<span class="cv-inv-name">{doc.relative_path}</span>'
            f"{badge}"
            f'<span class="cv-inv-meta">{chars} caracteres</span>'
            "</li>"
        )
    rows.append("</ul></div>")
    return "".join(rows)


def _item_choices(relatorio: RelatorioConformidade) -> list[str]:
    return [
        f"{item.numero} — {item.descricao[:70]}"
        + ("…" if len(item.descricao) > 70 else "")
        for item in relatorio.itens
    ]


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


def _empty_analysis_outputs():
    return (
        "",  # progresso
        "",  # cards
        "",  # resultado
        "",  # inventario
        None,  # state
        None,
        None,
        None,
        None,  # files
        gr.update(visible=True),  # painel envio
        gr.update(visible=False),  # painel resultado
        gr.update(choices=[], value=None),  # item select
        gr.update(value="Atendido"),
        gr.update(value=""),
    )


def analisar(tipo_label: str, zip_file):
    """ZIP → análise (gerador com progresso por etapas)."""
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

    # Etapa 1 — Extração
    yield (
        _progress_html(1),
        "",
        "Extraindo e lendo documentos (OCR se necessário)...",
        "",
        None,
        None,
        None,
        None,
        None,
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(),
        gr.update(),
        gr.update(),
    )

    documents = load_from_zip(local_zip, work / "extraidos")
    if not documents:
        documents = scan_folder(work)
    if not documents:
        raise gr.Error("Nenhum documento legível encontrado no ZIP.")

    # Etapa 2 — Regras
    yield (
        _progress_html(2),
        "",
        "Aplicando regras determinísticas (nome/conteúdo)...",
        _inventario_html(documents),
        None,
        None,
        None,
        None,
        None,
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(),
        gr.update(),
        gr.update(),
    )

    # Etapa 3 — IA
    yield (
        _progress_html(3),
        "",
        "Avaliando itens pendentes com IA...",
        _inventario_html(documents),
        None,
        None,
        None,
        None,
        None,
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(),
        gr.update(),
        gr.update(),
    )

    try:
        backend = resolve_backend(settings)
        if backend == "zerogpu":
            relatorio = _analisar_com_zerogpu(settings, checklist, documents)
        else:
            relatorio = analisar_conformidade(settings, checklist, documents)
    except (OllamaError, ValueError) as exc:
        raise gr.Error(str(exc)) from exc

    md_path, xlsx_path, docx_path, pdf_path = _export_files(relatorio, work)
    choices = _item_choices(relatorio)
    first = choices[0] if choices else None
    first_item = relatorio.itens[0] if relatorio.itens else None

    # Etapa 4 — Relatório + troca de painel
    yield (
        _progress_html(4),
        _resumo_cards_html(relatorio),
        _format_relatorio_md(relatorio),
        _inventario_html(documents),
        relatorio.to_dict(),
        md_path,
        xlsx_path,
        docx_path,
        pdf_path,
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(choices=choices, value=first),
        gr.update(
            value=_status_label(first_item.status)
            if first_item
            else "Atendido"
        ),
        gr.update(
            value=_capitalize_sentence(first_item.motivo)
            if first_item
            else ""
        ),
    )


def _parse_item_numero(label: str | None) -> int | None:
    if not label:
        return None
    head = str(label).split("—", 1)[0].strip()
    try:
        return int(head)
    except ValueError:
        return None


def carregar_item_revisao(item_label: str, state_dict):
    """Preenche dropdown/motivo ao trocar o item selecionado."""
    if not state_dict or not item_label:
        return gr.update(), gr.update()
    relatorio = RelatorioConformidade.from_dict(state_dict)
    numero = _parse_item_numero(item_label)
    for item in relatorio.itens:
        if item.numero == numero:
            return (
                _status_label(item.status),
                _capitalize_sentence(item.motivo),
            )
    return gr.update(), gr.update()


def salvar_item_revisao(item_label: str, status: str, motivo: str, state_dict):
    """Atualiza um item no estado via dropdowns."""
    if not state_dict:
        raise gr.Error("Execute a análise antes de revisar.")
    numero = _parse_item_numero(item_label)
    if numero is None:
        raise gr.Error("Selecione um item da lista.")
    relatorio = RelatorioConformidade.from_dict(state_dict)
    revisado = aplicar_revisao_humana(
        relatorio,
        [
            {
                "numero": numero,
                "status": status,
                "motivo": _capitalize_sentence(motivo),
            }
        ],
    )
    return (
        revisado.to_dict(),
        _resumo_cards_html(revisado),
        _format_relatorio_md(revisado),
        gr.update(choices=_item_choices(revisado), value=item_label),
    )


def gerar_relatorio_revisado(state_dict):
    """Gera exports a partir do estado já revisado."""
    if not state_dict:
        raise gr.Error("Execute a análise antes de revisar.")
    relatorio = RelatorioConformidade.from_dict(state_dict)
    if not relatorio.revisado:
        relatorio = replace(relatorio, revisado=True)
    md_path, xlsx_path, docx_path, pdf_path = _export_files(relatorio)
    return (
        _resumo_cards_html(relatorio),
        _format_relatorio_md(relatorio),
        relatorio.to_dict(),
        md_path,
        xlsx_path,
        docx_path,
        pdf_path,
    )


def nova_analise():
    """Volta ao formulário de envio."""
    return _empty_analysis_outputs()


def _gradio_major() -> int:
    return int(gr.__version__.split(".", 1)[0])


def build_ui() -> gr.Blocks:
    """Monta a interface institucional em coluna única."""

    hero_html = render_hero(
        "Verificação assistida dos documentos exigidos para doação "
        "e concessão de bens móveis."
    )

    blocks_kwargs: dict = {
        "title": "Codevasf 12ª SR — Conformidade Documental"
    }

    if _gradio_major() < 6:
        blocks_kwargs["theme"] = gradio_theme()
        blocks_kwargs["css"] = GRADIO_CSS

    with gr.Blocks(**blocks_kwargs) as demo:
        state = gr.State(None)

        # =========================================================
        # CONTEÚDO PRINCIPAL
        # =========================================================

        with gr.Column(elem_classes=["cv-main"]):
            gr.HTML(hero_html)
            gr.HTML(render_steps())

            # -----------------------------------------------------
            # AJUDA
            # -----------------------------------------------------

            with gr.Accordion(
                "Orientações de uso",
                open=False,
                elem_classes=["cv-help-accordion"],
            ):
                gr.HTML(
                    """
                    <div class="cv-help-content">
                      <section class="cv-help-card">
                        <span class="cv-help-number">1</span>
                        <div>
                          <strong>Prepare os documentos</strong>
                          <p>
                            Reúna os documentos do requerimento em um único
                            arquivo ZIP.
                          </p>
                        </div>
                      </section>

                      <section class="cv-help-card">
                        <span class="cv-help-number">2</span>
                        <div>
                          <strong>Nomeie os arquivos claramente</strong>
                          <p>
                            Utilize nomes como oficio.pdf, ata_posse.pdf,
                            cnpj.pdf e certidao_fgts.pdf.
                          </p>
                        </div>
                      </section>

                      <section class="cv-help-card">
                        <span class="cv-help-number">3</span>
                        <div>
                          <strong>Revise o resultado</strong>
                          <p>
                            A ferramenta auxilia a análise, mas a decisão
                            permanece com a equipe técnica.
                          </p>
                        </div>
                      </section>
                    </div>

                    <div class="cv-help-note">
                      <strong>O ZIP pode conter:</strong>
                      ofício ou requerimento, documentos institucionais,
                      documentos pessoais, certidões, comprovantes e anexos.
                    </div>
                    """
                )

            # -----------------------------------------------------
            # STATUS TÉCNICO
            # -----------------------------------------------------

            with gr.Accordion(
                "Status técnico do sistema",
                open=False,
                elem_classes=["cv-system-accordion"],
            ):
                status = gr.Markdown(_system_status())

                btn_status = gr.Button(
                    "Atualizar status",
                    size="sm",
                    elem_classes=["cv-btn-status"],
                )

                btn_status.click(
                    fn=_system_status,
                    outputs=status,
                )

            # Progresso dinâmico apresentado durante a análise
            progresso = gr.HTML(
                visible=True,
                elem_classes=["cv-progress-wrap"],
            )

            # =====================================================
            # PAINEL DE ENVIO
            # =====================================================

            with gr.Column(
                visible=True,
                elem_classes=["cv-painel-envio"],
            ) as painel_envio:

                gr.HTML(
                    """
                    <div class="cv-section-title">
                      <h2>Enviar documentação</h2>
                      <p>
                        Selecione o tipo de solicitante e anexe o arquivo ZIP
                        correspondente ao requerimento.
                      </p>
                    </div>
                    """
                )

                with gr.Row(
                    elem_classes=["cv-input-row"],
                    equal_height=True,
                ):
                    with gr.Column(
                        scale=1,
                        elem_classes=["cv-input-card"],
                    ):
                        tipo = gr.Radio(
                            choices=[
                                "Prefeitura",
                                (
                                    "Associação / Cooperativa / "
                                    "Instituição pública"
                                ),
                            ],
                            value="Prefeitura",
                            label="Tipo de solicitante",
                            elem_classes=["cv-tipo-radio"],
                        )

                    with gr.Column(
                        scale=1,
                        elem_classes=["cv-input-card"],
                    ):
                        zip_in = gr.File(
                            label="ZIP com a documentação",
                            file_types=[".zip"],
                            elem_classes=["cv-zip-upload"],
                            height=180,
                        )

                gr.HTML(
                    """
                    <div class="cv-upload-guidance">
                      <strong>Antes de iniciar:</strong>
                      confirme se o ZIP pertence ao solicitante selecionado e
                      se os arquivos podem ser abertos normalmente.
                    </div>
                    """
                )

                btn = gr.Button(
                    "Analisar conformidade",
                    variant="primary",
                    elem_classes=["cv-btn-analisar"],
                )

            # =====================================================
            # PAINEL DE RESULTADO
            # =====================================================

            with gr.Column(
                visible=False,
                elem_classes=["cv-painel-resultado"],
            ) as painel_resultado:

                with gr.Row(
                    elem_classes=["cv-result-toolbar"],
                ):
                    btn_nova = gr.Button(
                        "← Nova análise",
                        elem_classes=["cv-btn-nova"],
                    )

                    gr.HTML(
                        """
                        <div class="cv-result-toolbar-copy">
                          <strong>Resultado da análise</strong>
                          <span>
                            Confira prioritariamente os itens parciais e
                            não atendidos.
                          </span>
                        </div>
                        """
                    )

                resumo_cards = gr.HTML()

                # -------------------------------------------------
                # DETALHAMENTO
                # -------------------------------------------------

                resultado = gr.Markdown(
                    elem_classes=["cv-resultado"],
                )

                # -------------------------------------------------
                # INVENTÁRIO
                # -------------------------------------------------

                with gr.Accordion(
                    "Documentos analisados",
                    open=False,
                    elem_classes=["cv-inventory-accordion"],
                ):
                    inventario = gr.HTML()

                # -------------------------------------------------
                # REVISÃO HUMANA
                # -------------------------------------------------

                with gr.Accordion(
                    "Revisão humana",
                    open=True,
                    elem_classes=["cv-review-accordion"],
                ):
                    gr.HTML(
                        """
                        <div class="cv-review-intro">
                          <strong>Conferência da equipe técnica</strong>
                          <p>
                            Selecione um item, altere sua classificação quando
                            necessário e registre uma justificativa objetiva.
                          </p>
                        </div>
                        """
                    )

                    item_select = gr.Dropdown(
                        choices=[],
                        label="Item do checklist",
                        elem_classes=["cv-rev-item"],
                    )

                    with gr.Row(
                        elem_classes=["cv-review-fields"],
                    ):
                        status_dd = gr.Dropdown(
                            choices=STATUS_CHOICES,
                            value="Atendido",
                            label="Status",
                            scale=1,
                            elem_classes=["cv-rev-status"],
                        )

                        motivo_tb = gr.Textbox(
                            label="Justificativa da classificação",
                            lines=3,
                            scale=3,
                            placeholder=(
                                "Explicação objetiva da classificação."
                            ),
                        )

                    with gr.Row(
                        elem_classes=["cv-review-actions"],
                    ):
                        btn_salvar_item = gr.Button(
                            "Salvar alteração do item",
                            elem_classes=["cv-btn-save-review"],
                        )

                        btn_revisar = gr.Button(
                            "Atualizar relatório revisado",
                            variant="primary",
                            elem_classes=["cv-btn-generate-review"],
                        )

                # -------------------------------------------------
                # EXPORTAÇÃO
                # -------------------------------------------------

                gr.HTML(
                    """
                    <div class="cv-export-heading">
                      <h2>Exportar relatório</h2>
                      <p>
                        Utilize o PDF para conferência, o Word para edição e
                        o Excel para tratamento dos dados.
                      </p>
                    </div>
                    """
                )

                with gr.Row(elem_classes=["cv-downloads"]):
                    md_out = gr.File(
                        label="Markdown (.md)",
                        elem_classes=[
                            "cv-download",
                            "cv-download-technical",
                        ],
                    )

                    xlsx_out = gr.File(
                        label="Planilha Excel (.xlsx)",
                        elem_classes=["cv-download"],
                    )

                    docx_out = gr.File(
                        label="Documento Word (.docx)",
                        elem_classes=["cv-download"],
                    )

                    pdf_out = gr.File(
                        label="Relatório PDF (.pdf)",
                        elem_classes=[
                            "cv-download",
                            "cv-download-primary",
                        ],
                    )

            # =====================================================
            # RODAPÉ
            # =====================================================

            gr.HTML(
                """
                <footer class="cv-footer-note">
                  Codevasf — 12ª Superintendência Regional · Natal/RN<br>
                  Análise assistida por regras automáticas e inteligência
                  artificial. A decisão final permanece com a equipe técnica.
                </footer>
                """
            )

        # =========================================================
        # SAÍDAS DA ANÁLISE
        # A ordem deve acompanhar os valores retornados por analisar()
        # =========================================================

        analysis_outputs = [
            progresso,
            resumo_cards,
            resultado,
            inventario,
            state,
            md_out,
            xlsx_out,
            docx_out,
            pdf_out,
            painel_envio,
            painel_resultado,
            item_select,
            status_dd,
            motivo_tb,
        ]

        # =========================================================
        # EVENTOS
        # =========================================================

        btn.click(
            fn=analisar,
            inputs=[tipo, zip_in],
            outputs=analysis_outputs,
        )

        btn_nova.click(
            fn=nova_analise,
            outputs=analysis_outputs,
        )

        item_select.change(
            fn=carregar_item_revisao,
            inputs=[item_select, state],
            outputs=[status_dd, motivo_tb],
        )

        btn_salvar_item.click(
            fn=salvar_item_revisao,
            inputs=[
                item_select,
                status_dd,
                motivo_tb,
                state,
            ],
            outputs=[
                state,
                resumo_cards,
                resultado,
                item_select,
            ],
        )

        btn_revisar.click(
            fn=gerar_relatorio_revisado,
            inputs=[state],
            outputs=[
                resumo_cards,
                resultado,
                state,
                md_out,
                xlsx_out,
                docx_out,
                pdf_out,
            ],
        )

    return demo


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
