import pytest

from wordcut.edit.edit_list import EditList, Segment
from wordcut.edit.timeline import Cleanup, plan_segments, plan_timeline
from wordcut.transcript import Word

FPS = 30.0


def edit(*segments: tuple[float, float]) -> EditList:
    return EditList("teste", tuple(Segment(a, b) for a, b in segments))


def test_original_pauses_keep_a_long_pause_inside_a_segment_in_one_clip() -> None:
    words = [Word("Deus", 1.0, 1.4), Word("governa", 3.0, 3.5)]

    timeline = plan_timeline(edit((0.0, 10.0)), words, FPS, cleanup=Cleanup(pauses="original"))

    out = timeline.output_words()
    assert (len(timeline.clips), out[1].start - out[0].end) == (
        1,
        pytest.approx(1.6, abs=1 / FPS),
    )


def test_short_pauses_keep_less_breath_inside_and_after_a_sentence() -> None:
    words = [Word("Deus", 1.0, 1.4), Word("governa.", 3.0, 3.5), Word("Cristo", 5.0, 5.5)]

    out = plan_timeline(
        edit((0.0, 10.0)), words, FPS, cleanup=Cleanup(pauses="short")
    ).output_words()

    assert (out[1].start - out[0].end, out[2].start - out[1].end) == (
        pytest.approx(0.08, abs=2 / FPS),
        pytest.approx(0.20, abs=2 / FPS),
    )


def test_the_timeline_keeps_fillers_and_stammers_when_the_cleanup_keeps_them() -> None:
    words = [
        Word("o,", 1.0, 1.1),
        Word("o", 1.2, 1.3),
        Word("Senhor", 1.35, 1.7),
        Word("hã", 1.75, 1.9),
        Word("reina", 1.95, 2.3),
    ]

    timeline = plan_timeline(
        edit((0.0, 10.0)), words, FPS, cleanup=Cleanup(fillers=False, stammers=False)
    )

    assert ([w.text for w in timeline.output_words()], timeline.removed) == (
        ["o,", "o", "Senhor", "hã", "reina"],
        (),
    )


def test_a_segment_given_by_its_words_may_be_one_word_that_starts_where_it_ends() -> None:
    words = [Word("Deus", 1.0, 1.4), Word("Amém", 2.0, 2.0), Word("reina", 3.0, 3.4)]

    timeline = plan_segments([[words[1]]], words, FPS)

    assert [(clip.words, clip.segment) for clip in timeline.clips] == [((words[1],), 0)]


def test_the_default_cleanup_plans_the_same_timeline_as_before_the_options() -> None:
    words = [
        Word("Irmãos,", 1.0, 1.4),
        Word("hã", 1.5, 1.7),
        Word("o,", 1.8, 1.9),
        Word("o", 2.0, 2.1),
        Word("Senhor", 2.15, 2.6),
        Word("reina.", 4.0, 4.5),
        Word("Amém.", 8.0, 8.5),
    ]
    reordered = edit((7.5, 9.0), (0.5, 5.0))

    with_defaults = plan_timeline(
        reordered, words, FPS, cleanup=Cleanup(fillers=True, stammers=True, pauses="natural")
    )

    assert with_defaults == plan_timeline(reordered, words, FPS)
