import unittest
from datetime import datetime, timezone

from warden.control import flags_from_health


class ControlTests(unittest.TestCase):
    def test_armed_lease_can_act(self) -> None:
        now = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
        flags = flags_from_health(
            {"killed": False, "lease": {"armed_until": "2026-10-16T12:30:00Z"}},
            now,
        )
        self.assertEqual(flags.autonomy, "act")
        self.assertFalse(flags.killed)

    def test_expired_lease_can_hold_only(self) -> None:
        now = datetime(2026, 10, 16, 13, 0, tzinfo=timezone.utc)
        flags = flags_from_health(
            {"killed": False, "lease": {"armed_until": "2026-10-16T12:30:00Z"}},
            now,
        )
        self.assertEqual(flags.autonomy, "hold")

    def test_kill_switch_forces_observe(self) -> None:
        now = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
        flags = flags_from_health(
            {"killed": True, "lease": {"armed_until": "2026-10-16T12:30:00Z"}},
            now,
        )
        self.assertEqual(flags.autonomy, "observe")
        self.assertTrue(flags.killed)


if __name__ == "__main__":
    unittest.main()
