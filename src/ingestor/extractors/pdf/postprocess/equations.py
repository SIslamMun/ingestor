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
    - Removing spurious spaces from Docling extraction
    - Fixing \\\\ outside array environments

    Args:
        content: Markdown content with equations

    Returns:
        Content with cleaned equations
    """
    content = _fix_formula_placeholders(content)
    content = _fix_docling_spacing(content)
    content = _clean_latex_spacing(content)
    content = _fix_common_ocr_artifacts(content)
    content = _fix_bare_newlines_in_display_math(content)
    content = _normalize_equation_delimiters(content)
    return content


def _fix_docling_spacing(content: str) -> str:
    """
    Fix spacing issues introduced by Docling's LaTeX extraction.

    Docling often extracts equations with spaces between characters,
    e.g., "M u l t i H e a d" instead of "MultiHead"
    """
    def fix_equation(match: re.Match[str]) -> str:
        eq = match.group(1)

        # FIRST: Fix spacing in \text { X } -> \text{X}
        # This must happen before other replacements
        def fix_text_spacing(m: re.Match[str]) -> str:
            inner = m.group(1).strip()
            # Also fix "mode" -> "model" inside \text{}
            if inner == "mode":
                inner = "model"
            return f"\\text{{{inner}}}"
        eq = re.sub(r"\\text\s*\{\s*([^}]*?)\s*\}", fix_text_spacing, eq)

        # Fix spaced-out words that are NOT already inside \text{}
        # These patterns are for OCR artifacts like "M u l t i H e a d"
        spaced_ocr_words = [
            # Match various spacings in MultiHead
            (r"M\s*u\s*l?\s*t\s*i\s*\{?\s*H\s*e\s*a\s*d\s*\}?", "\\\\text{MultiHead}"),
            (r"(?<!\\text\{)F\s+F\s+N(?!\})", "\\\\text{FFN}"),
            (r"h\s+e\s+a\s+d\s+_", "head_"),  # "h e a d _" -> "head_"
        ]

        for pattern, replacement in spaced_ocr_words:
            eq = re.sub(pattern, replacement, eq)

        # Fix spaced variable names (not function names that should be in \text{})
        spaced_vars = [
            (r"h\s+e\s+a\s+d\b", "head"),
            (r"p\s+o\s+s\b", "pos"),
            (r"m\s+o\s+d\s+e\s+l\b", "model"),
            (r"s\s+t\s+e\s+p\b", "step"),
            (r"n\s+u\s+m\b", "num"),
            (r"w\s+a\s+r\s+m\s+u\s+p\b", "warmup"),
            (r"s\s+t\s+e\s+p\s+s\b", "steps"),
            (r"l\s+r\s+a\s+t\s+e\b", "lrate"),
            (r"d\s+r\s+o\s+p\s+o\s+u\s+t\b", "dropout"),
            # Fix partial splits like "step s" -> "steps"
            (r"\bstep\s+s\b", "steps"),
            # Fix common OCR spaced words
            (r"F\s+l\s+o\s+a\s+t\s+i\s+n\s+g\b", "Floating"),
            (r"B\s+a\s+n\s+d\s+w\s+i\s+d\s+t\s+h\b", "Bandwidth"),
            (r"I\s+O\s+P\s+S\b", "IOPS"),
            (r"M\s+e\s+m\s+o\s+r\s+y\b", "Memory"),
            (r"P\s+e\s+r\s+f\s+o\s+r\s+m\s+a\s+n\s+c\s+e\b", "Performance"),
            (r"T\s+h\s+r\s+o\s+u\s+g\s+h\s+p\s+u\s+t\b", "Throughput"),
            (r"L\s+a\s+t\s+e\s+n\s+c\s+y\b", "Latency"),
        ]

        for pattern, replacement in spaced_vars:
            eq = re.sub(pattern, replacement, eq)

        # Generic fix: sequences of single uppercase letters with spaces -> joined
        # e.g., "I O P S" -> "IOPS", "G P U" -> "GPU"
        def fix_uppercase_acronym(m: re.Match[str]) -> str:
            return m.group(0).replace(" ", "")
        eq = re.sub(r"\b([A-Z](?:\s+[A-Z])+)\b", fix_uppercase_acronym, eq)

        # Fix spaced numbers like "1 0 0 0 0" -> "10000"
        def fix_spaced_number(m: re.Match[str]) -> str:
            return m.group(0).replace(" ", "")

        eq = re.sub(r"\b(\d(?:\s+\d)+)\b", fix_spaced_number, eq)

        # Fix decimal numbers with spaces like "0 . 5" -> "0.5"
        eq = re.sub(r"(\d)\s*\.\s*(\d)", r"\1.\2", eq)

        # Fix spaced subscripts/superscripts like "d _ { k }" -> "d_{k}"
        # This must happen BEFORE the {-} fix
        eq = re.sub(r"\s*_\s*\{\s*", r"_{", eq)
        eq = re.sub(r"\s*\^\s*\{\s*", r"^{", eq)
        eq = re.sub(r"\s*\}", r"}", eq)

        # Fix spaces inside braces: ^{ - 0.5} -> ^{-0.5}
        def clean_brace_content(m: re.Match[str]) -> str:
            prefix = m.group(1)  # ^ or _
            content = m.group(2).strip()
            # Remove spaces around operators inside braces
            content = re.sub(r"\s*-\s*", "-", content)
            content = re.sub(r"\s*\+\s*", "+", content)
            return f"{prefix}{{{content}}}"
        eq = re.sub(r"(\^|_)\{([^}]+)\}", clean_brace_content, eq)

        # NOW fix subscript patterns like "step_{-}num" or "step_{-} num" -> "step_num"
        # (hyphen inside subscript braces indicates OCR artifact, e.g. step_num became step_{-}num)
        eq = re.sub(r"_\{\s*-\s*\}\s*(\w+)", r"_\1", eq)

        # Fix spacing around operators but preserve alignment
        eq = re.sub(r"\s*\+\s*", " + ", eq)
        eq = re.sub(r"(?<!\^)\s*-\s*(?!\d)", " - ", eq)  # Don't touch negative numbers or exponents
        eq = re.sub(r"\s*=\s*", " = ", eq)
        eq = re.sub(r"\s*\\cdot\s*", r" \\cdot ", eq)

        # Clean up multiple spaces
        eq = re.sub(r"  +", " ", eq)

        # Fix spaces inside parentheses: "( Q , K , V )" -> "(Q, K, V)"
        eq = re.sub(r"\(\s+", "(", eq)
        eq = re.sub(r"\s+\)", ")", eq)

        # Fix spaces around commas: ", " is good, " , " has extra space
        eq = re.sub(r"\s+,", ",", eq)

        # Fix double \text{} wrapping: \text{\text{X}} -> \text{X}
        # Handle spaces: \text { \text { X } } or \text{\text{X}}
        eq = re.sub(r"\\text\s*\{\s*\\text\s*\{([^}]*)\}\s*\}", "\\\\text{\\1}", eq)

        # Fix double backslashes: \\max -> \max (common Docling issue)
        eq = re.sub(r"\\\\(max|min|sin|cos|tan|log|exp|sqrt|frac|text|cdot)", r"\\\1", eq)

        return f"$${eq.strip()}$$"

    content = re.sub(r"\$\$(.*?)\$\$", fix_equation, content, flags=re.DOTALL)

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
    - Extra spaces around operators
    - Spaces in LaTeX commands
    """
    def clean_equation(match: re.Match[str]) -> str:
        eq = match.group(1)

        # Fix space after backslash before command: "\ frac" -> "\frac"
        # Use a callback to preserve the backslash correctly
        def fix_backslash_space(m: re.Match[str]) -> str:
            return "\\" + m.group(1)
        eq = re.sub(r"\\\s+([a-zA-Z])", fix_backslash_space, eq)

        # Fix spacing in common LaTeX commands (don't double backslashes!)
        eq = re.sub(r"\\text\s+\{", r"\\text{", eq)
        eq = re.sub(r"\\frac\s+\{", r"\\frac{", eq)
        eq = re.sub(r"\\sqrt\s+\{", r"\\sqrt{", eq)
        eq = re.sub(r"\\min\s+\(", r"\\min(", eq)
        eq = re.sub(r"\\max\s+\(", r"\\max(", eq)
        eq = re.sub(r"\\sin\s+\(", r"\\sin(", eq)
        eq = re.sub(r"\\cos\s+\(", r"\\cos(", eq)
        eq = re.sub(r"\\log\s+\(", r"\\log(", eq)
        eq = re.sub(r"\\exp\s+\(", r"\\exp(", eq)

        # Fix spaced-out trig/math function names: "s i n" -> "\sin"
        eq = re.sub(r"\bs\s+i\s+n\b", r"\\sin", eq)
        eq = re.sub(r"\bc\s+o\s+s\b", r"\\cos", eq)
        eq = re.sub(r"\bt\s+a\s+n\b", r"\\tan", eq)
        eq = re.sub(r"\bl\s+o\s+g\b", r"\\log", eq)
        eq = re.sub(r"\be\s+x\s+p\b", r"\\exp", eq)
        eq = re.sub(r"\bm\s+i\s+n\b", r"\\min", eq)
        eq = re.sub(r"\bm\s+a\s+x\b", r"\\max", eq)

        # Clean up multiple spaces
        eq = re.sub(r"\s{2,}", " ", eq)

        return f"$${eq}$$"

    # Process display math ($$...$$)
    content = re.sub(r"\$\$(.*?)\$\$", clean_equation, content, flags=re.DOTALL)

    return content


