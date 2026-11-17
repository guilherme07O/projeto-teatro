from datetime import datetime

from sqlalchemy import Computed, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .timeutils import utcnow


class Seat(Base):
    __tablename__ = "seats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="seat")


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        # Garante no banco, no máximo, UMA reserva ativa (reserved/paid) por assento.
        # Coluna gerada: vale NULL quando a reserva está encerrada (expired/cancelled),
        # permitindo reutilizar o assento após a expiração quantas vezes for necessário.
        UniqueConstraint("active_seat_id", name="uq_seat_active_reservation"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # status: reserved | paid | expired | cancelled
    active_seat_id: Mapped[int | None] = mapped_column(
        Integer,
        Computed(
            "CASE WHEN status IN ('reserved', 'paid') THEN seat_id ELSE NULL END",
            persisted=True,
        ),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    seat: Mapped[Seat] = relationship(back_populates="reservations")
