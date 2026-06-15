from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

try:
    from langfuse import get_client, observe

    langfuse_client = get_client()
except Exception:  # pragma: no cover - keeps the lab runnable without Langfuse
    langfuse_client = None

    def observe(*args: Any, **kwargs: Any) -> Callable:
        def decorator(func: Callable) -> Callable:
            return func

        return decorator


def tracing_enabled() -> bool:
    return bool(
        langfuse_client
        and os.getenv("LANGFUSE_PUBLIC_KEY")
        and os.getenv("LANGFUSE_SECRET_KEY")
    )


def update_current_trace(**kwargs: Any) -> None:
    if tracing_enabled():
        langfuse_client.update_current_trace(**kwargs)


def update_current_span(**kwargs: Any) -> None:
    if tracing_enabled():
        langfuse_client.update_current_span(**kwargs)


def update_current_generation(**kwargs: Any) -> None:
    if tracing_enabled():
        langfuse_client.update_current_generation(**kwargs)


def score_current_trace(name: str, value: float) -> None:
    if tracing_enabled():
        langfuse_client.score_current_trace(name=name, value=value)


def flush_traces() -> None:
    if tracing_enabled():
        langfuse_client.flush()
