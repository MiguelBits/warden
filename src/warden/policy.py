"""Bounded autonomy. A high score cannot skip the contract."""

from __future__ import annotations

from dataclasses import dataclass

WEIGHTS = {
    "urgency": 12,
    "payment": 22,
    "credential": 22,
    "isolation": 16,
    "authority": 14,
    "family_hook": 14,
    "link": 12,
}

_HARMFUL = {"payment", "credential", "link", "isolation"}
_SENSITIVE = {"payment", "credential"}
_TOOL = {
    "allow": "allow_through",
    "quarantine": "quarantine_message",
    "block": "block_sender",
    "review": "open_review",
}


@dataclass(frozen=True)
class PolicyDecision:
    verdict: str
    risk: int
    reason: str
    tool: str


def risk_score(tactics: tuple[str, ...], trusted_sender: bool) -> int:
    score = sum(WEIGHTS[name] for name in tactics)
    if trusted_sender and not (_SENSITIVE & set(tactics)):
        score = max(0, score - 18)
    return min(100, score)


def choose(
    tactics: tuple[str, ...],
    *,
    is_grounded: bool,
    trusted_sender: bool,
    autonomy: str,
    killed: bool,
    injection: bool = False,
) -> PolicyDecision:
    if autonomy not in {"observe", "hold", "act"}:
        autonomy = "observe"
    risk = risk_score(tactics, trusted_sender)
    harmful = bool(set(tactics) & _HARMFUL)

    if killed:
        return PolicyDecision("review", risk, "kill_switch", _TOOL["review"])
    if autonomy == "observe":
        return PolicyDecision("review", risk, "autonomy_observe", _TOOL["review"])
    if injection and not harmful:
        return PolicyDecision("review", risk, "prompt_injection", _TOOL["review"])
    if harmful and risk >= 40 and not is_grounded:
        return PolicyDecision("review", risk, "ungrounded", _TOOL["review"])

    if risk >= 70 and harmful and is_grounded:
        desired = "block"
    elif risk >= 45 and harmful and is_grounded:
        desired = "quarantine"
    elif risk <= 28 and not (_SENSITIVE & set(tactics)):
        desired = "allow"
    else:
        desired = "review"

    if desired == "block" and autonomy == "hold":
        return PolicyDecision("quarantine", risk, "autonomy_hold", _TOOL["quarantine"])
    if injection and desired == "allow":
        return PolicyDecision("review", risk, "prompt_injection", _TOOL["review"])
    return PolicyDecision(desired, risk, "policy", _TOOL[desired])
