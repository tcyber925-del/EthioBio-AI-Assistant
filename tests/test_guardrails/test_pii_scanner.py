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
