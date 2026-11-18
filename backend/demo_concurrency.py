"""Demonstração do requisito: 100 requisições simultâneas para o mesmo assento.

Com o backend rodando, execute:

    python demo_concurrency.py --host http://localhost:8000 --requests 100

Resultado esperado: exatamente UMA resposta ``201 Created`` e todas as demais
``409 Conflict``.

O script escolhe automaticamente o primeiro assento disponível. Se o assento
estiver reservado de uma execução anterior, recrie o banco (``docker compose
down -v`` e suba o backend de novo) ou use ``--seat`` com outro assento livre.
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import sys

import httpx


async def _fire(client: httpx.AsyncClient, gate: asyncio.Event, seat_id: int, index: int):
    await gate.wait()
    try:
        response = await client.post(
            "/reserve",
            json={"seat_id": seat_id, "user_id": f"demo-{index}"},
        )
        return response.status_code
    except httpx.HTTPError as exc:
        return f"erro:{exc.__class__.__name__}"


async def run(host: str, seat_id: int | None, total: int, timeout: float) -> int:
    limits = httpx.Limits(
        max_connections=total + 10,
        max_keepalive_connections=total + 10,
    )
    async with httpx.AsyncClient(base_url=host, timeout=timeout, limits=limits) as client:
        seats = (await client.get("/seats")).json()

        if seat_id is None:
            free = [seat["id"] for seat in seats if seat["status"] == "available"]
            if not free:
                print("Nenhum assento disponível.")
                print("Recrie o banco (docker compose down -v) ou escolha outro assento com --seat.")
                return 2
            seat_id = free[0]
        else:
            current = next((seat for seat in seats if seat["id"] == seat_id), None)
            if current and current["status"] != "available":
                print(f"O assento {seat_id} não está disponível (status={current['status']}).")
                print("Escolha outro assento com --seat ou recrie o banco (docker compose down -v).")
                return 2

        gate = asyncio.Event()
        tasks = [
            asyncio.create_task(_fire(client, gate, seat_id, index))
            for index in range(total)
        ]
        await asyncio.sleep(0.2)
        gate.set()
        results = await asyncio.gather(*tasks)

    counter = collections.Counter(results)
    print(f"Assento: {seat_id} | requisições simultâneas: {total}")
    for code, count in sorted(counter.items(), key=lambda item: str(item[0])):
        print(f"  {code}: {count}")

    ok = counter.get(201) == 1 and counter.get(409) == total - 1
    print(
        "Resultado: OK — exatamente uma reserva venceu e as demais receberam 409."
        if ok
        else "Resultado: INESPERADO — confira se o backend está usando MySQL e o banco está limpo."
    )
    return 0 if ok else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dispara N requisições simultâneas de reserva para o mesmo assento."
    )
    parser.add_argument("--host", default="http://localhost:8000")
    parser.add_argument(
        "--seat",
        type=int,
        default=None,
        help="ID do assento (padrão: primeiro assento disponível)",
    )
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    if args.requests < 2:
        parser.error("--requests deve ser pelo menos 2")

    try:
        sys.exit(asyncio.run(run(args.host, args.seat, args.requests, args.timeout)))
    except httpx.HTTPError as exc:
        print(f"Não foi possível falar com {args.host}: {exc}")
        print("O backend está rodando? (uvicorn app.main:app --reload)")
        sys.exit(3)


if __name__ == "__main__":
    main()
