"""
Tool: write
Writes content to a file on the filesystem.
Creates parent directories automatically if they don't exist.
Used by agents to write plan files and generated code files.
"""

import os


def write(path: str, content: str, overwrite: bool = True) -> dict:
    """
    Write content to a file. Creates intermediate directories automatically.

    Args:
        path:      Absolute or relative path to the file to write.
        content:   The string content to write to the file.
        overwrite: If False and the file already exists, return an error instead
                   of overwriting. Defaults to True.

    Returns:
        A dict with keys:
            - success (bool): Whether the write succeeded.
            - path (str): The absolute path that was written.
            - error (str | None): Error message if failed.
    """
    try:
        abs_path = os.path.abspath(path)
        if not overwrite and os.path.exists(abs_path):
            return {
                "success": False,
                "path": abs_path,
                "error": f"File already exists and overwrite=False: {abs_path}",
            }
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "path": abs_path, "error": None}
    except Exception as e:
        return {"success": False, "path": os.path.abspath(path), "error": str(e)}


# JSON schema for LLM function-calling
SCHEMA = {
    "name": "write",
    "description": (
        "Write content to a file on the filesystem. "
        "Automatically creates any missing parent directories. "
        "Use this to write plan files (output/plan/) and code files (output/code/)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path to the file to write. Can be absolute or relative to the project root.",
            },
            "content": {
                "type": "string",
                "description": "The full string content to write into the file.",
            },
            "overwrite": {
                "type": "boolean",
                "description": (
                    "Whether to overwrite the file if it already exists. "
                    "Defaults to true. Set to false to prevent accidental overwrites."
                ),
                "default": True,
            },
        },
        "required": ["path", "content"],
    },
}
