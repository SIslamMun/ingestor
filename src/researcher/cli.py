"""CLI for the Researcher module - Deep Research using Gemini API."""

import asyncio
import sys
from pathlib import Path

import click


@click.group()
@click.version_option(version="0.1.0", prog_name="researcher")
def cli():
    """Researcher CLI - Deep research using Gemini Deep Research Agent.

    Conduct automated multi-step research tasks and produce detailed reports.

    Requires GOOGLE_API_KEY environment variable.

    For parsing references from research output, use: parser parse-refs
    For downloading papers, use: parser download or parser batch
    """
    pass


@cli.command()
@click.argument("query", type=str)
@click.option("-o", "--output", type=click.Path(), default="./output", help="Output directory")
@click.option("--format", "output_format", type=str, default=None, help="Output format instructions")
@click.option("--no-stream", is_flag=True, help="Disable streaming (use polling)")
@click.option("--max-wait", type=int, default=3600, help="Max wait time in seconds (default: 3600)")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output with thinking steps")
def research(query: str, output: str, output_format: str | None,
             no_stream: bool, max_wait: int, verbose: bool):
    """Conduct deep research on a topic.

    QUERY is the research topic or question.

    The research agent will:
    1. Search multiple sources for information
    2. Synthesize findings into a comprehensive report
    3. Include citations with arXiv IDs and DOIs when available

    Output:
    - research_report.md: Main research report
    - research_metadata.json: Query, citations, timing info
    - thinking_steps.md: Agent reasoning (if --verbose)

    Examples:

        researcher research "What are the latest advances in quantum computing?"

        researcher research "Compare transformer architectures" --format "Include comparison table"

        researcher research "Survey of LLM agents" -o ./research --verbose

    After research, use 'parser parse-refs' to extract paper references.
    """
    from .deep_research import DeepResearcher, ResearchConfig

    async def run():
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)

        # Configure research
        config = ResearchConfig(
            output_format=output_format,
            max_wait_time=max_wait,
            enable_streaming=not no_stream,
            enable_thinking=verbose,
        )

        researcher = DeepResearcher(config=config)

        # Stream file for live output
        stream_file = output_path / "research_stream.md" if verbose else None
        if stream_file:
            stream_file.write_text("# Research Stream Log\n\n")  # Initialize with header

        # Progress callback
        def on_progress(text: str):
            if verbose:
                # Write to stream file
                if stream_file:
                    with open(stream_file, "a") as f:
                        f.write(text + "\n\n")

                # Also print to console
                if text.startswith("[Thinking]"):
                    click.echo(click.style(text, dim=True))
                else:
                    click.echo(text, nl=False)

        click.echo(f"Researching: {query[:80]}...")
        click.echo(f"Output: {output_path}")
        if stream_file:
            click.echo(f"Stream log: {stream_file}")
        click.echo()

        try:
            result = await researcher.research(query, on_progress=on_progress if verbose else None)
        except Exception as e:
            click.echo(click.style(f"Error: {e}", fg="red"), err=True)
            sys.exit(1)

        if result.succeeded:
            # Save results
            result.save(output_path / "research")

            click.echo()
            click.echo(click.style("Research completed!", fg="green"))
            click.echo(f"Duration: {result.duration_seconds:.1f}s")
            click.echo(f"Report saved to: {output_path / 'research' / 'research_report.md'}")
            if stream_file:
                click.echo(f"Stream log saved to: {stream_file}")

            # Print summary
            if verbose:
                click.echo()
                click.echo(click.style("Report Preview:", bold=True))
                preview = result.report[:500] + "..." if len(result.report) > 500 else result.report
                click.echo(preview)

            # Hint about next steps
            click.echo()
            click.echo(click.style("Next steps:", dim=True))
            click.echo(click.style(f"  parser parse-refs {output_path / 'research' / 'research_report.md'}", dim=True))
        else:
            click.echo()
            click.echo(click.style(f"Research failed: {result.error}", fg="red"), err=True)
            sys.exit(1)

    asyncio.run(run())


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
