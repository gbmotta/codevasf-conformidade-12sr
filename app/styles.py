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
  height: 120px;
  width: auto;
  max-width: min(560px, 95%);
  object-fit: contain;
  margin: 0 auto 1.1rem auto;
  border-radius: 8px;
  box-shadow: 0 6px 18px rgba(0,0,0,0.22);
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
  .cv-logo {{ height: 88px; }}
}}
</style>
"""


def render_hero(subtitle: str | None = None) -> str:
    """Cabeçalho compacto do sistema institucional."""
    body = subtitle or (
        "Verificação assistida de documentos para doação e concessão "
        "de bens móveis."
    )

    logo = logo_data_uri()
    logo_html = (
        f'<img class="cv-app-logo" src="{logo}" alt="Codevasf" />'
        if logo
        else '<strong class="cv-app-logo-fallback">CODEVASF</strong>'
    )

    return f"""
<header class="cv-app-header">
  <div class="cv-app-header-main">
    <div class="cv-app-brand">
      {logo_html}

      <div class="cv-app-identification">
        <span class="cv-app-institution">
          Companhia de Desenvolvimento dos Vales do São Francisco e do Parnaíba
        </span>

        <h1>Análise de Conformidade Documental</h1>

        <p>
          12ª Superintendência Regional · Natal/RN
        </p>
      </div>
    </div>

    <div class="cv-app-status" aria-label="Característica do sistema">
      <span class="cv-app-status-dot"></span>
      Sistema assistivo
    </div>
  </div>

  <div class="cv-app-description">
    <span>{body}</span>

    <span class="cv-app-description-alert">
      A decisão final permanece com a equipe técnica.
    </span>
  </div>
</header>
"""


def render_steps() -> str:
    """Fluxo resumido e compacto da atividade."""
    return """
<nav class="cv-workflow" aria-label="Etapas da análise">
  <div class="cv-workflow-item">
    <span class="cv-workflow-number">1</span>
    <span class="cv-workflow-content">
      <strong>Envio</strong>
      <small>Tipo e documentos</small>
    </span>
  </div>

  <span class="cv-workflow-line"></span>

  <div class="cv-workflow-item">
    <span class="cv-workflow-number">2</span>
    <span class="cv-workflow-content">
      <strong>Leitura</strong>
      <small>Extração e regras</small>
    </span>
  </div>

  <span class="cv-workflow-line"></span>

  <div class="cv-workflow-item">
    <span class="cv-workflow-number">3</span>
    <span class="cv-workflow-content">
      <strong>Análise</strong>
      <small>Validação assistida</small>
    </span>
  </div>

  <span class="cv-workflow-line"></span>

  <div class="cv-workflow-item">
    <span class="cv-workflow-number">4</span>
    <span class="cv-workflow-content">
      <strong>Revisão</strong>
      <small>Conferência e relatório</small>
    </span>
  </div>
</nav>
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
    <li><span class="cv-badge cv-badge-ok">Atendido</span> Documento Ok</li>
    <li><span class="cv-badge cv-badge-parcial">Parcial</span> Incompleto / Dúvida</li>
    <li><span class="cv-badge cv-badge-nao">Não Atendido</span> Ausente</li>
  </ul>
  <h3>Como a análise funciona</h3>
  <ul class="cv-side-list">
    <li>Regras pelo nome e conteúdo dos arquivos</li>
    <li>IA só nos itens em dúvida</li>
    <li>Você pode ajustar o status depois</li>
  </ul>
  <h3>Exportação</h3>
  <ul class="cv-side-list plain">
    <li>Texto (.md) — Leitura Rápida</li>
    <li>Excel (.xlsx) — Planilha</li>
    <li>Word (.docx) — Edição</li>
    <li>PDF (.pdf) — Arquivo Oficial</li>
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
  max-width: 1600px !important;
  width: 100% !important;
  margin: 0 auto !important;
  padding: 0.85rem 1rem 1.5rem !important;
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

/*
 * Layout em CSS Grid (3 colunas fixas).
 * Evita o flex-wrap do Gradio que deslocava as laterais após a análise,
 * e evita position:fixed que sobrepunha o centro.
 */
.cv-layout {{
  display: grid !important;
  grid-template-columns: 260px minmax(0, 1fr) 260px !important;
  gap: 1rem !important;
  align-items: start !important;
  width: 100% !important;
  flex-wrap: nowrap !important;
}}
.cv-layout > div {{
  min-width: 0 !important;
  max-width: 100% !important;
}}
/* Garante ordem mesmo se o Gradio inserir wrappers extras */
.cv-layout > .cv-side:first-of-type,
.cv-layout .cv-side:first-child {{
  grid-column: 1 !important;
}}
.cv-layout > .cv-main,
.cv-layout .cv-main {{
  grid-column: 2 !important;
}}
.cv-layout > .cv-side:last-of-type {{
  grid-column: 3 !important;
}}
.cv-side {{
  position: sticky !important;
  top: 0.75rem !important;
  align-self: start !important;
  width: 100% !important;
  max-height: calc(100vh - 1.25rem) !important;
  overflow-x: hidden !important;
  overflow-y: auto !important;
}}
.cv-main {{
  min-width: 0 !important;
  width: 100% !important;
  overflow-x: auto !important;
  grid-column: 2 !important;
}}
.cv-resultado,
.cv-editor {{
  max-width: 100% !important;
}}

