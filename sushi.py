"""Dependency-free backend for the Roll Call Sushi pricing tool.

Run ``python sushi.py serve`` to start the API. Invoking this file without
arguments keeps the original friendly command-line greeting intact.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


MONEY_PLACES = Decimal("0.01")


@dataclass(frozen=True)
class PricingRule:
    name: str
    price_per_guest: Decimal
    description: str


PRICING_RULES = {
    "lunch": PricingRule("lunch", Decimal("24.95"), "Mon–Fri, 11:30am–3pm"),
    "dinner": PricingRule("dinner", Decimal("32.95"), "Daily after 3pm"),
}
LEFTOVER_FEE_PER_PIECE = Decimal("1.00")


class PricingError(ValueError):
    """Raised when a quote request cannot be priced."""


def money(value: Decimal) -> str:
    return format(value.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP), ".2f")


def build_quote(service: str, guests: Any, leftover_pieces: Any = 0) -> dict[str, Any]:
    """Calculate an all-you-can-eat quote from validated request values."""
    if not isinstance(service, str) or service not in PRICING_RULES:
        raise PricingError("service must be one of: lunch, dinner")

    guest_count = _whole_number(guests, "guests", minimum=1)
    leftovers = _whole_number(leftover_pieces, "leftover_pieces", minimum=0)
    rule = PRICING_RULES[service]
    dining_subtotal = rule.price_per_guest * guest_count
    leftover_fee = LEFTOVER_FEE_PER_PIECE * leftovers
    total = dining_subtotal + leftover_fee
    return {
        "service": service,
        "guests": guest_count,
        "price_per_guest": money(rule.price_per_guest),
        "dining_subtotal": money(dining_subtotal),
        "leftover_pieces": leftovers,
        "leftover_fee": money(leftover_fee),
        "total": money(total),
        "currency": "USD",
    }


def menu_payload() -> dict[str, Any]:
    """Return the prices and rules the client needs to render the tool."""
    return {
        "currency": "USD",
        "leftover_fee_per_piece": money(LEFTOVER_FEE_PER_PIECE),
        "services": [
            {**asdict(rule), "price_per_guest": money(rule.price_per_guest)}
            for rule in PRICING_RULES.values()
        ],
    }


def _whole_number(value: Any, field: str, minimum: int) -> int:
    if isinstance(value, bool):
        raise PricingError(f"{field} must be a whole number")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise PricingError(f"{field} must be a whole number") from None
    if not number.is_finite() or number != number.to_integral_value():
        raise PricingError(f"{field} must be a whole number")
    result = int(number)
    if result < minimum:
        if minimum:
            raise PricingError(f"{field} must be at least {minimum}")
        raise PricingError(f"{field} must be zero or greater")
    return result


class SushiPricingHandler(BaseHTTPRequestHandler):
    """Small JSON API handler; no third-party web framework required."""
    server_version = "SushiPricing/1.0"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
        elif self.path == "/api/menu":
            self._send_json(HTTPStatus.OK, menu_payload())
        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "route not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/quote":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "route not found"})
            return
        try:
            payload = self._read_json()
            quote = build_quote(
                payload.get("service"), payload.get("guests"), payload.get("leftover_pieces", 0)
            )
        except PricingError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        self._send_json(HTTPStatus.OK, quote)

    def _read_json(self) -> dict[str, Any]:
        length = self.headers.get("Content-Length")
        if not length:
            raise PricingError("request body is required")
        try:
            body = self.rfile.read(int(length))
            payload = json.loads(body)
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            raise PricingError("request body must be valid JSON") from None
        if not isinstance(payload, dict):
            raise PricingError("request body must be a JSON object")
        return payload

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        """Keep normal API requests from cluttering command-line output."""


def serve() -> None:
    """Start the local HTTP server using configurable host and port values."""
    host = os.getenv("SUSHI_HOST", "127.0.0.1")
    port = int(os.getenv("SUSHI_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), SushiPricingHandler)
    print(f"Sushi pricing API listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down sushi pricing API.")
    finally:
        server.server_close()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("i love sushi")
    elif sys.argv[1:] == ["serve"]:
        serve()
    else:
        print("Usage: python sushi.py [serve]", file=sys.stderr)
        raise SystemExit(2)
