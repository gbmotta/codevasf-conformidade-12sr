"""
Inferência com Transformers em Hugging Face ZeroGPU.

Evita o endpoint pago ``router.huggingface.co`` (HTTP 402 quando créditos
acabam). O modelo padrão é compacto (``Qwen/Qwen2.5-1.5B-Instruct``).

Deve ser chamado de dentro de uma função decorada com ``@spaces.GPU``
(veja ``app.py``). Fora do Space, o pacote ``spaces`` é no-op.
"""

from __future__ import annotations

import os
import threading

import spaces
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Modelo compacto o bastante para ZeroGPU.
MODEL_ID = (
    os.getenv("ZEROGPU_MODEL")
    or os.getenv("HF_MODEL")
    or "Qwen/Qwen2.5-1.5B-Instruct"
)

_lock = threading.Lock()
_tokenizer: AutoTokenizer | None = None
_model: AutoModelForCausalLM | None = None


def _ensure_model() -> tuple[AutoTokenizer, AutoModelForCausalLM]:
    global _tokenizer, _model
    if _model is not None and _tokenizer is not None:
        return _tokenizer, _model

    with _lock:
        if _model is not None and _tokenizer is not None:
            return _tokenizer, _model

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
        _tokenizer, _model = tok, mdl
        return tok, mdl


def generate_chat(
    messages: list[dict[str, str]],
    temperature: float = 0.0,
    max_new_tokens: int = 768,
) -> str:
    """Gera resposta de chat. Deve ser chamado de dentro de @spaces.GPU."""
    tokenizer, model = _ensure_model()
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer([prompt], return_tensors="pt")
    device = next(model.parameters()).device
    inputs = {key: value.to(device) for key, value in inputs.items()}

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
