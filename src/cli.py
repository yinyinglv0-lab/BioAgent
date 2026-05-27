"""BioAgent CLI - Command-line interface for the bioinformatics agent."""

import argparse
import sys
import io
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from .agent import BioAgent
from .config import config

# Force UTF-8 on Windows to avoid GBK encoding errors with emoji
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

console = Console()


def banner():
    """Display startup banner."""
    console.print(
        Panel.fit(
            "[bold cyan]BioAgent[/bold cyan] [dim]v{version}[/dim]\n"
            "[dim]AI-Powered Bioinformatics Research Assistant[/dim]\n"
            "[dim]Powered by Claude API | {model}[/dim]".format(
                version=config.VERSION, model=config.AGENT_MODEL
            ),
            border_style="cyan",
        )
    )


def interactive_mode():
    """Run BioAgent in interactive CLI mode."""
    banner()
    console.print("[dim]Type 'help' for commands, 'reset' to clear context, 'quit' to exit[/dim]\n")

    agent = BioAgent()

    while True:
        try:
            user_input = console.input("[bold green]You >[/bold green] ").strip()

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                console.print("[dim]Goodbye![/dim]")
                break
            if user_input.lower() == "help":
                show_help()
                continue
            if user_input.lower() == "reset":
                agent.reset()
                console.print("[yellow]Context cleared.[/yellow]")
                continue

            with console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
                response = agent.chat(user_input)

            console.print(
                Panel(Markdown(response), title="BioAgent", border_style="cyan")
            )

        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted. Type 'quit' to exit.[/dim]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


def single_query_mode(query: str):
    """Run a single query and exit."""
    agent = BioAgent()
    with console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
        response = agent.chat(query)
    console.print(Markdown(response))


def pipeline_mode(input_file: str, output_file: str | None = None):
    """Run a batch research pipeline from a file of questions."""
    agent = BioAgent()

    with open(input_file, encoding="utf-8") as f:
        questions = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    results = []
    for i, question in enumerate(questions, 1):
        console.print(f"[cyan]Processing [{i}/{len(questions)}]: {question[:80]}...[/cyan]")
        answer = agent.run_pipeline(question)
        results.append(f"## Q{i}: {question}\n\n{answer}\n\n---\n")
        agent.reset()

    output = "\n".join(results)
    if output_file:
        Path(output_file).write_text(output, encoding="utf-8")
        console.print(f"[green]Results saved to {output_file}[/green]")
    else:
        console.print(Markdown(output))


def show_help():
    """Display help information."""
    table = Table(title="BioAgent Commands & Capabilities")
    table.add_column("Command / Feature", style="cyan")
    table.add_column("Description")

    table.add_row("Disease queries", "Query disease info, associated genes, statistics")
    table.add_row("Gene queries", "Gene function, expression, disease associations")
    table.add_row("PDF analysis", "Read and summarize scientific papers")
    table.add_row("Differential expression", "Find DEGs with custom thresholds")
    table.add_row("Survival analysis", "Kaplan-Meier curves and statistics")
    table.add_row("Literature search", "Search PubMed for relevant papers")
    table.add_row("Enrichment analysis", "GO/KEGG enrichment for gene sets")
    table.add_row("'reset'", "Clear conversation context")
    table.add_row("'quit'", "Exit BioAgent")

    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="BioAgent - AI Bioinformatics Research Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  bioagent                              # Interactive mode
  bioagent -q "Analyze TP53 in lung cancer"
  bioagent -p questions.txt -o report.md
        """,
    )
    parser.add_argument("-q", "--query", help="Single query mode")
    parser.add_argument("-p", "--pipeline", help="Batch pipeline: input file with questions")
    parser.add_argument("-o", "--output", help="Output file for pipeline results")
    parser.add_argument("--web", action="store_true", help="Start web UI")
    parser.add_argument("--port", type=int, default=8000, help="Web UI port (default: 8000)")
    args = parser.parse_args()

    config.check()

    if args.web:
        from .web import start_server
        start_server(port=args.port)
    elif args.query:
        single_query_mode(args.query)
    elif args.pipeline:
        pipeline_mode(args.pipeline, args.output)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
