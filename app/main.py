from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from structlog.contextvars import bind_contextvars

from .agent import LabAgent
from .incidents import disable, enable, status
from .logging_config import configure_logging, get_logger
from .metrics import record_error, snapshot
from .middleware import CorrelationIdMiddleware
from .pii import hash_user_id, summarize_text
from .schemas import ChatRequest, ChatResponse
from .tracing import flush_traces, tracing_enabled

configure_logging()
log = get_logger()


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info(
        "app_started",
        service=os.getenv("APP_NAME", "day13-observability-lab"),
        env=os.getenv("APP_ENV", "dev"),
        correlation_id="system",
        payload={"tracing_enabled": tracing_enabled()},
    )
    yield
    flush_traces()


app = FastAPI(title="Day 13 Observability Lab", lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)
agent = LabAgent()


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "tracing_enabled": tracing_enabled(), "incidents": status()}


@app.get("/metrics")
async def metrics() -> dict:
    return snapshot()


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    return HTMLResponse(_dashboard_html())


@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    # Enrich logs with request context (user_id_hash, session_id, feature, model, env)
    bind_contextvars(
        user_id_hash=hash_user_id(body.user_id),
        session_id=body.session_id,
        feature=body.feature,
        model=agent.model,
        env=os.getenv("APP_ENV", "dev"),
    )
    
    log.info(
        "request_received",
        service="api",
        payload={"message_preview": summarize_text(body.message)},
    )
    try:
        result = agent.run(
            user_id=body.user_id,
            feature=body.feature,
            session_id=body.session_id,
            message=body.message,
            correlation_id=request.state.correlation_id,
        )
        log.info(
            "response_sent",
            service="api",
            latency_ms=result.latency_ms,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_usd=result.cost_usd,
            payload={"answer_preview": summarize_text(result.answer)},
        )
        return ChatResponse(
            answer=result.answer,
            correlation_id=request.state.correlation_id,
            latency_ms=result.latency_ms,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_usd=result.cost_usd,
            quality_score=result.quality_score,
        )
    except Exception as exc:  # pragma: no cover
        error_type = type(exc).__name__
        record_error(error_type)
        log.error(
            "request_failed",
            service="api",
            error_type=error_type,
            payload={"detail": str(exc), "message_preview": summarize_text(body.message)},
        )
        raise HTTPException(status_code=500, detail=error_type) from exc


@app.post("/incidents/{name}/enable")
async def enable_incident(name: str) -> JSONResponse:
    try:
        enable(name)
        log.warning("incident_enabled", service="control", payload={"name": name})
        return JSONResponse({"ok": True, "incidents": status()})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _dashboard_html() -> str:
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Day 13 Observability Dashboard</title>
<style>
body{font-family:Arial,sans-serif;background:#0b1220;color:#e5e7eb;margin:0;padding:24px}
h1{margin:0 0 6px}.sub{color:#94a3b8;margin-bottom:20px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.card{background:#162033;border:1px solid #334155;border-radius:12px;padding:18px;min-height:125px}.label{color:#94a3b8;font-size:14px}.value{font-size:30px;font-weight:700;margin:14px 0 8px}.ok{color:#34d399}.warn{color:#fbbf24}.unit{font-size:14px;color:#94a3b8}
@media(max-width:800px){.grid{grid-template-columns:1fr}}
</style></head><body><h1>Agent Observability</h1><div class="sub">Auto-refresh: 15 seconds | SLO window: 28 days</div>
<div class="grid">
<div class="card"><div class="label">Latency P50 / P95 / P99</div><div class="value" id="latency">-</div><div class="unit">ms | P95 SLO &lt; 3000 ms</div></div>
<div class="card"><div class="label">Traffic</div><div class="value" id="traffic">-</div><div class="unit">successful requests</div></div>
<div class="card"><div class="label">Error Rate</div><div class="value" id="errors">-</div><div class="unit" id="error-types">SLO &lt; 2%</div></div>
<div class="card"><div class="label">Total Cost</div><div class="value" id="cost">-</div><div class="unit">USD | daily budget &lt; $2.50</div></div>
<div class="card"><div class="label">Tokens In / Out</div><div class="value" id="tokens">-</div><div class="unit">tokens</div></div>
<div class="card"><div class="label">Quality Proxy</div><div class="value" id="quality">-</div><div class="unit">target &gt;= 0.75</div></div>
</div><script>
async function refresh(){const m=await fetch('/metrics').then(r=>r.json());
document.getElementById('latency').textContent=`${m.latency_p50} / ${m.latency_p95} / ${m.latency_p99}`;
document.getElementById('traffic').textContent=m.traffic;
const e=document.getElementById('errors');e.textContent=`${m.error_rate_pct}%`;e.className='value '+(m.error_rate_pct<2?'ok':'warn');
document.getElementById('error-types').textContent=JSON.stringify(m.error_breakdown);
document.getElementById('cost').textContent=`$${m.total_cost_usd}`;
document.getElementById('tokens').textContent=`${m.tokens_in_total} / ${m.tokens_out_total}`;
const q=document.getElementById('quality');q.textContent=m.quality_avg;q.className='value '+(m.quality_avg>=0.75?'ok':'warn');}
refresh();setInterval(refresh,15000);
</script></body></html>"""


@app.post("/incidents/{name}/disable")
async def disable_incident(name: str) -> JSONResponse:
    try:
        disable(name)
        log.warning("incident_disabled", service="control", payload={"name": name})
        return JSONResponse({"ok": True, "incidents": status()})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
