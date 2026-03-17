"""Task replay validation.

Reads the cognitive task definition and re-executes the operation,
then compares the result against the recorded expected_output.
"""

import json
from pathlib import Path


_SUPPORTED_OPERATIONS = {"sum"}


def _execute(operation: str, inputs: list) -> object:
    if operation == "sum":
        return sum(inputs)
    raise ValueError(f"Unsupported operation: {operation!r}")


def replay_matches(task_path: Path) -> bool:
    """Return True iff re-executing the task produces expected_output."""
    with task_path.open("r", encoding="utf-8") as fh:
        task = json.load(fh)

    required = {"task_id", "operation", "inputs", "expected_output"}
    missing = required - task.keys()
    if missing:
        raise ValueError(f"Task missing required fields: {missing}")

    result = _execute(task["operation"], task["inputs"])
    return result == task["expected_output"]
