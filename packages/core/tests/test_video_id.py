import pytest

from wordcut.errors import WordcutError
from wordcut.youtube import video_id

VIDEO = "Ab3_x-9QzLk"


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={VIDEO}",
        f"https://www.youtube.com/watch?v={VIDEO}&t=120s",
        f"https://youtube.com/watch?list=PL123&v={VIDEO}",
        f"http://m.youtube.com/watch?v={VIDEO}&list=PL123",
        f"https://youtu.be/{VIDEO}",
        f"https://youtu.be/{VIDEO}?si=abc123",
        f"https://www.youtube.com/live/{VIDEO}?feature=share",
        f"https://youtube.com/live/{VIDEO}",
        f"https://m.youtube.com/shorts/{VIDEO}",
        f"http://www.youtube.com/shorts/{VIDEO}",
    ],
)
def test_every_link_format_of_the_same_video_gives_its_id(url: str) -> None:
    assert video_id(url) == VIDEO


@pytest.mark.parametrize(
    "url",
    [
        f"https://vimeo.com/watch?v={VIDEO}",
        f"https://youtube.com.golpe.example/watch?v={VIDEO}",
        f"https://notyoutube.com/watch?v={VIDEO}",
        f"https://youtu.be.example/{VIDEO}",
        "https://www.youtube.com/",
        "https://www.youtube.com/watch?v=",
        "https://www.youtube.com/watch?v=curto",
        f"https://www.youtube.com/watch?v={VIDEO}extra",
        "https://youtu.be/",
        "https://www.youtube.com/live/",
        f"https://www.youtube.com/channel/{VIDEO}",
        f"ftp://youtube.com/watch?v={VIDEO}",
        "não é um link",
        "",
    ],
)
def test_link_that_does_not_name_a_youtube_video_is_an_invalid_argument(url: str) -> None:
    with pytest.raises(WordcutError) as raised:
        video_id(url)

    assert (raised.value.code, raised.value.exit_code, raised.value.details) == (
        "invalid_argument",
        2,
        {"argument": "link"},
    )
