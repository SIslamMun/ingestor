"""Extractors for various media formats."""

# Archive extractor
from .archive import ZipExtractor

# Audio extractor
from .audio import AudioExtractor
from .base import BaseExtractor

# Data extractors
from .data import CsvExtractor, JsonExtractor, XmlExtractor
from .docx import DocxExtractor
from .epub import EpubExtractor

# Spreadsheet extractors
from .excel import XlsExtractor, XlsxExtractor

# Image extractor
from .image import ImageExtractor
from .pdf import PdfExtractor
from .pptx import PptxExtractor

# Document extractors
from .text import TxtExtractor

# Web extractors
from .web import WebExtractor
from .youtube import YouTubeExtractor

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
]
