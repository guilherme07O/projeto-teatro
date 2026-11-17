# AGENTS.md — Regras e decisões de engenharia

## Objetivo do projeto

Implementar a venda de ingressos com assento marcado (300 assentos), garantindo que dois usuários nunca comprem o mesmo assento e que reservas expirem em 10 minutos sem um processo que verifica o banco a cada segundo.

## Regras aplicadas

- **Backend:** FastAPI + SQLAlchemy (bibliotecas vistas/compatíveis com o escopo da disciplina).
- **Frontend:** React (Vite) para mapa de assentos e interação de reserva/pagamento.
- **Banco:** MySQL 8 via Docker Compose.
- **Concorrência:** transações com bloqueio de linha (`SELECT ... FOR UPDATE`) no assento/reserva ativa durante a tentativa de reserva.
- **Integridade:** `UNIQUE` sobre a coluna gerada `active_seat_id` (preenchida só em `reserved`/`paid`), impedindo múltiplas reservas ativas do mesmo assento sem impedir a reutilização após expiração. Conflito retorna `409 Conflict`.
- **Expiração:** campo `expires_at` + verificação preguiçosa (lazy) em leituras/operações; sem job de varredura a cada segundo.
- **Testes:** `pytest` cobrindo a regra central (conflito de reserva, pagamento, expiração, reutilização) e um teste de concorrência real no MySQL (100 requisições simultâneas).
- **Carga/demonstração:** `locustfile.py` e `demo_concurrency.py` para simular 100 requisições simultâneas no mesmo assento.

## Estrutura

- `backend/app/`: API, modelos, acesso a dados e regras de negócio.
  - `main.py` (rotas), `services.py` (casos de uso), `repositories.py` (dados),
    `expiration.py` (política), `interfaces.py` (contratos), `dependencies.py` (injeção),
    `schemas.py` (DTOs), `exceptions.py` (erros de domínio), `timeutils.py` (UTC).
- `backend/tests/`: testes automatizados com pytest.
- `backend/demo_concurrency.py`: demonstração das 100 requisições simultâneas.
- `backend/locustfile.py`: cenário de carga para a demonstração.
- `frontend/`: interface React com mapa de assentos.
- `docs/`: decisões arquiteturais (ADR), especificação da API, roteiro da apresentação, checklist operacional (`checklist-apresentacao.md`) e o roteiro completo para 5 apresentadores (`roteiro-apresentacao-5-pessoas.pdf`).

## Convenções

- Mensagens de erro de conflito de assento retornam HTTP `409`.
- Estados de reserva: `reserved`, `paid`, `expired` (e suporte a evolução para `cancelled`).
- Tempo de reserva configurável por ambiente (`RESERVATION_MINUTES`, padrão 10).
- Datas trafegam em UTC (`+00:00`) e são convertidas no navegador.
- Configuração local via `backend/.env` (modelo em `backend/.env.example`); segredos e `.env` não vão para o Git.
- Código e documentação em pt-BR quando voltados ao usuário/entrega acadêmica.

## Comandos úteis

```bash
docker compose up -d                     # banco
pytest -q                                # testes (SQLite, 6 passed + 1 skipped)
TEST_DATABASE_URL="mysql+pymysql://app:app@localhost:3306/teatro_test" pytest -q   # 7 passed (MySQL, concorrência real)
python demo_concurrency.py               # demo: 100 requisições simultâneas
locust -f locustfile.py -u 100 -r 100    # demo alternativa
```
