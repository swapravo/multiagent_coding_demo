"""
Pipeline Runner
===============
Runs the multi-agent coding pipeline in a fixed sequence:

  1. requirements_collection_agent
  2. data_modelling_agent
  3. backend_agent
  4. frontend_agent

Each agent is driven by:
  - A system prompt loaded from agents/<agent_name>.md
  - Access to a defined subset of tools (registered in tools/registry.py)
  - The OpenRouter API (model configurable via .env)

The LLM loop for each agent:
  - Sends the system prompt + task message
  - Handles tool_calls from the model by executing them via tools/registry.py
  - Continues until the model sends a final text message with no tool_calls
  - On ClarificationRequired: pauses, asks the user, and resumes

Usage:
  python pipeline.py "Build a simple TODO app with user authentication"
  python pipeline.py --task-file task.md
"""

import argparse
import json
import os
import sys
import textwrap
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from tools.clarify_or_ask_user import ClarificationRequired
from tools.registry import execute_from_json, get_schemas

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

PROJECT_ROOT = Path(__file__).parent
AGENTS_DIR = PROJECT_ROOT / "agents"
OUTPUT_PLAN_DIR = PROJECT_ROOT / "output" / "plan"
OUTPUT_CODE_DIR = PROJECT_ROOT / "output" / "code"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
OPENROUTER_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "multiagent_coding_demo")

if not OPENROUTER_API_KEY:
    sys.exit("ERROR: OPENROUTER_API_KEY is not set. Please add it to your .env file.")

# ---------------------------------------------------------------------------
# Pipeline definition
# Each entry: (agent_name, [tool_names_allowed])
# ---------------------------------------------------------------------------

PIPELINE: list[tuple[str, list[str]]] = [
    (
        "requirements_collection_agent",
        ["read", "write", "list_dir", "search_files_and_folders", "clarify_or_ask_user"],
    ),
    (
        "data_modelling_agent",
        ["read", "write", "edit", "list_dir", "search_files_and_folders", "run", "clarify_or_ask_user"],
    ),
    (
        "backend_agent",
        ["read", "write", "edit", "list_dir", "search_files_and_folders", "run", "clarify_or_ask_user"],
    ),
    (
        "frontend_agent",
        ["read", "write", "edit", "list_dir", "search_files_and_folders", "run", "clarify_or_ask_user"],
    ),
]

# ---------------------------------------------------------------------------
# OpenRouter client
# ---------------------------------------------------------------------------

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL,
    default_headers={
        "X-Title": OPENROUTER_APP_NAME,
    },
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_agent_system_prompt(agent_name: str) -> str:
    """Load the agent's persona/instructions from agents/<agent_name>.md."""
    path = AGENTS_DIR / f"{agent_name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Agent definition not found: {path}")
    return path.read_text(encoding="utf-8")


def load_conventions() -> str:
    """Load the shared conventions file."""
    path = PROJECT_ROOT / "conventions.md"
    if not path.exists():
        return "(conventions.md not found)"
    return path.read_text(encoding="utf-8")


def build_task_message(agent_name: str, user_task: str, conventions: str) -> str:
    """Build the initial user message for the agent."""
    # Collect all existing plan files so agents can read upstream context
    existing_plans = []
    if OUTPUT_PLAN_DIR.exists():
        for f in sorted(OUTPUT_PLAN_DIR.iterdir()):
            if f.suffix == ".md" or f.suffix == ".json":
                existing_plans.append(str(f.relative_to(PROJECT_ROOT)))

    plans_hint = (
        f"The following plan files already exist and you should read them first:\n"
        + "\n".join(f"  - {p}" for p in existing_plans)
        if existing_plans
        else "No upstream plan files exist yet (you are the first agent)."
    )

    return textwrap.dedent(f"""
        ## Your Task

        You are the `{agent_name}`. Execute your full workflow now.

        ### User's Original Request
        {user_task}

        ### Shared Conventions
        (Read the full `conventions.md` file using the `read` tool for authoritative details.)

        ### Upstream Plan Files
        {plans_hint}

        ### Instructions
        1. Use the `read` tool to read `conventions.md` first.
        2. Read all upstream plan files listed above.
        3. Execute your 2-step workflow exactly as defined in your persona.
        4. Do not stop until both steps are complete.
        5. When done, output a brief summary of what you produced.
    """).strip()


def ask_user_in_terminal(agent_name: str, question: str) -> str:
    """Prompt the user in the terminal for a clarification answer."""
    print(f"\n{'='*60}")
    print(f"  CLARIFICATION REQUIRED — {agent_name}")
    print(f"{'='*60}")
    print(f"\n  {question}\n")
    answer = input("  Your answer: ").strip()
    print(f"{'='*60}\n")
    return answer


def format_tool_result(result: dict) -> str:
    """Serialize a tool result to JSON string for the LLM."""
    return json.dumps(result, indent=2, default=str)


