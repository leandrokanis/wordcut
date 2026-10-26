from pathlib import Path

import pytest

from wordcut.config import config_dir, youtube_cookies


def test_secrets_folder_is_wordcut_config_when_it_is_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WORDCUT_CONFIG", str(tmp_path / "segredos"))

    assert config_dir() == tmp_path / "segredos"


def test_secrets_folder_defaults_to_the_user_config_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("WORDCUT_CONFIG", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    assert config_dir() == tmp_path / ".config/wordcut"


def test_youtube_cookies_file_is_in_the_secrets_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WORDCUT_CONFIG", str(tmp_path))

    assert youtube_cookies() == tmp_path / "youtube-cookies.txt"
