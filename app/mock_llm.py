from __future__ import annotations

import time
from dataclasses import dataclass

from .incidents import STATE
from .tracing import observe, update_current_generation


@dataclass
class FakeUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class FakeResponse:
    text: str
    usage: FakeUsage
    model: str


class FakeLLM:
    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model

    @observe(name="llm.generate", as_type="generation", capture_input=False, capture_output=False)
    def generate(self, prompt: str) -> FakeResponse:
        time.sleep(0.15)
        input_tokens = max(20, len(prompt) // 4)
        docs = next((line.removeprefix("Docs=") for line in prompt.splitlines() if line.startswith("Docs=")), "")
        answer = f"Based on the retrieved context: {docs}"
        output_tokens = max(20, len(answer) // 4)
        if STATE["cost_spike"]:
            output_tokens *= 4
        update_current_generation(
            model=self.model,
            usage_details={"input": input_tokens, "output": output_tokens},
            metadata={"mock": True, "cost_spike": STATE["cost_spike"]},
        )
        return FakeResponse(text=answer, usage=FakeUsage(input_tokens, output_tokens), model=self.model)