def _fix_common_ocr_artifacts(content: str) -> str:
    """
    Fix common OCR artifacts in equations.
    """
    def fix_equation(match: re.Match[str]) -> str:
        eq = match.group(1)

        # Fix common OCR misreads using simple string replace (not regex)
        simple_replacements = [
            ("Floting", "Floating"),
            ("rerferred", "transferred"),
            ("Mermoy", "Memory"),
        ]

        for old, new in simple_replacements:
            eq = eq.replace(old, new)

        # Fix spaced OCR artifacts that appear at end of equations
        # e.g., "\e r r o w" -> "" (remove), "\a r r o w" -> "\arrow"
        ocr_noise_patterns = [
            (r"\\?\s*e\s+r\s+r\s+o\s+w\s*", ""),  # "\e r r o w" -> remove
            (r"\\?\s*a\s+r\s+r\s+o\s+w\s*", r"\\rightarrow "),  # "a r r o w" -> \rightarrow
            (r"\\?\s*n\s+a\s+r\s+r\s+o\s+w\s*", r"\\rightarrow "),  # "n a r r o w" -> \rightarrow
        ]

        for pattern, replacement in ocr_noise_patterns:
            eq = re.sub(pattern, replacement, eq, flags=re.IGNORECASE)

        # === GAN-specific OCR fixes ===
        # Fix corrupted distribution names: p_{\} p a -> p_{\text{data}}
        eq = re.sub(r"p_\{\\?\}\s*p\s*a\b", r"p_{\\text{data}}", eq)
        eq = re.sub(r"P_\{\\?\}\s*p\s*a\b", r"p_{\\text{data}}", eq)
        # Fix p_{D} -> p_{\text{data}} in GAN context
        eq = re.sub(r"p_\{D\}\s*\(x\)", r"p_{\\text{data}}(x)", eq)
        # Fix p_{d a t a} with spaces
        eq = re.sub(r"p_\{d\s*a\s*t\s*a\}", r"p_{\\text{data}}", eq)
        eq = re.sub(r"p_\{d\s*a\s*t\s*i\}", r"p_{\\text{data}}", eq)

        # Fix \min_{G \D} \max_{D} -> \min_G \max_D (GAN minimax - remove duplicate \max_{D})
        eq = re.sub(r"\\min_\{G\s*\\D\}\s*\\max_\{D\}", r"\\min_G \\max_D", eq)
        eq = re.sub(r"p_\{d\s*o\s*t\s*a\}", r"p_{\\text{data}}", eq)

        # Fix \min_{G \D} -> \min_G \max_D (GAN minimax)
        eq = re.sub(r"\\min_\{G\s*\\D\}", r"\\min_G \\max_D", eq)

        # Fix double subscripts like p_{_{G}} -> p_G
        eq = re.sub(r"p_\{_\{([A-Za-z])\}\}", r"p_{\1}", eq)
        eq = re.sub(r"p_\{_\{([a-z])\}\}", r"p_{\1}", eq)

        # Fix \theta_s -> \theta_g (generator parameter in GAN)
        # Only in generator gradient context
        eq = re.sub(r"\\theta_\{?s\}?(?=.*\\log.*D.*G)", r"\\theta_g", eq)

        # Fix mismatched parentheses: \left) -> \right)
        eq = re.sub(r"\\left\)", r"\\right)", eq)

        # Fix spacing around \mathcal and similar commands
        eq = re.sub(r"\\mathcal\s*\{\s*(\w)\s*\}", r"\\mathcal{\1}", eq)
        eq = re.sub(r"\\mathbb\s*\{\s*(\w)\s*\}", r"\\mathbb{\1}", eq)
        eq = re.sub(r"\\mathbf\s*\{\s*(\w+)\s*\}", r"\\mathbf{\1}", eq)

        # Fix spacing inside set notation: \{ W _ { i } \} -> \{W_i\}
        eq = re.sub(r"\\\{\s*", r"\\{", eq)
        eq = re.sub(r"\s*\\\}", r"\\}", eq)

        # Fix equation number at end: "  (2)  " → " \quad (2)"
        eq = re.sub(r"\s*\(\s*(\d+)\s*\)\s*$", r" \\quad (\1)", eq)

        # Clean up multiple \quad
        eq = re.sub(r"(\\quad\s*)+", r"\\quad ", eq)

        # Clean up trailing whitespace before $$
        eq = eq.rstrip()

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


