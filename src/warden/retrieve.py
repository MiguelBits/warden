"""Playbook retrieval. Citations stay attached to the decision."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from pathlib import Path

from warden.tactics import fold

_DIM = 64
_STOP = {
    "a", "an", "the", "to", "of", "and", "or", "for", "de", "da", "do", "das", "dos",
    "que", "em", "um", "uma", "is", "it", "this", "your", "you", "me", "my", "na",
    "no", "os", "as", "por", "com", "from", "that", "they", "them", "was", "are",
}


@dataclass(frozen=True)
class Chunk:
    id: str
    title: str
    tactics: tuple[str, ...]
    text: str


@dataclass(frozen=True)
class Hit:
    id: str
    score: float
    tactics: tuple[str, ...]
    title: str


def tokens(text: str) -> list[str]:
    return [tok for tok in re.findall(r"[a-z0-9]{2,}", fold(text)) if tok not in _STOP]


def embed(text: str, dim: int = _DIM) -> list[float]:
    """Hashing embedder. Swap this function for a hosted embedding model."""
    vec = [0.0] * dim
    words = tokens(text)
    if not words:
        return vec
    for word in words:
        digest = hashlib.sha256(word.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:2], "big") % dim
        sign = 1.0 if digest[2] % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(value * value for value in vec)) or 1.0
    return [value / norm for value in vec]


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _coverage(query: str, document: str) -> float:
    wanted = set(tokens(query))
    if not wanted:
        return 0.0
    have = set(tokens(document))
    return len(wanted & have) / len(wanted)


def parse_playbook(path: Path) -> Chunk:
    raw = path.read_text(encoding="utf-8")
    head, _, body = raw.partition("\n\n")
    meta: dict[str, str] = {}
    for line in head.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    if "id" not in meta:
        raise ValueError(f"{path} is missing an id")
    tactics = tuple(part.strip() for part in meta.get("tactics", "").split(",") if part.strip())
    title = meta["id"]
    for line in body.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    return Chunk(id=meta["id"], title=title, tactics=tactics, text=body.strip())


def load_playbooks(directory: Path) -> list[Chunk]:
    paths = sorted(directory.glob("*.md"))
    return [parse_playbook(path) for path in paths]


def search(query: str, chunks: list[Chunk], tactics: tuple[str, ...] = (), k: int = 3) -> list[Hit]:
    if k < 1 or not chunks:
        return []
    query_vec = embed(query)
    detected = set(tactics)
    hits: list[Hit] = []
    for chunk in chunks:
        text_score = 0.35 * _cosine(query_vec, embed(chunk.text)) + 0.65 * _coverage(query, chunk.text)
        if detected:
            boost = len(detected & set(chunk.tactics)) / len(detected)
        else:
            boost = 0.0
        score = 0.55 * text_score + 0.45 * boost
        hits.append(Hit(id=chunk.id, score=score, tactics=chunk.tactics, title=chunk.title))
    hits.sort(key=lambda hit: (-hit.score, hit.id))
    return hits[:k]


def grounded(hits: list[Hit], tactics: tuple[str, ...], minimum: float = 0.2) -> bool:
    if not hits or not tactics:
        return False
    top = hits[0]
    if top.score < minimum:
        return False
    return bool(set(top.tactics) & set(tactics))
