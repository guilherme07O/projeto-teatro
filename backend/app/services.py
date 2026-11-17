from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .exceptions import ConflictError, DomainError, ForbiddenError, NotFoundError
from .interfaces import ExpirationPolicy, ReservationRepository, SeatRepository
from .models import Reservation, Seat
from .timeutils import utcnow


class SeatService:
    def __init__(self, seats: SeatRepository, reservations: ReservationRepository, expiration: ExpirationPolicy, db: Session):
        self.seats = seats
        self.reservations = reservations
        self.expiration = expiration
        self.db = db

    def seed_if_empty(self, total: int = 300) -> None:
        if self.seats.count() > 0:
            return
        self.seats.add_many([Seat(label=f"A{i}") for i in range(1, total + 1)])
        self.db.commit()

    def list_seats(self):
        now = utcnow()
        result = []
        for seat in self.seats.list_all_ordered():
            active = self.reservations.get_active_for_seat(seat.id, for_update=False)
            if active:
                self.expiration.expire_if_needed(active, now)
                if active.status == "expired":
                    active = None
            if not active:
                status = "available"
                reservation_id = None
                expires_at = None
            elif active.status == "paid":
                status = "paid"
                reservation_id = active.id
                expires_at = None
            else:
                status = "reserved"
                reservation_id = active.id
                expires_at = active.expires_at
            result.append({
                "id": seat.id,
                "label": seat.label,
                "status": status,
                "reservation_id": reservation_id,
                "expires_at": expires_at,
            })
        self.db.commit()
        return result


class ReservationService:
    def __init__(self, seats: SeatRepository, reservations: ReservationRepository, expiration: ExpirationPolicy, db: Session):
        self.seats = seats
        self.reservations = reservations
        self.expiration = expiration
        self.db = db

    def reserve(self, seat_id: int, user_id: str) -> Reservation:
        now = utcnow()
        try:
            # 1) Bloqueia a linha do assento: serializa concorrentes do MESMO assento.
            seat = self.seats.get_by_id_for_update(seat_id)
            if not seat:
                raise NotFoundError("Assento não encontrado")

            # 2) Verifica a reserva ativa (também bloqueada, quando existir).
            active = self.reservations.get_active_for_seat(seat_id, for_update=True)
            if active:
                # Expiração preguiçosa: quem encontra a reserva vencida a encerra.
                if not self.expiration.expire_if_needed(active, now):
                    raise ConflictError("Assento indisponível")
                # Libera a UNIQUE (active_seat_id) ANTES de inserir a nova reserva.
                self.db.flush()

            reservation = Reservation(
                seat_id=seat_id,
                user_id=user_id,
                status="reserved",
                expires_at=self.expiration.expires_at(now),
                created_at=now,
            )
            self.reservations.add(reservation)
            self.db.commit()
            self.db.refresh(reservation)
            return reservation
        except DomainError:
            self.db.rollback()
            raise
        except IntegrityError:
            # Barreira final: duas transações passaram pela verificação e o banco
            # recusou a segunda reserva ativa para o mesmo assento.
            self.db.rollback()
            raise ConflictError("Assento indisponível")
        except Exception:
            self.db.rollback()
            raise

    def pay(self, reservation_id: int, user_id: str) -> Reservation:
        now = utcnow()
        try:
            reservation = self.reservations.get_by_id_for_update(reservation_id)
            if not reservation:
                raise NotFoundError("Reserva não encontrada")
            if reservation.user_id != user_id:
                raise ForbiddenError("Reserva não pertence ao usuário")
            if reservation.status == "paid":
                self.db.commit()
                return reservation
            if reservation.status != "reserved":
                raise ConflictError("Reserva não está ativa")
            if self.expiration.expire_if_needed(reservation, now):
                self.db.commit()
                raise ConflictError("Reserva expirada")

            reservation.status = "paid"
            reservation.expires_at = None
            self.db.commit()
            self.db.refresh(reservation)
            return reservation
        except DomainError:
            self.db.rollback()
            raise
        except Exception:
            self.db.rollback()
            raise
