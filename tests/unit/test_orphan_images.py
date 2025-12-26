"""Unit tests for orphan image detection and recovery."""

import pytest

from ingestor.postprocess.orphan_images import (
    detect_orphan_images,
    recover_orphan_images,
    find_figure_references,
    analyze_document_structure,
    smart_insert_images,
    _generate_alt_text,
    OrphanImageResult,
)


class TestDetectOrphanImages:
    """Tests for detect_orphan_images function."""

    def test_no_orphans_all_referenced(self):
        """Test when all images are referenced."""
        markdown = """# Document

Here is some text.

![Figure 1](./img/figure_001.png)

More text.

![Chart](./img/chart.png)
"""
        images = ["figure_001.png", "chart.png"]
        result = detect_orphan_images(markdown, images)

        assert not result.has_orphans
        assert len(result.orphan_images) == 0
        assert len(result.referenced_images) == 2
        assert result.total_images == 2
        assert result.total_references == 2

    def test_all_orphans_none_referenced(self):
        """Test when no images are referenced."""
        markdown = """# Document

Just text, no images referenced.
"""
        images = ["figure_001.png", "chart.png", "diagram.png"]
        result = detect_orphan_images(markdown, images)

        assert result.has_orphans
        assert len(result.orphan_images) == 3
        assert len(result.referenced_images) == 0
        assert result.total_images == 3
        assert result.total_references == 0

    def test_partial_orphans(self):
        """Test when some images are orphaned."""
        markdown = """# Document

![Figure 1](./img/figure_001.png)

Some text without image reference.
"""
        images = ["figure_001.png", "figure_002.png", "table.png"]
        result = detect_orphan_images(markdown, images)

        assert result.has_orphans
        assert set(result.orphan_images) == {"figure_002.png", "table.png"}
        assert result.referenced_images == ["figure_001.png"]
        assert result.total_images == 3
        assert result.total_references == 1

    def test_missing_images(self):
        """Test detection of references to non-existent images."""
        markdown = """# Document

![Figure 1](./img/figure_001.png)
![Missing](./img/not_extracted.png)
"""
        images = ["figure_001.png"]
        result = detect_orphan_images(markdown, images)

        assert result.has_missing
        assert "not_extracted.png" in result.missing_images

    def test_handles_different_path_formats(self):
        """Test that different path formats are handled."""
        markdown = """
![Alt](./img/image1.png)
![Alt](img/image2.png)
![Alt](/img/image3.png)
"""
        images = ["image1.png", "image2.png", "image3.png"]
        result = detect_orphan_images(markdown, images)

        assert not result.has_orphans
        assert len(result.referenced_images) == 3

    def test_summary_generation(self):
        """Test summary string generation."""
        markdown = "![](./img/img1.png)"
        images = ["img1.png", "img2.png"]
        result = detect_orphan_images(markdown, images)

        summary = result.summary()
        assert "Total images: 2" in summary
        assert "Orphaned: 1" in summary
        assert "img2.png" in summary


class TestRecoverOrphanImages:
    """Tests for recover_orphan_images function."""

    def test_no_orphans_returns_unchanged(self):
        """Test that markdown is unchanged when no orphans."""
        markdown = "# Test\n\nContent here."
        result = recover_orphan_images(markdown, [])
        assert result == markdown

    def test_append_at_end(self):
        """Test appending orphans at end."""
        markdown = "# Test\n\nContent here."
        orphans = ["img1.png", "img2.png"]
        result = recover_orphan_images(markdown, orphans, position="end")

        assert "## Additional Images" in result
        assert "![Img1](./img/img1.png)" in result
        assert "![Img2](./img/img2.png)" in result

    def test_append_as_section(self):
        """Test appending as named section."""
        markdown = "# Test\n\nContent here."
        orphans = ["figure.png"]
        result = recover_orphan_images(
            markdown, orphans, position="section", section_title="Figures"
        )

        assert "## Figures" in result
        assert "![Figure](./img/figure.png)" in result

    def test_custom_image_dir(self):
        """Test with custom image directory."""
        markdown = "# Test"
        orphans = ["img.png"]
        result = recover_orphan_images(markdown, orphans, image_dir="./images")

        assert "![Img](./images/img.png)" in result


