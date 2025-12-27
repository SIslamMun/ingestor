"""Section processing: fix headers and subsection detection.

Ported from paper-to-md project.

Handles hierarchical section numbering in academic papers:
- Section: ## 1. INTRODUCTION or ## I. INTRODUCTION
- Subsection: ### 1.1 Background
- Subsubsection: #### 1.1.1 Details
- Paragraph: ##### 1.1.1.1 Fine details
"""

from __future__ import annotations

import re

# Maximum title length for a section header (longer text is likely a paragraph)
MAX_TITLE_LENGTH = 120


def process_sections(content: str) -> str:
    """
    Process section headers in markdown content.

    Handles:
    - Abstract artifacts: "Abstract -Modern HPC..." → "## Abstract\\n\\nModern HPC..."
    - Index Terms: "Index Terms -keywords" → "## Index Terms\\n\\nkeywords"
    - Numbered sections: "3.1.1 Design overview." → "#### 3.1.1 Design overview"
    - Bullet subsections: "- 1) Title:" → "### 1) Title"

    Args:
        content: Markdown content

    Returns:
        Content with fixed section headers
    """
    content = _fix_abstract_header(content)
    content = _fix_index_terms_header(content)
    content = _fix_hierarchical_sections(content)
    content = _fix_numbered_bullet_subsections(content)
    return content


def _fix_abstract_header(content: str) -> str:
    """
    Fix Abstract header artifacts.

    "Abstract -Modern HPC..." → "## Abstract\\n\\nModern HPC..."
    "Abstract-Modern HPC..." → "## Abstract\\n\\nModern HPC..."
    """
    pattern = r"^(#+\s*)?Abstract\s*[-–—]\s*"
    replacement = "## Abstract\n\n"
    return re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE | re.IGNORECASE)


def _fix_index_terms_header(content: str) -> str:
    """
    Fix Index Terms header artifacts.

    "Index Terms -keywords" → "## Index Terms\\n\\nkeywords"
    """
    pattern = r"^(#+\s*)?Index Terms\s*[-–—]\s*"
    replacement = "## Index Terms\n\n"
    return re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE | re.IGNORECASE)


def _determine_header_level(numbering: str) -> int:
    """
    Determine the markdown header level based on section numbering depth.

    Args:
        numbering: The section number (e.g., "3", "3.1", "3.1.1", "3.1.1.1")

    Returns:
        Header level (2 for ##, 3 for ###, etc.)

    Examples:
        "3" or "III" → 2 (## Section)
        "3.1" → 3 (### Subsection)
        "3.1.1" → 4 (#### Subsubsection)
        "3.1.1.1" → 5 (##### Paragraph)
    """
    parts = numbering.split(".")
    depth = len(parts)
    return min(depth + 1, 6)


def _is_section_title(title: str, following_lines: list[str]) -> bool:
    """
    Determine if text is likely a section title vs regular paragraph.

    Args:
        title: The potential section title
        following_lines: Lines that follow this one

    Returns:
        True if this looks like a section title
    """
    # Too long for a title
    if len(title) > MAX_TITLE_LENGTH:
        return False

    # Empty title is not valid
    if not title.strip():
        return False

    # Titles typically don't end with certain punctuation
    if title.rstrip().endswith((",", ";", ":")):
        return False

    # If followed by blank line or starts with capital, likely a title
    if following_lines:
        next_line = following_lines[0].strip()
        if not next_line:  # Blank line after = likely title
            return True

    # Short text (< 60 chars) ending with period is likely a title
    if len(title) < 60 and title.rstrip().endswith("."):
        return True

    # Capitalized or uppercase text is likely a title
    words = title.split()
    return bool(words and (words[0][0].isupper() or title.isupper()))


def _fix_hierarchical_sections(content: str) -> str:
    """
    Fix hierarchical numbered sections (1., 1.1, 1.1.1, etc.).

    Converts lines like:
    - "1. INTRODUCTION" → "## 1. INTRODUCTION"
    - "3.1 Background" → "### 3.1 Background"
    - "3.1.1 Design overview" → "#### 3.1.1 Design overview"
    """
    lines = content.split("\n")
    result = []

    # Pattern for numbered sections: "N." or "N.N" or "N.N.N" at start of line
    # Followed by space and title text
    section_pattern = re.compile(
        r"^(\d+(?:\.\d+)*\.?)\s+([A-Z].*?)$",  # Starts with capital after number
        re.IGNORECASE,
    )

    # Roman numeral pattern for top-level sections
    roman_pattern = re.compile(
        r"^(I{1,3}|IV|VI{0,3}|IX|X{1,3})\.?\s+([A-Z].*?)$",
        re.IGNORECASE,
    )

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip lines that are already headers
        if stripped.startswith("#"):
            result.append(line)
            continue

        # Check for numbered section
        match = section_pattern.match(stripped)
        if match:
            numbering = match.group(1).rstrip(".")
            title = match.group(2)
            following = lines[i + 1 :] if i + 1 < len(lines) else []

            if _is_section_title(title, following):
                level = _determine_header_level(numbering)
                hashes = "#" * level
                result.append(f"{hashes} {numbering}. {title}")
                continue

        # Check for Roman numeral section
        roman_match = roman_pattern.match(stripped)
        if roman_match:
            numeral = roman_match.group(1).upper()
            title = roman_match.group(2)
            following = lines[i + 1 :] if i + 1 < len(lines) else []

            if _is_section_title(title, following):
                result.append(f"## {numeral}. {title}")
                continue

        result.append(line)

    return "\n".join(result)


def _fix_numbered_bullet_subsections(content: str) -> str:
    """
    Convert numbered bullet items that are actually subsections.

    "- 1) Title:" or "• 1) Title" → "### 1) Title"
    """
    lines = content.split("\n")
    result = []

    # Pattern: bullet (-, *, •) followed by number and parenthesis
    bullet_section_pattern = re.compile(
        r"^[-*•]\s*(\d+)\)\s+(.+?)[:.]?\s*$"
    )

    for line in lines:
        stripped = line.strip()

        match = bullet_section_pattern.match(stripped)
        if match:
            num = match.group(1)
            title = match.group(2)
            # Only convert if title looks like a heading (short, capitalized)
            if len(title) < 80 and title[0].isupper():
                result.append(f"### {num}) {title}")
                continue

        result.append(line)

    return "\n".join(result)
