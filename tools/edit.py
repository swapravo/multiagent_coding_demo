"""
Tool: edit
Edits an existing file by replacing a specific string with new content.
Used by agents to make targeted changes to existing files without rewriting them entirely.
"""

import os


def edit(path: str, old_text: str, new_text: str) -> dict:
    """
    Replace the first occurrence of `old_text` in a file with `new_text`.

    Args:
        path:     Absolute or relative path to the file to edit.
        old_text: The exact string to search for and replace.
        new_text: The replacement string.

    Returns:
        A dict with keys:
            - success (bool): Whether the edit succeeded.
            - path (str): The absolute path of the edited file.
            - replacements (int): Number of replacements made (0 or 1).
            - error (str | None): Error message if failed.
    """
    try:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return {
                "success": False,
                "path": abs_path,
                "replacements": 0,
                "error": f"File not found: {abs_path}",
            }
        with open(abs_path, "r", encoding="utf-8") as f:
            original = f.read()
        if old_text not in original:
            return {
                "success": False,
                "path": abs_path,
                "replacements": 0,
                "error": f"old_text not found in file. No changes made.",
            }
        updated = original.replace(old_text, new_text, 1)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(updated)
        return {"success": True, "path": abs_path, "replacements": 1, "error": None}
    except Exception as e:
        return {"success": False, "path": os.path.abspath(path), "replacements": 0, "error": str(e)}


# JSON schema for LLM function-calling
SCHEMA = {
    "name": "edit",
    "description": (
        "Edit an existing file by replacing a specific substring with new content. "
        "Only replaces the FIRST occurrence. Use this for targeted edits to avoid "
        "rewriting entire files. Fails if old_text is not found."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path to the file to edit.",
            },
            "old_text": {
                "type": "string",
                "description": "The exact string to find and replace. Must match exactly including whitespace.",
            },
            "new_text": {
                "type": "string",
                "description": "The string to replace old_text with.",
            },
        },
        "required": ["path", "old_text", "new_text"],
    },
}
