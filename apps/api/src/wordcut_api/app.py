"""ASGI application factory: ``uvicorn wordcut_api.app:create_app --factory``."""

from __future__ import annotations

from fastapi import FastAPI

from wordcut_api import errors
from wordcut_api.auth import CurrentMember, identification
from wordcut_api.identity import KeySource
from wordcut_api.settings import ApiSettings


def create_app(settings: ApiSettings | None = None, keys: KeySource | None = None) -> FastAPI:
    app = FastAPI(title="Wordcut")
    errors.install(app)
    app.state.identification = identification(settings or ApiSettings.from_environment(), keys)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/me")
    def me(member: CurrentMember) -> dict[str, str]:
        return {"email": member.email, "role": member.role}

    return app
