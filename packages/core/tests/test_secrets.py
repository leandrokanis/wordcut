import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from wordcut.config import (
    has_youtube_cookies,
    llm_key_file,
    masked_llm_key,
    write_secret,
    youtube_cookies,
)
from wordcut.errors import WordcutError

FAKE_KEY = "sk-ficticia-0000abcd"


@pytest.fixture(autouse=True)
def open_umask() -> Iterator[None]:
    """A permissive umask, so a mode that is not set by the code shows up in the test."""
    previous = os.umask(0o022)
    try:
        yield
    finally:
        os.umask(previous)


def mode_of(path: Path) -> int:
    return os.stat(path).st_mode & 0o777


def test_a_secret_is_written_readable_only_by_its_owner(wordcut_config: Path) -> None:
    secret = wordcut_config / "openrouter-key"

    write_secret(secret, FAKE_KEY)

    assert mode_of(secret) == 0o600


def test_a_missing_secrets_folder_is_created_private_to_its_owner(wordcut_config: Path) -> None:
    write_secret(wordcut_config / "openrouter-key", FAKE_KEY)

    assert mode_of(wordcut_config) == 0o700


def test_rewriting_an_open_secret_leaves_only_the_new_content_private(
    wordcut_config: Path,
) -> None:
    secret = wordcut_config / "openrouter-key"
    wordcut_config.mkdir()
    secret.write_text("sk-ficticia-antiga-1111")
    secret.chmod(0o644)

    write_secret(secret, FAKE_KEY)

    assert (secret.read_text(), mode_of(secret)) == (FAKE_KEY, 0o600)


def test_a_failed_replace_keeps_the_previous_secret_and_leaves_no_temporary_file(
    wordcut_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = wordcut_config / "openrouter-key"
    write_secret(secret, "sk-ficticia-antiga-1111")

    def fail(source: object, destination: object) -> None:
        raise OSError("disco cheio")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(WordcutError):
        write_secret(secret, FAKE_KEY)

    assert [(path.name, path.read_text()) for path in wordcut_config.iterdir()] == [
        ("openrouter-key", "sk-ficticia-antiga-1111")
    ]


def test_a_temporary_file_left_by_an_interrupted_write_does_not_block_the_next_one(
    wordcut_config: Path,
) -> None:
    secret = wordcut_config / "openrouter-key"
    wordcut_config.mkdir()
    (wordcut_config / "openrouter-key.tmp").write_text("sk-ficticia-orfa-2222")

    write_secret(secret, FAKE_KEY)

    assert secret.read_text() == FAKE_KEY


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes to a read-only folder")
def test_a_read_only_secrets_folder_is_a_clear_error_without_the_secret(
    wordcut_config: Path,
) -> None:
    wordcut_config.mkdir()
    wordcut_config.chmod(0o500)

    with pytest.raises(WordcutError) as raised:
        write_secret(wordcut_config / "openrouter-key", FAKE_KEY)

    error = raised.value
    assert (error.code, error.exit_code, FAKE_KEY in repr(error.to_dict())) == (
        "config_not_writable",
        5,
        False,
    )


def test_the_masked_key_shows_only_its_last_four_characters() -> None:
    write_secret(llm_key_file(), FAKE_KEY)

    assert masked_llm_key() == "••••abcd"


def test_without_a_stored_key_there_is_no_masked_key() -> None:
    assert masked_llm_key() is None


@pytest.mark.parametrize(
    ("key", "masked"), [("sk-f1234", "••••1234"), ("sk-1234", "••••")], ids=["8 chars", "7 chars"]
)
def test_a_key_shorter_than_eight_characters_is_masked_whole(key: str, masked: str) -> None:
    write_secret(llm_key_file(), key)

    assert masked_llm_key() == masked


def test_cookies_are_present_only_once_stored() -> None:
    before = has_youtube_cookies()
    write_secret(youtube_cookies(), ".example.com\tTRUE\t/\tTRUE\t0\tSID\tficticio\n")

    assert (before, has_youtube_cookies()) == (False, True)
