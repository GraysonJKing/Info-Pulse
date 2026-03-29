"""Agent definitions for each pipeline stage.

Each function returns a ClaudeAgentOptions configured with the
appropriate model, tools, and system prompt for its role.
"""

from claude_agent_sdk import ClaudeAgentOptions

from config import HAIKU_MODEL, PROMPTS_DIR, SONNET_MODEL
from utils.io import read_text


def triage_options() -> ClaudeAgentOptions:
    """Options for triage agents (Step 2). Haiku, no tools."""
    return ClaudeAgentOptions(
        model=HAIKU_MODEL,
        allowed_tools=[],
        system_prompt=read_text(PROMPTS_DIR / "triage.md"),
        max_turns=1,
    )


def analyst_options() -> ClaudeAgentOptions:
    """Options for analyst agents (Step 3). Sonnet with web search."""
    return ClaudeAgentOptions(
        model=SONNET_MODEL,
        allowed_tools=["WebSearch", "WebFetch"],
        system_prompt=read_text(PROMPTS_DIR / "analysis.md"),
        max_turns=10,
    )


def memory_options() -> ClaudeAgentOptions:
    """Options for the memory curator agent (Step 4). Haiku, no tools."""
    return ClaudeAgentOptions(
        model=HAIKU_MODEL,
        allowed_tools=[],
        system_prompt=read_text(PROMPTS_DIR / "memory.md"),
        max_turns=1,
    )


def personalise_options() -> ClaudeAgentOptions:
    """Options for personaliser agents (Step 5). Haiku, no tools."""
    return ClaudeAgentOptions(
        model=HAIKU_MODEL,
        allowed_tools=[],
        system_prompt=read_text(PROMPTS_DIR / "personalise.md"),
        max_turns=1,
    )
