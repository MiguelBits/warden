"""Labeled-case gate. A moved verdict fails the run."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from warden.agent import triage
from warden.contracts import Inbound
from warden.control import RuntimeFlags
from warden.memory import MemoryStore

CATCH_VERDICTS = {"block", "quarantine"}
MIN_SCAM_CATCH = 0.8


def run_eval(root: Path) -> tuple[int, list[dict]]:
    cases_path = root / "evals" / "cases.jsonl"
    knowledge = root / "knowledge" / "playbooks"
    rows: list[dict] = []
    with tempfile.TemporaryDirectory() as tmp:
        memory = Path(tmp)
        for line in cases_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            case = json.loads(line)
            household_id = f"hh-{case['id']}"
            store = MemoryStore(memory)
            household = store.load(household_id)
            household["trusted_senders"] = list(case.get("trusted") or [])
            store.save(household)
            record = triage(
                Inbound(
                    household_id=household_id,
                    channel=case.get("channel", "sms"),
                    sender=case.get("sender", "unknown"),
                    text=case["text"],
                    case_id=case["id"],
                ),
                knowledge_dir=knowledge,
                memory_dir=memory,
                flags=RuntimeFlags(
                    autonomy=case.get("autonomy", "act"),
                    killed=bool(case.get("killed", False)),
                ),
            )
            rows.append(
                {
                    "id": case["id"],
                    "label": case["label"],
                    "expect": case["expect"],
                    "verdict": record.verdict,
                    "risk": record.risk,
                    "reason": record.reason,
                    "tool": record.tool,
                    "evidence": record.evidence[0]["id"] if record.grounded and record.evidence else "-",
                    "alert": record.alert,
                }
            )
    return _gate(rows)


def _gate(rows: list[dict]) -> tuple[int, list[dict]]:
    mismatches = [row for row in rows if row["verdict"] != row["expect"]]
    scam = [row for row in rows if row["label"] == "scam"]
    caught = [row for row in scam if row["verdict"] in CATCH_VERDICTS]
    benign_blocks = [row for row in rows if row["label"] == "benign" and row["verdict"] == "block"]
    catch_rate = (len(caught) / len(scam)) if scam else 1.0
    ok = not mismatches and catch_rate >= MIN_SCAM_CATCH and not benign_blocks
    _print(rows, catch_rate, ok, mismatches, benign_blocks)
    return (0 if ok else 1), rows


def _print(rows, catch_rate, ok, mismatches, benign_blocks) -> None:
    print(f"{'id':<22} {'label':<12} {'expect':<12} {'verdict':<12} {'risk':>4}  evidence")
    for row in rows:
        print(
            f"{row['id']:<22} {row['label']:<12} {row['expect']:<12} "
            f"{row['verdict']:<12} {row['risk']:>4}  {row['evidence']}"
        )
    print(f"scam_catch={catch_rate:.2f} mismatches={len(mismatches)} benign_blocks={len(benign_blocks)}")
    print("gate=pass" if ok else "gate=fail")
