"""Fixtures e helpers dos testes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GOLD_DIR = Path(__file__).resolve().parent / "gold"


@pytest.fixture(scope="session")
def project_root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def gold_dir() -> Path:
    return GOLD_DIR


def load_gold(name: str) -> dict:
    path = GOLD_DIR / f"{name}_expected.json"
    if not path.is_file():
        # grossos file is grossos_expected via nome field
        candidates = list(GOLD_DIR.glob("*_expected.json"))
        for c in candidates:
            data = json.loads(c.read_text(encoding="utf-8"))
            if data.get("nome") == name or c.stem.startswith(name):
                return data
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))
