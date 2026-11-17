# ADR 001 — Concorrência na reserva e expiração de assentos

## Contexto

Muitos usuários podem tentar reservar o mesmo assento simultaneamente. Além disso, uma reserva deve durar 10 minutos e expirar sem um processo que verifica o banco a cada segundo.

## Decisão

1. **Bloqueio pessimista por assento:** ao reservar, a aplicação inicia uma transação, executa `SELECT ... FOR UPDATE` no assento (e na reserva ativa, quando existente) para serializar concorrentes no mesmo recurso.
2. **Validação de disponibilidade:** após o lock, verifica-se se há reserva ativa (`reserved` não expirada ou `paid`). Se houver, retorna `409 Conflict`.
3. **Proteção adicional no banco:** coluna gerada `active_seat_id` que recebe o `seat_id` apenas quando o status é `reserved` ou `paid` (e `NULL` em `expired`/`cancelled`), com restrição `UNIQUE`. Violações de integridade são convertidas em `409 Conflict`.
4. **Expiração preguiçosa (lazy expiration):** cada reserva `reserved` possui `expires_at`. Nas operações de leitura/reserva/pagamento, se `expires_at <= agora`, o status é atualizado para `expired`. Não há worker/polling periódico de 1 em 1 segundo.
5. **Pagamento simulado:** `POST /pay` confirma a reserva do próprio usuário dentro de transação, marcando como `paid`.

### Correção: unicidade só para reservas ativas

A primeira versão usava `UNIQUE (seat_id, status)`. Isso impedia o assento de ser reutilizado após o **segundo** ciclo de expiração, porque uma segunda linha `expired` colidia com a primeira — na prática, o assento ficava indisponível para sempre depois de dois vencimentos.

A modelagem foi corrigida para `UNIQUE (active_seat_id)`, com a coluna gerada:

```sql
active_seat_id INT GENERATED ALWAYS AS (
  CASE WHEN status IN ('reserved', 'paid') THEN seat_id ELSE NULL END
) STORED
```

MySQL 8 e SQLite 3.31+ suportam essa construção, e o comportamento passou a ser coberto pelo teste `test_seat_can_be_reused_after_repeated_expirations`.

## Consequências

- **Positivas:** forte garantia contra dupla venda no mesmo assento; implementação simples sem scheduler frequente; comportamento correto mesmo sob carga; assento reutilizável indefinidamente após expirar.
- **Negativas:** contenção no mesmo assento (espera de lock) sob alta concorrência; reservas expiradas podem permanecer marcadas como `reserved` até o próximo acesso que as normalize (aceitável pelo requisito).

## Evidências

- `backend/tests/test_reservation.py`: regra central, pagamento, expiração e reutilização.
- `backend/tests/test_concurrency.py`: 100 requisições simultâneas no mesmo assento no MySQL → exatamente `1×201` e `99×409`.
- `backend/demo_concurrency.py`: mesma demonstração executável durante a apresentação.

## Resposta à pergunta central

- **Como garantir que dois usuários nunca comprem o mesmo assento?** Com transação + `SELECT ... FOR UPDATE` para serializar a decisão de reserva no banco e restrição de unicidade sobre as reservas ativas como barreira adicional, retornando `409` para os perdedores.
- **Como a reserva expira sem um processo que verifica o banco a cada segundo?** Armazenando `expires_at` e aplicando expiração preguiçosa: a validade é checada no momento de uso/leitura (e ao tentar reservar/pagar), liberando o assento sem varredura periódica contínua.
