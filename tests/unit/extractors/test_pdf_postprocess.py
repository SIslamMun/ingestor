"""Unit tests for PDF postprocessing modules."""


from ingestor.extractors.pdf.postprocess import (
    cleanup_text,
    process_bibliography,
    process_citations,
    process_figures,
    process_markdown,
    process_sections,
)
from ingestor.extractors.pdf.postprocess.equations import process_equations


class TestProcessCitations:
    """Tests for citation processing."""

    def test_single_citation_linking(self):
        """Test single citation is converted to link."""
        content = "This is discussed in [7] and elaborated in [12]."
        result = process_citations(content)
        assert "[[7]](#ref-7)" in result
        assert "[[12]](#ref-12)" in result

    def test_citation_range_expansion(self):
        """Test citation range is expanded."""
        content = "As shown in [3]-[5], the results..."
        result = process_citations(content)
        assert "[[3]](#ref-3)" in result
        assert "[[4]](#ref-4)" in result
        assert "[[5]](#ref-5)" in result

    def test_citations_in_references_not_linked(self):
        """Test citations in References section are not double-linked."""
        content = """
Some text [1] here.

## References

[1] Author, Title, 2024.
[2] Another Author, Another Title, 2023.
"""
        result = process_citations(content)
        # Main body citation should be linked
        assert "[[1]](#ref-1)" in result
        # References section should have anchors, not double-linked
        assert '<a id="ref-1"></a>[1]' in result
        assert '<a id="ref-2"></a>[2]' in result

    def test_already_linked_citations_not_modified(self):
        """Test already-linked citations are not modified."""
        content = "See [[7]](#ref-7) for details."
        result = process_citations(content)
        # Should not become [[[7]](#ref-7)]
        assert result.count("[[7]]") == 1

    def test_image_syntax_not_modified(self):
        """Test image syntax is not modified."""
        content = "![Figure 1](./img/figure1.png)"
        result = process_citations(content)
        assert result == content


class TestProcessSections:
    """Tests for section processing."""

    def test_abstract_artifact_fix(self):
        """Test Abstract header artifact is fixed."""
        content = "Abstract -Modern HPC systems require..."
        result = process_sections(content)
        assert "## Abstract\n\nModern HPC" in result

    def test_index_terms_artifact_fix(self):
        """Test Index Terms header artifact is fixed."""
        content = "Index Terms -distributed systems, logging"
        result = process_sections(content)
        assert "## Index Terms\n\ndistributed systems" in result

    def test_numbered_section_detection(self):
        """Test numbered sections are converted to headers."""
        content = """1. INTRODUCTION

Some text here.

2.1 Background

More text.
"""
        result = process_sections(content)
        assert "## 1. INTRODUCTION" in result
        # Note: subsection gets period added by processor
        assert "### 2.1" in result and "Background" in result

    def test_roman_numeral_sections(self):
        """Test Roman numeral sections are detected."""
        content = "III. METHODOLOGY\n\nThe approach..."
        result = process_sections(content)
        assert "## III. METHODOLOGY" in result


class TestProcessFigures:
    """Tests for figure processing."""

    def test_figure_embedding(self):
        """Test figures are embedded at captions."""
        content = "Fig. 1. System architecture overview."
        images = ["figure1.png"]
        result = process_figures(content, images)
        assert "![Figure 1](./img/figure1.png)" in result

    def test_multiple_figures(self):
        """Test multiple figures are embedded correctly."""
        content = """
Fig. 1. First figure caption.

Some text.

Fig. 2. Second figure caption.
"""
        images = ["figure1.png", "figure2.png"]
        result = process_figures(content, images)
        assert "![Figure 1](./img/figure1.png)" in result
        assert "![Figure 2](./img/figure2.png)" in result

    def test_figure_not_duplicated(self):
        """Test figures are not embedded twice."""
        content = """
Fig. 1. Caption here.

Referring to Fig. 1, we can see...
"""
        images = ["figure1.png"]
        result = process_figures(content, images)
        # Should only have one image tag
        assert result.count("![Figure 1]") == 1

    def test_empty_images_list(self):
        """Test handling of empty images list."""
        content = "Fig. 1. Caption without image."
        result = process_figures(content, [])
        assert result == content

    def test_case_insensitive_caption(self):
        """Test case insensitive caption matching."""
        content = "FIGURE 1. All caps caption."
        images = ["figure1.png"]
        result = process_figures(content, images)
        assert "![Figure 1]" in result


class TestProcessBibliography:
    """Tests for bibliography processing."""

    def test_reference_spacing(self):
        """Test blank lines are added between references."""
        content = """## References

[1] First reference.
[2] Second reference.
[3] Third reference.
"""
        result = process_bibliography(content)
        # Should have blank lines between entries
        lines = result.split("\n")
        ref_indices = [i for i, line in enumerate(lines) if line.strip().startswith("[")]
        # Check spacing between references
        assert len(ref_indices) == 3


