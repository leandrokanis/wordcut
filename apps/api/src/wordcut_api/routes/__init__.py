"""The business routes of the API, one router per resource, each a thin layer over
``wordcut.service`` (ADR-0004).

``ROUTERS`` lists every one of them: the application includes each with the identity of who
is asking, so no business route is left without it (ADR-0021).
"""

from fastapi import APIRouter

from wordcut_api.routes import (
    cuts,
    members,
    presets,
    renders,
    sermons,
    settings,
    status,
    tasks,
)

ROUTERS: tuple[APIRouter, ...] = (
    sermons.router,
    tasks.router,
    status.router,
    cuts.router,
    renders.router,
    settings.router,
    presets.router,
    members.router,
)
