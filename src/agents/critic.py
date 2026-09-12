import re

from state import AgentState

from llm import complete

SYSTEM = """You are a harsh but fair critic.
Evaluate whether the output fully satisfies the goal.
List every important success, missing requirement, and concrete change as concise bullets; do not omit points.
End with exactly one of these lines and nothing after it:
VERDICT: PASS
VERDICT: FAIL
PASS only if the output is complete enough to ship for the stated goal."""


def parse_verdict(text: str) -> bool:
    for line in reversed(text.strip().splitlines()):
        stripped = line.strip()
        match = re.match(r"(?i)^verdict:\s*(pass|fail)\s*$", stripped)
        if match:
            return match.group(1).lower() == "pass"
    return False


def critique(
    state: AgentState, *, model: str | None = None, dry_run: bool = False
) -> str:
    if dry_run:
        return (
            "Critically evaluate this output:\n\n"
            f"Goal:\n{state.goal}\n\n"
            f"Output:\n{state.output}\n\n"
            "Identify what should be improved.\n"
            "VERDICT: FAIL"
        )

    image_paths = [
        path for path in state.artifacts
        if path.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    ]
    user = f"""Goal:
{state.goal}

Plan:
{state.plan}

Output:
{state.output}

Generated media:
{len(state.artifacts)} artifact(s) were generated. {len(image_paths)} image(s) are attached to this message; inspect them directly and assess whether they satisfy the goal. Video artifacts are saved locally but are not sent as raw video.
"""
    return complete(SYSTEM, user, model=model, temperature=0.2, image_paths=image_paths)
