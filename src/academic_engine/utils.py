from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def extract_citations(text: str) -> list[str]:
    patterns = [
        r"\([A-Z][A-Za-z\-]+(?:\s+(?:&|and)\s+[A-Z][A-Za-z\-]+)?(?:\s+et al\.)?,\s*\d{4}[a-z]?(?:,\s*p\.?\s*\d+)?\)",
        r"\b[A-Z][A-Za-z\-]+(?:\s+(?:&|and)\s+[A-Z][A-Za-z\-]+)?(?:\s+et al\.)?\s+\(\d{4}[a-z]?\)",
        r"\[[0-9,\s\-]+\]",
    ]
    spans: list[str] = []
    for pattern in patterns:
        spans.extend(match.group(0) for match in re.finditer(pattern, text))
    return spans


def extract_numbers(text: str) -> list[str]:
    return re.findall(r"(?<!\w)(?:\d+(?:\.\d+)?%?|\d{4})(?!\w)", text)


def sentence_split(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]


def word_tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'\-]*|\d+(?:\.\d+)?%?", text)


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()
