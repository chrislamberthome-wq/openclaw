"""Tests for replay validation."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verifier.replay import replay_matches

TASK_PATH = Path(__file__).resolve().parent.parent / "input" / "cognitive_task.json"


def test_replay_matches_expected_output():
    assert replay_matches(TASK_PATH) is True


def test_replay_sum_operation(tmp_path):
    task = {
        "task_id": "task-test",
        "operation": "sum",
        "inputs": [10, 20, 30],
        "expected_output": 60,
    }
    p = tmp_path / "task.json"
    p.write_text(json.dumps(task), encoding="utf-8")
    assert replay_matches(p) is True


def test_replay_mismatch_detected(tmp_path):
    task = {
        "task_id": "task-test",
        "operation": "sum",
        "inputs": [1, 2, 3],
        "expected_output": 999,  # wrong
    }
    p = tmp_path / "task.json"
    p.write_text(json.dumps(task), encoding="utf-8")
    assert replay_matches(p) is False


def test_replay_missing_field_raises(tmp_path):
    import pytest  # noqa: PLC0415

    task = {"task_id": "t", "operation": "sum", "inputs": [1]}
    # missing expected_output
    p = tmp_path / "task.json"
    p.write_text(json.dumps(task), encoding="utf-8")
    with pytest.raises(ValueError, match="missing required fields"):
        replay_matches(p)


def test_replay_empty_inputs(tmp_path):
    task = {
        "task_id": "task-empty",
        "operation": "sum",
        "inputs": [],
        "expected_output": 0,
    }
    p = tmp_path / "task.json"
    p.write_text(json.dumps(task), encoding="utf-8")
    assert replay_matches(p) is True
