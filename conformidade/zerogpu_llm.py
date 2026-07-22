"""
Inferência com Transformers em Hugging Face ZeroGPU.

Evita o endpoint pago ``router.huggingface.co`` (HTTP 402 quando créditos
acabam). O modelo padrão é compacto (``Qwen/Qwen2.5-1.5B-Instruct``).

No Space:
  - carrega o modelo no nível do módulo (emulação CUDA fora de ``@spaces.GPU``);
  - cada chamada a ``generate_chat`` pede GPU com duração ≤ 60s (cota free).

Fora do Space, o pacote ``spaces`` é no-op e o modelo só carrega sob demanda.
"""

from __future__ import annotations

import os
import threading
from typing import Any

try:
    import spaces
except ImportError:  # local / CI sem pacote spaces

    class spaces:  # type: ignore[no-redef]
        @staticmethod
        def GPU(duration=None, **_kwargs):
            def decorator(fn):
                return fn

            return decorator


MODEL_ID = (
    os.getenv("ZEROGPU_MODEL")
    or os.getenv("HF_MODEL")
    or "Qwen/Qwen2.5-1.5B-Instruct"
)

# ZeroGPU free tier: lease padrão ~60s. Pedir mais gera "Expired ZeroGPU proxy token".
_GPU_DURATION = int(os.getenv("ZEROGPU_DURATION", "55"))

ON_SPACES = bool(
    os.getenv("SPACE_ID")
    or os.getenv("SPACES_ZERO_GPU")
    or os.getenv("SPACE_REPO_NAME")
)

_lock = threading.Lock()
_tokenizer: Any = None
_model: Any = None


def _load_model():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    dtype = (
        torch.bfloat16
        if torch.cuda.is_available() and torch.cuda.is_bf16_supported()
        else (torch.float16 if torch.cuda.is_available() else torch.float32)
    )
    mdl = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=dtype,
        device_map="auto",
        trust_remote_code=True,
    )
    if tok.pad_token_id is None and tok.eos_token_id is not None:
        tok.pad_token_id = tok.eos_token_id
    return tok, mdl


def _ensure_model():
    global _tokenizer, _model
    if _model is not None and _tokenizer is not None:
        return _tokenizer, _model

    with _lock:
        if _model is not None and _tokenizer is not None:
            return _tokenizer, _model
        _tokenizer, _model = _load_model()
        return _tokenizer, _model


# Não pré-carregar no import: no Space isso estoura o boot (timeout/OOM)
# antes do Gradio subir. O modelo sobe no 1º generate_chat sob @spaces.GPU.


def _gpu_duration(*_args, **_kwargs) -> int:
    return max(20, min(_GPU_DURATION, 60))


@spaces.GPU(duration=_gpu_duration)
def generate_chat(
    messages: list[dict[str, str]],
    temperature: float = 0.0,
    max_new_tokens: int = 512,
) -> str:
    """Gera resposta de chat sob lease curto da ZeroGPU."""
    import torch

    tokenizer, model = _ensure_model()
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer([prompt], return_tensors="pt")
    device = next(model.parameters()).device
    inputs = {key: value.to(device) for key, value in inputs.items()}

    # Cap defensivo: gerações longas estouram o lease de ~60s.
    max_new_tokens = max(64, min(int(max_new_tokens), 640))

    gen_kwargs: dict = {
        "max_new_tokens": max_new_tokens,
        "do_sample": temperature > 0,
        "pad_token_id": tokenizer.pad_token_id,
    }
    if temperature > 0:
        gen_kwargs["temperature"] = max(temperature, 0.01)

    with torch.inference_mode():
        output_ids = model.generate(**inputs, **gen_kwargs)

    prompt_len = inputs["input_ids"].shape[-1]
    generated = output_ids[0][prompt_len:]
    return tokenizer.decode(generated, skip_special_tokens=True).strip()


def model_label() -> str:
    return MODEL_ID


# Mantém `spaces` no grafo de import do Space (no-op fora do ZeroGPU).
_ = spaces
