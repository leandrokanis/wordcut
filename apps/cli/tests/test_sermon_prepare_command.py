"""``wordcut sermon prepare``: the thumbnails and waveform of the timeline (1.1.b.1)."""

from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from wordcut import timeline_media
from wordcut.timeline_media.storyboard import Storyboard
from wordcut.youtube import LiveInfo, YouTubeError
from wordcut_cli import deps, main

LINK = "https://youtu.be/Ab3_x-9QzLk"
FINISHED_LIVE = LiveInfo("Culto de domingo", date(2026, 10, 18), 7200.0, "was_live")

Launched = list["subprocess.Popen[bytes]"]


class FakeLive:
    def info(self, url: str) -> LiveInfo:
        return FINISHED_LIVE


class FakeTimelineGateways:
    def __init__(self, *, audio_fails: bool = False) -> None:
        self._audio_fails = audio_fails

    def storyboard(self, url: str, out_dir: Path) -> Storyboard | None:
        out_dir.mkdir(parents=True, exist_ok=True)
        image = out_dir / "strip.jpg"
        image.write_bytes(b"jpeg")
        return Storyboard(image=image, width=160, height=90, times=[0.0])

    def audio(self, url: str, output: Path) -> Path:
        if self._audio_fails:
            raise YouTubeError("yt-dlp --cookies /segredos/youtube-cookies.txt: HTTP 403")
        output.write_bytes(b"audio")
        return output

    def peaks(self, audio: Path, buckets: int) -> list[float]:
        return [0.0, 1.0]


@pytest.fixture
def live(monkeypatch: pytest.MonkeyPatch, wordcut_home: Path) -> None:
    monkeypatch.setattr(deps, "live_source", FakeLive)


def use_gateways(monkeypatch: pytest.MonkeyPatch, gateways: FakeTimelineGateways) -> None:
    monkeypatch.setattr(timeline_media, "default_gateways", lambda: gateways)


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main(argv)
    return exit_code, json.loads(capsys.readouterr().out)


def created(capsys: pytest.CaptureFixture[str], harmless_tasks: Launched) -> str:
    """A sermon whose preparation, launched by its creation, is no longer running."""
    exit_code, sermon = run_json(["sermon", "create", LINK, "--json"], capsys)
    assert exit_code == 0
    for process in harmless_tasks:
        process.kill()
        process.wait()
    return str(sermon["id"])


def test_prepare_with_wait_prints_the_ready_timeline_and_the_stages_on_stderr(
    live: None,
    harmless_tasks: Launched,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sermon_id = created(capsys, harmless_tasks)
    use_gateways(monkeypatch, FakeTimelineGateways())

    exit_code = main(["sermon", "prepare", sermon_id, "--wait", "--json"])

    out, err = capsys.readouterr()
    assert (exit_code, json.loads(out), err.splitlines()) == (
        0,
        {
            "sermon_id": int(sermon_id),
            "timeline": {"status": "ready", "error": None, "task_id": None},
        },
        ["[prepare] miniaturas 0%", "[prepare] áudio 30%", "[prepare] forma de onda 80%"],
    )


def test_prepare_without_wait_answers_the_running_task(
    live: None, harmless_tasks: Launched, capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_id = created(capsys, harmless_tasks)

    exit_code, task = run_json(["sermon", "prepare", sermon_id, "--json"], capsys)

    assert (exit_code, task) == (
        0,
        {
            "task_id": task["task_id"],
            "kind": "prepare",
            "status": "running",
            "sermon_id": int(sermon_id),
        },
    )


def test_prepare_while_the_creation_still_prepares_exits_4_busy_naming_that_task(
    live: None, harmless_tasks: Launched, capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_id = run_json(["sermon", "create", LINK, "--json"], capsys)[1]["id"]
    running = run_json(["sermon", "show", str(sermon_id), "--json"], capsys)[1]["timeline"]

    exit_code, refused = run_json(["sermon", "prepare", str(sermon_id), "--json"], capsys)

    assert (exit_code, refused["error"]["code"], refused["error"]["details"]["task_id"]) == (
        4,
        "busy",
        running["task_id"],
    )


def test_prepare_of_an_unknown_sermon_exits_3_not_found(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, refused = run_json(["sermon", "prepare", "99", "--json"], capsys)

    assert (exit_code, refused["error"]["code"]) == (3, "not_found")


def test_a_failed_preparation_exits_6_with_a_message_that_leaks_nothing(
    live: None,
    harmless_tasks: Launched,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sermon_id = created(capsys, harmless_tasks)
    use_gateways(monkeypatch, FakeTimelineGateways(audio_fails=True))

    exit_code, refused = run_json(["sermon", "prepare", sermon_id, "--wait", "--json"], capsys)

    assert (exit_code, refused["error"]["code"]) == (6, "youtube_error")
    assert "cookies" not in json.dumps(refused)


def test_show_tells_the_state_of_the_timeline_readably_and_in_json(
    live: None,
    harmless_tasks: Launched,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sermon_id = created(capsys, harmless_tasks)
    use_gateways(monkeypatch, FakeTimelineGateways())
    main(["sermon", "prepare", sermon_id, "--wait", "--quiet"])
    capsys.readouterr()

    main(["sermon", "show", sermon_id])
    readable = capsys.readouterr().out
    shown = run_json(["sermon", "show", sermon_id, "--json"], capsys)[1]

    assert ("Timeline: pronta" in readable.splitlines(), shown["timeline"]["status"]) == (
        True,
        "ready",
    )