# ---------------------------------------------------------------------------
# Core agent runner (agentic loop)
# ---------------------------------------------------------------------------


def run_agent(agent_name: str, allowed_tools: list[str], user_task: str) -> str:
    """
    Run a single agent to completion using an agentic tool-call loop.

    Returns the agent's final text response.
    """
    print(f"\n{'#'*60}")
    print(f"  RUNNING AGENT: {agent_name}")
    print(f"{'#'*60}\n")

    system_prompt = load_agent_system_prompt(agent_name)
    conventions = load_conventions()
    task_message = build_task_message(agent_name, user_task, conventions)
    tool_schemas = get_schemas(allowed_tools)

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task_message},
    ]

    max_iterations = 50  # Safety cap to prevent infinite loops
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        print(f"  [Iteration {iteration}] Calling model...")

        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=messages,
            tools=tool_schemas,
            tool_choice="auto",
        )

        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        # Append assistant message to history
        messages.append(message.model_dump(exclude_none=True))

        # If no tool calls, the agent is done
        if not message.tool_calls:
            final_text = message.content or ""
            print(f"\n  [DONE] {agent_name} finished.\n")
            print(f"  Summary:\n{textwrap.indent(final_text, '    ')}\n")
            return final_text

        # Process tool calls
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args_json = tool_call.function.arguments
            tool_call_id = tool_call.id

            print(f"  [Tool] {tool_name}({tool_args_json[:120]}{'...' if len(tool_args_json) > 120 else ''})")

            try:
                result = execute_from_json(tool_name, tool_args_json)
            except ClarificationRequired as e:
                # Pause and ask the user
                answer = ask_user_in_terminal(e.agent_name, e.question)
                result = {
                    "success": True,
                    "answer": answer,
                    "note": "User provided this clarification. Incorporate it and continue.",
                }

            tool_result_message = {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": format_tool_result(result),
            }
            messages.append(tool_result_message)

    # Safety: if we hit max iterations, return whatever we have
    last_content = next(
        (m.get("content", "") for m in reversed(messages) if m.get("role") == "assistant"),
        "[Agent did not produce a final response within the iteration limit]",
    )
    print(f"  [WARNING] {agent_name} hit max iterations ({max_iterations}). Stopping.")
    return last_content


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------


def run_pipeline(user_task: str) -> None:
    """Run all agents in sequence."""
    # Ensure output directories exist
    OUTPUT_PLAN_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_CODE_DIR.mkdir(parents=True, exist_ok=True)

    results: dict[str, str] = {}

    for agent_name, allowed_tools in PIPELINE:
        try:
            result = run_agent(agent_name, allowed_tools, user_task)
            results[agent_name] = result
        except Exception as e:
            print(f"\n  [ERROR] {agent_name} failed with exception: {e}")
            raise

    # Final summary
    print(f"\n{'='*60}")
    print("  PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"\n  Plan files:  {OUTPUT_PLAN_DIR}")
    print(f"  Code files:  {OUTPUT_CODE_DIR}")
    print("\n  Agents completed:")
    for agent_name in results:
        print(f"    ✅ {agent_name}")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the multi-agent coding pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Examples:
              python pipeline.py "Build a simple TODO app with user authentication"
              python pipeline.py --task-file task.md
        """),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "task",
        nargs="?",
        help="The coding task to execute, as a plain-text string.",
    )
    group.add_argument(
        "--task-file",
        metavar="PATH",
        help="Path to a .md or .txt file containing the task description.",
    )
    parser.add_argument(
        "--agent",
        metavar="AGENT_NAME",
        help="Run only a single agent (e.g. --agent backend_agent) instead of the full pipeline.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.task_file:
        task_path = Path(args.task_file)
        if not task_path.exists():
            sys.exit(f"ERROR: Task file not found: {task_path}")
        user_task = task_path.read_text(encoding="utf-8").strip()
    else:
        user_task = args.task.strip()

    if not user_task:
        sys.exit("ERROR: Task description is empty.")

    print(f"\n{'='*60}")
    print("  MULTI-AGENT CODING PIPELINE")
    print(f"{'='*60}")
    print(f"\n  Model  : {OPENROUTER_MODEL}")
    print(f"  Task   : {user_task[:100]}{'...' if len(user_task) > 100 else ''}")
    print()

    if args.agent:
        # Run a single agent
        matching = [(n, t) for n, t in PIPELINE if n == args.agent]
        if not matching:
            valid = [n for n, _ in PIPELINE]
            sys.exit(f"ERROR: Unknown agent '{args.agent}'. Valid agents: {valid}")
        agent_name, allowed_tools = matching[0]
        OUTPUT_PLAN_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_CODE_DIR.mkdir(parents=True, exist_ok=True)
        run_agent(agent_name, allowed_tools, user_task)
    else:
        run_pipeline(user_task)


if __name__ == "__main__":
    main()
