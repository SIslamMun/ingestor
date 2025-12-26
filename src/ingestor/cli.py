"""Command-line interface for ingestor."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from . import __version__
from .types import IngestConfig


# Use ASCII-safe spinner on Windows to avoid encoding issues
_IS_WINDOWS = sys.platform == "win32"
_SPINNER = "line" if _IS_WINDOWS else "dots"  # "line" uses ASCII: -\|/

console = Console(force_terminal=not _IS_WINDOWS)


def create_config(ctx: click.Context) -> IngestConfig:
    """Create IngestConfig from CLI context."""
    params = ctx.params
    return IngestConfig(
        output_dir=Path(params.get("output", "./output")),
        keep_raw_images=params.get("keep_raw", False),
        target_image_format=params.get("img_to", "png"),
        generate_metadata=params.get("metadata", False),
        verbose=params.get("verbose", False),
        describe_images=params.get("describe", False),
        use_agent=params.get("agent", False),
        crawl_strategy=params.get("strategy", "bfs"),
        crawl_max_depth=params.get("max_depth", 2),
        crawl_max_pages=params.get("max_pages", 50),
        youtube_captions=params.get("captions", "auto"),
        youtube_playlist=params.get("playlist", False),
        whisper_model=params.get("whisper_model", "turbo"),
        ollama_host=params.get("ollama_host", "http://localhost:11434"),
        vlm_model=params.get("vlm_model", "llava:7b"),
    )


@click.group()
@click.version_option(version=__version__)
def main():
    """Ingestor - Comprehensive media-to-markdown ingestion for LLM RAG."""
    pass


@main.command()
@click.argument("input", type=str)
@click.option("-o", "--output", type=click.Path(), default="./output", help="Output directory")
@click.option("--keep-raw", is_flag=True, help="Keep original image formats (don't convert to PNG)")
@click.option("--img-to", type=str, default="png", help="Target image format (default: png)")
@click.option("--metadata", is_flag=True, help="Generate JSON metadata files")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.option("--describe", is_flag=True, help="Generate VLM descriptions for images (requires Ollama)")
@click.option("--agent", is_flag=True, help="Run Claude agent for cleanup (requires Claude Code)")
@click.option("--whisper-model", type=str, default="turbo", help="Whisper model for audio (default: turbo)")
@click.option("--ollama-host", type=str, default="http://localhost:11434", help="Ollama server URL")
@click.option("--vlm-model", type=str, default="llava:7b", help="VLM model for image descriptions")
@click.pass_context
def ingest(ctx: click.Context, input: str, **kwargs):
    """Ingest a single file or URL.

    INPUT can be a file path or URL (including YouTube URLs).
    """
    config = create_config(ctx)

    async def run():
        from .core import ExtractorRegistry, Router
        from .output.writer import OutputWriter

        # Initialize registry with available extractors
        registry = _create_registry()
        router = Router(registry, config)
        writer = OutputWriter(config)

        # Check if we can process this input
        if not router.can_process(input):
            media_type = router.detect_type(input)
            console.print(f"[red]Error:[/red] No extractor available for {input}")
            console.print(f"Detected type: {media_type.value}")
            console.print("\nMake sure you have installed the required dependencies:")
            console.print(f"  pip install ingestor[{media_type.value}]")
            raise SystemExit(1)

        with Progress(
            SpinnerColumn(spinner_name=_SPINNER),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Processing {input}...", total=None)

            try:
                result = await router.process(input)
                progress.update(task, description="Writing output...")
                output_path = await writer.write(result)
                progress.update(task, completed=True, description="Done!")

                console.print(f"\n[green]Success![/green] Output written to: {output_path}")
                if result.has_images:
                    console.print(f"  Images: {result.image_count}")

            except Exception as e:
                progress.stop()
                console.print(f"[red]Error:[/red] {e}")
                if config.verbose:
                    console.print_exception()
                raise SystemExit(1)

    asyncio.run(run())


@main.command()
@click.argument("folder", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), default="./output", help="Output directory")
@click.option("--keep-raw", is_flag=True, help="Keep original image formats")
@click.option("--img-to", type=str, default="png", help="Target image format")
@click.option("--metadata", is_flag=True, help="Generate JSON metadata files")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.option("--describe", is_flag=True, help="Generate VLM descriptions")
@click.option("--agent", is_flag=True, help="Run Claude agent for cleanup")
@click.option("--recursive/--no-recursive", default=True, help="Process subdirectories")
@click.option("--concurrency", type=int, default=5, help="Max concurrent extractions")
@click.pass_context
def batch(ctx: click.Context, folder: str, recursive: bool, concurrency: int, **kwargs):
    """Process all supported files in a folder.

    Also processes .url files containing URLs to crawl.
    """
    config = create_config(ctx)

    async def run():
        from .core import ExtractorRegistry, Router
        from .output.writer import OutputWriter

        registry = _create_registry()
        router = Router(registry, config)
        writer = OutputWriter(config)

        console.print(f"Processing folder: {folder}")
        console.print(f"Recursive: {recursive}, Concurrency: {concurrency}")

        count = 0
        errors = 0

        async for result in router.process_directory(folder, recursive, concurrency):
            try:
                output_path = await writer.write(result)
                count += 1
                console.print(f"  [green]OK[/green] {result.source} -> {output_path}")
            except Exception as e:
                errors += 1
                console.print(f"  [red]ERROR[/red] {result.source}: {e}")

        console.print(f"\nCompleted: {count} files, {errors} errors")

    asyncio.run(run())


@main.command()
@click.argument("url", type=str)
@click.option("-o", "--output", type=click.Path(), default="./output", help="Output directory")
@click.option("--strategy", type=click.Choice(["bfs", "dfs", "bestfirst"]), default="bfs", help="Crawl strategy")
@click.option("--max-depth", type=int, default=2, help="Maximum crawl depth")
@click.option("--max-pages", type=int, default=50, help="Maximum pages to crawl")
@click.option("--include", type=str, multiple=True, help="URL patterns to include")
@click.option("--exclude", type=str, multiple=True, help="URL patterns to exclude")
@click.option("--domain", type=str, help="Restrict to domain")
@click.option("--metadata", is_flag=True, help="Generate JSON metadata")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.pass_context
def crawl(ctx: click.Context, url: str, **kwargs):
    """Deep crawl a website and convert to markdown.

    Crawls the URL and all linked pages up to max-depth.
    """
    config = create_config(ctx)

    async def run():
        from .core import ExtractorRegistry
        from .output.writer import OutputWriter

        registry = _create_registry()
        writer = OutputWriter(config)

        # Get web extractor
        from .types import MediaType
        extractor = registry.get(MediaType.WEB)
        if extractor is None:
            console.print("[red]Error:[/red] Web extractor not available")
            console.print("Install with: pip install ingestor[web]")
            raise SystemExit(1)

        console.print(f"Crawling: {url}")
        console.print(f"Strategy: {config.crawl_strategy}, Max depth: {config.crawl_max_depth}")

        # Configure extractor with crawl settings
        extractor.strategy = config.crawl_strategy
        extractor.max_depth = config.crawl_max_depth
        extractor.max_pages = config.crawl_max_pages

        count = 0
        results = await extractor.crawl_deep(url)
        for result in results:
            try:
                output_path = await writer.write(result)
                count += 1
                depth = result.metadata.get("depth", 0)
                console.print(f"  [green]OK[/green] [depth={depth}] {result.source}")
            except Exception as e:
                console.print(f"  [red]ERROR[/red] {result.source}: {e}")

        console.print(f"\nCrawled {count} pages")

    asyncio.run(run())


@main.command()
@click.argument("repo", type=str)
@click.option("-o", "--output", type=click.Path(), default="./output", help="Output directory")
@click.option("--shallow/--full", default=True, help="Use shallow clone (default: shallow)")
@click.option("--depth", type=int, default=1, help="Clone depth for shallow clones")
@click.option("--branch", type=str, help="Clone specific branch")
@click.option("--tag", type=str, help="Clone specific tag")
@click.option("--commit", type=str, help="Checkout specific commit after clone")
@click.option("--token", type=str, envvar="GITHUB_TOKEN", help="Git token for private repos")
@click.option("--submodules", is_flag=True, help="Include git submodules")
@click.option("--max-files", type=int, default=500, help="Maximum files to process")
@click.option("--max-file-size", type=int, default=500000, help="Maximum file size in bytes")
@click.option("--include-binary", is_flag=True, help="Include binary file metadata")
@click.option("--metadata", is_flag=True, help="Generate JSON metadata files")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.pass_context
def clone(ctx: click.Context, repo: str, **kwargs):
    """Clone and ingest a git repository.

    REPO can be:
    - HTTPS URL: https://github.com/user/repo
    - SSH URL: git@github.com:user/repo.git
    - Local path: /path/to/local/repo
    - .download_git file: repos.download_git

    Examples:
        ingestor clone https://github.com/pallets/flask
        ingestor clone git@github.com:user/private-repo.git --token $TOKEN
        ingestor clone ./repos.download_git --max-files 200
    """
    config = create_config(ctx)

    async def run():
        from .extractors.git.git_extractor import GitExtractor, GitRepoConfig
        from .output.writer import OutputWriter

        # Create git-specific config
        git_config = GitRepoConfig(
            shallow=kwargs.get("shallow", True),
            depth=kwargs.get("depth", 1),
            branch=kwargs.get("branch"),
            tag=kwargs.get("tag"),
            commit=kwargs.get("commit"),
            include_submodules=kwargs.get("submodules", False),
            max_total_files=kwargs.get("max_files", 500),
            max_file_size=kwargs.get("max_file_size", 500000),
            include_binary_metadata=kwargs.get("include_binary", False),
        )

        # Create registry for nested extractions
        registry = _create_registry()

        extractor = GitExtractor(
            config=git_config,
            token=kwargs.get("token"),
            registry=registry,
        )
        writer = OutputWriter(config)

        console.print(f"Cloning repository: {repo}")
        if git_config.branch:
            console.print(f"  Branch: {git_config.branch}")
        if git_config.tag:
            console.print(f"  Tag: {git_config.tag}")
        if git_config.shallow:
            console.print(f"  Shallow clone: depth={git_config.depth}")

        with Progress(
            SpinnerColumn(spinner_name=_SPINNER),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Cloning and processing...", total=None)

            try:
                result = await extractor.extract(repo)
                progress.update(task, description="Writing output...")
                output_path = await writer.write(result)
                progress.update(task, completed=True, description="Done!")

                console.print(f"\n[green]Success![/green] Output written to: {output_path}")
                file_count = result.metadata.get("file_count", 0)
                console.print(f"  Files processed: {file_count}")
                if result.metadata.get("skipped_count"):
                    console.print(f"  Files skipped: {result.metadata['skipped_count']}")
                if result.has_images:
                    console.print(f"  Images: {result.image_count}")

            except Exception as e:
                progress.stop()
                console.print(f"[red]Error:[/red] {e}")
                if config.verbose:
                    console.print_exception()
                raise SystemExit(1)

    asyncio.run(run())


@main.command()
@click.argument("input", type=click.Path(exists=True))
@click.option("--vlm-model", type=str, default="llava:7b", help="VLM model")
@click.option("--ollama-host", type=str, default="http://localhost:11434", help="Ollama server")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def describe(input: str, vlm_model: str, ollama_host: str, verbose: bool):
    """Generate VLM descriptions for images.

    INPUT can be an image file or folder of images.
    """
    async def run():
        try:
            from .ai.ollama.vlm import VLMDescriber
        except ImportError:
            console.print("[red]Error:[/red] VLM dependencies not installed")
            console.print("Install with: pip install ingestor[vlm]")
            raise SystemExit(1)

        describer = VLMDescriber(host=ollama_host, model=vlm_model)
        input_path = Path(input)

        if input_path.is_file():
            images = [input_path]
        else:
            images = list(input_path.glob("**/*"))
            images = [p for p in images if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}]

        console.print(f"Describing {len(images)} image(s)...")

        for img_path in images:
            try:
                description = await describer.describe_file(img_path)
                console.print(f"\n[bold]{img_path.name}[/bold]")
                console.print(description)
            except Exception as e:
                console.print(f"[red]Error[/red] {img_path.name}: {e}")

    asyncio.run(run())


@main.command()
@click.argument("query", type=str)
@click.option("-o", "--output", type=click.Path(), default="./output", help="Output directory")
@click.option("--format", "output_format", type=str, default=None, help="Output format instructions")
@click.option("--no-stream", is_flag=True, help="Disable streaming (use polling)")
@click.option("--max-wait", type=int, default=3600, help="Max wait time in seconds (default: 3600)")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.pass_context
def research(ctx: click.Context, query: str, output: str, output_format: str,
             no_stream: bool, max_wait: int, verbose: bool):
    """Conduct deep research using Gemini Deep Research Agent.
    
    QUERY is the research topic or question.
    
    Requires GOOGLE_API_KEY environment variable.
    
    Examples:
    
        ingestor research "What are the latest advances in quantum computing?"
        
        ingestor research "Compare transformer architectures" --format "Include comparison table"
    """
    async def run():
        try:
            from .researcher import DeepResearcher, ResearchConfig
        except ImportError as e:
            console.print(f"[red]Error:[/red] Researcher dependencies not installed: {e}")
            console.print("Install with: pip install google-genai")
            raise SystemExit(1)
        
        output_path = Path(output)
        
        # Configure research
        config = ResearchConfig(
            output_format=output_format,
            max_wait_time=max_wait,
            enable_streaming=not no_stream,
            enable_thinking=verbose,
        )
        
        researcher = DeepResearcher(config=config)
        
        # Progress callback
        def on_progress(text: str):
            if verbose:
                if text.startswith("[Thinking]"):
                    console.print(f"[dim]{text}[/dim]")
                else:
                    console.print(text, end="")
        
        with Progress(
            SpinnerColumn(spinner_name=_SPINNER),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(f"Researching: {query[:50]}...", total=None)
            
            try:
                result = await researcher.research(query, on_progress=on_progress if verbose else None)
            except Exception as e:
                console.print(f"\n[red]Error:[/red] {e}")
                raise SystemExit(1)
        
        if result.succeeded:
            # Save results
            result.save(output_path / "research")
            
            console.print(f"\n[green]Research completed![/green]")
            console.print(f"Duration: {result.duration_seconds:.1f}s")
            console.print(f"Report saved to: {output_path / 'research' / 'research_report.md'}")
            
            # Print summary
            if verbose:
                console.print(f"\n[bold]Report Preview:[/bold]")
                preview = result.report[:500] + "..." if len(result.report) > 500 else result.report
                console.print(preview)
        else:
            console.print(f"\n[red]Research failed:[/red] {result.error}")
            raise SystemExit(1)
    
    asyncio.run(run())


@main.command(name="parse-refs")
@click.argument("input", type=click.Path(exists=True))
@click.option("-o", "--output-dir", type=click.Path(), default=None, help="Output directory for reference files (default: same as input)")
def parse_refs(input: str, output_dir: str):
    """Extract references from a research document.
    
    Takes a research document and generates a list of PDFs, websites,
    citations, git repos, YouTube videos, podcasts, books, etc.
    
    Automatically generates both JSON and Markdown output files.
    
    INPUT is a research report (markdown, json, or text file).
    
    Examples:
    
        ingestor parse-refs research_report.md
        
        ingestor parse-refs research.md -o ./refs/
    """
    import json
    
    try:
        from .researcher import ResearchParser
    except ImportError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    
    input_path = Path(input)
    parser = ResearchParser()
    
    refs = parser.parse_file(input_path)
    
    if not refs:
        console.print("[yellow]No references found.[/yellow]")
        return
    
    # Determine output directory
    if output_dir:
        out_dir = Path(output_dir)
    else:
        out_dir = input_path.parent
    
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate output filenames based on input
    base_name = input_path.stem.replace("_report", "").replace("research", "references")
    if base_name == input_path.stem:
        base_name = f"{input_path.stem}_references"
    
    json_path = out_dir / f"{base_name}.json"
    md_path = out_dir / f"{base_name}.md"
    
    # Group by type for stats
    grouped = parser.group_by_type(refs)
    
    console.print(f"[bold green]✓ Extracted {len(refs)} references:[/bold green]\n")
    for ref_type, type_refs in grouped.items():
        console.print(f"  • {ref_type.value}: {len(type_refs)}")
    
    # Generate JSON output
    data = []
    for ref in refs:
        data.append({
            "type": ref.type.value,
            "value": ref.value,
            "title": ref.title,
            "authors": ref.authors,
            "year": ref.year,
            "url": ref.url,
        })
    
    json_path.write_text(json.dumps(data, indent=2))
    
    # Generate Markdown summary
    summary = parser.get_summary(refs)
    md_path.write_text(summary)
    
    console.print(f"\n[bold]Output files:[/bold]")
    console.print(f"  📄 {md_path}")
    console.print(f"  📋 {json_path}")


@main.command()
@click.argument("identifier", type=str)
@click.option("-o", "--output", type=click.Path(), default="./output", help="Output directory")
@click.option("--email", type=str, envvar="INGESTOR_EMAIL", help="Email for API access (CrossRef, Unpaywall)")
@click.option("--s2-key", type=str, envvar="S2_API_KEY", help="Semantic Scholar API key")
@click.option("--bibtex/--no-bibtex", default=True, help="Generate BibTeX citation file")
@click.option("--markdown/--no-markdown", default=False, help="Extract PDF to markdown with metadata header")
@click.option("--references/--no-references", default=True, help="Fetch and save citation references")
@click.option("--max-refs", type=int, default=50, help="Maximum references to fetch")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.pass_context
def paper(ctx: click.Context, identifier: str, **kwargs):
    """Download a paper PDF with metadata.

    Downloads PDF and generates BibTeX and references file.

    IDENTIFIER can be:
    - DOI: 10.1038/nature12373
    - DOI URL: https://doi.org/10.1038/nature12373
    - arXiv ID: arXiv:2301.12345 or 2301.12345
    - arXiv URL: https://arxiv.org/abs/2301.12345
    - Semantic Scholar URL: https://www.semanticscholar.org/paper/...
    - Direct PDF URL: https://example.com/paper.pdf
    - Paper title: "Attention Is All You Need"

    Output (default):
    - PDF file: Author_Year_Title.pdf
    - BibTeX: citation.bib
    - References: references.txt

    Optional:
    - Markdown: Author_Year_Title.md (with --markdown)

    Examples:
        ingestor paper 10.1038/nature12373
        ingestor paper arXiv:1706.03762 --markdown
        ingestor paper "Attention Is All You Need" -o ./papers
    """
    output_dir = Path(kwargs.get("output", "./output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    verbose = kwargs.get("verbose", False)

    async def run():
        try:
            from .extractors.paper.resolver import resolve_identifier
            from .extractors.paper.metadata import get_metadata
        except ImportError:
            console.print("[red]Error:[/red] Paper extractor not available")
            raise SystemExit(1)

        console.print(f"Processing paper: {identifier}")

        with Progress(
            SpinnerColumn(spinner_name=_SPINNER),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Resolving identifier...", total=None)

            try:
                # Step 1: Resolve identifier
                resolved = resolve_identifier(identifier)
                progress.update(task, description=f"Identifier: {resolved.type.value}")

                # Step 2: Get metadata
                progress.update(task, description="Fetching metadata...")
                metadata = await get_metadata(
                    resolved,
                    email=kwargs.get("email"),
                    s2_api_key=kwargs.get("s2_key"),
                )

                if not metadata:
                    progress.stop()
                    console.print(f"[red]Error:[/red] Could not find metadata for: {identifier}")
                    raise SystemExit(1)

                # Step 3: Get PDF URL
                progress.update(task, description="Finding PDF...")
                pdf_url = metadata.pdf_url
                
                if not pdf_url:
                    # Try arXiv URL if we have arxiv_id
                    if metadata.arxiv_id:
                        pdf_url = f"https://arxiv.org/pdf/{metadata.arxiv_id}.pdf"
                    elif resolved.arxiv_id:
                        pdf_url = f"https://arxiv.org/pdf/{resolved.arxiv_id}.pdf"

                if not pdf_url:
                    progress.stop()
                    console.print(f"[red]Error:[/red] No PDF URL found for: {identifier}")
                    console.print("Try: Unpaywall, arXiv, or institutional access")
                    raise SystemExit(1)

                # Step 4: Download PDF
                progress.update(task, description="Downloading PDF...")
                
                # Generate filename
                import re
                first_author = ""
                if metadata.authors:
                    first_author = metadata.authors[0].name.split()[-1]  # Last name
                year = str(metadata.year) if metadata.year else ""
                title_short = re.sub(r"[^\w\s-]", "", metadata.title or "paper")[:50]
                
                parts = [p for p in [first_author, year, title_short] if p]
                filename = "_".join(parts).replace(" ", "_") + ".pdf"
                pdf_path = output_dir / filename

                import httpx
                async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
                    response = await client.get(
                        pdf_url,
                        headers={"User-Agent": "ingestor/1.0"},
                    )
                    response.raise_for_status()
                    
                    content = response.content
                    if not content.startswith(b"%PDF"):
                        progress.stop()
                        console.print(f"[red]Error:[/red] URL did not return a PDF")
                        raise SystemExit(1)
                    
                    pdf_path.write_bytes(content)

                # Step 5: Extract to markdown with metadata header (only with --markdown flag)
                markdown_path = None
                if kwargs.get("markdown", False):
                    progress.update(task, description="Extracting to markdown...")
                    try:
                        from .extractors.pdf import PdfExtractor
                        
                        # Build metadata header
                        header_lines = ["---"]
                        if metadata.title:
                            header_lines.append(f"title: \"{metadata.title}\"")
                        if metadata.authors:
                            author_names = [a.name for a in metadata.authors]
                            header_lines.append(f"authors: {author_names}")
                        if metadata.year:
                            header_lines.append(f"year: {metadata.year}")
                        if metadata.doi:
                            header_lines.append(f"doi: \"{metadata.doi}\"")
                        if metadata.arxiv_id:
                            header_lines.append(f"arxiv: \"{metadata.arxiv_id}\"")
                        if metadata.venue:
                            header_lines.append(f"venue: \"{metadata.venue}\"")
                        if metadata.abstract:
                            # Escape quotes and format abstract
                            abstract_escaped = metadata.abstract.replace('"', '\\"').replace('\n', ' ')
                            header_lines.append(f"abstract: \"{abstract_escaped[:500]}...\"" if len(metadata.abstract) > 500 else f"abstract: \"{abstract_escaped}\"")
                        header_lines.append(f"source_pdf: \"{pdf_path.name}\"")
                        header_lines.append("---")
                        header_lines.append("")
                        metadata_header = "\n".join(header_lines)
                        
                        # Extract PDF content
                        pdf_extractor = PdfExtractor()
                        result = await pdf_extractor.extract(pdf_path)
                        
                        # Combine header + content
                        markdown_content = metadata_header + result.markdown
                        
                        # Save markdown file
                        markdown_path = pdf_path.with_suffix(".md")
                        markdown_path.write_text(markdown_content)
                        
                    except Exception as e:
                        if verbose:
                            console.print(f"  [yellow]Warning:[/yellow] Could not extract markdown: {e}")

                # Step 6: Generate BibTeX if requested
                bibtex_path = None
                if kwargs.get("bibtex", True):
                    bibtex = metadata.to_bibtex()
                    bibtex_path = output_dir / "citation.bib"
                    
                    # Append or create
                    if bibtex_path.exists():
                        existing = bibtex_path.read_text()
                        if metadata.bibtex_key not in existing:
                            bibtex_path.write_text(existing + "\n" + bibtex)
                    else:
                        bibtex_path.write_text(bibtex)

                # Step 7: Fetch references if requested (citation graph)
                refs_path = None
                refs_count = 0
                if kwargs.get("references", False):
                    progress.update(task, description="Fetching references...")
                    try:
                        from .extractors.paper.clients import SemanticScholarClient
                        
                        s2_client = SemanticScholarClient(api_key=kwargs.get("s2_key"))
                        max_refs = kwargs.get("max_refs", 50)
                        
                        # Get paper ID for S2 (prefer arXiv ID, then S2 ID, then DOI)
                        paper_id = None
                        if metadata.arxiv_id:
                            paper_id = f"ARXIV:{metadata.arxiv_id}"
                        elif metadata.s2_id:
                            paper_id = metadata.s2_id
                        elif metadata.doi and not metadata.doi.startswith("10.48550/arXiv"):
                            paper_id = f"DOI:{metadata.doi}"
                        
                        if paper_id:
                            refs = await s2_client.get_references(paper_id, limit=max_refs)
                            if refs:
                                refs_path = output_dir / "references.txt"
                                ref_lines = []
                                for ref in refs:
                                    title = ref.get("title", "Unknown")
                                    doi = ref.get("doi", "")
                                    year = ref.get("year", "")
                                    ref_lines.append(f"{title}")
                                    if doi:
                                        ref_lines.append(f"  DOI: {doi}")
                                    if year:
                                        ref_lines.append(f"  Year: {year}")
                                    ref_lines.append("")
                                refs_path.write_text("\n".join(ref_lines))
                                refs_count = len(refs)
                    except Exception as e:
                        if verbose:
                            console.print(f"  [yellow]Warning:[/yellow] Could not fetch references: {e}")

                progress.update(task, completed=True, description="Done!")

                # Show summary
                console.print(f"\n[green]Success![/green] PDF downloaded")
                console.print(f"  PDF: {pdf_path}")
                console.print(f"  Title: {metadata.title}")
                if metadata.authors:
                    author_names = [a.name for a in metadata.authors[:3]]
                    if len(metadata.authors) > 3:
                        author_names.append("et al.")
                    console.print(f"  Authors: {', '.join(author_names)}")
                if metadata.year:
                    console.print(f"  Year: {metadata.year}")
                if metadata.doi:
                    console.print(f"  DOI: {metadata.doi}")
                if metadata.arxiv_id:
                    console.print(f"  arXiv: {metadata.arxiv_id}")
                if markdown_path:
                    console.print(f"  Markdown: {markdown_path}")
                if bibtex_path:
                    console.print(f"  BibTeX: {bibtex_path}")
                if refs_path:
                    console.print(f"  References: {refs_path} ({refs_count} citations)")

            except SystemExit:
                raise
            except Exception as e:
                progress.stop()
                console.print(f"[red]Error:[/red] {e}")
                if verbose:
                    console.print_exception()
                raise SystemExit(1)

    asyncio.run(run())


@main.command(name="paper-meta")
@click.argument("identifier", type=str)
@click.option("--email", type=str, envvar="INGESTOR_EMAIL", help="Email for API access")
@click.option("--s2-key", type=str, envvar="S2_API_KEY", help="Semantic Scholar API key")
@click.option("--format", "output_format", type=click.Choice(["json", "bibtex", "yaml"]), default="json", help="Output format")
def paper_meta(identifier: str, email: Optional[str], s2_key: Optional[str], output_format: str):
    """Get metadata for a paper without downloading.

    IDENTIFIER can be a DOI, arXiv ID, or paper title.

    Examples:
        ingestor paper-meta 10.1038/nature12373
        ingestor paper-meta arXiv:1706.03762 --format bibtex
    """
    import json

    async def run():
        try:
            from .extractors.paper import PaperExtractor, PaperConfig
        except ImportError:
            console.print("[red]Error:[/red] Paper extractor not available")
            console.print("Install with: pip install ingestor[paper]")
            raise SystemExit(1)

        paper_config = PaperConfig(
            email=email,
            s2_api_key=s2_key,
        )

        extractor = PaperExtractor(config=paper_config)
        metadata = await extractor.get_metadata(identifier)

        if not metadata:
            console.print(f"[red]Error:[/red] Could not find metadata for: {identifier}")
            raise SystemExit(1)

        if output_format == "json":
            console.print(json.dumps(metadata, indent=2, default=str))
        elif output_format == "bibtex":
            bibtex = await extractor.get_bibtex(identifier)
            if bibtex:
                console.print(bibtex)
            else:
                console.print("[red]Error:[/red] Could not generate BibTeX")
        elif output_format == "yaml":
            import yaml
            console.print(yaml.dump(metadata, default_flow_style=False))

    asyncio.run(run())


@main.command(name="paper-batch")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), default="./output", help="Output directory")
@click.option("--email", type=str, envvar="INGESTOR_EMAIL", help="Email for API access")
@click.option("--s2-key", type=str, envvar="S2_API_KEY", help="Semantic Scholar API key")
@click.option("--concurrency", type=int, default=3, help="Maximum concurrent downloads")
@click.option("--bibtex/--no-bibtex", default=True, help="Generate BibTeX citation files")
@click.option("--skip-existing", is_flag=True, default=True, help="Skip already downloaded papers")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def paper_batch(input_file: str, output: str, email: Optional[str], s2_key: Optional[str], 
                concurrency: int, bibtex: bool, skip_existing: bool, verbose: bool):
    """Batch download paper PDFs from a file (like paper-acq batch).

    Downloads PDFs only - no markdown conversion.

    INPUT_FILE can be:
    - CSV: with 'doi' and/or 'title' columns
    - JSON: array of objects with 'doi' and/or 'title' fields
    - TXT: one identifier per line (DOI, arXiv ID, or title)

    Examples:
        ingestor paper-batch papers.csv -o ./papers
        ingestor paper-batch dois.txt --concurrency 5
        ingestor paper-batch references.json
    """
    import csv
    import json as json_module
    import re
    from pathlib import Path as PathLib

    import httpx

    output_dir = PathLib(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    async def run():
        try:
            from .extractors.paper.resolver import resolve_identifier
            from .extractors.paper.metadata import get_metadata
        except ImportError:
            console.print("[red]Error:[/red] Paper extractor not available")
            raise SystemExit(1)

        # Parse input file
        input_path = PathLib(input_file)
        papers: list[str] = []

        if input_path.suffix.lower() == ".csv":
            with open(input_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    identifier = row.get("doi", "").strip() or row.get("title", "").strip()
                    if identifier:
                        papers.append(identifier)
        elif input_path.suffix.lower() == ".json":
            with open(input_path, encoding="utf-8") as f:
                data = json_module.load(f)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            identifier = (item.get("doi") or item.get("title") or "").strip()
                        else:
                            identifier = str(item).strip()
                        if identifier:
                            papers.append(identifier)
        else:  # TXT or other - one per line
            with open(input_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        papers.append(line)

        if not papers:
            console.print("[red]Error:[/red] No papers found in input file")
            raise SystemExit(1)

        console.print(f"Found {len(papers)} papers to download")
        console.print(f"Output: {output_dir}")
        console.print(f"Concurrency: {concurrency}")

        # Process with semaphore for concurrency control
        semaphore = asyncio.Semaphore(concurrency)
        results = {"success": 0, "failed": 0, "skipped": 0}
        all_bibtex = []

        async def download_paper(identifier: str, idx: int):
            async with semaphore:
                try:
                    console.print(f"[{idx + 1}/{len(papers)}] Processing: {identifier[:50]}...")
                    
                    # Resolve identifier
                    resolved = resolve_identifier(identifier)
                    
                    # Get metadata
                    metadata = await get_metadata(
                        resolved,
                        email=email,
                        s2_api_key=s2_key,
                    )
                    
                    if not metadata:
                        results["failed"] += 1
                        console.print(f"  [red]FAILED[/red] No metadata found")
                        return
                    
                    # Get PDF URL
                    pdf_url = metadata.pdf_url
                    if not pdf_url and (metadata.arxiv_id or resolved.arxiv_id):
                        arxiv_id = metadata.arxiv_id or resolved.arxiv_id
                        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                    
                    if not pdf_url:
                        results["failed"] += 1
                        console.print(f"  [red]FAILED[/red] No PDF URL")
                        return
                    
                    # Generate filename
                    first_author = ""
                    if metadata.authors:
                        first_author = metadata.authors[0].name.split()[-1]
                    year = str(metadata.year) if metadata.year else ""
                    title_short = re.sub(r"[^\w\s-]", "", metadata.title or "paper")[:50]
                    
                    parts = [p for p in [first_author, year, title_short] if p]
                    filename = "_".join(parts).replace(" ", "_") + ".pdf"
                    pdf_path = output_dir / filename
                    
                    # Skip if exists
                    if skip_existing and pdf_path.exists():
                        results["skipped"] += 1
                        console.print(f"  [yellow]SKIP[/yellow] Already exists")
                        return
                    
                    # Download
                    async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
                        response = await client.get(
                            pdf_url,
                            headers={"User-Agent": "ingestor/1.0"},
                        )
                        response.raise_for_status()
                        
                        content = response.content
                        if not content.startswith(b"%PDF"):
                            results["failed"] += 1
                            console.print(f"  [red]FAILED[/red] Not a PDF")
                            return
                        
                        pdf_path.write_bytes(content)
                    
                    # Collect BibTeX
                    if bibtex:
                        all_bibtex.append(metadata.to_bibtex())
                    
                    results["success"] += 1
                    console.print(f"  [green]OK[/green] -> {pdf_path.name}")
                    
                except Exception as e:
                    results["failed"] += 1
                    console.print(f"  [red]FAILED[/red] {e}")
                    if verbose:
                        import traceback
                        traceback.print_exc()

        tasks = [download_paper(p, i) for i, p in enumerate(papers)]
        await asyncio.gather(*tasks)

        # Write combined BibTeX
        if bibtex and all_bibtex:
            bibtex_path = output_dir / "citation.bib"
            bibtex_path.write_text("\n\n".join(all_bibtex))
            console.print(f"\nBibTeX saved to: {bibtex_path}")

        console.print(f"\n{'=' * 50}")
        console.print("SUMMARY")
        console.print(f"{'=' * 50}")
        console.print(f"  Downloaded: {results['success']}")
        console.print(f"  Failed:     {results['failed']}")
        console.print(f"  Skipped:    {results['skipped']}")
        console.print(f"{'=' * 50}")

    asyncio.run(run())


@main.command(name="verify-bib")
@click.argument("input_path", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), default="./output", help="Output directory")
@click.option("--email", type=str, envvar="INGESTOR_EMAIL", help="Email for API access")
@click.option("--manual", type=click.Path(exists=True), help="Manual.bib with pre-verified entries")
@click.option("--skip", type=str, multiple=True, help="Citation keys to skip verification")
@click.option("--skip-file", type=click.Path(exists=True), help="File with keys to skip (one per line)")
@click.option("--dry-run", is_flag=True, help="Show what would be done without writing files")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def verify_bib(input_path: str, output: str, email: Optional[str], manual: Optional[str],
               skip: tuple, skip_file: Optional[str], dry_run: bool, verbose: bool):
    """Verify BibTeX citations against academic databases.

    INPUT_PATH can be:
    - A single .bib file: outputs verified.bib, failed.bib, report.md
    - A directory of .bib files: outputs verified/, failed/, report.md

    Verification sources:
    - CrossRef (DOI lookup)
    - arXiv API (arXiv papers)
    - DOI content negotiation

    Examples:
        ingestor verify-bib references.bib -o ./verified
        ingestor verify-bib ./citations -o ./output
        ingestor verify-bib refs.bib --manual custom.bib
        ingestor verify-bib refs.bib --skip key1 --skip key2
    """
    from pathlib import Path as PathLib

    async def run():
        try:
            from .extractors.paper.verifier import CitationVerifier
        except ImportError:
            console.print("[red]Error:[/red] Paper extractor not available")
            console.print("Install with: pip install ingestor[paper]")
            raise SystemExit(1)

        # Build skip set
        skip_keys: set[str] = set(skip)
        if skip_file:
            skip_path = PathLib(skip_file)
            for line in skip_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    skip_keys.add(line)

        input_p = PathLib(input_path)
        output_dir = PathLib(output)

        verifier = CitationVerifier(email=email)

        console.print("=" * 60)
        console.print("Citation Verification")
        console.print("=" * 60)
        console.print(f"Input: {input_p}")
        console.print(f"Output: {output_dir}")
        if skip_keys:
            console.print(f"Skipping: {len(skip_keys)} keys")
        if dry_run:
            console.print("[yellow]DRY RUN - no files will be written[/yellow]")
        console.print()

        if input_p.is_dir():
            # Directory mode
            bib_files = list(input_p.glob("*.bib"))
            console.print(f"Found {len(bib_files)} .bib files")
            console.print("-" * 60)

            stats, results = await verifier.verify_directory(
                input_dir=input_p,
                output_dir=output_dir,
                skip_keys=skip_keys if skip_keys else None,
                dry_run=dry_run,
            )
        else:
            # Single file mode
            from .extractors.paper.verifier import parse_bib_file
            entries = parse_bib_file(input_p)
            console.print(f"Found {len(entries)} entries")
            console.print("-" * 60)

            manual_path = PathLib(manual) if manual else None
            stats, results = await verifier.verify_file(
                input_path=input_p,
                output_dir=output_dir,
                skip_keys=skip_keys if skip_keys else None,
                manual_path=manual_path,
                dry_run=dry_run,
            )

        # Print results
        for result in results:
            status_color = {
                "verified": "green",
                "arxiv": "cyan",
                "searched": "blue",
                "website": "yellow",
                "manual": "magenta",
                "failed": "red",
            }.get(result.status, "white")
            console.print(f"  [{status_color}]{result.status.upper():8}[/{status_color}] {result.key}")
            if verbose:
                console.print(f"           {result.message}")

        # Summary
        console.print()
        console.print("=" * 60)
        console.print("SUMMARY")
        console.print("=" * 60)
        console.print(f"  verified:  {stats.verified}")
        console.print(f"  arxiv:     {stats.arxiv}")
        console.print(f"  searched:  {stats.searched}")
        console.print(f"  website:   {stats.website}")
        console.print(f"  manual:    {stats.manual}")
        console.print(f"  failed:    {stats.failed}")
        console.print("-" * 60)
        console.print(f"  [green]VERIFIED:  {stats.total_verified}[/green]")
        console.print(f"  [red]FAILED:    {stats.failed}[/red]")
        console.print("=" * 60)

        if not dry_run:
            console.print(f"\nOutput written to: {output_dir.absolute()}")

    asyncio.run(run())


@main.command(name="paper-sources")
def paper_sources():
    """List available paper sources and their status.

    Shows which sources are configured and available for paper retrieval.
    """
    import os

    console.print("=" * 60)
    console.print("Paper Acquisition Sources")
    console.print("=" * 60)
    console.print()

    # Check environment variables
    email = os.environ.get("INGESTOR_EMAIL")
    s2_key = os.environ.get("S2_API_KEY")
    ncbi_key = os.environ.get("NCBI_API_KEY")
    proxy_url = os.environ.get("INSTITUTIONAL_PROXY_URL")
    vpn_script = os.environ.get("INSTITUTIONAL_VPN_SCRIPT")

    # Check if Claude Agent SDK is available for web search
    try:
        from claude_code_sdk import query  # noqa: F401
        claude_sdk = True
    except ImportError:
        claude_sdk = False

    # Check if Selenium is available for institutional access
    try:
        from selenium import webdriver  # noqa: F401
        selenium_available = True
    except ImportError:
        selenium_available = False

    # Check if institutional cookies exist
    from pathlib import Path as PathLib
    cookies_exist = PathLib(".institutional_cookies.pkl").exists()

    # Source status - ordered by typical priority
    sources = [
        ("arXiv", True, "Open access preprints", "No auth required"),
        ("Unpaywall", bool(email), "Open access papers", f"Email: {'✓' if email else '✗ Set INGESTOR_EMAIL'}"),
        ("PMC", True, "PubMed Central", f"NCBI key: {'✓' if ncbi_key else '○ Optional: NCBI_API_KEY'}"),
        ("bioRxiv", True, "Biology preprints", "No auth required"),
        ("medRxiv", True, "Medical preprints", "No auth required"),
        ("CrossRef", True, "DOI metadata", f"Polite pool: {'✓' if email else '✗ Set INGESTOR_EMAIL'}"),
        ("Semantic Scholar", True, "Metadata & citations", f"API key: {'✓' if s2_key else '○ Optional: S2_API_KEY'}"),
        ("OpenAlex", True, "Metadata", f"Email: {'✓' if email else '✗ Set INGESTOR_EMAIL'}"),
        ("Institutional", bool(proxy_url or vpn_script or cookies_exist), "EZProxy/VPN access",
         f"{'✓ Configured' if (proxy_url or vpn_script or cookies_exist) else '○ Run: ingestor paper-auth'}"),
        ("WebSearch", claude_sdk, "Claude SDK search", f"{'✓ Available' if claude_sdk else '○ pip install claude-code-sdk'}"),
    ]

    console.print("| Source | Status | Description | Auth |")
    console.print("|--------|--------|-------------|------|")
    for name, available, desc, auth in sources:
        status = "[green]✓[/green]" if available else "[yellow]○[/yellow]"
        console.print(f"| {name:16} | {status} | {desc:20} | {auth} |")

    console.print()
    console.print("[bold]Not Implemented (Legal Concerns):[/bold]")
    console.print("  ⛔ Sci-Hub - PDF retrieval (intentionally excluded)")
    console.print("  ⛔ LibGen  - PDF retrieval (intentionally excluded)")

    console.print()
    console.print("[bold]Environment Variables:[/bold]")
    console.print(f"  INGESTOR_EMAIL           = {email or '(not set)'}")
    console.print(f"  S2_API_KEY               = {'***' if s2_key else '(not set)'}")
    console.print(f"  NCBI_API_KEY             = {'***' if ncbi_key else '(not set)'}")
    console.print(f"  INSTITUTIONAL_PROXY_URL  = {proxy_url or '(not set)'}")
    console.print(f"  INSTITUTIONAL_VPN_SCRIPT = {vpn_script or '(not set)'}")
    console.print()
    console.print("[bold]Recommended:[/bold]")
    console.print("  export INGESTOR_EMAIL='your@email.com'")
    console.print("  # For higher rate limits:")
    console.print("  export S2_API_KEY='your_api_key'")
    console.print("  export NCBI_API_KEY='your_ncbi_key'")
    console.print("  # For institutional access:")
    console.print("  ingestor paper-auth --proxy-url 'https://ezproxy.university.edu/login?url='")


@main.command(name="paper-init")
@click.option("--output", "-o", type=click.Path(), default="ingestor-paper.yaml", help="Config file path")
@click.option("--force", is_flag=True, help="Overwrite existing config")
def paper_init(output: str, force: bool):
    """Initialize a paper acquisition configuration file.

    Creates a YAML config file with default settings for paper acquisition.

    Examples:
        ingestor paper-init
        ingestor paper-init -o my-config.yaml
        ingestor paper-init --force
    """
    from pathlib import Path as PathLib

    config_path = PathLib(output)

    if config_path.exists() and not force:
        console.print(f"[yellow]Warning:[/yellow] {config_path} already exists")
        console.print("Use --force to overwrite")
        raise SystemExit(1)

    default_config = '''# Ingestor Paper Acquisition Configuration
# Edit this file to customize your settings

# Your email (required for polite API access to CrossRef, Unpaywall, OpenAlex)
user:
  email: "your.email@university.edu"

# API Keys (optional but recommended for higher rate limits)
api_keys:
  semantic_scholar: null  # Get from https://www.semanticscholar.org/product/api
  ncbi: null  # Get from https://www.ncbi.nlm.nih.gov/account/settings/

# Source configuration (ordered by priority)
# Lower priority number = tried first
sources:
  arxiv:
    enabled: true
    priority: 1
  unpaywall:
    enabled: true
    priority: 2
  pmc:
    enabled: true
    priority: 3
  biorxiv:
    enabled: true
    priority: 4
  semantic_scholar:
    enabled: true
    priority: 5
  openalex:
    enabled: true
    priority: 6

# Download settings
download:
  output_dir: "./papers"
  skip_existing: true
  max_title_length: 50
  extract_pdf: true  # Use Docling to extract PDF content

# Rate limiting (seconds between requests per source)
rate_limits:
  crossref: 0.5
  unpaywall: 0.1
  arxiv: 3.0
  pmc: 0.34
  semantic_scholar: 3.0
  biorxiv: 1.0
  openalex: 0.1

# Batch processing
batch:
  max_concurrent: 3
  retry_failed: true
  max_retries: 2

# BibTeX generation
bibtex:
  enabled: true
  output_file: "citation.bib"

# Citation verification (doi2bib-style)
verification:
  verify_doi: true
  verify_arxiv: true
  search_crossref: true
  add_access_dates: true
'''

    config_path.write_text(default_config)
    console.print(f"[green]Created[/green] {config_path}")
    console.print()
    console.print("Next steps:")
    console.print(f"  1. Edit {config_path} and set your email address")
    console.print("  2. Set environment variables:")
    console.print("     export INGESTOR_EMAIL='your@email.com'")
    console.print("  3. Start acquiring papers:")
    console.print("     ingestor paper 10.1038/nature12373")


@main.command(name="paper-auth")
@click.option("--proxy-url", type=str, help="EZProxy URL (e.g., https://ezproxy.gl.iit.edu/login?url=)")
@click.option("--vpn-script", type=click.Path(exists=True), help="Path to VPN connection script")
@click.option("--cookies-file", type=str, default=".institutional_cookies.pkl", help="Path to save cookies")
def paper_auth(proxy_url: Optional[str], vpn_script: Optional[str], cookies_file: str):
    """Authenticate with your institution for paper access.

    Two authentication modes are supported:

    1. VPN Mode: Runs your VPN connection script
       ingestor paper-auth --vpn-script ./connect-vpn.sh

    2. EZProxy Mode: Opens browser for Shibboleth/SAML login
       ingestor paper-auth --proxy-url "https://ezproxy.gl.iit.edu/login?url="

    Examples:
        ingestor paper-auth --vpn-script ~/vpn-connect.sh
        ingestor paper-auth --proxy-url "https://ezproxy.university.edu/login?url="
    """
    import os

    # Get from environment if not provided
    if not proxy_url:
        proxy_url = os.environ.get("INSTITUTIONAL_PROXY_URL")
    if not vpn_script:
        vpn_script = os.environ.get("INSTITUTIONAL_VPN_SCRIPT")

    if not proxy_url and not vpn_script:
        console.print("[red]Error:[/red] Must provide --proxy-url or --vpn-script")
        console.print()
        console.print("For EZProxy authentication:")
        console.print("  ingestor paper-auth --proxy-url 'https://ezproxy.university.edu/login?url='")
        console.print()
        console.print("For VPN authentication:")
        console.print("  ingestor paper-auth --vpn-script /path/to/vpn-connect.sh")
        console.print()
        console.print("Or set environment variables:")
        console.print("  export INSTITUTIONAL_PROXY_URL='https://ezproxy.university.edu/login?url='")
        console.print("  export INSTITUTIONAL_VPN_SCRIPT='/path/to/vpn-connect.sh'")
        raise SystemExit(1)

    try:
        from .extractors.paper.clients import InstitutionalAccessClient
    except ImportError as e:
        console.print(f"[red]Error:[/red] Could not import InstitutionalAccessClient: {e}")
        raise SystemExit(1)

    # VPN mode
    if vpn_script:
        client = InstitutionalAccessClient(
            vpn_enabled=True,
            vpn_script=vpn_script,
        )
        console.print(f"Running VPN script: {vpn_script}")
        success = client.connect_vpn()
        if success:
            console.print()
            console.print("[green]Success![/green] VPN connected. You can now download papers via institutional access.")
        else:
            console.print("[red]VPN connection failed.[/red]")
            raise SystemExit(1)
        return

    # EZProxy mode
    client = InstitutionalAccessClient(
        proxy_url=proxy_url,
        vpn_enabled=False,
        cookies_file=cookies_file,
    )

    try:
        success = client.authenticate_interactive()
        if success:
            console.print()
            console.print("[green]Success![/green] Authentication saved to " + cookies_file)
            console.print("You can now download papers via institutional access.")
        else:
            console.print("[red]Authentication failed.[/red]")
            raise SystemExit(1)
    except ImportError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print()
        console.print("Install Selenium with: pip install selenium webdriver-manager")
        raise SystemExit(1)


@main.command(name="paper-config-push")
@click.option("--config", "-c", type=click.Path(exists=True), default="ingestor-paper.yaml", help="Config file to push")
@click.option("--gist-id", type=str, help="Existing gist ID to update")
def paper_config_push(config: str, gist_id: Optional[str]):
    """Push paper config to a private GitHub gist.

    Requires GitHub CLI (gh) to be installed and authenticated.
    This allows syncing your paper acquisition config across machines.

    Examples:
        ingestor paper-config-push
        ingestor paper-config-push -c my-config.yaml
        ingestor paper-config-push --gist-id abc123def456
    """
    import subprocess
    from pathlib import Path as PathLib

    config_path = PathLib(config)
    gist_id_file = PathLib(".ingestor_gist_id")

    if not config_path.exists():
        console.print(f"[red]Error:[/red] Config file not found: {config_path}")
        console.print("Create one with: ingestor paper-init")
        raise SystemExit(1)

    # Check if gh is available
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print("[red]Error:[/red] GitHub CLI (gh) not found")
        console.print("Install from: https://cli.github.com/")
        raise SystemExit(1)

    # Get existing gist ID
    if not gist_id and gist_id_file.exists():
        gist_id = gist_id_file.read_text().strip()

    if gist_id:
        # Update existing gist
        console.print(f"Updating gist {gist_id}...")
        result = subprocess.run(
            ["gh", "gist", "edit", gist_id, "-f", str(config_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            console.print(f"[red]Error:[/red] {result.stderr}")
            raise SystemExit(1)
        console.print(f"[green]Success![/green] Config updated in gist {gist_id}")
    else:
        # Create new private gist
        console.print("Creating new private gist...")
        result = subprocess.run(
            ["gh", "gist", "create", str(config_path), "--desc", "ingestor paper config"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            console.print(f"[red]Error:[/red] {result.stderr}")
            raise SystemExit(1)

        # Extract gist ID from URL
        gist_url = result.stdout.strip()
        new_gist_id = gist_url.split("/")[-1]
        gist_id_file.write_text(new_gist_id)

        console.print(f"[green]Success![/green] Config uploaded to: {gist_url}")
        console.print(f"Gist ID saved to {gist_id_file}")


@main.command(name="paper-config-pull")
@click.option("--config", "-c", type=click.Path(), default="ingestor-paper.yaml", help="Where to save config")
@click.option("--gist-id", type=str, help="Gist ID to pull from")
def paper_config_pull(config: str, gist_id: Optional[str]):
    """Pull paper config from a private GitHub gist.

    Requires GitHub CLI (gh) to be installed and authenticated.
    This allows syncing your paper acquisition config across machines.

    Examples:
        ingestor paper-config-pull
        ingestor paper-config-pull --gist-id abc123def456
        ingestor paper-config-pull -c my-config.yaml
    """
    import subprocess
    from pathlib import Path as PathLib

    config_path = PathLib(config)
    gist_id_file = PathLib(".ingestor_gist_id")

    # Check if gh is available
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print("[red]Error:[/red] GitHub CLI (gh) not found")
        console.print("Install from: https://cli.github.com/")
        raise SystemExit(1)

    # Get gist ID
    if not gist_id:
        if gist_id_file.exists():
            gist_id = gist_id_file.read_text().strip()
        else:
            console.print("[red]Error:[/red] No gist ID provided or saved")
            console.print("Run with --gist-id or push a config first")
            raise SystemExit(1)

    console.print(f"Pulling config from gist {gist_id}...")

    # Get gist content
    result = subprocess.run(
        ["gh", "gist", "view", gist_id, "-r"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(f"[red]Error:[/red] {result.stderr}")
        raise SystemExit(1)

    # Backup existing config
    if config_path.exists():
        backup_path = config_path.with_suffix(".yaml.bak")
        config_path.rename(backup_path)
        console.print(f"Backed up existing config to {backup_path}")

    # Write new config
    config_path.write_text(result.stdout)
    gist_id_file.write_text(gist_id)

    console.print(f"[green]Success![/green] Config saved to {config_path}")


def _create_registry():
    """Create and populate the extractor registry."""
    from .core import ExtractorRegistry

    registry = ExtractorRegistry()

    # Try to import and register each extractor
    # These will fail silently if dependencies aren't installed

    try:
        from .extractors.text.txt_extractor import TxtExtractor
        registry.register(TxtExtractor())
    except ImportError:
        pass

    try:
        from .extractors.pdf.pdf_extractor import PdfExtractor
        registry.register(PdfExtractor())
    except ImportError:
        pass

    try:
        from .extractors.docx.docx_extractor import DocxExtractor
        registry.register(DocxExtractor())
    except ImportError:
        pass

    try:
        from .extractors.pptx.pptx_extractor import PptxExtractor
        registry.register(PptxExtractor())
    except ImportError:
        pass

    try:
        from .extractors.epub.epub_extractor import EpubExtractor
        registry.register(EpubExtractor())
    except ImportError:
        pass

    try:
        from .extractors.excel.xlsx_extractor import XlsxExtractor
        registry.register(XlsxExtractor())
    except ImportError:
        pass

    try:
        from .extractors.excel.xls_extractor import XlsExtractor
        registry.register(XlsExtractor())
    except ImportError:
        pass

    try:
        from .extractors.data.csv_extractor import CsvExtractor
        registry.register(CsvExtractor())
    except ImportError:
        pass

    try:
        from .extractors.data.json_extractor import JsonExtractor
        registry.register(JsonExtractor())
    except ImportError:
        pass

    try:
        from .extractors.data.xml_extractor import XmlExtractor
        registry.register(XmlExtractor())
    except ImportError:
        pass

    try:
        from .extractors.web.web_extractor import WebExtractor
        registry.register(WebExtractor())
    except ImportError:
        pass

    try:
        from .extractors.youtube.youtube_extractor import YouTubeExtractor
        registry.register(YouTubeExtractor())
    except ImportError:
        pass

    try:
        from .extractors.git.git_extractor import GitExtractor
        from .types import MediaType
        git_extractor = GitExtractor(registry=registry)
        registry.register(git_extractor)
        # Also register for GITHUB type since unified extractor handles both
        registry._extractors[MediaType.GITHUB] = git_extractor
    except ImportError:
        pass

    try:
        from .extractors.audio.audio_extractor import AudioExtractor
        registry.register(AudioExtractor())
    except ImportError:
        pass

    try:
        from .extractors.archive.zip_extractor import ZipExtractor
        registry.register(ZipExtractor(registry))
    except ImportError:
        pass

    try:
        from .extractors.image.image_extractor import ImageExtractor
        registry.register(ImageExtractor())
    except ImportError:
        pass

    return registry


if __name__ == "__main__":
    main()
