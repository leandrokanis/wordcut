import json
import subprocess
from collections.abc import Callable, Sequence
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut import rendering
from wordcut.db import connect, cuts, sermons, transcripts
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.sermons import NewSermon
from wordcut.edit.timeline import Clip
from wordcut.home import Home
from wordcut.transcript import Word
from wordcut.vertical.camera import CameraPath
from wordcut.vertical.captions import CaptionImage
from wordcut.vertical.detection import FrameDetections
from wordcut.vertical.render import Encoding
from wordcut_cli import main

StartLockOwner = Callable[[str, str], subprocess.Popen[str]]

NOW = datetime(2026, 10, 26, 22, 40, tzinfo=timezone.utc)
VIDEO_PATH = "media/sermons/1/sermon.mp4"
SPOKEN = (
    Word("Irmãos,", 0.3, 0.8),
    Word("graça", 0.9, 1.2),
    Word("e", 1.25, 1.3),
    Word("paz.", 1.35, 1.9),
)


class FakeGateways:
    """``RenderGateways`` double: the render writes a small file; nothing else is real."""

    def geometry(self, media: Path) -> tuple[int, int, float]:
        return 320, 180, 30.0

    def energy(self, media: Path) -> Callable[[float], float]:
        return lambda t: 0.0

    def assemble(
        self, source: Path, clips: Sequence[Clip], output: Path, fps: float, *, smooth_joins: bool
    ) -> Path:
        output.write_bytes(b"montage")
        return output

    def detect(self, montage: Path, progress: Callable[[int, int], None]) -> list[FrameDetections]:
        return [FrameDetections(False, ())] * 30

    def render(
        self,
        montage: Path,
        camera: CameraPath,
        captions: Sequence[CaptionImage],
        fps: float,
        output: Path,
        encoding: Encoding,
    ) -> Path:
        output.write_bytes(b"video")
        return output


@pytest.fixture
def cut_id(wordcut_home: Path, monkeypatch: pytest.MonkeyPatch) -> int:
    """A chosen cut of a processed sermon whose video is in the data folder."""
    monkeypatch.setattr(rendering, "default_gateways", FakeGateways)
    home = Home(wordcut_home)
    video = home.root / VIDEO_PATH
    video.parent.mkdir(parents=True, exist_ok=True)
    video.write_bytes(b"sermon")
    with closing(connect(home)) as connection, connection:
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
        transcripts.replace(connection, sermon.id, SPOKEN, ())
        sermons.record_processed(connection, sermon.id, 1000.0, 1100.0, VIDEO_PATH, NOW)
        word = [row.id for row in transcripts.words_of(connection, sermon.id)]
        new = NewCut("chosen", "Graça", (Segment(word[0], word[3]),), word[0], word[3], "llm", None)
        [created] = cuts.insert_many(connection, sermon.id, [new], NOW)
    return created


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main(argv)
    return exit_code, json.loads(capsys.readouterr().out)


def test_render_with_wait_prints_the_export_and_the_stages_on_stderr(
    cut_id: int, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["cut", "render", str(cut_id), "--wait", "--json"])

    out, err = capsys.readouterr()
    export = json.loads(out)
    assert (
        exit_code,
        sorted(export),
        export["cut_id"],
        Path(export["path"]).is_absolute() and Path(export["path"]).is_file(),
        {line.split()[0] for line in err.splitlines()},
    ) == (
        0,
        ["created_at", "cut_id", "duration", "id", "options", "path"],
        cut_id,
        True,
        {"[render]"},
    )


def test_options_given_once_are_saved_and_the_next_render_without_options_repeats_them(
    cut_id: int, capsys: pytest.CaptureFixture[str]
) -> None:
    run_json(
        ["cut", "render", str(cut_id), "--pauses", "short", "--no-fade",
         "--resolution", "720x1280", "--wait", "--json"],
        capsys,
    )  # fmt: skip

    exit_code, export = run_json(["cut", "render", str(cut_id), "--wait", "--json"], capsys)

    assert (exit_code, export["options"]) == (
        0,
        {"fillers": "remove", "stammers": "remove", "pauses": "short", "smooth_joins": True,
         "fade": False, "normalize": True, "caption": True, "resolution": "720x1280",
         "quality": "high"},
    )  # fmt: skip


def test_an_estimate_saves_nothing_creates_no_task_and_does_not_wait_for_the_lock(
    cut_id: int, lock_owner: StartLockOwner, capsys: pytest.CaptureFixture[str]
) -> None:
    lock_owner("process", "sermon 1")

    exit_code, estimate = run_json(
        ["cut", "render", str(cut_id), "--pauses", "short", "--no-caption", "--estimate",
         "--json"],
        capsys,
    )  # fmt: skip

    _, shown = run_json(["cut", "show", str(cut_id), "--json"], capsys)
    _, tasks = run_json(["task", "list", "--json"], capsys)
    assert (
        exit_code,
        sorted(estimate),
        (estimate["options"]["pauses"], estimate["options"]["caption"]),
        (shown["render_options"]["pauses"], shown["caption"]["enabled"]),
        tasks["items"],
    ) == (0, ["duration", "options"], ("short", False), ("natural", True), [])


