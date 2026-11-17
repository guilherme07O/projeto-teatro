"""Teste da regra central sob concorrência real.

Só roda no MySQL: o SQLite não implementa ``SELECT ... FOR UPDATE``, então o
teste passaria sem provar o bloqueio de linha. Rode com:

    $env:TEST_DATABASE_URL="mysql+pymysql://app:app@localhost:3307/teatro_test"
    pytest -q
"""

from __future__ import annotations

import asyncio
import collections
import os

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_DATABASE_URL", "sqlite").startswith("sqlite"),
    reason="Concorrência real exige MySQL (o SQLite ignora SELECT ... FOR UPDATE).",
)


def test_100_requisicoes_simultaneas_apenas_uma_vence(client):
    from app import main as main_module

    async def scenario():
        transport = httpx.ASGITransport(app=main_module.app)
        limits = httpx.Limits(max_connections=120, max_keepalive_connections=120)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            timeout=60,
            limits=limits,
        ) as api:
            gate = asyncio.Event()

            async def fire(index: int):
                await gate.wait()
                response = await api.post(
                    "/reserve",
                    json={"seat_id": 1, "user_id": f"user-{index}"},
                )
                return response.status_code

            tasks = [asyncio.create_task(fire(index)) for index in range(100)]
            # Pequena pausa para que todas as tasks fiquem prontas antes do disparo.
            await asyncio.sleep(0.2)
            gate.set()
            return await asyncio.gather(*tasks)

    codes = collections.Counter(asyncio.run(scenario()))

    assert codes[201] == 1, f"esperava exatamente 1 sucesso, obtive: {dict(codes)}"
    assert codes[409] == 99, f"esperava 99 conflitos, obtive: {dict(codes)}"
