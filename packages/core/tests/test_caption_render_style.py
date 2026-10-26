from dataclasses import replace

import numpy as np
import pytest

from wordcut.cuts.caption import DEFAULT_CAPTION, CaptionSettings, to_style, validated
from wordcut.vertical.captions import Caption, CaptionImage, CaptionRenderer, CaptionStyle
from wordcut.vertical.fonts import available_fonts

FRAME_WIDTH, FRAME_HEIGHT = 1080, 1920
GREEN, RED = (0, 255, 0), (255, 0, 0)
# Text and border in colours no shadow can produce, so each pixel says what drew it.
VIVID = replace(DEFAULT_CAPTION, color="#00FF00", border_color="#FF0000")
SHORT = Caption(0.0, 1.0, ("Graça e paz.",))


def drawn(settings: CaptionSettings, caption: Caption = SHORT) -> CaptionImage:
    return CaptionRenderer(FRAME_WIDTH, to_style(settings, FRAME_HEIGHT)).render(caption)


def opaque_pixels(image: CaptionImage, rgb: tuple[int, int, int]) -> int:
    """How many fully opaque pixels of the image are exactly ``rgb``."""
    exact = (image.bgr == np.array(rgb[::-1], dtype=np.float32)).all(axis=-1)
    return int((exact & (image.alpha[..., 0] == 1.0)).sum())


def test_the_drawing_style_carries_every_chosen_field() -> None:
    settings = replace(
        DEFAULT_CAPTION,
        size=72,
        color="#00FF00",
        position="bottom",
        offset=78,
        border=5,
        border_color="#FF0000",
        shadow="strong",
    )

    style = to_style(settings, FRAME_HEIGHT)

    assert style == CaptionStyle(
        size=72,
        color=(0, 255, 0),
        outline=5,
        outline_color=(255, 0, 0),
        shadow_offset=5,
        shadow_alpha=220,
        centre_y=1498,
        frame_height=FRAME_HEIGHT,
        font=available_fonts()["Open Sans Bold"],
    )


def test_the_border_is_drawn_in_its_colour_around_text_in_its_colour() -> None:
    image = drawn(VIVID)

    assert (opaque_pixels(image, GREEN) > 0, opaque_pixels(image, RED) > 0) == (True, True)


def test_without_a_border_no_pixel_has_the_border_colour() -> None:
    assert opaque_pixels(drawn(replace(VIVID, border=0)), RED) == 0


def shadow_alpha(image: CaptionImage) -> float:
    """The strongest alpha among pure black pixels: only the shadow draws black here."""
    black = (image.bgr == 0).all(axis=-1)
    return float(image.alpha[..., 0][black].max(initial=0.0))


@pytest.mark.parametrize(("shadow", "alpha"), [("none", 0), ("soft", 140), ("strong", 220)])
def test_each_shadow_level_draws_black_at_its_own_strength(shadow: str, alpha: int) -> None:
    image = drawn(replace(VIVID, shadow=shadow))

    # The shadow peeks out of the border only at anti-aliased edges, a few levels below.
    assert shadow_alpha(image) == pytest.approx(alpha / 255, abs=5 / 255)


def middle_row(image: CaptionImage) -> float:
    return image.top + image.bgr.shape[0] / 2


@pytest.mark.parametrize(("position", "row"), [("top", 384), ("center", 960), ("bottom", 1498)])
def test_the_caption_is_centred_at_the_height_of_its_position(position: str, row: int) -> None:
    settings = validated(VIVID, {"position": position})

    assert abs(middle_row(drawn(settings)) - row) <= 1


TALL = Caption(0.0, 1.0, ("Graça e paz", "a vocês"))


@pytest.mark.parametrize("offset", [10, 90])
def test_a_large_caption_at_either_end_of_the_frame_stays_inside_it(offset: int) -> None:
    image = drawn(replace(VIVID, size=160, offset=offset), TALL)

    assert (image.top >= 0, image.top + image.bgr.shape[0] <= FRAME_HEIGHT) == (True, True)


def test_a_larger_size_draws_a_taller_caption() -> None:
    small, large = drawn(replace(VIVID, size=40)), drawn(replace(VIVID, size=120))

    assert large.bgr.shape[0] > small.bgr.shape[0]


def test_the_default_caption_draws_exactly_like_the_legacy_default_style() -> None:
    legacy = CaptionRenderer(FRAME_WIDTH).render(SHORT)

    image = drawn(DEFAULT_CAPTION)

    assert (image.top, image.bgr.tobytes(), image.alpha.tobytes()) == (
        legacy.top,
        legacy.bgr.tobytes(),
        legacy.alpha.tobytes(),
    )


def test_on_a_720_by_1280_frame_the_style_shrinks_by_two_thirds() -> None:
    settings = replace(DEFAULT_CAPTION, size=72, border=6, shadow="strong", offset=50)

    style = to_style(settings, 1280)

    assert (
        style.size,
        style.outline,
        style.shadow_offset,
        style.max_width,
        style.centre_y,
        style.frame_height,
    ) == (48, 4, 3, 640, 640, 1280)
