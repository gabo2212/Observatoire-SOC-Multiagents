"""OpenAI-compatible client for local llama-server (Heretic GGUF)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openai import OpenAI

import config


@dataclass
class LLMResult:
    content: str
    tokens_in: int
    tokens_out: int
    model: str
    raw: Any = None


def get_client() -> OpenAI:
    return OpenAI(base_url=config.OPENAI_API_BASE, api_key=config.OPENAI_API_KEY)


def llm_ready(timeout: float = 2.0) -> bool:
    try:
        client = get_client()
        client.models.list()
        return True
    except Exception:
        return False


def chat(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.7,
    max_tokens: int = 700,
    model: str | None = None,
) -> LLMResult:
    """Call chat completions with Qwen3.6 thinking disabled."""
    client = get_client()
    model_name = model or config.LLM_MODEL
    resp = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    choice = resp.choices[0].message.content or ""
    usage = resp.usage
    tin = int(getattr(usage, "prompt_tokens", 0) or 0)
    tout = int(getattr(usage, "completion_tokens", 0) or 0)
    return LLMResult(
        content=choice.strip(),
        tokens_in=tin,
        tokens_out=tout,
        model=model_name,
        raw=resp,
    )


def estimate_cost(tokens_in: int, tokens_out: int) -> float:
    return (tokens_in / 1_000_000.0) * config.COST_PER_1M_INPUT + (
        tokens_out / 1_000_000.0
    ) * config.COST_PER_1M_OUTPUT


def smoke_test() -> str:
    result = chat(
        [
            {"role": "system", "content": "Tu es un assistant SOC concis."},
            {"role": "user", "content": "Réponds uniquement: OK"},
        ],
        max_tokens=16,
        temperature=0.1,
    )
    return result.content
