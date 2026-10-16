"""Deterministic tactic tags. The model is not on this path."""

from __future__ import annotations

import re

_FOLD = str.maketrans("áàâãéêíóôõúç", "aaaaeeiooouc")

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("urgency", re.compile(r"\b(now|immediately|urgent|urgente|agora|ja|right away|last chance)\b")),
    (
        "payment",
        re.compile(
            r"\b(pay|payment|pague|pagar|mb ?way|mbway|multibanco|iban|transfer\w*|gift card|wire)\b"
        ),
    ),
    (
        "credential",
        re.compile(r"\b(otp|one[- ]time|pin|password|palavra[- ]passe|codigo|code|verification code)\b"),
    ),
    (
        "isolation",
        re.compile(r"\b(do not tell|dont tell|nao digas|nao contes|keep this secret|segredo)\b"),
    ),
    (
        "authority",
        re.compile(r"\b(bank|banco|police|policia|financas|seguranca social|ctt|microsoft|amazon|irs)\b"),
    ),
    (
        "family_hook",
        re.compile(r"\b(hi mum|hi mom|ola mae|ola pai|new number|mudei de numero|its me|sou eu)\b"),
    ),
)

_LINK = re.compile(r"https?://|www\.", re.I)
_INJECTION = re.compile(
    r"ignore (all |previous |prior )?instructions|system prompt|you are now|mark this message as safe"
)


def fold(text: str) -> str:
    lowered = (text or "").lower().translate(_FOLD)
    return lowered.replace("'", "").replace("\u2019", "").replace("\u2018", "")


def detect_tactics(text: str) -> tuple[str, ...]:
    folded = fold(text)
    found = [name for name, pattern in _PATTERNS if pattern.search(folded)]
    if _LINK.search(text or ""):
        found.append("link")
    return tuple(found)


def is_injection(text: str) -> bool:
    return bool(_INJECTION.search(fold(text)))
