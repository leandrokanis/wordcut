import io
import json
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut.db import connect, cuts, sermons, transcripts
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.sermons import NewSermon
from wordcut.home import Home
from wordcut.processing.sentences import split_sentences
from wordcut.transcript import Word
from wordcut_cli import main

NOW = datetime(2026, 10, 27, 3, 0, tzinfo=timezone.utc)
SPOKEN = (
    Word("Irmãos,", 0.3, 0.8),
    Word("graça", 0.9, 1.2),
    Word("e", 1.25, 1.3),
    Word("paz.", 1.35, 1.9),
    Word("Deus", 2.5, 2.8),
    Word("governa.", 2.85, 3.4),
)


def cut_of_two_sentences() -> tuple[int, list[int]]:
    """A cut playing the two sentences of a processed ``SPOKEN`` sermon, over all of its
    words, its ID and the IDs of the sermon's words."""
    with closing(connect(Home.from_environment())) as connection, connection:
        sermon = sermons.insert(
            connection,
            NewSermon(
                youtube_id="Ab3_x-9QzLk",
                url="https://youtu.be/Ab3_x-9QzLk",
                title="Culto de domingo",
                service_date=date(2026, 10, 18),
                live_duration=7718.0,
                live_finished=True,
                created_at=NOW,
            ),
        )
        transcripts.replace(connection, sermon.id, SPOKEN, split_sentences(SPOKEN))
        word = [row.id for row in transcripts.words_of(connection, sermon.id)]
        new = NewCut(
            "suggested", "Graça", (Segment(word[0], word[5]),), word[0], word[5], "llm", None
        )
        [cut_id] = cuts.insert_many(connection, sermon.id, [new], NOW)
        return cut_id, word


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main(argv)
    return exit_code, json.loads(capsys.readouterr().out)


def spans(*pairs: tuple[int, int]) -> list[dict[str, int]]:
    return [{"from_word": first, "to_word": last} for first, last in pairs]


def test_segments_from_a_file_are_stored_and_printed_as_cut_show_prints_the_cut(
    wordcut_home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cut_id, word = cut_of_two_sentences()
    file = tmp_path / "segments.json"
    file.write_text(json.dumps(spans((word[4], word[5]), (word[0], word[3]))), encoding="utf-8")

    answer = run_json(["cut", "segments", str(cut_id), "--file", str(file), "--json"], capsys)

    shown = run_json(["cut", "show", str(cut_id), "--json"], capsys)
    assert (answer, shown[1]["text"]) == (shown, "Deus governa. Irmãos, graça e paz.")


def test_segments_from_the_standard_input_are_stored(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    cut_id, word = cut_of_two_sentences()
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(spans((word[4], word[5])))))

    main(["cut", "segments", str(cut_id), "--file", "-"])
    capsys.readouterr()

    assert run_json(["cut", "show", str(cut_id), "--json"], capsys)[1]["text"] == "Deus governa."


SECRET = "conteudo-secreto-digitado"
UNREADABLE = {
    "not json": SECRET,
    "not a list": json.dumps({"segments": SECRET}),
}


@pytest.mark.parametrize("case", list(UNREADABLE))
def test_a_file_that_is_not_a_json_list_exits_2_on_the_file_without_echoing_it(
    case: str,
    wordcut_home: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cut_id, _ = cut_of_two_sentences()
    monkeypatch.setattr("sys.stdin", io.StringIO(UNREADABLE[case]))

    exit_code, answer = run_json(["cut", "segments", str(cut_id), "--file", "-", "--json"], capsys)

    error = answer["error"]
    assert (exit_code, error["code"], error["details"], SECRET in json.dumps(answer)) == (
        2,
        "invalid_argument",
        {"argument": "file"},
        False,
    )


def test_a_file_that_does_not_exist_exits_2_on_the_file_without_its_path(
    wordcut_home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cut_id, _ = cut_of_two_sentences()
    missing = tmp_path / "segredo" / "trechos.json"

    exit_code, answer = run_json(
        ["cut", "segments", str(cut_id), "--file", str(missing), "--json"], capsys
    )

    assert (exit_code, answer["error"]["details"], "segredo" in json.dumps(answer)) == (
        2,
        {"argument": "file"},
        False,
    )


def test_overlapping_segments_exit_2_on_the_file_and_store_nothing(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    cut_id, word = cut_of_two_sentences()
    _, before = run_json(["cut", "show", str(cut_id), "--json"], capsys)
    overlapping = spans((word[0], word[3]), (word[2], word[5]))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(overlapping)))

    exit_code, answer = run_json(["cut", "segments", str(cut_id), "--file", "-", "--json"], capsys)

    assert (
        exit_code,
        answer["error"]["code"],
        answer["error"]["details"],
        run_json(["cut", "show", str(cut_id), "--json"], capsys)[1],
    ) == (2, "invalid_argument", {"argument": "file"}, before)


def test_segments_of_a_cut_that_does_not_exist_exit_3(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(spans((1, 2)))))

    exit_code, answer = run_json(["cut", "segments", "999", "--file", "-", "--json"], capsys)

    assert (exit_code, answer["error"]["code"], answer["error"]["details"]) == (
        3,
        "not_found",
        {"cut_id": 999},
    )


def test_segments_without_json_print_the_cut_as_cut_show_does(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    cut_id, word = cut_of_two_sentences()
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(spans((word[4], word[5])))))

    main(["cut", "segments", str(cut_id), "--file", "-"])
    printed = capsys.readouterr().out
    main(["cut", "show", str(cut_id)])

    assert printed == capsys.readouterr().out
