"""Tests for the configurable class-name → (person / ball) role mapping.

The keyless COCO default must keep matching "person"/"sports ball" exactly,
while a Universe model's custom labels can be mapped via env-driven settings.
"""

import pytest

from app.config import settings
from app.repo import detection


def test_defaults_match_coco_class_names():
    """Stock config reproduces the original hardcoded behavior."""
    assert detection.is_person("person")
    assert detection.is_ball("sports ball")
    assert not detection.is_person("sports ball")
    assert not detection.is_ball("person")
    assert not detection.is_person(None)
    assert not detection.is_ball(None)


def test_custom_universe_classes_match(monkeypatch):
    """A custom mapping (player / basketball) drives the heuristic."""
    monkeypatch.setattr(settings, "detection_person_classes", "player")
    monkeypatch.setattr(settings, "detection_ball_classes", "basketball")

    assert detection.is_person("player")
    assert detection.is_ball("basketball")
    # The COCO names no longer count once the model speaks a custom vocabulary.
    assert not detection.is_person("person")
    assert not detection.is_ball("sports ball")


def test_matching_is_case_insensitive(monkeypatch):
    """Class names normalize to lower-case on both sides of the match.

    `class_names_of` already lower-cases model labels, but the configured
    names are normalized too so mixed-case env values still match.
    """
    monkeypatch.setattr(settings, "detection_person_classes", "Player, Athlete")
    monkeypatch.setattr(settings, "detection_ball_classes", "Basketball")

    # class_names_of returns lower-cased names; verify those match the config.
    assert detection.is_person("player")
    assert detection.is_person("athlete")
    assert detection.is_ball("basketball")


def test_normalization_trims_and_drops_empties(monkeypatch):
    """Whitespace and empty entries are stripped from the configured sets."""
    monkeypatch.setattr(settings, "detection_person_classes", " player , , goalie ")
    monkeypatch.setattr(settings, "detection_ball_classes", "")

    assert settings.person_class_set == {"player", "goalie"}
    assert settings.ball_class_set == set()
    assert detection.is_person("goalie")
    assert not detection.is_ball("basketball")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("person", {"person"}),
        ("Person, PLAYER", {"person", "player"}),
        ("a,a,b", {"a", "b"}),
        ("  ", set()),
    ],
)
def test_normalize_classes(raw, expected):
    assert settings._normalize_classes(raw) == expected
