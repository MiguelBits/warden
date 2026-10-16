import json
import unittest
from pathlib import Path

from warden.cli import main
from warden.evaluate import run_eval

ROOT = Path(__file__).resolve().parents[1]


class EvalGateTests(unittest.TestCase):
    def test_labeled_gate_passes(self) -> None:
        code, rows = run_eval(ROOT)
        self.assertEqual(code, 0, rows)
        by_id = {row["id"]: row for row in rows}
        self.assertEqual(by_id["family-mbway"]["verdict"], "block")
        self.assertEqual(by_id["dinner"]["verdict"], "allow")
        self.assertNotIn("482913", json.dumps(by_id["injection-transfer"]))

    def test_cli_eval_exits_zero(self) -> None:
        self.assertEqual(main(["eval", "--root", str(ROOT)]), 0)


if __name__ == "__main__":
    unittest.main()
