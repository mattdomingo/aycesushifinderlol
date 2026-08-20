"""Tests for the sushi command-line script."""

from pathlib import Path
import subprocess
import sys
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class SushiScriptTests(unittest.TestCase):
    def test_prints_expected_message(self) -> None:
        result = subprocess.run(
            [sys.executable, "sushi.py"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertEqual(result.stdout, "i love sushi\n")
        self.assertEqual(result.stderr, "")

    def test_rejects_unknown_command_with_usage(self) -> None:
        result = subprocess.run(
            [sys.executable, "sushi.py", "unknown"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "Usage: python sushi.py [serve]\n")


if __name__ == "__main__":
    unittest.main()
