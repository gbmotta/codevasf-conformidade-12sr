"""
Tema visual institucional — Streamlit e Gradio (Codevasf 12ª SR).

Fonte normativa: ``id_visual_codevasf.pdf`` (Manual de Identidade Visual).

Conteúdo deste módulo:
  - Constantes de cor (marca + promocional)
  - ``APP_CSS`` / ``GRADIO_CSS`` — estilos da interface
  - ``render_hero`` / ``render_steps`` / laterais — HTML do cabeçalho
  - ``gradio_theme()`` — tema Gradio Soft com paleta oficial
  - ``logo_data_uri()`` — logo embutida (base64) a partir de ``app/static/``

Paleta da marca: Azul ``#005ca8`` · Verde ``#007d4e``
Paleta promocional: ``#0066B3`` · ``#008658`` · ``#89BD2B`` · ``#74C9EA`` ·
``#222B54`` · ``#F2F2F2``
Tipografia: Rawline (promocional); grafia em texto: ``Codevasf``.
"""

from __future__ import annotations

import base64
from pathlib import Path

# --- Paleta oficial (marca) ---
COLOR_AZUL_MARCA = "#005ca8"
COLOR_VERDE_MARCA = "#007d4e"

# --- Paleta promocional ---
COLOR_AZUL = "#0066B3"
COLOR_VERDE = "#008658"
COLOR_VERDE_CLARO = "#89BD2B"
COLOR_AZUL_CLARO = "#74C9EA"
COLOR_AZUL_ESCURO = "#222B54"
COLOR_OFFWHITE = "#F2F2F2"

# Aliases usados no tema Gradio / Streamlit
COLOR_BLUE_DARK = COLOR_AZUL_ESCURO
COLOR_BLUE = COLOR_AZUL_MARCA
COLOR_TEAL = COLOR_AZUL
COLOR_GREEN = COLOR_VERDE_MARCA
COLOR_GREEN_MID = COLOR_VERDE
COLOR_GREEN_DARK = "#005c39"
COLOR_GREEN_LIGHT = COLOR_VERDE_CLARO
COLOR_BG = COLOR_OFFWHITE
COLOR_BG_TOP = "#e8f4f8"
COLOR_BORDER = "#b7d7e8"
COLOR_TEXT = COLOR_AZUL_ESCURO
COLOR_MUTED = "#4a5878"

# Degradê “rio”: azul institucional → azul claro → verde institucional
RIVER_GRADIENT = (
    "linear-gradient(115deg, "
    f"{COLOR_AZUL_ESCURO} 0%, "
    f"{COLOR_AZUL_MARCA} 28%, "
    f"{COLOR_AZUL} 48%, "
    f"{COLOR_AZUL_CLARO} 62%, "
    f"{COLOR_VERDE} 82%, "
    f"{COLOR_VERDE_MARCA} 100%)"
)

FONT_STACK = '"Rawline", "IBM Plex Sans", "Segoe UI", sans-serif'

_STATIC = Path(__file__).resolve().parent / "static"
_LOGO_PATH = _STATIC / "logo_codevasf.png"


def logo_data_uri() -> str:
    if not _LOGO_PATH.exists():
        return ""
    encoded = base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


