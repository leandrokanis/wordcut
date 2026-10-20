from cortes_pregacao.edit.cleanup import remove_hesitations
from cortes_pregacao.transcript import Word


def words(*tokens: str, gap: float = 0.1) -> list[Word]:
    out, t = [], 0.0
    for token in tokens:
        out.append(Word(token, t, t + 0.3))
        t += 0.3 + gap
    return out


def kept_text(tokens: list[Word]) -> str:
    return " ".join(w.text for w in remove_hesitations(tokens).kept)


def test_drops_pure_fillers() -> None:
    assert kept_text(words("Deus,", "hã,", "governa,", "né?")) == "Deus, governa?"


def test_e_is_filler_only_when_trailing_off() -> None:
    assert kept_text(words("Ele", "é", "bom.")) == "Ele é bom."
    assert kept_text(words("é...", "Ele", "é", "bom.")) == "Ele é bom."


def test_stammer_on_short_word_is_removed() -> None:
    assert kept_text(words("o,", "o", "Senhor")) == "o Senhor"


def test_rhetorical_repetition_survives() -> None:
    assert kept_text(words("Santo,", "santo,", "santo")) == "Santo, santo, santo"


def test_distant_repetition_is_not_a_stammer() -> None:
    assert kept_text(words("a", "a", gap=2.0)) == "a a"


def test_reports_removed_words() -> None:
    result = remove_hesitations(words("hum", "graça"))

    assert [w.text for w in result.removed] == ["hum"]


def test_sentence_end_moves_to_previous_word() -> None:
    assert kept_text(words("só", "insônia,", "né.", "E", "entre")) == "só insônia. E entre"


def test_phrase_restart_is_removed() -> None:
    tokens = words("Não", "teve", "anjo,", "não", "teve,", "não", "teve", "sonho")

    assert kept_text(tokens) == "Não teve anjo, não teve sonho"


def test_phrase_repeated_without_trailing_off_survives() -> None:
    assert kept_text(words("Deus", "é", "bom", "Deus", "é", "bom")) == "Deus é bom Deus é bom"
