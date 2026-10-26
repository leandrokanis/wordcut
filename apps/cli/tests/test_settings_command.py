import getpass
import io
import json
import os
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from wordcut_cli import main

FAKE_KEY = "sk-ficticia-0000abcd"
FAKE_COOKIES = "# Netscape HTTP Cookie File\n.example.com\tTRUE\t/\tTRUE\t0\tSID\tficticio\n"


@pytest.fixture(autouse=True)
def home(wordcut_home: Path) -> Path:
    return wordcut_home


@pytest.fixture(autouse=True)
def open_umask() -> Iterator[None]:
    """A permissive umask, so a mode that is not set by the code shows up in the test."""
    previous = os.umask(0o022)
    try:
        yield
    finally:
        os.umask(previous)


def redirect_stdin(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    """Stdin as when a file is redirected to it (``< arquivo``): not a terminal."""
    monkeypatch.setattr(sys, "stdin", io.StringIO(text))


class Terminal(io.StringIO):
    """Stdin as a terminal: what is typed there comes through ``getpass``, without echo."""

    def isatty(self) -> bool:
        return True

    def read(self, size: int | None = -1) -> str:
        raise AssertionError("read the terminal with echo; use getpass")


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main(argv)
    return exit_code, json.loads(capsys.readouterr().out)


def test_show_of_a_new_installation_has_only_the_whisperx_model_set(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_json(["settings", "show", "--json"], capsys) == (
        0,
        {
            "llm_model": None,
            "whisper_model": "large-v3",
            "llm_key": None,
            "youtube_cookies": False,
            "default_preset_id": None,
        },
    )


def test_set_changes_both_models_and_show_reflects_them(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        ["settings", "set", "--model", "openai/gpt-ficticio", "--whisper-model", "medium"]
    )
    capsys.readouterr()

    _, shown = run_json(["settings", "show", "--json"], capsys)

    assert (exit_code, shown["llm_model"], shown["whisper_model"]) == (
        0,
        "openai/gpt-ficticio",
        "medium",
    )


def test_set_key_reads_the_key_from_redirected_stdin_into_a_private_file(
    wordcut_config: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    redirect_stdin(monkeypatch, f"{FAKE_KEY}\n")

    exit_code = main(["settings", "set-key"])
    capsys.readouterr()

    _, shown = run_json(["settings", "show", "--json"], capsys)
    mode = os.stat(wordcut_config / "openrouter-key").st_mode & 0o777
    assert (exit_code, mode, shown["llm_key"]) == (0, 0o600, "••••abcd")


def test_set_key_on_a_terminal_reads_the_key_without_echo(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdin", Terminal())
    monkeypatch.setattr(getpass, "getpass", lambda prompt="": FAKE_KEY)

    exit_code = main(["settings", "set-key"])
    capsys.readouterr()

    _, shown = run_json(["settings", "show", "--json"], capsys)
    assert (exit_code, shown["llm_key"]) == (0, "••••abcd")


@pytest.mark.parametrize("output", [["--json"], []], ids=["json", "text"])
def test_the_key_appears_in_no_output_of_set_key_nor_of_show(
    output: list[str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    redirect_stdin(monkeypatch, FAKE_KEY)

    exit_codes = [main(["settings", "set-key", *output]), main(["settings", "show", *output])]

    printed = capsys.readouterr()
    assert (exit_codes, FAKE_KEY in printed.out + printed.err) == ([0, 0], False)


def test_show_without_json_describes_a_new_installation_in_portuguese(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["settings", "show"])

    assert (exit_code, capsys.readouterr().out) == (
        0,
        "Modelo do LLM: não escolhido\n"
        "Modelo do WhisperX: large-v3\n"
        "Chave do LLM: não gravada\n"
        "Cookies do YouTube: não gravados\n"
        "Preset padrão: nenhum\n",
    )


def test_set_cookies_reads_the_cookies_from_redirected_stdin_into_a_private_file(
    wordcut_config: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    redirect_stdin(monkeypatch, FAKE_COOKIES)

    exit_code = main(["settings", "set-cookies"])
    capsys.readouterr()

    _, shown = run_json(["settings", "show", "--json"], capsys)
    mode = os.stat(wordcut_config / "youtube-cookies.txt").st_mode & 0o777
    assert (exit_code, mode, shown["youtube_cookies"]) == (0, 0o600, True)


def test_set_cookies_on_a_terminal_asks_for_the_file_to_be_redirected(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdin", Terminal())

    exit_code, printed = run_json(["settings", "set-cookies", "--json"], capsys)

    error = printed["error"]
    assert (exit_code, error["code"], "set-cookies < " in error["message"]) == (
        2,
        "invalid_argument",
        True,
    )


@pytest.mark.parametrize(
    ("action", "secret"),
    [("set-key", "openrouter-key"), ("set-cookies", "youtube-cookies.txt")],
)
@pytest.mark.parametrize("text", ["", " \n"], ids=["empty", "blank"])
def test_an_empty_stdin_is_refused_and_nothing_is_stored(
    action: str,
    secret: str,
    text: str,
    wordcut_config: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    redirect_stdin(monkeypatch, text)

    exit_code, printed = run_json(["settings", action, "--json"], capsys)

    assert (exit_code, printed["error"]["code"], (wordcut_config / secret).exists()) == (
        2,
        "invalid_argument",
        False,
    )


@pytest.mark.parametrize(
    ("action", "secret", "stdin"),
    [
        ("set-key", "openrouter-key", FAKE_KEY),
        ("set-cookies", "youtube-cookies.txt", FAKE_COOKIES),
    ],
    ids=["set-key", "set-cookies"],
)
@pytest.mark.parametrize(
    "given",
    [[FAKE_KEY], ["--key", FAKE_KEY], [f"--key={FAKE_KEY}"]],
    ids=["positional", "option", "option="],
)
@pytest.mark.parametrize("output", [["--json"], []], ids=["json", "text"])
def test_a_secret_given_as_argument_is_refused_without_being_echoed(
    action: str,
    secret: str,
    stdin: str,
    given: list[str],
    output: list[str],
    wordcut_config: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A valid secret waits on stdin, so only the refusal of the argument can stop the write.
    redirect_stdin(monkeypatch, stdin)

    exit_code = main(["settings", action, *given, *output])

    printed = capsys.readouterr()
    assert (
        exit_code,
        FAKE_KEY in printed.out + printed.err,
        (wordcut_config / secret).exists(),
    ) == (
        2,
        False,
        False,
    )


@pytest.mark.parametrize(
    "given",
    [[FAKE_KEY], ["--key", FAKE_KEY, "set-key"], [FAKE_KEY, "set-key"]],
    ids=["in-place-of-the-action", "option-before-the-action", "before-the-action"],
)
@pytest.mark.parametrize("output", [["--json"], []], ids=["json", "text"])
def test_a_secret_given_where_the_action_goes_is_refused_without_being_echoed(
    given: list[str],
    output: list[str],
    wordcut_config: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    redirect_stdin(monkeypatch, FAKE_KEY)

    exit_code = main(["settings", *given, *output])

    printed = capsys.readouterr()
    assert (
        exit_code,
        FAKE_KEY in printed.out + printed.err,
        (wordcut_config / "openrouter-key").exists(),
    ) == (
        2,
        False,
        False,
    )


SECRET_AS_OPTION = "--sk-or-v1-ficticia"


@pytest.mark.parametrize(
    "argv",
    [
        ["sermon", "list", SECRET_AS_OPTION],
        ["settings", "set", SECRET_AS_OPTION],
        ["settings", "set-key", SECRET_AS_OPTION],
        [SECRET_AS_OPTION],
    ],
    ids=["sermon-list", "settings-set", "settings-set-key", "root"],
)
@pytest.mark.parametrize("output", [["--json"], []], ids=["json", "text"])
def test_a_secret_shaped_like_an_option_is_refused_without_being_repeated(
    argv: list[str],
    output: list[str],
    wordcut_config: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A valid key waits on stdin, so only the refusal of the argument can stop the write.
    redirect_stdin(monkeypatch, FAKE_KEY)

    exit_code = main([*argv, *output])
    printed = capsys.readouterr()
    _, shown = run_json(["settings", "show", "--json"], capsys)

    assert (
        exit_code,
        "sk-or-v1-ficticia" in printed.out + printed.err,
        wordcut_config.exists() and sorted(p.name for p in wordcut_config.iterdir()),
        shown["llm_model"],
    ) == (2, False, False, None)


def read_only(folder: Path) -> None:
    folder.mkdir()
    folder.chmod(0o500)


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes to a read-only folder")
def test_set_key_into_a_read_only_folder_is_a_config_not_writable_error(
    wordcut_config: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    read_only(wordcut_config)
    redirect_stdin(monkeypatch, FAKE_KEY)

    exit_code, printed = run_json(["settings", "set-key", "--json"], capsys)

    assert (exit_code, printed["error"]["code"]) == (5, "config_not_writable")


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes to a read-only folder")
@pytest.mark.parametrize("output", [["--json"], []], ids=["json", "text"])
def test_the_read_only_folder_error_does_not_carry_the_key(
    output: list[str],
    wordcut_config: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    read_only(wordcut_config)
    redirect_stdin(monkeypatch, FAKE_KEY)

    main(["settings", "set-key", *output])

    printed = capsys.readouterr()
    assert FAKE_KEY not in printed.out + printed.err


@pytest.mark.parametrize("action", ["show", "set", "set-key", "set-cookies"])
def test_each_settings_action_help_says_it_is_for_the_administrator_with_an_example(
    action: str, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["settings", action, "--help"])

    help_text = capsys.readouterr().out
    assert (
        exit_code,
        "administrador" in help_text,
        f"wordcut settings {action} " in help_text,
    ) == (
        0,
        True,
        True,
    )


def test_set_without_any_model_is_an_invalid_argument_naming_the_options(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code, printed = run_json(["settings", "set", "--json"], capsys)

    error = printed["error"]
    assert (exit_code, error["code"], "argument" in error["details"]) == (
        2,
        "invalid_argument",
        True,
    )
