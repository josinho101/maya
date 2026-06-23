import pytest

from maya.managers.slugify import EmptySlugError, slugify


def test_basic_case():
    assert slugify("Acme Webapp") == "acme-webapp"


def test_collapses_punctuation_and_whitespace():
    assert slugify("  Acme!!  Webapp ") == "acme-webapp"


def test_strips_boundary_hyphens():
    assert slugify("-Acme-") == "acme"


def test_truncates_at_max_length_and_restrips_trailing_hyphen():
    name = "a" * 63 + " " + "b" * 10
    result = slugify(name)
    assert len(result) <= 64
    assert not result.endswith("-")


def test_all_punctuation_raises_empty_slug_error():
    with pytest.raises(EmptySlugError):
        slugify("!!!")


def test_non_ascii_characters_are_treated_as_non_alnum():
    assert slugify("Café Project") == "caf-project"
