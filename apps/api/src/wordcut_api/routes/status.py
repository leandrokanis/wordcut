"""Machine status: who holds the processing lock and which tasks run (docs/api.md)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from wordcut.service.status import machine_status
from wordcut_api import deps

router = APIRouter(prefix="/api/status")


@router.get("")
def status() -> dict[str, Any]:
    return machine_status(deps.home())
