"""The base of the request bodies: what a body may hold and how a change is read.

A body is strict (ADR-0021): a field it does not declare is refused, so a misspelt field
never passes as absent, and a value of the wrong type is refused instead of reaching the
service.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class Body(BaseModel):
    """A request body that refuses any field it does not declare."""

    model_config = ConfigDict(extra="forbid")


class Changes(Body):
    """The fields to change, each optional; a field given must carry a value, never null."""

    @field_validator("*")
    @classmethod
    def _given_with_a_value(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("a field given must carry a value")
        return value

    def given(self) -> dict[str, Any]:
        """The fields the request gave, by name."""
        return self.model_dump(exclude_unset=True)
