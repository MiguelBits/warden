"""Per-household memory. Incidents keep the decision and drop the body."""

from __future__ import annotations

import json
from pathlib import Path


class MemoryStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, household_id: str) -> Path:
        safe = "".join(ch for ch in household_id if ch.isalnum() or ch in {"-", "_"})
        if not safe:
            raise ValueError("household_id is empty after normalization")
        return self.root / f"{safe}.json"

    def load(self, household_id: str) -> dict:
        path = self.path_for(household_id)
        if not path.is_file():
            return {"household_id": household_id, "trusted_senders": [], "incidents": []}
        data = json.loads(path.read_text(encoding="utf-8"))
        data.setdefault("household_id", household_id)
        data.setdefault("trusted_senders", [])
        data.setdefault("incidents", [])
        return data

    def save(self, record: dict) -> None:
        path = self.path_for(record["household_id"])
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    def trusted(self, record: dict, sender: str) -> bool:
        names = {str(item).casefold() for item in record.get("trusted_senders") or []}
        return sender.casefold() in names

    def append_incident(self, record: dict, incident: dict) -> dict:
        incidents = list(record.get("incidents") or [])
        incidents.append(incident)
        record["incidents"] = incidents[-50:]
        self.save(record)
        return record
