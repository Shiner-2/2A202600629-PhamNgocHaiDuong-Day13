from __future__ import annotations

import time

from .incidents import STATE
from .tracing import observe, update_current_span

CORPUS = {
    "refund": ["Refunds are available within 7 days with proof of purchase."],
    "monitoring": ["Metrics detect incidents, traces localize them, logs explain root cause."],
    "policy": ["Do not expose PII or other sensitive data in logs. Use sanitized summaries only."],
}

TOPIC_KEYWORDS = {
    "refund": ("refund",),
    "policy": ("policy", "pii", "sensitive", "credit card", "phone", "should not appear", "logged"),
    "monitoring": ("monitoring", "metrics", "traces", "observability", "latency", "alerts"),
}


@observe(name="rag.retrieve", capture_input=False, capture_output=False)
def retrieve(message: str) -> list[str]:
    if STATE["tool_fail"]:
        raise RuntimeError("Vector store timeout")
    if STATE["rag_slow"]:
        time.sleep(3.5)
    lowered = message.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            docs = CORPUS[topic]
            update_current_span(metadata={"matched_topic": topic, "doc_count": len(docs)})
            return docs
    update_current_span(metadata={"matched_topic": None, "doc_count": 1})
    return ["No domain document matched. Use general fallback answer."]
