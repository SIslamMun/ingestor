"""Equation processing: clean up LaTeX equations and fix OCR artifacts.

Handles LaTeX equations extracted by Docling's formula enrichment.
"""

from __future__ import annotations

import re


def process_equations(content: str) -> str:
    """
    Process LaTeX equations in markdown content.

    Handles:
    - Cleaning up OCR artifacts in equations
    - Normalizing equation delimiters
    - Fixing common LaTeX spacing issues
    - Converting placeholder markers to proper format

    Args:
        content: Markdown content with equations

    Returns:
        Content with cleaned equations
    """
    content = _fix_formula_placeholders(content)
    content = _clean_latex_spacing(content)
    content = _fix_common_ocr_artifacts(content)
    content = _normalize_equation_delimiters(content)
    return content


def _fix_formula_placeholders(content: str) -> str:
    """
    Convert formula placeholder comments to a cleaner format.

    <!-- formula-not-decoded --> → [Formula not decoded]
    """
    content = re.sub(
        r"<!--\s*formula-not-decoded\s*-->",
        r"*[Formula - see original PDF]*",
        content,
        flags=re.IGNORECASE,
    )
    return content


def _clean_latex_spacing(content: str) -> str:
    """
    Fix spacing issues in LaTeX equations from OCR.

    Handles patterns like:
    - "O r e p a l i n s i t y" → "Operationality" (spaced letters)
    - Extra spaces around operators
    """
    def clean_equation(match: re.Match[str]) -> str:
        eq = match.group(1)

        # Fix spaced-out words (common OCR artifact)
        # Pattern: single letters separated by spaces that form words
        # e.g., "F l o a t i n g" → "Floating"
        eq = _fix_spaced_words(eq)

        # Fix extra spaces around common LaTeX commands
        eq = re.sub(r"\\\s+", r"\\", eq)  # \\ frac → \\frac
        eq = re.sub(r"\\text\s*\{", r"\\text{", eq)
        eq = re.sub(r"\\frac\s*\{", r"\\frac{", eq)
        eq = re.sub(r"\\min\s*\(", r"\\min(", eq)
        eq = re.sub(r"\\max\s*\(", r"\\max(", eq)

        # Clean up multiple spaces
        eq = re.sub(r"\s{2,}", " ", eq)

        return f"$${eq}$$"

    # Process display math ($$...$$)
    content = re.sub(r"\$\$(.*?)\$\$", clean_equation, content, flags=re.DOTALL)

    return content


def _fix_spaced_words(text: str) -> str:
    """
    Fix words that have spaces between each letter (OCR artifact).

    e.g., "F l o a t i n g" → "Floating"
    """
    # Common words that appear spaced in equations
    spaced_patterns = [
        (r"F\s*l\s*o\s*a\s*t\s*i\s*n\s*g", "Floating"),
        (r"p\s*o\s*i\s*n\s*t", "point"),
        (r"o\s*p\s*e\s*r\s*a\s*t\s*i\s*o\s*n\s*s", "operations"),
        (r"M\s*e\s*m\s*o\s*r\s*y", "Memory"),
        (r"m\s*e\s*m\s*o\s*r\s*y", "memory"),
        (r"b\s*y\s*t\s*e\s*s", "bytes"),
        (r"B\s*a\s*n\s*d\s*w\s*i\s*d\s*t\s*h", "Bandwidth"),
        (r"b\s*a\s*n\s*d\s*w\s*i\s*d\s*t\s*h", "bandwidth"),
        (r"T\s*r\s*a\s*n\s*s\s*f\s*e\s*r", "Transfer"),
        (r"t\s*r\s*a\s*n\s*s\s*f\s*e\s*r\s*r\s*e\s*d", "transferred"),
        (r"P\s*e\s*a\s*k", "Peak"),
        (r"p\s*e\s*a\s*k", "peak"),
        (r"P\s*e\s*r\s*f\s*o\s*r\s*m\s*a\s*n\s*c\s*e", "Performance"),
        (r"S\s*i\s*z\s*e", "Size"),
        (r"I\s*O\s*P\s*S", "IOPS"),
        (r"I\s*O\s*P\s*s", "IOPS"),
    ]

    for pattern, replacement in spaced_patterns:
        text = re.sub(pattern, replacement, text)

    return text


def _fix_common_ocr_artifacts(content: str) -> str:
    """
    Fix common OCR artifacts in equations.
    """
    def fix_equation(match: re.Match[str]) -> str:
        eq = match.group(1)

        # Fix common OCR misreads using simple string replace (not regex)
        # to avoid issues with LaTeX backslashes
        simple_replacements = [
            ("Floting", "Floating"),
            ("rerferred", "transferred"),
            ("Mermoy", "Memory"),
        ]

        for old, new in simple_replacements:
            eq = eq.replace(old, new)

        # Fix equation number at end: "  (2)  " → " \quad (2)"
        eq = re.sub(r"\s*\(\s*(\d+)\s*\)\s*$", r" \\quad (\1)", eq)

        return f"$${eq}$$"

    content = re.sub(r"\$\$(.*?)\$\$", fix_equation, content, flags=re.DOTALL)

    return content


def _normalize_equation_delimiters(content: str) -> str:
    """
    Normalize equation delimiters for consistency.

    Ensures proper spacing around display equations.
    """
    # Ensure blank line before display equations
    content = re.sub(r"([^\n])\n(\$\$)", r"\1\n\n\2", content)

    # Ensure blank line after display equations
    content = re.sub(r"(\$\$)\n([^\n])", r"\1\n\n\2", content)

    return content
