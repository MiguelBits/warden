"""Orchestrate memory, retrieval, policy, and one authorized tool."""

from __future__ import annotations

import uuid
from pathlib import Path

from warden.contracts import Inbound, Record
from warden.control import RuntimeFlags
from warden.memory import MemoryStore
from warden.policy import choose
from warden.retrieve import grounded, load_playbooks, search
from warden.tactics import detect_tactics, is_injection
from warden.tools import authorize, execute


def triage(
    inbound: Inbound,
    *,
    knowledge_dir: Path,
    memory_dir: Path,
    flags: RuntimeFlags | None = None,
) -> Record:
    flags = flags or RuntimeFlags()
    steps = [
        "load_memory",
        "detect_tactics",
        "retrieve",
        "policy",
        "authorize",
        "execute",
        "persist_memory",
    ]
    store = MemoryStore(memory_dir)
    household = store.load(inbound.household_id)
    tactics = detect_tactics(inbound.text)
    chunks = load_playbooks(knowledge_dir)
    hits = search(inbound.text, chunks, tactics)
    is_grounded = grounded(hits, tactics)
    decision = choose(
        tactics,
        is_grounded=is_grounded,
        trusted_sender=store.trusted(household, inbound.sender),
        autonomy=flags.autonomy,
        killed=flags.killed,
        injection=is_injection(inbound.text),
    )
    tool_name = decision.tool
    stopped = authorize(tool_name, flags.autonomy, flags.killed)
    reason = decision.reason
    verdict = decision.verdict
    if stopped:
        tool_name = "open_review"
        verdict = "review"
        reason = stopped
        steps.append("downgrade_review")
    result = execute(tool_name, inbound.channel, verdict, tactics)
    case_id = inbound.case_id or uuid.uuid4().hex[:12]
    record = Record(
        case_id=case_id,
        household_id=inbound.household_id,
        channel=inbound.channel,
        sender=inbound.sender,
        verdict=verdict,
        risk=decision.risk,
        reason=reason,
        tactics=list(tactics),
        grounded=is_grounded,
        evidence=[hit_to_dict(hit) for hit in hits],
        tool=result["tool"],
        alert=result["alert"],
        autonomy=flags.autonomy,
        killed=flags.killed,
        stopped_by=stopped,
        steps=steps,
    )
    store.append_incident(
        household,
        {
            "case_id": record.case_id,
            "verdict": record.verdict,
            "risk": record.risk,
            "reason": record.reason,
            "tactics": record.tactics,
            "tool": record.tool,
            "sender": record.sender,
            "channel": record.channel,
        },
    )
    return record


def hit_to_dict(hit) -> dict:
    return {"id": hit.id, "score": round(hit.score, 4)}
