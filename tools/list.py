"""
Tool: list
Lists files and subdirectories within a given directory.
Used by agents to explore the project structure and discover existing outputs.
"""

import os


def list_dir(path: str, recursive: bool = False) -> dict:
    """
    List the contents of a directory.

    Args:
        path:      Absolute or relative path to the directory to list.
        recursive: If True, recursively list all nested files and directories.
                   Defaults to False (top-level only).

    Returns:
        A dict with keys:
            - success (bool): Whether the listing succeeded.
            - path (str): The absolute path that was listed.
            - entries (list[dict]): List of entries, each with:
                - name (str): File or directory name.
                - type (str): "file" or "directory".
                - size_bytes (int | None): File size in bytes (files only).
                - relative_path (str): Path relative to the listed directory.
            - error (str | None): Error message if failed.
    """
    try:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return {"success": False, "path": abs_path, "entries": [], "error": f"Path not found: {abs_path}"}
        if not os.path.isdir(abs_path):
            return {"success": False, "path": abs_path, "entries": [], "error": f"Path is not a directory: {abs_path}"}

        entries = []

        def _collect(dir_path: str, rel_base: str):
            try:
                names = sorted(os.listdir(dir_path))
            except PermissionError:
                return
            for name in names:
                full = os.path.join(dir_path, name)
                rel = os.path.join(rel_base, name) if rel_base else name
                if os.path.isfile(full):
                    entries.append({
                        "name": name,
                        "type": "file",
                        "size_bytes": os.path.getsize(full),
                        "relative_path": rel,
                    })
                elif os.path.isdir(full):
                    entries.append({
                        "name": name,
                        "type": "directory",
                        "size_bytes": None,
                        "relative_path": rel,
                    })
                    if recursive:
                        _collect(full, rel)

        _collect(abs_path, "")
        return {"success": True, "path": abs_path, "entries": entries, "error": None}
    except Exception as e:
        return {"success": False, "path": os.path.abspath(path), "entries": [], "error": str(e)}


# JSON schema for LLM function-calling
SCHEMA = {
    "name": "list_dir",
    "description": (
        "List the files and subdirectories inside a directory. "
        "Use this to explore the project structure, discover existing output files, "
        "or check what code has already been generated."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path to the directory to list.",
            },
            "recursive": {
                "type": "boolean",
                "description": "If true, recursively list all nested files and directories. Defaults to false.",
                "default": False,
            },
        },
        "required": ["path"],
    },
}
