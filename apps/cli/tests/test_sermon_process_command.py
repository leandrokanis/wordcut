import json
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from wordcut import processing
from wordcut.home import Home
from wordcut.lock import ProcessingLock
from wordcut.processing import OnProgress
from wordcut.transcript import Transcript, Word
from wordcut.youtube import LiveInfo, YouTubeError
from wordcut_cli import deps, main

LINK = "https://youtu.be/Ab3_x-9QzLk"
FINISHED_LIVE = LiveInfo(
    title="Culto de domingo",
    service_date=date(2026, 10, 18),
    duration=7200.0,
    live_status="was_live",
)
# The section is synced to start at 970 s of the live, where it was requested.
SECTION_START = 970.0
LIVE_WORDS = (
    Word("Irmãos", 1000.0, 1000.4, score=0.91),
    Word("graça.", 1000.5, 1001.0, score=0.88),
    Word("Amém.", 1098.5, 1100.0, score=0.97),
)


class FakeLive:
    def __init__(self, info: LiveInfo = FINISHED_LIVE) -> None:
        self.answer = info

    def info(self, url: str) -> LiveInfo:
        return self.answer


class FakeGateways:
    """``ProcessingGateways`` double: the section holds ``LIVE_WORDS``."""

    def download_section(
        self, url: str, start: float, end: float, output: Path, *, on_progress: OnProgress
    ) -> Path:
        return output

    def download_audio_window(
        self, url: str, start: float, end: float, output: Path, *, on_progress: OnProgress
    ) -> Path:
        return output

    def locate(self, recording: Path, clip: Path, expected_start: float, search: float) -> float:
        return expected_start

    def transcribe(self, media: Path, workdir: Path, *, on_progress: OnProgress) -> Transcript:
        words = tuple(word.shifted(-SECTION_START) for word in LIVE_WORDS)
        return Transcript(words=words, language="pt", model="fake")

    def duration(self, media: Path) -> float:
        return 200.0

    def cut(self, source: Path, start: float, end: float, output: Path) -> Path:
        output.write_bytes(b"sermon")
        return output


@pytest.fixture
def live(monkeypatch: pytest.MonkeyPatch, wordcut_home: Path) -> FakeLive:
    fake = FakeLive()
    monkeypatch.setattr(deps, "live_source", lambda: fake)
    return fake


@pytest.fixture
def gateways(monkeypatch: pytest.MonkeyPatch) -> Callable[[type[FakeGateways]], None]:
    """Process with the given ``FakeGateways`` class; the plain one by default."""

    def use(fake: type[FakeGateways]) -> None:
        monkeypatch.setattr(processing, "default_gateways", lambda whisper_model: fake())

    use(FakeGateways)
    return use


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main(argv)
    return exit_code, json.loads(capsys.readouterr().out)


def trimmed(capsys: pytest.CaptureFixture[str]) -> str:
    exit_code, sermon = run_json(
        ["sermon", "create", LINK, "--start", "16:40", "--end", "18:20", "--json"], capsys
    )
    assert exit_code == 0
    return str(sermon["id"])


