import json
from pathlib import Path

from src.telegram.i18n import _get, _messages, t


def _clear_cache():
    _messages.clear()


def test_en_and_am_have_same_keys():
    base = Path(__file__).parent.parent / "src" / "telegram" / "messages"
    with open(base / "en.json") as f:
        en = json.load(f)
    with open(base / "am.json") as f:
        am = json.load(f)

    def extract_keys(d, prefix=""):
        ks = set()
        for k, v in d.items():
            if isinstance(v, dict):
                ks |= extract_keys(v, f"{prefix}{k}.")
            else:
                ks.add(f"{prefix}{k}")
        return ks

    en_keys = extract_keys(en)
    am_keys = extract_keys(am)
    assert en_keys == am_keys, (
        f"Key mismatch. Missing in am: {en_keys - am_keys}. Extra in am: {am_keys - en_keys}"
    )


def test_t_returns_flat_key():
    _clear_cache()
    result = t("ask_question")
    assert "Ask a Question" in result


def test_t_returns_amharic():
    _clear_cache()
    result = t("ask_question", "am")
    assert "ጥያቄ" in result


def test_t_returns_namespaced():
    _clear_cache()
    result = t("help.text")
    assert "EthioSci" in result


def test_t_interpolation():
    _clear_cache()
    result = t("tutor.grade_prompt", "en", grade=7)
    assert "Grade 7" in result


def test_t_missing_key_returns_key():
    _clear_cache()
    result = t("completely.bogus.key")
    assert result == "completely.bogus.key"


def test_t_missing_lang_falls_back_to_english():
    _clear_cache()
    result = t("help.text", "xx")
    assert "EthioSci" in result


def test_get_flat_key():
    d = {"foo": "bar"}
    assert _get(d, "foo") == "bar"


def test_get_nested_key():
    d = {"a": {"b": {"c": "val"}}}
    assert _get(d, "a.b.c") == "val"


def test_get_missing():
    assert _get({}, "x.y") is None
    assert _get({"a": "str"}, "a.b") is None
