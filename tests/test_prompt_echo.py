from cortes_pregacao.asr.prompt_echo import remove_prompt_echoes
from cortes_pregacao.transcript import Word

PROMPT = "Hã, é... então, né, tipo assim, é, o, o Senhor, ãh, a gente, hum, aí, né."


def words(text: str) -> list[Word]:
    return [Word(token, float(i), i + 0.5) for i, token in enumerate(text.split())]


def texts(items: list[Word]) -> str:
    return " ".join(word.text for word in items)


def test_drops_run_copied_from_prompt() -> None:
    result = remove_prompt_echoes(words("Amém. ãh, a gente, hum, aí Deus é bom"), PROMPT)

    assert texts(result) == "Amém. Deus é bom"


def test_keeps_short_genuine_hesitations() -> None:
    sentence = "então, né, Esther entrou no palácio"

    assert texts(remove_prompt_echoes(words(sentence), PROMPT)) == sentence


def test_matching_ignores_case_and_punctuation() -> None:
    result = remove_prompt_echoes(words("Tipo assim É O graça"), PROMPT)

    assert texts(result) == "graça"
