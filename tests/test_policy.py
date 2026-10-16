import unittest

from warden.policy import choose, risk_score


class PolicyTests(unittest.TestCase):
    def test_trusted_sender_does_not_excuse_a_payment_code(self) -> None:
        tactics = ("payment", "credential", "urgency")
        self.assertEqual(risk_score(tactics, True), risk_score(tactics, False))

    def test_trusted_sender_lowers_a_weak_signal(self) -> None:
        tactics = ("authority", "urgency")
        self.assertLess(risk_score(tactics, True), risk_score(tactics, False))

    def test_injection_without_a_scam_signal_opens_review(self) -> None:
        decision = choose(
            (),
            is_grounded=False,
            trusted_sender=False,
            autonomy="act",
            killed=False,
            injection=True,
        )
        self.assertEqual(decision.verdict, "review")
        self.assertEqual(decision.reason, "prompt_injection")

    def test_injection_does_not_clear_a_grounded_scam(self) -> None:
        decision = choose(
            ("payment", "credential", "urgency", "isolation"),
            is_grounded=True,
            trusted_sender=False,
            autonomy="act",
            killed=False,
            injection=True,
        )
        self.assertEqual(decision.verdict, "block")

    def test_ungrounded_harm_stops_for_a_person(self) -> None:
        decision = choose(
            ("payment", "credential"),
            is_grounded=False,
            trusted_sender=False,
            autonomy="act",
            killed=False,
        )
        self.assertEqual(decision.verdict, "review")
        self.assertEqual(decision.reason, "ungrounded")

    def test_kill_switch_overrides_a_block(self) -> None:
        decision = choose(
            ("payment", "credential", "urgency", "isolation"),
            is_grounded=True,
            trusted_sender=False,
            autonomy="act",
            killed=True,
        )
        self.assertEqual(decision.verdict, "review")
        self.assertEqual(decision.reason, "kill_switch")
        self.assertEqual(decision.tool, "open_review")

    def test_hold_autonomy_cannot_block(self) -> None:
        decision = choose(
            ("payment", "credential", "urgency", "isolation"),
            is_grounded=True,
            trusted_sender=False,
            autonomy="hold",
            killed=False,
        )
        self.assertEqual(decision.verdict, "quarantine")
        self.assertEqual(decision.reason, "autonomy_hold")
        self.assertEqual(decision.tool, "quarantine_message")


if __name__ == "__main__":
    unittest.main()
