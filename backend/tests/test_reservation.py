from datetime import timedelta

from app import database
from app.models import Reservation
from app.timeutils import utcnow


def _expire(reservation_id: int) -> None:
    """Força o vencimento da reserva (a expiração real é aplicada de forma lazy)."""
    db = database.SessionLocal()
    try:
        reservation = db.get(Reservation, reservation_id)
        reservation.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()


def test_reserve_seat_success(client):
    resp = client.post("/reserve", json={"seat_id": 1, "user_id": "user-a"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["seat_id"] == 1
    assert data["user_id"] == "user-a"
    assert data["status"] == "reserved"


def test_cannot_reserve_same_seat_twice(client):
    r1 = client.post("/reserve", json={"seat_id": 1, "user_id": "user-a"})
    assert r1.status_code == 201

    r2 = client.post("/reserve", json={"seat_id": 1, "user_id": "user-b"})
    assert r2.status_code == 409


def test_pay_confirms_reservation(client):
    r = client.post("/reserve", json={"seat_id": 2, "user_id": "user-a"})
    assert r.status_code == 201
    reservation_id = r.json()["id"]

    p = client.post("/pay", json={"reservation_id": reservation_id, "user_id": "user-a"})
    assert p.status_code == 200
    assert p.json()["status"] == "paid"

    # assento pago continua indisponível
    r2 = client.post("/reserve", json={"seat_id": 2, "user_id": "user-b"})
    assert r2.status_code == 409


def test_pay_rejects_another_user(client):
    r = client.post("/reserve", json={"seat_id": 4, "user_id": "user-a"})
    reservation_id = r.json()["id"]

    p = client.post("/pay", json={"reservation_id": reservation_id, "user_id": "user-b"})
    assert p.status_code == 403


def test_expired_reservation_becomes_available(client):
    # cria a reserva
    r = client.post("/reserve", json={"seat_id": 3, "user_id": "user-a"})
    assert r.status_code == 201
    _expire(r.json()["id"])

    # o próximo acesso normaliza a reserva vencida e libera o assento
    seats = {seat["id"]: seat for seat in client.get("/seats").json()}
    assert seats[3]["status"] == "available"

    r2 = client.post("/reserve", json={"seat_id": 3, "user_id": "user-b"})
    assert r2.status_code == 201
    assert r2.json()["user_id"] == "user-b"


def test_seat_can_be_reused_after_repeated_expirations(client):
    """Regressão: o assento deve voltar a ficar livre em TODO ciclo de expiração.

    A restrição UNIQUE era (seat_id, status) e travava o assento no segundo
    vencimento, pois duas linhas 'expired' colidiam.
    """
    user_ids = ["user-a", "user-b", "user-c"]

    for attempt, user_id in enumerate(user_ids, start=1):
        resp = client.post("/reserve", json={"seat_id": 5, "user_id": user_id})
        assert resp.status_code == 201, f"reserva #{attempt} deveria funcionar"
        _expire(resp.json()["id"])

    # após três ciclos, o assento continua disponível
    seats = {seat["id"]: seat for seat in client.get("/seats").json()}
    assert seats[5]["status"] == "available"

    final = client.post("/reserve", json={"seat_id": 5, "user_id": "user-d"})
    assert final.status_code == 201