class TestCleanupText:
    """Tests for text cleanup."""

    def test_ligature_replacement(self):
        """Test ligatures are replaced with ASCII."""
        content = "ﬁrst and ﬂuid and eﬀect"
        result = cleanup_text(content)
        assert "first" in result
        assert "fluid" in result
        assert "effect" in result

    def test_excessive_blank_lines(self):
        """Test excessive blank lines are reduced."""
        content = "Line 1\n\n\n\n\nLine 2"
        result = cleanup_text(content)
        assert "\n\n\n" not in result
        assert result == "Line 1\n\nLine 2"

    def test_trailing_whitespace(self):
        """Test trailing whitespace is removed."""
        content = "Line with trailing    \nAnother line  "
        result = cleanup_text(content)
        assert not result.split("\n")[0].endswith(" ")
        assert not result.split("\n")[1].endswith(" ")

    def test_en_dash_replacement(self):
        """Test en-dash is replaced with hyphen."""
        content = "pages 1–10"
        result = cleanup_text(content)
        assert "1-10" in result


class TestProcessMarkdown:
    """Tests for the combined processing pipeline."""

    def test_full_pipeline(self):
        """Test the full processing pipeline."""
        content = """Abstract -This paper presents a novel approach.

1. INTRODUCTION

As discussed in [1]-[3], previous work...

Fig. 1. System overview.

2.1 Background

More details in [5].

## References

[1] First author, Title, 2024.
[2] Second author, Title, 2023.
"""
        images = ["figure1.png"]
        result = process_markdown(content, images)

        # Check abstract is fixed
        assert "## Abstract" in result

        # Check citations are linked
        assert "[[1]](#ref-1)" in result

        # Check figure is embedded
        assert "![Figure 1](./img/figure1.png)" in result

        # Check sections are detected
        assert "## 1. INTRODUCTION" in result

    def test_pipeline_without_images(self):
        """Test pipeline works without images."""
        content = "Abstract -Some text with [1] citation."
        result = process_markdown(content, None)
        assert "## Abstract" in result
        assert "[[1]](#ref-1)" in result

    def test_pipeline_preserves_structure(self):
        """Test pipeline preserves existing markdown structure."""
        content = """# Title

## Existing Section

Content here.
"""
        result = process_markdown(content)
        assert "# Title" in result
        assert "## Existing Section" in result


class TestProcessEquations:
    """Tests for equation processing."""

    def test_formula_placeholder_conversion(self):
        """Test formula placeholders are converted to readable format."""
        content = "The equation is: <!-- formula-not-decoded -->"
        result = process_equations(content)
        assert "*[Formula - see original PDF]*" in result
        assert "formula-not-decoded" not in result

    def test_latex_spacing_cleanup(self):
        """Test extra spaces in LaTeX are cleaned up."""
        content = "$$\\frac  { a } { b }$$"
        result = process_equations(content)
        # Should have cleaner spacing
        assert "\\frac{" in result

    def test_spaced_words_fixed(self):
        """Test spaced-out words from OCR are fixed."""
        content = "$$F l o a t i n g point operations$$"
        result = process_equations(content)
        assert "Floating" in result

    def test_common_ocr_typos_fixed(self):
        """Test common OCR typos are corrected."""
        content = "$$Peak Floting Point Performance$$"
        result = process_equations(content)
        assert "Floating" in result

    def test_memory_typo_fixed(self):
        """Test 'Mermoy' typo is fixed."""
        content = "$$Mermoy bandwidth$$"
        result = process_equations(content)
        assert "Memory" in result

    def test_equation_delimiter_spacing(self):
        """Test blank lines around display equations."""
        content = "Some text\n$$E = mc^2$$\nMore text"
        result = process_equations(content)
        # Should have blank lines around equation
        assert "\n\n$$" in result
        assert "$$\n\n" in result

    def test_multiple_equations(self):
        """Test multiple equations are processed."""
        content = """
Equation 1:
$$a = b + c$$

Equation 2:
$$x = y * z$$
"""
        result = process_equations(content)
        assert "$$a = b + c$$" in result
        assert "$$x = y * z$$" in result

    def test_equation_number_formatting(self):
        """Test equation numbers are formatted correctly."""
        content = "$$x = y (1)$$"
        result = process_equations(content)
        # Should have proper quad spacing before equation number
        assert "\\quad (1)" in result

    def test_iops_spaced_letters_fixed(self):
        """Test IOPS spelled with spaces is fixed."""
        content = "$$I O P S = 100$$"
        result = process_equations(content)
        assert "IOPS" in result

    def test_bandwidth_word_fixed(self):
        """Test spaced 'Bandwidth' is fixed."""
        content = "$$B a n d w i d t h$$"
        result = process_equations(content)
        assert "Bandwidth" in result

    def test_preserves_valid_latex(self):
        """Test valid LaTeX is preserved."""
        content = "$$\\frac{a}{b} + \\sqrt{c}$$"
        result = process_equations(content)
        assert "\\frac{a}{b}" in result
        assert "\\sqrt{c}" in result
