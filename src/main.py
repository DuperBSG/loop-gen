from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from rich.align import Align
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.rule import Rule
from rich.text import Text

from agents.critic import critique, parse_verdict
from comfy import ComfyClient, load_api_workflow, set_prompt
from agents.executor import execute
from agents.improver import improve
from agents.planner import plan
from config import DEFAULT_MODEL
from llm import name_image
from state import AgentState

MAX_ITERATIONS = 10
RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"
console = Console()


def compact_text(content: str) -> str:
    """Normalize spacing without dropping any content or points."""
    return "\n".join(line.strip() for line in content.splitlines() if line.strip())


def render_markdown_panel(content: str, title: str, border_style: str) -> Panel:
    body = Markdown(compact_text(content) or "_No content returned._")
    return Panel(
        body,
        title=f"[bold]{title}[/bold]",
        title_align="left",
        border_style=border_style,
        padding=(1, 2),
    )


def run(
    goal: str,
    *,
    max_iterations: int = MAX_ITERATIONS,
    model: str | None = None,
    dry_run: bool = False,
    comfy_workflow: Path | None = None,
    comfy_url: str = "http://127.0.0.1:8188",
    comfy_prompt_node: str = "",
    comfy_prompt_field: str = "text",
) -> AgentState:
    state = AgentState(goal=goal)
    kwargs = {"model": model, "dry_run": dry_run}
    comfy_template = load_api_workflow(comfy_workflow) if comfy_workflow else None
    if comfy_template is not None and not comfy_prompt_node:
        raise ValueError("--comfy-prompt-node is required with --comfy-workflow")

    console.print(
        Panel(
            Group(
                Align.center(Text("AGENT LOOP", style="bold bright_cyan")),
                Align.center(Text("plan  →  execute  →  critique  →  improve", style="dim")),
            ),
            border_style="bright_cyan",
            padding=(1, 2),
        )
    )
    console.print(Padding(f"[dim]Goal:[/dim] [bold]{goal}[/bold]", (0, 0, 1, 0)))

    while state.iteration < max_iterations:
        iteration = state.iteration + 1
        console.print(Rule(f"[bold cyan]Iteration {iteration}/{max_iterations}[/bold cyan]"))
        with Progress(
            SpinnerColumn(style="bright_magenta"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=28, complete_style="bright_green"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Planning", total=4)
            state.plan = plan(state, **kwargs)
            progress.advance(task)

            progress.update(task, description="Executing")
            state.output = execute(state, **kwargs)
            progress.advance(task)

            if comfy_template is not None:
                progress.update(task, description="Rendering in ComfyUI")
                workflow = set_prompt(comfy_template, comfy_prompt_node, comfy_prompt_field, state.output)
                output_dir = RUNS_DIR / "comfy" / f"iteration-{iteration}"
                client = ComfyClient(comfy_url)
                media = client.wait_for_media(client.queue(workflow), output_dir)
                named_media = []
                for item in media:
                    if item.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                        media_name = name_image(str(item), goal, model=model)
                    else:
                        media_name = "generated-video"
                    destination = item.with_name(f"{media_name}{item.suffix}")
                    counter = 2
                    while destination.exists():
                        destination = item.with_name(f"{media_name}-{counter}{item.suffix}")
                        counter += 1
                    item.rename(destination)
                    named_media.append(destination)
                state.artifacts.extend(str(path) for path in named_media)
                progress.update(task, description=f"Critiquing ({len(named_media)} media generated)")

            progress.update(task, description="Critiquing")
            state.critique = critique(state, **kwargs)
            state.passed = parse_verdict(state.critique)
            progress.advance(task)

            if not state.passed:
                progress.update(task, description="Improving")
                state.guidance = improve(state, **kwargs)
                progress.advance(task)
            else:
                progress.update(task, description="Passed")
                progress.update(task, completed=4)

        console.print(render_markdown_panel(state.plan, "Plan", "bright_blue"))
        console.print(render_markdown_panel(state.output, "Output", "bright_green"))
        console.print(render_markdown_panel(state.critique, "Critique", "bright_yellow"))
        if state.artifacts:
            names = ", ".join(Path(path).name for path in state.artifacts)
            console.print(f"[dim]Generated media: {names}[/dim]")

        if not state.passed:
            console.print(
                render_markdown_panel(
                    state.guidance, "Next iteration", "bright_magenta"
                )
            )

        state.history.append(state.snapshot())

        if state.passed:
            console.print("[bold green]Passed.[/bold green]")
            break

        state.iteration += 1
    else:
        console.print(
            f"[bold yellow]Stopped after {max_iterations} iterations without PASS.[/bold yellow]"
        )

    return state


def save_run(state: AgentState, model: str, dry_run: bool) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = RUNS_DIR / f"{stamp}.json"
    path.write_text(
        json.dumps(
            {
                "goal": state.goal,
                "model": model,
                "dry_run": dry_run,
                "passed": state.passed,
                "iterations": state.iteration + 1,
                "final_output": state.output,
                "history": state.history,
                "artifacts": state.artifacts,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def cli(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run a plan-execute-critique-improve loop.")
    parser.add_argument(
        "goal",
        nargs="?",
        default="Create a 30 second liminal-space video",
        help="What the loop should achieve",
    )
    parser.add_argument("-n", "--max-iterations", type=int, default=MAX_ITERATIONS)
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip LLM calls and print the prompt stubs instead",
    )
    parser.add_argument("--comfy-workflow", type=Path, help="ComfyUI workflow exported with Save (API Format)")
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--comfy-prompt-node", help="Node id containing the prompt input")
    parser.add_argument("--comfy-prompt-field", default="text")
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not write a JSON run record under runs/",
    )
    args = parser.parse_args(argv)

    state = run(
        args.goal,
        max_iterations=args.max_iterations,
        model=args.model,
        dry_run=args.dry_run,
        comfy_workflow=args.comfy_workflow,
        comfy_url=args.comfy_url,
        comfy_prompt_node=args.comfy_prompt_node or "",
        comfy_prompt_field=args.comfy_prompt_field,
    )
    if not args.no_save:
        path = save_run(state, args.model, args.dry_run)
        console.print(f"\n[dim]Saved run to {path}[/dim]")


if __name__ == "__main__":
    cli(sys.argv[1:])
