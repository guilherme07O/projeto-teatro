# Venda de Ingressos com Assento Marcado

Sistema de venda de ingressos para um teatro com **300 assentos**, com reserva temporária de **10 minutos** para pagamento simulado e garantia de que **dois usuários nunca compram o mesmo assento** — mesmo com 100 tentativas simultâneas.

**Stack:** FastAPI + SQLAlchemy (backend), React + Vite (frontend), MySQL 8.4 via Docker Compose, pytest e Locust.

---

## Estrutura do repositório

```
.
├── backend/
│   ├── app/
│   │   ├── main.py            # rotas HTTP, lifespan e mapeamento de erros
│   │   ├── services.py        # casos de uso (reserva, pagamento, listagem)
│   │   ├── repositories.py    # acesso a dados (Repository Pattern / FOR UPDATE)
│   │   ├── expiration.py      # política de expiração preguiçosa (Strategy)
│   │   ├── interfaces.py      # contratos (Protocol) para inversão de dependência
│   │   ├── dependencies.py    # composition root / injeção de dependências
│   │   ├── models.py          # modelo ORM (Seat, Reservation)
│   │   ├── schemas.py         # DTOs de entrada/saída da API
│   │   ├── exceptions.py      # erros de domínio
│   │   ├── database.py        # engine, sessão e carregamento do .env
│   │   └── timeutils.py       # utilitários de data/hora em UTC
│   ├── tests/                 # pytest (regra central + concorrência real)
│   ├── demo_concurrency.py    # demonstração determinística das 100 requisições
│   ├── locustfile.py          # teste de carga com Locust
│   ├── requirements.txt
│   └── .env.example
├── frontend/                  # React + Vite (mapa de assentos)
├── docker/mysql-init/         # cria o banco de testes (teatro_test)
├── docs/
│   ├── adr-001-concorrencia-e-expiracao.md
│   ├── spec-api.md
│   ├── apresentacao.md
│   ├── checklist-apresentacao.md
│   ├── roteiro-apresentacao-5-pessoas.pdf   # roteiro completo dividido em 5 falas
│   └── roteiro-apresentacao-5-pessoas.html  # mesma versão, para reimprimir no navegador
├── docker-compose.yml         # MySQL 8.4
├── AGENTS.md                  # regras e decisões de engenharia
└── README.md
```

## Pré-requisitos

- **Docker** com **Docker Compose** (usado para o MySQL)
- **Python 3.11+**
- **Node.js 18+** e **npm**

---

## Como executar

São três terminais: banco, backend e frontend.

### 1. Banco (MySQL via Docker Compose)

```bash
docker compose up -d
docker compose ps
```

Isso sobe o MySQL 8.4 em `localhost:3306`, com banco `teatro`, usuário `app` e senha `app`. Espere aparecer `healthy` na coluna `STATUS` (leva ~20 s).

> **Porta 3306 já ocupada?** Se você tem outro MySQL instalado na máquina, crie um `.env` na raiz com outra porta:
>
> ```bash
> echo "MYSQL_PORT=3307" > .env
> ```
>
> E ajuste a mesma porta em `backend/.env` (passo 2). O padrão do projeto continua sendo 3306.

### 2. Backend (FastAPI)

```bash
cp backend/.env.example backend/.env       # macOS / Linux
copy backend\.env.example backend\.env     # Windows (CMD / PowerShell)
```

O `backend/.env` já vem com `DATABASE_URL=mysql+pymysql://app:app@localhost:3306/teatro`. **Se você usou outra porta no passo 1, troque a porta nessa linha.** O arquivo é carregado automaticamente na subida da API.

**macOS / Linux:**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Windows (PowerShell):**

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Windows (CMD):**

```cmd
cd backend
py -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

> Se o PowerShell bloquear o `Activate.ps1` por política de scripts, não ative o ambiente — chame o Python diretamente:
>
> ```powershell
> .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
> ```

A API fica em `http://localhost:8000` (documentação interativa em `/docs`). Na inicialização, as tabelas são criadas e **300 assentos** são semeados automaticamente.

### 3. Frontend (React)

Em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

O frontend fica em `http://localhost:5173` e usa proxy `/api` para o backend em `localhost:8000`.

---

## Testes automatizados (pytest)

Cobrem a regra central: conflito de reserva, pagamento, expiração e reutilização do assento.

```bash
cd backend
source .venv/bin/activate      # Windows: .\.venv\Scripts\Activate.ps1
pytest -q
```

Por padrão os testes usam **SQLite em memória** (rápido e isolado): `6 passed, 1 skipped`.

### Modo MySQL (concorrência real)

O teste das 100 requisições simultâneas só roda no MySQL, porque o SQLite ignora `SELECT ... FOR UPDATE`.

Os testes **recriam as tabelas** e semeiam 10 assentos, por isso usam um banco separado (`teatro_test`), criado automaticamente pelo Compose. **Nunca aponte `TEST_DATABASE_URL` para o banco `teatro`** (ele tem os 300 assentos de desenvolvimento) — o `conftest.py` bloqueia isso com uma mensagem de erro.

