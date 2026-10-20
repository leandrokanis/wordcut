import pytest

from cortes_pregacao.transcript import Word
from cortes_pregacao.vertical.captions import (
    LINGER_S,
    CaptionRenderer,
    CaptionStyle,
    build_captions,
)

STYLE = CaptionStyle(max_width=300)


def measure(text: str) -> float:
    return 30.0 * len(text)  # 10 characters per line


def spoken(*tokens: str, gap: float = 0.05) -> list[Word]:
    words, t = [], 0.0
    for token in tokens:
        words.append(Word(token, t, t + 0.3))
        t += 0.3 + gap
    return words


def test_blocks_have_at_most_two_lines_that_fit() -> None:
    captions = build_captions(
        spoken("um", "dois", "tres", "quatro", "cinco", "seis", "sete"), measure, STYLE
    )

    for caption in captions:
        assert len(caption.lines) <= 2
        assert all(measure(line) <= 300 for line in caption.lines)


def test_sentence_end_closes_block() -> None:
    captions = build_captions(spoken("Ele", "é", "bom.", "Sempre"), measure, STYLE)

    assert [c.lines for c in captions] == [("Ele é bom.",), ("Sempre",)]


def test_pause_closes_block_and_caption_lingers_briefly() -> None:
    words = [Word("Amém", 0.0, 0.4), Word("Igreja", 2.0, 2.4)]

    first, second = build_captions(words, measure, STYLE)

    assert first.end == pytest.approx(0.4 + LINGER_S)
    assert second.start == 2.0


def test_consecutive_blocks_hand_over_without_gap() -> None:
    first, second = build_captions(spoken("Ele", "é", "bom.", "Sempre"), measure, STYLE)

    assert first.end == second.start


def test_renderer_centres_caption_on_frame() -> None:
    renderer = CaptionRenderer(1080)
    (caption,) = build_captions(spoken("Graça", "e", "paz."), renderer.measure)

    image = renderer.render(caption)

    assert image.bgr.shape[:2] == image.alpha.shape[:2]
    assert image.alpha.max() == 1.0
    middle = image.top + image.bgr.shape[0] / 2
    assert abs(middle - 960) <= 1
