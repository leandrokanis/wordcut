import pytest

from wordcut.timefmt import format_timestamp, parse_timestamp


@pytest.mark.parametrize(
    ("text", "seconds"),
    [("90", 90.0), ("01:30", 90.0), ("00:43:20.439", 2600.439), ("1:24:50.5", 5090.5)],
)
def test_parse_timestamp(text: str, seconds: float) -> None:
    assert parse_timestamp(text) == pytest.approx(seconds)


@pytest.mark.parametrize("text", ["", "1:2:3:4", "a:10", "10:"])
def test_parse_timestamp_rejects_garbage(text: str) -> None:
    with pytest.raises(ValueError):
        parse_timestamp(text)


def test_format_timestamp_round_trips() -> None:
    assert format_timestamp(5092.4) == "01:24:52.400"
    assert parse_timestamp(format_timestamp(2600.439)) == pytest.approx(2600.439)
