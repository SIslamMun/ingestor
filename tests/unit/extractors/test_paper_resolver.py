"""Tests for paper identifier resolution."""


from parser.doi2bib.resolver import (
    IdentifierType,
    PaperIdentifier,
    arxiv_id_to_doi,
    normalize_arxiv_id,
    normalize_doi,
    resolve_identifier,
)


class TestResolveIdentifier:
    """Tests for resolve_identifier function."""

    def test_doi_basic(self):
        """Test basic DOI resolution."""
        result = resolve_identifier("10.1038/nature12373")
        assert result.type == IdentifierType.DOI
        assert result.value == "10.1038/nature12373"
        assert result.doi == "10.1038/nature12373"

    def test_doi_with_prefix(self):
        """Test DOI with doi: prefix."""
        result = resolve_identifier("doi:10.1038/nature12373")
        assert result.type == IdentifierType.DOI
        assert result.doi == "10.1038/nature12373"

    def test_doi_url(self):
        """Test DOI URL resolution."""
        result = resolve_identifier("https://doi.org/10.1038/nature12373")
        assert result.type == IdentifierType.DOI
        assert result.doi == "10.1038/nature12373"

    def test_doi_dx_url(self):
        """Test dx.doi.org URL resolution."""
        result = resolve_identifier("http://dx.doi.org/10.1038/nature12373")
        assert result.type == IdentifierType.DOI
        assert result.doi == "10.1038/nature12373"

    def test_arxiv_new_format(self):
        """Test new arXiv ID format (YYMM.NNNNN)."""
        result = resolve_identifier("2301.12345")
        assert result.type == IdentifierType.ARXIV
        assert result.value == "2301.12345"
        assert result.arxiv_id == "2301.12345"
        assert result.doi == "10.48550/arXiv.2301.12345"

    def test_arxiv_with_prefix(self):
        """Test arXiv ID with arXiv: prefix."""
        result = resolve_identifier("arXiv:2301.12345")
        assert result.type == IdentifierType.ARXIV
        assert result.arxiv_id == "2301.12345"

    def test_arxiv_with_version(self):
        """Test arXiv ID with version suffix."""
        result = resolve_identifier("arXiv:2301.12345v2")
        assert result.type == IdentifierType.ARXIV
        assert "2301.12345" in result.arxiv_id

    def test_arxiv_url(self):
        """Test arXiv URL resolution."""
        result = resolve_identifier("https://arxiv.org/abs/2301.12345")
        assert result.type == IdentifierType.ARXIV
        assert result.arxiv_id == "2301.12345"

    def test_arxiv_pdf_url(self):
        """Test arXiv PDF URL resolution."""
        result = resolve_identifier("https://arxiv.org/pdf/2301.12345")
        assert result.type == IdentifierType.ARXIV
        assert result.arxiv_id == "2301.12345"

    def test_arxiv_old_format(self):
        """Test old arXiv ID format (category/NNNNNNN)."""
        result = resolve_identifier("hep-th/9901001")
        assert result.type == IdentifierType.ARXIV
        assert result.value == "hep-th/9901001"

    def test_arxiv_doi(self):
        """Test arXiv DOI format (10.48550/arXiv.XXXX.XXXXX)."""
        result = resolve_identifier("10.48550/arXiv.2301.12345")
        assert result.type == IdentifierType.ARXIV
        assert result.arxiv_id == "2301.12345"
        assert result.doi == "10.48550/arXiv.2301.12345"

    def test_semantic_scholar_url(self):
        """Test Semantic Scholar URL resolution."""
        result = resolve_identifier(
            "https://www.semanticscholar.org/paper/Attention-is-All-You-Need-Vaswani-Shazeer/"
            "204e3073870fae3d05bcbc2f6a8e263d9b72e776"
        )
        assert result.type == IdentifierType.SEMANTIC_SCHOLAR
        assert result.value == "204e3073870fae3d05bcbc2f6a8e263d9b72e776"

    def test_semantic_scholar_id(self):
        """Test Semantic Scholar corpus ID resolution."""
        result = resolve_identifier("204e3073870fae3d05bcbc2f6a8e263d9b72e776")
        assert result.type == IdentifierType.SEMANTIC_SCHOLAR
        assert result.value == "204e3073870fae3d05bcbc2f6a8e263d9b72e776"

    def test_openalex_id(self):
        """Test OpenAlex ID resolution."""
        result = resolve_identifier("W2741809807")
        assert result.type == IdentifierType.OPENALEX
        assert result.value == "W2741809807"

    def test_openalex_url(self):
        """Test OpenAlex URL resolution."""
        result = resolve_identifier("https://openalex.org/W2741809807")
        assert result.type == IdentifierType.OPENALEX
        assert result.value == "W2741809807"

    def test_pubmed_id(self):
        """Test PubMed ID resolution."""
        result = resolve_identifier("PMID:12345678")
        assert result.type == IdentifierType.PUBMED
        assert result.value == "12345678"

    def test_pubmed_url(self):
        """Test PubMed URL resolution."""
        result = resolve_identifier("https://pubmed.ncbi.nlm.nih.gov/12345678")
        assert result.type == IdentifierType.PUBMED
        assert result.value == "12345678"

    def test_pmc_id(self):
        """Test PMC ID resolution."""
        result = resolve_identifier("PMC1234567")
        assert result.type == IdentifierType.PMC
        assert result.value == "PMC1234567"

    def test_pdf_url(self):
        """Test direct PDF URL resolution."""
        result = resolve_identifier("https://example.com/paper.pdf")
        assert result.type == IdentifierType.PDF_URL
        assert result.url == "https://example.com/paper.pdf"

    def test_title_fallback(self):
        """Test title search fallback."""
        result = resolve_identifier("Attention Is All You Need")
        assert result.type == IdentifierType.TITLE
        assert result.value == "Attention Is All You Need"

    def test_whitespace_handling(self):
        """Test that whitespace is stripped."""
        result = resolve_identifier("  10.1038/nature12373  ")
        assert result.type == IdentifierType.DOI
        assert result.doi == "10.1038/nature12373"


