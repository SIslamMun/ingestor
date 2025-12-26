"""Tests for citation verifier module."""

import pytest
from pathlib import Path
from ingestor.extractors.paper.verifier import (
    BibEntry,
    CitationVerifier,
    VerificationResult,
    VerificationStats,
    clean_doi,
    normalize,
    titles_match,
    is_website,
    get_arxiv_doi,
    replace_key,
    add_access_date,
    parse_bib_file,
)


class TestBibEntry:
    """Tests for BibEntry parsing."""

    def test_parse_basic_article(self):
        """Test parsing basic article entry."""
        raw = """@article{smith2023,
  title = {A Great Paper},
  author = {Smith, John and Doe, Jane},
  journal = {Nature},
  year = {2023},
  doi = {10.1038/nature12345}
}"""
        entry = BibEntry.parse(raw)
        assert entry is not None
        assert entry.key == "smith2023"
        assert entry.entry_type == "article"
        assert entry.title == "A Great Paper"
        assert entry.doi == "10.1038/nature12345"
        assert entry.author == "Smith, John and Doe, Jane"

    def test_parse_arxiv_entry(self):
        """Test parsing arXiv entry."""
        raw = """@misc{attention2017,
  title = {Attention Is All You Need},
  author = {Vaswani, Ashish},
  year = {2017},
  eprint = {1706.03762},
  archivePrefix = {arXiv},
  primaryClass = {cs.CL}
}"""
        entry = BibEntry.parse(raw)
        assert entry is not None
        assert entry.key == "attention2017"
        assert entry.eprint == "1706.03762"
        assert entry.is_arxiv is True

    def test_parse_website_entry(self):
        """Test parsing website/misc entry."""
        raw = """@misc{github2024,
  title = {My Project},
  howpublished = {\\url{https://github.com/user/repo}},
  note = {Accessed 2024-01-01}
}"""
        entry = BibEntry.parse(raw)
        assert entry is not None
        assert entry.key == "github2024"
        assert "github.com" in entry.howpublished

    def test_parse_invalid(self):
        """Test parsing invalid entry returns None."""
        assert BibEntry.parse("") is None
        assert BibEntry.parse("not a bibtex entry") is None
        assert BibEntry.parse("@article{") is None


class TestCleanDoi:
    """Tests for DOI cleaning."""

    def test_clean_basic(self):
        """Test basic DOI cleaning."""
        assert clean_doi("10.1038/nature12345") == "10.1038/nature12345"

    def test_clean_with_prefix(self):
        """Test DOI with 'DOI ' prefix."""
        assert clean_doi("DOI 10.1038/nature12345") == "10.1038/nature12345"
        assert clean_doi("doi 10.1109/ACCESS.2023") == "10.1109/ACCESS.2023"

    def test_clean_with_braces(self):
        """Test DOI with braces."""
        assert clean_doi("{10.1038/nature12345}") == "10.1038/nature12345"

    def test_clean_with_whitespace(self):
        """Test DOI with whitespace."""
        assert clean_doi("  10.1038/nature12345  ") == "10.1038/nature12345"

    def test_clean_empty(self):
        """Test empty DOI."""
        assert clean_doi(None) == ""
        assert clean_doi("") == ""


class TestNormalize:
    """Tests for string normalization."""

    def test_normalize_basic(self):
        """Test basic normalization."""
        assert normalize("Hello World") == "helloworld"

    def test_normalize_latex(self):
        """Test LaTeX command removal."""
        # The regex removes \cmd{content} -> content
        # H\"ohere -> the \" command captures o, resulting in just o
        assert normalize("H\\\"ohere Informatik") == "hohereinformatik"
        assert normalize("caf\\'{e}") == "cafe"

    def test_normalize_punctuation(self):
        """Test punctuation removal."""
        assert normalize("Machine-Learning: A Survey") == "machinelearningasurvey"

    def test_normalize_empty(self):
        """Test empty string."""
        assert normalize("") == ""
        assert normalize(None) == ""


