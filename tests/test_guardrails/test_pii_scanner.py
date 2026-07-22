from src.guardrails.output.pii_scanner import PIIScanner


def test_no_pii():
    s = PIIScanner()
    result = s.scan("Mitochondria produce ATP through cellular respiration.")
    assert not result.flagged


def test_email_detected():
    s = PIIScanner()
    result = s.scan("Contact me at student@school.com for help.")
    assert result.flagged
    assert any(f["type"] == "email" for f in result.findings)


def test_phone_detected():
    s = PIIScanner()
    result = s.scan("Call me at 555-123-4567")
    assert result.flagged
    assert any(f["type"] == "phone" for f in result.findings)


def test_ethiopian_phone():
    s = PIIScanner()
    result = s.scan("Reach me at +251911234567")
    assert result.flagged
    assert any(f["type"] == "ethiopian_phone" for f in result.findings)


def test_pii_redaction_email():
    scanner = PIIScanner()
    text = "Contact me at student@school.com for help"
    result = scanner.scan(text, redact=True)
    assert result.flagged
    assert "student@school.com" not in result.redacted_text
    assert "[REDACTED email]" in result.redacted_text


def test_pii_redaction_phone():
    scanner = PIIScanner()
    text = "Call +251911234567 for help"
    result = scanner.scan(text, redact=True)
    assert result.flagged
    assert "[REDACTED ethiopian_phone]" in result.redacted_text


def test_pii_redaction_disabled():
    scanner = PIIScanner()
    text = "Email me at test@test.com"
    result = scanner.scan(text, redact=False)
    assert result.flagged
    assert result.redacted_text == text


def test_pii_no_pii():
    scanner = PIIScanner()
    text = "What is the function of mitochondria?"
    result = scanner.scan(text, redact=True)
    assert not result.flagged
    assert result.redacted_text == text


def test_pii_multiple_redactions():
    scanner = PIIScanner()
    text = "Email: user@example.com, Phone: +251911234567"
    result = scanner.scan(text, redact=True)
    assert "[REDACTED email]" in result.redacted_text
    assert "[REDACTED ethiopian_phone]" in result.redacted_text
    assert "user@example.com" not in result.redacted_text


def test_pii_overlapping_patterns():
    """Two patterns matching overlapping text should both be handled."""
    scanner = PIIScanner()
    text = "Card: 4111 1111 1111 1111"
    result = scanner.scan(text, redact=True)
    assert "[REDACTED credit_card]" in result.redacted_text
    assert "4111" not in result.redacted_text
