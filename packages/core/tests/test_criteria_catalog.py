import shutil
from pathlib import Path

import pytest

from wordcut.criteria import LEVELS, TEXTS, CatalogError, catalog, load_catalog

# docs/requirements 2.1.a.2 and the prototype: the criteria in the order of
# sugerir-cortes.md, filters first, with the default level of each.
EXPECTED = [
    ("triumphalism", "filter", "strict"),
    ("fragile_theology", "filter", "strict"),
    ("allegory", "filter", "moderate"),
    ("graceless_moralism", "filter", "moderate"),
    ("out_of_context", "filter", "strict"),
    ("sectarianism", "filter", "strict"),
    ("people_exposure", "filter", "strict"),
    ("factual_error", "filter", "moderate"),
    ("christological", "value", "strict"),
    ("practical_application", "value", "moderate"),
    ("memorable_phrase", "value", "moderate"),
]


def test_the_packaged_catalog_has_the_eight_filters_and_three_values_with_their_defaults() -> None:
    found = [(c.id, c.type, c.default_level) for c in catalog().criteria]

    assert found == EXPECTED


def copied_texts(tmp_path: Path) -> Path:
    """A copy of the packaged texts that a test can break."""
    return Path(shutil.copytree(TEXTS, tmp_path / "texts"))


def test_a_criterion_without_the_strict_level_is_a_programming_error_naming_its_file(
    tmp_path: Path,
) -> None:
    texts = copied_texts(tmp_path)
    allegory = texts / "allegory.md"
    allegory.write_text(allegory.read_text(encoding="utf-8").split("## strict")[0])

    with pytest.raises(CatalogError, match=r"allegory\.md"):
        load_catalog(texts)


@pytest.mark.parametrize(
    ("line", "broken"),
    [
        ("type: filter", "type: filtro"),
        ("default_level: moderate", "default_level: brando"),
        ("id: allegory", "id: triumphalism"),
    ],
    ids=["invalid type", "invalid default level", "repeated id"],
)
def test_a_malformed_criterion_header_is_a_programming_error_naming_its_file(
    tmp_path: Path, line: str, broken: str
) -> None:
    texts = copied_texts(tmp_path)
    allegory = texts / "allegory.md"
    allegory.write_text(allegory.read_text(encoding="utf-8").replace(line, broken))

    with pytest.raises(CatalogError, match=r"allegory\.md"):
        load_catalog(texts)


def test_a_criterion_with_a_section_that_is_not_a_level_is_a_programming_error(
    tmp_path: Path,
) -> None:
    texts = copied_texts(tmp_path)
    with (texts / "allegory.md").open("a", encoding="utf-8") as allegory:
        allegory.write("\n## extreme\n\nTexto de um nível que não existe.\n")

    with pytest.raises(CatalogError, match=r"allegory\.md"):
        load_catalog(texts)


@pytest.mark.parametrize("text", ["", "Objetivo sem os critérios."], ids=["empty", "no slots"])
def test_a_base_prompt_that_is_empty_or_lacks_a_slot_is_a_programming_error(
    tmp_path: Path, text: str
) -> None:
    texts = copied_texts(tmp_path)
    (texts / "base.md").write_text(text)

    with pytest.raises(CatalogError, match=r"base\.md"):
        load_catalog(texts)


def test_every_packaged_criterion_has_a_name_and_a_distinct_text_for_each_level() -> None:
    for criterion in catalog().criteria:
        texts = [criterion.fragment(level) for level in LEVELS]
        assert (bool(criterion.name), criterion.name != criterion.id) == (True, True)
        assert (all(texts), len(set(texts))) == (True, len(LEVELS)), criterion.id


def test_the_texts_ship_inside_the_package_next_to_the_module() -> None:
    import wordcut

    package = Path(wordcut.__file__).parent

    assert (TEXTS.is_relative_to(package), (TEXTS / "base.md").is_file()) == (True, True)


def test_a_missing_option_text_is_a_programming_error_naming_its_file(tmp_path: Path) -> None:
    texts = copied_texts(tmp_path)
    (texts / "options" / "reorder.md").unlink()

    with pytest.raises(CatalogError, match=r"reorder\.md"):
        load_catalog(texts)
