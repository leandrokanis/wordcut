import pytest

from cortes_pregacao.edit.edit_list import EditList, Segment
from cortes_pregacao.edit.timeline import PAUSE_S, RHETORICAL_PAUSE_S, plan_timeline
from cortes_pregacao.transcript import Word

FPS = 30.0


def edit(*segments: tuple[float, float]) -> EditList:
    return EditList("teste", tuple(Segment(a, b) for a, b in segments))


def on_frame(t: float) -> bool:
    return abs(t * FPS - round(t * FPS)) < 1e-6


def test_long_pause_inside_sentence_is_cut_to_short_pause() -> None:
    words = [Word("Deus", 1.0, 1.4), Word("governa", 3.0, 3.5)]

    timeline = plan_timeline(edit((0.0, 10.0)), words, FPS)

    assert len(timeline.clips) == 2
    out = timeline.output_words()
    assert out[1].start - out[0].end == pytest.approx(PAUSE_S, abs=2 / FPS)


def test_pause_after_sentence_keeps_rhetorical_breath() -> None:
    words = [Word("vida.", 1.0, 1.4), Word("Cristo", 3.0, 3.5)]

    out = plan_timeline(edit((0.0, 10.0)), words, FPS).output_words()

    assert out[1].start - out[0].end == pytest.approx(RHETORICAL_PAUSE_S, abs=2 / FPS)


def test_short_natural_pause_is_untouched() -> None:
    words = [Word("graça", 1.0, 1.4), Word("e", 1.5, 1.6), Word("paz", 1.65, 2.0)]

    timeline = plan_timeline(edit((0.0, 10.0)), words, FPS)

    assert len(timeline.clips) == 1


def test_hesitation_is_cut_even_without_pause() -> None:
    words = [Word("Deus", 1.0, 1.4), Word("hã", 1.45, 1.6), Word("governa", 1.65, 2.0)]

    timeline = plan_timeline(edit((0.0, 10.0)), words, FPS)

    assert [w.text for w in timeline.removed] == ["hã"]
    assert len(timeline.clips) == 2
    assert timeline.clips[0].end <= 1.45 and timeline.clips[1].start >= 1.6


def test_cuts_land_on_frames_and_never_inside_words() -> None:
    words = [Word("a", 1.013, 1.4), Word("b", 2.91, 3.333), Word("c", 6.2, 6.71)]

    for clip in plan_timeline(edit((0.0, 10.0)), words, FPS).clips:
        assert on_frame(clip.start) and on_frame(clip.end)
        assert clip.start <= clip.words[0].start and clip.end >= clip.words[-1].end


def test_prefers_quietest_frame() -> None:
    words = [Word("a", 1.0, 1.4), Word("b", 5.0, 5.4)]
    quiet = 1.5

    clip = plan_timeline(edit((0.0, 10.0)), words, FPS, energy=lambda t: abs(t - quiet)).clips[0]

    assert clip.end == pytest.approx(quiet)


def test_segments_can_be_reordered_and_are_marked() -> None:
    words = [Word("antes.", 1.0, 1.5), Word("depois.", 8.0, 8.5)]
    edit_list = edit((7.5, 9.0), (0.5, 2.0))

    timeline = plan_timeline(edit_list, words, FPS)

    assert [w.text for w in timeline.output_words()] == ["depois.", "antes."]
    assert edit_list.reordered() == [0]
    assert timeline.segment_starts() == [pytest.approx(timeline.clips[0].duration)]


def test_hook_from_conclusion_is_the_reordered_segment() -> None:
    edit_list = edit((40.0, 44.0), (14.0, 39.0), (45.0, 90.0))

    assert edit_list.reordered() == [0]


def test_chronological_edit_list_has_no_reorder() -> None:
    assert edit((1.0, 2.0), (5.0, 6.0)).reordered() == []
