import json
import tempfile
import unittest
from pathlib import Path

from warden.agent import triage
from warden.contracts import Inbound
from warden.control import RuntimeFlags

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOKS = ROOT / "knowledge" / "playbooks"
SCAM = "Transfer to IBAN PT50000201231234567890154 now. Code 482913. Do not tell anyone."


class AgentTests(unittest.TestCase):
    def test_decision_record_drops_the_message_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = triage(
                Inbound("casa-1", "sms", "unknown", SCAM, case_id="case-1"),
                knowledge_dir=PLAYBOOKS,
                memory_dir=Path(tmp),
                flags=RuntimeFlags(autonomy="act"),
            )
            dumped = json.dumps(record.to_dict())
            self.assertNotIn("482913", dumped)
            self.assertNotIn("PT50000201231234567890154", dumped)
            self.assertNotIn("482913", record.alert)
            stored = Path(tmp, "casa-1.json").read_text(encoding="utf-8")
            self.assertNotIn("482913", stored)
            self.assertNotIn(SCAM, stored)
            self.assertEqual(record.verdict, "block")

    def test_empty_knowledge_cannot_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp, "knowledge")
            empty.mkdir()
            record = triage(
                Inbound("casa-1", "sms", "unknown", "Send the MB WAY code now"),
                knowledge_dir=empty,
                memory_dir=Path(tmp, "memory"),
                flags=RuntimeFlags(autonomy="act"),
            )
            self.assertEqual(record.verdict, "review")
            self.assertEqual(record.reason, "ungrounded")

    def test_killed_runtime_queues_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = triage(
                Inbound("casa-1", "sms", "unknown", SCAM),
                knowledge_dir=PLAYBOOKS,
                memory_dir=Path(tmp),
                flags=RuntimeFlags(autonomy="act", killed=True),
            )
            self.assertEqual(record.verdict, "review")
            self.assertEqual(record.reason, "kill_switch")
            self.assertEqual(record.tool, "open_review")


if __name__ == "__main__":
    unittest.main()
