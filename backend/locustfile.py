import os

from locust import HttpUser, between, task

SEAT_ID = int(os.getenv("SEAT_ID", "1"))

EXPECTED_STATUS = (201, 409)


class SeatUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def reserve_same_seat(self):
        with self.client.post(
            "/reserve",
            json={"seat_id": SEAT_ID, "user_id": f"user-{os.getpid()}-{id(self)}"},
            name=f"/reserve (assento {SEAT_ID})",
            catch_response=True,
        ) as response:
            if response.status_code in EXPECTED_STATUS:
                response.success()
            else:
                response.failure(
                    f"status inesperado {response.status_code}: {response.text[:120]}"
                )
