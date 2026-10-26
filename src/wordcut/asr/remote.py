"""Run the transcription worker on a remote CUDA host over SSH.

The worker runs detached from the SSH session, so a dropped connection (e.g. a
Wi-Fi hiccup during a 30-minute job) does not kill it. The client polls a
status file and can re-attach to a running job by its id.
"""

from __future__ import annotations

import shlex
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parents[1]
POLL_INTERVAL_S = 15.0
MAX_CONSECUTIVE_POLL_FAILURES = 20


class RemoteJobError(RuntimeError):
    """The remote worker exited with an error; its log tail is in the message."""


@dataclass(frozen=True)
class RemoteHost:
    """SSH host with the worker environment installed under ``home``.

    Layout on the host::

        <home>/venv/        virtualenv with the ``asr`` extra
        <home>/src/         copy of this package, synced before each run
        <home>/jobs/<id>/   audio.wav, transcript.json, log, status
    """

    name: str
    home: str = "~/.local/share/wordcut"

    def ssh_command(self, remote_command: str) -> list[str]:
        return ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", self.name, remote_command]

    def job_dir(self, job_id: str) -> str:
        return f"{self.home}/jobs/{job_id}"


class RemoteTranscriber:
    def __init__(self, host: RemoteHost, model: str = "large-v3") -> None:
        self._host = host
        self._model = model

    def transcribe(self, audio: Path, output: Path) -> None:
        job_id = self.submit(audio)
        print(f"job remoto: {job_id} (retome com --job {job_id})", file=sys.stderr)
        self.wait_and_fetch(job_id, output)

    def submit(self, audio: Path) -> str:
        """Upload ``audio`` and start the worker detached. Returns the job id."""
        self._sync_package()
        jobs = f"{self._host.home}/jobs"
        job_dir = _run(
            self._host.ssh_command(f"mkdir -p {jobs} && mktemp -d {jobs}/XXXXXX"), capture=True
        ).strip()
        job_id = job_dir.rsplit("/", 1)[-1]
        _run(["scp", "-q", str(audio), f"{self._host.name}:{job_dir}/audio.wav"])
        _run(self._host.ssh_command(self._launch_command(job_id)))
        return job_id

    def wait_and_fetch(self, job_id: str, output: Path) -> None:
        """Block until the job finishes, then download its transcript.

        The remote job directory is removed only on success; on failure it is
        kept for inspection.
        """
        status = self._wait(job_id)
        job_dir = self._host.job_dir(job_id)
        if status != 0:
            raise RemoteJobError(
                f"worker saiu com código {status}; log em {self._host.name}:{job_dir}/log\n"
                + self._log_tail(job_id)
            )
        _run(["scp", "-q", f"{self._host.name}:{job_dir}/transcript.json", str(output)])
        _run(self._host.ssh_command(f"rm -rf {job_dir}"))

    def _launch_command(self, job_id: str) -> str:
        job_dir = self._host.job_dir(job_id)
        home = self._host.home
        worker = (
            f"PYTHONPATH={home}/src {home}/venv/bin/python -u -m wordcut.asr.worker "
            f"{job_dir}/audio.wav {job_dir}/transcript.json --model {shlex.quote(self._model)}"
        )
        # setsid + nohup: survive the SSH session; status is written when the worker exits.
        job = f"{worker} > {job_dir}/log 2>&1; echo $? > {job_dir}/status"
        return f"setsid nohup sh -c {shlex.quote(job)} > /dev/null 2>&1 < /dev/null &"

    def _wait(self, job_id: str) -> int:
        job_dir = self._host.job_dir(job_id)
        probe = f"cat {job_dir}/status 2>/dev/null; echo '--'; tail -c 300 {job_dir}/log"
        failures = 0
        last_progress = ""
        while True:
            try:
                reply = _run(self._host.ssh_command(probe), capture=True)
                failures = 0
            except subprocess.CalledProcessError:
                failures += 1
                if failures >= MAX_CONSECUTIVE_POLL_FAILURES:
                    raise
                time.sleep(POLL_INTERVAL_S)
                continue
            status, _, log_tail = reply.partition("--\n")
            progress = _last_progress_line(log_tail)
            if progress and progress != last_progress:
                print(progress, file=sys.stderr)
                last_progress = progress
            if status.strip():
                return int(status)
            time.sleep(POLL_INTERVAL_S)

    def _log_tail(self, job_id: str) -> str:
        return _run(
            self._host.ssh_command(f"tail -n 20 {self._host.job_dir(job_id)}/log"), capture=True
        )

    def _sync_package(self) -> None:
        destination = f"{self._host.name}:{self._host.home}/src/"
        _run(
            [
                "rsync", "-a", "--delete", "--exclude", "__pycache__",
                str(PACKAGE_DIR), destination,
            ]
        )  # fmt: skip


def _last_progress_line(log_tail: str) -> str:
    lines = [line.strip() for line in log_tail.replace("\r", "\n").splitlines()]
    progress = [line for line in lines if "Progress" in line or line.startswith("etapa")]
    return progress[-1] if progress else ""


def _run(command: Sequence[str], capture: bool = False) -> str:
    result = subprocess.run(command, check=True, capture_output=capture, text=True)
    return result.stdout if capture else ""
