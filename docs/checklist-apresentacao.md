# Checklist da apresentação

Apresentação no **notebook da equipe**, com o MySQL rodando em Docker. Tempo sugerido: 10–15 min. O roteiro do que falar está em [`apresentacao.md`](apresentacao.md); aqui é só a parte operacional.

---

## Antes de sair de casa

- [ ] **Docker Desktop** abre sem pedir atualização e o ícone da baleia fica parado (engine pronta).
- [ ] **Imagem do MySQL baixada** (rode uma vez com internet):
      ```bash
      docker compose pull
      ```
- [ ] **`node_modules` instalado** (`cd frontend && npm install`), para o frontend não depender de internet.
- [ ] **`.venv` criado e dependências instaladas** (`cd backend && pip install -r requirements.txt`).
- [ ] **Bateria/carregador** — a apresentação inteira usa Docker, backend e frontend ao mesmo tempo.
- [ ] **Rede**: a demo usa só `localhost`, não depende de internet. Só o `npm install`/`pip install` dependem.

## 10 minutos antes de apresentar

```bash
# na raiz do projeto
docker compose up -d
docker compose ps            # esperar "healthy"

# banco limpo: 300 assentos livres
docker compose down -v
docker compose up -d
docker compose ps
```

Depois, em dois terminais:

```bash
# Terminal 2 — backend
cd backend
source .venv/Scripts/activate        # Windows: .\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8000

# Terminal 3 — frontend
cd frontend
npm run dev
```

Confira antes de chamar o professor:

- [ ] `http://localhost:8000/health` → `{"status":"ok"}`
- [ ] `http://localhost:8000/docs` → Swagger abriu
- [ ] `http://localhost:5173` → mapa com **300 disponíveis / 0 reservados**
- [ ] Um clique num assento deixa ele laranja com horário de expiração (isso já mostra a reserva de 10 min)

> Se a porta 3306 estiver ocupada no notebook (MySQL nativo), use `.env` com `MYSQL_PORT=3307` **e** `backend/.env` apontando para 3307 — ver README, passo 1.

---

## Ordem da demonstração

| # | Ação | Como | O que mostrar |
|---|---|---|---|
| 1 | Mapa de assentos | abrir `localhost:5173` | 300 assentos, contadores |
| 2 | Reserva | clicar em um assento verde | fica laranja + horário de expiração (UTC convertido no navegador) |
| 3 | Conflito | tentar o mesmo assento com outro `user_id` | `409 Conflict` |
| 4 | Pagamento | clicar de novo no assento reservado (mesmo usuário) | fica azul (`paid`) e continua indisponível |
| 5 | **100 simultâneas** | `python demo_concurrency.py --requests 100` | `201: 1` e `409: 99` |
| 6 | Carga (Locust) | `locust -f locustfile.py --host http://localhost:8000 -u 100 -r 100` | gráfico de requisições, maioria 409 |
| 7 | Testes | `pytest -q` e o modo MySQL | `6 passed, 1 skipped` e `7 passed` |

### Comandos dos passos 5–7

```bash
cd backend

# 5) demonstração exigida: 100 requisições no mesmo instante
python demo_concurrency.py --requests 100

# 6) Locust (abrir http://localhost:8089 e clicar em Start)
locust -f locustfile.py --host http://localhost:8000 -u 100 -r 100

# 7) testes
pytest -q
# Windows (PowerShell):
$env:TEST_DATABASE_URL="mysql+pymysql://app:app@localhost:3306/teatro_test"
pytest -q        # 7 passed
```

> A demo do passo 5 reserva um assento. Se for rodar o Locust **depois**, use outro assento: `SEAT_ID=2 locust ...`, ou recrie o banco.

---

## Plano B

| Problema | O que fazer |
|---|---|
| Docker Desktop não abre | Reiniciar o Windows e abrir o Docker Desktop antes de qualquer coisa. **Sempre** validar 10 min antes. |
| `docker: command not found` | Abrir um terminal **novo** (o PATH só atualiza em sessões novas). |
| `error getting credentials` | Docker Desktop fechado; abrir e repetir. |
| `ports are not available` | Outro MySQL/processo na porta. `.env` com `MYSQL_PORT=3307` + `backend/.env` na 3307. |
| Backend: `Can't connect to MySQL` | Banco ainda `starting`: `docker compose ps`, esperar `healthy`, subir o backend de novo. |
| Assento já reservado na demo | `docker compose down -v && docker compose up -d` (e subir o backend de novo). |
| Frontend não carrega | `cd frontend && npm install && npm run dev`; conferir que o backend está na 8000. |
| Porta 8000 presa por processo antigo | `Get-NetTCPConnection -LocalPort 8000 -State Listen \| ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }` |
| Sem internet | Tudo funciona (imagem já baixada, `node_modules` e `.venv` prontos). Só não rode `docker compose pull`. |
| Notebook da Unirios | Levar a pasta do projeto + Docker instalado; avisar o professor com antecedência (o enunciado pede). |

---

## Perguntas que podem aparecer

Estão respondidas em [`apresentacao.md`](apresentacao.md), seção 6: por que não Redis, por que expiração preguiçosa, por que `UNIQUE` em coluna gerada, qual o gargalo.

## Números para citar de memória

- 300 assentos; reserva de **10 minutos**.
- 100 requisições simultâneas → **1×201** e **99×409**.
- Testes: **7 passed** no MySQL (inclui as 100 simultâneas) e **6 passed + 1 skipped** no SQLite.
