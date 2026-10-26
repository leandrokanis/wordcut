"""``WordcutError`` as an HTTP response: a status and the error object of the CLI.

The body is ``{"error": {"code", "message", "details"?}}``, the object of docs/cli.md §5.2
(ADR-0004), so the web and agents decide by ``code`` as they do with the CLI.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from wordcut.errors import WordcutError

STATUS_BY_EXIT_CODE = {1: 500, 2: 400, 3: 404, 4: 409, 5: 409, 6: 502}
# Exit 1 is any failure for the CLI; the API tells who is asking apart from a fault.
STATUS_BY_CODE = {"unauthenticated": 401, "forbidden": 403}
# The text of an unexpected exception may carry a token or an e-mail (docs/constitution.md §VI).
UNEXPECTED = WordcutError("internal_error", "Erro interno na API.")


def http_status(error: WordcutError) -> int:
    return STATUS_BY_CODE.get(error.code, STATUS_BY_EXIT_CODE[error.exit_code])


def install(app: FastAPI) -> None:
    """Answer every ``WordcutError`` a route raises with its status and error object.

    Any other exception answers ``internal_error`` without its text.
    """

    @app.exception_handler(WordcutError)
    def wordcut_error(request: Request, error: WordcutError) -> JSONResponse:
        return response(error)

    @app.exception_handler(Exception)
    def unexpected(request: Request, error: Exception) -> JSONResponse:
        return response(UNEXPECTED)


def response(error: WordcutError) -> JSONResponse:
    return JSONResponse({"error": error.to_dict()}, status_code=http_status(error))
