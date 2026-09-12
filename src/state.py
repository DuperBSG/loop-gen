from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:
    goal: str
    iteration: int = 0
    plan: str = ""
    output: str = ""
    critique: str = ""
    guidance: str = ""
    passed: bool = False
    history: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)

    def snapshot(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "plan": self.plan,
            "output": self.output,
            "critique": self.critique,
            "guidance": self.guidance,
            "passed": self.passed,
            "artifacts": list(self.artifacts),
        }

    def recent_history(self, n: int = 3) -> str:
        if not self.history:
            return "(none)"
        chunks = []
        for item in self.history[-n:]:
            chunks.append(
                f"## Iteration {item['iteration']}\n"
                f"Plan:\n{item['plan']}\n\n"
                f"Output:\n{item['output']}\n\n"
                f"Critique:\n{item['critique']}\n"
            )
        return "\n".join(chunks)
