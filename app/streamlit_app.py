"""Interface Streamlit institucional — Conformidade Documental CODEVASF 12ª SR."""

from __future__ import annotations

import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app.styles import APP_CSS, render_hero, render_steps
from conformidade.analyzer import analisar_conformidade
from conformidade.checklist import (
    TipoEntidade,
    infer_tipo_from_names,
    label_tipo,
    load_checklist,
)
from conformidade.config import load_settings
from conformidade.llm import OllamaError, check_llm_health, resolve_backend
from conformidade.loaders import (
    LoadedDocument,
    load_from_zip,
    ocr_available,
    save_uploaded_bytes,
    scan_folder,
    summarize_inventory,
)
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


STATUS_UI = {
    StatusConformidade.ATENDIDO: ("Atendido", "cv-badge-ok"),
    StatusConformidade.PARCIAL: ("Parcial", "cv-badge-parcial"),
    StatusConformidade.NAO_ATENDIDO: ("Não atendido", "cv-badge-nao"),
}


def init_session_state() -> None:
    defaults = {
        "documents": None,
        "session_dir": None,
        "relatorio": None,
        "inventory_text": "",
        "tipo_selecionado": "Prefeitura",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _new_session_dir(uploads_path: Path) -> Path:
    session_dir = uploads_path / f"sessao_{uuid.uuid4().hex[:10]}"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def _cleanup_session_dir() -> None:
    path = st.session_state.get("session_dir")
    if path and Path(path).exists():
        shutil.rmtree(path, ignore_errors=True)
    st.session_state.session_dir = None
    st.session_state.documents = None
    st.session_state.relatorio = None
    st.session_state.inventory_text = ""


def render_sidebar(settings) -> None:
    st.sidebar.markdown("### Rede interna · 12ª SR")
    st.sidebar.caption("Ferramenta assistiva para análise de requerimentos de doação.")

    healthy, llm_message = check_llm_health(settings)
    backend = resolve_backend(settings)
    ocr_ok, ocr_message = ocr_available()
    with st.sidebar.expander("Status do sistema (TI)", expanded=False):
        st.markdown(f"**LLM** (`{backend}`)")
        if backend == "ollama":
            st.code(settings.ollama_base_url, language=None)
            st.markdown(f"Modelo: `{settings.ollama_chat_model}`")
        else:
            st.markdown(f"Modelo HF: `{settings.hf_model}`")
        st.markdown("✅ " + llm_message if healthy else "❌ " + llm_message)
        st.markdown("**OCR (PDFs escaneados)**")
        st.markdown("✅ " + ocr_message if ocr_ok else "❌ " + ocr_message)
        st.markdown("**Checklists**")
        st.code(str(settings.checklists_path), language=None)
        st.markdown(
            "✅ Listas encontradas" if settings.checklists_path_exists() else "❌ Listas ausentes"
        )

    if not ocr_ok:
        st.sidebar.warning(
            "OCR indisponível: PDFs escaneados podem ficar sem texto. "
            "Instale Tesseract (por) + pymupdf/pytesseract."
        )

    st.sidebar.divider()
    st.sidebar.markdown("**Como usar**")
    st.sidebar.markdown(
        "1. Escolha Prefeitura ou Associação\n"
        "2. Envie o ZIP do requerimento\n"
        "3. Clique em **Analisar conformidade**\n"
        "4. Revise o relatório e baixe se necessário"
    )

    if st.sidebar.button("Nova análise / limpar sessão", use_container_width=True):
        _cleanup_session_dir()
        st.rerun()


def _load_documents_from_inputs(
    settings,
    uploaded_zips,
    uploaded_files,
    folder_path: str,
) -> list[LoadedDocument]:
    session_dir = _new_session_dir(settings.uploads_path)
    st.session_state.session_dir = str(session_dir)
    documents: list[LoadedDocument] = []

    if folder_path.strip():
        folder = Path(folder_path.strip()).expanduser()
        documents.extend(scan_folder(folder))

    for uploaded in uploaded_zips or []:
        zip_path = save_uploaded_bytes(
            uploaded.name,
            uploaded.getvalue(),
            session_dir / "zips",
        )
        documents.extend(load_from_zip(zip_path, session_dir / "extraidos"))

    if uploaded_files:
        loose_dir = session_dir / "avulsos"
        loose_dir.mkdir(parents=True, exist_ok=True)
        for uploaded in uploaded_files:
            save_uploaded_bytes(uploaded.name, uploaded.getvalue(), loose_dir)
        documents.extend(scan_folder(loose_dir))

    unique: dict[str, LoadedDocument] = {}
    for doc in documents:
        key = f"{doc.relative_path}::{doc.file_name}::{len(doc.content)}"
        unique[key] = doc
    return list(unique.values())


def render_item(item) -> None:
    label, css = STATUS_UI[item.status]
    st.markdown(
        f"""
<div class="cv-card">
  <span class="cv-badge {css}">{label}</span>
  <span class="cv-muted">fonte: {item.fonte}</span>
  <div class="cv-item-title">{item.numero}. {item.descricao}</div>
  <div><strong>Motivo:</strong> {item.motivo}</div>
  {"<div class='cv-muted' style='margin-top:0.4rem'>Arquivos: " + ", ".join(item.documentos_relacionados) + "</div>" if item.documentos_relacionados else ""}
</div>
""",
        unsafe_allow_html=True,
    )


def render_relatorio(relatorio: RelatorioConformidade) -> None:
    counts = relatorio.contagem
    total = len(relatorio.itens) or 1
    versao = "revisada" if relatorio.revisado else "automática"

    st.markdown("### Resultado da análise")
    st.markdown(
        f"**Entidade / município:** {relatorio.entidade_detectada}  \n"
        f"**Checklist:** {label_tipo(relatorio.tipo)}  \n"
        f"**Versão:** {versao}"
    )
    st.info(relatorio.resumo)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Itens do checklist", len(relatorio.itens))
    c2.metric("Atendidos", counts["atendido"])
    c3.metric("Parciais", counts["parcial"])
    c4.metric("Não atendidos", counts["nao_atendido"])
    st.progress(counts["atendido"] / total, text=f"Conformidade plena: {counts['atendido']}/{total}")

    st.markdown("#### Ajuste humano (opcional)")
    st.caption("Altere o status e/ou motivo e clique em aplicar para gerar a versão revisada.")
    overrides: list[dict] = []
    for item in relatorio.itens:
        with st.expander(
            f"{item.numero}. [{item.status.value}] ({item.fonte}) {item.descricao[:80]}…",
            expanded=False,
        ):
            status_opts = ["atendido", "parcial", "nao_atendido"]
            new_status = st.selectbox(
                "Status",
                options=status_opts,
                index=status_opts.index(item.status.value),
                key=f"rev_status_{item.numero}_{relatorio.revisado}",
            )
            new_motivo = st.text_area(
                "Motivo",
                value=item.motivo,
                key=f"rev_motivo_{item.numero}_{relatorio.revisado}",
                height=80,
            )
            if item.documentos_relacionados:
                st.caption("Arquivos: " + ", ".join(item.documentos_relacionados))
            overrides.append(
                {"numero": item.numero, "status": new_status, "motivo": new_motivo}
            )

    if st.button("Aplicar revisão e atualizar relatório", type="primary"):
        st.session_state.relatorio = aplicar_revisao_humana(relatorio, overrides)
        st.success("Revisão aplicada. Baixe o relatório atualizado abaixo.")
        st.rerun()

    md = relatorio_para_markdown(relatorio)
    xlsx = relatorio_para_xlsx(relatorio)
    docx = relatorio_para_docx(relatorio)
    pdf = relatorio_para_pdf(relatorio)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    suffix = "_revisado" if relatorio.revisado else ""
    dl_md, dl_xlsx, dl_docx, dl_pdf = st.columns(4)
    with dl_md:
        st.download_button(
            "Baixar .md",
            data=md.encode("utf-8"),
            file_name=f"relatorio_conformidade{suffix}_{stamp}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with dl_xlsx:
        st.download_button(
            "Baixar .xlsx",
            data=xlsx,
            file_name=f"relatorio_conformidade{suffix}_{stamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with dl_docx:
        st.download_button(
            "Baixar .docx",
            data=docx,
            file_name=f"relatorio_conformidade{suffix}_{stamp}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
    with dl_pdf:
        st.download_button(
            "Baixar .pdf",
            data=pdf,
            file_name=f"relatorio_conformidade{suffix}_{stamp}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    tabs = st.tabs(
        [
            f"Atendidos ({counts['atendido']})",
            f"Parciais ({counts['parcial']})",
            f"Não atendidos ({counts['nao_atendido']})",
            "Todos os itens",
        ]
    )

    with tabs[0]:
        items = [i for i in relatorio.itens if i.status is StatusConformidade.ATENDIDO]
        if not items:
            st.caption("Nenhum item plenamente atendido.")
        for item in items:
            render_item(item)

    with tabs[1]:
        items = [i for i in relatorio.itens if i.status is StatusConformidade.PARCIAL]
        if not items:
            st.caption("Nenhum item parcial.")
        for item in items:
            render_item(item)

    with tabs[2]:
        items = [i for i in relatorio.itens if i.status is StatusConformidade.NAO_ATENDIDO]
        if not items:
            st.caption("Nenhum item pendente.")
        for item in items:
            render_item(item)

    with tabs[3]:
        for item in relatorio.itens:
            render_item(item)

    with st.expander("Documentos analisados"):
        for name in relatorio.documentos_analisados:
            st.markdown(f"- `{name}`")

    if relatorio.resposta_bruta:
        with st.expander("Detalhes técnicos da análise (TI)"):
            st.code(relatorio.resposta_bruta, language="json")


def main() -> None:
    settings = load_settings()
    init_session_state()

    st.set_page_config(
        page_title="CODEVASF 12ª SR — Conformidade Documental",
        page_icon="📑",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(APP_CSS, unsafe_allow_html=True)
    st.markdown(render_hero(), unsafe_allow_html=True)
    st.markdown(render_steps(), unsafe_allow_html=True)

    render_sidebar(settings)

    # --- Passo 1 ---
    st.markdown("#### 1. Tipo de solicitante")
    tipo_label = st.radio(
        "Selecione o tipo de requerimento",
        options=["Prefeitura", "Associação / Cooperativa / Instituição pública"],
        horizontal=True,
        label_visibility="collapsed",
        key="tipo_selecionado",
    )
    tipo = (
        TipoEntidade.PREFEITURA
        if tipo_label.startswith("Prefeitura")
        else TipoEntidade.ASSOCIACAO
    )
    sugestao_placeholder = st.empty()

    checklist = load_checklist(settings.checklists_path, tipo)
    with st.expander(f"Ver checklist — {checklist.titulo} ({len(checklist.itens)} itens)"):
        st.caption(f"Fonte: {Path(checklist.fonte).name}")
        for item in checklist.itens:
            st.markdown(f"{item.numero}. {item.descricao}")

    st.divider()

    # --- Passo 2 ---
    st.markdown("#### 2. Documentos do requerimento")
    tab_zip, tab_pasta, tab_avulsos = st.tabs(
        ["ZIP (recomendado)", "Pasta no servidor", "Arquivos avulsos"]
    )

    with tab_zip:
        st.caption(
            "Formato mais comum dos requerimentos recebidos por e-mail. "
            "PDFs escaneados são lidos automaticamente via OCR."
        )
        uploaded_zips = st.file_uploader(
            "Arraste ou selecione o(s) arquivo(s) .zip",
            type=["zip"],
            accept_multiple_files=True,
            key="uploader_zip",
        )

    with tab_pasta:
        st.caption("Quando os arquivos já estão em pasta acessível ao servidor (ex.: share).")
        folder_path = st.text_input(
            "Caminho da pasta",
            placeholder=r"Z:\Requerimentos\Municipio_Exemplo  ou  /mnt/codevasf/...",
            help="Caminho absoluto no servidor onde a aplicação está rodando.",
        )

    with tab_avulsos:
        st.caption("Envio pontual de PDFs/DOCX/imagens quando não houver ZIP. Imagens e PDFs escaneados passam por OCR.")
        uploaded_files = st.file_uploader(
            "PDFs, DOCX, TXT ou imagens",
            type=["pdf", "docx", "txt", "md", "png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"],
            accept_multiple_files=True,
            key="uploader_files",
        )

    load_col, analyze_col = st.columns([1, 1])
    with load_col:
        carregar = st.button("Carregar documentos", use_container_width=True)
    with analyze_col:
        analisar = st.button(
            "Analisar conformidade",
            type="primary",
            use_container_width=True,
        )

    if carregar:
        try:
            if st.session_state.session_dir:
                shutil.rmtree(st.session_state.session_dir, ignore_errors=True)
            documents = _load_documents_from_inputs(
                settings, uploaded_zips, uploaded_files, folder_path
            )
            st.session_state.documents = documents
            st.session_state.inventory_text = summarize_inventory(documents)
            st.session_state.relatorio = None
            if not documents:
                st.warning("Nenhum documento legível encontrado.")
            else:
                sugestao = infer_tipo_from_names([d.file_name for d in documents])
                if sugestao and sugestao != tipo:
                    sugestao_placeholder.warning(
                        f"Pelos nomes dos arquivos, o conjunto parece ser de "
                        f"**{label_tipo(sugestao)}**, mas o checklist selecionado é "
                        f"**{label_tipo(tipo)}**. Confirme o tipo antes de analisar."
                    )
                st.success(f"{len(documents)} documento(s) carregado(s).")
        except Exception as exc:
            st.error(f"Falha ao carregar documentos: {exc}")

    if st.session_state.documents:
        with st.expander("Inventário dos documentos carregados", expanded=True):
            st.text(st.session_state.inventory_text)

    st.divider()

    # --- Passo 3 ---
    st.markdown("#### 3. Análise e resultado")

    if analisar:
        documents = st.session_state.documents
        if not documents:
            try:
                if st.session_state.session_dir:
                    shutil.rmtree(st.session_state.session_dir, ignore_errors=True)
                documents = _load_documents_from_inputs(
                    settings, uploaded_zips, uploaded_files, folder_path
                )
                st.session_state.documents = documents
                st.session_state.inventory_text = summarize_inventory(documents)
            except Exception as exc:
                st.error(f"Falha ao carregar documentos: {exc}")
                return

        if not documents:
            st.warning("Envie um ZIP, arquivos avulsos ou informe uma pasta antes de analisar.")
            return

        healthy, llm_message = check_llm_health(settings)
        if not healthy:
            st.error(
                "Serviço de IA indisponível. Detalhe: " + llm_message
            )
            return

        progress = st.empty()
        bar = st.progress(0, text="Iniciando análise...")
        total_batches = max(1, (len(checklist.itens) + 2) // 3)
        state = {"done": 0}

        def _progress(msg: str) -> None:
            state["done"] = min(state["done"] + 1, total_batches)
            bar.progress(state["done"] / total_batches, text=msg)
            progress.info(msg)

        with st.spinner("Analisando no servidor interno (IA local). Aguarde alguns minutos..."):
            try:
                relatorio = analisar_conformidade(
                    settings,
                    checklist,
                    documents,
                    on_progress=_progress,
                )
                progress.empty()
                bar.progress(1.0, text="Análise concluída")
                st.session_state.relatorio = relatorio
            except (OllamaError, ValueError) as exc:
                progress.empty()
                bar.empty()
                st.error(str(exc))
                return

    if st.session_state.relatorio:
        render_relatorio(st.session_state.relatorio)
    else:
        st.markdown(
            '<p class="cv-muted">O relatório aparecerá aqui após a análise.</p>',
            unsafe_allow_html=True,
        )

    st.markdown(
        """
<div class="cv-footer-note">
  CODEVASF — Companhia de Desenvolvimento dos Vales do São Francisco e do Parnaíba ·
  12ª Superintendência Regional (Natal/RN) · Uso interno ·
  Esta ferramenta não substitui a conferência humana da documentação.
</div>
""",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
