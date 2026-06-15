from app.mock_llm import FakeLLM


def test_fake_llm_uses_retrieved_context() -> None:
    response = FakeLLM().generate(
        "Feature=qa\nDocs=['Refunds are available within 7 days with proof of purchase.']\nQuestion=Refund?"
    )
    assert "7 days" in response.text
    assert "proof of purchase" in response.text
