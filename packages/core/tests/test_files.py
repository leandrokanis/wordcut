import errno
import os
import shutil
from datetime import date
from pathlib import Path
from typing import BinaryIO

import pytest

from wordcut.files import copy_without_overwrite, folder_name, remove_within

SUGGESTED = "2026-10-18 - Culto de domingo.mp4"
# Arbitrary, non-repeating bytes: a copy that drops or reorders any of them is caught.
VIDEO = bytes(range(256)) * 3 + b"end of the sermon"
# Errors of os.link on a filesystem without hard links (FAT, some network shares) or when the
# link would cross devices.
NO_HARD_LINK = [
    pytest.param(errno.EPERM, id="EPERM"),
    pytest.param(errno.ENOTSUP, id="ENOTSUP"),
    pytest.param(errno.EOPNOTSUPP, id="EOPNOTSUPP"),
    pytest.param(errno.EXDEV, id="EXDEV"),
]


def video_in(folder: Path) -> Path:
    source = folder / "media" / "sermon.mp4"
    source.parent.mkdir(parents=True)
    source.write_bytes(VIDEO)
    return source


def test_copy_to_a_file_path_writes_identical_bytes_and_returns_that_absolute_path(
    tmp_path: Path,
) -> None:
    source = video_in(tmp_path)
    destination = tmp_path / "out" / "pregacao.mp4"
    destination.parent.mkdir()

    copied = copy_without_overwrite(source, destination, SUGGESTED)

    assert (copied, copied.is_absolute(), copied.read_bytes()) == (destination, True, VIDEO)


def test_copy_creates_the_missing_folders_of_the_destination(tmp_path: Path) -> None:
    source = video_in(tmp_path)
    destination = tmp_path / "x" / "y" / "pregacao.mp4"

    copy_without_overwrite(source, destination, SUGGESTED)

    assert destination.read_bytes() == VIDEO


def test_copy_to_an_existing_folder_writes_the_suggested_name_inside_it(tmp_path: Path) -> None:
    source = video_in(tmp_path)
    folder = tmp_path / "downloads"
    folder.mkdir()

    copied = copy_without_overwrite(source, folder, SUGGESTED)

    assert (copied, copied.read_bytes()) == (folder / SUGGESTED, VIDEO)


def test_existing_destination_is_kept_and_the_copy_gets_2_before_the_extension(
    tmp_path: Path,
) -> None:
    source = video_in(tmp_path)
    taken = tmp_path / SUGGESTED
    taken.write_bytes(b"older download")

    copied = copy_without_overwrite(source, taken, SUGGESTED)

    assert (copied.name, copied.read_bytes(), taken.read_bytes()) == (
        "2026-10-18 - Culto de domingo (2).mp4",
        VIDEO,
        b"older download",
    )


def test_with_2_taken_too_the_copy_gets_3_and_both_earlier_files_are_kept(
    tmp_path: Path,
) -> None:
    source = video_in(tmp_path)
    first = tmp_path / SUGGESTED
    second = tmp_path / "2026-10-18 - Culto de domingo (2).mp4"
    first.write_bytes(b"first download")
    second.write_bytes(b"second download")

    copied = copy_without_overwrite(source, tmp_path, SUGGESTED)

    assert (copied.name, copied.read_bytes(), first.read_bytes(), second.read_bytes()) == (
        "2026-10-18 - Culto de domingo (3).mp4",
        VIDEO,
        b"first download",
        b"second download",
    )


def test_after_a_copy_the_destination_folder_holds_only_the_copied_file(
    tmp_path: Path,
) -> None:
    source = video_in(tmp_path)
    folder = tmp_path / "downloads"

    copy_without_overwrite(source, folder / "pregacao.mp4", SUGGESTED)

    assert [path.name for path in folder.iterdir()] == ["pregacao.mp4"]


