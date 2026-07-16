"""Interface Gradio para Hugging Face Spaces — Conformidade Documental CODEVASF 12ª SR."""

from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path

import gradio as gr
import spaces

from conformidade.analyzer import StatusConformidade, analisar_conformidade
from conformidade.checklist import TipoEntidade, label_tipo, load_checklist
from conformidade.config import load_settings
from conformidade.llm import OllamaError, check_llm_health, resolve_backend
from conformidade.loaders import load_from_zip, ocr_available, scan_folder
from conformidade.report import relatorio_para_markdown, relatorio_para_xlsx

STATUS_PT = {
    StatusConformidade.ATENDIDO: "ATENDIDO",
    StatusConformidade.PARCIAL: "PARCIAL",
    StatusConformidade.NAO_ATENDIDO: "NÃO ATENDIDO",
}


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


@spaces.GPU(duration=180)
def analisar(tipo_label: str, zip_file, progress=gr.Progress(track_tqdm=False)):
    """ZeroGPU exige @spaces.GPU; a inferência LLM usa HF API (CPU/OCR no container)."""
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
    try:
        zip_path = Path(zip_file) if isinstance(zip_file, str) else Path(zip_file.name)
        # Gradio pode entregar caminho temporário; copia para pasta de trabalho
        local_zip = work / (zip_path.name or f"upload_{uuid.uuid4().hex}.zip")
        shutil.copy2(zip_path, local_zip)

        progress(0.1, desc="Extraindo e lendo documentos (OCR se necessário)...")
        documents = load_from_zip(local_zip, work / "extraidos")
        if not documents:
            # fallback: se o upload não for zip válido, tenta pasta
            documents = scan_folder(work)
        if not documents:
            raise gr.Error("Nenhum documento legível encontrado no ZIP.")

        total_batches = max(1, (len(checklist.itens) + 2) // 3)
        state = {"n": 0}

        def on_progress(msg: str) -> None:
            state["n"] = min(state["n"] + 1, total_batches)
            progress(0.15 + 0.8 * (state["n"] / total_batches), desc=msg)

        progress(0.15, desc="Analisando conformidade com o modelo...")
        try:
            relatorio = analisar_conformidade(
                settings, checklist, documents, on_progress=on_progress
            )
        except (OllamaError, ValueError) as exc:
            raise gr.Error(str(exc)) from exc

        counts = relatorio.contagem
        lines = [
            f"## Resultado — {label_tipo(relatorio.tipo)}",
            f"**Entidade:** {relatorio.entidade_detectada}",
            "",
            relatorio.resumo,
            "",
            f"- Atendidos: **{counts['atendido']}**",
            f"- Parciais: **{counts['parcial']}**",
            f"- Não atendidos: **{counts['nao_atendido']}**",
            "",
            "---",
            "",
        ]
        for item in relatorio.itens:
            lines.append(
                f"### {item.numero}. [{STATUS_PT[item.status]}] {item.descricao}"
            )
            lines.append(f"**Motivo:** {item.motivo}")
            if item.documentos_relacionados:
                lines.append("**Arquivos:** " + ", ".join(item.documentos_relacionados))
            lines.append("")

        out_dir = work / "saida"
        out_dir.mkdir(exist_ok=True)
        md_path = out_dir / "relatorio_conformidade.md"
        xlsx_path = out_dir / "relatorio_conformidade.xlsx"
        md_path.write_text(relatorio_para_markdown(relatorio), encoding="utf-8")
        xlsx_path.write_bytes(relatorio_para_xlsx(relatorio))

        inventory = "\n".join(
            f"- {d.relative_path} ({d.extraction_method}, {len(d.content)} chars)"
            for d in documents
        )
        progress(1.0, desc="Concluído")
        return "\n".join(lines), inventory, str(md_path), str(xlsx_path)
    finally:
        # Mantém pasta até o Gradio servir os downloads; limpeza fica com /tmp do Space
        pass


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="CODEVASF 12ª SR — Conformidade Documental") as demo:
        gr.Markdown(
            """
# CODEVASF 12ª SR — Análise de Conformidade Documental
Compare o ZIP do requerimento com a Lista de Documentos (Prefeitura ou Associação).
Ferramenta **assistiva** — a decisão final é da equipe técnica.
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

        resultado = gr.Markdown(label="Resultado")
        inventario = gr.Textbox(label="Inventário dos arquivos", lines=8)
        with gr.Row():
            md_out = gr.File(label="Relatório .md")
            xlsx_out = gr.File(label="Relatório .xlsx")

        btn.click(
            fn=analisar,
            inputs=[tipo, zip_in],
            outputs=[resultado, inventario, md_out, xlsx_out],
        )
        gr.Markdown(
            "CODEVASF — 12ª Superintendência Regional (Natal/RN) · Uso assistivo"
        )
    return demo


demo = build_ui()

if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=7860)
