# =============================================================================
# Docker — interface Streamlit para intranet (Codevasf 12ª SR)
# =============================================================================
# Build:  docker compose build
# Run:    docker compose up -d
# App:    http://localhost:8502  (mapeia container:7860)
#
# IA: Ollama no host (OLLAMA_BASE_URL=http://host.docker.internal:11434)
# OCR: Tesseract com pacote de idioma português
# =============================================================================

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LLM_BACKEND=ollama \
    CHECKLISTS_PATH=/app/checklists \
    UPLOADS_PATH=/app/data/uploads \
    PORT=7860

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        tesseract-ocr \
        tesseract-ocr-por \
        tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ app/
COPY conformidade/ conformidade/
COPY checklists/ checklists/
COPY config.yaml .
COPY .streamlit/ .streamlit/

RUN mkdir -p /app/data/uploads \
    && useradd -m -u 1000 user \
    && chown -R user:user /app
USER user

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import os,urllib.request; p=os.environ.get('PORT','7860'); urllib.request.urlopen(f'http://127.0.0.1:{p}/_stcore/health')"

CMD streamlit run app/streamlit_app.py --server.address=0.0.0.0 --server.port=${PORT}