class TestTitlesMatch:
    """Tests for title matching."""

    def test_exact_match(self):
        """Test exact title match."""
        assert titles_match("Attention Is All You Need", "Attention Is All You Need")

    def test_case_insensitive(self):
        """Test case insensitive matching."""
        assert titles_match("ATTENTION IS ALL YOU NEED", "attention is all you need")

    def test_substring_match(self):
        """Test substring matching."""
        assert titles_match("Attention Is All You Need", "Attention Is All You Need: Transformers")
        assert titles_match("Transformer", "Attention Is All You Need: Transformer Architecture")

    def test_no_match(self):
        """Test non-matching titles."""
        assert not titles_match("Machine Learning", "Deep Learning")

    def test_empty(self):
        """Test empty titles."""
        assert not titles_match("", "Something")
        assert not titles_match("Something", "")


class TestIsWebsite:
    """Tests for website detection."""

    def test_github_is_website(self):
        """Test GitHub URLs are websites."""
        entry = BibEntry(
            key="test",
            entry_type="misc",
            raw="",
            url="https://github.com/user/repo",
        )
        assert is_website(entry) is True

    def test_edu_is_website(self):
        """Test .edu URLs are websites."""
        entry = BibEntry(
            key="test",
            entry_type="misc",
            raw="",
            url="https://cs.stanford.edu/research",
        )
        assert is_website(entry) is True

    def test_arxiv_is_not_website(self):
        """Test arXiv is not a website."""
        entry = BibEntry(
            key="test",
            entry_type="misc",
            raw="",
            url="https://arxiv.org/abs/1706.03762",
        )
        assert is_website(entry) is False

    def test_arxiv_entry_is_not_website(self):
        """Test arXiv entry is not a website."""
        entry = BibEntry(
            key="test",
            entry_type="misc",
            raw="",
            eprint="1706.03762",
            is_arxiv=True,
        )
        assert is_website(entry) is False

    def test_conference_paper_is_not_website(self):
        """Test conference paper is not a website."""
        entry = BibEntry(
            key="test",
            entry_type="inproceedings",
            raw="",
            booktitle="NeurIPS 2023",
        )
        assert is_website(entry) is False


class TestGetArxivDoi:
    """Tests for arXiv DOI generation."""

    def test_basic_eprint(self):
        """Test basic eprint to DOI conversion."""
        entry = BibEntry(
            key="test",
            entry_type="misc",
            raw="",
            eprint="1706.03762",
        )
        assert get_arxiv_doi(entry) == "10.48550/arXiv.1706.03762"

    def test_no_eprint(self):
        """Test entry without eprint."""
        entry = BibEntry(
            key="test",
            entry_type="article",
            raw="",
        )
        assert get_arxiv_doi(entry) is None


class TestReplaceKey:
    """Tests for citation key replacement."""

    def test_replace_key(self):
        """Test basic key replacement."""
        bibtex = "@article{old_key,\n  title = {Test}\n}"
        result = replace_key(bibtex, "new_key")
        assert "@article{new_key," in result
        assert "old_key" not in result

    def test_replace_key_preserves_content(self):
        """Test key replacement preserves content."""
        bibtex = "@article{old_key,\n  title = {Test},\n  year = {2023}\n}"
        result = replace_key(bibtex, "new_key")
        assert "title = {Test}" in result
        assert "year = {2023}" in result


class TestAddAccessDate:
    """Tests for access date addition."""

    def test_add_to_entry_without_note(self):
        """Test adding access date to entry without note."""
        bibtex = "@misc{test,\n  title = {Test}\n}"
        result = add_access_date(bibtex)
        assert "note = {Last accessed:" in result

    def test_append_to_existing_note(self):
        """Test appending access date to existing note."""
        bibtex = "@misc{test,\n  title = {Test},\n  note = {Some note}\n}"
        result = add_access_date(bibtex)
        assert "Some note, Last accessed:" in result

    def test_skip_if_already_has_accessed(self):
        """Test skipping if already has accessed date."""
        bibtex = "@misc{test,\n  note = {Accessed 2024-01-01}\n}"
        result = add_access_date(bibtex)
        assert result == bibtex  # Unchanged


