import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut.db import MIGRATIONS, connect, sermons
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.lock import ProcessingLock
from wordcut.service.sermons import create_sermon, list_sermons, show_sermon, trim_sermon
from wordcut.youtube import LiveInfo

LINK = "https://youtu.be/Ab3_x-9QzLk"
CREATED_AT = datetime(2026, 10, 26, 19, 40, tzinfo=timezone(timedelta(hours=-3)))
TRIMMED_AT = CREATED_AT + timedelta(minutes=5)
LIVE_ON_AIR = LiveInfo.from_metadata(
    {"title": "Culto ao vivo", "timestamp": 1792361083, "live_status": "is_live"}
)
TWO_HOUR_LIVE = LiveInfo(
    title="Culto de domingo",
    service_date=date(2026, 10, 18),
    duration=7200.0,
    live_status="was_live",
)


class FakeLive:
    """``LiveSource`` double that always answers the same live."""

    def __init__(self, info: LiveInfo = TWO_HOUR_LIVE) -> None:
        self.answer = info

    def info(self, url: str) -> LiveInfo:
        return self.answer


def home_of(connection: sqlite3.Connection) -> Home:
    """The data folder of the database ``connection`` is open on."""
    [(_, _, database)] = connection.execute("PRAGMA database_list").fetchall()
    return Home(Path(database).parent)


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(Home(tmp_path))) as opened:
        yield opened


def put_in_state(connection: sqlite3.Connection, sermon_id: int, status: str) -> None:
    """Stand in for the processing flow (item 5), which does not exist yet."""
    with connection:
        connection.execute("UPDATE sermons SET status = ? WHERE id = ?", (status, sermon_id))


@contextmanager
def being_processed(connection: sqlite3.Connection, sermon_id: int) -> Iterator[None]:
    """The sermon ``processing`` with the lock held for it, as while its task runs."""
    with ProcessingLock(home_of(connection)).acquire("process", f"sermon {sermon_id}"):
        put_in_state(connection, sermon_id, "processing")
        yield


def failure_of(connection: sqlite3.Connection, sermon_id: int, start: float, end: float) -> Any:
    """The error of a trim that must fail, and the sermon as shown after it."""
    with pytest.raises(WordcutError) as raised:
        trim_sermon(connection, sermon_id, start, end, now=TRIMMED_AT)
    return raised.value, show_sermon(connection, sermon_id, home=home_of(connection))


@pytest.fixture
def sermon(connection: sqlite3.Connection) -> dict[str, Any]:
    return create_sermon(connection, FakeLive(), LINK, now=CREATED_AT, home=home_of(connection))


def test_trimming_a_created_sermon_records_the_borders_and_makes_it_trimmed(
    connection: sqlite3.Connection, sermon: dict[str, Any]
) -> None:
    trim_sermon(connection, sermon["id"], 3730.0, 6510.0, now=TRIMMED_AT)

    shown = show_sermon(connection, sermon["id"], home=home_of(connection))
    assert (shown["status"], shown["live_start"], shown["live_end"]) == (
        "trimmed",
        3730.0,
        6510.0,
    )


def test_trimming_an_unknown_sermon_is_not_found(connection: sqlite3.Connection) -> None:
    with pytest.raises(WordcutError) as raised:
        trim_sermon(connection, 999, 3730.0, 6510.0, now=TRIMMED_AT)

    assert (raised.value.code, raised.value.exit_code, raised.value.details) == (
        "not_found",
        3,
        {"sermon_id": 999},
    )


def test_trimming_a_sermon_being_processed_is_busy_and_changes_nothing(
    connection: sqlite3.Connection, sermon: dict[str, Any]
) -> None:
    with being_processed(connection, sermon["id"]):
        before = show_sermon(connection, sermon["id"], home=home_of(connection))

        error, after = failure_of(connection, sermon["id"], 3730.0, 6510.0)

    assert (error.code, error.exit_code, after) == ("busy", 4, before)


@pytest.mark.parametrize(("start", "end"), [(3730.0, 3789.999), (4043.757, 4103.756)])
def test_range_shorter_than_a_minute_is_too_short_and_changes_nothing(
    connection: sqlite3.Connection, sermon: dict[str, Any], start: float, end: float
) -> None:
    before = show_sermon(connection, sermon["id"], home=home_of(connection))

    error, after = failure_of(connection, sermon["id"], start, end)

    assert (error.code, error.exit_code, after) == ("sermon_too_short", 5, before)


