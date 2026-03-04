"""CLI interface for Prompt Optimizer."""

import argparse
import sys

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from prompt_optimizer.config import load_config
from prompt_optimizer.optimizer import Optimizer

console = Console()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _print_scores(scores: dict, title: str = "Scores") -> None:
    """Render a score table."""
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Dimension", style="bold")
    table.add_column("Score", justify="center")
    for dim, val in scores.items():
        color = "green" if val >= 7 else "yellow" if val >= 4 else "red"
        table.add_row(dim.capitalize(), f"[{color}]{val}/10[/{color}]")
    console.print(table)


def _print_prompt(prompt_text: str, title: str = "Optimized Prompt") -> None:
    """Display a prompt in a panel."""
    console.print(Panel(prompt_text, title=f"[bold green]{title}[/bold green]", border_style="green"))


def _get_client_and_optimizer(args: argparse.Namespace | None = None) -> Optimizer:
    """Load config and create the appropriate client + optimizer."""
    try:
        cfg = load_config()
    except ValueError as e:
        console.print(f"[bold red]Configuration error:[/bold red] {e}")
        sys.exit(1)

    backend = getattr(args, "backend", None) or cfg.app.backend
    model = getattr(args, "model", None) or cfg.app.local_model

    if backend == "local":
        from prompt_optimizer.local_client import LocalClient
        client = LocalClient(model=model)
    else:
        from prompt_optimizer.azure_client import AzureClient
        client = AzureClient(cfg.azure)

    return Optimizer(client, max_questions=cfg.app.max_follow_up_questions)


# ── Interactive Mode ─────────────────────────────────────────────────────────

def cmd_interactive(args: argparse.Namespace | None = None) -> None:
    """Interactive Q&A prompt optimization."""
    console.print("\n[bold cyan]🚀 Prompt Optimizer — Interactive Mode[/bold cyan]\n")

    raw_prompt = questionary.text(
        "Enter your rough prompt idea (press Enter to submit):",
    ).ask()

    if not raw_prompt:
        console.print("[yellow]No input provided. Exiting.[/yellow]")
        return

    optimizer = _get_client_and_optimizer(args)

    console.print("[bold blue]Analyzing your prompt...[/bold blue]")
    try:
        analysis = optimizer.analyze(raw_prompt)
    except Exception as e:
        console.print(f"[bold red]Error during analysis:[/bold red] {e}")
        return

    # Show initial analysis
    console.print("\n[bold]Initial Analysis[/bold]")
    console.print(f"  Summary: {analysis.get('summary', 'N/A')}")
    if analysis.get("gaps"):
        console.print(f"  [yellow]Gaps found:[/yellow] {', '.join(analysis['gaps'])}")
    if analysis.get("scores"):
        _print_scores(analysis["scores"], "Current Scores")

    # Generate and ask follow-up questions
    console.print("[bold blue]Generating follow-up questions...[/bold blue]")
    try:
        questions = optimizer.get_questions(raw_prompt, analysis)
    except Exception as e:
        console.print(f"[bold red]Error generating questions:[/bold red] {e}")
        return

    if not questions:
        console.print("[green]Your prompt looks solid! Running one-shot improvement...[/green]")
        with console.status("[bold blue]Optimizing..."):
            try:
                result = optimizer.one_shot(raw_prompt)
            except Exception as e:
                console.print(f"[bold red]Error optimizing:[/bold red] {e}")
                return
        _print_prompt(result["improved_prompt"])
        return

    console.print(f"\n[bold]I have {len(questions)} question(s) to help refine your prompt:[/bold]\n")

    qa_pairs: list[dict[str, str]] = []
    for q in questions:
        question_text = q["question"]
        suggestions = q.get("suggestions", [])

        if suggestions:
            choices = suggestions + ["(custom answer)"]
            answer = questionary.select(
                question_text,
                choices=choices,
            ).ask()
            if answer == "(custom answer)":
                answer = questionary.text("Your answer:").ask() or ""
        else:
            answer = questionary.text(question_text).ask() or ""

        qa_pairs.append({"question": question_text, "answer": answer})

    # Assemble final prompt
    console.print("[bold blue]Assembling optimized prompt...[/bold blue]")
    try:
        result = optimizer.assemble(raw_prompt, qa_pairs)
    except Exception as e:
        console.print(f"[bold red]Error assembling prompt:[/bold red] {e}")
        return

    optimized = result.get("optimized_prompt", "")
    _print_prompt(optimized)

    if result.get("scores"):
        _print_scores(result["scores"], "Final Scores")

    # Copy option
    if questionary.confirm("Copy optimized prompt to clipboard?", default=True).ask():
        try:
            import subprocess
            proc = subprocess.Popen(["clip.exe"], stdin=subprocess.PIPE)
            proc.communicate(optimized.encode("utf-8"))
            console.print("[green]✓ Copied to clipboard![/green]")
        except Exception:
            console.print("[yellow]Could not copy to clipboard. Please copy manually.[/yellow]")


# ── One-Shot Mode ────────────────────────────────────────────────────────────

def cmd_analyze(args: argparse.Namespace | None = None) -> None:
    """One-shot prompt analysis and improvement."""
    console.print("\n[bold cyan]🔍 Prompt Optimizer — One-Shot Analysis[/bold cyan]\n")

    raw_prompt = questionary.text(
        "Paste your prompt to optimize (press Enter to submit):",
    ).ask()

    if not raw_prompt:
        console.print("[yellow]No input provided. Exiting.[/yellow]")
        return

    optimizer = _get_client_and_optimizer(args)

    console.print("[bold blue]Analyzing and optimizing...[/bold blue]")
    try:
        result = optimizer.one_shot(raw_prompt)
    except Exception as e:
        console.print(f"[bold red]Error during analysis:[/bold red] {e}")
        return

    # Show original scores
    if result.get("original_scores"):
        _print_scores(result["original_scores"], "Original Scores")

    # Show changes
    if result.get("changes_made"):
        console.print("\n[bold]Changes Made:[/bold]")
        for change in result["changes_made"]:
            console.print(f"  [green]✓[/green] {change}")

    # Show improved prompt
    console.print()
    _print_prompt(result["improved_prompt"])

    # Show new scores
    if result.get("new_scores"):
        _print_scores(result["new_scores"], "Improved Scores")


# ── CLI Entry Point ──────────────────────────────────────────────────────────

def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="prompt-optimizer",
        description="Transform rough ideas into well-structured AI prompts.",
    )
    parser.add_argument(
        "-b", "--backend",
        choices=["azure", "local"],
        default=None,
        help="LLM backend to use (default: from config or 'azure')",
    )
    parser.add_argument(
        "-m", "--model",
        default=None,
        help="Model alias for local backend (e.g., phi-4-mini-reasoning)",
    )

    subparsers = parser.add_subparsers(dest="command")

    # optimize (interactive)
    subparsers.add_parser("optimize", help="Interactive Q&A prompt optimization")

    # analyze (one-shot)
    subparsers.add_parser("analyze", help="One-shot prompt analysis and improvement")

    args = parser.parse_args()

    # Show banner with backend info
    backend = args.backend or "azure"
    if backend == "local":
        try:
            cfg = load_config()
        except ValueError:
            cfg = None
        model = args.model or (cfg.app.local_model if cfg else "unknown")
        console.print(f"[dim]Backend: Foundry Local ({model})[/dim]")
    else:
        console.print("[dim]Backend: Azure OpenAI[/dim]")

    if args.command == "optimize" or args.command is None:
        cmd_interactive(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
