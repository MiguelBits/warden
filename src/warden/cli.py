"""Local triage and the eval gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from warden.agent import triage
from warden.contracts import Inbound
from warden.control import RuntimeFlags
from warden.evaluate import run_eval

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="warden")
    sub = parser.add_subparsers(dest="cmd", required=True)

    triage_cmd = sub.add_parser("triage", help="Score one message and pick one tool")
    triage_cmd.add_argument("--household", required=True)
    triage_cmd.add_argument("--channel", default="sms", choices=("sms", "call", "message"))
    triage_cmd.add_argument("--sender", default="unknown")
    triage_cmd.add_argument("--text", required=True)
    triage_cmd.add_argument("--autonomy", default="act", choices=("observe", "hold", "act"))
    triage_cmd.add_argument("--killed", action="store_true")
    triage_cmd.add_argument("--json", action="store_true")
    triage_cmd.add_argument("--knowledge", type=Path, default=ROOT / "knowledge" / "playbooks")
    triage_cmd.add_argument("--memory", type=Path, default=ROOT / "data" / "households")

    eval_cmd = sub.add_parser("eval", help="Run the labeled gate")
    eval_cmd.add_argument("--root", type=Path, default=ROOT)

    args = parser.parse_args(argv)
    if args.cmd == "eval":
        code, _rows = run_eval(args.root)
        return code
    record = triage(
        Inbound(
            household_id=args.household,
            channel=args.channel,
            sender=args.sender,
            text=args.text,
        ),
        knowledge_dir=args.knowledge,
        memory_dir=args.memory,
        flags=RuntimeFlags(autonomy=args.autonomy, killed=args.killed),
    )
    if args.json:
        json.dump(record.to_dict(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    if record.grounded and record.evidence:
        top = record.evidence[0]
        grounded_line = f"yes {top['id']} {top['score']}"
    else:
        grounded_line = "no"
    print(f"verdict: {record.verdict}")
    print(f"risk: {record.risk}")
    print(f"tool: {record.tool}")
    print(f"reason: {record.reason}")
    print(f"tactics: {', '.join(record.tactics) or 'none'}")
    print(f"grounded: {grounded_line}")
    print(f"alert: {record.alert}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
