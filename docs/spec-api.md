# Especificação da API — Venda de Ingressos com Assento Marcado

Base local: `http://localhost:8000` · Documentação interativa: `/docs`

## Modelo de estados da reserva

```
                 POST /pay (mesmo usuário)
   reserved ────────────────────────────────► paid
      │                                        │
      │ expires_at <= agora (lazy)             │ (estado final)
      ▼                                        ▼
   expired ─────► o assento volta a ficar disponível
```

| Status | Significado | Ocupa o assento? |
|---|---|---|
| `reserved` | Reserva ativa aguardando pagamento (10 min) | Sim |
| `paid` | Pagamento confirmado | Sim (definitivo) |
| `expired` | Reserva vencida sem pagamento | Não |
| `cancelled` | Reservado para evolução futura | Não |

Regra de integridade: no máximo **uma** reserva com status `reserved` ou `paid` por assento. Implementada pela coluna gerada `active_seat_id` + `UNIQUE`, além do bloqueio de linha na reserva.

## `GET /health`

Verificação simples de disponibilidade.

**200**
```json
{ "status": "ok" }
```

## `GET /seats`

Lista os assentos com o estado consolidado (aplica expiração preguiçosa).

**200**
```json
[
  {
    "id": 1,
    "label": "A1",
    "status": "available",
    "reservation_id": null,
    "expires_at": null
  },
  {
    "id": 2,
    "label": "A2",
    "status": "reserved",
    "reservation_id": 15,
    "expires_at": "2026-11-17T18:42:10+00:00"
  }
]
```

`status`: `available` | `reserved` | `paid`. As datas são sempre UTC (sufixo `+00:00`), para o navegador converter ao fuso local.

## `POST /reserve`

Reserva um assento por 10 minutos. Executa em transação com `SELECT ... FOR UPDATE` na linha do assento.

**Requisição**
```json
{ "seat_id": 1, "user_id": "user-123" }
```

**201 Created**
```json
{
  "id": 16,
  "seat_id": 1,
  "user_id": "user-123",
  "status": "reserved",
  "expires_at": "2026-11-17T18:42:10+00:00",
  "created_at": "2026-11-17T18:32:10+00:00"
}
```

| Código | Situação |
|---|---|
| `201` | Reserva criada (ou assento liberado por expiração) |
| `404` | Assento inexistente |
| `409` | Assento indisponível (reservado ou pago) |
| `422` | Corpo inválido |

## `POST /pay`

Confirma o pagamento simulado da reserva do próprio usuário.

**Requisição**
```json
{ "reservation_id": 16, "user_id": "user-123" }
```

**200 OK**
```json
{
  "id": 16,
  "seat_id": 1,
  "user_id": "user-123",
  "status": "paid",
  "expires_at": null,
  "created_at": "2026-11-17T18:32:10+00:00"
}
```

| Código | Situação |
|---|---|
| `200` | Pagamento confirmado (idempotente se já estava `paid`) |
| `403` | Reserva pertence a outro usuário |
| `404` | Reserva inexistente |
| `409` | Reserva expirada ou em estado que não permite pagamento |

## Garantias de concorrência

1. `SELECT ... FOR UPDATE` na linha de `seats` serializa tentativas do mesmo assento.
2. A reserva ativa também é bloqueada quando existe.
3. `UNIQUE (active_seat_id)` impede, no banco, duas reservas ativas para o mesmo assento.
4. Violação de integridade é convertida em `409 Conflict`, nunca em erro 500.

## Expiração

- `RESERVATION_MINUTES` (padrão `10`) define a duração.
- Nenhum processo periódico consulta o banco.
- `GET /seats` e as operações de reserva/pagamento encerram reservas com `expires_at <= agora`.
- Enquanto ninguém acessar, a linha permanece `reserved` no banco, mas é considerada livre na próxima leitura.
