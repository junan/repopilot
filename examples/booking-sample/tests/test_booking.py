"""Regression tests for the sample booking service.

``test_retry_with_same_idempotency_key_does_not_duplicate`` currently fails.
That failure is intentional: it is the defect RepoPilot is meant to fix.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from booking.handler import BookingService


def test_create_reservation_returns_booking() -> None:
    service = BookingService()

    reservation = service.create_reservation("room-101", "Ada")

    assert reservation.room_id == "room-101"
    assert reservation.guest == "Ada"
    assert service.store.count() == 1


def test_retry_with_same_idempotency_key_does_not_duplicate() -> None:
    service = BookingService()

    first = service.create_reservation(
        "room-202",
        "Grace",
        idempotency_key="retry-1",
    )
    second = service.create_reservation(
        "room-202",
        "Grace",
        idempotency_key="retry-1",
    )

    assert first.id == second.id
    assert service.store.count() == 1
