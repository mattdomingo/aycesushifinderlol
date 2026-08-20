"""Dependency-free backend for the Roll Call Sushi pricing tool.

Run ``python sushi.py serve`` to start the API. Invoking this file without
arguments keeps the original friendly command-line greeting intact.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from typing import Any
from urllib.parse import urlparse


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
DEFAULT_TIMER_DURATION_SECONDS = 2 * 60 * 60
MAX_TIMER_DURATION_SECONDS = 24 * 60 * 60


class PricingError(ValueError):
    """Raised when a quote request cannot be priced."""


class TimerError(ValueError):
    """Raised when a timer request cannot be completed."""


@dataclass
class DiningTimer:
    """A single table's elapsed-time tracker, stored in memory."""

    identifier: str
    duration_seconds: int
    table: str | None
    started_at: float
    remaining_seconds: float
    state: str = "running"
    paused_at: float | None = None

    def remaining_at(self, now: float) -> float:
        if self.state != "running":
            return self.remaining_seconds
        return max(0.0, self.remaining_seconds - (now - self.started_at))

    def snapshot(self, now: float | None = None) -> dict[str, Any]:
        now = time.monotonic() if now is None else now
        remaining = self.remaining_at(now)
        state = self.state
        if state == "running" and remaining == 0:
            state = "expired"
        whole_seconds = math.ceil(remaining)
        return {
            "id": self.identifier,
            "table": self.table,
            "status": state,
            "duration_seconds": self.duration_seconds,
            "remaining_seconds": whole_seconds,
            "elapsed_seconds": self.duration_seconds - whole_seconds,
        }


class TimerStore:
    """Thread-safe in-memory store for dining timers.

    Timers intentionally live only as long as the server process. Restaurant
    staff can use the API without setting up a database for this lightweight
    tool.
    """

    def __init__(self) -> None:
        self._timers: dict[str, DiningTimer] = {}
        self._lock = Lock()

    def create(self, duration_seconds: int, table: str | None) -> dict[str, Any]:
        now = time.monotonic()
        timer = DiningTimer(
            identifier=uuid.uuid4().hex,
            duration_seconds=duration_seconds,
            table=table,
            started_at=now,
            remaining_seconds=float(duration_seconds),
        )
        with self._lock:
            self._timers[timer.identifier] = timer
        return timer.snapshot(now)

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [timer.snapshot() for timer in self._timers.values()]

    def get(self, identifier: str) -> dict[str, Any]:
        with self._lock:
            return self._get(identifier).snapshot()

    def pause(self, identifier: str) -> dict[str, Any]:
        with self._lock:
            timer = self._get(identifier)
            now = time.monotonic()
            snapshot = timer.snapshot(now)
            if snapshot["status"] == "expired":
                timer.remaining_seconds = 0
                timer.state = "expired"
                raise TimerError("timer has expired")
            if timer.state == "paused":
                return snapshot
            timer.remaining_seconds = timer.remaining_at(now)
            timer.state = "paused"
            timer.paused_at = now
            return timer.snapshot(now)

    def resume(self, identifier: str) -> dict[str, Any]:
        with self._lock:
            timer = self._get(identifier)
            now = time.monotonic()
            snapshot = timer.snapshot(now)
            if snapshot["status"] == "expired":
                timer.remaining_seconds = 0
                timer.state = "expired"
                raise TimerError("timer has expired")
            if timer.state == "running":
                return snapshot
            timer.started_at = now
            timer.state = "running"
            timer.paused_at = None
            return timer.snapshot(now)

    def reset(self, identifier: str) -> dict[str, Any]:
        with self._lock:
            timer = self._get(identifier)
            timer.remaining_seconds = float(timer.duration_seconds)
            now = time.monotonic()
            timer.started_at = now
            timer.state = "running"
            timer.paused_at = None
            return timer.snapshot(now)

    def delete(self, identifier: str) -> None:
        with self._lock:
            self._get(identifier)
            del self._timers[identifier]

    def _get(self, identifier: str) -> DiningTimer:
        try:
            return self._timers[identifier]
        except KeyError:
            raise TimerError("timer not found") from None


TIMERS = TimerStore()


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


def _timer_duration(value: Any) -> int:
    """Validate a requested duration in whole minutes and return seconds."""
    try:
        minutes = _whole_number(value, "duration_minutes", minimum=1)
    except PricingError as error:
        raise TimerError(str(error)) from None
    seconds = minutes * 60
    if seconds > MAX_TIMER_DURATION_SECONDS:
        raise TimerError("duration_minutes must be 1440 or less")
    return seconds


def _table_name(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TimerError("table must be a string")
    table = value.strip()
    if not table:
        raise TimerError("table must not be blank")
    if len(table) > 80:
        raise TimerError("table must be 80 characters or fewer")
    return table


class SushiPricingHandler(BaseHTTPRequestHandler):
    """Small JSON API handler; no third-party web framework required."""
    server_version = "SushiPricing/1.1"

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
        elif path == "/api/menu":
            self._send_json(HTTPStatus.OK, menu_payload())
        elif path == "/api/timers":
            self._send_json(HTTPStatus.OK, {"timers": TIMERS.list()})
        elif (timer_id := self._timer_id(path)):
            try:
                self._send_json(HTTPStatus.OK, TIMERS.get(timer_id))
            except TimerError as error:
                self._send_timer_error(error)
        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "route not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/quote":
            self._create_quote()
            return

        if path == "/api/timers":
            self._create_timer()
            return

        parts = path.split("/")
        if len(parts) == 5 and parts[:3] == ["", "api", "timers"] and parts[4] in {
            "pause",
            "resume",
            "reset",
        }:
            self._change_timer(parts[3], parts[4])
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "route not found"})

    def do_DELETE(self) -> None:  # noqa: N802
        timer_id = self._timer_id(urlparse(self.path).path)
        if not timer_id:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "route not found"})
            return
        try:
            TIMERS.delete(timer_id)
        except TimerError as error:
            self._send_timer_error(error)
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _create_quote(self) -> None:
        try:
            payload = self._read_json()
            quote = build_quote(
                payload.get("service"), payload.get("guests"), payload.get("leftover_pieces", 0)
            )
        except PricingError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        self._send_json(HTTPStatus.OK, quote)

    def _create_timer(self) -> None:
        try:
            payload = self._read_optional_json()
            duration = _timer_duration(
                payload.get("duration_minutes", DEFAULT_TIMER_DURATION_SECONDS // 60)
            )
            table = _table_name(payload.get("table"))
        except TimerError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        self._send_json(HTTPStatus.CREATED, TIMERS.create(duration, table))

    def _change_timer(self, timer_id: str, action: str) -> None:
        try:
            result = getattr(TIMERS, action)(timer_id)
        except TimerError as error:
            self._send_timer_error(error)
            return
        self._send_json(HTTPStatus.OK, result)

    @staticmethod
    def _timer_id(path: str) -> str | None:
        parts = path.split("/")
        if len(parts) == 4 and parts[:3] == ["", "api", "timers"] and parts[3]:
            return parts[3]
        return None

    def _send_timer_error(self, error: TimerError) -> None:
        status = HTTPStatus.NOT_FOUND if str(error) == "timer not found" else HTTPStatus.CONFLICT
        self._send_json(status, {"error": str(error)})

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

    def _read_optional_json(self) -> dict[str, Any]:
        if self.headers.get("Content-Length") in (None, "0"):
            return {}
        try:
            return self._read_json()
        except PricingError as error:
            raise TimerError(str(error)) from None

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
