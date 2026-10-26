import logging
import os
import stat
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from wordcut import config
from wordcut.db import connect
from wordcut.home import Home
from wordcut.service.settings import show_settings, update_settings


def test_the_settings_answer_as_the_cli_shows_them(admin: TestClient, home: Home) -> None:
    response = admin.get("/api/settings")

    with closing(connect(home)) as connection:
        expected = show_settings(connection)
    assert (response.status_code, response.json()) == (200, expected)


def test_changing_the_models_answers_the_settings_as_the_cli_changes_them(
    admin: TestClient, home: Home
) -> None:
    changes = {"llm_model": "provedor/modelo-de-teste", "whisper_model": "medium"}

    response = admin.patch("/api/settings", json=changes)

    with closing(connect(home)) as connection:
        expected = update_settings(connection, **changes)
    assert (response.status_code, response.json(), expected["whisper_model"]) == (
        200,
        expected,
        "medium",
    )


@pytest.mark.parametrize(
    ("changes", "argument"),
    [({}, "llm_model, whisper_model"), ({"whisper_model": "  "}, "whisper_model")],
    ids=["no model", "blank model"],
)
def test_changing_no_model_or_a_blank_one_is_invalid_argument(
    changes: dict[str, str], argument: str, admin: TestClient
) -> None:
    response = admin.patch("/api/settings", json=changes)

    assert (response.status_code, response.json()["error"]["details"]) == (
        400,
        {"argument": argument},
    )


# Fictitious, long and unique: the mask shows its last 4 characters on purpose (2.1.a).
FAKE_KEY = "sk-or-v1-ficticia-0123456789abcdef0123456789abcdef-WXYZ"
# Netscape cookie file (https://curl.se/docs/http-cookies.html): seven TAB-separated fields.
FAKE_COOKIE_VALUE = "valor-ficticio-0123456789abcdef0123456789abcdef"
FAKE_COOKIES = (
    "# Netscape HTTP Cookie File\n"
    f".youtube.com\tTRUE\t/\tTRUE\t1893456000\tSID-FICTICIO\t{FAKE_COOKIE_VALUE}\n"
)


def everything_said(response: Any, caplog: pytest.LogCaptureFixture) -> str:
    """The body and headers of the response and every line logged."""
    return response.text + str(dict(response.headers)) + caplog.text


def test_storing_the_llm_key_answers_the_settings_with_the_key_masked_never_in_clear(
    admin: TestClient, home: Home, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)

    response = admin.put("/api/settings/llm-key", json={"value": f"  {FAKE_KEY}\n"})

    with closing(connect(home)) as connection:
        expected = show_settings(connection)
    stored = config.llm_key_file()
    assert (
        response.status_code,
        response.json(),
        expected["llm_key"],
        FAKE_KEY in everything_said(response, caplog),
        stored.read_text(encoding="utf-8"),
        stat.S_IMODE(stored.stat().st_mode),
    ) == (200, expected, "••••WXYZ", False, FAKE_KEY, 0o600)


def test_an_empty_llm_key_is_invalid_argument_naming_value(admin: TestClient) -> None:
    response = admin.put("/api/settings/llm-key", json={"value": "  \n"})

    assert (response.status_code, response.json()["error"]["details"]) == (
        400,
        {"argument": "value"},
    )


def read_only(folder: Path) -> None:
    folder.mkdir()
    folder.chmod(0o500)


# ADR-0003: the containers mount the configuration folder read-only.
@pytest.mark.skipif(os.geteuid() == 0, reason="root writes to a read-only folder")
@pytest.mark.parametrize("route", ["llm-key", "youtube-cookies"])
def test_a_secret_into_a_read_only_folder_is_config_not_writable_without_the_secret(
    route: str, admin: TestClient, wordcut_config: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    read_only(wordcut_config)
    value = {"llm-key": FAKE_KEY, "youtube-cookies": FAKE_COOKIES}[route]

    response = admin.put(f"/api/settings/{route}", json={"value": value})

    said = everything_said(response, caplog)
    assert (
        response.status_code,
        response.json()["error"]["code"],
        FAKE_KEY in said or FAKE_COOKIE_VALUE in said,
    ) == (409, "config_not_writable", False)


# ADR-0021: the web never sees the folders of the server; the CLI, on the host, may.
@pytest.mark.skipif(os.geteuid() == 0, reason="root writes to a read-only folder")
@pytest.mark.parametrize("route", ["llm-key", "youtube-cookies"])
def test_a_secret_into_a_read_only_folder_never_shows_the_configuration_folder(
    route: str, admin: TestClient, wordcut_config: Path
) -> None:
    read_only(wordcut_config)
    value = {"llm-key": FAKE_KEY, "youtube-cookies": FAKE_COOKIES}[route]

    response = admin.put(f"/api/settings/{route}", json={"value": value})

    said = response.text + str(dict(response.headers))
    assert (
        response.status_code,
        str(wordcut_config) in said or "/config" in said,
        "details" in response.json()["error"],
    ) == (409, False, False)


def test_storing_the_cookies_answers_the_settings_with_them_present_never_in_clear(
    admin: TestClient, home: Home, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)

    response = admin.put("/api/settings/youtube-cookies", json={"value": FAKE_COOKIES})

    with closing(connect(home)) as connection:
        expected = show_settings(connection)
    said = everything_said(response, caplog)
    assert (
        response.status_code,
        response.json(),
        expected["youtube_cookies"],
        FAKE_COOKIE_VALUE in said or "SID-FICTICIO" in said,
        config.youtube_cookies().read_text(encoding="utf-8"),
    ) == (200, expected, True, False, FAKE_COOKIES)


@pytest.mark.parametrize("route", ["llm-key", "youtube-cookies"])
@pytest.mark.parametrize(
    "body",
    [{"value": 1}, {"value": None}, {}, {"value": "x", "segredo-digitado": 1}],
    ids=["not text", "null", "no value", "unknown field"],
)
def test_a_malformed_secret_body_is_invalid_argument_storing_nothing(
    route: str, body: dict[str, Any], admin: TestClient, wordcut_config: Path
) -> None:
    response = admin.put(f"/api/settings/{route}", json=body)

    assert (
        response.status_code,
        response.json()["error"]["code"],
        "segredo" in response.text,
        wordcut_config.exists() and any(wordcut_config.iterdir()),
    ) == (400, "invalid_argument", False, False)


def test_cookies_outside_the_netscape_format_are_refused_without_echo(
    admin: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    typed = f"SID={FAKE_COOKIE_VALUE}"

    response = admin.put("/api/settings/youtube-cookies", json={"value": typed})

    assert (
        response.status_code,
        response.json()["error"]["details"],
        FAKE_COOKIE_VALUE in everything_said(response, caplog),
        config.has_youtube_cookies(),
    ) == (400, {"argument": "value"}, False, False)
