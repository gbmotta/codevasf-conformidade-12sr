"""
Interface Streamlit — intranet / Docker (Codevasf 12ª SR).

Entrada típica:
  streamlit run app/streamlit_app.py --server.port 8502

Diferença em relação ao ``app.py`` (Gradio):
  - Pensada para servidor interno com Ollama
  - Visual institucional próprio (``app/styles.py`` → APP_CSS)
  - Mesmo núcleo de análise (``conformidade.*``)

Não é o runtime do Hugging Face Space (lá usa Gradio + ZeroGPU).
"""

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
from conformidade.batch import analyze_zip_batch
from conformidade.history import compare_history, list_history, load_history, save_analysis
from conformidade.inventory_ui import (
    build_inventory,
    collect_validade_alerts,
    labels_csv_bytes,
)
from conformidade.loaders import (
    LoadedDocument,
    load_from_zip,
    ocr_available,
    save_uploaded_bytes,
    scan_folder,
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
        "inventory_entries": None,
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
    st.session_state.inventory_entries = None


def _refresh_inventory(documents: list[LoadedDocument]) -> None:
    entries = build_inventory(documents)
    st.session_state.inventory_entries = entries
    lines = []
    for e in entries:
        conf = f"{e.confidence * 100:.0f}%"
        val = ""
        if e.validade_status == "vencida":
            val = " | VENCIDA"
        elif e.validade_status == "a_vencer":
            val = f" | faltam {e.validade_dias}d"
        lines.append(
            f"- [{e.label} {conf}] {e.relative_path} ({e.chars} car., {e.method}){val}"
        )
    alerts = collect_validade_alerts(entries)
    if alerts:
        lines.append("")
        lines.append("ALERTAS DE VALIDADE:")
        for a in alerts:
            lines.append(f"  ! {a.file_name}: {a.validade_msg}")
    st.session_state.inventory_text = "\n".join(lines) if lines else "(vazio)"

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
        + (f"  \n**CNPJ:** {relatorio.cnpj_principal}" if relatorio.cnpj_principal else "")
        + (f"  \n**Histórico:** `{relatorio.history_id}`" if relatorio.history_id else "")
    )
    st.info(relatorio.resumo)
    if relatorio.alertas:
        with st.expander(f"Alertas do pacote ({len(relatorio.alertas)})", expanded=True):
            for a in relatorio.alertas:
                st.warning(a)

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

    entries = st.session_state.get("inventory_entries")
    if entries:
        st.download_button(
            "Exportar rótulos desta análise (CSV)",
            data=labels_csv_bytes(entries),
            file_name=f"rotulos_para_treino_{stamp}.csv",
            mime="text/csv",
            use_container_width=True,
            key="dl_labels_relatorio",
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



def _render_historico_tab() -> None:
    st.markdown("#### Histórico de pacotes analisados")
    st.caption("Reabra um relatório salvo ou compare duas versões.")
    metas = list_history(limit=80)
    if not metas:
        st.info("Nenhuma análise salva ainda. Rode uma análise individual ou em lote.")
        return

    labels = [
        f"{m.created_at} · {m.entidade} · A{m.atendidos}/P{m.parciais}/N{m.nao_atendidos} · {m.id}"
        for m in metas
    ]
    choice = st.selectbox("Pacote", options=labels, key="hist_select")
    meta = metas[labels.index(choice)]

    c1, c2, c3 = st.columns(3)
    c1.metric("Atendidos", meta.atendidos)
    c2.metric("Parciais", meta.parciais)
    c3.metric("Não atendidos", meta.nao_atendidos)
    st.caption(f"ZIP: {meta.zip_name or '—'} · CNPJ: {meta.cnpj or '—'}")

    if st.button("Reabrir este relatório", key="hist_reopen"):
        _, rel = load_history(meta.id)
        st.session_state.relatorio = rel
        st.success("Relatório carregado na sessão.")
        render_relatorio(rel)

    st.divider()
    st.markdown("##### Comparar duas versões")
    ids = [m.id for m in metas]
    a = st.selectbox("Versão A", ids, key="cmp_a")
    b = st.selectbox("Versão B", ids, index=min(1, len(ids) - 1), key="cmp_b")
    if st.button("Comparar status dos itens", key="cmp_btn") and a != b:
        rows = compare_history(a, b)
        changed = [r for r in rows if r["mudou"]]
        st.write(f"{len(changed)} item(ns) com status diferente de {len(rows)}.")
        st.dataframe(rows, use_container_width=True)


def _render_lote_tab(settings) -> None:
    st.markdown("#### Análise em lote → planilha consolidada")
    st.caption("Vários ZIPs → XLSX (estilo controle 201–220) + histórico.")
    tipo_label = st.radio(
        "Tipo do lote",
        options=["Associação / Cooperativa", "Prefeitura"],
        horizontal=True,
        key="lote_tipo",
    )
    tipo = (
        TipoEntidade.PREFEITURA
        if tipo_label.startswith("Prefeitura")
        else TipoEntidade.ASSOCIACAO
    )
    zips = st.file_uploader(
        "ZIPs do lote",
        type=["zip"],
        accept_multiple_files=True,
        key="lote_zips",
    )
    if st.button("Analisar lote e gerar planilha", type="primary", key="lote_run"):
        if not zips:
            st.warning("Envie ao menos um ZIP.")
            return
        healthy, llm_message = check_llm_health(settings)
        if not healthy:
            st.error("IA indisponível: " + llm_message)
            return
        session = _new_session_dir(settings.uploads_path)
        paths = []
        for up in zips:
            paths.append(save_uploaded_bytes(up.name, up.getvalue(), session / "lote_zips"))
        prog = st.empty()

        def _p(msg: str) -> None:
            prog.info(msg)

        with st.spinner("Processando lote..."):
            result = analyze_zip_batch(
                settings,
                paths,
                tipo,
                save_history=True,
                work_dir=session / "work",
                on_progress=_p,
            )
        prog.empty()
        xlsx = result.to_xlsx_bytes()
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        st.success(f"Concluído: {len(result.rows)} pacote(s).")
        st.dataframe(
            [
                {
                    "ITEM": r.ordem,
                    "BENEFICIÁRIO": r.beneficiario,
                    "SITUAÇÃO": r.situacao,
                    "A/P/N": f"{r.atendidos}/{r.parciais}/{r.nao_atendidos}",
                    "CNPJ": r.cnpj,
                }
                for r in result.rows
            ],
            use_container_width=True,
        )
        st.download_button(
            "Baixar planilha consolidada (.xlsx)",
            data=xlsx,
            file_name=f"CONTROLE_LOTE_Conformidade_{stamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


def main() -> None:
    settings = load_settings()
    init_session_state()

    st.set_page_config(
        page_title="Codevasf 12ª SR — Conformidade Documental",
        page_icon="📑",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(APP_CSS, unsafe_allow_html=True)
    st.markdown(render_hero(), unsafe_allow_html=True)
    st.markdown(render_steps(), unsafe_allow_html=True)

    render_sidebar(settings)

    main_tab, hist_tab, lote_tab = st.tabs(
        ["Análise individual", "Histórico / fila", "Lote consolidado"]
    )

    with hist_tab:
        _render_historico_tab()

    with lote_tab:
        _render_lote_tab(settings)

    with main_tab:
        _render_analise_individual(settings)

    st.markdown(
        """
<div class="cv-footer-note">
  Codevasf — 12ª Superintendência Regional (Natal/RN) · Uso interno ·
  Esta ferramenta não substitui a conferência humana da documentação.
</div>
""",
        unsafe_allow_html=True,
    )


def _render_analise_individual(settings) -> None:
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
            _refresh_inventory(documents)
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
        with st.expander("Inventário tipado dos documentos", expanded=True):
            st.text(st.session_state.inventory_text)
            entries = st.session_state.get("inventory_entries") or []
            if entries:
                st.download_button(
                    "Exportar rótulos desta análise (CSV)",
                    data=labels_csv_bytes(entries),
                    file_name=f"rotulos_para_treino_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

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
                _refresh_inventory(documents)
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
                zip_name = uploaded_zips[0].name if uploaded_zips else ''
                inv = [e.to_dict() for e in (st.session_state.inventory_entries or [])]
                meta = save_analysis(
                    relatorio,
                    zip_name=zip_name,
                    alertas=list(relatorio.alertas or []),
                    cnpj=relatorio.cnpj_principal,
                    inventory=inv,
                )
                relatorio.history_id = meta.id
                st.session_state.relatorio = relatorio
                _refresh_inventory(documents)
                st.success(f'Salvo no histórico: {meta.id}')
                alerts = collect_validade_alerts(st.session_state.inventory_entries or [])
                if alerts:
                    st.warning(
                        "Alertas de validade: "
                        + "; ".join(
                            f"{a.file_name} ({a.validade_msg})" for a in alerts[:5]
                        )
                    )
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



if __name__ == "__main__":
    main()
