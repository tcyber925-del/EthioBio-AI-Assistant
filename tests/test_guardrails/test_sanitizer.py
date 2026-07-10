from src.guardrails.input.sanitizer import InputSanitizer


def test_sanitizer_removes_control_chars():
    s = InputSanitizer()
    assert s.sanitize("hello\x00world") == "helloworld"


def test_sanitizer_strips_whitespace():
    s = InputSanitizer()
    assert s.sanitize("  hello  ") == "hello"


def test_sanitizer_normalizes_nfc():
    s = InputSanitizer()
    result = s.sanitize("café")
    assert result == "café"


def test_sanitizer_truncates_long_input():
    s = InputSanitizer()
    long_str = "a" * 5000
    result = s.sanitize(long_str)
    assert len(result) <= s.MAX_INPUT_LENGTH


def test_validate_length_empty():
    s = InputSanitizer()
    assert not s.validate_length("")


def test_validate_length_valid():
    s = InputSanitizer()
    assert s.validate_length("valid message")


def test_validate_length_too_long():
    s = InputSanitizer()
    assert not s.validate_length("a" * 5000)
