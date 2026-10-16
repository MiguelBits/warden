import unittest
from pathlib import Path

from warden.retrieve import grounded, load_playbooks, search
from warden.tactics import detect_tactics

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOKS = ROOT / "knowledge" / "playbooks"


class RetrieveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.chunks = load_playbooks(PLAYBOOKS)

    def test_family_message_cites_the_family_playbook(self) -> None:
        text = "Ola mae, mudei de numero. Envia ja um codigo MB WAY e nao digas ao pai."
        tactics = detect_tactics(text)
        hits = search(text, self.chunks, tactics)
        self.assertEqual(hits[0].id, "family_impersonation", hits)
        self.assertTrue(grounded(hits, tactics))

    def test_bank_call_cites_the_bank_playbook(self) -> None:
        text = "This is your bank. Suspicious payment. Read the one-time code now. Do not tell anyone."
        tactics = detect_tactics(text)
        hits = search(text, self.chunks, tactics)
        self.assertEqual(hits[0].id, "bank_impersonation", hits)

    def test_benign_text_is_not_grounded(self) -> None:
        text = "I will be home at 7, please start dinner"
        tactics = detect_tactics(text)
        hits = search(text, self.chunks, tactics)
        self.assertFalse(grounded(hits, tactics))


if __name__ == "__main__":
    unittest.main()
