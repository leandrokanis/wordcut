"""Where the data of a Wordcut installation lives (docs/cli.md §14)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PRIVATE_FOLDER_MODE = 0o700


@dataclass(frozen=True)
class Home:
    root: Path

    @classmethod
    def from_environment(cls) -> Home:
        override = os.environ.get("WORDCUT_HOME")
        return cls(Path(override) if override else Path.home() / ".local/share/wordcut")

    @property
    def database(self) -> Path:
        return self.root / "wordcut.db"

    @property
    def lock_file(self) -> Path:
        return self.root / "processing.lock"

    def task_log(self, task_id: int) -> Path:
        """The output of the detached process of task ``task_id``."""
        return self.root / "tasks" / f"{task_id}.log"

    def sermon_media(self, sermon_id: int) -> Path:
        """The folder of the media files of sermon ``sermon_id``."""
        return self.root / "media" / "sermons" / str(sermon_id)

    def cut_media(self, cut_id: int) -> Path:
        """The folder of the exports of cut ``cut_id``."""
        return self.root / "media" / "cuts" / str(cut_id)

    def ensure(self) -> None:
        """Create the data folder, readable only by its owner, if it does not exist."""
        self.root.mkdir(mode=PRIVATE_FOLDER_MODE, parents=True, exist_ok=True)
