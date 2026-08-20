"""Tests for the pricing engine and its HTTP endpoints."""

import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

from sushi import SushiPricingHandler, build_quote, menu_payload


class PricingEngineTests(unittest.TestCase):
    def test_dinner_quote_includes_leftover_charge(self) -> None:
        self.assertEqual(
            build_quote("dinner", 2, 3),
            {"service": "dinner", "guests": 2, "price_per_guest": "32.95", "dining_subtotal": "65.90", "leftover_pieces": 3, "leftover_fee": "3.00", "total": "68.90", "currency": "USD"},
        )

    def test_menu_exposes_lunch_and_dinner_prices(self) -> None:
        self.assertEqual([service["name"] for service in menu_payload()["services"]], ["lunch", "dinner"])


class PricingApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), SushiPricingHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, method: str, path: str, payload=None):
        connection = HTTPConnection("127.0.0.1", self.server.server_port)
        body = json.dumps(payload) if payload is not None else None
        connection.request(method, path, body, {"Content-Type": "application/json"})
        response = connection.getresponse()
        result = response.status, json.loads(response.read())
        connection.close()
        return result

    def test_quote_endpoint(self) -> None:
        status, payload = self.request("POST", "/api/quote", {"service": "lunch", "guests": 3})
        self.assertEqual(status, 200)
        self.assertEqual(payload["total"], "74.85")

    def test_quote_rejects_invalid_guest_count(self) -> None:
        status, payload = self.request("POST", "/api/quote", {"service": "lunch", "guests": 0})
        self.assertEqual(status, 400)
        self.assertIn("guests", payload["error"])