@pytest.mark.parametrize(("start", "end"), [(3730.0, 3790.0), (4043.757, 4103.757)])
def test_range_of_exactly_one_minute_is_accepted(
    connection: sqlite3.Connection, sermon: dict[str, Any], start: float, end: float
) -> None:
    trimmed = trim_sermon(connection, sermon["id"], start, end, now=TRIMMED_AT)

    assert (trimmed["status"], trimmed["live_start"], trimmed["live_end"]) == (
        "trimmed",
        start,
        end,
    )


@pytest.mark.parametrize(
    ("start", "end"),
    [(-0.001, 3730.0), (3730.0, 3730.0), (6510.0, 3730.0), (3730.0, 7200.001)],
)
def test_borders_outside_the_live_or_out_of_order_are_invalid_and_change_nothing(
    connection: sqlite3.Connection, sermon: dict[str, Any], start: float, end: float
) -> None:
    before = show_sermon(connection, sermon["id"], home=home_of(connection))

    error, after = failure_of(connection, sermon["id"], start, end)

    assert (error.code, error.exit_code, error.details, after) == (
        "invalid_argument",
        2,
        {"start": start, "end": end, "live_duration": 7200.0},
        before,
    )


def test_borders_may_touch_both_ends_of_the_live(
    connection: sqlite3.Connection, sermon: dict[str, Any]
) -> None:
    trimmed = trim_sermon(connection, sermon["id"], 0.0, 7200.0, now=TRIMMED_AT)

    assert (trimmed["status"], trimmed["live_start"], trimmed["live_end"]) == (
        "trimmed",
        0.0,
        7200.0,
    )


@pytest.mark.parametrize(
    ("start", "end", "kept"),
    [(0.0004, 60.0004, (0.0, 60.0)), (7140.0, 7200.0004, (7140.0, 7200.0))],
)
def test_borders_are_kept_to_the_millisecond_before_they_are_checked(
    connection: sqlite3.Connection,
    sermon: dict[str, Any],
    start: float,
    end: float,
    kept: tuple[float, float],
) -> None:
    trimmed = trim_sermon(connection, sermon["id"], start, end, now=TRIMMED_AT)

    assert (trimmed["live_start"], trimmed["live_end"]) == kept


@pytest.mark.parametrize("status", ["trimmed", "failed"])
def test_trimming_again_or_after_a_failure_makes_the_sermon_trimmed_without_reprocess_warning(
    connection: sqlite3.Connection, sermon: dict[str, Any], status: str
) -> None:
    put_in_state(connection, sermon["id"], status)

    trimmed = trim_sermon(connection, sermon["id"], 3730.0, 6510.0, now=TRIMMED_AT)

    assert (trimmed["status"], trimmed["needs_reprocess"]) == ("trimmed", False)


def test_trimming_a_processed_sermon_keeps_it_processed_and_asks_for_a_reprocess(
    connection: sqlite3.Connection, sermon: dict[str, Any]
) -> None:
    put_in_state(connection, sermon["id"], "processed")

    trimmed = trim_sermon(connection, sermon["id"], 3730.0, 6510.0, now=TRIMMED_AT)

    shown = show_sermon(connection, sermon["id"], home=home_of(connection))
    assert (
        shown["status"],
        shown["live_start"],
        shown["live_end"],
        trimmed["needs_reprocess"],
    ) == (
        "processed",
        3730.0,
        6510.0,
        True,
    )


def test_trimmed_sermon_is_answered_as_shown_with_the_duration_between_its_borders(
    connection: sqlite3.Connection, sermon: dict[str, Any]
) -> None:
    trimmed = trim_sermon(connection, sermon["id"], 3730.0, 6510.0, now=TRIMMED_AT)

    shown = show_sermon(connection, sermon["id"], home=home_of(connection))
    assert (trimmed, shown["duration"]) == ({**shown, "needs_reprocess": False}, 2780.0)


def test_listed_sermon_shows_the_duration_between_its_borders(
    connection: sqlite3.Connection, sermon: dict[str, Any]
) -> None:
    trim_sermon(connection, sermon["id"], 3730.0, 6510.0, now=TRIMMED_AT)

    assert [
        item["duration"] for item in list_sermons(connection, home=home_of(connection))["items"]
    ] == [2780.0]


def test_live_of_unknown_duration_accepts_any_ordered_range_of_at_least_a_minute(
    connection: sqlite3.Connection,
) -> None:
    on_air = create_sermon(
        connection, FakeLive(LIVE_ON_AIR), LINK, now=CREATED_AT, home=home_of(connection)
    )

    trimmed = trim_sermon(connection, on_air["id"], 3730.0, 99999.0, now=TRIMMED_AT)

    assert (trimmed["status"], trimmed["live_end"]) == ("trimmed", 99999.0)