APP_CSS = f"""
<style>
@import url('https://fonts.cdnfonts.com/css/rawline');
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {{
  font-family: {FONT_STACK};
}}

.stApp {{
  background:
    linear-gradient(180deg, {COLOR_BG_TOP} 0%, {COLOR_OFFWHITE} 220px, #ffffff 420px);
}}

#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
header[data-testid="stHeader"] {{ background: transparent; }}

.cv-hero {{
  position: relative;
  overflow: hidden;
  background: {RIVER_GRADIENT};
  color: #fff;
  border-radius: 14px;
  padding: 1.35rem 1.6rem 1.55rem;
  margin-bottom: 1.25rem;
  box-shadow: 0 10px 28px rgba(0, 92, 168, 0.28);
  border: 1px solid rgba(255,255,255,0.10);
  text-align: center;
}}
.cv-hero::after {{
  content: "";
  position: absolute;
  left: 0; right: 0; bottom: -2px;
  height: 28px;
  background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 40' preserveAspectRatio='none'%3E%3Cpath d='M0 20 Q150 0 300 20 T600 20 T900 20 T1200 20 V40 H0 Z' fill='rgba(255,255,255,0.14)'/%3E%3C/svg%3E") repeat-x bottom;
  background-size: 600px 28px;
  pointer-events: none;
}}
.cv-logo {{
  display: block;
  height: 52px;
  width: auto;
  margin: 0 auto 0.9rem auto;
  border-radius: 6px;
  box-shadow: 0 4px 14px rgba(0,0,0,0.18);
}}
.cv-hero-kicker {{
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.92;
  margin: 0 0 0.35rem 0;
  font-weight: 600;
}}
.cv-hero h1 {{
  font-size: 1.55rem;
  line-height: 1.25;
  margin: 0 0 0.35rem 0;
  font-weight: 700;
  color: #fff !important;
}}
.cv-hero p {{
  margin: 0 auto;
  opacity: 0.95;
  font-size: 0.98rem;
  max-width: 58rem;
}}
.cv-steps {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
  margin: 0 0 1.25rem 0;
}}
.cv-step {{
  background: #fff;
  border: 1px solid {COLOR_BORDER};
  border-radius: 12px;
  padding: 0.85rem 1rem;
  box-shadow: 0 2px 8px rgba(0, 92, 168, 0.06);
}}
.cv-step-num {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.55rem;
  height: 1.55rem;
  border-radius: 999px;
  background: {COLOR_AZUL_MARCA};
  color: #fff;
  font-size: 0.8rem;
  font-weight: 700;
  margin-right: 0.45rem;
}}
.cv-step strong {{ color: {COLOR_AZUL_ESCURO}; font-size: 0.95rem; }}
.cv-step span {{
  display: block;
  margin-top: 0.25rem;
  color: {COLOR_MUTED};
  font-size: 0.84rem;
}}
.cv-card {{
  background: #fff;
  border: 1px solid {COLOR_BORDER};
  border-radius: 12px;
  padding: 1rem 1.1rem;
  margin-bottom: 0.85rem;
}}
.cv-badge {{
  display: inline-block;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
}}
.cv-badge-ok {{ background: #d7f0e5; color: {COLOR_VERDE_MARCA}; }}
.cv-badge-parcial {{ background: #eef7d4; color: #5f7d12; }}
.cv-badge-nao {{ background: #fde2e2; color: #9b1c1c; }}
.cv-footer-note {{
  margin-top: 1.5rem;
  padding-top: 0.85rem;
  border-top: 1px solid {COLOR_BORDER};
  color: {COLOR_MUTED};
  font-size: 0.82rem;
}}
div[data-testid="stMetric"] {{
  background: #fff;
  border: 1px solid {COLOR_BORDER};
  border-radius: 12px;
  padding: 0.55rem 0.75rem;
}}
@media (max-width: 900px) {{
  .cv-steps {{ grid-template-columns: 1fr; }}
  .cv-hero h1 {{ font-size: 1.3rem; }}
}}
</style>
"""


def render_hero(subtitle: str | None = None) -> str:
    body = subtitle or (
        "Compare o requerimento enviado (ZIP ou pasta) com a Lista de Documentos "
        "exigida para doação de bens móveis — Prefeituras ou Associações — "
        "com apoio de IA local no servidor interno."
    )
    logo = logo_data_uri()
    logo_html = (
        f'<img class="cv-logo" src="{logo}" alt="Marca Codevasf" />' if logo else ""
    )
    return f"""
<div class="cv-hero">
  {logo_html}
  <p class="cv-hero-kicker">Codevasf · 12ª Superintendência Regional · Natal/RN</p>
  <h1>Análise de Conformidade Documental</h1>
  <p>{body}</p>
</div>
"""


def render_steps() -> str:
    return """
<div class="cv-steps">
  <div class="cv-step">
    <strong><span class="cv-step-num">1</span>Tipo de solicitante</strong>
    <span>Prefeitura ou Associação / Cooperativa</span>
  </div>
  <div class="cv-step">
    <strong><span class="cv-step-num">2</span>Documentos</strong>
    <span>Envie o ZIP do requerimento ou informe a pasta</span>
  </div>
  <div class="cv-step">
    <strong><span class="cv-step-num">3</span>Resultado</strong>
    <span>Itens atendidos, parciais e pendentes com motivos</span>
  </div>
</div>
"""


def _icon_tile(svg_paths: str) -> str:
    return (
        '<div class="cv-icon-tile" aria-hidden="true">'
        f'<svg viewBox="0 0 40 40" width="28" height="28" fill="none" '
        f'stroke="currentColor" stroke-width="1.6">{svg_paths}</svg></div>'
    )


