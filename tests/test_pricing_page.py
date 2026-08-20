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

    def test_page_has_a_descriptive_title_and_menu_description(self) -> None:
        self.assertIn("<title>Roll Call Sushi | All You Can Eat</title>", self.html)
        self.assertIn(
            {"name": "description", "content": "An all-you-can-eat sushi menu."},
            self.page.meta,
        )

    def test_primary_dinner_price_is_displayed_per_guest(self) -> None:
        self.assertIn("$32.95 per guest", self.page.rendered_text)

    def test_lunch_and_dinner_prices_and_availability_are_clear(self) -> None:
        page_text = self.page.rendered_text
        self.assertIn("Lunch: $24.95 · Mon–Fri, 11:30am–3pm", page_text)
        self.assertIn("Dinner: $32.95 · Daily after 3pm", page_text)

    def test_dining_rules_disclose_time_limit_and_leftover_fee(self) -> None:
        page_text = self.page.rendered_text
        self.assertIn("Two-hour dining limit.", page_text)
        self.assertIn("$1 charge may apply for each leftover piece.", page_text)

    def test_all_menu_categories_and_items_are_present(self) -> None:
        page_text = self.page.rendered_text
        for category in ("Start here", "Classic rolls", "Nigiri & sashimi"):
            self.assertIn(category, page_text)
        for item in (
            "Edamame",
            "Miso soup",
            "Gyoza",
            "Seaweed salad",
            "Spicy tuna",
            "California",
            "Salmon avocado",
            "Crunchy shrimp",
            "Salmon",
            "Tuna",
            "Yellowtail",
            "Sweet shrimp",
        ):
            self.assertIn(item, page_text)

    def test_portion_sizes_are_disclosed_for_rolls_and_nigiri(self) -> None:
        self.assertIn("Six pieces each", self.page.rendered_text)
        self.assertIn("Two pieces each", self.page.rendered_text)

    def test_menu_section_is_labeled_for_assistive_technology(self) -> None:
        self.assertIn('<section class="menu-card" aria-labelledby="menu-heading">', self.html)
        self.assertIn('<h2 id="menu-heading">All-you-can-eat menu</h2>', self.html)

    def test_reservation_action_uses_a_clickable_phone_link(self) -> None:
        self.assertIn(
            {"class": "button", "href": "tel:+15555550188"}, self.page.links
        )

    def test_mobile_breakpoints_keep_menu_usable_on_narrow_screens(self) -> None:
        self.assertIn("@media (max-width: 750px)", self.html)
        self.assertIn(".menu-grid { grid-template-columns: 1fr; }", self.html)
        self.assertIn("@media (max-width: 430px)", self.html)


if __name__ == "__main__":
    unittest.main()
