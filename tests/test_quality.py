from app.mock_llm import FakeLLM
from app.mock_rag import retrieve


def _answer(question: str) -> str:
    docs = retrieve(question)
    return FakeLLM().generate(f"Feature=qa\nDocs={docs}\nQuestion={question}").text.lower()


def test_expected_answer_keywords() -> None:
    cases = {
        "What is your refund policy?": ("7 days", "proof of purchase"),
        "Explain why metrics traces and logs work together": ("metrics", "traces", "logs"),
        "What should not appear in app logs?": ("pii", "sensitive"),
    }
    for question, expected in cases.items():
        answer = _answer(question)
        assert all(keyword in answer for keyword in expected)
