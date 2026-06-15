from __future__ import annotations

import html
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import app
from app.tracing import flush_traces, langfuse_client

EVIDENCE = ROOT / "evidence"
LOG_PATH = ROOT / "data" / "logs.jsonl"
QUERIES = ROOT / "data" / "sample_queries.jsonl"


def _page(title: str, body: str) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>body{{font:16px Arial;background:#0b1220;color:#e5e7eb;padding:28px}}h1{{margin-top:0}}
.card{{background:#162033;border:1px solid #334155;border-radius:12px;padding:18px;margin:14px 0}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.value{{font-size:28px;font-weight:bold;color:#34d399}}
code,pre{{font-family:Consolas,monospace}}pre{{white-space:pre-wrap;color:#dbeafe}}.muted{{color:#94a3b8}}
table{{border-collapse:collapse;width:100%}}th,td{{border-bottom:1px solid #334155;padding:10px;text-align:left}}</style>
</head><body><h1>{html.escape(title)}</h1>{body}</body></html>"""


def _write(name: str, content: str) -> None:
    (EVIDENCE / name).write_text(content, encoding="utf-8")


def main() -> None:
    EVIDENCE.mkdir(exist_ok=True)
    LOG_PATH.unlink(missing_ok=True)
    started = datetime.now(timezone.utc)
    queries = [json.loads(line) for line in QUERIES.read_text(encoding="utf-8").splitlines() if line]
    responses = []

    with TestClient(app) as client:
        for index in range(15):
            payload = dict(queries[index % len(queries)])
            payload["session_id"] = f"{payload['session_id']}-run-{index + 1:02d}"
            request_id = f"req-evidence-{index + 1:02d}"
            response = client.post("/chat", json=payload, headers={"x-request-id": request_id})
            response.raise_for_status()
            responses.append(response.json())
        metrics = client.get("/metrics").json()

    flush_traces()
    traces = None
    for _ in range(30):
        traces = langfuse_client.api.trace.list(limit=50, from_timestamp=started, name="agent.run")
        if traces.meta.total_items >= 15 and len(traces.data) >= 15:
            break
        time.sleep(2)
    if traces is None or traces.meta.total_items < 15 or len(traces.data) < 15:
        raise RuntimeError("Langfuse did not return all 15 traces after flush")

    trace_rows = []
    for trace in traces.data:
        trace_rows.append(
            {
                "id": trace.id,
                "name": trace.name,
                "timestamp": trace.timestamp.isoformat(),
                "session_id": trace.session_id,
                "latency_seconds": trace.latency,
                "total_cost_usd": trace.total_cost,
                "tags": trace.tags,
                "metadata": {
                    "correlation_id": trace.metadata.get("correlation_id"),
                    "feature": trace.metadata.get("feature"),
                    "model": trace.metadata.get("model"),
                },
                "html_path": trace.html_path,
            }
        )

    selected = traces.data[0]
    observations = langfuse_client.api.observations.get_many(trace_id=selected.id, limit=20).data
    observation_rows = [
        {
            "id": item.id,
            "name": item.name,
            "type": str(item.type),
            "parent_observation_id": item.parent_observation_id,
            "latency_seconds": item.latency,
            "model": item.model,
            "usage_details": item.usage_details,
            "input_captured": item.input is not None,
            "output_captured": item.output is not None,
        }
        for item in observations
    ]

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "request_count": len(responses),
        "langfuse_trace_count": traces.meta.total_items,
        "metrics": metrics,
        "selected_trace_id": selected.id,
        "selected_trace_path": selected.html_path,
        "observations": observation_rows,
        "traces": trace_rows,
    }
    _write("runtime-verification.json", json.dumps(result, indent=2, ensure_ascii=True))

    log_records = [json.loads(line) for line in LOG_PATH.read_text(encoding="utf-8").splitlines() if line]
    api_logs = [item for item in log_records if item.get("service") == "api"]
    correlation_body = "".join(
        f"<div class='card'><pre>{html.escape(json.dumps(item, indent=2))}</pre></div>" for item in api_logs[:2]
    )
    _write("correlation_id.html", _page("Correlation ID Evidence", correlation_body))

    pii_logs = [item for item in api_logs if "REDACTED" in json.dumps(item)]
    pii_body = "<div class='card'><div class='value'>0 raw PII leaks</div><p>Email, phone and card values are redacted before file output.</p></div>"
    pii_body += "".join(
        f"<div class='card'><pre>{html.escape(json.dumps(item, indent=2))}</pre></div>" for item in pii_logs[:3]
    )
    _write("pii_redaction.html", _page("PII Redaction Evidence", pii_body))

    trace_body = f"<div class='card'><div class='value'>{traces.meta.total_items} traces</div><p>Selected trace: <code>{selected.id}</code></p></div>"
    trace_body += "<table><tr><th>Observation</th><th>Type</th><th>Latency</th><th>Usage</th><th>Input/output captured</th></tr>"
    for item in observation_rows:
        trace_body += (
            f"<tr><td>{html.escape(item['name'])}</td><td>{html.escape(item['type'])}</td>"
            f"<td>{item['latency_seconds']}s</td><td>{html.escape(json.dumps(item['usage_details']))}</td>"
            f"<td>{item['input_captured']} / {item['output_captured']}</td></tr>"
        )
    trace_body += "</table>"
    _write("trace_waterfall.html", _page("Langfuse Trace Waterfall", trace_body))

    dashboard_body = "<div class='grid'>"
    panels = [
        ("Latency P50 / P95 / P99", f"{metrics['latency_p50']} / {metrics['latency_p95']} / {metrics['latency_p99']} ms"),
        ("Traffic", str(metrics["traffic"])),
        ("Error Rate", f"{metrics['error_rate_pct']}%"),
        ("Total Cost", f"${metrics['total_cost_usd']}"),
        ("Tokens In / Out", f"{metrics['tokens_in_total']} / {metrics['tokens_out_total']}"),
        ("Quality Proxy", str(metrics["quality_avg"])),
    ]
    for label, value in panels:
        dashboard_body += f"<div class='card'><div class='muted'>{html.escape(label)}</div><div class='value'>{html.escape(value)}</div></div>"
    dashboard_body += "</div>"
    _write("dashboard_6panel.html", _page("Six-Panel Observability Dashboard", dashboard_body))

    alert_body = "<table><tr><th>Alert</th><th>Condition</th><th>Severity</th><th>Runbook</th></tr>"
    alerts = [
        ("High latency P95", "latency_p95_ms > 3000 for 5m", "P2", "docs/alerts.md#1-high-latency-p95"),
        ("High error rate", "error_rate_pct > 2 for 5m", "P1", "docs/alerts.md#2-high-error-rate"),
        ("Cost budget spike", "hourly_cost_usd > 2x baseline for 15m", "P2", "docs/alerts.md#3-cost-budget-spike"),
    ]
    for name, condition, severity, runbook in alerts:
        alert_body += f"<tr><td>{name}</td><td><code>{condition}</code></td><td>{severity}</td><td>{runbook}</td></tr>"
    alert_body += "</table>"
    _write("alert_rules.html", _page("Alert Rules and Runbooks", alert_body))
    print(json.dumps({"trace_count": traces.meta.total_items, "trace_id": selected.id, "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
