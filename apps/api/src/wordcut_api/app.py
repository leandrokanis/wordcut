"""ASGI application factory: ``uvicorn wordcut_api.app:create_app --factory``."""

from __future__ import annotations

from fastapi import Depends, FastAPI

from wordcut_api import errors
from wordcut_api.auth import CurrentMember, DevIdentification, current_member, identification
from wordcut_api.identity import KeySource
from wordcut_api.routes import ROUTERS
from wordcut_api.settings import ApiSettings


def create_app(settings: ApiSettings | None = None, keys: KeySource | None = None) -> FastAPI:
    identifies = identification(settings or ApiSettings.from_environment(), keys)
    # ADR-0020: the schema and its page only in development, never behind Access.
    in_development = isinstance(identifies, DevIdentification)
    app = FastAPI(
        title="Wordcut",
        docs_url="/api/docs" if in_development else None,
        openapi_url="/api/openapi.json" if in_development else None,
        redoc_url=None,
    )
    errors.install(app)
    app.state.identification = identifies

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/me")
    def me(member: CurrentMember) -> dict[str, str]:
        return {"email": member.email, "role": member.role}

    # ADR-0021: the identity is required here, in one place, for every business router.
    for router in ROUTERS:
        app.include_router(router, dependencies=[Depends(current_member)])
    return app
