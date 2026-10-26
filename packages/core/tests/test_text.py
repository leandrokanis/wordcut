from wordcut.edit.text import capitalize, tidy_joins
from wordcut.transcript import Word


def words(*tokens: str) -> list[Word]:
    return [Word(token, float(i), i + 0.5) for i, token in enumerate(tokens)]


def texts(items: list[Word]) -> str:
    return " ".join(word.text for word in items)


def test_capitalize_skips_leading_punctuation() -> None:
    assert capitalize(Word('"ela', 0, 1)).text == '"Ela'


def test_comma_before_next_segment_becomes_full_stop() -> None:
    tidy = tidy_joins(words("pernas", "tremendo,", "Ela", "tinha"), [True, False, True, False])

    assert texts(tidy) == "pernas tremendo. Ela tinha"


def test_hesitation_ellipsis_inside_sentence_is_dropped() -> None:
    tidy = tidy_joins(words("O", "modelo...", "Para", "o", "marido"), [True] + [False] * 4)

    assert texts(tidy) == "O modelo para o marido"


def test_capitalized_function_word_mid_sentence_is_lowered() -> None:
    tidy = tidy_joins(words("do", "que", "A", "sua", "Deus"), [True] + [False] * 4)

    assert texts(tidy) == "do que a sua Deus"


def test_sentence_start_keeps_capital() -> None:
    tidy = tidy_joins(words("vida.", "A", "dívida"), [True, False, False])

    assert texts(tidy) == "vida. A dívida"


def test_ellipsis_before_next_segment_becomes_full_stop() -> None:
    tidy = tidy_joins(words("então...", "Ela", "foi"), [True, True, False])

    assert texts(tidy) == "então. Ela foi"
