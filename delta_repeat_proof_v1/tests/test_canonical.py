"""Tests for canonical.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verifier.canonical import canonical_dumps, is_canonical, load_canonical_line


def test_canonical_dumps_sorts_keys():
    result = canonical_dumps({"b": 2, "a": 1})
    assert result == '{"a":1,"b":2}'


def test_canonical_dumps_no_spaces():
    result = canonical_dumps({"key": "value"})
    assert " " not in result


def test_canonical_dumps_nested():
    result = canonical_dumps({"z": {"y": 1, "x": 2}})
    assert result == '{"z":{"x":2,"y":1}}'


def test_is_canonical_true():
    assert is_canonical('{"a":1,"b":2}') is True


def test_is_canonical_false_extra_space():
    assert is_canonical('{"a": 1}') is False


def test_is_canonical_false_wrong_key_order():
    assert is_canonical('{"b":2,"a":1}') is False


def test_is_canonical_invalid_json():
    assert is_canonical("{not json}") is False


def test_load_canonical_line_valid():
    obj = load_canonical_line('{"a":1,"b":2}')
    assert obj == {"a": 1, "b": 2}


def test_load_canonical_line_strips_newline():
    obj = load_canonical_line('{"a":1}\n')
    assert obj == {"a": 1}


def test_load_canonical_line_raises_on_non_canonical():
    import pytest  # noqa: PLC0415

    with pytest.raises(ValueError, match="Non-canonical"):
        load_canonical_line('{"b":2,"a":1}')
