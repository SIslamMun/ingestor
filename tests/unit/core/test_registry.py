"""Tests for ExtractorRegistry."""


from ingestor.core.registry import ExtractorRegistry, create_default_registry
from ingestor.extractors.base import BaseExtractor
from ingestor.types import MediaType


class MockExtractor(BaseExtractor):
    """Mock extractor for testing."""

    media_type = MediaType.TXT

    async def extract(self, source):
        pass

    def supports(self, source):
        return str(source).endswith(".txt")


class TestExtractorRegistry:
    """Tests for ExtractorRegistry class."""

    def test_register_extractor(self, empty_registry):
        """Test registering an extractor."""
        extractor = MockExtractor()
        empty_registry.register(extractor)

        assert MediaType.TXT in empty_registry
        assert len(empty_registry) == 1

    def test_register_class(self, empty_registry):
        """Test registering an extractor class."""
        empty_registry.register_class(MockExtractor)

        assert MediaType.TXT in empty_registry
        assert isinstance(empty_registry.get(MediaType.TXT), MockExtractor)

    def test_get_extractor(self, empty_registry):
        """Test getting extractor by media type."""
        extractor = MockExtractor()
        empty_registry.register(extractor)

        result = empty_registry.get(MediaType.TXT)
        assert result is extractor

    def test_get_nonexistent(self, empty_registry):
        """Test getting non-existent extractor returns None."""
        result = empty_registry.get(MediaType.PDF)
        assert result is None

    def test_has_media_type(self, empty_registry):
        """Test checking if media type is registered."""
        extractor = MockExtractor()
        empty_registry.register(extractor)

        assert empty_registry.has(MediaType.TXT)
        assert not empty_registry.has(MediaType.PDF)

    def test_list_supported(self, empty_registry):
        """Test listing supported media types."""
        extractor = MockExtractor()
        empty_registry.register(extractor)

        supported = empty_registry.list_supported()
        assert MediaType.TXT in supported
        assert len(supported) == 1

    def test_list_extractors(self, empty_registry):
        """Test listing all extractors."""
        extractor = MockExtractor()
        empty_registry.register(extractor)

        extractors = empty_registry.list_extractors()
        assert extractor in extractors
        assert len(extractors) == 1

    def test_contains(self, empty_registry):
        """Test __contains__ magic method."""
        extractor = MockExtractor()
        empty_registry.register(extractor)

        assert MediaType.TXT in empty_registry
        assert MediaType.PDF not in empty_registry

    def test_len(self, empty_registry):
        """Test __len__ magic method."""
        assert len(empty_registry) == 0

        extractor = MockExtractor()
        empty_registry.register(extractor)
        assert len(empty_registry) == 1

    def test_detector_property(self, empty_registry):
        """Test detector property returns FileDetector."""
        detector = empty_registry.detector
        assert detector is not None


class TestCreateDefaultRegistry:
    """Tests for create_default_registry function."""

    def test_creates_registry(self):
        """Test that factory creates a registry."""
        registry = create_default_registry()
        assert isinstance(registry, ExtractorRegistry)

    def test_registers_txt_extractor(self):
        """Test that TXT extractor is always registered."""
        registry = create_default_registry()
        assert MediaType.TXT in registry

    def test_registers_json_extractor(self):
        """Test that JSON extractor is registered."""
        registry = create_default_registry()
        # JSON should be available as it uses built-in json
        assert MediaType.JSON in registry
