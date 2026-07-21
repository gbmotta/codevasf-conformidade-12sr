#!/usr/bin/env python3
"""
Publica a interface Gradio no Hugging Face Spaces.

Uso:
  python scripts/deploy_hf_space.py gbmotta --space codevasf-conformidade
  python scripts/deploy_hf_space.py --build-only   # só monta .deploy_hf/

Passos do deploy:
  1. Monta staging (``.deploy_hf``) com app, conformidade, checklists
  2. Usa ``deploy/requirements-space.txt`` (deps enxutas do Space)
  3. Copia ``deploy/README_HF.md`` como README do Space
  4. Define secrets/variables (``LLM_BACKEND=zerogpu``, modelo, token)
  5. Faz upload e reinicia o Space

Token: env ``HF_TOKEN`` ou arquivo ``huggin_token.txt`` na raiz do projeto.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / ".deploy_hf"

# Pastas/arquivos enviados ao Space Gradio
COPY_DIRS = ("conformidade", "checklists", "app", "examples")
COPY_FILES = (
    "app.py",
    "packages.txt",
    "config.yaml",
    "requirements.txt",
)


def _ignore(_dir: str, names: list[str]) -> set[str]:
    """Ignora caches Python no staging."""
    return {n for n in names if n == "__pycache__" or n.endswith((".pyc", ".pyo"))}


def build_stage() -> Path:
    """Monta o diretório temporário que será enviado ao Space."""
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    for name in COPY_DIRS:
        src = ROOT / name
        if src.exists():
            shutil.copytree(src, STAGE / name, ignore=_ignore)

    for name in COPY_FILES:
        src = ROOT / name
        if src.exists():
            shutil.copy2(src, STAGE / name)

    shutil.copy2(ROOT / "deploy" / "README_HF.md", STAGE / "README.md")
    # Requirements enxuto do Space (sem streamlit/torch pin — build mais rápido)
    space_req = ROOT / "deploy" / "requirements-space.txt"
    if space_req.exists():
        shutil.copy2(space_req, STAGE / "requirements.txt")
    else:
        req = (STAGE / "requirements.txt").read_text(encoding="utf-8")
        if "gradio" not in req:
            (STAGE / "requirements.txt").write_text(
                req.rstrip() + "\ngradio>=5.0.0\n", encoding="utf-8"
            )
    print(f"Staging: {STAGE}")
    return STAGE


def deploy(username: str, space_name: str, token: str) -> str:
    """Envia o staging ao Space e configura ZeroGPU."""
    from huggingface_hub import HfApi
    from huggingface_hub.utils import RepositoryNotFoundError

    repo_id = f"{username}/{space_name}"
    api = HfApi(token=token)
    print("Logado como:", api.whoami().get("name"))

    stage = build_stage()
    try:
        api.repo_info(repo_id=repo_id, repo_type="space")
        print(f"Space existente: {repo_id}")
    except RepositoryNotFoundError as exc:
        raise SystemExit(
            f"Space {repo_id} não existe. Crie com Gradio+ZeroGPU ou rode o fluxo de create."
        ) from exc

    # ZeroGPU local — sem Inference Providers (evita HTTP 402 por créditos)
    try:
        api.add_space_secret(repo_id, "HF_TOKEN", token)
        api.add_space_variable(repo_id, "LLM_BACKEND", "zerogpu")
        api.add_space_variable(
            repo_id,
            "HF_MODEL",
            os.environ.get("HF_MODEL", "Qwen/Qwen2.5-1.5B-Instruct"),
        )
        api.add_space_variable(
            repo_id,
            "ZEROGPU_MODEL",
            os.environ.get("ZEROGPU_MODEL", "Qwen/Qwen2.5-1.5B-Instruct"),
        )
    except Exception as exc:
        print("Aviso ao configurar secrets/variables:", exc)

    api.upload_folder(
        folder_path=str(stage),
        repo_id=repo_id,
        repo_type="space",
        token=token,
        commit_message="Fix: FOR-198 não conta como Doação/Cessão Onerosa",
    )

    try:
        api.restart_space(repo_id)
        print("Restart do Space solicitado.")
    except Exception as exc:
        print("Aviso ao reiniciar Space:", exc)

    url = f"https://huggingface.co/spaces/{repo_id}"
    print("Space publicado:", url)
    return url


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy da conformidade Codevasf 12ª SR no Hugging Face Spaces"
    )
    parser.add_argument("username", nargs="?", default=os.environ.get("HF_USERNAME", "gbmotta"))
    parser.add_argument("--space", default=os.environ.get("HF_SPACE", "codevasf-conformidade"))
    parser.add_argument("--token", default=os.environ.get("HF_TOKEN"))
    parser.add_argument(
        "--build-only",
        action="store_true",
        help="Apenas monta .deploy_hf/ sem enviar",
    )
    args = parser.parse_args()

    if args.build_only:
        build_stage()
        return

    token = args.token
    if not token:
        for candidate in (ROOT / "huggin_token.txt", Path.home() / "Documentos" / "huggin_token.txt"):
            if candidate.exists():
                token = candidate.read_text(encoding="utf-8").strip()
                break
    if not token:
        raise SystemExit("HF_TOKEN ausente")

    deploy(args.username, args.space, token)


if __name__ == "__main__":
    main()
