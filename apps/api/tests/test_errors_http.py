from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from wordcut.errors import EXIT_CODES, WordcutError
from wordcut_api.app import create_app

# The HTTP status of each code (plan, Decisões técnicas; L5): rules (exit 5) are 409 and an
# outside failure (exit 6) is 502.
STATUS_BY_CODE = {
    "internal_error": 500,
    "interrupted": 500,
    "processing_error": 500,
    "unauthenticated": 401,
    "forbidden": 403,
    "invalid_argument": 400,
    "not_found": 404,
    "busy": 409,
}
STATUS_BY_EXIT_CODE = {5: 409, 6: 502}


def expected_status(code: str) -> int:
    exit_code = EXIT_CODES[code]
    if exit_code in STATUS_BY_EXIT_CODE:
        return STATUS_BY_EXIT_CODE[exit_code]
    return STATUS_BY_CODE[code]


def app_raising(error: Exception) -> FastAPI:
    app = create_app()

    @app.get("/api/test-error")
    def fail() -> None:
        raise error

    return app


def get(app: FastAPI) -> Any:
    return TestClient(app, raise_server_exceptions=False).get("/api/test-error")


@pytest.mark.parametrize("code", EXIT_CODES)
def test_every_error_code_answers_with_its_status_and_the_error_object_of_the_cli(
    code: str,
) -> None:
    error = WordcutError(code, "Mensagem de teste.", {"argument": "email"})

    response = get(app_raising(error))

    assert (response.status_code, response.json()) == (
        expected_status(code),
        {"error": error.to_dict()},
    )


def test_an_error_without_details_answers_without_details() -> None:
    response = get(app_raising(WordcutError("not_found", "Pregação não encontrada.")))

    assert response.json() == {
        "error": {"code": "not_found", "message": "Pregação não encontrada."}
    }


def test_an_unexpected_failure_answers_internal_error_without_its_text() -> None:
    secret = "token-ou-email-assistente@exemplo.org"

    response = get(app_raising(RuntimeError(secret)))

    assert (response.status_code, response.json(), secret in response.text) == (
        500,
        {"error": {"code": "internal_error", "message": "Erro interno na API."}},
        False,
    )
