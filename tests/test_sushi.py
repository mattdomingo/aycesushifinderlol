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


if __name__ == "__main__":
    unittest.main()
