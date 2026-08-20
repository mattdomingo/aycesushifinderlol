"""Regression tests for the all-you-can-eat sushi menu page."""

from html.parser import HTMLParser
from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MENU_PAGE = REPOSITORY_ROOT / "index.html"


class MenuPageParser(HTMLParser):
    """Collect page text and attributes without requiring third-party packages."""

    def __init__(self) -> None:
        super().__init__()
        self.text = []
        self.headings = []
        self.links = []
        self.meta = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag in {"h1", "h2", "h3"}:
            self.headings.append((tag, attributes))
        elif tag == "a":
            self.links.append(attributes)
        elif tag == "meta":
            self.meta.append(attributes)

    def handle_data(self, data: str) -> None:
        self.text.append(data)

    @property
    def rendered_text(self) -> str:
        return " ".join(" ".join(self.text).split())


class SushiPricingPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = MENU_PAGE.read_text(encoding="utf-8")
        cls.page = MenuPageParser()
        cls.page.feed(cls.html)

    def test_page_has_a_descriptive_title_and_pricing_description(self) -> None:
        self.assertIn("<title>Roll Call Sushi | Price Your Visit</title>", self.html)
        self.assertIn(
            {
                "name": "description",
                "content": "Calculate the price of your all-you-can-eat sushi visit.",
            },
            self.page.meta,
        )

    def test_pricing_choices_are_displayed(self) -> None:
        page_text = self.page.rendered_text
        self.assertIn("Weekday lunch Mon–Fri · before 3pm", page_text)
        self.assertIn("Dinner Daily · after 3pm", page_text)
        self.assertIn("Weekend Sat–Sun · all day", page_text)

    def test_dining_rules_disclose_time_limit_and_leftover_fee(self) -> None:
        page_text = self.page.rendered_text
        self.assertIn("A two-hour dining limit applies.", page_text)
        self.assertIn("$1 charge applies to each leftover piece.", page_text)

    def test_share_control_has_an_accessible_status_message(self) -> None:
        self.assertIn('id="share-app"', self.html)
        self.assertIn('aria-describedby="share-status"', self.html)
        self.assertIn('id="share-status" role="status"', self.html)

    def test_sharing_uses_the_native_share_sheet_and_copy_fallback(self) -> None:
        self.assertIn("navigator.share", self.html)
        self.assertIn("navigator.clipboard?.writeText", self.html)
        self.assertIn("url:window.location.href", self.html)

    def test_mobile_breakpoint_keeps_pricing_tool_usable_on_narrow_screens(self) -> None:
        self.assertIn("@media (max-width:720px)", self.html)
        self.assertIn("@media (max-width:430px)", self.html)


if __name__ == "__main__":
    unittest.main()
