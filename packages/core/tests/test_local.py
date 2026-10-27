import subprocess
import sys
from pathlib import Path

import pytest

from wordcut.asr.local import LocalTranscriber


def test_command_runs_worker_module_with_env_python(tmp_path: Path) -> None:
    transcriber = LocalTranscriber(model="large-v3", worker_env=tmp_path / "venv")

    command = transcriber.command(Path("a.wav"), Path("out.json"))

    assert command[0] == str(tmp_path / "venv/bin/python")
    assert command[1:] == [
        "-u", "-m", "wordcut.asr.worker", "a.wav", "out.json", "--model", "large-v3",
    ]  # fmt: skip


def test_missing_worker_env_gives_actionable_error(tmp_path: Path) -> None:
    transcriber = LocalTranscriber(worker_env=tmp_path / "missing")

    with pytest.raises(FileNotFoundError, match="README"):
        transcriber.transcribe(Path("a.wav"), Path("out.json"))


def fake_worker_env(tmp_path: Path, *lines: str, exit_code: int = 0) -> Path:
    """A worker environment whose python is a Python process printing ``lines``."""
    python = tmp_path / "venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text(
        f"#!{sys.executable}\nimport sys\n"
        f"for line in {list(lines)!r}:\n    print(line, flush=True)\nsys.exit({exit_code})\n"
    )
    python.chmod(0o755)
    return tmp_path / "venv"


def transcription_progress(worker_env: Path) -> list[float]:
    heard: list[float] = []
    LocalTranscriber(worker_env=worker_env).transcribe(
        Path("a.wav"), Path("out.json"), on_progress=heard.append
    )
    return heard


def test_recognition_progress_of_the_worker_is_most_of_the_transcription(
    tmp_path: Path,
) -> None:
    worker_env = fake_worker_env(tmp_path, "etapa 1/2: reconhecimento", "Progress: 50.00%...")

    assert transcription_progress(worker_env) == [pytest.approx(0.45)]


def test_alignment_fills_the_rest_of_the_transcription_after_the_recognition(
    tmp_path: Path,
) -> None:
    worker_env = fake_worker_env(
        tmp_path,
        "etapa 1/2: reconhecimento",
        "Progress: 100.00%...",
        "etapa 2/2: alinhamento por palavra",
        "Progress: 50.00%...",
    )

    assert transcription_progress(worker_env) == [
        pytest.approx(0.9),
        pytest.approx(0.9),
        pytest.approx(0.95),
    ]


def test_worker_output_still_goes_to_the_output_of_the_task(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    lines = ("etapa 1/2: reconhecimento", "Progress: 50.00%...", "linha qualquer do WhisperX")
    worker_env = fake_worker_env(tmp_path, *lines)

    transcription_progress(worker_env)

    assert capfd.readouterr().out.splitlines() == list(lines)


def test_worker_that_fails_is_still_a_failed_process(tmp_path: Path) -> None:
    worker_env = fake_worker_env(tmp_path, "Progress: 10.00%...", exit_code=1)

    with pytest.raises(subprocess.CalledProcessError):
        transcription_progress(worker_env)
