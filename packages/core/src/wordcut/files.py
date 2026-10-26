"""Copies of media files to a place the user chose, never overwriting what is there, and the
readable names they suggest."""

from __future__ import annotations

import errno
import os
import re
import shutil
import uuid
from collections.abc import Iterator
from datetime import date
from itertools import count
from pathlib import Path

# The first number given to a copy whose name is taken: "Name (2).mp4".
FIRST_COPY_NUMBER = 2

# os.link fails this way on filesystems without hard links (FAT, some network shares) and
# across devices; the copy then falls back to an exclusive create of the final name.
NO_HARD_LINK = frozenset({errno.EPERM, errno.ENOTSUP, errno.EOPNOTSUPP, errno.EXDEV})

# Characters that some filesystem refuses in a file name.
PATH_UNSAFE = re.compile(r'[/\\:*?"<>|]')


def folder_name(service_date: date, title: str) -> str:
    """``2026-10-18 - Título``, without the characters a file name cannot hold."""
    clean_title = re.sub(r"\s+", " ", PATH_UNSAFE.sub("", title)).strip()
    return f"{service_date.isoformat()} - {clean_title}"


def copy_without_overwrite(
    source: Path, destination: str | os.PathLike[str], suggested_name: str
) -> Path:
    """Copy ``source`` to ``destination`` and return the absolute path of the copy.

    ``destination`` is a file path, or a folder (one that exists, or any path ending in a
    separator) that receives ``suggested_name``. A relative path starts at the current
    folder, and missing folders are created. A taken name is never overwritten: the copy
    gets the first free one of ``Name (2).ext``, ``Name (3).ext``… The final name appears
    only once the copy is complete, except on a filesystem without hard links, where the
    copy is written under the final name and removed if it fails.
    """
    target = _target(destination, suggested_name)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".wordcut-{uuid.uuid4().hex}.part"
    try:
        shutil.copyfile(source, temporary)
        return _placed(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _target(destination: str | os.PathLike[str], suggested_name: str) -> Path:
    path = Path(destination).absolute()
    if _names_a_folder(destination) or path.is_dir():
        return path / suggested_name
    return path


def _names_a_folder(destination: str | os.PathLike[str]) -> bool:
    return os.fspath(destination).endswith((os.sep, os.altsep or os.sep))


def _placed(temporary: Path, target: Path) -> Path:
    """Give ``temporary`` the first free name among ``target``, ``target (2)``…

    ``os.link``, and the exclusive create that stands in for it, fail when the name exists,
    so a file that appears between two tries is never overwritten, unlike ``os.replace``.
    """
    candidates = _candidates(target)
    while True:
        candidate = next(candidates)
        try:
            _place(temporary, candidate)
        except FileExistsError:
            continue
        return candidate


def _place(temporary: Path, candidate: Path) -> None:
    try:
        os.link(temporary, candidate)
    except OSError as error:
        if error.errno not in NO_HARD_LINK:
            raise
        _copy_exclusive(temporary, candidate)


def _copy_exclusive(temporary: Path, candidate: Path) -> None:
    """Copy ``temporary`` to ``candidate``, which must not exist yet.

    A copy that fails midway removes ``candidate``: it was created here, so it holds no one
    else's file.
    """
    with temporary.open("rb") as origin:
        copy = candidate.open("xb")
        try:
            with copy:
                shutil.copyfileobj(origin, copy)
        except BaseException:
            candidate.unlink(missing_ok=True)
            raise


def _candidates(target: Path) -> Iterator[Path]:
    yield target
    for number in count(FIRST_COPY_NUMBER):
        yield target.with_name(f"{target.stem} ({number}){target.suffix}")