def render_side_left() -> str:
    """Painel lateral esquerdo — orientação + padronagem visual."""
    icons = "".join(
        [
            _icon_tile(  # gota
                '<path d="M20 6 C20 6 10 18 10 25 a10 10 0 0 0 20 0 C30 18 20 6 20 6z"/>'
            ),
            _icon_tile(  # ondas
                '<path d="M6 16 q7 6 14 0 t14 0"/><path d="M6 24 q7 6 14 0 t14 0"/>'
            ),
            _icon_tile(  # rio
                '<path d="M8 10 c6 8 6 12 0 20"/><path d="M20 8 c6 8 6 14 0 24"/>'
                '<path d="M32 10 c-6 8 -6 12 0 20"/>'
            ),
            _icon_tile(  # planta
                '<path d="M20 32 V18"/><path d="M20 22 c-8 -2 -10 -10 -8 -14 6 2 10 8 8 14z"/>'
                '<path d="M20 24 c8 -2 10 -10 8 -14 -6 2 -10 8 -8 14z"/>'
            ),
            _icon_tile(  # peixe
                '<path d="M8 20 c6 -8 18 -8 24 0 c-6 8 -18 8 -24 0z"/>'
                '<circle cx="14" cy="19" r="1.2" fill="currentColor"/>'
                '<path d="M32 20 l6 -5 v10z"/>'
            ),
            _icon_tile(  # trator simplificado
                '<circle cx="12" cy="26" r="5"/><circle cx="28" cy="26" r="5"/>'
                '<path d="M8 20 h16 l4 -8 h6 v14"/>'
            ),
        ]
    )
    return f"""
<aside class="cv-side-panel">
  <h3>Como usar</h3>
  <ol class="cv-side-list">
    <li>Escolha Prefeitura ou Associação</li>
    <li>Envie o ZIP com os documentos</li>
    <li>Clique em Analisar conformidade</li>
    <li>Revise e baixe o relatório</li>
  </ol>
  <h3>Dica</h3>
  <p class="cv-side-text">
    Prefira um ZIP com os PDFs nomeados de forma clara
    (ex.: <em>oficio.pdf</em>, <em>ata_posse.pdf</em>).
  </p>
  <div class="cv-icon-grid">{icons}</div>
  <h3>O que entra no ZIP</h3>
  <ul class="cv-side-list plain">
    <li>Ofício / requerimento</li>
    <li>Atas e documentos societários</li>
    <li>Documentos pessoais / CNPJ</li>
    <li>Comprovantes e anexos em PDF</li>
  </ul>
</aside>
"""


def render_side_right() -> str:
    """Painel lateral direito — legendas e contatos."""
    return """
<aside class="cv-side-panel">
  <h3>Legenda</h3>
  <ul class="cv-legend">
    <li><span class="cv-badge cv-badge-ok">Atendido</span> documento ok</li>
    <li><span class="cv-badge cv-badge-parcial">Parcial</span> incompleto / dúvida</li>
    <li><span class="cv-badge cv-badge-nao">Não atendido</span> ausente</li>
  </ul>
  <h3>Como a análise funciona</h3>
  <ul class="cv-side-list">
    <li>Regras pelo nome e conteúdo dos arquivos</li>
    <li>IA só nos itens em dúvida</li>
    <li>Você pode ajustar o status depois</li>
  </ul>
  <h3>Exportação</h3>
  <ul class="cv-side-list plain">
    <li>Texto (.md) — leitura rápida</li>
    <li>Excel (.xlsx) — planilha</li>
    <li>Word (.docx) — edição</li>
    <li>PDF (.pdf) — arquivo oficial</li>
  </ul>
  <h3>12ª SR</h3>
  <p class="cv-side-text">
    Superintendência Regional — Natal/RN<br/>
    Doação / concessão de bens móveis<br/>
    Análise assistiva — a decisão final é da equipe técnica.
  </p>
  <p class="cv-side-link"><a href="https://www.codevasf.gov.br" target="_blank" rel="noopener">codevasf.gov.br</a></p>
</aside>
"""