def test_a_copy_that_fails_midway_leaves_neither_the_final_name_nor_a_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = video_in(tmp_path)
    folder = tmp_path / "downloads"
    folder.mkdir()

    def copy_half_then_fail(origin: Path, target: Path) -> None:
        Path(target).write_bytes(VIDEO[: len(VIDEO) // 2])
        raise OSError("disk full")

    monkeypatch.setattr(shutil, "copyfile", copy_half_then_fail)

    with pytest.raises(OSError, match="disk full"):
        copy_without_overwrite(source, folder / "pregacao.mp4", SUGGESTED)

    assert list(folder.iterdir()) == []


def test_a_relative_destination_is_resolved_against_the_current_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = video_in(tmp_path)
    current = tmp_path / "current"
    current.mkdir()
    monkeypatch.chdir(current)

    copied = copy_without_overwrite(source, Path("sub/pregacao.mp4"), SUGGESTED)

    assert (copied, copied.read_bytes()) == (current / "sub" / "pregacao.mp4", VIDEO)


def test_a_missing_destination_ending_in_a_separator_is_a_folder_created_with_the_name_inside(
    tmp_path: Path,
) -> None:
    source = video_in(tmp_path)

    copied = copy_without_overwrite(source, f"{tmp_path}/saida/", SUGGESTED)

    assert (copied, copied.read_bytes()) == (tmp_path / "saida" / SUGGESTED, VIDEO)


def refuse_hard_links(monkeypatch: pytest.MonkeyPatch, code: int) -> None:
    def link(origin: object, target: object) -> None:
        raise OSError(code, os.strerror(code))

    monkeypatch.setattr(os, "link", link)


@pytest.mark.parametrize("code", NO_HARD_LINK)
def test_without_hard_links_the_copy_still_lands_with_identical_bytes_and_no_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    source = video_in(tmp_path)
    folder = tmp_path / "downloads"
    refuse_hard_links(monkeypatch, code)

    copied = copy_without_overwrite(source, folder / "pregacao.mp4", SUGGESTED)

    assert (copied.read_bytes(), [path.name for path in folder.iterdir()]) == (
        VIDEO,
        ["pregacao.mp4"],
    )


@pytest.mark.parametrize("code", NO_HARD_LINK)
def test_without_hard_links_an_existing_destination_is_kept_and_the_copy_gets_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    source = video_in(tmp_path)
    taken = tmp_path / SUGGESTED
    taken.write_bytes(b"older download")
    refuse_hard_links(monkeypatch, code)

    copied = copy_without_overwrite(source, tmp_path, SUGGESTED)

    assert (copied.name, copied.read_bytes(), taken.read_bytes()) == (
        "2026-10-18 - Culto de domingo (2).mp4",
        VIDEO,
        b"older download",
    )


def test_another_link_error_propagates_and_leaves_the_destination_folder_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = video_in(tmp_path)
    folder = tmp_path / "downloads"
    refuse_hard_links(monkeypatch, errno.EIO)

    with pytest.raises(OSError) as raised:
        copy_without_overwrite(source, folder / "pregacao.mp4", SUGGESTED)

    assert (raised.value.errno, list(folder.iterdir())) == (errno.EIO, [])


def test_without_hard_links_a_failed_copy_leaves_no_final_name_and_no_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = video_in(tmp_path)
    folder = tmp_path / "downloads"
    refuse_hard_links(monkeypatch, errno.EXDEV)

    def copy_half_then_fail(origin: BinaryIO, target: BinaryIO) -> None:
        target.write(origin.read(len(VIDEO) // 2))
        raise OSError("disk full")

    monkeypatch.setattr(shutil, "copyfileobj", copy_half_then_fail)

    with pytest.raises(OSError, match="disk full"):
        copy_without_overwrite(source, folder / "pregacao.mp4", SUGGESTED)

    assert list(folder.iterdir()) == []


def test_folder_name_strips_path_unsafe_characters() -> None:
    assert folder_name(date(2026, 1, 2), 'Quem é "Deus"?/') == "2026-01-02 - Quem é Deus"


def test_remove_within_takes_a_folder_with_what_it_holds_and_a_file(tmp_path: Path) -> None:
    root = tmp_path / "home"
    folder, file = root / "media" / "cuts" / "3", root / "tasks" / "9.log"
    (folder / "work").mkdir(parents=True)
    (folder / "4.mp4").write_bytes(VIDEO)
    file.parent.mkdir()
    file.write_text("log")

    remove_within(root, [folder, file])

    assert (folder.exists(), file.exists()) == (False, False)


def test_remove_within_skips_what_is_already_gone(tmp_path: Path) -> None:
    root = tmp_path / "home"
    root.mkdir()
    kept = root / "kept.mp4"
    kept.write_bytes(VIDEO)

    remove_within(root, [root / "gone", root / "gone.mp4", kept])

    assert not kept.exists()


@pytest.mark.parametrize("escape", ["../outside.mp4", "media/../../outside.mp4", "absolute"])
def test_remove_within_never_removes_outside_its_root(tmp_path: Path, escape: str) -> None:
    root = tmp_path / "home"
    root.mkdir()
    bait = tmp_path / "outside.mp4"
    bait.write_bytes(VIDEO)

    remove_within(root, [bait if escape == "absolute" else root / escape])

    assert bait.read_bytes() == VIDEO


def test_remove_within_never_removes_its_root_itself(tmp_path: Path) -> None:
    root = tmp_path / "home"
    root.mkdir()

    remove_within(root, [root, root / "media" / ".."])

    assert root.is_dir()


def test_remove_within_does_not_follow_a_link_that_leads_outside(tmp_path: Path) -> None:
    root = tmp_path / "home"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.mp4").write_bytes(VIDEO)
    (root / "link").symlink_to(outside)

    remove_within(root, [root / "link"])

    assert (outside / "keep.mp4").read_bytes() == VIDEO


def test_remove_within_skips_a_path_that_leaves_its_root_through_a_link_on_the_way(
    tmp_path: Path,
) -> None:
    root = tmp_path / "home"
    root.mkdir()
    outside = tmp_path / "outside"
    (outside / "cuts" / "3").mkdir(parents=True)
    (outside / "cuts" / "3" / "4.mp4").write_bytes(VIDEO)
    (root / "media").symlink_to(outside)

    remove_within(root, [root / "media" / "cuts" / "3"])

    assert (outside / "cuts" / "3" / "4.mp4").read_bytes() == VIDEO
