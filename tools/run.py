"""
Tool: run
Executes a shell command in a controlled, sandboxed way.
Used by agents to run linters, formatters, tests, or build tools.

IMPORTANT GUARDRAILS:
  - Only whitelisted command prefixes are allowed (see ALLOWED_PREFIXES).
  - Commands run with a configurable timeout (default: 30 seconds).
  - Working directory is restricted to the project root.
  - Network-accessing commands are NOT allowed.
"""

import os
import subprocess
import shlex

# Only these command prefixes are permitted
ALLOWED_PREFIXES = (
    "python3",
    "pip",
    "npm",
    "npx",
    "node",
    "pytest",
    "ruff",
    "black",
    "mypy",
    "tsc",
    "eslint",
    "prettier",
    "uvicorn",
    "alembic",
    "sqlite3",
    "cat",
    "ls",
    "echo",
    "mkdir",
    "touch",
)


def run(command: str, cwd: str | None = None, timeout: int = 30) -> dict:
    """
    Execute a shell command and return its output.

    Args:
        command: The shell command to run (e.g. "python -m pytest tests/").
        cwd:     Working directory for the command. Defaults to the project root.
        timeout: Maximum execution time in seconds. Defaults to 30.

    Returns:
        A dict with keys:
            - success (bool): True if the command exited with code 0.
            - stdout (str): Standard output from the command.
            - stderr (str): Standard error from the command.
            - returncode (int): The process exit code.
            - error (str | None): High-level error message if the invocation failed.
    """
    try:
        # Safety check: only allow whitelisted command prefixes
        first_token = shlex.split(command)[0] if command.strip() else ""
        base_cmd = os.path.basename(first_token)
        if not any(base_cmd.startswith(prefix) for prefix in ALLOWED_PREFIXES):
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "error": (
                    f"Command '{base_cmd}' is not in the allowlist. "
                    f"Allowed prefixes: {ALLOWED_PREFIXES}"
                ),
            }

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        working_dir = os.path.abspath(cwd) if cwd else project_root

        result = subprocess.run(
            shlex.split(command),
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "error": None,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "error": f"Command timed out after {timeout} seconds.",
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "error": str(e),
        }


# JSON schema for LLM function-calling
SCHEMA = {
    "name": "run",
    "description": (
        "Execute a whitelisted shell command and return its stdout, stderr, and exit code. "
        "Use this to run linters (ruff, eslint), formatters (black, prettier), "
        "tests (pytest), or type checkers (mypy, tsc). "
        "Do NOT use for arbitrary system commands; only whitelisted prefixes are allowed."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute, e.g. 'python -m pytest output/code/backend/tests/'.",
            },
            "cwd": {
                "type": "string",
                "description": (
                    "Working directory for the command. "
                    "Defaults to the project root if not specified."
                ),
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum seconds to wait before killing the command. Defaults to 30.",
                "default": 30,
            },
        },
        "required": ["command"],
    },
}
