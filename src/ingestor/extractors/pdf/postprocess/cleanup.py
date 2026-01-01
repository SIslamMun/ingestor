"""General text cleanup: ligatures, whitespace, etc.

Ported from paper-to-md project.
"""

from __future__ import annotations

import re


def cleanup_text(content: str) -> str:
    """
    Apply general text cleanup to markdown content.

    Handles:
    - Ligature replacement (ﬁ→fi, ﬂ→fl, ﬀ→ff, etc.)
    - Excessive blank lines (max 2 consecutive)
    - Trailing whitespace
    - Glyph artifacts from PDF extraction

    Args:
        content: Markdown content

    Returns:
        Cleaned content
    """
    content = _fix_ligatures(content)
    content = _fix_glyph_artifacts(content)
    content = _fix_excessive_blank_lines(content)
    content = _fix_trailing_whitespace(content)
    return content


def _fix_ligatures(content: str) -> str:
    """
    Replace common ligature characters with their ASCII equivalents.
    """
    ligatures = {
        "ﬁ": "fi",
        "ﬂ": "fl",
        "ﬀ": "ff",
        "ﬃ": "ffi",
        "ﬄ": "ffl",
        "ﬅ": "ft",
        "ﬆ": "st",
        # Common dash variants
        "–": "-",  # en-dash to hyphen (keep em-dash for intentional use)
    }

    for ligature, replacement in ligatures.items():
        content = content.replace(ligature, replacement)

    return content


def _fix_excessive_blank_lines(content: str) -> str:
    """
    Reduce multiple consecutive blank lines to maximum of 2.
    """
    return re.sub(r"\n{3,}", "\n\n", content)


def _fix_glyph_artifacts(content: str) -> str:
    """
    Fix glyph[...] artifacts from PDF extraction.

    Common patterns:
    - glyph[epsilon1] -> ε
    - glyph[alpha] -> α
    """
    # Map of glyph names to Unicode characters
    glyph_map = {
        "epsilon1": "ε",
        "epsilon": "ε",
        "alpha": "α",
        "beta": "β",
        "gamma": "γ",
        "delta": "δ",
        "theta": "θ",
        "lambda": "λ",
        "mu": "μ",
        "sigma": "σ",
        "phi": "φ",
        "psi": "ψ",
        "omega": "ω",
        "pi": "π",
        "rho": "ρ",
        "tau": "τ",
        "eta": "η",
        "zeta": "ζ",
        "xi": "ξ",
        "nu": "ν",
        "kappa": "κ",
        "iota": "ι",
        "chi": "χ",
        "upsilon": "υ",
    }

    def replace_glyph(match: re.Match[str]) -> str:
        glyph_name = match.group(1).lower()
        return glyph_map.get(glyph_name, match.group(0))

    # Match glyph[name] pattern
    content = re.sub(r"glyph\[(\w+)\]", replace_glyph, content, flags=re.IGNORECASE)

    return content


def _fix_trailing_whitespace(content: str) -> str:
    """
    Remove trailing whitespace from each line.
    """
    lines = content.split("\n")
    return "\n".join(line.rstrip() for line in lines)


def fix_hyphenated_words(content: str) -> str:
    """
    Fix words broken by hyphenation at line endings.

    Note: This is aggressive and may have false positives.
    Use with caution or as part of agent review.

    Example: "docu-\\nment" → "document"
    """
    pattern = r"(\w+)-\n(\s*)([a-z]\w*)"

    def fix_hyphen(match: re.Match[str]) -> str:
        word1 = match.group(1)
        word2 = match.group(3)
        return f"{word1}{word2}"

    return re.sub(pattern, fix_hyphen, content)


def normalize_unicode(content: str) -> str:
    """
    Normalize Unicode characters to their ASCII equivalents where appropriate.

    Handles common academic paper artifacts:
    - Smart quotes → regular quotes
    - Various dash types → standard hyphen/dash
    - Special spaces → regular space
    """
    replacements = {
        # Quotes
        """: '"',
        """: '"',
        "'": "'",
        "„": '"',
        "‟": '"',
        # Dashes
        "—": "--",  # em-dash
        "―": "--",  # horizontal bar
        "‒": "-",   # figure dash
        "−": "-",   # minus sign
        # Spaces
        "\u00a0": " ",  # non-breaking space
        "\u2002": " ",  # en space
        "\u2003": " ",  # em space
        "\u2009": " ",  # thin space
        "\u200a": " ",  # hair space
        # Other
        "…": "...",
        "•": "-",
        "·": "-",
    }

    for char, replacement in replacements.items():
        content = content.replace(char, replacement)

    return content
