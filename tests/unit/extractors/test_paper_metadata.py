"""Tests for paper metadata extraction and BibTeX generation."""


from parser.doi2bib.metadata import (
    Author,
    PaperMetadata,
)


class TestAuthor:
    """Tests for Author dataclass."""

    def test_basic_author(self):
        """Test basic author creation."""
        author = Author(name="John Doe")
        assert author.name == "John Doe"
        assert author.given is None
        assert author.family is None

    def test_author_with_parts(self):
        """Test author with given/family name parts."""
        author = Author(
            name="John Doe",
            given="John",
            family="Doe",
            orcid="0000-0000-0000-0001",
            affiliations=["MIT", "Harvard"],
        )
        assert author.given == "John"
        assert author.family == "Doe"
        assert author.orcid == "0000-0000-0000-0001"
        assert "MIT" in author.affiliations

    def test_to_dict(self):
        """Test author serialization."""
        author = Author(name="John Doe", given="John", family="Doe")
        data = author.to_dict()
        assert data["name"] == "John Doe"
        assert data["given"] == "John"
        assert data["family"] == "Doe"

    def test_from_dict(self):
        """Test author deserialization."""
        data = {"name": "John Doe", "given": "John", "family": "Doe"}
        author = Author.from_dict(data)
        assert author.name == "John Doe"
        assert author.given == "John"


class TestPaperMetadata:
    """Tests for PaperMetadata dataclass."""

    def test_basic_metadata(self):
        """Test basic metadata creation."""
        meta = PaperMetadata(
            title="Test Paper",
            authors=[Author(name="John Doe")],
            year=2024,
        )
        assert meta.title == "Test Paper"
        assert len(meta.authors) == 1
        assert meta.year == 2024

    def test_first_author(self):
        """Test first_author property."""
        meta = PaperMetadata(
            title="Test",
            authors=[Author(name="John Doe"), Author(name="Jane Smith")],
        )
        assert meta.first_author == "John Doe"

    def test_first_author_empty(self):
        """Test first_author with no authors."""
        meta = PaperMetadata(title="Test")
        assert meta.first_author == "Unknown"

    def test_first_author_last_name(self):
        """Test first_author_last_name property."""
        # With family name
        meta = PaperMetadata(
            title="Test",
            authors=[Author(name="John Doe", family="Doe")],
        )
        assert meta.first_author_last_name == "Doe"

        # Without family name, extract from full name
        meta2 = PaperMetadata(
            title="Test",
            authors=[Author(name="John Doe")],
        )
        assert meta2.first_author_last_name == "Doe"

    def test_author_string_single(self):
        """Test author_string with single author."""
        meta = PaperMetadata(
            title="Test",
            authors=[Author(name="John Doe")],
        )
        assert meta.author_string == "John Doe"

    def test_author_string_two(self):
        """Test author_string with two authors."""
        meta = PaperMetadata(
            title="Test",
            authors=[Author(name="John Doe"), Author(name="Jane Smith")],
        )
        assert meta.author_string == "John Doe and Jane Smith"

    def test_author_string_many(self):
        """Test author_string with many authors."""
        meta = PaperMetadata(
            title="Test",
            authors=[
                Author(name="John Doe"),
                Author(name="Jane Smith"),
                Author(name="Bob Wilson"),
            ],
        )
        assert meta.author_string == "John Doe et al."

    def test_bibtex_key(self):
        """Test BibTeX key generation."""
        meta = PaperMetadata(
            title="Attention Is All You Need",
            authors=[Author(name="Ashish Vaswani", family="Vaswani")],
            year=2017,
        )
        key = meta.bibtex_key
        assert "vaswani" in key.lower()
        assert "2017" in key
        assert "attention" in key.lower()

    def test_bibtex_key_skips_articles(self):
        """Test that BibTeX key skips common articles."""
        meta = PaperMetadata(
            title="The Great Paper",
            authors=[Author(name="John Doe", family="Doe")],
            year=2024,
        )
        key = meta.bibtex_key
        # Should use "great" not "the"
        assert "great" in key.lower()
        assert "the" not in key.lower()


