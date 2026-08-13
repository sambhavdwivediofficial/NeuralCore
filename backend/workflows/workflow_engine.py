# workflows/workflow_engine.py
from __future__ import annotations

import re
from typing import Any

from monitoring.logging import get_logger
from workflows.workflow_registry import StepDefinition, StepType

logger = get_logger("neuralcore.workflows.engine")

_TEMPLATE_VAR_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_.]*)\}")


def render_template_string(template: str, context: dict[str, Any]) -> str:
    def _replace(match: re.Match[str]) -> str:
        path = match.group(1)
        value = _resolve_path(path, context)
        return str(value) if value is not None else match.group(0)

    return _TEMPLATE_VAR_PATTERN.sub(_replace, template)


def render_template_dict(template: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    rendered: dict[str, Any] = {}
    for key, value in template.items():
        if isinstance(value, str):
            rendered[key] = render_template_string(value, context)
        elif isinstance(value, dict):
            rendered[key] = render_template_dict(value, context)
        elif isinstance(value, list):
            rendered[key] = [render_template_string(v, context) if isinstance(v, str) else v for v in value]
        else:
            rendered[key] = value
    return rendered


def _resolve_path(path: str, context: dict[str, Any]) -> Any:
    parts = path.split(".")
    current: Any = context
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return None
        if current is None:
            return None
    return current


_COMPARISON_PATTERN = re.compile(r"^\s*(.+?)\s*(==|!=|>=|<=|>|<)\s*(.+?)\s*$")


def evaluate_condition(expression: str, context: dict[str, Any]) -> bool:
    rendered = render_template_string(expression, context)
    match = _COMPARISON_PATTERN.match(rendered)

    if not match:
        return _truthy(rendered)

    left_raw, operator, right_raw = match.groups()
    left = _coerce_literal(left_raw)
    right = _coerce_literal(right_raw)

    try:
        if operator == "==":
            return left == right
        if operator == "!=":
            return left != right
        if operator == ">=":
            return float(left) >= float(right)
        if operator == "<=":
            return float(left) <= float(right)
        if operator == ">":
            return float(left) > float(right)
        if operator == "<":
            return float(left) < float(right)
    except (TypeError, ValueError):
        return False

    return False


def _coerce_literal(value: str) -> Any:
    value = value.strip().strip("'\"")
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _truthy(value: str) -> bool:
    return value.strip().lower() not in ("", "false", "none", "null", "0")


def topological_sort(steps: list[StepDefinition]) -> list[StepDefinition]:
    step_map = {s.id: s for s in steps}
    in_degree = {s.id: 0 for s in steps}
    for step in steps:
        for dep in step.depends_on:
            in_degree[step.id] += 1

    queue = [s for s in steps if in_degree[s.id] == 0]
    ordered: list[StepDefinition] = []

    while queue:
        current = queue.pop(0)
        ordered.append(current)
        for step in steps:
            if current.id in step.depends_on:
                in_degree[step.id] -= 1
                if in_degree[step.id] == 0:
                    queue.append(step_map[step.id])

    if len(ordered) != len(steps):
        raise ValueError("Workflow has a circular dependency and cannot be topologically sorted")

    return ordered


def get_ready_steps(
    steps: list[StepDefinition], completed_ids: set[str], failed_ids: set[str]
) -> list[StepDefinition]:
    ready: list[StepDefinition] = []
    for step in steps:
        if step.id in completed_ids or step.id in failed_ids:
            continue
        if any(dep in failed_ids for dep in step.depends_on):
            continue
        if all(dep in completed_ids for dep in step.depends_on):
            ready.append(step)
    return ready
