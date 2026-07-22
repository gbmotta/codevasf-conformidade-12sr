"""
Cliente unificado de LLM para a análise.

Backends (``Settings.llm_backend`` / env ``LLM_BACKEND``):
  - ``ollama``  — API local ``/api/chat``
  - ``zerogpu`` — modelo Transformers no Space (ver ``zerogpu_llm``)
  - ``hf``      — Hugging Face Inference Providers (pode exigir créditos)
  - ``auto``    — prefere Ollama; no Space cai para ZeroGPU

API principal: ``chat_completion`` / ``check_llm_health`` / ``resolve_backend``.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests

from conformidade.config import Settings


class OllamaError(RuntimeError):
    """Erro de comunicação ou resposta inválida do provedor de LLM."""


@dataclass
class ChatMessage:
    role: str
    content: str


def _request_json(
    settings: Settings,
    method: str,
    path: str,
    payload: dict | None = None,
    timeout: int = 300,
) -> dict:
    url = f"{settings.ollama_base_url}{path}"
    try:
        response = requests.request(method, url, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError as exc:
        raise OllamaError(
            f"Não foi possível conectar ao Ollama em {settings.ollama_base_url}. "
            "Verifique se o serviço está em execução."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise OllamaError("Tempo esgotado ao aguardar resposta do Ollama.") from exc
    except requests.exceptions.HTTPError as exc:
        detail = ""
        resp = getattr(exc, "response", None)
        if resp is not None:
            try:
                payload = resp.json()
                detail = str(payload.get("error") or payload)
            except Exception:
                detail = (resp.text or "")[:300]
        if detail:
            raise OllamaError(f"Erro HTTP do Ollama: {exc} — {detail}") from exc
        raise OllamaError(f"Erro HTTP do Ollama: {exc}") from exc
    except ValueError as exc:
        raise OllamaError("Resposta inválida do Ollama (JSON esperado).") from exc


def _ollama_healthy(settings: Settings) -> tuple[bool, str]:
    try:
        data = _request_json(settings, "GET", "/api/tags", timeout=10)
        models = [model.get("name", "") for model in data.get("models", [])]
        if not models:
            return True, "Ollama acessível, mas nenhum modelo listado."

        required = settings.ollama_chat_model
        if not any(required in name for name in models):
            return True, f"Ollama acessível. Modelo ausente: {required}"
        return True, "Ollama acessível e modelo configurado encontrado."
    except OllamaError as exc:
        return False, str(exc)


def _hf_healthy(settings: Settings) -> tuple[bool, str]:
    try:
        from huggingface_hub import InferenceClient
    except ImportError:
        return False, "huggingface_hub não instalado."

    if not settings.hf_token:
        return False, "HF_TOKEN ausente (configure o secret no Space ou no .env)."

    try:
        _ = InferenceClient(token=settings.hf_token)
        return True, f"HF Inference configurado (modelo: {settings.hf_model})"
    except Exception as exc:
        return False, f"HF Inference indisponível: {exc}"


def _zerogpu_healthy(settings: Settings) -> tuple[bool, str]:
    try:
        import spaces  # noqa: F401
        import torch  # noqa: F401
        from transformers import AutoModelForCausalLM  # noqa: F401
    except ImportError as exc:
        return False, f"Dependências ZeroGPU ausentes: {exc}"

    model = settings.zerogpu_model
    return True, f"ZeroGPU local (modelo: {model})"


def resolve_backend(settings: Settings) -> str:
    backend = settings.llm_backend
    if backend in {"ollama", "hf", "zerogpu"}:
        return backend
    # auto
    ok, _ = _ollama_healthy(settings)
    if ok:
        return "ollama"
    if settings.on_spaces:
        return "zerogpu"
    return "hf"


def check_llm_health(settings: Settings) -> tuple[bool, str]:
    backend = resolve_backend(settings)
    if backend == "ollama":
        ok, msg = _ollama_healthy(settings)
        return ok, f"[Ollama] {msg}"
    if backend == "zerogpu":
        ok, msg = _zerogpu_healthy(settings)
        return ok, f"[ZeroGPU] {msg}"
    ok, msg = _hf_healthy(settings)
    return ok, f"[HF] {msg}"


# Compatibilidade com imports antigos
def check_ollama_health(settings: Settings) -> tuple[bool, str]:
    return check_llm_health(settings)


def _chat_ollama(
    settings: Settings,
    messages: list[ChatMessage],
    system_prompt: str | None,
    temperature: float,
) -> str:
    payload_messages = []
    if system_prompt:
        payload_messages.append({"role": "system", "content": system_prompt})
    payload_messages.extend(
        {"role": message.role, "content": message.content} for message in messages
    )

    data = _request_json(
        settings,
        "POST",
        "/api/chat",
        {
            "model": settings.ollama_chat_model,
            "messages": payload_messages,
            "stream": False,
            "options": {"temperature": temperature},
        },
        timeout=600,
    )
    message = data.get("message", {})
    content = message.get("content", "").strip()
    if not content:
        raise OllamaError("O modelo de chat retornou resposta vazia.")
    return content


def _chat_hf(
    settings: Settings,
    messages: list[ChatMessage],
    system_prompt: str | None,
    temperature: float,
) -> str:
    try:
        from huggingface_hub import InferenceClient
    except ImportError as exc:
        raise OllamaError("huggingface_hub não instalado.") from exc

    if not settings.hf_token:
        raise OllamaError(
            "HF_TOKEN não configurado. No Space: Settings → Secrets → HF_TOKEN."
        )

    payload_messages = []
    if system_prompt:
        payload_messages.append({"role": "system", "content": system_prompt})
    payload_messages.extend(
        {"role": message.role, "content": message.content} for message in messages
    )

    client = InferenceClient(token=settings.hf_token)
    try:
        completion = client.chat.completions.create(
            model=settings.hf_model,
            messages=payload_messages,
            temperature=temperature,
            max_tokens=2048,
        )
        content = (completion.choices[0].message.content or "").strip()
    except Exception as exc:
        err = str(exc)
        if "402" in err or "Payment Required" in err or "depleted" in err.lower():
            raise OllamaError(
                "Créditos do Hugging Face Inference Providers esgotados (HTTP 402). "
                "No Space, use LLM_BACKEND=zerogpu (inferência gratuita na ZeroGPU). "
                "Localmente, use Ollama (LLM_BACKEND=ollama)."
            ) from exc
        raise OllamaError(f"Falha na inferência HF ({settings.hf_model}): {exc}") from exc

    if not content:
        raise OllamaError("O modelo HF retornou resposta vazia.")
    return content


def _chat_zerogpu(
    settings: Settings,
    messages: list[ChatMessage],
    system_prompt: str | None,
    temperature: float,
) -> str:
    # Import sob demanda: evita carregar o modelo no Streamlit/intranet local.
    from conformidade.zerogpu_llm import generate_chat

    payload_messages: list[dict[str, str]] = []
    if system_prompt:
        payload_messages.append({"role": "system", "content": system_prompt})
    payload_messages.extend(
        {"role": message.role, "content": message.content} for message in messages
    )

    try:
        content = generate_chat(
            payload_messages,
            temperature=temperature,
            max_new_tokens=512 if settings.on_spaces else 1024,
        ).strip()
    except Exception as exc:
        err = str(exc)
        if "Expired ZeroGPU" in err or "proxy token" in err.lower():
            raise OllamaError(
                "Lease da ZeroGPU expirou (~60s/chamada no free tier). "
                "Entre em huggingface.co, recarregue a página do Space e tente de novo; "
                "pacotes grandes podem precisar de mais de uma tentativa. "
                f"Detalhe: {exc}"
            ) from exc
        raise OllamaError(
            f"Falha na inferência ZeroGPU ({settings.zerogpu_model}): {exc}"
        ) from exc

    if not content:
        raise OllamaError("O modelo ZeroGPU retornou resposta vazia.")
    return content


def chat_completion(
    settings: Settings,
    messages: list[ChatMessage],
    system_prompt: str | None = None,
    temperature: float = 0.1,
) -> str:
    backend = resolve_backend(settings)
    if backend == "ollama":
        return _chat_ollama(settings, messages, system_prompt, temperature)
    if backend == "zerogpu":
        return _chat_zerogpu(settings, messages, system_prompt, temperature)
    return _chat_hf(settings, messages, system_prompt, temperature)
