from __future__ import annotations

import os
from typing import Any

try:
    from langfuse import Langfuse, observe
    
    # Initialize Langfuse client
    langfuse_client = Langfuse()
    
    # Create a simple context wrapper to match the expected API
    class LangfuseContextWrapper:
        def __init__(self, client: Langfuse):
            self.client = client
        
        def update_current_trace(self, **kwargs: Any) -> None:
            try:
                self.client.update_current_trace(**kwargs)
            except Exception:
                pass
        
        def update_current_observation(self, **kwargs: Any) -> None:
            try:
                self.client.update_current_observation(**kwargs)
            except Exception:
                pass
    
    langfuse_context = LangfuseContextWrapper(langfuse_client)
    
except Exception:  # pragma: no cover
    def observe(*args: Any, **kwargs: Any):
        def decorator(func):
            return func
        return decorator

    class _DummyContext:
        def update_current_trace(self, **kwargs: Any) -> None:
            return None

        def update_current_observation(self, **kwargs: Any) -> None:
            return None

    langfuse_context = _DummyContext()


def tracing_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))
