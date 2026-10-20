"""Scene splitter — divide a transcript into timed scenes.

Each scene maps to one B-roll clip. Splitting is sentence-boundary based so
narration timing is preserved exactly.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Scene:
    index: int
    text: str
    start: float      # seconds into the narration
    end: float        # seconds into the narration
    visual_hint: str  # keyword query used to find footage
    relevance_score: float = 0.0
    clip_path: Optional[str] = None
    clip_meta: dict = field(default_factory=dict)


def split_into_scenes(
    text: str,
    audio_duration: float,
    pre_split_scenes: Optional[List[dict]] = None,
) -> List[Scene]:
    """Split *text* into scenes timed to *audio_duration*.

    If *pre_split_scenes* is supplied (IncuBrix scene list format), use those
    boundaries; otherwise split on sentence boundaries.
    Returns a list of Scene objects with proportional start/end times.
    """
    if pre_split_scenes:
        raw = [(s.get("text", ""), s.get("visual_hint", "")) for s in pre_split_scenes]
    else:
        sentences = _sentence_split(text)
        raw = [(s, _extract_hint(s)) for s in sentences if s.strip()]

    if not raw:
        return []

    # Distribute audio time proportionally by word count
    word_counts = [max(1, len(t.split())) for t, _ in raw]
    total_words = sum(word_counts)
    scenes: List[Scene] = []
    cursor = 0.0
    for i, ((txt, hint), wc) in enumerate(zip(raw, word_counts)):
        frac = wc / total_words
        duration = audio_duration * frac
        scenes.append(Scene(
            index=i,
            text=txt.strip(),
            start=round(cursor, 3),
            end=round(cursor + duration, 3),
            visual_hint=hint,
        ))
        cursor += duration
    return scenes


# ─── private helpers ──────────────────────────────────────────────────────────

_SENTENCE_RE = re.compile(r'(?<=[.!?])\s+')


def _sentence_split(text: str) -> List[str]:
    """Split on sentence boundaries; fall back to clause-level for long text."""
    parts = _SENTENCE_RE.split(text.strip())
    result = []
    for p in parts:
        if len(p.split()) > 40:
            # Split long sentence on comma/semicolon
            sub = re.split(r'[,;]\s+', p)
            result.extend(sub)
        else:
            result.append(p)
    return [p for p in result if p.strip()]


# Maps abstract concepts to more visual search terms
_ABSTRACT_MAP = {
    "trust": "handshake agreement",
    "value": "investment growth chart",
    "bank": "bank building finance",
    "cloud": "cloud computing data center",
    "python": "programming code development",
    "mouse": "computer mouse device",
    "saving money": "piggy bank savings",
    "sales": "business sales growth",
    "statistics": "data analytics chart",
    "saving": "piggy bank coins",
}


def _extract_hint(sentence: str) -> str:
    """Derive a visual search query from a sentence."""
    lower = sentence.lower()
    for abstract, concrete in _ABSTRACT_MAP.items():
        if abstract in lower:
            return concrete
    # Fallback: remove stopwords, take first 5 content words
    stopwords = {
        "the","a","an","is","are","was","were","be","been","being",
        "have","has","had","do","does","did","will","would","could","should",
        "may","might","shall","can","need","dare","ought","used","to","of",
        "in","on","at","by","for","with","about","against","between","into",
        "through","during","before","after","above","below","from","up","down",
        "out","off","over","under","again","then","once","and","but","or",
        "nor","so","yet","both","either","neither","not","only","own","same",
        "than","too","very","just","because","as","until","while","although",
        "if","though","since","when","where","which","who","that","this","it",
        "its","i","my","we","our","you","your","he","she","they","their",
    }
    words = [w for w in re.findall(r'[a-z]+', lower) if w not in stopwords]
    return " ".join(words[:5]) or sentence[:30]