class TestParseBibFile:
    """Tests for BibTeX file parsing."""

    def test_parse_multiple_entries(self, tmp_path):
        """Test parsing file with multiple entries."""
        bib_content = """@article{paper1,
  title = {First Paper},
  doi = {10.1000/paper1}
}

@article{paper2,
  title = {Second Paper},
  doi = {10.1000/paper2}
}"""
        bib_file = tmp_path / "test.bib"
        bib_file.write_text(bib_content)
        
        entries = parse_bib_file(bib_file)
        assert len(entries) == 2
        assert entries[0].key == "paper1"
        assert entries[1].key == "paper2"

    def test_parse_empty_file(self, tmp_path):
        """Test parsing empty file."""
        bib_file = tmp_path / "empty.bib"
        bib_file.write_text("")
        
        entries = parse_bib_file(bib_file)
        assert len(entries) == 0

    def test_parse_nonexistent_file(self, tmp_path):
        """Test parsing nonexistent file."""
        entries = parse_bib_file(tmp_path / "nonexistent.bib")
        assert len(entries) == 0


class TestVerificationStats:
    """Tests for VerificationStats."""

    def test_total_verified(self):
        """Test total_verified calculation."""
        stats = VerificationStats(
            verified=5,
            arxiv=3,
            searched=2,
            website=4,
            manual=1,
            failed=3,
        )
        assert stats.total_verified == 15
        assert stats.total == 18

    def test_default_values(self):
        """Test default values are zero."""
        stats = VerificationStats()
        assert stats.verified == 0
        assert stats.total_verified == 0
        assert stats.total == 0


class TestCitationVerifier:
    """Tests for CitationVerifier class."""

    @pytest.fixture
    def verifier(self):
        """Create a verifier instance."""
        return CitationVerifier(email="test@example.com", rate_limit=0.01)

    @pytest.mark.asyncio
    async def test_verify_website_entry(self, verifier):
        """Test verifying a website entry."""
        entry = BibEntry(
            key="github_test",
            entry_type="misc",
            raw="@misc{github_test,\n  title = {Test},\n  url = {https://github.com/test}\n}",
            url="https://github.com/test",
        )
        
        result = await verifier.verify_entry(entry)
        assert result.status == "website"
        assert "github_test" == result.key
        assert "Last accessed:" in result.bibtex

    @pytest.mark.asyncio
    async def test_verify_skipped_entry(self, verifier):
        """Test skipping verification for specified keys."""
        entry = BibEntry(
            key="skip_me",
            entry_type="article",
            raw="@article{skip_me,\n  title = {Test}\n}",
        )
        
        result = await verifier.verify_entry(entry, skip_keys={"skip_me"})
        assert result.status == "manual"
        assert "skipped verification" in result.message.lower()

    @pytest.mark.asyncio
    async def test_verify_file_dry_run(self, verifier, tmp_path):
        """Test dry run mode doesn't write files."""
        bib_content = """@misc{github_test,
  title = {Test Project},
  url = {https://github.com/test/project}
}"""
        bib_file = tmp_path / "test.bib"
        bib_file.write_text(bib_content)
        output_dir = tmp_path / "output"
        
        stats, results = await verifier.verify_file(
            input_path=bib_file,
            output_dir=output_dir,
            dry_run=True,
        )
        
        # Output should not be created
        assert not output_dir.exists()
        # But results should be returned
        assert len(results) == 1
        assert stats.website == 1

    @pytest.mark.asyncio
    async def test_verify_file_writes_output(self, verifier, tmp_path):
        """Test file verification writes output."""
        bib_content = """@misc{github_test,
  title = {Test Project},
  url = {https://github.com/test/project}
}"""
        bib_file = tmp_path / "test.bib"
        bib_file.write_text(bib_content)
        output_dir = tmp_path / "output"
        
        stats, results = await verifier.verify_file(
            input_path=bib_file,
            output_dir=output_dir,
            dry_run=False,
        )
        
        # Check output files
        assert (output_dir / "verified.bib").exists()
        assert (output_dir / "failed.bib").exists()
        assert (output_dir / "report.md").exists()
        
        # Check verified.bib content
        verified_content = (output_dir / "verified.bib").read_text()
        assert "github_test" in verified_content
