from state import AgentState

from llm import complete

SYSTEM = """You turn a critique into next-iteration guidance.
Write 3-7 specific, concise instructions covering every required change the planner and executor must follow next.
Do not rewrite the full deliverable. Do not include a verdict."""


def improve(state: AgentState, *, model: str | None = None, dry_run: bool = False) -> str:
    if dry_run:
        return (
            "Based on the following critique:\n\n"
            f"{state.critique}\n\n"
            "Determine what should change in the next iteration."
        )

    user = f"""Goal:
{state.goal}

Critique:
{state.critique}

Current output:
{state.output}
"""
    return complete(SYSTEM, user, model=model, temperature=0.3)
