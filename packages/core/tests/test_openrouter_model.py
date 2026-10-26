import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from wordcut.errors import WordcutError
from wordcut.suggestion.model import (
    OPENROUTER_URL,
    TIMEOUT_SECONDS,
    OpenRouterModel,
    SuggestionModel,
)

# Fictitious: no test ever reaches OpenRouter.
SENTINEL_KEY = "sk-or-v1-sentinela-ficticia-7f3a"
MODEL = "provedor/modelo-de-teste"
SYSTEM = "Prompt do preset com os critérios."
USER = "1: Irmãos, graça.\n2: Cristo vive."
ANSWER = '{"cuts": []}'

Handler = Callable[[httpx.Request], httpx.Response]


def model_answering(handler: Handler) -> OpenRouterModel:
    return OpenRouterModel(
        MODEL, SENTINEL_KEY, httpx.Client(transport=httpx.MockTransport(handler))
    )


def envelope(content: Any) -> dict[str, Any]:
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


def test_completing_posts_the_messages_to_openrouter_with_the_key_and_returns_the_content() -> None:
    sent: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json=envelope(ANSWER))

    model: SuggestionModel = model_answering(answer)

    content = model.complete(SYSTEM, USER)

    [request] = sent
    assert (
        content,
        request.method,
        str(request.url),
        request.headers["Authorization"],
        json.loads(request.content),
        request.extensions["timeout"]["read"],
    ) == (
        ANSWER,
        "POST",
        OPENROUTER_URL,
        f"Bearer {SENTINEL_KEY}",
        {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": USER},
            ],
            "response_format": {"type": "json_object"},
        },
        TIMEOUT_SECONDS,
    )


ECHOING_BODY = {"error": {"message": f"Chave {SENTINEL_KEY} recusada para: {SYSTEM} {USER}"}}


def status(code: int) -> Handler:
    return lambda request: httpx.Response(code, json=ECHOING_BODY)


def raising(error: type[httpx.TransportError]) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error(f"falhou com {SENTINEL_KEY}", request=request)

    return handler


def answering(body: Any) -> Handler:
    return lambda request: httpx.Response(200, json=body)


@pytest.mark.parametrize(
    "handler",
    [
        status(401),
        status(429),
        status(500),
        raising(httpx.ReadTimeout),
        raising(httpx.ConnectError),
        lambda request: httpx.Response(200, text=f"<html>{SENTINEL_KEY}</html>"),
        answering({"error": ECHOING_BODY}),
        answering({"choices": []}),
        answering(envelope(None)),
    ],
    ids=[
        "401",
        "429",
        "500",
        "timeout",
        "connection refused",
        "200 not json",
        "200 without choices",
        "200 with empty choices",
        "200 with null content",
    ],
)
def test_any_failure_to_get_an_answer_is_an_llm_error_without_key_messages_or_body(
    handler: Handler, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("DEBUG")

    with pytest.raises(WordcutError) as raised:
        model_answering(handler).complete(SYSTEM, USER)

    reported = " ".join(
        [str(raised.value), json.dumps(raised.value.to_dict(), ensure_ascii=False), caplog.text]
    )
    assert (
        raised.value.code,
        raised.value.exit_code,
        [secret for secret in (SENTINEL_KEY, SYSTEM, "Irmãos", "recusada") if secret in reported],
    ) == ("llm_error", 6, [])
