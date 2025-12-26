"""Extractors for various media formats."""

from .base import BaseExtractor

# Document extractors
from .text import TxtExtractor
from .pdf import PdfExtractor
from .docx import DocxExtractor
from .pptx import PptxExtractor
from .epub import EpubExtractor

# Spreadsheet extractors
from .excel import XlsxExtractor, XlsExtractor

# Data extractors
from .data import CsvExtractor, JsonExtractor, XmlExtractor

# Web extractors
from .web import WebExtractor
from .youtube import YouTubeExtractor

# Audio extractor
from .audio import AudioExtractor

# Archive extractor
from .archive import ZipExtractor

# Image extractor
from .image import ImageExtractor

# Paper extractor (scientific papers from DOI, arXiv, etc.)
from .paper import PaperExtractor, PaperConfig

__all__ = [
    "BaseExtractor",
    # Documents
    "TxtExtractor",
    "PdfExtractor",
    "DocxExtractor",
    "PptxExtractor",
    "EpubExtractor",
    # Spreadsheets
    "XlsxExtractor",
    "XlsExtractor",
    # Data
    "CsvExtractor",
    "JsonExtractor",
    "XmlExtractor",
    # Web
    "WebExtractor",
    "YouTubeExtractor",
    # Audio
    "AudioExtractor",
    # Archive
    "ZipExtractor",
    # Image
    "ImageExtractor",
    # Paper
    "PaperExtractor",
    "PaperConfig",
]
