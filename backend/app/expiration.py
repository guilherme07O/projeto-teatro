from __future__ import annotations

import os
from datetime import datetime, timedelta
from .models import Reservation


class LazyReservationExpirationPolicy:
    """Expiração preguiçosa: avalia expires_at no momento de uso, sem polling periódico."""

    def __init__(self, reservation_minutes: int | None = None):
        self.reservation_minutes = reservation_minutes if reservation_minutes is not None else int(os.getenv("RESERVATION_MINUTES", "10"))

    def is_expired(self, reservation: Reservation, now: datetime) -> bool:
        return bool(
            reservation.status == "reserved"
            and reservation.expires_at
            and reservation.expires_at <= now
        )

    def expires_at(self, now: datetime) -> datetime:
        return now + timedelta(minutes=self.reservation_minutes)

    def expire_if_needed(self, reservation: Reservation, now: datetime) -> bool:
        if self.is_expired(reservation, now):
            reservation.status = "expired"
            return True
        return False