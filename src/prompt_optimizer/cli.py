"""CLI interface for Prompt Optimizer."""

import argparse
import json
import sys

import questionary
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from prompt_optimizer.azure_client import AzureClient
from prompt_optimizer.config import load_config
from prompt_optimizer.history import HistoryDB
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


def _get_client_and_optimizer() -> tuple[AzureClient, Optimizer]:
    """Load config and create client + optimizer."""
    try:
        cfg = load_config()
    except ValueError as e:
        console.print(f"[bold red]Configuration error:[/bold red] {e}")
        sys.exit(1)

    client = AzureClient(cfg.azure)
    optimizer = Optimizer(client, max_questions=cfg.app.max_follow_up_questions)
    return client, optimizer


# ── Interactive Mode ─────────────────────────────────────────────────────────

def cmd_interactive() -> None:
    """Interactive Q&A prompt optimization."""
    console.print("\n[bold cyan]🚀 Prompt Optimizer — Interactive Mode[/bold cyan]\n")

    raw_prompt = questionary.text(
        "Enter your rough prompt idea (press Enter to submit):",
    ).ask()

    if not raw_prompt:
        console.print("[yellow]No input provided. Exiting.[/yellow]")
        return

    _, optimizer = _get_client_and_optimizer()

    console.print("[bold blue]Analyzing your prompt...[/bold blue]")
    try:
        analysis = optimizer.analyze(raw_prompt)
    except Exception as e:
        console.print(f"[bold red]Error calling Azure OpenAI:[/bold red] {e}")
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
        _save_to_history(raw_prompt, result["improved_prompt"], result.get("new_scores", {}), "interactive")
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

    _save_to_history(raw_prompt, optimized, result.get("scores", {}), "interactive")

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

def cmd_analyze() -> None:
    """One-shot prompt analysis and improvement."""
    console.print("\n[bold cyan]🔍 Prompt Optimizer — One-Shot Analysis[/bold cyan]\n")

    raw_prompt = questionary.text(
        "Paste your prompt to optimize (press Enter to submit):",
    ).ask()

    if not raw_prompt:
        console.print("[yellow]No input provided. Exiting.[/yellow]")
        return

    _, optimizer = _get_client_and_optimizer()

    console.print("[bold blue]Analyzing and optimizing...[/bold blue]")
    try:
        result = optimizer.one_shot(raw_prompt)
    except Exception as e:
        console.print(f"[bold red]Error calling Azure OpenAI:[/bold red] {e}")
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
        _print_scores(result["new_scores"], "Improved Scores (self-reported)")

    # Show independently verified scores
    if result.get("verified_scores"):
        _print_scores(result["verified_scores"], "Verified Scores (independent re-analysis)")

    _save_to_history(raw_prompt, result["improved_prompt"], result.get("verified_scores") or result.get("new_scores", {}), "oneshot")


# ── History ──────────────────────────────────────────────────────────────────

def cmd_history(args: argparse.Namespace) -> None:
    """Manage prompt history."""
    db = HistoryDB()

    if args.history_action == "list":
        entries = db.list_all(limit=args.limit if hasattr(args, "limit") else 20)
        if not entries:
            console.print("[yellow]No history entries found.[/yellow]")
            return
        table = Table(title="Prompt History", show_header=True, header_style="bold cyan")
        table.add_column("ID", style="dim")
        table.add_column("Mode")
        table.add_column("Original (preview)", max_width=50)
        table.add_column("Tags")
        table.add_column("Created")
        for entry in entries:
            preview = entry["original"][:47] + "..." if len(entry["original"]) > 50 else entry["original"]
            table.add_row(
                entry["id"],
                entry["mode"],
                preview,
                entry["tags"],
                entry["created_at"][:19],
            )
        console.print(table)

    elif args.history_action == "view":
        entry = db.get(args.id)
        if not entry:
            console.print(f"[red]Entry '{args.id}' not found.[/red]")
            return
        console.print(Panel(entry["original"], title="[bold]Original Prompt[/bold]"))
        _print_prompt(entry["optimized"])
        if entry["scores"] and entry["scores"] != "{}":
            _print_scores(json.loads(entry["scores"]))

    elif args.history_action == "search":
        entries = db.search(args.query)
        if not entries:
            console.print(f"[yellow]No results for '{args.query}'.[/yellow]")
            return
        for entry in entries:
            console.print(f"[bold]{entry['id']}[/bold] ({entry['mode']}) — {entry['original'][:60]}...")

    elif args.history_action == "delete":
        if db.delete(args.id):
            console.print(f"[green]Deleted entry '{args.id}'.[/green]")
        else:
            console.print(f"[red]Entry '{args.id}' not found.[/red]")

    db.close()


# ── History saving helper ────────────────────────────────────────────────────

def _save_to_history(original: str, optimized: str, scores: dict, mode: str) -> None:
    """Silently save a prompt pair to history."""
    try:
        db = HistoryDB()
        db.save(
            original=original,
            optimized=optimized,
            scores=json.dumps(scores),
            mode=mode,
        )
        db.close()
        console.print("[dim]✓ Saved to history[/dim]")
    except Exception:
        pass  # Don't interrupt the user for history failures


# ── CLI Entry Point ──────────────────────────────────────────────────────────

def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="prompt-optimizer",
        description="Transform rough ideas into well-structured AI prompts.",
    )
    subparsers = parser.add_subparsers(dest="command")

    # optimize (interactive)
    subparsers.add_parser("optimize", help="Interactive Q&A prompt optimization")

    # analyze (one-shot)
    subparsers.add_parser("analyze", help="One-shot prompt analysis and improvement")

    # history
    history_parser = subparsers.add_parser("history", help="Manage prompt history")
    history_sub = history_parser.add_subparsers(dest="history_action")

    list_parser = history_sub.add_parser("list", help="List recent prompts")
    list_parser.add_argument("-n", "--limit", type=int, default=20, help="Number of entries")

    view_parser = history_sub.add_parser("view", help="View a specific prompt")
    view_parser.add_argument("id", help="Prompt history ID")

    search_parser = history_sub.add_parser("search", help="Search prompt history")
    search_parser.add_argument("query", help="Search query")

    delete_parser = history_sub.add_parser("delete", help="Delete a history entry")
    delete_parser.add_argument("id", help="Prompt history ID")

    args = parser.parse_args()

    if args.command == "optimize" or args.command is None:
        cmd_interactive()
    elif args.command == "analyze":
        cmd_analyze()
    elif args.command == "history":
        if not args.history_action:
            cmd_history(argparse.Namespace(history_action="list", limit=20))
        else:
            cmd_history(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
