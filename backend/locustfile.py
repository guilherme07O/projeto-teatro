import os

from locust import HttpUser, between, task

# Assento usado na demonstração (padrão: 1). Defina SEAT_ID para testar outro.
SEAT_ID = int(os.getenv("SEAT_ID", "1"))

# Códigos que representam o comportamento correto do sistema:
# 201 = a única requisição que venceu; 409 = todas as demais (assento já reservado).
EXPECTED_STATUS = (201, 409)


class SeatUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def reserve_same_seat(self):
        # Demonstração: 100 usuários disputando o mesmo assento.
        # Execute com: locust -f locustfile.py --host http://localhost:8000 -u 100 -r 100
        # Resultado esperado: 1 resposta 201 e as demais 409 Conflict.
        with self.client.post(
            "/reserve",
            json={"seat_id": SEAT_ID, "user_id": f"user-{os.getpid()}-{id(self)}"},
            name=f"/reserve (assento {SEAT_ID})",
            catch_response=True,
        ) as response:
            # 409 é o resultado esperado para quem perde a disputa: conta como
            # sucesso para o relatório não ficar vermelho por um comportamento correto.
            if response.status_code in EXPECTED_STATUS:
                response.success()
            else:
                response.failure(
                    f"status inesperado {response.status_code}: {response.text[:120]}"
                )
