# Roteiro da apresentação

> **Versão completa (recomendada para a equipe de 5):** [`roteiro-apresentacao-5-pessoas.pdf`](roteiro-apresentacao-5-pessoas.pdf) — 40 páginas, falas cronometradas por integrante, arquitetura, comparação de alternativas, padrões de projeto/SOLID, dossiê de cada arquivo, runbook da demo e 18 perguntas da banca com respostas. Este arquivo aqui é o resumo de 1 página.

Duração sugerida: **10 a 15 minutos**. A nota da apresentação e o conhecimento demonstrado valem 70% da avaliação.

## 1. Contexto e problema (1–2 min)

- Teatro com **300 assentos**; muitos usuários tentam o **mesmo assento no mesmo segundo**.
- Duas perguntas centrais:
  1. Como garantir que dois usuários nunca comprem o mesmo assento?
  2. Como a reserva expira em 10 minutos **sem** um processo verificando o banco a cada segundo?

## 2. Arquitetura (2 min)

Mostre a estrutura e explique a separação:

- `main.py` → rotas finas (HTTP)
- `services.py` → regras de negócio e transação
- `repositories.py` → acesso a dados com `SELECT ... FOR UPDATE`
- `expiration.py` → política de expiração (Strategy)
- `interfaces.py` + `dependencies.py` → contratos e injeção de dependência
- `schemas.py` / `exceptions.py` → DTOs e erros de domínio

Frase de efeito: *"a regra de negócio não conhece HTTP nem SQL."*

## 3. Como a exclusividade é garantida (3 min)

Explique em camadas:

1. **Bloqueio pessimista**: `SELECT ... FOR UPDATE` na linha do assento serializa concorrentes do mesmo assento.
2. **Restrição no banco**: `UNIQUE` sobre `active_seat_id` (coluna gerada que só tem valor em `reserved`/`paid`).
3. **Tratamento**: `IntegrityError` → `409 Conflict`.

Ponto importante para a pergunta central: *mesmo que a aplicação falhe, o banco não permite duas reservas ativas.*

## 4. Expiração sem polling (2 min)

- `expires_at` gravado na reserva.
- Expiração **preguiçosa**: aplicada quando o assento é lido/reservado/pago.
- Não existe cron, worker ou `sleep` consultando o banco.
- Trade-off: a linha só muda para `expired` no próximo acesso — e isso é suficiente para o requisito.

## 5. Demonstração ao vivo (3–4 min)

### Preparação (antes de entrar na sala)

```bash
docker compose up -d
cd backend
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm run dev
```

Deixe o banco limpo:

```bash
docker compose down -v
docker compose up -d
```

### Ordem da demo

1. Abra o mapa em `http://localhost:5173`, reserve um assento e mostre o horário de expiração.
2. Tente reservar o mesmo assento em outra janela (ou outro `user_id`) → **409**.
3. Pague a reserva e mostre o assento como **pago**.
4. Rode a demonstração exigida:

```bash
cd backend
python demo_concurrency.py --requests 100
```

Resultado esperado: `201: 1` e `409: 99`.

5. (Opcional) Mostre o Locust com 100 usuários.
6. Mostre os testes:

```bash
$env:TEST_DATABASE_URL="mysql+pymysql://app:app@localhost:3306/teatro_test"
pytest -q
```

Resultado esperado: `7 passed`.

### Plano B

- **Sem Docker na máquina**: use MySQL local e ajuste `DATABASE_URL`; ou rode os testes em SQLite (o teste de concorrência é pulado com justificativa).
- **Backend caiu**: o script mostra a mensagem de conexão recusada; reinicie o `uvicorn` e repita.
- **Assento já reservado**: `--seat <id>` escolhe outro, ou recrie o banco.

## 6. Perguntas prováveis

**"Por que não usar Redis?"**
Seria válido (lock com TTL), mas adiciona um componente e um segundo estado a reconciliar. O banco relacional já é a fonte de verdade e resolve com lock + constraint.

**"Por que a expiração é preguiçosa?"**
Porque o requisito proíbe um processo verificando o banco a cada segundo. O estado só importa quando alguém tenta usar o assento — e é exatamente aí que a expiração é aplicada.

**"E se ninguém acessar o assento?"**
Ele continua `reserved` no banco, mas a próxima leitura o considera livre. Nenhuma venda é afetada.

**"Por que `UNIQUE` em coluna gerada e não em `(seat_id, status)`?"**
Porque `(seat_id, status)` impediria o assento de expirar duas vezes (duas linhas `expired`). A coluna gerada vale `NULL` quando a reserva não está ativa, então a unicidade só se aplica a `reserved`/`paid`.

**"Qual o gargalo?"**
Contenção no mesmo assento: as requisições esperam o lock. É o trade-off por consistência forte.

## 7. Encerramento (1 min)

Retome as duas perguntas e responda em uma frase cada, citando os arquivos que implementam cada garantia.
