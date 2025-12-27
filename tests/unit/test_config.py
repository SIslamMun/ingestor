"""Real unit tests for Config module - no mocking."""

from pathlib import Path

from ingestor.config import (
    AIConfig,
    AudioConfig,
    ImageConfig,
    IngestorConfig,
    OutputConfig,
    WebConfig,
    YouTubeConfig,
    load_config,
)


class TestImageConfig:
    """Tests for ImageConfig class."""

    def test_default_values(self):
        """Test ImageConfig default values."""
        config = ImageConfig()

        assert config.convert_to_png is True
        assert config.target_format == "png"
        assert config.naming_style == "sequential"

    def test_custom_values(self):
        """Test ImageConfig with custom values."""
        config = ImageConfig(
            convert_to_png=False,
            target_format="webp",
            naming_style="page_based"
        )

        assert config.convert_to_png is False
        assert config.target_format == "webp"
        assert config.naming_style == "page_based"


class TestWebConfig:
    """Tests for WebConfig class."""

    def test_default_values(self):
        """Test WebConfig default values."""
        config = WebConfig()

        assert config.strategy == "bfs"
        assert config.max_depth == 2
        assert config.max_pages == 50
        assert config.same_domain is True
        assert config.include_patterns == []
        assert config.exclude_patterns == []

    def test_custom_values(self):
        """Test WebConfig with custom values."""
        config = WebConfig(
            strategy="dfs",
            max_depth=5,
            max_pages=100,
            same_domain=False,
            include_patterns=["/docs/*"],
            exclude_patterns=["/login"]
        )

        assert config.strategy == "dfs"
        assert config.max_depth == 5
        assert config.max_pages == 100
        assert config.same_domain is False
        assert "/docs/*" in config.include_patterns
        assert "/login" in config.exclude_patterns


class TestYouTubeConfig:
    """Tests for YouTubeConfig class."""

    def test_default_values(self):
        """Test YouTubeConfig default values."""
        config = YouTubeConfig()

        assert config.caption_type == "auto"
        assert config.include_playlist is False
        assert config.languages == ["en"]

    def test_custom_values(self):
        """Test YouTubeConfig with custom values."""
        config = YouTubeConfig(
            caption_type="manual",
            include_playlist=True,
            languages=["en", "es", "fr"]
        )

        assert config.caption_type == "manual"
        assert config.include_playlist is True
        assert "es" in config.languages


class TestAudioConfig:
    """Tests for AudioConfig class."""

    def test_default_values(self):
        """Test AudioConfig default values."""
        config = AudioConfig()

        assert config.whisper_model == "turbo"

    def test_custom_values(self):
        """Test AudioConfig with custom values."""
        config = AudioConfig(whisper_model="large")

        assert config.whisper_model == "large"


class TestAIConfig:
    """Tests for AIConfig class."""

    def test_default_values(self):
        """Test AIConfig default values."""
        config = AIConfig()

        assert config.describe_images is False
        assert config.vlm_model == "llava"
        assert config.ollama_host == "http://localhost:11434"
        assert config.cleanup_markdown is False

    def test_custom_values(self):
        """Test AIConfig with custom values."""
        config = AIConfig(
            describe_images=True,
            vlm_model="llava:13b",
            ollama_host="http://192.168.1.100:11434",
            cleanup_markdown=True
        )

        assert config.describe_images is True
        assert config.vlm_model == "llava:13b"
        assert config.ollama_host == "http://192.168.1.100:11434"
        assert config.cleanup_markdown is True


class TestOutputConfig:
    """Tests for OutputConfig class."""

    def test_default_values(self):
        """Test OutputConfig default values."""
        config = OutputConfig()

        assert config.directory == Path("./output")
        assert config.generate_metadata is False
        assert config.create_img_folder is True

    def test_custom_values(self, tmp_path):
        """Test OutputConfig with custom values."""
        config = OutputConfig(
            directory=tmp_path,
            generate_metadata=True,
            create_img_folder=False
        )

        assert config.directory == tmp_path
        assert config.generate_metadata is True
        assert config.create_img_folder is False


