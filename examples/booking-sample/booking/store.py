"""In-memory reservation store for the sample booking service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class Reservation:
    """A booked room for a guest."""

    id: str
    room_id: str
    guest: str
    idempotency_key: str | None = None


@dataclass
class ReservationStore:
    """Simple store used by the sample handler."""

    _by_id: dict[str, Reservation] = field(default_factory=dict)

    def add(self, room_id: str, guest: str, idempotency_key: str | None = None) -> Reservation:
        reservation = Reservation(
            id=str(uuid.uuid4()),
            room_id=room_id,
            guest=guest,
            idempotency_key=idempotency_key,
        )
        self._by_id[reservation.id] = reservation
        return reservation

    def get(self, reservation_id: str) -> Reservation | None:
        return self._by_id.get(reservation_id)

    def list(self) -> list[Reservation]:
        return list(self._by_id.values())

    def count(self) -> int:
        return len(self._by_id)
