"""
Tool: clarify_or_ask_user
Pauses the agent's execution and asks the user a clarifying question.
Used when requirements are ambiguous and the agent cannot safely proceed without input.

In the pipeline context, this writes a question to a shared file and raises a
`ClarificationRequired` exception that the pipeline runner catches and presents
to the user. The runner resumes the agent once the user provides an answer.
"""

import json
import os
from datetime import datetime, timezone


# Path where pending clarification questions are stored
_CLARIFICATIONS_FILE = os.path.join(
    os.path.dirname(__file__), "..", "output", "clarifications.json"
)


class ClarificationRequired(Exception):
    """Raised when an agent needs user input before continuing."""
    def __init__(self, agent_name: str, question: str):
        self.agent_name = agent_name
        self.question = question
        super().__init__(f"[{agent_name}] Clarification required: {question}")


def clarify_or_ask_user(agent_name: str, question: str) -> dict:
    """
    Ask the user a clarifying question and pause execution.

    This function:
    1. Appends the question to `output/clarifications.json` with metadata.
    2. Raises `ClarificationRequired` for the pipeline runner to catch.

    The pipeline runner is responsible for presenting the question to the user,
    collecting the response, and re-invoking the agent with the answer injected
    into its context.

    Args:
        agent_name: Name of the agent asking the question (e.g., "requirements_collection_agent").
        question:   The question to ask the user.

    Returns:
        This function always raises; the return value is for schema documentation only.
        Returns a dict with keys:
            - agent_name (str)
            - question (str)
            - timestamp (str)
    """
    record = {
        "agent_name": agent_name,
        "question": question,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "answered": False,
        "answer": None,
    }

    # Persist the question so the pipeline runner can display it
    os.makedirs(os.path.dirname(_CLARIFICATIONS_FILE), exist_ok=True)
    existing = []
    if os.path.exists(_CLARIFICATIONS_FILE):
        try:
            with open(_CLARIFICATIONS_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []
    existing.append(record)
    with open(_CLARIFICATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

    raise ClarificationRequired(agent_name=agent_name, question=question)


# JSON schema for LLM function-calling
SCHEMA = {
    "name": "clarify_or_ask_user",
    "description": (
        "Ask the user a clarifying question when requirements are ambiguous and you cannot "
        "safely proceed without more information. This PAUSES execution. "
        "Use sparingly -- only when truly blocked. Do NOT ask for information you can infer "
        "from the conventions file or existing plan files."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "agent_name": {
                "type": "string",
                "description": "Your own agent name, e.g. 'backend_agent'.",
            },
            "question": {
                "type": "string",
                "description": "The specific, concise question you need answered to proceed.",
            },
        },
        "required": ["agent_name", "question"],
    },
}