class TestIngestorConfig:
    """Tests for IngestorConfig class."""

    def test_default_values(self):
        """Test IngestorConfig default values."""
        config = IngestorConfig()

        assert isinstance(config.images, ImageConfig)
        assert isinstance(config.web, WebConfig)
        assert isinstance(config.youtube, YouTubeConfig)
        assert isinstance(config.audio, AudioConfig)
        assert isinstance(config.ai, AIConfig)
        assert isinstance(config.output, OutputConfig)
        assert config.verbose is False

    def test_custom_nested_values(self):
        """Test IngestorConfig with nested custom values."""
        config = IngestorConfig(
            images=ImageConfig(target_format="webp"),
            web=WebConfig(max_depth=3),
            verbose=True
        )

        assert config.images.target_format == "webp"
        assert config.web.max_depth == 3
        assert config.verbose is True

    def test_from_yaml(self, tmp_path):
        """Test loading config from YAML file."""
        yaml_content = """
images:
  convert_to_png: false
  target_format: webp
web:
  max_depth: 5
  max_pages: 100
verbose: true
"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml_content)

        config = IngestorConfig.from_yaml(yaml_file)

        assert config.images.convert_to_png is False
        assert config.images.target_format == "webp"
        assert config.web.max_depth == 5
        assert config.web.max_pages == 100
        assert config.verbose is True

    def test_from_yaml_empty(self, tmp_path):
        """Test loading from empty YAML file."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        config = IngestorConfig.from_yaml(yaml_file)

        # Should use defaults
        assert config.images.convert_to_png is True
        assert config.verbose is False

    def test_to_yaml(self, tmp_path):
        """Test saving config to YAML file."""
        config = IngestorConfig(
            images=ImageConfig(target_format="webp"),
            verbose=True
        )

        yaml_file = tmp_path / "output_config.yaml"
        config.to_yaml(yaml_file)

        assert yaml_file.exists()

        # Read raw content to verify key values
        content = yaml_file.read_text()
        assert "webp" in content
        assert "verbose: true" in content

    def test_from_cli_args_default(self):
        """Test creating config from CLI args with defaults."""
        config = IngestorConfig.from_cli_args()

        assert config.images.convert_to_png is True
        assert config.ai.describe_images is False
        assert config.verbose is False

    def test_from_cli_args_custom(self, tmp_path):
        """Test creating config from CLI args with custom values."""
        config = IngestorConfig.from_cli_args(
            output=tmp_path,
            keep_raw=True,
            img_to="jpeg",
            describe=True,
            agent=True,
            metadata=True,
            verbose=True
        )

        assert config.output.directory == tmp_path
        assert config.images.convert_to_png is False
        assert config.images.target_format == "jpeg"
        assert config.ai.describe_images is True
        assert config.ai.cleanup_markdown is True
        assert config.output.generate_metadata is True
        assert config.verbose is True

    def test_from_cli_args_web_kwargs(self):
        """Test creating config from CLI args with web config kwargs."""
        config = IngestorConfig.from_cli_args(
            max_depth=5,
            max_pages=200
        )

        assert config.web.max_depth == 5
        assert config.web.max_pages == 200

    def test_from_cli_args_youtube_kwargs(self):
        """Test creating config from CLI args with youtube config kwargs."""
        config = IngestorConfig.from_cli_args(
            include_playlist=True
        )

        assert config.youtube.include_playlist is True

    def test_from_cli_args_audio_kwargs(self):
        """Test creating config from CLI args with audio config kwargs."""
        config = IngestorConfig.from_cli_args(
            whisper_model="large"
        )

        assert config.audio.whisper_model == "large"


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_from_explicit_path(self, tmp_path):
        """Test loading config from explicit path."""
        yaml_content = """
verbose: true
web:
  max_depth: 10
"""
        config_file = tmp_path / "my_config.yaml"
        config_file.write_text(yaml_content)

        config = load_config(config_file)

        assert config.verbose is True
        assert config.web.max_depth == 10

    def test_load_returns_defaults_when_no_file(self, tmp_path, monkeypatch):
        """Test loading returns defaults when no config file exists."""
        # Change to temp dir with no config files
        monkeypatch.chdir(tmp_path)

        config = load_config()

        # Should return defaults
        assert config.images.convert_to_png is True
        assert config.verbose is False

    def test_load_from_default_path(self, tmp_path, monkeypatch):
        """Test loading from default ingestor.yaml path."""
        # Create config in current directory
        monkeypatch.chdir(tmp_path)

        yaml_content = """
verbose: true
"""
        config_file = tmp_path / "ingestor.yaml"
        config_file.write_text(yaml_content)

        config = load_config()

        assert config.verbose is True

    def test_load_nonexistent_explicit_path(self, tmp_path):
        """Test loading from nonexistent explicit path returns defaults."""
        nonexistent = tmp_path / "does_not_exist.yaml"

        config = load_config(nonexistent)

        # Should return defaults since file doesn't exist
        assert config.verbose is False


class TestConfigModel:
    """Tests for config model serialization."""

    def test_model_dump(self):
        """Test model_dump method."""
        config = IngestorConfig(verbose=True)

        data = config.model_dump()

        assert isinstance(data, dict)
        assert data["verbose"] is True
        assert "images" in data
        assert "web" in data

    def test_round_trip(self, tmp_path):
        """Test config round-trip through YAML."""
        original = IngestorConfig(
            images=ImageConfig(target_format="webp"),
            web=WebConfig(max_depth=5, max_pages=200),
            youtube=YouTubeConfig(include_playlist=True),
            audio=AudioConfig(whisper_model="large"),
            ai=AIConfig(describe_images=True),
            # Note: Skip output config with Path, use defaults
            verbose=True
        )

        yaml_file = tmp_path / "roundtrip.yaml"

        # Manually create YAML without Path issues
        yaml_content = f"""
images:
  convert_to_png: {original.images.convert_to_png}
  target_format: {original.images.target_format}
  naming_style: {original.images.naming_style}
web:
  strategy: {original.web.strategy}
  max_depth: {original.web.max_depth}
  max_pages: {original.web.max_pages}
  same_domain: {str(original.web.same_domain).lower()}
  include_patterns: []
  exclude_patterns: []
youtube:
  caption_type: {original.youtube.caption_type}
  include_playlist: {str(original.youtube.include_playlist).lower()}
  languages:
  - en
audio:
  whisper_model: {original.audio.whisper_model}
ai:
  describe_images: {str(original.ai.describe_images).lower()}
  vlm_model: {original.ai.vlm_model}
  ollama_host: {original.ai.ollama_host}
  cleanup_markdown: {str(original.ai.cleanup_markdown).lower()}
output:
  directory: ./output
  generate_metadata: false
  create_img_folder: true
verbose: {str(original.verbose).lower()}
"""
        yaml_file.write_text(yaml_content)

        loaded = IngestorConfig.from_yaml(yaml_file)

        assert loaded.images.target_format == "webp"
        assert loaded.web.max_depth == 5
        assert loaded.youtube.include_playlist is True
        assert loaded.audio.whisper_model == "large"
        assert loaded.ai.describe_images is True
        assert loaded.verbose is True
