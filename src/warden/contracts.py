"""Stable shapes shared by the agent, the eval gate, and the control plane."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


CHANNELS = ("sms", "call", "message")
VERDICTS = ("allow", "quarantine", "block", "review")
AUTONOMY = ("observe", "hold", "act")


@dataclass(frozen=True)
class Inbound:
    household_id: str
    channel: str
    sender: str
    text: str
    case_id: str = ""

    def __post_init__(self) -> None:
        if self.channel not in CHANNELS:
            raise ValueError(f"channel must be one of {CHANNELS}")
        if not self.household_id.strip():
            raise ValueError("household_id is required")
        if len(self.text) > 4000:
            raise ValueError("text exceeds 4000 characters")


@dataclass(frozen=True)
class Evidence:
    id: str
    score: float
    tactics: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"id": self.id, "score": round(self.score, 4), "tactics": list(self.tactics)}


@dataclass
class Record:
    """Decision contract. The message body is never stored here."""

    case_id: str
    household_id: str
    channel: str
    sender: str
    verdict: str
    risk: int
    reason: str
    tactics: list[str]
    grounded: bool
    evidence: list[dict]
    tool: str
    alert: str
    autonomy: str
    killed: bool
    stopped_by: str = ""
    steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["steps"] = list(self.steps)
        return data
