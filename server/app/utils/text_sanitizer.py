"""Sanitize and normalize free-text inputs for LLM consumption.

Functions:
 - sanitize_text(text): returns normalized text with control chars removed and whitespace normalized.
"""
from __future__ import annotations
import re
from typing import Optional


def sanitize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove control characters except newline and tab
    # Keep characters with ord >= 32, newline(10), tab(9)
    cleaned_chars = []
    for ch in text:
        o = ord(ch)
        if ch == "\n" or ch == "\t" or o >= 32:
            cleaned_chars.append(ch)
        # else drop control char
    text = "".join(cleaned_chars)

    # Collapse repeated spaces/tabs into single space
    text = re.sub(r"[ \t]+", " ", text)

    # Collapse multiple blank lines into at most two
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Trim leading/trailing whitespace on each line and overall
    lines = [ln.rstrip() for ln in text.split("\n")]
    text = "\n".join(lines).strip()

    return text
