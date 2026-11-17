from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .models import Seat, Reservation


class SqlAlchemySeatRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all_ordered(self):
        return self.db.execute(select(Seat).order_by(Seat.id)).scalars().all()

    def get_by_id_for_update(self, seat_id: int):
        return self.db.execute(
            select(Seat).where(Seat.id == seat_id).with_for_update()
        ).scalar_one_or_none()

    def count(self) -> int:
        return int(self.db.execute(select(func.count()).select_from(Seat)).scalar_one())

    def add_many(self, seats):
        self.db.add_all(list(seats))


class SqlAlchemyReservationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_for_seat(self, seat_id: int, for_update: bool = False):
        stmt = select(Reservation).where(
            Reservation.seat_id == seat_id,
            Reservation.status.in_(["reserved", "paid"]),
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.execute(stmt).scalars().first()

    def get_by_id_for_update(self, reservation_id: int):
        return self.db.execute(
            select(Reservation).where(Reservation.id == reservation_id).with_for_update()
        ).scalar_one_or_none()

    def add(self, reservation: Reservation):
        self.db.add(reservation)