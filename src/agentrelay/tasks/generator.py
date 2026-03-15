"""Task generator: create task dicts from templates with randomized inputs.

Usage:
    from agentrelay.tasks.generator import generate_task, generate_tasks

    # Single task from a specific template
    task = generate_task("ds_earnings", publisher_id="...")

    # Batch: one task per template (20 total)
    tasks = generate_tasks(publisher_id="...")

    # Batch: N random tasks
    tasks = generate_tasks(publisher_id="...", count=50)
"""

from __future__ import annotations

import random
from typing import Any

from .templates import ALL_TEMPLATES, TEMPLATES_BY_TYPE, get_template


def generate_task(
    template_id: str,
    publisher_id: str,
    *,
    deadline_override: int | None = None,
    reward_override: float | None = None,
) -> dict[str, Any]:
    """Generate a single task dict from a template, with randomized input_data.

    Returns a dict ready to POST to /tasks.
    """
    tmpl = get_template(template_id)
    if tmpl is None:
        raise ValueError(f"Unknown template: {template_id}")

    input_data = tmpl["generate_input"]()

    return {
        "task_spec": {
            "task_type": tmpl["task_type"],
            "difficulty": tmpl["difficulty"],
            "input_data": input_data,
            "output_schema": tmpl["output_schema"],
            "validation_method": tmpl["validation_method"],
            "token_estimate": tmpl["token_estimate"],
        },
        "publisher_id": publisher_id,
        "reward": reward_override if reward_override is not None else tmpl["reward"],
        "deadline_seconds": deadline_override if deadline_override is not None else tmpl["deadline_seconds"],
    }


def generate_tasks(
    publisher_id: str,
    *,
    count: int | None = None,
    task_type: str | None = None,
    deadline_override: int | None = None,
) -> list[dict[str, Any]]:
    """Generate multiple tasks.

    - count=None, task_type=None  → one task per template (20 total)
    - count=N, task_type=None     → N random tasks from all templates
    - count=N, task_type="coding" → N random tasks from that type only
    - count=None, task_type="coding" → all templates of that type
    """
    if task_type is not None:
        pool = TEMPLATES_BY_TYPE.get(task_type, [])
        if not pool:
            raise ValueError(f"No templates for type: {task_type}")
    else:
        pool = ALL_TEMPLATES

    if count is None:
        templates = pool
    else:
        templates = [random.choice(pool) for _ in range(count)]

    return [
        generate_task(
            tmpl["id"],
            publisher_id,
            deadline_override=deadline_override,
        )
        for tmpl in templates
    ]
