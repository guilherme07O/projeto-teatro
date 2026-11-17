from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine, SessionLocal
from .dependencies import get_reservation_service, get_seat_service
from .exceptions import ConflictError, ForbiddenError, NotFoundError
from .expiration import LazyReservationExpirationPolicy
from .repositories import SqlAlchemyReservationRepository, SqlAlchemySeatRepository
from .schemas import PayRequest, ReservationOut, ReserveRequest, SeatOut
from .services import ReservationService, SeatService


def seed_seats(db=None, total: int = 300):
    close = False
    if db is None:
        db = SessionLocal()
        close = True
    try:
        service = SeatService(
            seats=SqlAlchemySeatRepository(db),
            reservations=SqlAlchemyReservationRepository(db),
            expiration=LazyReservationExpirationPolicy(),
            db=db,
        )
        service.seed_if_empty(total=total)
    finally:
        if close:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_seats(total=300)
    yield


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(title="Venda de Ingressos - Assento Marcado", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _handle_domain_error(err: Exception):
    if isinstance(err, NotFoundError):
        raise HTTPException(status_code=404, detail=str(err))
    if isinstance(err, ConflictError):
        raise HTTPException(status_code=409, detail=str(err))
    if isinstance(err, ForbiddenError):
        raise HTTPException(status_code=403, detail=str(err))
    raise err


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/seats", response_model=list[SeatOut])
def list_seats(service: SeatService = Depends(get_seat_service)):
    return service.list_seats()


@app.post("/reserve", response_model=ReservationOut, status_code=201)
def reserve(req: ReserveRequest, service: ReservationService = Depends(get_reservation_service)):
    try:
        return service.reserve(seat_id=req.seat_id, user_id=req.user_id)
    except Exception as err:
        _handle_domain_error(err)


@app.post("/pay", response_model=ReservationOut)
def pay(req: PayRequest, service: ReservationService = Depends(get_reservation_service)):
    try:
        return service.pay(reservation_id=req.reservation_id, user_id=req.user_id)
    except Exception as err:
        _handle_domain_error(err)
