"""Run the transcription worker on this machine.

The worker needs WhisperX, which lives in its own virtualenv (heavy CUDA
dependencies), so it runs as a subprocess of that environment's interpreter.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

PACKAGE_PARENT = Path(__file__).resolve().parents[2]
DEFAULT_WORKER_ENV = Path.home() / ".local/share/cortes-pregacao/venv"


class LocalTranscriber:
    def __init__(self, model: str = "large-v3", worker_env: Path = DEFAULT_WORKER_ENV) -> None:
        self._model = model
        self._python = worker_env / "bin/python"

    def transcribe(self, audio: Path, output: Path) -> None:
        if not self._python.exists():
            raise FileNotFoundError(
                f"ambiente do WhisperX não encontrado em {self._python.parent.parent}; "
                "veja a seção Instalação do README"
            )
        subprocess.run(self.command(audio, output), check=True, env=self._env())

    def command(self, audio: Path, output: Path) -> list[str]:
        return [
            str(self._python), "-u", "-m", "cortes_pregacao.asr.worker",
            str(audio), str(output), "--model", self._model,
        ]  # fmt: skip

    def _env(self) -> dict[str, str]:
        return {**os.environ, "PYTHONPATH": str(PACKAGE_PARENT)}
