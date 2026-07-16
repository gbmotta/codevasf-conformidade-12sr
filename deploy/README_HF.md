---
title: CODEVASF Conformidade 12SR
emoji: 📑
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 5.49.1
python_version: "3.12"
app_file: app.py
pinned: false
license: mit
short_description: Conformidade documental doação bens 12ª SR
---

# CODEVASF 12ª SR — Análise de Conformidade Documental

Interface para testar a conformidade de requerimentos (ZIP) com a Lista de Documentos
de **Prefeituras** ou **Associações / Cooperativas**.

1. Escolha o tipo de solicitante  
2. Envie o ZIP  
3. Clique em **Analisar conformidade**  
4. Baixe o relatório (`.md` / `.xlsx`)

**Secrets necessários no Space:** `HF_TOKEN` (token com Inference).  
Opcional: `HF_MODEL` (padrão `Qwen/Qwen2.5-7B-Instruct`), `LLM_BACKEND=hf`.

> Análise assistiva — não substitui a conferência humana da 12ª SR.
