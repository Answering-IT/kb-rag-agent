"""
Migration Utilities

Common functions for metadata generation and S3 operations.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional, Any

# Get migration directory
MIGRATION_DIR = Path(__file__).parent


def generate_partition_key(
    tenant_id: str,
    project_id: Optional[str] = None,
    task_id: Optional[str] = None,
    subtask_id: Optional[str] = None
) -> str:
    """
    Generate partition_key from IDs.

    Format:
    - Tenant: t{tenant_id}
    - Project: t{tenant_id}_p{project_id}
    - Task: t{tenant_id}_p{project_id}_t{task_id}
    - Subtask: t{tenant_id}_p{project_id}_t{task_id}_s{subtask_id}
    """
    if not tenant_id:
        raise ValueError("tenant_id is required")

    key = f"t{tenant_id}"

    if project_id:
        key += f"_p{project_id}"

    if task_id:
        if not project_id:
            raise ValueError("project_id required when task_id is provided")
        key += f"_t{task_id}"

    if subtask_id:
        if not task_id:
            raise ValueError("task_id required when subtask_id is provided")
        key += f"_s{subtask_id}"

    return key


def parse_s3_path(s3_path: str, tenant_id: str) -> Dict[str, Optional[str]]:
    """
    Parse S3 path to extract tenant, project, task, subtask IDs.

    Examples:
        organizations/1/projects/949/file.pdf
        -> {tenant_id: "1", project_id: "949", task_id: None, subtask_id: None}

        organizations/1/projects/949/tasks/5/file.pdf
        -> {tenant_id: "1", project_id: "949", task_id: "5", subtask_id: None}

        organizations/1/projects/949/tasks/5/subtasks/10/file.pdf
        -> {tenant_id: "1", project_id: "949", task_id: "5", subtask_id: "10"}
    """
    parts = s3_path.split('/')

    result = {
        "tenant_id": tenant_id,
        "project_id": None,
        "task_id": None,
        "subtask_id": None
    }

    try:
        # Find projects index
        if "projects" in parts:
            projects_idx = parts.index("projects")
            if len(parts) > projects_idx + 1:
                result["project_id"] = parts[projects_idx + 1]

        # Find tasks index
        if "tasks" in parts:
            tasks_idx = parts.index("tasks")
            if len(parts) > tasks_idx + 1:
                result["task_id"] = parts[tasks_idx + 1]

        # Find subtasks index
        if "subtasks" in parts:
            subtasks_idx = parts.index("subtasks")
            if len(parts) > subtasks_idx + 1:
                result["subtask_id"] = parts[subtasks_idx + 1]

    except (ValueError, IndexError):
        pass

    return result


def generate_project_path(
    tenant_id: str,
    project_id: str,
    task_id: Optional[str] = None,
    subtask_id: Optional[str] = None
) -> str:
    """
    Generate project_path based on hierarchy level.

    Returns:
        - Project: "organizations/1/projects/949"
        - Task: "organizations/1/projects/949/tasks/5"
        - Subtask: "organizations/1/projects/949/tasks/5/subtasks/10"
    """
    path = f"organizations/{tenant_id}/projects/{project_id}"

    if task_id:
        path += f"/tasks/{task_id}"

    if subtask_id:
        path += f"/subtasks/{subtask_id}"

    return path


def generate_metadata_json(
    tenant_id: str,
    project_id: Optional[str] = None,
    task_id: Optional[str] = None,
    subtask_id: Optional[str] = None,
    attachment_id: Optional[str] = None,
    file_name: Optional[str] = None,
    attachment_type: Optional[str] = None,
    project_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate metadata JSON in Bedrock KB format.

    Returns:
        {
            "metadataAttributes": {
                "tenant_id": "1",
                "project_id": "949",
                "partition_key": "t1_p949",
                "attachment_id": "670",
                "file_name": "doc.pdf",
                "attachment_type": "NORMAL",
                "project_path": "organizations/1/projects/949"
            }
        }
    """
    # Generate partition_key
    partition_key = generate_partition_key(
        tenant_id=tenant_id,
        project_id=project_id,
        task_id=task_id,
        subtask_id=subtask_id
    )

    # Build metadata attributes
    metadata = {
        "tenant_id": tenant_id,
        "partition_key": partition_key
    }

    # Add optional filterable fields
    if project_id:
        metadata["project_id"] = project_id
    if task_id:
        metadata["task_id"] = task_id
    if subtask_id:
        metadata["subtask_id"] = subtask_id

    # Add non-filterable fields (if provided)
    if attachment_id:
        metadata["attachment_id"] = str(attachment_id)
    if file_name:
        metadata["file_name"] = file_name
    if attachment_type:
        metadata["attachment_type"] = attachment_type
    if project_path:
        metadata["project_path"] = project_path
    elif project_id:
        # Generate project_path if not provided
        metadata["project_path"] = generate_project_path(
            tenant_id=tenant_id,
            project_id=project_id,
            task_id=task_id,
            subtask_id=subtask_id
        )

    return {
        "metadataAttributes": metadata
    }


def get_absolute_path(relative_path: str) -> Path:
    """Convert relative path to absolute path from migration directory."""
    return MIGRATION_DIR / relative_path


def save_json(data: Any, file_path: str):
    """Save data as JSON file."""
    abs_path = get_absolute_path(file_path) if not Path(file_path).is_absolute() else Path(file_path)
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    with open(abs_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(file_path: str) -> Any:
    """Load JSON file."""
    abs_path = get_absolute_path(file_path) if not Path(file_path).is_absolute() else Path(file_path)
    if not abs_path.exists():
        return None
    with open(abs_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_partition_from_path(s3_path: str) -> str:
    """
    Get partition string for API call from S3 path.

    Examples:
        organizations/1/projects/949/file.pdf -> PROJECT-949
        organizations/1/projects/949/tasks/5/file.pdf -> TASK-5
        organizations/1/projects/949/tasks/5/subtasks/10/file.pdf -> SUBTASK-10
    """
    parsed = parse_s3_path(s3_path, "1")

    if parsed["subtask_id"]:
        return f"SUBTASK-{parsed['subtask_id']}"
    elif parsed["task_id"]:
        return f"TASK-{parsed['task_id']}"
    elif parsed["project_id"]:
        return f"PROJECT-{parsed['project_id']}"
    else:
        return None


def is_allowed_file(file_name: str, allowed_extensions: list) -> bool:
    """Check if file extension is allowed."""
    ext = Path(file_name).suffix.lower()
    return ext in allowed_extensions


def should_ignore_file(file_name: str, ignored_extensions: list) -> bool:
    """Check if file should be ignored (no metadata needed)."""
    ext = Path(file_name).suffix.lower()
    return ext in ignored_extensions
