"""Tests for the pricing engine and its HTTP endpoints."""

import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

from sushi import SushiPricingHandler, TimerError, TimerStore, build_quote, menu_payload


class PricingEngineTests(unittest.TestCase):
    def test_dinner_quote_includes_leftover_charge(self) -> None:
        self.assertEqual(
            build_quote("dinner", 2, 3),
            {"service": "dinner", "guests": 2, "price_per_guest": "32.95", "dining_subtotal": "65.90", "leftover_pieces": 3, "leftover_fee": "3.00", "total": "68.90", "currency": "USD"},
        )

    def test_menu_exposes_lunch_and_dinner_prices(self) -> None:
        self.assertEqual([service["name"] for service in menu_payload()["services"]], ["lunch", "dinner"])


class DiningTimerTests(unittest.TestCase):
    def test_timer_can_be_paused_resumed_and_reset(self) -> None:
        timers = TimerStore()
        created = timers.create(120, "Table 3")
        self.assertEqual(created["status"], "running")
        self.assertEqual(created["remaining_seconds"], 120)

        paused = timers.pause(created["id"])
        self.assertEqual(paused["status"], "paused")
        self.assertEqual(paused["table"], "Table 3")
        self.assertEqual(timers.resume(created["id"])["status"], "running")
        self.assertEqual(timers.reset(created["id"])["remaining_seconds"], 120)

    def test_unknown_timer_has_a_clear_error(self) -> None:
        with self.assertRaisesRegex(TimerError, "timer not found"):
            TimerStore().get("missing")


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

    def test_timer_endpoints_create_and_manage_a_table_timer(self) -> None:
        status, created = self.request("POST", "/api/timers", {"table": "Patio 2", "duration_minutes": 30})
        self.assertEqual(status, 201)
        self.assertEqual(created["duration_seconds"], 1800)
        self.assertEqual(created["status"], "running")

        status, paused = self.request("POST", f"/api/timers/{created['id']}/pause", {})
        self.assertEqual(status, 200)
        self.assertEqual(paused["status"], "paused")

        status, listed = self.request("GET", "/api/timers")
        self.assertEqual(status, 200)
        self.assertIn(created["id"], [timer["id"] for timer in listed["timers"]])
