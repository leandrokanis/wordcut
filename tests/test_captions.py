import pytest

from wordcut.transcript import Word
from wordcut.vertical.captions import (
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


def test_sentences_are_never_mixed_in_one_block() -> None:
    style = CaptionStyle(max_width=600)
    words = spoken("maior", "do", "que", "Ester.", "Ester", "era", "uma", "das", "condenadas")

    captions = build_captions(words, measure, style)

    assert [" ".join(c.lines) for c in captions] == [
        "maior do que Ester.",
        "Ester era uma das condenadas",
    ]


def test_long_sentence_split_avoids_weak_word_before_cut() -> None:
    style = CaptionStyle(max_width=600)  # 20 characters per line: 63 chars need 2 blocks
    words = spoken(
        "E", "quando", "vocês", "não", "enxergarem", "Deus", "agindo,", "lembrem-se", "de", "Ester."
    )

    captions = build_captions(words, measure, style)

    for caption in captions[:-1]:
        assert caption.lines[-1].split()[-1] not in {"de", "E"}
    assert len(captions) == 2


def test_two_lines_are_balanced() -> None:
    style = CaptionStyle(max_width=450)
    (caption,) = build_captions(
        spoken("Jesus", "não", "tinha", "pecado", "nenhum."), measure, style
    )

    widths = [measure(line) for line in caption.lines]
    assert len(widths) == 2 and abs(widths[0] - widths[1]) <= 6 * 30


def test_prefers_breaking_at_comma() -> None:
    style = CaptionStyle(max_width=900)  # 30 chars per line: one 2-line block
    words = spoken("Deus", "estava", "ali", "o", "tempo", "todo,", "preparando", "o", "livramento.")

    (caption,) = build_captions(words, measure, style)

    assert caption.lines[0].endswith("todo,")
