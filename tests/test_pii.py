from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_supported_pii_types() -> None:
    text = " ".join(
        [
            "0987654321",
            "012345678901",
            "4111 1111 1111 1111",
            "B1234567",
            "192.168.1.20",
            "123-45-6789",
        ]
    )
    out = scrub_text(text)
    for marker in (
        "REDACTED_PHONE_VN",
        "REDACTED_CCCD",
        "REDACTED_CREDIT_CARD",
        "REDACTED_PASSPORT",
        "REDACTED_IP_ADDRESS",
        "REDACTED_SSN",
    ):
        assert marker in out