def test_live_of_unknown_duration_still_refuses_borders_out_of_order(
    connection: sqlite3.Connection,
) -> None:
    on_air = create_sermon(
        connection, FakeLive(LIVE_ON_AIR), LINK, now=CREATED_AT, home=home_of(connection)
    )

    error, _ = failure_of(connection, on_air["id"], 6510.0, 3730.0)

    assert (error.code, error.details) == (
        "invalid_argument",
        {"start": 6510.0, "end": 3730.0, "live_duration": None},
    )


def test_sermon_being_processed_is_busy_before_its_borders_are_checked(
    connection: sqlite3.Connection, sermon: dict[str, Any]
) -> None:
    put_in_state(connection, sermon["id"], "processing")

    error, _ = failure_of(connection, sermon["id"], 6510.0, 3730.0)

    assert error.code == "busy"


def test_sermon_created_with_borders_is_already_trimmed(
    connection: sqlite3.Connection,
) -> None:
    created = create_sermon(
        connection,
        FakeLive(),
        LINK,
        now=CREATED_AT,
        start=3730.0,
        end=6510.0,
        home=home_of(connection),
    )

    shown = show_sermon(connection, created["id"], home=home_of(connection))
    assert (created["created"], shown["status"], shown["live_start"], shown["live_end"]) == (
        True,
        "trimmed",
        3730.0,
        6510.0,
    )


def test_answer_of_a_create_with_borders_has_the_trimmed_status(
    connection: sqlite3.Connection,
) -> None:
    created = create_sermon(
        connection,
        FakeLive(),
        LINK,
        now=CREATED_AT,
        start=3730.0,
        end=6510.0,
        home=home_of(connection),
    )

    assert created["status"] == "trimmed"


@pytest.mark.parametrize(
    ("start", "end", "code"),
    [
        (3730.0, 3789.0, "sermon_too_short"),
        (6510.0, 3730.0, "invalid_argument"),
        (3730.0, 7200.5, "invalid_argument"),
    ],
)
def test_create_with_refused_borders_fails_and_creates_no_sermon(
    connection: sqlite3.Connection, start: float, end: float, code: str
) -> None:
    with pytest.raises(WordcutError) as raised:
        create_sermon(
            connection,
            FakeLive(),
            LINK,
            now=CREATED_AT,
            start=start,
            end=end,
            home=home_of(connection),
        )

    assert (raised.value.code, list_sermons(connection, home=home_of(connection))) == (
        code,
        {"items": []},
    )


def test_create_with_borders_of_a_known_video_trims_the_existing_sermon(
    connection: sqlite3.Connection, sermon: dict[str, Any]
) -> None:
    again = create_sermon(
        connection,
        FakeLive(),
        LINK,
        now=TRIMMED_AT,
        start=3730.0,
        end=6510.0,
        home=home_of(connection),
    )

    shown = show_sermon(connection, sermon["id"], home=home_of(connection))
    assert (again["id"], again["created"], again["status"], shown["live_start"]) == (
        sermon["id"],
        False,
        "trimmed",
        3730.0,
    )


def test_create_with_borders_of_a_processed_sermon_keeps_it_and_asks_for_a_reprocess(
    connection: sqlite3.Connection, sermon: dict[str, Any]
) -> None:
    put_in_state(connection, sermon["id"], "processed")

    again = create_sermon(
        connection,
        FakeLive(),
        LINK,
        now=TRIMMED_AT,
        start=3730.0,
        end=6510.0,
        home=home_of(connection),
    )

    assert (again["created"], again["status"], again["needs_reprocess"]) == (
        False,
        "processed",
        True,
    )


@pytest.mark.parametrize(
    ("start", "end", "missing"), [(3730.0, None, "end"), (None, 6510.0, "start")]
)
def test_create_with_a_single_border_is_refused_before_anything_is_created(
    connection: sqlite3.Connection, start: float | None, end: float | None, missing: str
) -> None:
    with pytest.raises(WordcutError) as raised:
        create_sermon(
            connection,
            FakeLive(),
            LINK,
            now=CREATED_AT,
            start=start,
            end=end,
            home=home_of(connection),
        )

    assert (
        raised.value.code,
        raised.value.details,
        list_sermons(connection, home=home_of(connection)),
    ) == (
        "invalid_argument",
        {"argument": missing},
        {"items": []},
    )


