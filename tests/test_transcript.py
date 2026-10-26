from pathlib import Path

import pytest

from wordcut.transcript import RawWord, Transcript, Word, fill_missing_times


def make_transcript(*words: Word) -> Transcript:
    return Transcript(words=words, language="pt", model="test")


class TestWord:
    def test_rejects_end_before_start(self) -> None:
        with pytest.raises(ValueError):
            Word("graça", start=2.0, end=1.0)

    def test_shifted_moves_both_ends(self) -> None:
        assert Word("graça", 1.0, 1.5).shifted(-1.0) == Word("graça", 0.0, 0.5)


class TestTranscript:
    def test_between_keeps_words_inside_and_rebases(self) -> None:
        transcript = make_transcript(
            Word("antes", 0.0, 0.4),
            Word("dentro", 1.0, 1.4),
            Word("cruza", 1.8, 2.3),
        )

        sliced = transcript.between(1.0, 2.0)

        assert [w.text for w in sliced.words] == ["dentro"]
        assert sliced.words[0].start == 0.0
        assert sliced.words[0].end == pytest.approx(0.4)

    def test_json_round_trip(self, tmp_path: Path) -> None:
        transcript = make_transcript(Word("Cristo", 0.1, 0.6, score=0.9, estimated=True))
        path = tmp_path / "palavras.json"

        transcript.save(path)

        assert Transcript.load(path) == transcript

    def test_rejects_unknown_schema_version(self) -> None:
        with pytest.raises(ValueError, match="version"):
            Transcript.from_json({"version": 99, "words": [], "language": "pt", "model": "x"})


class TestFillMissingTimes:
    def test_keeps_timed_words(self) -> None:
        words = fill_missing_times([RawWord("fé", 0.0, 0.3, 0.8)], total_duration=1.0)

        assert words == [Word("fé", 0.0, 0.3, 0.8)]

    def test_spreads_untimed_run_over_gap(self) -> None:
        raw = [
            RawWord("capítulo", 0.0, 0.5),
            RawWord("18"),
            RawWord("21"),
            RawWord("verso", 1.5, 1.9),
        ]

        words = fill_missing_times(raw, total_duration=3.0)

        assert [(w.text, w.start, w.end, w.estimated) for w in words[1:3]] == [
            ("18", 0.5, 1.0, True),
            ("21", 1.0, 1.5, True),
        ]

    def test_untimed_at_edges_use_media_bounds(self) -> None:
        raw = [RawWord("é"), RawWord("amém", 1.0, 1.4), RawWord("hum")]

        words = fill_missing_times(raw, total_duration=2.0)

        assert (words[0].start, words[0].end) == (0.0, 1.0)
        assert (words[-1].start, words[-1].end) == (1.4, 2.0)
