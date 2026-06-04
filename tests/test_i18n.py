from src.telegram.i18n import t, TRANSLATIONS


def test_t_returns_english_by_default():
    assert t("help") == "❓ Help"


def test_t_returns_amharic():
    assert t("help", "am") == "❓ እገዛ"


def test_t_falls_back_to_english_for_missing_key():
    assert t("nonexistent_key", "am") == "nonexistent_key"


def test_t_falls_back_to_english_for_unknown_lang():
    assert t("help", "fr") == "❓ Help"


def test_all_keys_have_amharic():
    for key in TRANSLATIONS["en"]:
        assert key in TRANSLATIONS["am"], f"Missing Amharic translation for '{key}'"


def test_no_extra_keys_in_amharic():
    for key in TRANSLATIONS["am"]:
        assert key in TRANSLATIONS["en"], f"Extra key in Amharic: '{key}'"
