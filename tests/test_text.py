import pytest

from cortes_pregacao.edit.edit_list import EditList, Segment
from cortes_pregacao.edit.text import apply_corrections, capitalize
from cortes_pregacao.transcript import Word


def words(*tokens: str) -> list[Word]:
    return [Word(token, float(i), i + 0.5) for i, token in enumerate(tokens)]


def texts(items: list[Word]) -> str:
    return " ".join(word.text for word in items)


def test_correction_keeps_punctuation_and_timing() -> None:
    fixed = apply_corrections(words("Em", "Esté,", "o", "decreto"), {"Esté": "Ester"})

    assert texts(fixed) == "Em Ester, o decreto"
    assert fixed[1].start == 1.0


def test_phrase_correction_and_capital_preserved() -> None:
    fixed = apply_corrections(words("A", "direita", "do", "Pai."), {"a direita": "à direita"})

    assert texts(fixed) == "À direita do Pai."


def test_correction_needs_same_word_count() -> None:
    with pytest.raises(ValueError, match="mesmo número"):
        EditList("x", (Segment(0, 1),), corrections={"Amã": "o Hamã"})


def test_capitalize_skips_leading_punctuation() -> None:
    assert capitalize(Word('"ela', 0, 1)).text == '"Ela'
