"""Booking handler with a deliberate idempotency bug for demos."""

from __future__ import annotations

from booking.store import Reservation, ReservationStore


class BookingService:
    """Creates reservations. Retries with the same key currently duplicate."""

    def __init__(self, store: ReservationStore | None = None) -> None:
        self._store = store or ReservationStore()

    def create_reservation(
        self,
        room_id: str,
        guest: str,
        *,
        idempotency_key: str | None = None,
    ) -> Reservation:
        """Create a reservation for a room and guest.

        BUG: ``idempotency_key`` is accepted but not consulted, so client retries
        insert a second reservation instead of returning the original.
        """
        # Intentionally ignore idempotency_key so RepoPilot has a clear defect
        # to investigate and patch in later iterations.
        return self._store.add(room_id=room_id, guest=guest, idempotency_key=idempotency_key)

    @property
    def store(self) -> ReservationStore:
        return self._store
