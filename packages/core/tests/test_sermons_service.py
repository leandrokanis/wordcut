import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut.db import connect
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.service.sermons import create_sermon, list_sermons, show_sermon
from wordcut.youtube import LiveInfo, YouTubeError

VIDEO = "Ab3_x-9QzLk"
LINK = f"https://www.youtube.com/watch?v={VIDEO}"
NOW = datetime(2026, 10, 26, 19, 40, tzinfo=timezone(timedelta(hours=-3)))
FINISHED_LIVE = LiveInfo(
    title="Culto de domingo",
    service_date=date(2026, 10, 18),
    duration=7718.0,
    live_status="was_live",
)


def live_on(service_date: date) -> LiveInfo:
    return LiveInfo(
        title="Culto", service_date=service_date, duration=3600.0, live_status="was_live"
    )


def link(youtube_id: str) -> str:
    return f"https://youtu.be/{youtube_id}"


def listed(created: dict[str, Any]) -> dict[str, Any]:
    """What ``list_sermons`` shows of a sermon that has no borders nor cuts yet."""
    sermon = {field: value for field, value in created.items() if field != "created"}
    return {**sermon, "duration": None, "cut_counts": {"suggested": 0, "chosen": 0, "discarded": 0}}


class FakeLive:
    """``LiveSource`` double that answers ``info`` and counts the calls."""

    def __init__(self, info: LiveInfo = FINISHED_LIVE) -> None:
        self.answer = info
        self.calls = 0

    def info(self, url: str) -> LiveInfo:
        self.calls += 1
        return self.answer


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(Home(tmp_path))) as opened:
        yield opened


def test_first_sermon_of_a_finished_live_is_created_with_the_live_data(
    connection: sqlite3.Connection,
) -> None:
    sermon = create_sermon(connection, FakeLive(), LINK, now=NOW)

    assert (type(sermon["id"]), sermon) == (
        int,
        {
            "id": sermon["id"],
            "youtube_id": VIDEO,
            "url": LINK,
            "title": "Culto de domingo",
            "service_date": "2026-10-18",
            "live_duration": 7718.0,
            "live_finished": True,
            "status": "created",
            "created_at": "2026-10-26T19:40:00-03:00",
            "created": True,
        },
    )


def test_same_video_through_another_link_returns_the_existing_sermon_without_asking_youtube(
    connection: sqlite3.Connection,
) -> None:
    live = FakeLive()
    first = create_sermon(connection, live, LINK, now=NOW)

    again = create_sermon(connection, live, f"https://youtu.be/{VIDEO}?si=abc", now=NOW)

    assert (again, live.calls) == ({**first, "created": False}, 1)


def test_live_still_on_air_without_duration_is_created_unfinished_with_unknown_duration(
    connection: sqlite3.Connection,
) -> None:
    on_air = LiveInfo.from_metadata(
        {"title": "Culto ao vivo", "timestamp": 1792361083, "live_status": "is_live"}
    )

    sermon = create_sermon(connection, FakeLive(on_air), LINK, now=NOW)

    assert (sermon["live_finished"], sermon["live_duration"], sermon["created"]) == (
        False,
        None,
        True,
    )


def test_link_without_a_video_is_refused_before_asking_youtube(
    connection: sqlite3.Connection,
) -> None:
    live = FakeLive()

    with pytest.raises(WordcutError) as raised:
        create_sermon(connection, live, "https://vimeo.com/123456", now=NOW)

    assert (raised.value.code, raised.value.details, live.calls) == (
        "invalid_argument",
        {"argument": "link"},
        0,
    )


def test_sermons_are_listed_newest_service_first_with_zeroed_cut_counts(
    connection: sqlite3.Connection,
) -> None:
    older = create_sermon(connection, FakeLive(live_on(date(2026, 10, 11))), link("Aaaaaaaaaa1"))
    newer = create_sermon(connection, FakeLive(live_on(date(2026, 10, 18))), link("Aaaaaaaaaa2"))

    assert list_sermons(connection) == {
        "items": [listed(newer), listed(older)],
    }


def test_listing_by_status_keeps_only_the_sermons_in_that_state(
    connection: sqlite3.Connection,
) -> None:
    create_sermon(connection, FakeLive(), LINK, now=NOW)

    assert (
        list_sermons(connection, "trimmed"),
        len(list_sermons(connection, "created")["items"]),
    ) == (
        {"items": []},
        1,
    )


class UnreachableYouTube:
    def info(self, url: str) -> LiveInfo:
        raise YouTubeError("O YouTube recusou o pedido.")


def test_youtube_failure_is_a_youtube_error_and_creates_nothing(
    connection: sqlite3.Connection,
) -> None:
    with pytest.raises(WordcutError) as raised:
        create_sermon(connection, UnreachableYouTube(), LINK, now=NOW)

    assert (raised.value.code, raised.value.exit_code, list_sermons(connection)) == (
        "youtube_error",
        6,
        {"items": []},
    )


class RacedLive(FakeLive):
    """Another ``create`` of the same video finishes while this one waits for YouTube."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__()
        self.connection = connection
        self.winner: dict[str, Any] = {}

    def info(self, url: str) -> LiveInfo:
        self.winner = create_sermon(self.connection, FakeLive(), url, now=NOW)
        return super().info(url)


def test_create_that_loses_a_race_for_the_same_video_returns_the_winner(
    connection: sqlite3.Connection,
) -> None:
    live = RacedLive(connection)

    sermon = create_sermon(connection, live, LINK, now=NOW)

    assert sermon == {**live.winner, "created": False}


def test_shown_sermon_has_empty_borders_no_task_and_no_cuts(
    connection: sqlite3.Connection,
) -> None:
    created = create_sermon(connection, FakeLive(), LINK, now=NOW)

    assert show_sermon(connection, created["id"]) == {
        **listed(created),
        "live_start": None,
        "live_end": None,
        "last_task": None,
        "cuts": [],
    }


def test_showing_an_unknown_sermon_is_not_found(connection: sqlite3.Connection) -> None:
    with pytest.raises(WordcutError) as raised:
        show_sermon(connection, 999)

    assert (raised.value.code, raised.value.exit_code, raised.value.details) == (
        "not_found",
        3,
        {"sermon_id": 999},
    )
