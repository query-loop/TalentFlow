from __future__ import annotations

from typing import List, Dict, Tuple
import re
from bs4 import BeautifulSoup, NavigableString, Tag


HEADING_ALIASES: Dict[str, str] = {
    # left: regex prefix, right: normalized section name
    r"^(about( us)?|overview|summary|the role|position)$": "Overview",
    r"^(what you will do|what you'll do|responsibilities|duties|what you will)$": "Responsibilities",
    r"^(requirements|qualifications|basic qualifications|preferred qualifications|min(imum)? requirements|preferred requirements|what we require)$": "Requirements",
    r"^(benefits|compensation|salary|pay|benefits & compensation)$": "Benefits",
    r"^(who you are)$": "Who You Are",
    r"^(who we are|about the team|culture)$": "About The Team",
    r"^(diversity|equal opportunity|eeo)$": "EEO",
    # Palantir-style/company-centric headings
    r"^(a world[- ]changing company|life at .+)$": "About The Company",
    r"^(what we value|our values|values)$": "Values",
}

ORDER = [
    "Overview",
    "Responsibilities",
    "Requirements",
    "Benefits",
    "Who You Are",
    "About The Team",
    "About The Company",
    "Values",
    "EEO",
]


def _normalize_spaces(s: str) -> str:
    s = s.replace('\r', '\n')
    s = re.sub(r"\u00a0", " ", s)  # nbsp
    s = re.sub(r"[\t ]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _alias_heading(text: str) -> str | None:
    t = text.strip().lower().rstrip(' :')
    for pattern, norm in HEADING_ALIASES.items():
        if re.match(pattern, t, flags=re.I):
            return norm
    return None


def html_to_text_preserve_lists(html: str) -> str:
    """Convert HTML to plain text while preserving list bullets and paragraph/heading separation."""
    soup = BeautifulSoup(html, 'html.parser')

    lines: List[str] = []

    def emit(s: str):
        s = s.strip()
        if not s:
            return
        # split hard newlines into separate lines
        for part in _normalize_spaces(s).split('\n'):
            part = part.strip()
            if part:
                lines.append(part)

    def walk(node: Tag | NavigableString):
        if isinstance(node, NavigableString):
            text = str(node)
            if text and text.strip():
                emit(text)
            return
        if not isinstance(node, Tag):
            return

        name = node.name.lower()
        if name in {"script", "style", "noscript"}:
            return

        if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            heading_text = node.get_text(" ", strip=True)
            if heading_text:
                lines.append("")
                lines.append(heading_text.strip())
                lines.append("")
            return

        if name in {"br"}:
            lines.append("")
            return

        if name in {"ul", "ol"}:
            is_ol = name == "ol"
            i = 1
            for li in node.find_all("li", recursive=False):
                li_text = li.get_text(" ", strip=True)
                if not li_text:
                    continue
                bullet = f"{i}. " if is_ol else "- "
                lines.append(bullet + li_text)
                i += 1
            lines.append("")
            return

        if name == "p":
            p_text = node.get_text(" ", strip=True)
            if p_text:
                lines.append(p_text)
                lines.append("")
            return

        # default: walk children
        for child in node.children:
            walk(child)

    body = soup.body or soup
    walk(body)

    # collapse extra blanks
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_into_blocks(text: str) -> List[str]:
    # blocks separated by blank lines
    text = _normalize_spaces(text)
    blocks = re.split(r"\n\s*\n+", text)
    return [b.strip() for b in blocks if b.strip()]


def _is_list_block(lines: List[str]) -> bool:
    return len(lines) > 1 and all(re.match(r"^\s*(?:[-*•]|\d+[\.)])\s+", l) for l in lines)


def normalize_jd_text(html_or_text: str) -> str:
    """Normalize JD into clean, consistently structured plain text.

    Steps:
      - Strip HTML and preserve bullets/numbering and headings as plain lines
      - Identify known sections by heading aliases and group content under normalized headings
      - Reorder sections into a conventional order while preserving unmatched content order
      - Normalize bullets to "- " for unordered lists
    """
    if not html_or_text:
        return ""

    has_tags = bool(re.search(r"<[^>]+>", html_or_text))
    text = html_to_text_preserve_lists(html_or_text) if has_tags else _normalize_spaces(html_or_text)

    blocks = _split_into_blocks(text)
    sections: Dict[str, List[str]] = {}
    other_blocks: List[Tuple[str, List[str]]] = []  # (heading or '', lines)

    current_key: str | None = None
    current_lines: List[str] = []

    def flush():
        nonlocal current_key, current_lines
        if not current_lines:
            return
        if current_key:
            sections.setdefault(current_key, []).extend(current_lines)
        else:
            other_blocks.append(("", current_lines[:]))
        current_lines = []

    for b in blocks:
        lines = [l for l in b.split('\n') if l.strip()]
        if not lines:
            continue
        # If first line looks like a heading or matches alias, start a new section
        first = lines[0].strip().rstrip(':')
        alias = _alias_heading(first)
        if alias or (len(lines) == 1 and _looks_like_heading(first)):
            flush()
            current_key = alias or first
            current_lines = []
            continue

        # If entire block is a list, keep list lines
        if _is_list_block(lines):
            current_lines.extend(_normalize_list_lines(lines))
        else:
            current_lines.append(" ".join(lines))

    flush()

    # Build output in ORDER, then remaining aliased sections, then other blocks
    out_lines: List[str] = []

    def emit_section(name: str, lines: List[str]):
        if not lines:
            return
        out_lines.append(f"{name}:")
        for ln in lines:
            out_lines.append(ln)
        out_lines.append("")

    # Emit preferred ordered sections
    for key in ORDER:
        if key in sections:
            emit_section(key, sections.pop(key))

    # Emit any remaining recognized sections
    for key, lines in list(sections.items()):
        emit_section(key, lines)
        sections.pop(key, None)

    # Emit other blocks (intro or unmatched)
    for _, lines in other_blocks:
        for ln in lines:
            out_lines.append(ln)
        out_lines.append("")

    text_out = "\n".join(out_lines)
    text_out = re.sub(r"\n{3,}", "\n\n", text_out).strip()
    return text_out


def _looks_like_heading(s: str) -> bool:
    s = s.strip()
    if not s or len(s) > 80:
        return False
    if re.search(r"[.?!]$", s):
        return False
    words = s.split()
    if len(words) > 10:
        return False
    return s[0].isupper() or s.isupper()


def _normalize_list_lines(lines: List[str]) -> List[str]:
    out: List[str] = []
    for l in lines:
        m = re.match(r"^\s*(?:[-*•]|(\d+)[\.)])\s+(.*)$", l)
        if m:
            num = m.group(1)
            content = m.group(2) if m.group(2) is not None else ""
            if num:
                out.append(f"{num}. {content.strip()}")
            else:
                out.append(f"- {content.strip()}")
        else:
            out.append(l.strip())
    return out