GRADIO_CSS = f"""
@import url('https://fonts.cdnfonts.com/css/rawline');
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

/* Fundo da página inteira (laterais) — não branco */
html, body, .gradio-container,
body.gradio-container,
.main, .app, .wrap.svelte-1byvi7d,
.contain {{
  background: linear-gradient(
    165deg,
    #dceef7 0%,
    {COLOR_OFFWHITE} 38%,
    #e6f3ec 72%,
    #d9efe6 100%
  ) !important;
  background-attachment: fixed !important;
}}
.gradio-container {{
  font-family: {FONT_STACK} !important;
  max-width: 100% !important;
  width: 100% !important;
  margin: 0 !important;
  padding: 0.85rem 1.25rem 1.5rem !important;
  min-height: 100vh !important;
  box-sizing: border-box !important;
}}
.gradio-container > .main,
.gradio-container .main {{
  max-width: 100% !important;
  width: 100% !important;
  margin: 0 !important;
  background: transparent !important;
}}
footer {{
  justify-content: center !important;
  background: transparent !important;
}}

/* Layout largo: laterais maiores + centro */
.cv-layout {{
  align-items: flex-start !important;
  gap: 1rem !important;
  width: 100% !important;
}}
.cv-side {{
  flex: 0 0 280px !important;
  min-width: 260px !important;
  max-width: 320px !important;
}}
.cv-main {{
  flex: 1 1 auto !important;
  min-width: 0 !important;
}}
.cv-side-panel {{
  background: linear-gradient(180deg, #e8f4f8 0%, {COLOR_OFFWHITE} 55%, #e9f5ef 100%);
  border: 1px solid {COLOR_BORDER};
  border-radius: 14px;
  padding: 1.15rem 1.1rem 1.25rem;
  box-shadow: 0 4px 16px rgba(0, 92, 168, 0.08);
  position: sticky;
  top: 0.75rem;
}}
.cv-side-panel h3 {{
  margin: 1rem 0 0.5rem 0;
  font-size: 0.84rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: {COLOR_AZUL_MARCA};
  font-weight: 700;
}}
.cv-side-panel h3:first-child {{ margin-top: 0; }}
.cv-side-list {{
  margin: 0;
  padding-left: 1.15rem;
  color: {COLOR_AZUL_ESCURO};
  font-size: 0.9rem;
  line-height: 1.5;
}}
.cv-side-list.plain {{
  list-style: none;
  padding-left: 0;
}}
.cv-side-list.plain li {{
  padding: 0.28rem 0;
  border-bottom: 1px dashed {COLOR_BORDER};
}}
.cv-side-text {{
  margin: 0;
  color: {COLOR_MUTED};
  font-size: 0.88rem;
  line-height: 1.5;
}}
.cv-side-link {{
  margin: 0.75rem 0 0 0;
  font-size: 0.9rem;
}}
.cv-side-link a {{
  color: {COLOR_AZUL_MARCA};
  font-weight: 600;
  text-decoration: none;
}}
.cv-side-link a:hover {{ text-decoration: underline; }}
.cv-legend {{
  list-style: none;
  margin: 0;
  padding: 0;
  font-size: 0.88rem;
  color: {COLOR_AZUL_ESCURO};
}}
.cv-legend li {{
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin-bottom: 0.45rem;
}}
.cv-badge {{
  display: inline-block;
  padding: 0.18rem 0.5rem;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 700;
  white-space: nowrap;
}}
.cv-badge-ok {{ background: #d7f0e5; color: {COLOR_VERDE_MARCA}; }}
.cv-badge-parcial {{ background: #eef7d4; color: #5f7d12; }}
.cv-badge-nao {{ background: #fde2e2; color: #9b1c1c; }}
.cv-icon-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.4rem;
  margin: 0.35rem 0 0.25rem 0;
}}
.cv-icon-tile {{
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid {COLOR_AZUL_CLARO};
  border-radius: 6px;
  color: {COLOR_AZUL_MARCA};
  background: rgba(255,255,255,0.55);
}}
@media (max-width: 1200px) {{
  .cv-side {{
    flex-basis: 220px !important;
    min-width: 200px !important;
    max-width: 240px !important;
  }}
}}
@media (max-width: 980px) {{
  .cv-side {{ display: none !important; }}
}}

.cv-hero {{
  position: relative;
  overflow: hidden;
  background: {RIVER_GRADIENT};
  color: #fff;
  border-radius: 14px;
  padding: 1.35rem 1.6rem 1.55rem;
  margin: 0 auto 1rem auto;
  text-align: center;
  box-shadow: 0 10px 28px rgba(0, 92, 168, 0.28);
  border: 1px solid rgba(255,255,255,0.10);
}}
.cv-hero::after {{
  content: "";
  position: absolute;
  left: 0; right: 0; bottom: -2px;
  height: 28px;
  background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 40' preserveAspectRatio='none'%3E%3Cpath d='M0 20 Q150 0 300 20 T600 20 T900 20 T1200 20 V40 H0 Z' fill='rgba(255,255,255,0.14)'/%3E%3C/svg%3E") repeat-x bottom;
  background-size: 600px 28px;
  pointer-events: none;
}}
.cv-logo {{
  display: block;
  height: 52px;
  width: auto;
  margin: 0 auto 0.9rem auto;
  border-radius: 6px;
  box-shadow: 0 4px 14px rgba(0,0,0,0.18);
}}
.cv-hero-kicker {{
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.92;
  margin: 0 0 0.35rem 0;
  font-weight: 600;
}}
.cv-hero h1 {{
  font-size: 1.55rem;
  line-height: 1.25;
  margin: 0 auto 0.35rem auto;
  font-weight: 700;
  color: #fff !important;
  max-width: 36rem;
}}
.cv-hero p {{
  margin: 0 auto;
  opacity: 0.95;
  font-size: 0.98rem;
  max-width: 40rem;
}}
.cv-steps {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
  margin: 0 auto 1.1rem auto;
  max-width: 960px;
}}
.cv-step {{
  background: #fff;
  border: 1px solid {COLOR_BORDER};
  border-radius: 12px;
  padding: 0.85rem 1rem;
  box-shadow: 0 2px 8px rgba(0, 92, 168, 0.06);
  text-align: center;
}}
.cv-step-num {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.55rem;
  height: 1.55rem;
  border-radius: 999px;
  background: {COLOR_AZUL_MARCA};
  color: #fff;
  font-size: 0.8rem;
  font-weight: 700;
  margin: 0 0.4rem 0 0;
  vertical-align: middle;
}}
.cv-step strong {{ color: {COLOR_AZUL_ESCURO}; font-size: 0.95rem; }}
.cv-step span {{
  display: block;
  margin-top: 0.25rem;
  color: {COLOR_MUTED};
  font-size: 0.84rem;
}}
.cv-footer-note {{
  margin-top: 1.25rem;
  padding-top: 0.85rem;
  border-top: 1px solid {COLOR_BORDER};
  color: {COLOR_MUTED};
  font-size: 0.82rem;
  text-align: center;
}}

/* Cards de download — fundo institucional e rótulos alinhados */
.cv-downloads {{
  gap: 0.75rem !important;
  align-items: stretch !important;
}}
.cv-downloads > * {{
  flex: 1 1 0 !important;
  min-width: 0 !important;
}}
.cv-download,
.cv-download > .block,
.cv-download .wrap,
.cv-download .empty,
.cv-download .file-preview,
.cv-download [data-testid="file"],
.cv-download .upload-container {{
  background: linear-gradient(180deg, #e8f4f8 0%, {COLOR_OFFWHITE} 100%) !important;
  border-color: {COLOR_BORDER} !important;
  height: 100% !important;
}}
.cv-download .label-wrap,
.cv-download label {{
  color: {COLOR_AZUL_ESCURO} !important;
  font-weight: 600 !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  min-height: 1.6rem !important;
}}
.cv-download .icon,
.cv-download svg {{
  color: {COLOR_AZUL_MARCA} !important;
  opacity: 0.55;
}}

@media (max-width: 900px) {{
  .cv-steps {{ grid-template-columns: 1fr; }}
  .cv-hero h1 {{ font-size: 1.3rem; }}
  .cv-logo {{ height: 42px; }}
}}
"""


