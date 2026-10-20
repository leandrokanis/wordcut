from cortes_pregacao.overview import overview_lines
from cortes_pregacao.transcript import Transcript, Word


def transcript(*words: tuple[str, float, float]) -> Transcript:
    return Transcript(words=tuple(Word(*w) for w in words), language="pt", model="test")


def test_breaks_on_sentence_end_and_long_pause() -> None:
    t = transcript(
        ("Deus", 0.0, 0.3),
        ("governa.", 0.4, 0.9),
        ("Mesmo", 1.0, 1.3),
        ("calado", 1.4, 1.8),
        ("Amém", 5.0, 5.3),
    )

    assert list(overview_lines(t)) == [
        "[00:00:00.000] Deus governa.",
        "[00:00:01.000] Mesmo calado",
        "[00:00:05.000] Amém",
    ]


def test_restricts_to_range() -> None:
    t = transcript(("antes.", 0.0, 0.5), ("dentro.", 10.0, 10.5), ("depois.", 20.0, 20.5))

    assert list(overview_lines(t, start=5.0, end=15.0)) == ["[00:00:10.000] dentro."]
