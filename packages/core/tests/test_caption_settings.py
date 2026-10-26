from dataclasses import replace

import pytest

from wordcut.cuts.caption import DEFAULT_CAPTION, stored_caption, validated
from wordcut.errors import WordcutError
from wordcut.vertical.fonts import available_fonts


def test_default_caption_is_the_church_style() -> None:
    assert DEFAULT_CAPTION.as_dict() == {
        "enabled": True,
        "font": "Open Sans Bold",
        "size": 60,
        "color": "#FFD600",
        "position": "center",
        "offset": 50,
        "border": 3,
        "border_color": "#000000",
        "shadow": "soft",
    }


def test_a_change_applies_only_the_given_fields_over_the_current_style() -> None:
    current = replace(DEFAULT_CAPTION, size=72, shadow="strong")

    changed = validated(current, {"color": "#FFFFFF", "border": 5})

    assert changed == replace(current, color="#FFFFFF", border=5)


@pytest.mark.parametrize(
    ("field", "value", "low", "high"),
    [
        ("size", 23, 24, 160),
        ("size", 161, 24, 160),
        ("offset", 9, 10, 90),
        ("offset", 91, 10, 90),
        ("border", -1, 0, 12),
        ("border", 13, 0, 12),
    ],
)
def test_a_value_out_of_its_range_is_an_invalid_argument_naming_the_range(
    field: str, value: int, low: int, high: int
) -> None:
    with pytest.raises(WordcutError) as raised:
        validated(DEFAULT_CAPTION, {field: value})

    error = raised.value
    assert (error.code, error.details) == (
        "invalid_argument",
        {"argument": field, "min": low, "max": high},
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [("size", 24), ("size", 160), ("offset", 10), ("offset", 90), ("border", 0), ("border", 12)],
)
def test_a_value_at_the_edge_of_its_range_is_accepted(field: str, value: int) -> None:
    assert validated(DEFAULT_CAPTION, {field: value}).as_dict()[field] == value


@pytest.mark.parametrize("field", ["color", "border_color"])
def test_a_colour_is_kept_in_upper_case(field: str) -> None:
    assert validated(DEFAULT_CAPTION, {field: "#ffd6a0"}).as_dict()[field] == "#FFD6A0"


@pytest.mark.parametrize("field", ["color", "border_color"])
@pytest.mark.parametrize("value", ["#FFF", "FFFFFF", "#GGGGGG", "", "#FFFFFF0"])
def test_a_colour_out_of_the_rrggbb_form_is_an_invalid_argument(field: str, value: str) -> None:
    with pytest.raises(WordcutError) as raised:
        validated(DEFAULT_CAPTION, {field: value})

    assert (raised.value.code, raised.value.details) == ("invalid_argument", {"argument": field})


@pytest.mark.parametrize(("position", "offset"), [("top", 20), ("center", 50), ("bottom", 78)])
def test_choosing_a_position_moves_the_height_to_it(position: str, offset: int) -> None:
    current = replace(DEFAULT_CAPTION, position="center", offset=35)

    changed = validated(current, {"position": position})

    assert (changed.position, changed.offset) == (position, offset)


def test_an_explicit_height_wins_over_the_position_given_with_it() -> None:
    changed = validated(DEFAULT_CAPTION, {"position": "bottom", "offset": 70})

    assert (changed.position, changed.offset) == ("bottom", 70)


def test_a_height_alone_keeps_the_position() -> None:
    changed = validated(replace(DEFAULT_CAPTION, position="top", offset=20), {"offset": 30})

    assert (changed.position, changed.offset) == ("top", 30)


@pytest.mark.parametrize(
    ("field", "value", "choices"),
    [
        ("position", "middle", ["top", "center", "bottom"]),
        ("shadow", "hard", ["none", "soft", "strong"]),
    ],
)
def test_a_position_or_shadow_out_of_its_choices_is_an_invalid_argument_listing_them(
    field: str, value: str, choices: list[str]
) -> None:
    with pytest.raises(WordcutError) as raised:
        validated(DEFAULT_CAPTION, {field: value})

    assert (raised.value.code, raised.value.details) == (
        "invalid_argument",
        {"argument": field, "choices": choices},
    )


def test_the_font_catalogue_names_each_packaged_font_by_its_own_metadata() -> None:
    catalogue = available_fonts()

    assert {name: path.name for name, path in catalogue.items()} == {
        "Open Sans Bold": "OpenSans-Bold.ttf"
    }


def test_a_font_not_in_the_package_is_an_invalid_argument_listing_the_fonts() -> None:
    with pytest.raises(WordcutError) as raised:
        validated(DEFAULT_CAPTION, {"font": "Comic Sans MS"})

    assert (raised.value.code, raised.value.details) == (
        "invalid_argument",
        {"argument": "font", "choices": ["Open Sans Bold"]},
    )


def test_a_packaged_font_is_accepted() -> None:
    assert validated(DEFAULT_CAPTION, {"font": "Open Sans Bold"}).font == "Open Sans Bold"


def test_no_stored_style_means_the_default() -> None:
    assert stored_caption(None) == DEFAULT_CAPTION


def test_an_incomplete_or_old_stored_style_is_completed_by_the_default() -> None:
    stored = {"size": 72, "shadow": "none", "font_size": 90}

    assert stored_caption(stored) == replace(DEFAULT_CAPTION, size=72, shadow="none")
