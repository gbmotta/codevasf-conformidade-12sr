#!/usr/bin/env python3
"""Publica a interface Gradio no Hugging Face Spaces (padrão PepMem-AI)."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / ".deploy_hf"

COPY_DIRS = ("conformidade", "checklists", "app")
COPY_FILES = (
    "app.py",
    "packages.txt",
    "config.yaml",
    "requirements.txt",
)


def _ignore(_dir: str, names: list[str]) -> set[str]:
    return {n for n in names if n == "__pycache__" or n.endswith((".pyc", ".pyo"))}


def build_stage() -> Path:
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
    # requirements do Space (sem streamlit obrigatório, mas ok manter)
    req = (STAGE / "requirements.txt").read_text(encoding="utf-8")
    if "gradio" not in req:
        (STAGE / "requirements.txt").write_text(req.rstrip() + "\ngradio>=5.0.0\n", encoding="utf-8")
    print(f"Staging: {STAGE}")
    return STAGE


def deploy(username: str, space_name: str, token: str) -> str:
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

    # Secret para Inference
    try:
        api.add_space_secret(repo_id, "HF_TOKEN", token)
        api.add_space_variable(repo_id, "LLM_BACKEND", "hf")
        api.add_space_variable(repo_id, "HF_MODEL", os.environ.get("HF_MODEL", "Qwen/Qwen2.5-7B-Instruct"))
    except Exception as exc:
        print("Aviso ao configurar secrets/variables:", exc)

    api.upload_folder(
        folder_path=str(stage),
        repo_id=repo_id,
        repo_type="space",
        token=token,
        commit_message="Deploy interface conformidade CODEVASF 12ª SR",
    )
    url = f"https://huggingface.co/spaces/{repo_id}"
    print("Space publicado:", url)
    return url


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("username", nargs="?", default=os.environ.get("HF_USERNAME", "gbmotta"))
    parser.add_argument("--space", default=os.environ.get("HF_SPACE", "codevasf-conformidade"))
    parser.add_argument("--token", default=os.environ.get("HF_TOKEN"))
    parser.add_argument("--build-only", action="store_true")
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
