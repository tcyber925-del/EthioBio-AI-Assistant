import pytest
from src.schemas.common import LanguageEnum


def test_enum_values():
    assert LanguageEnum.EN.value == "en"
    assert LanguageEnum.AM.value == "am"
    assert LanguageEnum.BOTH.value == "both"


def test_is_amharic():
    assert LanguageEnum.AM.is_amharic()
    assert not LanguageEnum.EN.is_amharic()
    assert not LanguageEnum.BOTH.is_amharic()


def test_is_bilingual():
    assert LanguageEnum.BOTH.is_bilingual()
    assert not LanguageEnum.EN.is_bilingual()
    assert not LanguageEnum.AM.is_bilingual()


def test_is_english():
    assert LanguageEnum.EN.is_english()
    assert not LanguageEnum.AM.is_english()
    assert not LanguageEnum.BOTH.is_english()


def test_string_comparison():
    assert LanguageEnum.EN == "en"
    assert LanguageEnum.AM == "am"
    assert LanguageEnum.BOTH == "both"
