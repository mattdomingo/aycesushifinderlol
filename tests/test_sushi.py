"""Tests for the sushi command-line script."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class SushiScriptTests(unittest.TestCase):
    def run_script(self, *args: str, **kwargs: object) -> subprocess.CompletedProcess:
        """Run the script as a user would, without invoking a shell."""
        return subprocess.run(
            [sys.executable, str(REPOSITORY_ROOT / "sushi.py"), *args],
            capture_output=True,
            text=True,
            **kwargs,
        )

    def test_prints_expected_message(self) -> None:
        result = self.run_script(check=True)

        self.assertEqual(result.stdout, "i love sushi\n")
        self.assertEqual(result.stderr, "")

    def test_ignores_edge_and_option_like_arguments(self) -> None:
        result = self.run_script(
            "--help",
            "--",
            "sushi roll",
            "🍣",
            "$(not-a-shell-command)",
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "i love sushi\n")
        self.assertEqual(result.stderr, "")

    def test_ignores_malformed_binary_standard_input(self) -> None:
        result = subprocess.run(
            [sys.executable, str(REPOSITORY_ROOT / "sushi.py")],
            input=b"\x00\xffnot valid UTF-8\n",
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"i love sushi\n")
        self.assertEqual(result.stderr, b"")

    def test_runs_from_an_unrelated_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            result = self.run_script(cwd=temporary_directory)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "i love sushi\n")
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
