---
title: CODEVASF Conformidade 12SR
emoji: 📑
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Análise de conformidade documental CODEVASF 12ª SR
---

# CODEVASF 12ª SR — Análise de Conformidade Documental

Interface web (Streamlit) para comparar requerimentos de doação (ZIP ou pasta) com a **Lista de Documentos** da 12ª Superintendência Regional.

- **Local / intranet:** IA via **Ollama**
- **Hugging Face Spaces:** IA via **HF Inference API** (`LLM_BACKEND=hf`)

## Demo no Hugging Face

1. Abra o Space
2. Em **Settings → Secrets**, configure `HF_TOKEN` (token com permissão de Inference)
3. Opcional: `HF_MODEL` (padrão `Qwen/Qwen2.5-7B-Instruct`)

## Interface

1. Escolher **Prefeitura** ou **Associação / Cooperativa**
2. Enviar o **ZIP** do requerimento (ou arquivos avulsos)
3. Clicar em **Analisar conformidade**
4. Revisar abas e baixar relatório (`.md` / `.xlsx`)

## Rede interna (Srv0312sr)

| Serviço | URL | Porta |
|---------|-----|-------|
| Assistente RAG | `http://Srv0312sr:8501` | 8501 |
| **Conformidade** | `http://Srv0312sr:8502` | **8502** |

Atalhos em `deploy/share/` para `\\Srv0312sr\12.SR`.

## Docker (servidor interno)

```bash
cp .env.docker.example .env
docker compose up -d --build
```

## Desenvolvimento local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Ollama local
ollama pull llama3
streamlit run app/streamlit_app.py
```

## OCR

PDFs escaneados usam **Tesseract (por)** + **PyMuPDF**. No Docker/Space o Tesseract já vem na imagem.

## Observações

- Ferramenta **assistiva** — a decisão final é da equipe da 12ª SR.
- Documentos enviados no Space ficam só na sessão do container (não use dados sensíveis em Space público sem política clara).
