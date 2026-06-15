from fastapi.testclient import TestClient

from app.agent import AgentResult
from app.main import agent, app


def test_chat_propagates_correlation_id(monkeypatch) -> None:
    monkeypatch.setattr(
        agent,
        "run",
        lambda **_: AgentResult(
            answer="test answer",
            latency_ms=10,
            tokens_in=5,
            tokens_out=6,
            cost_usd=0.001,
            quality_score=0.8,
        ),
    )
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            headers={"x-request-id": "req-test0001"},
            json={
                "user_id": "u-test",
                "session_id": "s-test",
                "feature": "qa",
                "message": "hello",
            },
        )
    assert response.status_code == 200
    assert response.json()["correlation_id"] == "req-test0001"
    assert response.headers["x-request-id"] == "req-test0001"
    assert "x-response-time-ms" in response.headers


def test_dashboard_has_six_panels() -> None:
    with TestClient(app) as client:
        response = client.get("/dashboard")
    assert response.status_code == 200
    assert response.text.count('class="card"') == 6
    assert "P95 SLO" in response.text
