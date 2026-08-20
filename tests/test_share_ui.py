"""Regression tests for the static page's sharing controls."""

from pathlib import Path
import unittest


PAGE = Path(__file__).resolve().parents[1] / "index.html"


class ShareUiTests(unittest.TestCase):
    def test_share_control_has_native_and_copy_link_paths(self) -> None:
        page = PAGE.read_text(encoding="utf-8")

        self.assertIn('id="share-app"', page)
        self.assertIn('id="share-status" aria-live="polite"', page)
        self.assertIn("navigator.share(shareData)", page)
        self.assertIn("navigator.clipboard.writeText(shareData.url)", page)


if __name__ == "__main__":
    unittest.main()
