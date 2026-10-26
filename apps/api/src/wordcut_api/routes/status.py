"""Machine status: who holds the processing lock and which tasks run (docs/api.md)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from wordcut.service.status import machine_status
from wordcut_api import deps
from wordcut_api.auth import current_member

router = APIRouter(prefix="/api/status", dependencies=[Depends(current_member)])


@router.get("")
def status() -> dict[str, Any]:
    return machine_status(deps.home())
