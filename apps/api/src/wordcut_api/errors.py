"""``WordcutError`` as an HTTP response: a status and the error object of the CLI.

The body is ``{"error": {"code", "message", "details"?}}``, the object of docs/cli.md §5.2
(ADR-0004), so the web and agents decide by ``code`` as they do with the CLI.
"""

from __future__ import annotations

from typing import Any, Literal, get_args, get_origin

from fastapi import FastAPI, Request, Response
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException
from starlette.status import HTTP_404_NOT_FOUND

from wordcut.errors import WordcutError

STATUS_BY_EXIT_CODE = {1: 500, 2: 400, 3: 404, 4: 409, 5: 409, 6: 502}
# Exit 1 is any failure for the CLI; the API tells who is asking apart from a fault.
STATUS_BY_CODE = {"unauthenticated": 401, "forbidden": 403}
# The text of an unexpected exception may carry a token or an e-mail (docs/constitution.md §VI).
UNEXPECTED = WordcutError("internal_error", "Erro interno na API.")
NO_ROUTE = WordcutError("not_found", "Rota não encontrada.")


def http_status(error: WordcutError) -> int:
    return STATUS_BY_CODE.get(error.code, STATUS_BY_EXIT_CODE[error.exit_code])


def install(app: FastAPI) -> None:
    """Answer every ``WordcutError`` a route raises with its status and error object.

    A request the route cannot read answers ``invalid_argument`` (400) naming the argument,
    never the value sent (ADR-0015, ADR-0020), and a path without a route answers
    ``not_found``. Any other exception answers ``internal_error`` without its text.
    """

    @app.exception_handler(WordcutError)
    def wordcut_error(request: Request, error: WordcutError) -> JSONResponse:
        return response(error)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException) -> Response:
        if error.status_code == HTTP_404_NOT_FOUND:
            return response(NO_ROUTE)
        return await http_exception_handler(request, error)

    @app.exception_handler(RequestValidationError)
    def invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
        return response(invalid_argument(request, error))

    @app.exception_handler(Exception)
    def unexpected(request: Request, error: Exception) -> JSONResponse:
        return response(UNEXPECTED)


def response(error: WordcutError) -> JSONResponse:
    return JSONResponse({"error": error.to_dict()}, status_code=http_status(error))


def invalid_argument(request: Request, error: RequestValidationError) -> WordcutError:
    """The first problem of the request as ``invalid_argument``, worded as the CLI words it.

    Pydantic's message and ``input`` repeat the value sent, which may be a secret; only the
    name of the argument and its choices come out.
    """
    problem = error.errors()[0]
    location, *path = problem["loc"]
    argument = next((part for part in reversed(path) if isinstance(part, str)), location)
    if problem["type"] == "missing":
        return WordcutError(
            "invalid_argument",
            f"Argumento obrigatório ausente: {argument}.",
            {"argument": argument},
        )
    choices = _choices(request, location, argument)
    if choices is None:
        return WordcutError(
            "invalid_argument", f"Valor inválido para {argument}.", {"argument": argument}
        )
    return WordcutError(
        "invalid_argument",
        f"Valor inválido para {argument}; use um de: {', '.join(choices)}.",
        {"argument": argument, "choices": choices},
    )


def _choices(request: Request, location: str, argument: str) -> list[str] | None:
    """The values of the ``Literal`` the route declares for the parameter, if it does."""
    route = request.scope.get("route")
    if not isinstance(route, APIRoute):
        return None
    declared = {"query": route.dependant.query_params, "path": route.dependant.path_params}
    for parameter in declared.get(location, []):
        if parameter.alias == argument:
            return _literal_values(parameter.field_info.annotation)
    return None


def _literal_values(annotation: Any) -> list[str] | None:
    if get_origin(annotation) is Literal:
        return [str(value) for value in get_args(annotation)]
    # An optional parameter is a union with None: look inside it.
    for member in get_args(annotation):
        values = _literal_values(member)
        if values is not None:
            return values
    return None
