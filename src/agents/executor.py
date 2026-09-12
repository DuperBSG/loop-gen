from state import AgentState

from llm import complete

SYSTEM = """You are an executor. Carry out the plan and produce the deliverable.
If the goal cannot be physically produced in text (e.g. video, audio), produce
the most complete artifact you can: script, shot list, prompts, and production notes.
Be specific and concise. Preserve every required deliverable, constraint, and detail, but avoid repetition.
Do not recap the plan. Do not ask questions."""


def execute(state: AgentState, *, model: str | None = None, dry_run: bool = False) -> str:
    if dry_run:
        return (
            f"Execute this plan:\n\n{state.plan}\n\n"
            f"Original goal:\n{state.goal}"
        )

    user = f"""Goal:
{state.goal}

Plan:
{state.plan}

Guidance:
{state.guidance or "(none)"}
"""
    return complete(SYSTEM, user, model=model, temperature=0.5)
