"""CSS institucional da interface CODEVASF 12ª SR."""

APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
  font-family: "IBM Plex Sans", "Source Sans 3", "Segoe UI", sans-serif;
}

.stApp {
  background:
    linear-gradient(180deg, #e8f2ec 0%, #f7faf8 220px, #ffffff 420px);
}

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

.cv-hero {
  background: linear-gradient(135deg, #004d29 0%, #006b3f 55%, #0a8f55 100%);
  color: #fff;
  border-radius: 14px;
  padding: 1.35rem 1.6rem 1.45rem;
  margin-bottom: 1.25rem;
  box-shadow: 0 10px 28px rgba(0, 77, 41, 0.22);
  border: 1px solid rgba(255,255,255,0.08);
}

.cv-hero-kicker {
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.85;
  margin: 0 0 0.35rem 0;
  font-weight: 600;
}

.cv-hero h1 {
  font-size: 1.55rem;
  line-height: 1.25;
  margin: 0 0 0.35rem 0;
  font-weight: 700;
  color: #fff !important;
}

.cv-hero p {
  margin: 0;
  opacity: 0.92;
  font-size: 0.98rem;
  max-width: 58rem;
}

.cv-steps {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
  margin: 0 0 1.25rem 0;
}

.cv-step {
  background: #fff;
  border: 1px solid #d5e5db;
  border-radius: 12px;
  padding: 0.85rem 1rem;
  box-shadow: 0 2px 8px rgba(0, 60, 30, 0.04);
}

.cv-step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.55rem;
  height: 1.55rem;
  border-radius: 999px;
  background: #006633;
  color: #fff;
  font-size: 0.8rem;
  font-weight: 700;
  margin-right: 0.45rem;
}

.cv-step strong {
  color: #123525;
  font-size: 0.95rem;
}

.cv-step span {
  display: block;
  margin-top: 0.25rem;
  color: #4b6356;
  font-size: 0.84rem;
}

.cv-card {
  background: #fff;
  border: 1px solid #d7e4dc;
  border-radius: 12px;
  padding: 1rem 1.1rem;
  margin-bottom: 0.85rem;
}

.cv-badge {
  display: inline-block;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.cv-badge-ok { background: #d9f2e3; color: #0b6b3a; }
.cv-badge-parcial { background: #fff1d6; color: #8a5a00; }
.cv-badge-nao { background: #fde2e2; color: #9b1c1c; }

.cv-item-title {
  font-weight: 600;
  color: #163528;
  margin: 0.35rem 0 0.45rem 0;
}

.cv-muted {
  color: #5a7264;
  font-size: 0.9rem;
}

.cv-footer-note {
  margin-top: 1.5rem;
  padding-top: 0.85rem;
  border-top: 1px solid #d7e4dc;
  color: #5a7264;
  font-size: 0.82rem;
}

div[data-testid="stMetric"] {
  background: #fff;
  border: 1px solid #d7e4dc;
  border-radius: 12px;
  padding: 0.55rem 0.75rem;
}

@media (max-width: 900px) {
  .cv-steps { grid-template-columns: 1fr; }
  .cv-hero h1 { font-size: 1.3rem; }
}
</style>
"""


def render_hero() -> str:
    return """
<div class="cv-hero">
  <p class="cv-hero-kicker">CODEVASF · 12ª Superintendência Regional · Natal/RN</p>
  <h1>Análise de Conformidade Documental</h1>
  <p>
    Compare o requerimento enviado (ZIP ou pasta) com a Lista de Documentos
    exigida para doação de bens móveis — Prefeituras ou Associações —
    com apoio de IA local no servidor interno.
  </p>
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
