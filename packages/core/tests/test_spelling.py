import unicodedata

import pytest

from wordcut.cuts.spelling import check_spelling, levenshtein, word_core


# Distances and limits are written out by hand, never recomputed by the formula: the cases
# fix the rule of the prototype's checkWord (docs/prototype/wordcut.html).
@pytest.mark.parametrize(
    ("original", "proposed", "distance", "limit", "accepted"),
    [
        ("Jesús", "Jesus", 1, 1, True),
        ("não", "sim", 3, 1, False),
        ("deus", "Deus", 0, 1, True),
        ("paz.", "paz", 0, 1, True),
        ("e", "é", 1, 1, True),
        ("e", "ou", 2, 1, False),
        ("guarda-chuva", "guardachuva", 1, 4, True),
        ("misericórdia", "mizerycordea", 4, 4, True),
        ("misericórdia", "mizerycordeo", 5, 4, False),
        (unicodedata.normalize("NFD", "Jesús"), "Jesús", 0, 1, True),
    ],
)
def test_spelling_lock_accepts_only_a_fix_within_a_third_of_the_original_word(
    original: str, proposed: str, distance: int, limit: int, accepted: bool
) -> None:
    check = check_spelling(original, proposed)

    assert (check.distance, check.limit, check.accepted) == (distance, limit, accepted)


@pytest.mark.parametrize(
    ("text", "core"),
    [
        ("Jesús,", "jesús"),
        ("GRAÇA!", "graça"),
        ("guarda-chuva.", "guarda-chuva"),
        ("“João”", "joão"),
        ("3:16", "316"),
    ],
)
def test_word_core_keeps_lower_case_letters_digits_and_hyphens_only(text: str, core: str) -> None:
    assert word_core(text) == core


@pytest.mark.parametrize(
    ("a", "b", "distance"),
    [
        ("", "", 0),
        ("", "paz", 3),
        ("graça", "graca", 1),
        ("kitten", "sitting", 3),
        ("amor", "roma", 4),
    ],
)
def test_levenshtein_counts_insertions_deletions_and_substitutions_as_one_edit_each(
    a: str, b: str, distance: int
) -> None:
    assert levenshtein(a, b) == distance
