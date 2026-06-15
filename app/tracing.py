from __future__ import annotations

import os
from typing import Any

class DummyClient:
    def update_current_trace(self, **kwargs: Any) -> None:
        pass

    def update_current_span(self, **kwargs: Any) -> None:
        pass

    def update_current_generation(self, **kwargs: Any) -> None:
        pass

    def flush(self) -> None:
        pass

if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
    def observe(*args: Any, **kwargs: Any):
        def decorator(func):
            return func
        return decorator

    langfuse_client = DummyClient()
else:
    try:
        from langfuse import observe, get_client
        langfuse_client = get_client()
    except Exception:  # pragma: no cover
        def observe(*args: Any, **kwargs: Any):
            def decorator(func):
                return func
            return decorator

        langfuse_client = DummyClient()

def get_langfuse_client():
    return langfuse_client

def tracing_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))
