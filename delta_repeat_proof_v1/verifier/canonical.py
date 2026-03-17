"""Canonical JSON serialisation and validation.

Canonical form: UTF-8, keys sorted lexicographically, no extra whitespace,
no trailing newline on a single object. Any deviation is a hard error.
"""

import json


def canonical_dumps(obj: object) -> str:
    """Return the canonical JSON string for *obj*."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def is_canonical(raw: str) -> bool:
    """Return True iff *raw* is already in canonical form."""
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return False
    return canonical_dumps(obj) == raw


def load_canonical_line(line: str) -> dict:
    """Parse *line* and raise ValueError if it is not canonical."""
    line = line.rstrip("\n")
    if not is_canonical(line):
        raise ValueError(f"Non-canonical JSON line: {line!r}")
    return json.loads(line)
