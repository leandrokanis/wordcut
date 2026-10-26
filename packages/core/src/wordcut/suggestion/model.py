"""The LLM of the cut suggestion, behind ``SuggestionModel`` (ADR-0010).

``OpenRouterModel`` calls OpenRouter's chat completions; tests hand the suggestion a double
of ``SuggestionModel`` instead, or an ``httpx.MockTransport`` to the real one.
"""

from __future__ import annotations

from typing import Any, Protocol

import httpx

from wordcut.errors import WordcutError

# OpenRouter's OpenAI-compatible endpoint: https://openrouter.ai/docs/api-reference/overview
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Answering a whole sermon takes the model a while; past this, the suggestion gives up.
TIMEOUT_SECONDS = 300.0


class SuggestionModel(Protocol):
    def complete(self, system: str, user: str) -> str:
        """The model's answer to the ``system`` and ``user`` messages."""


class OpenRouterModel:
    """``model`` on OpenRouter, called with ``key``; ``client`` defaults to a new one."""

    def __init__(self, model: str, key: str, client: httpx.Client | None = None) -> None:
        self._model = model
        self._key = key
        self._client = client or httpx.Client()

    def complete(self, system: str, user: str) -> str:
        """The model's answer; any failure to get one is ``WordcutError("llm_error")``.

        The error never carries the key, the messages nor what OpenRouter answered.
        """
        try:
            response = self._post(system, user)
        except httpx.TimeoutException:
            raise _llm_error(f"O OpenRouter não respondeu em {TIMEOUT_SECONDS:.0f} s.") from None
        except httpx.HTTPError:
            raise _llm_error("Não foi possível falar com o OpenRouter.") from None
        if response.is_error:
            raise _llm_error(
                f"O OpenRouter recusou o pedido (HTTP {response.status_code}).",
                {"status": response.status_code},
            )
        return _content(response)

    def _post(self, system: str, user: str) -> httpx.Response:
        return self._client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {self._key}"},
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=TIMEOUT_SECONDS,
        )


def _content(response: httpx.Response) -> str:
    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (ValueError, LookupError, TypeError):
        content = None
    if not isinstance(content, str):
        raise _llm_error("O OpenRouter respondeu sem a resposta do modelo.")
    return content


def _llm_error(message: str, details: dict[str, Any] | None = None) -> WordcutError:
    return WordcutError("llm_error", message, details)
