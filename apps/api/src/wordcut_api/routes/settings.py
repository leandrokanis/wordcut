"""Settings of the installation: the models, the LLM key and the YouTube cookies; only an
administrator may see or change them (docs/api.md)."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import closing
from typing import Any

from fastapi import APIRouter, Depends

from wordcut import db
from wordcut.errors import WordcutError
from wordcut.service.settings import (
    show_settings,
    store_llm_key,
    store_youtube_cookies,
    update_settings,
)
from wordcut_api import deps
from wordcut_api.auth import require
from wordcut_api.bodies import Body, Changes

CONFIG_NOT_WRITABLE = (
    "A pasta de configuração não aceita gravação; grave o segredo pela CLI no host."
)

router = APIRouter(prefix="/api/settings", dependencies=[Depends(require("admin"))])


class ModelChanges(Changes):
    """The models to change (docs/cli.md §11.1)."""

    llm_model: str | None = None
    whisper_model: str | None = None


class Secret(Body):
    """A secret, which only ever comes in: the answer shows it masked or as present."""

    value: str


@router.get("")
def show() -> dict[str, Any]:
    with closing(db.connect(deps.home())) as connection:
        return show_settings(connection)


@router.patch("")
def change(body: ModelChanges) -> dict[str, Any]:
    with closing(db.connect(deps.home())) as connection:
        return update_settings(connection, **body.given())


@router.put("/llm-key")
def store_key(body: Secret) -> dict[str, Any]:
    return _stored(store_llm_key, body.value)


@router.put("/youtube-cookies")
def store_cookies(body: Secret) -> dict[str, Any]:
    return _stored(store_youtube_cookies, body.value)


def _stored(store: Callable[[str], None], value: str) -> dict[str, Any]:
    """The settings once ``store`` writes the secret; a refusal names ``value``, the field of
    the body, where the service names its own argument, and a folder that takes no writes
    answers without its path, which only the CLI on the host may show (ADR-0021)."""
    try:
        store(value)
    except WordcutError as error:
        if error.code == "config_not_writable":
            raise WordcutError(error.code, CONFIG_NOT_WRITABLE) from None
        if error.details is None or "argument" not in error.details:
            raise
        raise WordcutError(
            error.code, error.message, {**error.details, "argument": "value"}
        ) from None
    return show()