def test_render_without_wait_answers_the_running_render_task(
    cut_id: int, harmless_tasks: list[Any], capsys: pytest.CaptureFixture[str]
) -> None:
    answer = run_json(["cut", "render", str(cut_id), "--json"], capsys)

    exit_code, task = answer
    assert (exit_code, task) == (
        0,
        {"task_id": task["task_id"], "kind": "render", "status": "running", "cut_id": cut_id},
    )


def test_task_show_of_a_finished_render_carries_the_render_id(
    cut_id: int, capsys: pytest.CaptureFixture[str]
) -> None:
    _, export = run_json(["cut", "render", str(cut_id), "--wait", "--json"], capsys)
    _, tasks = run_json(["task", "list", "--kind", "render", "--json"], capsys)

    _, task = run_json(["task", "show", str(tasks["items"][0]["id"]), "--json"], capsys)

    assert (task["cut_id"], task["result"]) == (cut_id, {"render_id": export["id"]})


def test_render_without_caption_leaves_the_cut_caption_off(
    cut_id: int, capsys: pytest.CaptureFixture[str]
) -> None:
    run_json(["cut", "render", str(cut_id), "--no-caption", "--wait", "--json"], capsys)

    exit_code, style = run_json(["cut", "caption", str(cut_id), "--json"], capsys)

    assert (exit_code, style["enabled"]) == (0, False)


@pytest.mark.parametrize(
    ("option", "value", "choices"),
    [
        ("--resolution", "640x480", ["1080x1920", "720x1280"]),
        ("--quality", "max", ["high", "small"]),
        ("--pauses", "long", ["original", "natural", "short"]),
        ("--fillers", "drop", ["remove", "keep"]),
    ],
)
def test_a_value_out_of_the_choices_is_refused_with_them_and_without_echo(
    cut_id: int, capsys: pytest.CaptureFixture[str], option: str, value: str, choices: list[str]
) -> None:
    exit_code, answer = run_json(["cut", "render", str(cut_id), option, value, "--json"], capsys)

    error = answer["error"]
    assert (exit_code, error["code"], error["details"], value in error["message"]) == (
        2,
        "invalid_argument",
        {"argument": option, "choices": choices},
        False,
    )


def test_a_switch_given_both_ways_is_refused(
    cut_id: int, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, answer = run_json(
        ["cut", "render", str(cut_id), "--fade", "--no-fade", "--json"], capsys
    )

    assert (exit_code, answer["error"]["code"]) == (2, "invalid_argument")


@pytest.mark.parametrize("estimate", [[], ["--estimate"]], ids=["render", "estimate"])
def test_a_cut_that_does_not_exist_exits_3(
    cut_id: int, capsys: pytest.CaptureFixture[str], estimate: list[str]
) -> None:
    exit_code, answer = run_json(["cut", "render", "999", *estimate, "--json"], capsys)

    assert (exit_code, answer["error"]["code"]) == (3, "not_found")


def test_with_the_machine_busy_render_exits_4_and_creates_no_task(
    cut_id: int, lock_owner: StartLockOwner, capsys: pytest.CaptureFixture[str]
) -> None:
    lock_owner("process", "sermon 1")

    exit_code, answer = run_json(["cut", "render", str(cut_id), "--wait", "--json"], capsys)

    _, tasks = run_json(["task", "list", "--json"], capsys)
    assert (exit_code, answer["error"]["code"], tasks["items"]) == (4, "busy", [])


def test_a_cut_of_a_sermon_not_processed_exits_5(
    cut_id: int, capsys: pytest.CaptureFixture[str]
) -> None:
    with closing(connect(Home.from_environment())) as connection, connection:
        sermons.set_status(connection, 1, "processing", NOW)

    exit_code, answer = run_json(["cut", "render", str(cut_id), "--wait", "--json"], capsys)

    assert (exit_code, answer["error"]["code"]) == (5, "sermon_not_processed")


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        (["--wait"], "Exportação 1 do corte"),
        (["--estimate"], "Duração estimada:"),
    ],
    ids=["export", "estimate"],
)
def test_without_json_the_answer_is_readable(
    cut_id: int, capsys: pytest.CaptureFixture[str], extra: list[str], expected: str
) -> None:
    exit_code = main(["cut", "render", str(cut_id), *extra])

    assert (exit_code, capsys.readouterr().out.startswith(expected)) == (0, True)


def test_without_json_or_wait_the_launched_task_is_readable(
    cut_id: int, harmless_tasks: list[Any], capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["cut", "render", str(cut_id)])

    assert (exit_code, capsys.readouterr().out.startswith("Tarefa ")) == (0, True)


def test_an_estimate_does_not_wait_for_anything_so_wait_with_it_is_refused(
    cut_id: int, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, answer = run_json(
        ["cut", "render", str(cut_id), "--estimate", "--wait", "--json"], capsys
    )

    assert (exit_code, answer["error"]["code"], answer["error"]["details"]) == (
        2,
        "invalid_argument",
        {"argument": "--wait"},
    )