/* Bloco central: tipo + ZIP */
.cv-section-title {{
  text-align: center;
  margin: 0.35rem auto 0.85rem auto;
  max-width: 36rem;
}}
.cv-section-title h2 {{
  margin: 0 0 0.3rem 0;
  font-size: 1.15rem;
  font-weight: 700;
  color: {COLOR_AZUL_ESCURO};
}}
.cv-section-title p {{
  margin: 0;
  font-size: 0.9rem;
  color: {COLOR_MUTED};
  line-height: 1.4;
}}
.cv-input-row {{
  display: grid !important;
  grid-template-columns: 1fr 1fr !important;
  gap: 1rem !important;
  align-items: stretch !important;
  max-width: 820px !important;
  margin: 0 auto 1rem auto !important;
  width: 100% !important;
}}
.cv-input-row > div {{
  min-width: 0 !important;
  height: 100% !important;
}}
.cv-input-card {{
  background: linear-gradient(180deg, #e8f4f8 0%, {COLOR_OFFWHITE} 100%) !important;
  border: 1px solid {COLOR_BORDER} !important;
  border-radius: 14px !important;
  padding: 0.85rem 0.9rem 1rem !important;
  box-shadow: 0 3px 12px rgba(0, 92, 168, 0.07) !important;
  height: 100% !important;
}}
.cv-input-card label,
.cv-input-card .label-wrap span {{
  color: {COLOR_AZUL_ESCURO} !important;
  font-weight: 700 !important;
  justify-content: center !important;
  text-align: center !important;
  width: 100% !important;
}}
.cv-tipo-radio {{
  display: flex !important;
  flex-direction: column !important;
  align-items: stretch !important;
  gap: 0.55rem !important;
}}
.cv-tipo-radio .wrap {{
  display: flex !important;
  flex-direction: column !important;
  gap: 0.55rem !important;
  align-items: stretch !important;
}}
.cv-tipo-radio label {{
  border: 1px solid {COLOR_BORDER} !important;
  border-radius: 10px !important;
  padding: 0.65rem 0.85rem !important;
  background: #fff !important;
  margin: 0 !important;
}}
.cv-zip-upload,
.cv-zip-upload .wrap,
.cv-zip-upload .upload-container,
.cv-zip-upload .center {{
  min-height: 160px !important;
  height: 100% !important;
  border-radius: 10px !important;
  background: rgba(255,255,255,0.75) !important;
  border: 1px dashed {COLOR_AZUL_CLARO} !important;
}}
.cv-btn-analisar {{
  max-width: 820px !important;
  margin: 0 auto 1rem auto !important;
  display: block !important;
  width: 100% !important;
}}
@media (max-width: 700px) {{
  .cv-input-row {{
    grid-template-columns: 1fr !important;
  }}
}}

/* Progresso por etapas */
.cv-progress {{
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  flex-wrap: wrap;
  margin: 0.5rem auto 1rem auto;
  max-width: 720px;
}}
.cv-progress-step {{
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 600;
  border: 1px solid {COLOR_BORDER};
  background: #fff;
  color: {COLOR_MUTED};
}}
.cv-progress-step.active {{
  background: {COLOR_AZUL_MARCA};
  border-color: {COLOR_AZUL_MARCA};
  color: #fff;
}}
.cv-progress-step.done {{
  background: #d7f0e5;
  border-color: {COLOR_VERDE_MARCA};
  color: {COLOR_VERDE_MARCA};
}}
.cv-progress-num {{
  display: inline-flex;
  width: 1.25rem;
  height: 1.25rem;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: rgba(0,0,0,0.08);
  font-size: 0.75rem;
}}
.cv-progress-step.active .cv-progress-num {{
  background: rgba(255,255,255,0.25);
}}
.cv-progress-sep {{
  width: 1.1rem;
  height: 2px;
  background: {COLOR_BORDER};
}}

/* Cards de resumo */
.cv-resumo {{
  margin: 0.5rem 0 1rem 0;
}}
.cv-resumo-head {{
  text-align: center;
  margin-bottom: 0.65rem;
}}
.cv-resumo-head strong {{
  display: block;
  color: {COLOR_AZUL_ESCURO};
  font-size: 1.05rem;
}}
.cv-resumo-head span {{
  color: {COLOR_MUTED};
  font-size: 0.88rem;
}}
.cv-cards {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
  max-width: 720px;
  margin: 0 auto;
}}
.cv-card-stat {{
  text-align: center;
  border-radius: 14px;
  padding: 0.9rem 0.5rem;
  border: 1px solid {COLOR_BORDER};
  background: #fff;
}}
.cv-card-stat.ok {{ background: #eaf8f0; border-color: #b7e4c7; }}
.cv-card-stat.parcial {{ background: #f7f9e8; border-color: #d8e59a; }}
.cv-card-stat.nao {{ background: #fdeced; border-color: #f5c2c7; }}
.cv-card-num {{
  display: block;
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.1;
  color: {COLOR_AZUL_ESCURO};
}}
.cv-card-stat.ok .cv-card-num {{ color: {COLOR_VERDE_MARCA}; }}
.cv-card-stat.parcial .cv-card-num {{ color: #5f7d12; }}
.cv-card-stat.nao .cv-card-num {{ color: #9b1c1c; }}
.cv-card-label {{
  font-size: 0.85rem;
  font-weight: 600;
  color: {COLOR_MUTED};
}}

/* Inventário */
.cv-inventory {{
  margin: 0.75rem 0 1rem 0;
  background: linear-gradient(180deg, #e8f4f8 0%, {COLOR_OFFWHITE} 100%);
  border: 1px solid {COLOR_BORDER};
  border-radius: 14px;
  padding: 0.85rem 1rem;
}}
.cv-inventory h3 {{
  margin: 0 0 0.55rem 0;
  font-size: 0.95rem;
  color: {COLOR_AZUL_ESCURO};
}}
.cv-inventory ul {{
  list-style: none;
  margin: 0;
  padding: 0;
}}
.cv-inventory li {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem;
  padding: 0.35rem 0;
  border-bottom: 1px dashed {COLOR_BORDER};
  font-size: 0.86rem;
}}
.cv-inventory li:last-child {{ border-bottom: none; }}
.cv-inv-kind {{
  display: inline-block;
  min-width: 2.4rem;
  text-align: center;
  padding: 0.1rem 0.35rem;
  border-radius: 6px;
  background: {COLOR_AZUL_MARCA};
  color: #fff;
  font-size: 0.72rem;
  font-weight: 700;
}}
.cv-inv-name {{
  flex: 1 1 12rem;
  color: {COLOR_AZUL_ESCURO};
  word-break: break-all;
}}
.cv-inv-badge {{
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
  background: #e2eef6;
  color: {COLOR_AZUL_MARCA};
}}
.cv-inv-badge.ocr {{
  background: #fff1d6;
  color: #8a5a00;
}}
.cv-inv-badge.type-fgts {{ background: #e3f2fd; color: #0d47a1; }}
.cv-inv-badge.type-federal {{ background: #e8eaf6; color: #283593; }}
.cv-inv-badge.type-cndt {{ background: #f3e5f5; color: #6a1b9a; }}
.cv-inv-badge.type-impedimento {{ background: #fce4ec; color: #880e4f; }}
.cv-inv-badge.type-doacao_onerosa {{ background: #e8f5e9; color: #1b5e20; }}
.cv-inv-badge.type-oficio {{ background: #e0f2f1; color: #00695c; }}
.cv-inv-badge.type-cnpj {{ background: #fff8e1; color: #f57f17; }}
.cv-inv-badge.val-vencida {{ background: #fde2e2; color: #9b1c1c; }}
.cv-inv-badge.val-avencer {{ background: #fff3cd; color: #856404; }}
.cv-inv-badge.val-ok {{ background: #d7f0e5; color: #0b6b3a; }}
.cv-validade-alerts {{
  margin: 0.75rem 0 1rem;
  padding: 0.85rem 1rem;
  border-radius: 10px;
  border: 1px solid #f0d78c;
  background: #fffbeb;
}}
.cv-validade-alerts h3 {{ margin: 0 0 0.5rem; font-size: 0.95rem; color: #856404; }}
.cv-validade-vencida {{ color: #9b1c1c; }}
.cv-validade-a-vencer {{ color: #856404; }}
.cv-inv-meta {{
  color: {COLOR_MUTED};
  font-size: 0.78rem;
}}

.cv-exemplo-row {{
  max-width: 820px !important;
  margin: 0 auto 0.85rem auto !important;
}}
.cv-btn-nova {{
  max-width: 220px !important;
  margin-bottom: 0.75rem !important;
}}
.cv-badge {{
  display: inline-block;
  padding: 0.18rem 0.5rem;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 700;
}}
.cv-badge-ok {{ background: #d7f0e5; color: {COLOR_VERDE_MARCA}; }}
.cv-badge-parcial {{ background: #eef7d4; color: #5f7d12; }}
.cv-badge-nao {{ background: #fde2e2; color: #9b1c1c; }}

@media (max-width: 700px) {{
  .cv-cards {{ grid-template-columns: 1fr; }}
}}
.cv-side-panel {{
  background: linear-gradient(180deg, #e8f4f8 0%, {COLOR_OFFWHITE} 55%, #e9f5ef 100%);
  border: 1px solid {COLOR_BORDER};
  border-radius: 14px;
  padding: 1rem 0.95rem 1.1rem;
  box-shadow: 0 4px 16px rgba(0, 92, 168, 0.08);
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
@media (max-width: 1100px) {{
  .cv-layout {{
    grid-template-columns: 1fr !important;
  }}
  .cv-side {{
    display: none !important;
  }}
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
  height: 120px;
  width: auto;
  max-width: min(560px, 95%);
  object-fit: contain;
  margin: 0 auto 1.1rem auto;
  border-radius: 8px;
  box-shadow: 0 6px 18px rgba(0,0,0,0.22);
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
  .cv-logo {{ height: 88px; }}
}}
"""

GRADIO_CSS += r"""
/* ==========================================================
   NOVO LAYOUT INSTITUCIONAL — CODEVASF 12ª SR
   Sobrescrita final das regras anteriores
   ========================================================== */

/* ---------- Estrutura geral ---------- */

html,
body,
.gradio-container,
body.gradio-container,
.main,
.app,
.contain {
  background: #f4f6f8 !important;
}

body {
  color: #1f2937 !important;
}

.gradio-container {
  width: 100% !important;
  max-width: 1320px !important;
  min-height: 100vh !important;
  margin: 0 auto !important;
  padding: 1rem 1.5rem 2rem !important;
  box-sizing: border-box !important;
}

/*
 * O app ainda possui as duas colunas laterais no Python.
 * Neste primeiro momento elas serão ocultadas por CSS.
 */
.cv-layout {
  display: grid !important;
  grid-template-columns: minmax(0, 1fr) !important;
  width: 100% !important;
  max-width: 100% !important;
  gap: 0 !important;
  align-items: start !important;
}

.cv-layout > .cv-side,
.cv-layout .cv-side {
  display: none !important;
}

.cv-layout > .cv-main,
.cv-layout .cv-main,
.cv-main {
  display: block !important;
  grid-column: 1 !important;
  width: 100% !important;
  max-width: 1180px !important;
  min-width: 0 !important;
  margin: 0 auto !important;
  overflow: visible !important;
}

/* ---------- Cabeçalho institucional ---------- */

.cv-hero {
  display: none !important;
}

.cv-app-header {
  overflow: hidden;
  margin: 0 0 0.85rem;
  background: #ffffff;
  border: 1px solid #d7dee5;
  border-top: 5px solid #005ca8;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(31, 41, 55, 0.06);
}

.cv-app-header-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  padding: 1rem 1.25rem 0.9rem;
}

.cv-app-brand {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 1.15rem;
}

.cv-app-logo {
  display: block;
  flex: 0 0 auto;
  width: auto;
  height: 52px;
  max-width: 230px;
  margin: 0;
  padding: 0;
  object-fit: contain;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.cv-app-logo-fallback {
  display: inline-flex;
  align-items: center;
  min-height: 48px;
  padding: 0.4rem 0.75rem;
  background: #005ca8;
  color: #ffffff;
  font-size: 1.1rem;
  letter-spacing: 0.03em;
}

.cv-app-identification {
  min-width: 0;
  padding-left: 1.15rem;
  border-left: 1px solid #d7dee5;
}

.cv-app-institution {
  display: block;
  overflow: hidden;
  margin-bottom: 0.15rem;
  color: #5f6b7a;
  font-size: 0.71rem;
  font-weight: 600;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cv-app-identification h1 {
  margin: 0 !important;
  color: #222b54 !important;
  font-size: clamp(1.25rem, 2vw, 1.65rem) !important;
  font-weight: 700 !important;
  line-height: 1.2 !important;
}

.cv-app-identification p {
  margin: 0.25rem 0 0 !important;
  color: #4b5d70 !important;
  font-size: 0.88rem !important;
}

.cv-app-status {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 0.45rem;
  padding: 0.45rem 0.7rem;
  border: 1px solid #b7e0cd;
  border-radius: 999px;
  background: #edf8f3;
  color: #006b43;
  font-size: 0.78rem;
  font-weight: 700;
  white-space: nowrap;
}

.cv-app-status-dot {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 999px;
  background: #008658;
  box-shadow: 0 0 0 3px rgba(0, 134, 88, 0.12);
}

.cv-app-description {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.65rem 1.25rem;
  border-top: 1px solid #e4e9ee;
  background: #f8fafb;
  color: #536273;
  font-size: 0.82rem;
  line-height: 1.4;
}

.cv-app-description-alert {
  color: #005ca8;
  font-weight: 600;
  white-space: nowrap;
}

/* ---------- Fluxo compacto ---------- */

.cv-steps {
  display: none !important;
}

.cv-workflow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  margin: 0 0 0.85rem;
  padding: 0.75rem 1rem;
  box-sizing: border-box;
  background: #ffffff;
  border: 1px solid #d7dee5;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(31, 41, 55, 0.04);
}

.cv-workflow-item {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  gap: 0.55rem;
}

.cv-workflow-number {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border: 1px solid #a9cbe1;
  border-radius: 999px;
  background: #edf5fa;
  color: #005ca8;
  font-size: 0.78rem;
  font-weight: 700;
}

.cv-workflow-content {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.cv-workflow-content strong {
  color: #27364a;
  font-size: 0.82rem;
  line-height: 1.2;
}

.cv-workflow-content small {
  margin-top: 0.1rem;
  color: #738092;
  font-size: 0.7rem;
  line-height: 1.2;
  white-space: nowrap;
}

.cv-workflow-line {
  flex: 1 1 3rem;
  max-width: 6rem;
  min-width: 1.5rem;
  height: 1px;
  margin: 0 0.8rem;
  background: #cfd8e2;
}

/* ---------- Acordeão de status ---------- */

.cv-main .gradio-accordion,
.cv-main .accordion {
  margin-bottom: 0.8rem !important;
  overflow: hidden !important;
  border: 1px solid #d7dee5 !important;
  border-radius: 8px !important;
  background: #ffffff !important;
  box-shadow: none !important;
}

.cv-audit-accordion {
  margin-top: 0.5rem !important;
  opacity: 0.92;
}

.cv-audit-intro {
  margin: 0 0 0.75rem;
  padding: 0.65rem 0.8rem;
  border-left: 3px solid #7a8a96;
  background: #f4f6f8;
  color: #4a5a66;
  font-size: 0.88rem;
  line-height: 1.45;
}

.cv-audit-log {
  max-height: 28rem;
  overflow: auto;
  font-size: 0.9rem;
}

/* ---------- Área de envio ---------- */

.cv-painel-envio {
  padding: 1.25rem !important;
  border: 1px solid #d7dee5 !important;
  border-radius: 10px !important;
  background: #ffffff !important;
  box-shadow: 0 2px 8px rgba(31, 41, 55, 0.05) !important;
}

.cv-section-title {
  max-width: 100% !important;
  margin: 0 0 1rem !important;
  text-align: left !important;
}

.cv-section-title h2 {
  margin: 0 0 0.25rem !important;
  color: #222b54 !important;
  font-size: 1.15rem !important;
  font-weight: 700 !important;
}

.cv-section-title p {
  margin: 0 !important;
  color: #667386 !important;
  font-size: 0.88rem !important;
}

.cv-input-row {
  display: grid !important;
  grid-template-columns: minmax(280px, 0.8fr) minmax(380px, 1.2fr) !important;
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 0 1rem !important;
  gap: 1rem !important;
  align-items: stretch !important;
}

.cv-input-card {
  height: 100% !important;
  padding: 1rem !important;
  box-sizing: border-box !important;
  border: 1px solid #dbe3ea !important;
  border-radius: 8px !important;
  background: #f8fafb !important;
  box-shadow: none !important;
}

.cv-input-card label,
.cv-input-card .label-wrap span {
  justify-content: flex-start !important;
  color: #27364a !important;
  text-align: left !important;
  font-size: 0.86rem !important;
  font-weight: 700 !important;
}

.cv-tipo-radio,
.cv-tipo-radio .wrap {
  display: flex !important;
  flex-direction: column !important;
  gap: 0.5rem !important;
}

.cv-tipo-radio label {
  margin: 0 !important;
  padding: 0.65rem 0.75rem !important;
  border: 1px solid #d7dee5 !important;
  border-radius: 7px !important;
  background: #ffffff !important;
  color: #344256 !important;
  transition:
    border-color 120ms ease,
    background-color 120ms ease;
}

.cv-tipo-radio label:hover {
  border-color: #74aeda !important;
  background: #f3f8fc !important;
}

.cv-zip-upload,
.cv-zip-upload .wrap,
.cv-zip-upload .upload-container,
.cv-zip-upload .center {
  min-height: 150px !important;
  height: 100% !important;
  border: 1px dashed #8abbd8 !important;
  border-radius: 8px !important;
  background: #ffffff !important;
}

.cv-btn-analisar {
  display: block !important;
  width: 100% !important;
  max-width: 100% !important;
  min-height: 44px !important;
  margin: 0 !important;
  border-radius: 7px !important;
  font-size: 0.95rem !important;
  font-weight: 700 !important;
}

/* ---------- Progresso ---------- */

.cv-progress-wrap {
  margin: 0 !important;
}

.cv-progress {
  width: 100%;
  max-width: 760px;
  margin: 0.8rem auto;
  gap: 0.4rem;
}

.cv-progress-step {
  min-height: 30px;
  padding: 0.35rem 0.7rem;
  border: 1px solid #d4dce5;
  border-radius: 999px;
  background: #ffffff;
  color: #657184;
  font-size: 0.78rem;
}

.cv-progress-step.active {
  border-color: #005ca8;
  background: #005ca8;
  color: #ffffff;
}

.cv-progress-step.done {
  border-color: #9dd1b9;
  background: #e9f7f0;
  color: #007d4e;
}

.cv-progress-sep {
  background: #ccd6df;
}

/* ---------- Área de resultado ---------- */

.cv-painel-resultado {
  padding: 1.25rem !important;
  border: 1px solid #d7dee5 !important;
  border-radius: 10px !important;
  background: #ffffff !important;
  box-shadow: 0 2px 8px rgba(31, 41, 55, 0.05) !important;
}

.cv-btn-nova {
  width: auto !important;
  max-width: 190px !important;
  margin: 0 0 0.85rem !important;
  border-color: #b9c5d1 !important;
  color: #344256 !important;
}

/* ---------- Resumo ---------- */

.cv-resumo {
  margin: 0 0 1.25rem;
}

.cv-resumo-head {
  margin-bottom: 0.75rem;
  text-align: left;
}

.cv-resumo-head strong {
  color: #222b54;
  font-size: 1.12rem;
}

.cv-resumo-head span {
  display: block;
  margin-top: 0.15rem;
  color: #687589;
  font-size: 0.84rem;
}

.cv-cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  width: 100%;
  max-width: 100%;
  margin: 0;
  gap: 0.75rem;
}

.cv-card-stat {
  min-height: 92px;
  padding: 0.9rem;
  text-align: left;
  border: 1px solid #d7dee5;
  border-left-width: 4px;
  border-radius: 8px;
  background: #ffffff;
}

.cv-card-stat.ok {
  border-color: #b9dfcc;
  border-left-color: #007d4e;
  background: #f4fbf7;
}

.cv-card-stat.parcial {
  border-color: #dbe4a6;
  border-left-color: #809e20;
  background: #fbfcef;
}

.cv-card-stat.nao {
  border-color: #efc4c4;
  border-left-color: #b42318;
  background: #fff7f6;
}

.cv-card-num {
  margin-bottom: 0.25rem;
  font-size: 1.8rem;
  line-height: 1;
}

.cv-card-label {
  color: #536173;
  font-size: 0.8rem;
}

/* ---------- Detalhamento Markdown ---------- */

.cv-resultado {
  overflow: visible !important;
  padding: 0 !important;
}

.cv-resultado h2 {
  margin: 1.4rem 0 0.35rem !important;
  color: #222b54 !important;
  font-size: 1.25rem !important;
}

.cv-resultado > div > p,
.cv-resultado p {
  color: #4b596c;
  line-height: 1.55;
}

.cv-resultado h3 {
  margin: 1rem 0 0 !important;
  padding: 0.85rem 1rem !important;
  border: 1px solid #dbe3ea !important;
  border-bottom: 0 !important;
  border-radius: 8px 8px 0 0 !important;
  background: #f7f9fb !important;
  color: #27364a !important;
  font-size: 0.95rem !important;
  line-height: 1.45 !important;
}

.cv-resultado h3 + p {
  margin: 0 !important;
  padding: 0.8rem 1rem 0.35rem !important;
  border-right: 1px solid #dbe3ea !important;
  border-left: 1px solid #dbe3ea !important;
  background: #ffffff !important;
}

.cv-resultado h3 + p + p {
  margin: 0 0 0.75rem !important;
  padding: 0.15rem 1rem 0.85rem !important;
  border-right: 1px solid #dbe3ea !important;
  border-bottom: 1px solid #dbe3ea !important;
  border-left: 1px solid #dbe3ea !important;
  border-radius: 0 0 8px 8px !important;
  background: #ffffff !important;
}

.cv-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.18rem 0.48rem;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 700;
  line-height: 1.2;
  white-space: nowrap;
}

.cv-badge-ok {
  background: #dff4e9;
  color: #006b43;
}

.cv-badge-parcial {
  background: #eff5ce;
  color: #627b12;
}

.cv-badge-nao {
  background: #fee4e2;
  color: #b42318;
}

/* ---------- Inventário ---------- */

.cv-inventory {
  margin: 1.25rem 0;
  padding: 0;
  overflow: hidden;
  border: 1px solid #d7dee5;
  border-radius: 8px;
  background: #ffffff;
}

.cv-inventory h3 {
  margin: 0;
  padding: 0.8rem 1rem;
  border-bottom: 1px solid #d7dee5;
  background: #f7f9fb;
  color: #27364a;
  font-size: 0.95rem;
}

.cv-inventory ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.cv-inventory li {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr) auto auto;
  align-items: center;
  min-height: 44px;
  padding: 0.55rem 1rem;
  gap: 0.75rem;
  border-bottom: 1px solid #e5e9ee;
  font-size: 0.82rem;
  line-height: 1.2;
  box-sizing: border-box;
}

.cv-inventory li:last-child {
  border-bottom: 0;
}

.cv-inv-kind {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  align-self: center;
  min-width: 2.6rem;
  height: 1.45rem;
  padding: 0 0.4rem;
  border-radius: 4px;
  background: #005ca8;
  color: #ffffff;
  font-size: 0.66rem;
  font-weight: 700;
  line-height: 1;
}

.cv-inv-name {
  display: block;
  overflow: hidden;
  align-self: center;
  color: #344256;
  text-overflow: ellipsis;
  white-space: nowrap;
  word-break: normal;
  line-height: 1.3;
}

.cv-inv-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  align-self: center;
  height: 1.45rem;
  padding: 0 0.55rem;
  border-radius: 999px;
  background: #edf3f8;
  color: #005ca8;
  font-size: 0.7rem;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
}

.cv-inv-badge.ocr {
  background: #fff2d7;
  color: #8b5a00;
}

.cv-inv-badge.type-fgts { background: #e3f2fd; color: #0d47a1; }
.cv-inv-badge.type-federal { background: #e8eaf6; color: #283593; }
.cv-inv-badge.type-cndt { background: #f3e5f5; color: #6a1b9a; }
.cv-inv-badge.type-impedimento { background: #fce4ec; color: #880e4f; }
.cv-inv-badge.type-doacao_onerosa { background: #e8f5e9; color: #1b5e20; }
.cv-inv-badge.type-oficio { background: #e0f2f1; color: #00695c; }
.cv-inv-badge.type-cnpj { background: #fff8e1; color: #f57f17; }
.cv-inv-badge.type-outro,
.cv-inv-badge.type-ilegivel { background: #eceff1; color: #455a64; }
.cv-inv-badge.val-vencida { background: #fde2e2; color: #9b1c1c; }
.cv-inv-badge.val-avencer { background: #fff3cd; color: #856404; }
.cv-inv-badge.val-ok { background: #d7f0e5; color: #0b6b3a; }

.cv-validade-alerts {
  margin: 0.75rem 0 1rem;
  padding: 0.85rem 1rem;
  border-radius: 10px;
  border: 1px solid #f0d78c;
  background: #fffbeb;
}
.cv-validade-alerts h3 {
  margin: 0 0 0.5rem;
  font-size: 0.95rem;
  color: #856404;
}
.cv-validade-alerts ul {
  margin: 0;
  padding-left: 1.1rem;
}
.cv-validade-alerts li { margin: 0.25rem 0; font-size: 0.88rem; }
.cv-validade-vencida { color: #9b1c1c; }
.cv-validade-a-vencer { color: #856404; }
.cv-labels-export {
  margin-top: 0.75rem !important;
  gap: 0.75rem !important;
  align-items: center !important;
}
.cv-btn-export-labels {
  max-width: 22rem !important;
}

.cv-inv-meta {
  display: inline-flex;
  align-items: center;
  align-self: center;
  color: #798596;
  font-size: 0.72rem;
  line-height: 1;
  white-space: nowrap;
  min-width: 5.5rem;
  justify-content: flex-end;
}

/* ---------- Revisão humana ---------- */

.cv-rev-item,
.cv-rev-status {
  border-radius: 8px !important;
}

.cv-painel-resultado .form,
.cv-painel-resultado .block {
  box-shadow: none;
}

.cv-painel-resultado textarea,
.cv-painel-resultado input {
  border-color: #cfd8e2 !important;
}

/* ---------- Downloads ---------- */

.cv-downloads {
  display: grid !important;
  grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
  margin-top: 1rem !important;
  gap: 0.65rem !important;
}

.cv-downloads > * {
  min-width: 0 !important;
}

.cv-download,
.cv-download > .block,
.cv-download .wrap,
.cv-download .empty,
.cv-download .file-preview,
.cv-download [data-testid="file"],
.cv-download .upload-container {
  min-height: 76px !important;
  border: 1px solid #d7dee5 !important;
  border-radius: 8px !important;
  background: #f8fafb !important;
  box-shadow: none !important;
}

.cv-downloads > *:last-child .cv-download,
.cv-downloads > *:last-child > div,
.cv-downloads > *:last-child .block {
  border-color: #93cdb3 !important;
  background: #f1faf6 !important;
}

/* ---------- Rodapé ---------- */

.cv-footer-note {
  margin: 1rem 0 0;
  padding: 0.85rem 0.25rem 0;
  border-top: 1px solid #d7dee5;
  color: #748092;
  text-align: center;
  font-size: 0.74rem;
}

/* ---------- Acessibilidade ---------- */

button:focus-visible,
input:focus-visible,
textarea:focus-visible,
select:focus-visible,
[role="button"]:focus-visible {
  outline: 3px solid rgba(0, 92, 168, 0.25) !important;
  outline-offset: 2px !important;
}

button,
[role="button"] {
  transition:
    background-color 120ms ease,
    border-color 120ms ease,
    box-shadow 120ms ease,
    transform 120ms ease !important;
}

button:hover,
[role="button"]:hover {
  box-shadow: 0 2px 7px rgba(31, 41, 55, 0.1) !important;
}

/* ---------- Responsividade ---------- */

@media (max-width: 900px) {
  .gradio-container {
    padding: 0.75rem !important;
  }

  .cv-app-header-main {
    align-items: flex-start;
  }

  .cv-app-logo {
    height: 44px;
    max-width: 180px;
  }

  .cv-app-status {
    display: none;
  }

  .cv-app-description {
    align-items: flex-start;
    flex-direction: column;
    gap: 0.25rem;
  }

  .cv-app-description-alert {
    white-space: normal;
  }

  .cv-input-row {
    grid-template-columns: 1fr !important;
  }

  .cv-downloads {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  }
}

@media (max-width: 680px) {
  .cv-app-header-main {
    padding: 0.9rem;
  }

  .cv-app-brand {
    align-items: flex-start;
    flex-direction: column;
    gap: 0.7rem;
  }

  .cv-app-identification {
    padding-left: 0;
    border-left: 0;
  }

  .cv-app-institution {
    white-space: normal;
  }

  .cv-app-description {
    padding: 0.65rem 0.9rem;
  }

  .cv-workflow {
    align-items: stretch;
    flex-direction: column;
    padding: 0.75rem;
    gap: 0.45rem;
  }

  .cv-workflow-line {
    width: 1px;
    height: 12px;
    min-width: 1px;
    margin: 0 0 0 0.85rem;
  }

  .cv-painel-envio,
  .cv-painel-resultado {
    padding: 0.85rem !important;
  }

  .cv-cards {
    grid-template-columns: 1fr;
  }

  .cv-inventory li {
    grid-template-columns: 42px minmax(0, 1fr);
  }

  .cv-inv-badge,
  .cv-inv-meta {
    grid-column: 2;
  }

  .cv-downloads {
    grid-template-columns: 1fr !important;
  }
}
"""

GRADIO_CSS += r"""
/* ==========================================================
   COMPONENTES ADICIONAIS DO NOVO APP.PY
   ========================================================== */

.cv-help-content {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
  padding: 0.4rem 0;
}

.cv-help-card {
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
  min-height: 105px;
  padding: 0.85rem;
  border: 1px solid #dbe3ea;
  border-radius: 8px;
  background: #f8fafb;
}

.cv-help-number {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 1.7rem;
  height: 1.7rem;
  border-radius: 999px;
  background: #005ca8;
  color: #ffffff;
  font-size: 0.75rem;
  font-weight: 700;
}

.cv-help-card strong {
  display: block;
  margin-bottom: 0.25rem;
  color: #27364a;
  font-size: 0.86rem;
}

.cv-help-card p {
  margin: 0;
  color: #657184;
  font-size: 0.78rem;
  line-height: 1.45;
}

.cv-help-note {
  margin-top: 0.75rem;
  padding: 0.7rem 0.85rem;
  border-left: 3px solid #005ca8;
  background: #f2f7fb;
  color: #536173;
  font-size: 0.8rem;
  line-height: 1.5;
}

.cv-upload-guidance {
  margin: 0 0 1rem;
  padding: 0.65rem 0.8rem;
  border: 1px solid #d8e6ef;
  border-radius: 7px;
  background: #f4f9fc;
  color: #566477;
  font-size: 0.79rem;
  line-height: 1.45;
}

.cv-result-toolbar {
  display: grid !important;
  grid-template-columns: auto minmax(0, 1fr) !important;
  align-items: center !important;
  margin-bottom: 1rem !important;
  gap: 1rem !important;
}

.cv-result-toolbar-copy {
  text-align: right;
}

.cv-result-toolbar-copy strong {
  display: block;
  color: #222b54;
  font-size: 1rem;
}

.cv-result-toolbar-copy span {
  display: block;
  margin-top: 0.15rem;
  color: #6a7687;
  font-size: 0.78rem;
}

.cv-review-intro {
  margin-bottom: 0.85rem;
}

.cv-review-intro strong {
  color: #27364a;
  font-size: 0.92rem;
}

.cv-review-intro p {
  margin: 0.25rem 0 0;
  color: #687589;
  font-size: 0.8rem;
  line-height: 1.45;
}

.cv-review-fields {
  align-items: stretch !important;
  gap: 0.75rem !important;
}

.cv-review-actions {
  margin-top: 0.6rem !important;
  gap: 0.75rem !important;
}

.cv-btn-save-review,
.cv-btn-generate-review {
  min-height: 42px !important;
  border-radius: 7px !important;
  font-weight: 700 !important;
}

.cv-export-heading {
  margin: 1.25rem 0 0.75rem;
  padding-top: 1rem;
  border-top: 1px solid #d7dee5;
}

.cv-export-heading h2 {
  margin: 0 0 0.2rem;
  color: #222b54;
  font-size: 1.08rem;
}

.cv-export-heading p {
  margin: 0;
  color: #687589;
  font-size: 0.8rem;
}

.cv-download-primary,
.cv-download-primary > .block,
.cv-download-primary .wrap,
.cv-download-primary .file-preview,
.cv-download-primary .upload-container {
  border-color: #72bb99 !important;
  background: #f0faf5 !important;
}

.cv-download-primary label,
.cv-download-primary .label-wrap span {
  color: #006b43 !important;
  font-weight: 700 !important;
}

.cv-download-technical {
  opacity: 0.82;
}

@media (max-width: 850px) {
  .cv-help-content {
    grid-template-columns: 1fr;
  }

  .cv-help-card {
    min-height: auto;
  }
}

@media (max-width: 620px) {
  .cv-result-toolbar {
    grid-template-columns: 1fr !important;
  }

  .cv-result-toolbar-copy {
    text-align: left;
  }

  .cv-review-fields,
  .cv-review-actions {
    flex-direction: column !important;
  }
}
"""

GRADIO_CSS += r"""
/* Inventário — alinhamento vertical reforçado */
.cv-inventory li {
  display: grid !important;
  grid-template-columns: 48px minmax(0, 1fr) auto auto !important;
  align-items: center !important;
}

.cv-inventory li > * {
  align-self: center !important;
  margin-top: 0 !important;
  margin-bottom: 0 !important;
}

.cv-inv-kind,
.cv-inv-badge,
.cv-inv-meta {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  height: 1.45rem !important;
  line-height: 1 !important;
}

.cv-inv-meta {
  justify-content: flex-end !important;
}

@media (max-width: 680px) {
  .cv-inventory li {
    grid-template-columns: 42px minmax(0, 1fr) !important;
    row-gap: 0.35rem !important;
  }

  .cv-inv-badge,
  .cv-inv-meta {
    grid-column: 2 !important;
    justify-self: start !important;
  }

  .cv-inv-meta {
    justify-content: flex-start !important;
  }
}
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
