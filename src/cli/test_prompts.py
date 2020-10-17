from unittest import TestCase
import unittest

from src.cli.prompts import _password_check


class Test(TestCase):
    def test__password_check(self):
        self.assertEqual(True, _password_check("11"), "Should PASS - too short")
        self.assertEqual(True, _password_check("11jhjdkjdhdjkhdk"), "ShouldPASS - no capital")
        self.assertEqual(True, _password_check("11^&^YGYG$YGUGygygy"), "ShouldPASS - has $&")
        self.assertEqual(False, _password_check("11Tggghghghhghg"), "ShouldPASS - Complaint")


if __name__ == '__main__':
    unittest.main()