def test_process_with_wait_prints_the_processed_sermon_and_the_stages_on_stderr(
    live: FakeLive, gateways: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_id = trimmed(capsys)

    exit_code = main(["sermon", "process", sermon_id, "--wait", "--json"])

    out, err = capsys.readouterr()
    sermon = json.loads(out)
    assert (
        exit_code,
        (sermon["id"], sermon["status"], sermon["sermon_start"], sermon["sermon_end"]),
        sermon["last_task"]["status"],
        err.splitlines(),
    ) == (
        0,
        (int(sermon_id), "processed", 999.7, 1101.5),
        "succeeded",
        [
            "[process] baixando 0%",
            "[process] sincronizando 30%",
            "[process] transcrevendo 35%",
            "[process] cortando 85%",
            "[process] gravando 95%",
            "[process] sugerindo 96%",
        ],
    )


def test_quiet_process_with_wait_prints_no_progress(
    live: FakeLive, gateways: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_id = trimmed(capsys)

    exit_code = main(["sermon", "process", sermon_id, "--wait", "--json", "--quiet"])

    assert (exit_code, capsys.readouterr().err) == (0, "")


def test_process_without_wait_answers_the_running_task_and_the_sermon_is_processing(
    live: FakeLive, harmless_tasks: list[Any], capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_id = trimmed(capsys)

    exit_code, task = run_json(["sermon", "process", sermon_id, "--json"], capsys)

    shown = run_json(["sermon", "show", sermon_id, "--json"], capsys)[1]
    assert (exit_code, task, shown["status"]) == (
        0,
        {
            "task_id": task["task_id"],
            "kind": "process",
            "status": "running",
            "sermon_id": int(sermon_id),
        },
        "processing",
    )


def test_force_processes_a_processed_sermon_again(
    live: FakeLive, gateways: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_id = trimmed(capsys)
    _, first = run_json(["sermon", "process", sermon_id, "--wait", "--json"], capsys)

    exit_code, sermon = run_json(
        ["sermon", "process", sermon_id, "--force", "--wait", "--json"], capsys
    )

    assert (exit_code, sermon["status"], sermon["last_task"]["id"]) == (
        0,
        "processed",
        first["last_task"]["id"] + 1,
    )


class RefusingYouTube(FakeGateways):
    def download_section(
        self, url: str, start: float, end: float, output: Path, *, on_progress: OnProgress
    ) -> Path:
        raise YouTubeError("O YouTube recusou o pedido.")


class MissingWhisperX(FakeGateways):
    def transcribe(self, media: Path, workdir: Path, *, on_progress: OnProgress) -> Transcript:
        raise FileNotFoundError("ambiente do WhisperX não encontrado")


@pytest.mark.parametrize(
    ("failing", "code"),
    [(RefusingYouTube, "youtube_error"), (MissingWhisperX, "transcription_error")],
)
def test_an_outside_failure_exits_6_with_its_code_and_the_sermon_failed(
    failing: type[FakeGateways],
    code: str,
    live: FakeLive,
    gateways: Callable[[type[FakeGateways]], None],
    capsys: pytest.CaptureFixture[str],
) -> None:
    sermon_id = trimmed(capsys)
    gateways(failing)

    exit_code, answer = run_json(["sermon", "process", sermon_id, "--wait", "--json"], capsys)

    shown = run_json(["sermon", "show", sermon_id, "--json"], capsys)[1]
    assert (exit_code, answer["error"]["code"], shown["status"]) == (6, code, "failed")


LIVE_ON_AIR = LiveInfo.from_metadata(
    {"title": "Culto ao vivo", "timestamp": 1792361083, "live_status": "is_live"}
)


def untrimmed(capsys: pytest.CaptureFixture[str], live: FakeLive) -> str:
    return str(run_json(["sermon", "create", LINK, "--json"], capsys)[1]["id"])


def on_air(capsys: pytest.CaptureFixture[str], live: FakeLive) -> str:
    live.answer = LIVE_ON_AIR
    return trimmed(capsys)


def processed(capsys: pytest.CaptureFixture[str], live: FakeLive) -> str:
    sermon_id = trimmed(capsys)
    main(["sermon", "process", sermon_id, "--wait", "--quiet"])
    capsys.readouterr()
    return sermon_id


@pytest.mark.parametrize(
    ("prepare", "exit_code", "code"),
    [
        (lambda capsys, live: "999", 3, "not_found"),
        (untrimmed, 5, "sermon_not_trimmed"),
        (on_air, 5, "live_not_finished"),
        (processed, 5, "would_discard_edits"),
    ],
)
def test_a_sermon_that_cannot_be_processed_exits_with_the_contract_code_and_no_task(
    prepare: Callable[[pytest.CaptureFixture[str], FakeLive], str],
    exit_code: int,
    code: str,
    live: FakeLive,
    gateways: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sermon_id = prepare(capsys, live)
    tasks_before = run_json(["task", "list", "--json"], capsys)[1]["items"]

    refused = run_json(["sermon", "process", sermon_id, "--json"], capsys)

    tasks_after = run_json(["task", "list", "--json"], capsys)[1]["items"]
    assert (refused[0], refused[1]["error"]["code"], tasks_after) == (exit_code, code, tasks_before)


def test_process_while_the_machine_is_busy_exits_4(
    live: FakeLive, gateways: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_id = trimmed(capsys)

    with ProcessingLock(Home.from_environment()).acquire("render", "cut 34"):
        exit_code, answer = run_json(["sermon", "process", sermon_id, "--json"], capsys)

    assert (exit_code, answer["error"]["code"]) == (4, "busy")


def test_create_with_borders_and_process_with_wait_does_everything_in_one_command(
    live: FakeLive, gateways: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, sermon = run_json(
        ["sermon", "create", LINK, "--start", "16:40", "--end", "18:20", "--process", "--wait",
         "--json"],
        capsys,
    )  # fmt: skip

    assert (exit_code, sermon["status"], sermon["live_start"], sermon["sermon_start"]) == (
        0,
        "processed",
        1000.0,
        999.7,
    )


@pytest.mark.parametrize(
    ("options", "argument"),
    [(["--process"], "--start"), (["--process", "--wait"], "--start"), (["--wait"], "--process")],
)
def test_create_refuses_process_without_borders_and_wait_without_process_creating_nothing(
    options: list[str],
    argument: str,
    live: FakeLive,
    gateways: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code, answer = run_json(["sermon", "create", LINK, *options, "--json"], capsys)

    assert (
        exit_code,
        answer["error"]["code"],
        answer["error"]["details"]["argument"],
        run_json(["sermon", "list", "--json"], capsys)[1],
    ) == (2, "invalid_argument", argument, {"items": []})


CREATE_AND_PROCESS = ["sermon", "create", LINK, "--start", "16:40", "--end", "18:20", "--process"]


def test_create_and_process_of_a_live_on_air_keeps_the_trimmed_sermon_and_exits_5(
    live: FakeLive, gateways: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    live.answer = LIVE_ON_AIR

    exit_code, answer = run_json([*CREATE_AND_PROCESS, "--json"], capsys)

    [kept] = run_json(["sermon", "list", "--json"], capsys)[1]["items"]
    assert (exit_code, answer["error"]["code"], kept["status"]) == (
        5,
        "live_not_finished",
        "trimmed",
    )


def test_create_and_process_of_a_processed_sermon_would_discard_edits(
    live: FakeLive, gateways: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    processed(capsys, live)

    exit_code, answer = run_json([*CREATE_AND_PROCESS, "--json"], capsys)

    assert (exit_code, answer["error"]["code"]) == (5, "would_discard_edits")


def test_create_and_process_without_wait_answers_the_running_task(
    live: FakeLive, harmless_tasks: list[Any], capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, task = run_json([*CREATE_AND_PROCESS, "--json"], capsys)

    assert (exit_code, task["kind"], task["status"], task["sermon_id"]) == (
        0,
        "process",
        "running",
        1,
    )


def test_show_with_transcript_in_json_adds_the_sentences_in_sermon_time(
    live: FakeLive, gateways: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_id = processed(capsys, live)

    exit_code, sermon = run_json(["sermon", "show", sermon_id, "--transcript", "--json"], capsys)

    assert (exit_code, [(item["start"], item["text"]) for item in sermon["sentences"]]) == (
        0,
        [(0.3, "Irmãos graça."), (98.8, "Amém.")],
    )


def test_show_with_transcript_in_text_prints_one_sentence_per_line(
    live: FakeLive, gateways: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_id = processed(capsys, live)
    sentences = run_json(["sermon", "show", sermon_id, "--transcript", "--json"], capsys)[1][
        "sentences"
    ]

    exit_code = main(["sermon", "show", sermon_id, "--transcript"])

    first, second = sentences
    assert (exit_code, capsys.readouterr().out.splitlines()[-3:]) == (
        0,
        [
            "Transcrição:",
            f"{first['id']}  00:00:00.300  Irmãos graça.  (palavras {first['first_word_id']}"
            f"–{first['last_word_id']})",
            f"{second['id']}  00:01:38.800  Amém.  (palavras {second['first_word_id']}"
            f"–{second['last_word_id']})",
        ],
    )


@pytest.mark.parametrize(
    ("argv", "described"),
    [
        (["sermon", "process", "--help"], ["processa a pregação delimitada", "--force", "--wait"]),
        (["sermon", "create", "--help"], ["--process", "exige --start e --end"]),
        (["sermon", "show", "--help"], ["--transcript", "uma frase por linha"]),
    ],
)
def test_help_of_the_new_options_is_in_portuguese(
    argv: list[str], described: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(argv)

    # argparse wraps the help text at the terminal width.
    out = " ".join(capsys.readouterr().out.split())
    assert (exit_code, [text for text in described if text not in out]) == (0, [])
