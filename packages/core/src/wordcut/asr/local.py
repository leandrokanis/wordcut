"""Run the transcription worker on this machine.

The worker needs WhisperX, which lives in its own virtualenv (heavy CUDA
dependencies), so it runs as a subprocess of that environment's interpreter.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

PACKAGE_PARENT = Path(__file__).resolve().parents[2]
DEFAULT_WORKER_ENV = Path.home() / ".local/share/wordcut/venv"

# WhisperX prints "Progress: N%..." with print_progress=True in both stages of the worker,
# which announces the second one (wordcut.asr.worker).
WORKER_PROGRESS = re.compile(r"Progress: (\d+(?:\.\d+)?)%")
ALIGNMENT_STAGE = "etapa 2/2"
RECOGNITION_SHARE = 0.9


class LocalTranscriber:
    def __init__(self, model: str = "large-v3", worker_env: Path = DEFAULT_WORKER_ENV) -> None:
        self._model = model
        self._python = worker_env / "bin/python"

    def transcribe(
        self, audio: Path, output: Path, *, on_progress: Callable[[float], None] | None = None
    ) -> None:
        if not self._python.exists():
            raise FileNotFoundError(
                f"ambiente do WhisperX não encontrado em {self._python.parent.parent}; "
                "veja a seção Instalação do README"
            )
        command = self.command(audio, output)
        with subprocess.Popen(
            command, stdout=subprocess.PIPE, text=True, env=self._env()
        ) as process:
            assert process.stdout is not None
            progress = _WorkerProgress()
            for line in process.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                fraction = progress.read(line)
                if fraction is not None and on_progress is not None:
                    on_progress(fraction)
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command)

    def command(self, audio: Path, output: Path) -> list[str]:
        return [
            str(self._python), "-u", "-m", "wordcut.asr.worker",
            str(audio), str(output), "--model", self._model,
        ]  # fmt: skip

    def _env(self) -> dict[str, str]:
        return {**os.environ, "PYTHONPATH": str(PACKAGE_PARENT)}


class _WorkerProgress:
    """How far the worker is, from its output: recognition first, then alignment."""

    def __init__(self) -> None:
        self._aligning = False

    def read(self, line: str) -> float | None:
        """The progress ``line`` tells, if any."""
        if line.startswith(ALIGNMENT_STAGE):
            self._aligning = True
            return RECOGNITION_SHARE
        found = WORKER_PROGRESS.match(line)
        if found is None:
            return None
        done = float(found.group(1)) / 100
        if self._aligning:
            return RECOGNITION_SHARE + (1 - RECOGNITION_SHARE) * done
        return RECOGNITION_SHARE * done
