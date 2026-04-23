"""Tests for the templates module."""

from prompt_optimizer.templates import SCORING_DIMENSIONS

EXPECTED_DIMENSIONS = {"clarity", "specificity", "structure", "actionability"}


def test_scoring_dimensions_has_all_expected_keys():
    """SCORING_DIMENSIONS contains exactly the 4 expected dimensions."""
    assert set(SCORING_DIMENSIONS.keys()) == EXPECTED_DIMENSIONS


def test_scoring_dimensions_descriptions_are_non_empty_strings():
    """Each dimension has a non-empty description string."""
    for key in EXPECTED_DIMENSIONS:
        value = SCORING_DIMENSIONS[key]
        assert isinstance(value, str), f"{key} description should be a string"
        assert len(value) > 0, f"{key} description should not be empty"
