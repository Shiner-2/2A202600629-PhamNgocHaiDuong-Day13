# Day 13 Observability Lab Report

> **Instruction**: Fill in all sections below. This report is designed to be parsed by an automated grading assistant. Ensure all tags (e.g., `[GROUP_NAME]`) are preserved.

## 1. Team Metadata
- [GROUP_NAME]: Day 13 Observability Lab - 2A202600629 Pham Ngoc Hai Duong
- [REPO_URL]: https://github.com/vinuni-student/day13-observability
- [MEMBERS]:
  - Member A: Pham Ngoc Hai Duong | Role: Logging & PII
  - Member B: Pham Ngoc Hai Duong | Role: Tracing & Enrichment
  - Member C: Pham Ngoc Hai Duong | Role: SLO & Alerts
  - Member D: Pham Ngoc Hai Duong | Role: Load Test & Dashboard
  - Member E: Pham Ngoc Hai Duong | Role: Demo & Report

---

## 2. Group Performance (Auto-Verified)
- [VALIDATE_LOGS_FINAL_SCORE]: 100/100
- [TOTAL_TRACES_COUNT]: 15
- [PII_LEAKS_FOUND]: 0 

---

## 3. Technical Evidence (Group)

### 3.1 Logging & Tracing
- [EVIDENCE_CORRELATION_ID_SCREENSHOT]: evidence/correlation_id.png
- [EVIDENCE_PII_REDACTION_SCREENSHOT]: evidence/pii_redaction.png
- [EVIDENCE_TRACE_WATERFALL_SCREENSHOT]: evidence/trace_waterfall.png
- [TRACE_WATERFALL_EXPLANATION]: The trace shows an end-to-end request flow where the agent.run() span contains sub-spans for retrieve() (RAG document fetching) and llm.generate() (LLM inference). Each span is tagged with correlation_id for distributed tracing. PII in prompts and responses are automatically redacted at the logging layer.

### 3.2 Dashboard & SLOs
- [DASHBOARD_6_PANELS_SCREENSHOT]: evidence/dashboard_6panel.png
- [SLO_TABLE]:
| SLI | Target | Window | Current Value |
|---|---:|---|---:|
| Latency P95 | < 3000ms | 28d | 245ms |
| Error Rate | < 2% | 28d | 0% |
| Cost Budget | < $2.5/day | 1d | $0.02 |
| Quality Score | > 0.6 | 1d | 0.68 |
| Token Usage | < 1M/day | 1d | 8,200 |
| PII Leak Rate | 0% | 28d | 0% |

### 3.3 Alerts & Runbook
- [ALERT_RULES_SCREENSHOT]: evidence/alert_rules.png
- [SAMPLE_RUNBOOK_LINK]: docs/alerts.md#high-latency-alert

---

## 4. Incident Response (Group)
- [SCENARIO_NAME]: rag_slow (RAG Retrieval Latency Spike)
- [SYMPTOMS_OBSERVED]: Requests to /chat endpoint returned latency > 5000ms; quality_score dropped below 0.5
- [ROOT_CAUSE_PROVED_BY]: Trace ID: trace-rag-slow-001 showed retrieve() span took 4200ms (vs normal 50ms); logs showed no PII leaks during incident
- [FIX_ACTION]: Disabled slow RAG toggle via /incidents/rag_slow/disable endpoint; latency returned to baseline within 30s
- [PREVENTIVE_MEASURE]: Added P95 latency alert at 3000ms threshold; configured SLO error budget tracking 

---

## 5. Individual Contributions & Evidence

### Pham Ngoc Hai Duong (All Roles)
- [TASKS_COMPLETED]: 
  - Logging & PII: Implemented correlation ID middleware, enabled PII scrubber for email/phone/CCCD/credit_card/passport patterns
  - Tracing & Enrichment: Fixed langfuse import to work with v3.2.1 API, bound user_id_hash/session_id/feature/model/env to all requests
  - SLO & Alerts: Configured 6 SLO targets, set up alert rules for latency/error_rate/cost_budget
  - Load Test & Dashboard: Generated 15+ requests via load_test.py, verified correlation ID propagation and metrics collection
  - Demo & Report: Completed blueprint report, validated logging output, confirmed 100/100 test score

- [EVIDENCE_LINK]: 
  - app/middleware.py (Correlation ID implementation)
  - app/logging_config.py (PII scrubbing enabled)
  - app/main.py (Request enrichment with contextvars)
  - app/tracing.py (Langfuse API integration)
  - app/pii.py (Extended PII patterns) 

---

## 6. Bonus Items (Optional)
- [BONUS_COST_OPTIMIZATION]: Implemented token usage tracking and cost per request calculation; total cost for 15 requests was $0.02 (avg $0.0013/req) using mock LLM
- [BONUS_AUDIT_LOGS]: Created audit trail with correlation ID binding to all logs; enables 100% traceability of user actions
- [BONUS_CUSTOM_METRIC]: Added quality_score metric (heuristic: presence of docs + answer length + term matching); tracks model output quality independent of latency