```bash
# macOS / Linux
TEST_DATABASE_URL="mysql+pymysql://app:app@localhost:3306/teatro_test" pytest -q

# Windows (PowerShell)
$env:TEST_DATABASE_URL="mysql+pymysql://app:app@localhost:3306/teatro_test"
pytest -q
```

Resultado esperado: `7 passed`, incluindo `tests/test_concurrency.py`.

> Se você usa outra porta no passo 1, troque a porta na URL acima também.

---

## Demonstração: 100 requisições simultâneas para o mesmo assento

### Teste de carga com Locust (requisito do desafio)

```bash
cd backend
locust -f locustfile.py --host http://localhost:8000 -u 100 -r 100
```

Abra `http://localhost:8089` e inicie o teste. Também é possível rodar sem interface:

```bash
locust -f locustfile.py --host http://localhost:8000 -u 100 -r 100 --run-time 10s --headless
```

Defina `SEAT_ID` para testar outro assento (padrão: `1`).

### Demonstração determinística (as 100 exatamente juntas)

O Locust distribui requisições ao longo do tempo; para provar a exclusividade com **as 100 partindo no mesmo instante**, use o script:

```bash
cd backend
python demo_concurrency.py --host http://localhost:8000 --requests 100
```

Saída esperada:

```
Assento: 1 | requisições simultâneas: 100
  201: 1
  409: 99
Resultado: OK — exatamente uma reserva venceu e as demais receberam 409.
```

> Se o assento já estiver reservado de uma execução anterior, recrie o banco antes da demo:
>
> ```bash
> docker compose down -v
> docker compose up -d
> ```
>
> Ou escolha outro assento livre com `--seat <id>`.

Parar o banco: `docker compose down` (os dados ficam no volume). Para apagar os dados: `docker compose down -v`.

---

## Decisões da equipe (resumo)

- **Exclusividade do assento:** a reserva acontece em uma transação que bloqueia a linha do assento com `SELECT ... FOR UPDATE` antes de verificar/criar a reserva ativa. Tentativas concorrentes para o mesmo assento são serializadas.
- **Barreira adicional no banco:** coluna gerada `active_seat_id` (preenchida apenas quando o status é `reserved` ou `paid`) com `UNIQUE`. Se alguma corrida escapar do lock, o banco recusa a segunda reserva ativa e a API responde `409 Conflict`. Reservas `expired`/`cancelled` ficam com `NULL`, então **o assento volta a ficar livre em todo ciclo de expiração**.
- **Expiração sem polling:** cada reserva tem `expires_at` (10 minutos, configurável por `RESERVATION_MINUTES`). A expiração é **preguiçosa (lazy)**: aplicada sempre que o sistema lê ou opera a reserva. Não existe processo consultando o banco a cada segundo.
- **Pagamento simulado:** `POST /pay` confirma a reserva do próprio usuário (`403` caso contrário) e muda o status para `paid`.
- **Frontend:** mapa de 300 assentos, atualizado a cada 5 segundos, com reserva por clique e pagamento simulado.

## Resposta à pergunta central

- **Como garantir que dois usuários nunca comprem o mesmo assento?** Transação + `SELECT ... FOR UPDATE` na linha do assento (serializa concorrentes) somada a uma restrição `UNIQUE` sobre as reservas ativas como última barreira. O perdedor recebe `409 Conflict`.
- **Como a reserva expira sem verificar o banco a cada segundo?** Com `expires_at` e expiração preguiçosa: a validade é checada no momento de uso (listar assentos, reservar, pagar) e a reserva vencida é encerrada ali mesmo, liberando o assento.

Detalhes em [`AGENTS.md`](AGENTS.md), [`docs/adr-001-concorrencia-e-expiracao.md`](docs/adr-001-concorrencia-e-expiracao.md) e [`docs/spec-api.md`](docs/spec-api.md). O roteiro da apresentação está em [`docs/apresentacao.md`](docs/apresentacao.md) e a lista de verificação em [`docs/checklist-apresentacao.md`](docs/checklist-apresentacao.md).

### Roteiro da apresentação (equipe de 5)

O documento completo — falas cronometradas por integrante, arquitetura, comparação com as alternativas (lock no Redis e job de varredura), padrões de projeto/SOLID, dossiê dos 25 arquivos, runbook da demo e 18 perguntas da banca com respostas — está em:

- [`docs/roteiro-apresentacao-5-pessoas.pdf`](docs/roteiro-apresentacao-5-pessoas.pdf) (40 páginas)
- [`docs/roteiro-apresentacao-5-pessoas.html`](docs/roteiro-apresentacao-5-pessoas.html) (fonte para reimprimir: abrir no navegador e usar *Imprimir → Salvar como PDF*)

## Limitações conhecidas

- Não há migrations (Alembic): o schema é criado por `Base.metadata.create_all` na subida. Alterações de modelo exigem recriar o banco.
- Autenticação simplificada: o `user_id` é informado pelo cliente, sem login.
- Uma única instância de backend; a escalabilidade horizontal depende do banco como ponto de serialização.
