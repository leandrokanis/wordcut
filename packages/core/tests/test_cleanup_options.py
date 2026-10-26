from wordcut.edit.cleanup import remove_hesitations
from wordcut.transcript import Word

# A filler ("hã", "né"), a word stammer ("o, o") and a phrase restart ("não teve, não teve").
SPOKEN = ("hã,", "o,", "o", "Senhor", "não", "teve,", "não", "teve", "sonho,", "né?")


def words(*tokens: str, gap: float = 0.1) -> list[Word]:
    out, t = [], 0.0
    for token in tokens:
        out.append(Word(token, t, t + 0.3))
        t += 0.3 + gap
    return out


def kept_text(*, fillers: bool, stammers: bool) -> str:
    kept = remove_hesitations(words(*SPOKEN), fillers=fillers, stammers=stammers).kept
    return " ".join(word.text for word in kept)


def test_keeping_fillers_keeps_them_and_still_removes_the_stammers() -> None:
    assert kept_text(fillers=False, stammers=True) == "hã, o Senhor não teve sonho, né?"


def test_keeping_stammers_keeps_word_and_phrase_stammers_and_still_removes_the_fillers() -> None:
    assert kept_text(fillers=True, stammers=False) == "o, o Senhor não teve, não teve sonho?"


def test_keeping_both_removes_nothing() -> None:
    assert kept_text(fillers=False, stammers=False) == " ".join(SPOKEN)
