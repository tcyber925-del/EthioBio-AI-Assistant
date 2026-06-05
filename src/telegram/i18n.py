import json
from pathlib import Path


_messages: dict[str, dict] = {}


def _load_messages():
    base = Path(__file__).parent / "messages"
    for lang in ["en", "am"]:
        with open(base / f"{lang}.json") as f:
            _messages[lang] = json.load(f)


def _get(msg: dict, key: str) -> str | None:
    parts = key.split(".")
    for part in parts:
        if not isinstance(msg, dict):
            return None
        msg = msg.get(part)
    return msg if isinstance(msg, str) else None


def t(key: str, lang: str = "en", **kwargs) -> str:
    if not _messages:
        _load_messages()
    val = _get(_messages.get(lang, {}), key)
    if val is None:
        val = _get(_messages.get("en", {}), key)
    if val is None:
        return key
    return val.format(**kwargs) if kwargs else val
