"""
Tool Registry (Harness)
=======================
Central registry of all tools available to agents.

This module provides:
  - `get_schemas(tools)` : Returns a list of OpenAI-style JSON schemas for the given tool names.
                           Pass these directly to the LLM as `tools=` in the API call.
  - `execute(name, args)`: Dispatches a tool call (name + args dict) to the correct Python function.
                           Call this when the LLM returns a tool_call in its response.
  - `ALL_TOOL_NAMES`     : List of all registered tool names.

Usage example (inside a pipeline agent runner):
    from tools.registry import get_schemas, execute

    schemas = get_schemas(["read", "write", "list_dir"])
    response = openai_client.chat.completions.create(
        model=..., messages=..., tools=schemas
    )
    for tool_call in response.choices[0].message.tool_calls or []:
        result = execute(tool_call.function.name, json.loads(tool_call.function.arguments))
        # Append result to messages as a tool response
"""

import importlib
import json
from typing import Any

# ---------------------------------------------------------------------------
# Registry: maps tool name -> (module_path, function_name)
# ---------------------------------------------------------------------------
_REGISTRY: dict[str, tuple[str, str]] = {
    "read":                    ("tools.read",                    "read"),
    "write":                   ("tools.write",                   "write"),
    "edit":                    ("tools.edit",                    "edit"),
    "list_dir":                ("tools.list",                    "list_dir"),
    "search_files_and_folders":("tools.search_files_and_folders","search_files_and_folders"),
    "run":                     ("tools.run",                     "run"),
    "clarify_or_ask_user":     ("tools.clarify_or_ask_user",     "clarify_or_ask_user"),
}

ALL_TOOL_NAMES: list[str] = list(_REGISTRY.keys())


def get_schemas(tools: list[str] | None = None) -> list[dict]:
    """
    Return OpenAI function-calling schemas for the specified tools.

    Args:
        tools: List of tool names to include. If None, returns all tools.

    Returns:
        List of dicts in OpenAI `{"type": "function", "function": {...}}` format.
    """
    names = tools if tools is not None else ALL_TOOL_NAMES
    schemas = []
    for name in names:
        if name not in _REGISTRY:
            raise ValueError(f"Unknown tool '{name}'. Available: {ALL_TOOL_NAMES}")
        module_path, _ = _REGISTRY[name]
        mod = importlib.import_module(module_path)
        schemas.append({"type": "function", "function": mod.SCHEMA})
    return schemas


def execute(name: str, args: dict[str, Any]) -> dict:
    """
    Execute a tool by name with the given arguments.

    Args:
        name: The tool name (must match a key in the registry).
        args: Keyword arguments to pass to the tool function.

    Returns:
        The tool's return value (always a dict).
    """
    if name not in _REGISTRY:
        return {
            "success": False,
            "error": f"Unknown tool '{name}'. Available: {ALL_TOOL_NAMES}",
        }
    module_path, func_name = _REGISTRY[name]
    mod = importlib.import_module(module_path)
    func = getattr(mod, func_name)
    try:
        return func(**args)
    except Exception as e:
        return {"success": False, "error": f"Tool '{name}' raised an exception: {e}"}


def execute_from_json(name: str, arguments_json: str) -> dict:
    """
    Convenience wrapper: parse JSON arguments string, then execute.

    Args:
        name:            Tool name.
        arguments_json:  JSON string of keyword arguments (from LLM tool_call.function.arguments).

    Returns:
        The tool's return value (always a dict).
    """
    try:
        args = json.loads(arguments_json)
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Failed to parse tool arguments JSON: {e}"}
    return execute(name, args)
