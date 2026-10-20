from pathlib import Path

import pytest

from cortes_pregacao.asr.local import LocalTranscriber


def test_command_runs_worker_module_with_env_python(tmp_path: Path) -> None:
    transcriber = LocalTranscriber(model="large-v3", worker_env=tmp_path / "venv")

    command = transcriber.command(Path("a.wav"), Path("out.json"))

    assert command[0] == str(tmp_path / "venv/bin/python")
    assert command[1:] == [
        "-u", "-m", "cortes_pregacao.asr.worker", "a.wav", "out.json", "--model", "large-v3",
    ]  # fmt: skip


def test_missing_worker_env_gives_actionable_error(tmp_path: Path) -> None:
    transcriber = LocalTranscriber(worker_env=tmp_path / "missing")

    with pytest.raises(FileNotFoundError, match="README"):
        transcriber.transcribe(Path("a.wav"), Path("out.json"))
