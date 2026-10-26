from dataclasses import replace

import pytest

from wordcut.errors import WordcutError
from wordcut.rendering.options import RenderOptions, merged


def test_the_options_default_to_those_of_the_export_dialog() -> None:
    assert RenderOptions() == RenderOptions(
        fillers="remove",
        stammers="remove",
        pauses="natural",
        smooth_joins=True,
        fade=True,
        normalize=True,
        resolution="1080x1920",
        quality="high",
    )


def test_a_given_option_beats_the_saved_one_and_a_saved_one_beats_the_default() -> None:
    options = merged({"pauses": "short", "fade": False}, {"pauses": "original"})

    assert options == replace(RenderOptions(), pauses="original", fade=False)


def test_saved_unknown_keys_are_ignored_and_saved_invalid_values_are_the_defaults() -> None:
    options = merged({"speed": 2, "quality": "max", "fade": "yes", "pauses": "short"}, {})

    assert options == replace(RenderOptions(), pauses="short")


def test_a_given_resolution_out_of_the_choices_is_an_invalid_argument_that_lists_them() -> None:
    with pytest.raises(WordcutError) as raised:
        merged(None, {"resolution": "640x480"})

    error = raised.value
    assert (error.code, error.details, "640x480" in error.message) == (
        "invalid_argument",
        {"argument": "resolution", "choices": ["1080x1920", "720x1280"]},
        False,
    )


def test_the_summary_has_the_nine_choices_with_the_caption_the_cut_shows() -> None:
    summary = replace(RenderOptions(), quality="small").summary(caption=False)

    assert summary == {
        "fillers": "remove",
        "stammers": "remove",
        "pauses": "natural",
        "smooth_joins": True,
        "fade": True,
        "normalize": True,
        "caption": False,
        "resolution": "1080x1920",
        "quality": "small",
    }
