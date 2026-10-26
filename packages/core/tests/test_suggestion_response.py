import json

import pytest

from wordcut.suggestion.response import InvalidResponse, SuggestedCut, parse_response

SENTENCE_COUNT = 10


@pytest.mark.parametrize(
    ("text", "reorder", "cuts"),
    [
        ('{"cuts": []}', False, []),
        (
            '{"cuts": [{"title": "Graça", "sentences": [3, 4, 5, 9]}]}',
            False,
            [SuggestedCut("Graça", (3, 4, 5, 9))],
        ),
        (
            '{"cuts": [{"title": "Graça", "sentences": [1, 2]},'
            ' {"title": "Fé", "sentences": [2, 7]}]}',
            False,
            [SuggestedCut("Graça", (1, 2)), SuggestedCut("Fé", (2, 7))],
        ),
        (
            '{"cuts": [{"title": "Gancho no fim", "sentences": [9, 10, 3]}]}',
            True,
            [SuggestedCut("Gancho no fim", (9, 10, 3))],
        ),
        (
            '{"cuts": [{"title": "Graça", "sentences": [3, 4],'
            ' "note": "termina no gancho da frase 4"}]}',
            False,
            [SuggestedCut("Graça", (3, 4))],
        ),
        (
            '{"cuts": [{"title": "Graça", "sentences": [3, 4], "tom": "pastoral"}]}',
            False,
            [SuggestedCut("Graça", (3, 4))],
        ),
    ],
    ids=[
        "no cuts",
        "one cut",
        "same sentence in two cuts",
        "reordered when allowed",
        "note of the reorder option ignored",
        "unknown field in the cut ignored",
    ],
)
def test_an_answer_in_the_schema_gives_its_cuts(
    text: str, reorder: bool, cuts: list[SuggestedCut]
) -> None:
    assert parse_response(text, SENTENCE_COUNT, reorder=reorder) == cuts


def cut_with(**fields: object) -> str:
    return json.dumps({"cuts": [{"title": "Graça", "sentences": [3, 4], **fields}]})


@pytest.mark.parametrize(
    "text",
    [
        "Aqui estão os cortes: 3, 4 e 5.",
        '```json\n{"cuts": []}\n```',
        '[{"title": "Graça", "sentences": [3]}]',
        '{"cortes": []}',
        '{"cuts": {"title": "Graça", "sentences": [3]}}',
        '{"cuts": ["Graça"]}',
        '{"cuts": [{"sentences": [3, 4]}]}',
        cut_with(title=""),
        cut_with(title="   "),
        cut_with(title=7),
        '{"cuts": [{"title": "Graça"}]}',
        cut_with(sentences=[]),
        cut_with(sentences="3-4"),
        cut_with(sentences=[3, True]),
        cut_with(sentences=[3, 4.0]),
        cut_with(sentences=[3, "4"]),
        cut_with(sentences=[3, 11]),
        cut_with(sentences=[0, 3]),
        cut_with(sentences=[3, 4, 3]),
        cut_with(sentences=[9, 3]),
    ],
    ids=[
        "not json",
        "json inside a markdown fence",
        "root is not an object",
        "cuts missing",
        "cuts is not a list",
        "cut is not an object",
        "title missing",
        "title empty",
        "title blank",
        "title not a string",
        "sentences missing",
        "sentences empty",
        "sentences not a list",
        "sentence id is a boolean",
        "sentence id is a float",
        "sentence id is a string",
        "sentence past the last one",
        "sentence before the first one",
        "sentence repeated in the cut",
        "out of sermon order without reorder",
    ],
)
def test_an_answer_outside_the_schema_is_invalid_and_says_why(text: str) -> None:
    with pytest.raises(InvalidResponse) as raised:
        parse_response(text, SENTENCE_COUNT, reorder=False)

    assert str(raised.value).strip() != ""


def test_a_sentence_repeated_in_a_cut_is_invalid_even_when_reordering_is_allowed() -> None:
    with pytest.raises(InvalidResponse, match="repete"):
        parse_response(cut_with(sentences=[3, 4, 3]), SENTENCE_COUNT, reorder=True)