class TestBibTexGeneration:
    """Tests for BibTeX generation."""

    def test_basic_article(self):
        """Test basic article BibTeX."""
        meta = PaperMetadata(
            title="Test Paper",
            authors=[Author(name="John Doe")],
            year=2024,
            venue="Nature",
            doi="10.1038/test",
        )
        bibtex = meta.to_bibtex()
        assert "@article{" in bibtex
        assert "title = {Test Paper}" in bibtex
        assert "author = {John Doe}" in bibtex
        assert "year = {2024}" in bibtex
        assert "journal = {Nature}" in bibtex
        assert "doi = {10.1038/test}" in bibtex

    def test_arxiv_preprint(self):
        """Test arXiv preprint BibTeX."""
        meta = PaperMetadata(
            title="Test Paper",
            authors=[Author(name="John Doe")],
            year=2024,
            arxiv_id="2301.12345",
            subjects=["cs.CL"],
        )
        bibtex = meta.to_bibtex()
        assert "@misc{" in bibtex
        assert "eprint = {2301.12345}" in bibtex
        assert "archiveprefix = {arXiv}" in bibtex
        assert "primaryclass = {cs.CL}" in bibtex

    def test_conference_paper(self):
        """Test conference paper BibTeX."""
        meta = PaperMetadata(
            title="Test Paper",
            authors=[Author(name="John Doe")],
            year=2024,
            venue="NeurIPS 2024",
            publication_type="proceedings-article",
        )
        bibtex = meta.to_bibtex()
        assert "@inproceedings{" in bibtex
        assert "booktitle = {NeurIPS 2024}" in bibtex

    def test_multiple_authors(self):
        """Test BibTeX with multiple authors."""
        meta = PaperMetadata(
            title="Test Paper",
            authors=[
                Author(name="John Doe"),
                Author(name="Jane Smith"),
            ],
            year=2024,
        )
        bibtex = meta.to_bibtex()
        assert "author = {John Doe and Jane Smith}" in bibtex

    def test_custom_key(self):
        """Test BibTeX with custom key."""
        meta = PaperMetadata(
            title="Test Paper",
            authors=[Author(name="John Doe")],
            year=2024,
        )
        bibtex = meta.to_bibtex(key="custom_key")
        assert "@article{custom_key," in bibtex

    def test_special_characters(self):
        """Test BibTeX escapes special characters."""
        meta = PaperMetadata(
            title="Test {Paper} with braces",
            authors=[Author(name="John Doe")],
            year=2024,
        )
        bibtex = meta.to_bibtex()
        # Braces should be escaped
        assert "\\{" in bibtex or "{Paper}" in bibtex

    def test_abstract_included(self):
        """Test that abstract is included in BibTeX."""
        meta = PaperMetadata(
            title="Test Paper",
            authors=[Author(name="John Doe")],
            year=2024,
            abstract="This is the abstract.",
        )
        bibtex = meta.to_bibtex()
        assert "abstract = {This is the abstract.}" in bibtex


class TestMetadataSerialization:
    """Tests for metadata serialization."""

    def test_to_dict(self):
        """Test metadata to dict conversion."""
        meta = PaperMetadata(
            title="Test Paper",
            authors=[Author(name="John Doe")],
            year=2024,
            doi="10.1038/test",
            citation_count=100,
        )
        data = meta.to_dict()
        assert data["title"] == "Test Paper"
        assert len(data["authors"]) == 1
        assert data["year"] == 2024
        assert data["doi"] == "10.1038/test"
        assert data["citation_count"] == 100

    def test_from_dict(self):
        """Test metadata from dict creation."""
        data = {
            "title": "Test Paper",
            "authors": [{"name": "John Doe"}],
            "year": 2024,
            "doi": "10.1038/test",
        }
        meta = PaperMetadata.from_dict(data)
        assert meta.title == "Test Paper"
        assert len(meta.authors) == 1
        assert meta.authors[0].name == "John Doe"
        assert meta.year == 2024
        assert meta.doi == "10.1038/test"

    def test_from_dict_string_authors(self):
        """Test metadata from dict with string authors."""
        data = {
            "title": "Test Paper",
            "authors": ["John Doe", "Jane Smith"],
            "year": 2024,
        }
        meta = PaperMetadata.from_dict(data)
        assert len(meta.authors) == 2
        assert meta.authors[0].name == "John Doe"
        assert meta.authors[1].name == "Jane Smith"

    def test_roundtrip(self):
        """Test dict serialization roundtrip."""
        original = PaperMetadata(
            title="Test Paper",
            authors=[Author(name="John Doe", family="Doe")],
            year=2024,
            doi="10.1038/test",
            arxiv_id="2301.12345",
            citation_count=100,
            keywords=["test", "paper"],
        )
        data = original.to_dict()
        restored = PaperMetadata.from_dict(data)

        assert restored.title == original.title
        assert len(restored.authors) == len(original.authors)
        assert restored.year == original.year
        assert restored.doi == original.doi
        assert restored.arxiv_id == original.arxiv_id
        assert restored.citation_count == original.citation_count
        assert restored.keywords == original.keywords
