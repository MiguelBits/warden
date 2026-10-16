"""Map a control-plane health payload onto runtime flags."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class RuntimeFlags:
    autonomy: str = "act"
    killed: bool = False


def lease_active(lease: dict | None, now: datetime | None = None) -> bool:
    until = (lease or {}).get("armed_until")
    if not until or not isinstance(until, str):
        return False
    try:
        armed_until = datetime.fromisoformat(until.replace("Z", "+00:00"))
    except ValueError:
        return False
    if armed_until.tzinfo is None:
        armed_until = armed_until.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    return armed_until > current


def flags_from_health(health: dict, now: datetime | None = None) -> RuntimeFlags:
    """Block only while a person has armed the lease and the kill switch is off."""
    killed = bool(health.get("killed"))
    if killed:
        return RuntimeFlags(autonomy="observe", killed=True)
    if lease_active(health.get("lease") or {}, now):
        return RuntimeFlags(autonomy="act", killed=False)
    return RuntimeFlags(autonomy="hold", killed=False)
