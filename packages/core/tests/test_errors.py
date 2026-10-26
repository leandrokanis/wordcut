import pytest

from wordcut.errors import WordcutError

EXIT_CODE_BY_ERROR_CODE = {
    "internal_error": 1,
    "invalid_argument": 2,
    "not_found": 3,
    "busy": 4,
    "live_not_finished": 5,
    "sermon_not_trimmed": 5,
    "sermon_too_short": 5,
    "sermon_not_processed": 5,
    "would_discard_edits": 5,
    "spelling_too_different": 5,
    "default_preset": 5,
    "last_admin": 5,
    "youtube_error": 6,
    "llm_error": 6,
    "network_error": 6,
    "transcription_error": 6,
    "interrupted": 1,
    "processing_error": 1,
}


@pytest.mark.parametrize(("code", "exit_code"), EXIT_CODE_BY_ERROR_CODE.items())
def test_every_documented_error_code_maps_to_its_exit_code(code: str, exit_code: int) -> None:
    assert WordcutError(code, "mensagem").exit_code == exit_code


def test_an_unlisted_code_is_rejected_so_every_error_has_an_exit_code() -> None:
    with pytest.raises(ValueError, match="sermon_on_fire"):
        WordcutError("sermon_on_fire", "mensagem")
