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

Ferramenta **assistiva** para comparar o pacote documental de um requerimento de **doação / concessão de bens móveis** com a **Lista de Documentos** oficial da **12ª Superintendência Regional da CODEVASF** (Natal/RN), em **ano eleitoral**.

Não substitui a conferência humana da equipe. O sistema sugere status por item (`atendido` / `parcial` / `não atendido`), gera relatório exportável e permite **revisão humana** antes do download.

---

## Sumário

1. [Onde está publicado](#onde-está-publicado)
2. [O que o sistema faz](#o-que-o-sistema-faz)
3. [Tipos de solicitante e checklists](#tipos-de-solicitante-e-checklists)
4. [Arquitetura](#arquitetura)
5. [Pipeline de análise (passo a passo)](#pipeline-de-análise-passo-a-passo)
6. [Regras determinísticas vs IA](#regras-determinísticas-vs-ia)
7. [OCR e formatos de arquivo](#ocr-e-formatos-de-arquivo)
8. [Backends de LLM](#backends-de-llm)
9. [Interfaces (Gradio e Streamlit)](#interfaces-gradio-e-streamlit)
10. [Estrutura de pastas](#estrutura-de-pastas)
11. [Configuração (`.env` e `config.yaml`)](#configuração-env-e-configyaml)
12. [Desenvolvimento local](#desenvolvimento-local)
13. [Docker (intranet / Srv0312sr)](#docker-intranet--srv0312sr)
14. [Hugging Face Space](#hugging-face-space)
15. [Deploy do Space (`scripts/deploy_hf_space.py`)](#deploy-do-space-scriptsdeploy_hf_spacepy)
16. [Exportação de relatórios](#exportação-de-relatórios)
17. [Exemplos de ZIP](#exemplos-de-zip)
18. [Atalhos na rede interna](#atalhos-na-rede-interna)
19. [Troubleshooting](#troubleshooting)
20. [Limitações e boas práticas](#limitações-e-boas-práticas)
21. [Licença](#licença)

---

## Onde está publicado

| Destino | URL | Função |
|---------|-----|--------|
| **GitHub (código-fonte)** | https://github.com/gbmotta/codevasf-conformidade-12sr | Clonar, desenvolver, issues |
| **HF Space (interface pública)** | https://huggingface.co/spaces/gbmotta/codevasf-conformidade | Testar no navegador (Gradio + ZeroGPU) |
| **App do Space** | https://gbmotta-codevasf-conformidade.hf.space | Endpoint direto do container |
| **HF (espelho de código)** | https://huggingface.co/gbmotta/codevasf-conformidade-12sr | Espelho do repositório |

### Rede interna (Srv0312sr)

| Serviço | URL | Porta |
|---------|-----|-------|
| Assistente RAG | `http://Srv0312sr:8501` | 8501 |
| **Conformidade (este sistema)** | `http://Srv0312sr:8502` | **8502** |

Atalhos para usuários finais (sem Python): pasta `deploy/share/` → copiar para `\\Srv0312sr\12.SR` (ver [Atalhos na rede interna](#atalhos-na-rede-interna)).

---

## O que o sistema faz

### Entrada

- **ZIP** do e-mail / requerimento (caso mais comum)
- **Pasta** com PDFs/DOCX (Streamlit: pasta local ou montada no servidor)
- **Arquivos avulsos** (upload múltiplo no Gradio)

### Processamento

1. Extrai e lê o texto de cada documento (nativo + OCR quando necessário)
2. Carrega a **lista oficial** correta (Prefeitura **ou** Associação/Cooperativa)
3. Avalia **cada item numerado** da lista:
   - primeiro por **regras determinísticas** (nome + trechos de conteúdo)
   - depois por **LLM** só nos itens ainda dúbios
4. Monta um `RelatorioConformidade` com resumo e contagens

### Saída

- Visualização na UI (cards, badges, inventário)
- Download: **Markdown (`.md`)**, **Excel (`.xlsx`)**, **Word (`.docx`)**, **PDF**
- Opcional: ajustes manuais de status/motivo (**revisão humana**) e novo download

### Destinatário institucional (contexto do ofício)

As listas exigem ofício dirigido ao Superintendente da 12ª SR:

- **Sr. Leonlene de Sousa Aguiar**
- Envio típico: `12a.gb@codevasf.gov.br`

---

## Tipos de solicitante e checklists

Dois tipos (`conformidade/checklist.py` → `TipoEntidade`):

| Enum | Rótulo na UI | PDF em `checklists/` | Contrapartida Doação Onerosa (ano eleitoral) |
|------|--------------|----------------------|-----------------------------------------------|
| `prefeitura` | Prefeitura | `lista_prefeituras.pdf` | **1,5%** |
| `associacao` | Associação / Cooperativa / Instituição pública | `lista_associacoes.pdf` | **1%** |

Se o PDF não for parseável, o código usa **itens embutidos** (`FALLBACK_ITEMS`) com o mesmo conteúdo esperado das listas oficiais.

### Prefeitura — 12 itens (resumo)

1. Ofício timbrado (bens + uso), ao Sr. Leonlene  
2. CNPJ  
3. CND Receita Federal / Dívida Ativa (PJ)  
4. CRF do FGTS  
5. CNDT  
6. Ata de posse / termo de transmissão  
7. Diploma do Prefeito(a)  
8. RG e CPF do Prefeito(a)  
9. Comprovante de votação **ou** quitação eleitoral  
10. Comprovante de residência  
11. Declaração de Doação Onerosa (**1,5%**)  
12. Plano de Uso do Bem (formulário típico **FOR-195** para direito público)

### Associação / Cooperativa — 10 itens (resumo)

1. Ofício timbrado com menção a **fins / interesse social**, ao Sr. Leonlene  
2. Estatuto / contrato social em vigor  
3. Ata de criação ou eleição da diretoria (registrada em cartório)  
4. CNPJ  
5. CND Receita Federal  
6. CRF do FGTS  
7. CNDT  
8. Docs pessoais do responsável (RG, CPF, título, endereço)  
9. Declaração de Doação Onerosa (**1%**)  
10. Plano de Uso do Bem (formulário típico **FOR-196** para PJ sem fins lucrativos)

### Inferência automática do tipo

`infer_tipo_from_names()` pontua tokens nos nomes dos arquivos (`prefeitura`, `diploma`, `estatuto`, `cooperativa`, etc.) e sugere Prefeitura ou Associação. A UI ainda exige confirmação explícita do usuário.

### Atenção frequente (ano eleitoral)

- **FOR-198** (declaração de não ocorrência de impedimentos / Lei 13.019) **não substitui** a Declaração de Doação Onerosa.
- **Plano de Trabalho** não substitui o **Plano de Uso** (FOR-195 / FOR-196).
- CRF do FGTS tem validade curta — o sistema pode marcar parcial/ausente se não houver evidência clara.

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│  UI Gradio (app.py)          UI Streamlit (app/streamlit_app.py) │
│  HF Space / localhost:7860    Local / Docker :8502→7860          │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  conformidade/analyzer.py  — orquestra regras + LLM + relatório │
├──────────────┬────────────────┬─────────────────────────────────┤
│ checklist.py │ loaders.py     │ rules.py                        │
│ listas PDF   │ ZIP/pasta/OCR  │ hints nome + conteúdo           │
├──────────────┼────────────────┼─────────────────────────────────┤
│ llm.py       │ zerogpu_llm.py │ models.py + report.py           │
│ ollama/hf/…  │ Transformers   │ status + export md/xlsx/docx/pdf│
└──────────────┴────────────────┴─────────────────────────────────┘
```

| Módulo | Responsabilidade |
|--------|------------------|
| `conformidade/checklist.py` | Tipo de entidade, parse das listas PDF, fallback |
| `conformidade/loaders.py` | ZIP/pasta, PDF/DOCX/imagem; delega OCR a `ocr.py` |
| `conformidade/ocr.py` | Tesseract aprimorado (DPI 350, preprocess, PSM, por+eng, por página) |
| `conformidade/ml/` | Classificador de docs, extratores, matching (sem LLM) |
| `conformidade/rules.py` | Score por nome/conteúdo; decisões fortes sem LLM |
| `conformidade/analyzer.py` | Pipeline completo + prompt JSON para itens pendentes |
| `conformidade/llm.py` | Cliente unificado (`auto` / `ollama` / `zerogpu` / `hf`) |
| `conformidade/zerogpu_llm.py` | Inferência local no Space via Transformers + `@spaces.GPU` |
| `conformidade/models.py` | `ItemResultado`, `RelatorioConformidade`, revisão humana |
| `conformidade/report.py` | Exportação visual (paleta institucional Codevasf) |
| `conformidade/config.py` | Settings a partir de env + `config.yaml` |
| `app.py` | Interface Gradio (Space + `python app.py`) |
| `app/streamlit_app.py` | Interface Streamlit (intranet / Docker) |
| `app/styles.py` | CSS/tema Gradio |
| `scripts/deploy_hf_space.py` | Staging + upload + secrets/variables + restart do Space |
| `checklists/` | PDFs oficiais das listas |
| `deploy/` | README do Space, requirements enxuto, atalhos de rede |

---

## Pipeline de análise (passo a passo)

Função pública: `analisar_conformidade(settings, checklist, documents, ...)`.

1. **Carregar documentos** (`load_from_zip` / `scan_folder`)  
   - Cada arquivo vira `LoadedDocument` com `content`, `file_name`, `relative_path`, `extraction_method` (`texto` | `ocr` | `hibrido` | `vazio` | `erro`).

2. **Para cada item do checklist**  
   - `evaluate_item_rules(item, documents)`:
     - mapeia a descrição do item para chaves (`oficio`, `cnpj`, `fgts`, `doacao_onerosa`, …)
     - pontua arquivos por **nome** (+3 por token) e **conteúdo** (+2 por token)
     - se não achar nada → **não atendido** (regra resolvida)
     - se score alto e coerente → **atendido** ou **parcial** (regra resolvida)
     - se ambíguo → `resolved=False` (vai para LLM)

3. **Lotes LLM** (só itens pendentes)  
   - Monta bloco de documentos truncado (`max_chars_per_document`, `max_total_document_chars` em `config.yaml`)
   - Prompt de sistema exige JSON com `status` ∈ {`atendido`, `parcial`, `nao_atendido`}
   - Parse robusto (remove fences markdown, extrai `{...}`)

4. **Montagem do relatório**  
   - Contagens, resumo textual, lista de arquivos analisados, `fonte` por item (`regra` | `ia` | depois `humano`)

5. **Revisão humana (opcional na UI)**  
   - `aplicar_revisao_humana(relatorio, overrides)` atualiza status/motivo e marca `revisado=True`

---

## Regras determinísticas vs IA

### Quando a regra decide sozinha

- Arquivo claramente ausente para o item → `nao_atendido`
- Nome + conteúdo fortes (ex.: `Certidao FGTS.pdf` + texto “Certificado de Regularidade do FGTS”) → `atendido` / `parcial`

### Quando chama a IA

- Item sem mapeamento de hints
- Vários arquivos candidatos conflitantes
- Conteúdo fraco / OCR ruim / formulário genérico

### Hints principais (`rules.py`)

| Chave | Exemplos no nome | Exemplos no conteúdo |
|-------|------------------|----------------------|
| `oficio` | oficio, requerimento | superintendente, codevasf, doação |
| `cnpj` | cnpj | cadastro nacional |
| `federal` | receita, rfb, certidao conjunta | tributos federais, dívida ativa |
| `fgts` | fgts, crf | fundo de garantia, caixa |
| `cndt` | trabalhista, cndt | tribunal superior do trabalho |
| `doacao_onerosa` | doação/cessão onerosa, aceitação onerosa | doação onerosa, contrapartida de 1%/1,5% |
| `plano_uso` | plano de uso, for.195 | uso do bem, destinação |
| `estatuto` | estatuto, contrato social | associação, cooperativa |
| `ata_diretoria` | ata de eleicao, diretoria | assembleia, eleição |

**FOR-198 ≠ Doação Onerosa:** a regra `_evaluate_doacao_onerosa` marca `nao_atendido` se só houver Declaração de Impedimentos (FOR-198). Hints de `doacao_onerosa` **não** incluem impedimento/FOR-198.

---

## OCR e formatos de arquivo

### Extensões aceitas (`loaders.py`)

| Tipo | Extensões |
|------|-----------|
| Texto / documento | `.pdf`, `.docx`, `.doc`, `.txt`, `.md` |
| Imagem | `.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`, `.bmp`, `.webp` |

### Política de OCR (`conformidade/ocr.py`)

- Decisão **por página**: texto nativo &lt; **40 caracteres** → OCR só naquela página (PDF híbrido)
- Idioma: **`por+eng`** (fallback `por`)
- DPI: **350** (env `OCR_DPI`)
- Máximo de páginas OCR: **40** (env `OCR_MAX_PAGES`)
- Pré-processamento: contraste, nitidez, binarização leve, OSD/orientação; deskew se o 1º resultado for fraco
- Tesseract: `--oem 3` + PSM `6/4/3` (melhor score)
- Fallback opcional **EasyOCR** se instalado com `OCR_ENGINE=easyocr` ou `auto` + `OCR_ALLOW_EASYOCR=1` (não vem no Space)
- Dependências Space: **PyMuPDF** + **pytesseract** + **Pillow** + `tesseract-ocr` + `tesseract-ocr-por` + `tesseract-ocr-eng`

### Instalação do Tesseract

| Ambiente | Como |
|----------|------|
| Docker intranet | `Dockerfile` (`tesseract-ocr`, `por`, preferir também `eng`) |
| HF Space | Via `packages.txt` (apt no build Gradio) |
| Windows local | Instalar Tesseract e, se preciso, `TESSERACT_CMD=C:\...\tesseract.exe` |
| Linux | `sudo apt install tesseract-ocr tesseract-ocr-por tesseract-ocr-eng` |

`ocr_available()` expõe na UI se OCR está utilizável (e se EasyOCR está presente).

### Observação crítica — `packages.txt` no Space

O runtime Gradio do HF faz:

```text
xargs -a packages.txt apt-get install -y
```

Regras:

1. **Sem comentários `#`** (viram “nomes de pacote” inválidos)
2. **Somente LF** (Unix) — CRLF do Windows faz o apt procurar `tesseract-ocr\r` e o build cai em `BUILD_ERROR`
3. Pacotes atuais: `tesseract-ocr`, `tesseract-ocr-por`, `fonts-dejavu-core`

---

## Backends de LLM

Variável: `LLM_BACKEND` (`conformidade/llm.py` → `resolve_backend`).

| Valor | Uso | Observação |
|-------|-----|------------|
| `auto` | Padrão local | Prefere Ollama; no Space tende a ZeroGPU |
| `ollama` | Intranet / PC | `OLLAMA_BASE_URL` + `OLLAMA_CHAT_MODEL` |
| `zerogpu` | HF Space | Modelo Transformers no GPU dinâmico; **sem** créditos Inference Providers |
| `hf` | Inference Providers | Pode exigir créditos / pagamento (`HF_TOKEN`, `HF_MODEL`) |

### Variáveis relacionadas

```env
LLM_BACKEND=auto
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=llama3.2:1b

# Space
# LLM_BACKEND=zerogpu
# ZEROGPU_MODEL=Qwen/Qwen2.5-1.5B-Instruct
# HF_MODEL=Qwen/Qwen2.5-1.5B-Instruct

# Inference Providers (opcional / pago)
# HF_TOKEN=hf_...
# HF_MODEL=Qwen/Qwen2.5-7B-Instruct
```

No Space, o deploy script grava secrets/variables:

- Secret: `HF_TOKEN`
- Variables: `LLM_BACKEND=zerogpu`, `HF_MODEL`, `ZEROGPU_MODEL`

A UI Gradio mostra status do sistema (acordeão) — deve indicar `LLM: zerogpu` no Space.

---

## Interfaces (Gradio e Streamlit)

### Gradio — `app.py` (HF Space e `python app.py`)

- Porta padrão: **7860**
- Fluxo:
  1. Escolher tipo (Prefeitura / Associação)
  2. Enviar ZIP ou arquivos
  3. **Analisar conformidade**
  4. Ver resumo + itens
  5. (Opcional) revisar status/motivo
  6. Baixar `.md` / `.xlsx` / `.docx` / `.pdf`
- UX: hero, passos, badges, inventário HTML, CSS em `app/styles.py`
- ZeroGPU: funções de inferência decoráveis com `@spaces.GPU` (stub local se `spaces` ausente)

### Streamlit — `app/streamlit_app.py` (intranet)

- Comando: `streamlit run app/streamlit_app.py`
- Docker mapeia host **8502** → container **7860**
- Adequado a pasta montada no servidor (`REQUERIMENTOS_HOST_PATH`)
- Config Streamlit: `.streamlit/config.toml`

| Cenário | Interface recomendada |
|---------|------------------------|
| Demo pública / teste rápido | Gradio (Space) |
| Rede interna 12ª SR | Streamlit + Docker + Ollama |
| Desenvolvimento | Qualquer uma das duas |

---

## Estrutura de pastas

```text
codevasf-conformidade-12sr/
├── app.py                      # Entrada Gradio
├── app/
│   ├── streamlit_app.py        # Entrada Streamlit
│   ├── styles.py
│   └── static/logo_codevasf.png
├── conformidade/               # Núcleo da análise
│   ├── analyzer.py
│   ├── checklist.py
│   ├── config.py
│   ├── llm.py
│   ├── loaders.py
│   ├── ocr.py
│   ├── ml/                     # ML clássico (sem LLM)
│   │   ├── schema.py           # Rótulos de tipo de documento
│   │   ├── classifier.py       # TF-IDF + LogisticRegression
│   │   ├── extractors.py       # CNPJ / datas / validade
│   │   ├── matching.py         # Item ↔ documento
│   │   └── artifacts/          # Modelo .joblib treinado
│   ├── models.py
│   ├── report.py
│   ├── rules.py
│   └── zerogpu_llm.py
├── checklists/
│   ├── lista_associacoes.pdf
│   └── lista_prefeituras.pdf
├── config.yaml                 # Limites de contexto + OCR
├── data/
│   ├── uploads/
│   └── ml/                     # CSV de rótulos (export)
├── deploy/
│   ├── README_HF.md            # Frontmatter + texto do Space Gradio
│   ├── requirements-space.txt  # Deps enxutas do Space
│   └── share/                  # Atalhos .url / .bat / .html / LEIA-ME
├── examples/
│   ├── exemplo_equador.zip
│   └── exemplo_prefeitura_acari.zip
├── scripts/
│   ├── deploy_hf_space.py
│   ├── export_doc_labels.py    # Exporta CSV de rótulos
│   └── train_doc_classifier.py # Treina classificador
├── packages.txt                # Apt do Space (LF, sem comentários!)
├── requirements.txt            # Local + Docker Streamlit
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .env.docker.example
└── README.md                   # Este arquivo
```

---

## ML clássico (sem LLM)

Objetivo: classificar documentos e extrair campos **antes** (ou no lugar) da chamada à IA.

| Módulo | Função |
|--------|--------|
| `ml/schema.py` | Rótulos (`oficio`, `fgts`, `impedimento`, `doacao_onerosa`, …) |
| `ml/heuristics.py` | Pseudo-rótulos por nome/conteúdo |
| `ml/classifier.py` | TF-IDF + regressão logística (`scikit-learn`) |
| `ml/extractors.py` | CNPJ/CPF válidos, datas, validade de certidão |
| `ml/matching.py` | Ranking item ↔ arquivos por similaridade |

Integração: `rules.py` usa o classificador como boost/penalidade e marca certidões **vencidas** como parcial.

### Exportar rótulos e treinar

```bash
# 1) CSV a partir de seed + (opcional) relatórios JSON / pasta de PDFs
python scripts/export_doc_labels.py --seed-only --out data/ml/labels.csv
python scripts/export_doc_labels.py --reports-dir ./meus_relatorios_json --docs-root ./pacotes --out data/ml/labels.csv

# 2) Treinar e gravar modelo em conformidade/ml/artifacts/
python scripts/train_doc_classifier.py --from-seed
python scripts/train_doc_classifier.py --csv data/ml/labels.csv
```

Relatórios JSON = saída de `RelatorioConformidade.to_dict()` (export da UI). Itens `atendido`/`parcial` geram linhas `(arquivo → rótulo do item)`.

Sem modelo treinado, o sistema usa só a heurística (já cobre FOR-198 ≠ onerosa).

---

## Configuração (`.env` e `config.yaml`)

### `.env` (local) — a partir de `.env.example`

| Variável | Descrição | Padrão típico |
|----------|-----------|---------------|
| `LLM_BACKEND` | `auto` \| `ollama` \| `zerogpu` \| `hf` | `auto` |
| `OLLAMA_BASE_URL` | URL da API Ollama | `http://localhost:11434` |
| `OLLAMA_CHAT_MODEL` | Tag do modelo | `llama3.2:1b` (ajuste ao seu pull) |
| `CHECKLISTS_PATH` | Pasta das listas PDF | `./checklists` |
| `UPLOADS_PATH` | Extração temporária | `./data/uploads` |
| `STREAMLIT_PUBLIC_URL` | URL pública intranet | `http://Srv0312sr:8502` |
| `TESSERACT_CMD` | Caminho do binário (Windows) | (opcional) |
| `HF_TOKEN` | Token Hub / Inference | (opcional / Space) |
| `HF_MODEL` / `ZEROGPU_MODEL` | Modelo Transformers | `Qwen/Qwen2.5-1.5B-Instruct` |

### `.env` (Docker) — a partir de `.env.docker.example`

| Variável | Descrição |
|----------|-----------|
| `STREAMLIT_PORT` | Porta no host (padrão `8502`) |
| `OLLAMA_BASE_URL` | No compose: `http://host.docker.internal:11434` |
| `REQUERIMENTOS_HOST_PATH` | Pasta do host montada em `/requerimentos:ro` |

### `config.yaml`

```yaml
app:
  title: "Codevasf 12ª SR — Análise de Conformidade Documental"

analysis:
  max_chars_per_document: 3500   # por arquivo no prompt
  max_total_document_chars: 28000  # teto total do bloco de docs
```

Variáveis de ambiente **sobrescrevem** valores equivalentes quando o loader de settings assim definir.

### Segredos e git

Não versionar: `.env`, `*_token.txt`, `huggin_token.txt`, conteúdo de `data/uploads/*`, `.deploy_hf/`.

---

## Desenvolvimento local

### Pré-requisitos

- Python **3.12+** recomendado (Space usa 3.12)
- (Opcional) [Ollama](https://ollama.com) com um modelo puxado
- (Opcional) Tesseract + pacote `por` para PDFs escaneados

### Windows (PowerShell)

```powershell
cd codevasf-conformidade-12sr
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edite .env (OLLAMA_CHAT_MODEL deve bater com: ollama list)

ollama pull llama3.2:1b
# Interface Streamlit:
streamlit run app/streamlit_app.py
# ou Gradio:
python app.py
```

### Linux / macOS

```bash
cd codevasf-conformidade-12sr
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
ollama pull llama3.2:1b
streamlit run app/streamlit_app.py
# ou: python app.py
```

### Portas locais

| App | URL típica |
|-----|------------|
| Streamlit | http://localhost:8501 (padrão Streamlit) — ou a porta que você passar |
| Gradio | http://localhost:7860 |
| Docker intranet | http://localhost:8502 |

---

## Docker (intranet / Srv0312sr)

Imagem baseada em `python:3.12-slim`, com Tesseract PT, usuário não-root `uid 1000`, healthcheck no endpoint Streamlit `/_stcore/health`.

```bash
cp .env.docker.example .env
# Ajuste OLLAMA_BASE_URL / OLLAMA_CHAT_MODEL / STREAMLIT_PORT / REQUERIMENTOS_HOST_PATH

docker compose up -d --build
```

- Container: `codevasf-conformidade`
- Host: `${STREAMLIT_PORT:-8502}` → container `7860`
- Volume nomeado: `uploads_data` → `/app/data/uploads`
- `extra_hosts`: `host.docker.internal` para alcançar Ollama no host

Verificar:

```bash
docker compose ps
curl -f http://127.0.0.1:8502/_stcore/health
```

---

## Hugging Face Space

- SDK: **Gradio** (`sdk_version` em `deploy/README_HF.md`, ex. 5.49.1)
- Hardware: **ZeroGPU** (`zero-a10g`)
- App: `app.py`
- Dependências do Space: `deploy/requirements-space.txt` (sem Streamlit; torch vem da imagem)
- Apt: `packages.txt` (LF, sem `#`)
- IA: `LLM_BACKEND=zerogpu` — **não** usa `router.huggingface.co` / Inference Providers pagos

### Fluxo do usuário no Space

1. Tipo de solicitante  
2. ZIP (ou arquivos)  
3. Analisar  
4. Revisar se quiser  
5. Baixar relatório  

### Privacidade

Arquivos ficam na sessão/container do Space. **Não envie dados sensíveis** em Space público sem política clara da 12ª SR. Para produção interna, use Docker no Srv0312sr.

### Hardware / PRO

- ZeroGPU é o alvo do Space público.
- Trocas de flavor (ex.: para `cpu-basic`) podem exigir assinatura / regras de billing do Hub.
- Se a GPU falhar por cota, a análise por **regras** ainda pode concluir parte dos itens; a parte LLM fica degradada.

---

## Deploy do Space (`scripts/deploy_hf_space.py`)

### O que o script faz

1. Monta staging em `.deploy_hf/` (gitignored)
2. Copia `conformidade/`, `checklists/`, `app/`, `examples/`, `app.py`, `packages.txt`, `config.yaml`
3. Usa `deploy/README_HF.md` como `README.md` do Space
4. Substitui `requirements.txt` por `deploy/requirements-space.txt`
5. Configura secret `HF_TOKEN` e variables `LLM_BACKEND`, `HF_MODEL`, `ZEROGPU_MODEL`
6. `upload_folder` + `restart_space`

### Uso

```bash
# Só montar staging (sem enviar)
python scripts/deploy_hf_space.py --build-only

# Publicar (token via env ou arquivo)
set HF_TOKEN=hf_...          # PowerShell: $env:HF_TOKEN="hf_..."
python scripts/deploy_hf_space.py gbmotta --space codevasf-conformidade
```

Token aceito em:

- Variável `HF_TOKEN`
- Arquivo `huggin_token.txt` / equivalente na raiz (não versionar)
- Flag `--token`

### Checklist pós-deploy

1. Space em **Running** (não `BUILD_ERROR`)
2. `packages.txt` no Hub com LF e sem comentários
3. Acordeão de status: `LLM: zerogpu`
4. Teste com `examples/exemplo_prefeitura_acari.zip`

### Build error clássico (já corrigido neste repo)

```text
E: Unable to locate package tesseract-ocr
```

Causa comum: **CRLF** no `packages.txt`. Reescreva com LF e redeploy.

---

## Exportação de relatórios

`conformidade/report.py` — paleta institucional (azul `#005CA8`, verde `#007D4E`, etc.):

| Formato | Função | Conteúdo típico |
|--------|--------|-----------------|
| Markdown | `relatorio_para_markdown` | Texto legível / versionamento |
| Excel | `relatorio_para_xlsx` | Planilha com status coloridos |
| Word | `relatorio_para_docx` | Documento formal |
| PDF | `relatorio_para_pdf` | via fpdf2 |

Cada item exportado traz: número, descrição, status, motivo, documentos relacionados, fonte (`regra` / `ia` / `humano`).

---

## Exemplos de ZIP

Em `examples/`:

| Arquivo | Uso sugerido |
|---------|--------------|
| `exemplo_prefeitura_acari.zip` | Checklist **Prefeitura** |
| `exemplo_equador.zip` | Checklist **Prefeitura** (outro município) |

Úteis para smoke test no Space e em CI manual após deploy.

---

## Atalhos na rede interna

Pasta `deploy/share/` — copiar para a raiz do share `\\Srv0312sr\12.SR`:

| Arquivo | Quando usar |
|---------|-------------|
| `CODEVASF Conformidade.url` | **Recomendado** em qualquer PC da rede → `http://Srv0312sr:8502` |
| `Abrir Conformidade CODEVASF.bat` | Alternativa |
| `Abrir Conformidade CODEVASF.html` | Alternativa |
| `CODEVASF Conformidade (somente neste servidor).url` | Só logado **no** Srv0312sr (localhost) |
| `LEIA-ME.txt` | Instruções para usuários / TI |

**Não** use atalho `localhost` a partir de outro PC: `localhost` seria a máquina do usuário, não o servidor.

Requisitos de TI: container Docker no ar, porta **8502** liberada, Ollama alcançável pelo container.

---

## Troubleshooting

| Sintoma | O que verificar |
|---------|-----------------|
| Space em `BUILD_ERROR` / apt “Unable to locate package …” | `packages.txt` com **LF** e **sem** linhas `#` |
| OCR limitado às primeiras N páginas | `OCR_MAX_PAGES` (padrão 40); demais usam texto nativo se existir |
| OCR ruim / ilegível | DPI 350 + preprocess; opcional `OCR_ALLOW_EASYOCR=1` na intranet |
| Ollama: connection error | Serviço rodando; URL correta; no Docker usar `host.docker.internal` |
| Modelo Ollama ausente | `ollama list` / `ollama pull <modelo>` alinhado a `OLLAMA_CHAT_MODEL` |
| Itens todos “não atendido” | ZIP vazio, tipo errado (prefeitura vs associação), só imagens sem OCR |
| Doação Onerosa marcada OK com só FOR-198 | Corrigido em `rules.py` (`_evaluate_doacao_onerosa`); redeploy do Space se ainda ocorrer |
| Plano de Uso faltando com “Plano de Trabalho” presente | Esperado: plano de trabalho não substitui FOR-195/196 |
| Export PDF com fonte estranha | `fonts-dejavu-core` no Space; fpdf2 no `requirements` |
| Token HF / deploy 401 | Token **write**; `hf auth whoami` |
| ZeroGPU / 402 billing | Conta / cota / política de hardware do Hub |

Logs do Space:

```bash
hf spaces logs gbmotta/codevasf-conformidade --build --tail 100
hf spaces info gbmotta/codevasf-conformidade
```

---

## Limitações e boas práticas

1. **Assistivo** — decisão final é da equipe da 12ª SR.  
2. **OCR limitado** a 20 páginas/arquivo — atas/estatutos longos podem ficar parciais.  
3. **Contexto do LLM truncado** — arquivos muito grandes têm trechos omitidos.  
4. **Ano eleitoral** — Doação Onerosa (1% / 1,5%) é crítica; não confundir com FOR-198.  
5. **Space público** — evite PII/documentos oficiais reais; use Docker interno.  
6. **Validar validade de certidões** (FGTS, CND) fora do sistema quando o envio for tardio.  
7. Após análise automática, use a **revisão humana** na UI antes de arquivar o relatório.

---

## Licença

MIT (conforme metadados do repositório / Space).

---

## Referência rápida de comandos

```bash
# Local Streamlit
streamlit run app/streamlit_app.py

# Local Gradio
python app.py

# Docker intranet
cp .env.docker.example .env && docker compose up -d --build

# Staging Space (sem upload)
python scripts/deploy_hf_space.py --build-only

# Publicar Space
python scripts/deploy_hf_space.py gbmotta --space codevasf-conformidade
```

**Space:** https://huggingface.co/spaces/gbmotta/codevasf-conformidade  
**Código:** https://github.com/gbmotta/codevasf-conformidade-12sr