PROCESSED_AT = TRIMMED_AT + timedelta(minutes=30)


def processed_between(
    connection: sqlite3.Connection, sermon_id: int, start: float, end: float
) -> None:
    """Stand in for a processing that succeeded with the borders ``start`` and ``end``."""
    trim_sermon(connection, sermon_id, start, end, now=TRIMMED_AT)
    with connection:
        sermons.record_processed(
            connection, sermon_id, start + 0.4, end - 0.6, "sermon.mp4", PROCESSED_AT
        )


def borders_changed(connection: sqlite3.Connection, sermon_id: int) -> bool:
    changed: bool = show_sermon(connection, sermon_id, home=home_of(connection))["borders_changed"]
    return changed


def test_processed_sermon_whose_borders_changed_tells_so(
    connection: sqlite3.Connection, sermon: dict[str, Any]
) -> None:
    processed_between(connection, sermon["id"], 3730.0, 6510.0)
    trim_sermon(connection, sermon["id"], 3735.5, 6510.0, now=PROCESSED_AT)

    assert borders_changed(connection, sermon["id"]) is True


def test_processed_sermon_with_its_processed_borders_shows_no_change(
    connection: sqlite3.Connection, sermon: dict[str, Any]
) -> None:
    processed_between(connection, sermon["id"], 3730.0, 6510.0)

    assert borders_changed(connection, sermon["id"]) is False


def test_borders_put_back_to_the_processed_ones_show_no_change(
    connection: sqlite3.Connection, sermon: dict[str, Any]
) -> None:
    processed_between(connection, sermon["id"], 3730.0, 6510.0)
    trim_sermon(connection, sermon["id"], 3735.5, 6400.0, now=PROCESSED_AT)

    trim_sermon(connection, sermon["id"], 3730.0, 6510.0, now=PROCESSED_AT)

    assert borders_changed(connection, sermon["id"]) is False


@pytest.mark.parametrize("status", ["created", "trimmed", "failed"])
def test_sermon_not_processed_shows_no_change_whatever_its_borders(
    connection: sqlite3.Connection, sermon: dict[str, Any], status: str
) -> None:
    processed_between(connection, sermon["id"], 3730.0, 6510.0)
    trim_sermon(connection, sermon["id"], 3735.5, 6400.0, now=PROCESSED_AT)
    put_in_state(connection, sermon["id"], status)

    assert borders_changed(connection, sermon["id"]) is False


def test_listed_sermon_tells_whether_its_borders_changed(
    connection: sqlite3.Connection, sermon: dict[str, Any]
) -> None:
    processed_between(connection, sermon["id"], 3730.0, 6510.0)
    trim_sermon(connection, sermon["id"], 3735.5, 6510.0, now=PROCESSED_AT)

    assert [
        item["borders_changed"]
        for item in list_sermons(connection, home=home_of(connection))["items"]
    ] == [True]


def test_trimming_a_processed_sermon_answers_whether_its_borders_changed(
    connection: sqlite3.Connection, sermon: dict[str, Any]
) -> None:
    processed_between(connection, sermon["id"], 3730.0, 6510.0)

    answers = [
        trim_sermon(connection, sermon["id"], start, 6510.0, now=PROCESSED_AT)["borders_changed"]
        for start in (3735.5, 3730.0)
    ]

    assert answers == [True, False]


def test_sermon_processed_before_the_processed_borders_were_kept_shows_no_change(
    tmp_path: Path,
) -> None:
    home = Home(tmp_path / "home")
    up_to_10 = tmp_path / "migrations"
    up_to_10.mkdir()
    for packaged in MIGRATIONS.glob("*.sql"):
        if int(packaged.name.split("_")[0]) <= 10:
            (up_to_10 / packaged.name).write_text(packaged.read_text(encoding="utf-8"))
    with closing(connect(home, up_to_10)) as old, old:
        sermon_id = old.execute(
            "INSERT INTO sermons (youtube_id, url, title, service_date, live_finished, status,"
            " live_start, live_end, created_at, updated_at) VALUES ('Ab3_x-9QzLk', ?, 'Culto',"
            " '2026-10-18', 1, 'processed', 3730.0, 6510.0, '2026-10-26T19:40:00-03:00',"
            " '2026-10-26T19:40:00-03:00')",
            (LINK,),
        ).lastrowid
    assert sermon_id is not None

    with closing(connect(home)) as migrated:
        assert borders_changed(migrated, sermon_id) is False