def _fix_bare_newlines_in_display_math(content: str) -> str:
    """
    Fix \\\\ used inside $$...$$ without an array/aligned/cases environment.

    LaTeX requires \\\\ to be inside a multi-line environment like:
    - \\begin{array}...\\end{array}
    - \\begin{aligned}...\\end{aligned}
    - \\begin{cases}...\\end{cases}
    - \\begin{matrix}...\\end{matrix}

    If \\\\ appears outside these environments, wrap in aligned.
    """
    # LaTeX commands that start with \\ but are NOT newlines
    latex_commands = [
        "begin", "end", "text", "frac", "sqrt", "sum", "prod", "int",
        "lim", "sin", "cos", "tan", "log", "exp", "min", "max", "sup", "inf",
        "left", "right", "big", "Big", "bigg", "Bigg", "cdot", "cdots", "ldots",
        "alpha", "beta", "gamma", "delta", "epsilon", "varepsilon", "zeta", "eta",
        "theta", "vartheta", "iota", "kappa", "lambda", "mu", "nu", "xi", "pi",
        "rho", "sigma", "tau", "upsilon", "phi", "varphi", "chi", "psi", "omega",
        "Gamma", "Delta", "Theta", "Lambda", "Xi", "Pi", "Sigma", "Upsilon", "Phi",
        "Psi", "Omega", "partial", "nabla", "infty", "forall", "exists", "neg",
        "in", "notin", "subset", "supset", "cap", "cup", "wedge", "vee", "times",
        "div", "pm", "mp", "leq", "geq", "neq", "approx", "equiv", "sim", "simeq",
        "propto", "perp", "parallel", "angle", "triangle", "square", "circ",
        "quad", "qquad", "hspace", "vspace", "mathbb", "mathbf", "mathcal", "mathrm",
        "mathit", "mathsf", "mathtt", "boldsymbol", "overline", "underline", "hat",
        "bar", "vec", "dot", "ddot", "tilde", "widetilde", "widehat", "overbrace",
        "underbrace", "stackrel", "overset", "underset", "displaystyle", "scriptstyle",
        "not", "to", "rightarrow", "leftarrow", "Rightarrow", "Leftarrow",
        "longrightarrow", "longleftarrow", "mapsto", "iff", "implies",
    ]

    def fix_equation(match: re.Match[str]) -> str:
        eq = match.group(1).strip()

        # Find all \\ that are newlines (not LaTeX commands)
        # Pattern: \\ followed by space, digit, {, or end, OR followed by letter not in commands list
        newline_positions: list[int] = []

        i = 0
        while i < len(eq) - 1:
            if eq[i:i+2] == "\\\\":
                # Check what follows
                rest = eq[i+2:]
                if not rest:
                    # \\ at end - it's a newline
                    newline_positions.append(i)
                elif rest[0] in " \t\n{[0-9":
                    # \\ followed by space, brace, or digit - it's a newline
                    newline_positions.append(i)
                elif rest[0].isalpha():
                    # Check if it's a known LaTeX command
                    # Extract the word
                    word_match = re.match(r"([a-zA-Z]+)", rest)
                    if word_match:
                        word = word_match.group(1)
                        if word not in latex_commands:
                            # Not a known command, so \\ is likely a newline
                            newline_positions.append(i)
                i += 1
            else:
                i += 1

        if not newline_positions:
            return f"$${eq}$$"

        # Find all environment ranges
        multiline_envs = [
            "array", "aligned", "align", "cases", "matrix", "pmatrix",
            "bmatrix", "vmatrix", "Vmatrix", "gather", "gathered",
            "split", "multline", "eqnarray"
        ]

        env_ranges: list[tuple[int, int]] = []
        for env in multiline_envs:
            begin_pattern = rf"\\begin\s*\{{\s*{env}\s*\}}"
            end_pattern = rf"\\end\s*\{{\s*{env}\s*\}}"

            for begin_match in re.finditer(begin_pattern, eq):
                begin_pos = begin_match.start()
                end_match = re.search(end_pattern, eq[begin_pos:])
                if end_match:
                    end_pos = begin_pos + end_match.end()
                    env_ranges.append((begin_pos, end_pos))

        # Check if any newline is outside all environment ranges
        has_bare_newline = False
        for pos in newline_positions:
            inside_env = any(start <= pos < end for start, end in env_ranges)
            if not inside_env:
                has_bare_newline = True
                break

        if not has_bare_newline:
            return f"$${eq}$$"

        # There's a bare \\ - wrap the entire equation in aligned environment
        wrapped = f"\\begin{{aligned}}\n{eq}\n\\end{{aligned}}"

        return f"$${wrapped}$$"

    content = re.sub(r"\$\$(.*?)\$\$", fix_equation, content, flags=re.DOTALL)

    return content
