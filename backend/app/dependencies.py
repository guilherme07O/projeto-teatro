from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from .database import get_db
from .repositories import SqlAlchemySeatRepository, SqlAlchemyReservationRepository
from .expiration import LazyReservationExpirationPolicy
from .services import SeatService, ReservationService


def get_expiration_policy() -> LazyReservationExpirationPolicy:
    return LazyReservationExpirationPolicy()


def get_seat_service(db: Session = Depends(get_db)) -> SeatService:
    return SeatService(
        seats=SqlAlchemySeatRepository(db),
        reservations=SqlAlchemyReservationRepository(db),
        expiration=get_expiration_policy(),
        db=db,
    )


def get_reservation_service(db: Session = Depends(get_db)) -> ReservationService:
    return ReservationService(
        seats=SqlAlchemySeatRepository(db),
        reservations=SqlAlchemyReservationRepository(db),
        expiration=get_expiration_policy(),
        db=db,
    )