class TestNormalizeDoi:
    """Tests for normalize_doi function."""

    def test_basic_doi(self):
        """Test basic DOI normalization."""
        assert normalize_doi("10.1038/nature12373") == "10.1038/nature12373"

    def test_doi_with_url_prefix(self):
        """Test DOI with URL prefix."""
        assert normalize_doi("https://doi.org/10.1038/nature12373") == "10.1038/nature12373"
        assert normalize_doi("http://dx.doi.org/10.1038/nature12373") == "10.1038/nature12373"

    def test_doi_with_prefix(self):
        """Test DOI with doi: prefix."""
        assert normalize_doi("doi:10.1038/nature12373") == "10.1038/nature12373"
        assert normalize_doi("DOI:10.1038/nature12373") == "10.1038/nature12373"


class TestNormalizeArxivId:
    """Tests for normalize_arxiv_id function."""

    def test_basic_arxiv_id(self):
        """Test basic arXiv ID normalization."""
        assert normalize_arxiv_id("2301.12345") == "2301.12345"

    def test_arxiv_with_prefix(self):
        """Test arXiv ID with prefix."""
        assert normalize_arxiv_id("arXiv:2301.12345") == "2301.12345"

    def test_arxiv_url(self):
        """Test arXiv URL normalization."""
        assert normalize_arxiv_id("https://arxiv.org/abs/2301.12345") == "2301.12345"
        assert normalize_arxiv_id("https://arxiv.org/pdf/2301.12345.pdf") == "2301.12345"


class TestArxivIdToDoi:
    """Tests for arxiv_id_to_doi function."""

    def test_basic_conversion(self):
        """Test basic arXiv ID to DOI conversion."""
        assert arxiv_id_to_doi("2301.12345") == "10.48550/arXiv.2301.12345"

    def test_with_prefix(self):
        """Test conversion with arXiv: prefix."""
        assert arxiv_id_to_doi("arXiv:2301.12345") == "10.48550/arXiv.2301.12345"


class TestPaperIdentifier:
    """Tests for PaperIdentifier dataclass."""

    def test_has_doi(self):
        """Test has_doi property."""
        with_doi = PaperIdentifier(
            original="10.1038/nature12373",
            type=IdentifierType.DOI,
            value="10.1038/nature12373",
            doi="10.1038/nature12373",
        )
        assert with_doi.has_doi is True

        without_doi = PaperIdentifier(
            original="Title",
            type=IdentifierType.TITLE,
            value="Title",
        )
        assert without_doi.has_doi is False

    def test_str_representation(self):
        """Test string representation."""
        doi_id = PaperIdentifier(
            original="10.1038/nature12373",
            type=IdentifierType.DOI,
            value="10.1038/nature12373",
            doi="10.1038/nature12373",
        )
        assert str(doi_id) == "DOI:10.1038/nature12373"

        arxiv_id = PaperIdentifier(
            original="2301.12345",
            type=IdentifierType.ARXIV,
            value="2301.12345",
            arxiv_id="2301.12345",
        )
        assert str(arxiv_id) == "arXiv:2301.12345"
