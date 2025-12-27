"""Configuration management using Pydantic."""

from pathlib import Path

from pydantic import BaseModel, Field


class ImageConfig(BaseModel):
    """Image processing configuration."""

    convert_to_png: bool = Field(default=True, description="Convert images to PNG")
    target_format: str = Field(default="png", description="Target format when converting")
    naming_style: str = Field(default="sequential", description="Image naming style")


class WebConfig(BaseModel):
    """Web crawling configuration."""

    strategy: str = Field(default="bfs", description="Crawl strategy (bfs, dfs)")
    max_depth: int = Field(default=2, description="Maximum crawl depth")
    max_pages: int = Field(default=50, description="Maximum pages to crawl")
    same_domain: bool = Field(default=True, description="Restrict to same domain")
    include_patterns: list[str] = Field(default_factory=list, description="URL patterns to include")
    exclude_patterns: list[str] = Field(default_factory=list, description="URL patterns to exclude")


class YouTubeConfig(BaseModel):
    """YouTube extraction configuration."""

    caption_type: str = Field(default="auto", description="Caption type (auto, manual)")
    include_playlist: bool = Field(default=False, description="Process entire playlist")
    languages: list[str] = Field(default=["en"], description="Preferred languages")


class AudioConfig(BaseModel):
    """Audio transcription configuration."""

    whisper_model: str = Field(default="turbo", description="Whisper model size")


class AIConfig(BaseModel):
    """AI features configuration."""

    describe_images: bool = Field(default=False, description="Generate image descriptions")
    vlm_model: str = Field(default="llava", description="VLM model for descriptions")
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama server URL")
    cleanup_markdown: bool = Field(default=False, description="Clean up markdown with Claude")


class OutputConfig(BaseModel):
    """Output configuration."""

    directory: Path = Field(default=Path("./output"), description="Output directory")
    generate_metadata: bool = Field(default=False, description="Generate JSON metadata")
    create_img_folder: bool = Field(default=True, description="Create img subfolder")


class IngestorConfig(BaseModel):
    """Main configuration for the ingestor."""

    images: ImageConfig = Field(default_factory=ImageConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    youtube: YouTubeConfig = Field(default_factory=YouTubeConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    verbose: bool = Field(default=False, description="Verbose output")

    @classmethod
    def from_yaml(cls, path: Path) -> "IngestorConfig":
        """Load configuration from YAML file.

        Args:
            path: Path to YAML file

        Returns:
            Loaded configuration
        """
        import yaml

        with open(path) as f:
            data = yaml.safe_load(f)

        return cls(**data) if data else cls()

    def to_yaml(self, path: Path) -> None:
        """Save configuration to YAML file.

        Args:
            path: Path to save to
        """
        import yaml

        with open(path, "w") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False)

    @classmethod
    def from_cli_args(
        cls,
        output: Path | None = None,
        keep_raw: bool = False,
        img_to: str = "png",
        describe: bool = False,
        agent: bool = False,
        metadata: bool = False,
        verbose: bool = False,
        **kwargs,
    ) -> "IngestorConfig":
        """Create configuration from CLI arguments.

        Args:
            output: Output directory
            keep_raw: Keep original image formats
            img_to: Target image format
            describe: Enable VLM descriptions
            agent: Enable Claude cleanup
            metadata: Generate metadata
            verbose: Verbose output

        Returns:
            Configuration from CLI args
        """
        config = cls()

        if output:
            config.output.directory = output

        config.images.convert_to_png = not keep_raw
        config.images.target_format = img_to
        config.ai.describe_images = describe
        config.ai.cleanup_markdown = agent
        config.output.generate_metadata = metadata
        config.verbose = verbose

        # Apply any additional kwargs
        for key, value in kwargs.items():
            if hasattr(config.web, key):
                setattr(config.web, key, value)
            elif hasattr(config.youtube, key):
                setattr(config.youtube, key, value)
            elif hasattr(config.audio, key):
                setattr(config.audio, key, value)

        return config


def load_config(path: Path | None = None) -> IngestorConfig:
    """Load configuration from file or return defaults.

    Args:
        path: Optional path to config file

    Returns:
        Configuration
    """
    if path and path.exists():
        return IngestorConfig.from_yaml(path)

    # Check default locations
    default_paths = [
        Path("./ingestor.yaml"),
        Path("./configs/default.yaml"),
        Path.home() / ".config" / "ingestor" / "config.yaml",
    ]

    for default_path in default_paths:
        if default_path.exists():
            return IngestorConfig.from_yaml(default_path)

    return IngestorConfig()
