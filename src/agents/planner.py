from state import AgentState

from llm import complete

SYSTEM = """You are a planner for an iterative agent loop.
Produce a concrete, numbered plan for the given goal.
Use prior critique and guidance to correct course.
Return only a concise numbered plan; preserve every required task and constraint.
Do not execute the plan or add a preamble."""


def plan(state: AgentState, *, model: str | None = None, dry_run: bool = False) -> str:
    if dry_run:
        return (
            f"Create a plan for achieving this goal:\n\n{state.goal}\n\n"
            f"Previous feedback:\n{state.critique or '(none)'}\n"
            f"Guidance:\n{state.guidance or '(none)'}"
        )

    user = f"""Goal:
{state.goal}

Guidance from last iteration:
{state.guidance or "(first iteration — none yet)"}

Latest critique:
{state.critique or "(none)"}

Recent history:
{state.recent_history()}
"""
    return complete(SYSTEM, user, model=model, temperature=0.3)
