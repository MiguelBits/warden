"""Tool contracts. Adapters that place real calls would implement these names."""

from __future__ import annotations

from dataclasses import dataclass

RANK = {"observe": 0, "hold": 1, "act": 2}


@dataclass(frozen=True)
class ToolContract:
    name: str
    effect: str
    min_autonomy: str
    description: str


CONTRACTS: dict[str, ToolContract] = {
    "allow_through": ToolContract(
        "allow_through",
        "deliver",
        "observe",
        "Release the message to the household device.",
    ),
    "quarantine_message": ToolContract(
        "quarantine_message",
        "hold",
        "hold",
        "Keep the message off the lock screen and alert the household.",
    ),
    "block_sender": ToolContract(
        "block_sender",
        "drop",
        "act",
        "Drop the message and suppress the sender for this case.",
    ),
    "open_review": ToolContract(
        "open_review",
        "queue_human",
        "observe",
        "Stop automated action and queue a person.",
    ),
}


def authorize(tool_name: str, autonomy: str, killed: bool) -> str:
    """Return an empty string when the tool may run, otherwise the stop reason."""
    contract = CONTRACTS[tool_name]
    if killed and tool_name != "open_review":
        return "kill_switch"
    level = RANK.get(autonomy, 0)
    if level < RANK[contract.min_autonomy]:
        return "autonomy"
    return ""


def render_alert(channel: str, verdict: str, tactics: tuple[str, ...] | list[str]) -> str:
    label = {"sms": "SMS", "call": "call", "message": "message"}.get(channel, "message")
    action = {
        "allow": "delivered",
        "quarantine": "held",
        "block": "blocked",
        "review": "queued",
    }[verdict]
    shown = ", ".join(tactics) if tactics else "none"
    return f"Warden {action} an {label}. Tactics: {shown}."


def execute(tool_name: str, channel: str, verdict: str, tactics: tuple[str, ...]) -> dict:
    contract = CONTRACTS[tool_name]
    return {
        "tool": contract.name,
        "effect": contract.effect,
        "alert": render_alert(channel, verdict, tactics),
    }
