from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from .timeutils import as_utc


class ReserveRequest(BaseModel):
    seat_id: int
    user_id: str


class PayRequest(BaseModel):
    reservation_id: int
    user_id: str


class SeatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    status: str  # available | reserved | paid
    reservation_id: int | None = None
    expires_at: datetime | None = None

    @field_serializer("expires_at")
    def _serialize_expires_at(self, value: datetime | None):
        # Datas são gravadas em UTC (naive); marcamos como UTC para o navegador
        # converter corretamente para o fuso local do usuário.
        return as_utc(value)


class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    seat_id: int
    user_id: str
    status: str
    expires_at: datetime | None
    created_at: datetime

    @field_serializer("expires_at", "created_at")
    def _serialize_datetimes(self, value: datetime | None):
        return as_utc(value)