def gradio_theme():
    """Tema Gradio com paleta oficial do manual Codevasf."""
    import gradio as gr

    return gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="green",
        neutral_hue="slate",
        font=[gr.themes.GoogleFont("IBM Plex Sans"), "Rawline", "Segoe UI", "sans-serif"],
    ).set(
        body_background_fill="#e8f4f0",
        body_background_fill_dark="#e8f4f0",
        block_background_fill="#ffffff",
        block_border_color=COLOR_BORDER,
        block_label_text_color=COLOR_AZUL_ESCURO,
        block_title_text_color=COLOR_AZUL_ESCURO,
        border_color_primary=COLOR_BORDER,
        button_primary_background_fill=COLOR_VERDE_MARCA,
        button_primary_background_fill_hover=COLOR_AZUL_MARCA,
        button_primary_background_fill_dark=COLOR_VERDE_MARCA,
        button_primary_background_fill_hover_dark=COLOR_AZUL_MARCA,
        button_primary_text_color="#ffffff",
        button_primary_text_color_dark="#ffffff",
        button_secondary_background_fill="#ffffff",
        button_secondary_border_color=COLOR_AZUL_MARCA,
        button_secondary_text_color=COLOR_AZUL_MARCA,
        input_border_color=COLOR_BORDER,
        input_background_fill="#ffffff",
        checkbox_label_background_fill_selected=COLOR_AZUL,
        checkbox_background_color_selected=COLOR_AZUL_MARCA,
        slider_color=COLOR_VERDE,
    )
