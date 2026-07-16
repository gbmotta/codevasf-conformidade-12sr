"""Configuração da análise de conformidade."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def _load_yaml_config() -> dict:
    if not DEFAULT_CONFIG_PATH.exists():
        return {}
    with DEFAULT_CONFIG_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _resolve_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


@dataclass(frozen=True)
class Settings:
    llm_backend: str  # auto | ollama | hf
    ollama_base_url: str
    ollama_chat_model: str
    hf_model: str
    hf_token: str | None
    checklists_path: Path
    uploads_path: Path
    app_title: str
    max_chars_per_document: int
    max_total_document_chars: int

    def checklists_path_exists(self) -> bool:
        return self.checklists_path.exists()


def load_settings(env_path: Path | None = None) -> Settings:
    load_dotenv(env_path or DEFAULT_ENV_PATH)
    yaml_config = _load_yaml_config()
    app_cfg = yaml_config.get("app", {})
    analysis_cfg = yaml_config.get("analysis", {})

    # Em Spaces do HF, prioriza inferência remota se não houver Ollama explícito
    default_backend = "auto"
    if os.getenv("SPACE_ID") or os.getenv("SYSTEM") == "spaces":
        default_backend = "hf"

    return Settings(
        llm_backend=os.getenv("LLM_BACKEND", default_backend).strip().lower(),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        ollama_chat_model=os.getenv("OLLAMA_CHAT_MODEL", "llama3"),
        hf_model=os.getenv("HF_MODEL", "Qwen/Qwen2.5-7B-Instruct"),
        hf_token=os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN"),
        checklists_path=_resolve_path(os.getenv("CHECKLISTS_PATH", "./checklists")),
        uploads_path=_resolve_path(os.getenv("UPLOADS_PATH", "./data/uploads")),
        app_title=str(
            app_cfg.get("title", "CODEVASF 12ª SR — Análise de Conformidade Documental")
        ),
        max_chars_per_document=_env_int(
            "MAX_CHARS_PER_DOCUMENT",
            int(analysis_cfg.get("max_chars_per_document", 3500)),
        ),
        max_total_document_chars=_env_int(
            "MAX_TOTAL_DOCUMENT_CHARS",
            int(analysis_cfg.get("max_total_document_chars", 28000)),
        ),
    )