class TestGenerateAltText:
    """Tests for alt text generation from filename."""

    def test_simple_filename(self):
        """Test simple filename conversion."""
        assert _generate_alt_text("figure.png") == "Figure"

    def test_filename_with_numbers(self):
        """Test filename with number padding."""
        assert _generate_alt_text("figure_001.png") == "Figure 1"
        assert _generate_alt_text("image_12.jpg") == "Image 12"

    def test_filename_with_hash(self):
        """Test removal of hash suffix."""
        assert _generate_alt_text("image_1_9cd53a2f.png") == "Image 1"

    def test_complex_filename(self):
        """Test complex filename patterns."""
        assert _generate_alt_text("slide3_img2.png") == "Slide3 Img2"

    def test_underscores_to_spaces(self):
        """Test underscore to space conversion."""
        assert _generate_alt_text("my_image_name.png") == "My Image Name"


class TestFindFigureReferences:
    """Tests for finding figure references in text."""

    def test_finds_figure_patterns(self):
        """Test detection of figure patterns."""
        text = "As shown in Figure 1, the results... See Fig. 2 for details."
        refs = find_figure_references(text)

        assert len(refs) >= 2
        ref_texts = [r[0] for r in refs]
        assert any("Figure 1" in t for t in ref_texts)
        assert any("Fig. 2" in t for t in ref_texts)

    def test_finds_directional_refs(self):
        """Test detection of directional references."""
        text = "As shown in the figure below, the system works."
        refs = find_figure_references(text)

        assert len(refs) >= 1
        assert any("figure below" in r[0].lower() for r in refs)

    def test_case_insensitive(self):
        """Test case insensitive matching."""
        text = "FIGURE 1 and figure 2 and Figure 3"
        refs = find_figure_references(text)

        # Should find all three
        assert len(refs) >= 3


class TestAnalyzeDocumentStructure:
    """Tests for document structure analysis."""

    def test_finds_sections(self):
        """Test heading detection."""
        markdown = """# Title

## Section 1

Content

### Subsection

More content

## Section 2
"""
        analysis = analyze_document_structure(markdown)

        assert len(analysis["sections"]) == 4
        assert analysis["sections"][0][0] == "Title"
        assert analysis["sections"][0][1] == 1  # h1
        assert analysis["sections"][1][1] == 2  # h2

    def test_finds_figure_refs(self):
        """Test figure reference detection in analysis."""
        markdown = """# Document

As shown in Figure 1, the system...

See Fig. 2 below.
"""
        analysis = analyze_document_structure(markdown)

        assert len(analysis["figure_refs"]) >= 2


class TestSmartInsertImages:
    """Tests for smart image insertion."""

    def test_no_orphans_unchanged(self):
        """Test unchanged when no orphans."""
        markdown = "# Test\n\nContent"
        result = smart_insert_images(markdown, [])
        assert result == markdown

    def test_matches_figure_numbers(self):
        """Test matching images to figure references by number."""
        markdown = """# Results

As shown in Figure 1, the data indicates...

More analysis in Figure 2 reveals...
"""
        orphans = ["figure_1.png", "figure_2.png"]
        result = smart_insert_images(markdown, orphans)

        # Should have inserted images after their respective paragraphs
        assert "![Figure 1](./img/figure_1.png)" in result
        assert "![Figure 2](./img/figure_2.png)" in result

    def test_unmatched_goes_to_end(self):
        """Test that unmatched images go to end."""
        markdown = "# Test\n\nNo figure references here."
        orphans = ["random_img.png"]
        result = smart_insert_images(markdown, orphans)

        assert "## Additional Images" in result
        assert "random_img.png" in result


class TestIntegration:
    """Integration tests for orphan image workflow."""

    def test_full_workflow(self):
        """Test complete detect -> recover workflow."""
        markdown = """# Document Title

Here is the introduction.

As shown in Figure 1, the results are significant.

## Methods

The methodology involves several steps.
"""
        images = ["figure_1.png", "methodology_diagram.png"]

        # Detect orphans
        detection = detect_orphan_images(markdown, images)
        assert detection.has_orphans
        assert "methodology_diagram.png" in detection.orphan_images

        # Smart insert
        result = smart_insert_images(markdown, detection.orphan_images)

        # figure_1.png should be placed near "Figure 1" reference
        assert "figure_1.png" in result

        # methodology_diagram should be at the end
        assert "methodology_diagram.png" in result

    def test_empty_document(self):
        """Test handling of empty document."""
        result = detect_orphan_images("", ["img.png"])
        assert result.has_orphans
        assert result.orphan_images == ["img.png"]

    def test_no_images(self):
        """Test handling when no images provided."""
        markdown = "# Test\n\n![Missing](./img/missing.png)"
        result = detect_orphan_images(markdown, [])
        
        assert not result.has_orphans
        assert result.total_images == 0
        assert result.has_missing
        assert "missing.png" in result.missing_images
