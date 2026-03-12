"""Tests for verifier.canonicalize — v1.0."""

from __future__ import annotations

import pytest

from verifier.canonicalize import canonical_json_bytes


class TestCanonicalJsonBytes:
    def test_empty_object(self) -> None:
        assert canonical_json_bytes({}) == b"{}"

    def test_single_key(self) -> None:
        assert canonical_json_bytes({"a": 1}) == b'{"a":1}'

    def test_key_sort_order(self) -> None:
        # Keys must be sorted lexicographically.
        assert canonical_json_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'

    def test_nested_object_key_sort(self) -> None:
        # Sorting applies recursively.
        assert canonical_json_bytes({"k": {"z": 0, "a": 1}}) == b'{"k":{"a":1,"z":0}}'

    def test_array_preserves_order(self) -> None:
        # Arrays must NOT be sorted.
        assert canonical_json_bytes({"x": [3, 1, 2]}) == b'{"x":[3,1,2]}'

    def test_boolean_true(self) -> None:
        assert canonical_json_bytes({"v": True}) == b'{"v":true}'

    def test_boolean_false(self) -> None:
        assert canonical_json_bytes({"v": False}) == b'{"v":false}'

    def test_null(self) -> None:
        assert canonical_json_bytes({"v": None}) == b'{"v":null}'

    def test_integer(self) -> None:
        assert canonical_json_bytes({"n": 42}) == b'{"n":42}'

    def test_negative_integer(self) -> None:
        assert canonical_json_bytes({"n": -7}) == b'{"n":-7}'

    def test_float(self) -> None:
        assert canonical_json_bytes({"n": 0.95}) == b'{"n":0.95}'

    def test_float_one(self) -> None:
        assert canonical_json_bytes({"n": 1.0}) == b'{"n":1.0}'

    def test_string_basic(self) -> None:
        assert canonical_json_bytes({"s": "hello"}) == b'{"s":"hello"}'

    def test_string_double_quote_escaped(self) -> None:
        assert canonical_json_bytes({"s": 'he"llo'}) == b'{"s":"he\\"llo"}'

    def test_string_backslash_escaped(self) -> None:
        assert canonical_json_bytes({"s": "a\\b"}) == b'{"s":"a\\\\b"}'

    def test_string_control_char_escaped(self) -> None:
        # Newline (U+000A) must be escaped as \u000a.
        result = canonical_json_bytes({"s": "\n"})
        assert result == b'{"s":"\\u000a"}'

    def test_string_non_ascii_not_escaped(self) -> None:
        # Non-ASCII characters are emitted as UTF-8 bytes, not \uXXXX escapes.
        result = canonical_json_bytes({"s": "\u00e9"})  # é
        assert result == '{"s":"\u00e9"}'.encode("utf-8")

    def test_no_trailing_newline(self) -> None:
        result = canonical_json_bytes({"a": 1})
        assert not result.endswith(b"\n")

    def test_no_whitespace_between_tokens(self) -> None:
        result = canonical_json_bytes({"a": 1, "b": 2})
        assert b" " not in result
        assert b"\n" not in result

    def test_nan_raises(self) -> None:
        import math
        with pytest.raises(ValueError, match="NaN"):
            canonical_json_bytes({"x": math.nan})

    def test_infinity_raises(self) -> None:
        import math
        with pytest.raises(ValueError, match="Infinity"):
            canonical_json_bytes({"x": math.inf})

    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(TypeError):
            canonical_json_bytes({"x": object()})

    def test_non_string_key_raises(self) -> None:
        with pytest.raises(TypeError):
            canonical_json_bytes({1: "v"})  # type: ignore[dict-item]

    def test_nested_list_of_objects(self) -> None:
        obj = {"items": [{"b": 2, "a": 1}, {"d": 4, "c": 3}]}
        result = canonical_json_bytes(obj)
        assert result == b'{"items":[{"a":1,"b":2},{"c":3,"d":4}]}'

    def test_output_is_utf8_bytes(self) -> None:
        result = canonical_json_bytes({"x": 1})
        assert isinstance(result, bytes)
