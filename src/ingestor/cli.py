"""Command-line interface for ingestor."""

import asyncio
import sys
from pathlib import Path

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
        from .core import Router
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
            console.print(f"  uv sync --extra {media_type.value}")
            console.print(f"  # or: pip install ingestor[{media_type.value}]")
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
                raise SystemExit(1) from e

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
        from .core import Router
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
        from .output.writer import OutputWriter

        registry = _create_registry()
        writer = OutputWriter(config)

        # Get web extractor
        from .types import MediaType
        extractor = registry.get(MediaType.WEB)
        if extractor is None:
            console.print("[red]Error:[/red] Web extractor not available")
            console.print("Install with: uv sync --extra web")
            console.print("  # or: pip install ingestor[web]")
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
                await writer.write(result)
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
            task = progress.add_task("Cloning and processing...", total=None)

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
                raise SystemExit(1) from e

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
        except ImportError as e:
            console.print("[red]Error:[/red] VLM dependencies not installed")
            console.print("Install with: uv sync --extra vlm")
            console.print("  # or: pip install ingestor[vlm]")
            raise SystemExit(1) from e

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
