"""Tests for ImageNamer."""


from ingestor.images.naming import PATTERNS, ImageNamer, create_namer
from ingestor.types import ExtractedImage


class TestImageNamer:
    """Tests for ImageNamer class."""

    def test_default_pattern(self):
        """Test default sequential naming pattern."""
        namer = ImageNamer()
        image = ExtractedImage(filename="orig.png", data=b"", format="png")

        name = namer.generate(image)

        assert name == "figure_001.png"

    def test_sequential_numbering(self):
        """Test that numbers increment."""
        namer = ImageNamer()

        names = []
        for i in range(3):
            image = ExtractedImage(filename=f"img{i}.png", data=b"", format="png")
            names.append(namer.generate(image))

        assert names == ["figure_001.png", "figure_002.png", "figure_003.png"]

    def test_page_based_pattern(self):
        """Test page-based naming pattern."""
        namer = ImageNamer(pattern="page{page}_img{page_num}")
        image = ExtractedImage(filename="a.png", data=b"", format="png", page=5)

        name = namer.generate(image)

        assert name == "page5_img1.png"

    def test_source_based_pattern(self):
        """Test source-based naming pattern."""
        namer = ImageNamer(pattern="{source}_{num:03d}")
        image = ExtractedImage(filename="a.png", data=b"", format="png")

        name = namer.generate(image, source_name="Document.docx")

        assert name == "document_{num:03d}.png" or "document" in name.lower()

    def test_prefix(self):
        """Test adding prefix to filenames."""
        namer = ImageNamer(prefix="doc1")
        image = ExtractedImage(filename="a.png", data=b"", format="png")

        name = namer.generate(image)

        assert name.startswith("doc1_")

    def test_reset_counter(self):
        """Test counter reset."""
        namer = ImageNamer()
        image = ExtractedImage(filename="a.png", data=b"", format="png")

        namer.generate(image)
        namer.generate(image)
        namer.reset()
        name = namer.generate(image)

        assert name == "figure_001.png"

    def test_rename_returns_new_image(self):
        """Test rename creates new ExtractedImage."""
        namer = ImageNamer()
        image = ExtractedImage(
            filename="original.png",
            data=b"test_data",
            format="png",
            page=3,
            caption="A caption",
        )

        renamed = namer.rename(image)

        assert renamed.filename == "figure_001.png"
        assert renamed.data == b"test_data"
        assert renamed.page == 3
        assert renamed.caption == "A caption"

    def test_rename_all(self):
        """Test batch rename."""
        namer = ImageNamer()
        images = [
            ExtractedImage(filename=f"img{i}.png", data=b"", format="png")
            for i in range(3)
        ]

        renamed = namer.rename_all(images)

        assert len(renamed) == 3
        assert renamed[0].filename == "figure_001.png"
        assert renamed[1].filename == "figure_002.png"
        assert renamed[2].filename == "figure_003.png"

    def test_sanitize_source_name(self):
        """Test source name sanitization."""
        namer = ImageNamer(pattern="{source}_{num:03d}")
        image = ExtractedImage(filename="a.png", data=b"", format="png")

        name = namer.generate(image, source_name="My Document (v2).docx")

        # Should not contain spaces or special chars
        assert " " not in name
        assert "(" not in name


class TestCreateNamer:
    """Tests for create_namer factory function."""

    def test_sequential_style(self):
        """Test creating sequential namer."""
        namer = create_namer("sequential")
        assert namer.pattern == PATTERNS["sequential"]

    def test_page_based_style(self):
        """Test creating page-based namer."""
        namer = create_namer("page_based")
        assert namer.pattern == PATTERNS["page_based"]

    def test_with_prefix(self):
        """Test creating namer with prefix."""
        namer = create_namer("sequential", prefix="test")
        assert namer.prefix == "test"

    def test_unknown_style_uses_default(self):
        """Test unknown style falls back to sequential."""
        namer = create_namer("nonexistent")
        assert namer.pattern == PATTERNS["sequential"]
