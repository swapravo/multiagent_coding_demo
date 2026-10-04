"""
Tool: search_files_and_folders
Searches for files and folders matching a glob pattern or containing a text string.
Used by agents to find relevant files without knowing exact paths.
"""

import fnmatch
import os
import re


def search_files_and_folders(
    root: str,
    pattern: str | None = None,
    contains: str | None = None,
    case_sensitive: bool = False,
) -> dict:
    """
    Search for files/folders under `root` by glob pattern and/or text content.

    Args:
        root:           Directory to search under (absolute or relative).
        pattern:        Glob pattern to match filenames against (e.g. "*.py", "*.md").
                        If None, matches all files.
        contains:       Text string to search for inside file contents.
                        If None, only the filename pattern is used.
        case_sensitive: Whether the `contains` search is case-sensitive. Defaults to False.

    Returns:
        A dict with keys:
            - success (bool)
            - root (str): Absolute path searched.
            - matches (list[dict]): Each match has:
                - path (str): Absolute path to the file.
                - relative_path (str): Path relative to root.
                - match_lines (list[str]): Lines containing the search term (if `contains` used).
            - error (str | None)
    """
    try:
        abs_root = os.path.abspath(root)
        if not os.path.isdir(abs_root):
            return {"success": False, "root": abs_root, "matches": [], "error": f"Directory not found: {abs_root}"}

        flags = 0 if case_sensitive else re.IGNORECASE
        contains_re = re.compile(re.escape(contains), flags) if contains else None

        matches = []
        for dirpath, _, filenames in os.walk(abs_root):
            for filename in sorted(filenames):
                # Filter by glob pattern
                if pattern and not fnmatch.fnmatch(filename, pattern):
                    continue
                full_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(full_path, abs_root)

                # Filter by content
                match_lines = []
                if contains_re:
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            for line in f:
                                if contains_re.search(line):
                                    match_lines.append(line.rstrip())
                        if not match_lines:
                            continue
                    except Exception:
                        continue

                matches.append({
                    "path": full_path,
                    "relative_path": rel_path,
                    "match_lines": match_lines,
                })

        return {"success": True, "root": abs_root, "matches": matches, "error": None}
    except Exception as e:
        return {"success": False, "root": os.path.abspath(root), "matches": [], "error": str(e)}


# JSON schema for LLM function-calling
SCHEMA = {
    "name": "search_files_and_folders",
    "description": (
        "Search for files under a directory by filename glob pattern and/or text content. "
        "Use this to find relevant existing files, check if a file already exists, "
        "or find all files of a certain type (e.g., all .py files, all plan .md files)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "root": {
                "type": "string",
                "description": "The root directory to search in.",
            },
            "pattern": {
                "type": "string",
                "description": (
                    "Glob pattern to match filenames, e.g. '*.py', '*.md', '*_plan.md'. "
                    "If omitted, all files are considered."
                ),
            },
            "contains": {
                "type": "string",
                "description": "Text string to search for inside file contents. Case-insensitive by default.",
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether the content search is case-sensitive. Defaults to false.",
                "default": False,
            },
        },
        "required": ["root"],
    },
}
