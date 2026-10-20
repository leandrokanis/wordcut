from datetime import date
from pathlib import Path

from cortes_pregacao.sermon_folder import SermonFolder, folder_name


def test_folder_name_with_reference_replaces_colon() -> None:
    name = folder_name(date(2026, 10, 4), "O azeite da viúva", "2 Reis 4:1-7")

    assert name == "2026-10-04 - O azeite da viúva - 2 Reis 4.1-7"


def test_folder_name_strips_path_unsafe_characters() -> None:
    assert folder_name(date(2026, 1, 2), 'Quem é "Deus"?/') == "2026-01-02 - Quem é Deus"


def test_sermon_video_is_named_after_folder(tmp_path: Path) -> None:
    folder = SermonFolder(tmp_path / "2026-10-18 - Título").create()

    assert folder.sermon_video.name == "2026-10-18 - Título.mp4"
    assert {p.name for p in folder.path.iterdir()} == {"roteiros", "cortes", "trabalho"}
