"""
Tool: read
Reads the content of a file from the filesystem.
Used by agents to read existing plans, code, schemas, and conventions.
"""

import os


def read(path: str) -> dict:
    """
    Read the full content of a file.

    Args:
        path: Absolute or relative path to the file to read.

    Returns:
        A dict with keys:
            - success (bool): Whether the read succeeded.
            - content (str | None): The file content, or None on failure.
            - error (str | None): Error message if failed.
    """
    try:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return {"success": False, "content": None, "error": f"File not found: {abs_path}"}
        if not os.path.isfile(abs_path):
            return {"success": False, "content": None, "error": f"Path is not a file: {abs_path}"}
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"success": True, "content": content, "error": None}
    except Exception as e:
        return {"success": False, "content": None, "error": str(e)}


# JSON schema for LLM function-calling
SCHEMA = {
    "name": "read",
    "description": (
        "Read the full content of a file from the filesystem. "
        "Use this to read existing plan files, code files, SQL schemas, conventions, etc."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path to the file to read. Can be absolute or relative to the project root.",
            }
        },
        "required": ["path"],
    },
}
