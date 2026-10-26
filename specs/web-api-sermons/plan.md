# Plan: Rotas da API para pregações, tarefas e estado (SSE)

**Issue**: web-api-sermons
**Feature**: specs/web-api-sermons
**Data**: 2026-10-26

---

## Resumo

Routers FastAPI finos sobre a camada de serviço: pregações, tarefas, estado e eventos SSE
por polling do banco. Conexão SQLite por requisição, identidade e papel do item 19.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Contexto de código

| Situação | Path |
|---|---|
| Criar | `apps/api/src/wordcut_api/deps.py` — `home()` e `live_source()` (porta do YouTube), chamados na hora da requisição; sem `connection()` com `yield` (L1, L5) |
| Criar | `apps/api/src/wordcut_api/routes/sermons.py`, `routes/tasks.py`, `routes/status.py` — cada rota abre `with closing(db.connect(home))` no próprio corpo (L1) |
| Criar | `apps/api/src/wordcut_api/sse.py` — gerador assíncrono de eventos por polling de `service.tasks.show_task` em `run_in_threadpool`, com `asyncio.sleep`; `progress`/`done`/`failed` com o JSON de `show_task`; heartbeat `: ping`; intervalos em constantes do módulo (L6, L12) |
| Alterar | `apps/api/src/wordcut_api/app.py` — registra os routers; OpenAPI em `/api/docs` e `/api/openapi.json` só com `DevIdentification` (L8) |
| Alterar | `apps/api/src/wordcut_api/errors.py` — `RequestValidationError` → 400 `invalid_argument` sem eco; 404 do Starlette → `not_found` (L2) |
| Alterar | `apps/api/tests/conftest.py` — guarda autouse que troca `deps.live_source` por dublê que falha (L5) e fixtures de membro identificado |
| Criar | `apps/api/tests/test_sermons_routes.py`, `test_tasks_routes.py`, `test_sse.py` |
| Alterar | `docs/architecture/README.md` (§4, linha API; fluxo novo "Processar uma pregação pela web", L7), `CHANGELOG.md`, `docs/adr/0020-rotas-e-progresso-por-sse-na-api.md` com entrada no índice (L14); documento curto da API em `docs/api.md` (rotas, corpos, status, eventos; o cliente fecha o `EventSource` no `done`/`failed`, L13) |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Conexão (L1) | a rota abre `with closing(db.connect(home))` no próprio corpo; nenhuma `Depends` entrega conexão | ADR-0019: a dependência e a rota podem rodar em threads diferentes, e a conexão SQLite fica presa à sua |
| Tarefas | serviços existentes com `detach=True`; testes com `harmless_tasks` | ADR-0007/0013; nada pesado em teste |
| Corpo da tarefa lançada (L4) | 202 com `service.tasks.launched_task(row)` | Mesmo corpo da CLI sem `--wait` (docs/cli.md §6.2) |
| SSE (L6, L12) | `StreamingResponse` `text/event-stream` sobre gerador assíncrono (`asyncio.sleep`, `run_in_threadpool(show_task, …)`), polling do banco, encerra no estado final; `data` de todo evento = JSON de `show_task`; `progress` só quando muda `(progress, progress_message)`, como `wait_task`; heartbeat `: ping`; inexistente → 404 JSON antes do fluxo; `POLL_SECONDS` e `HEARTBEAT_SECONDS` em constantes do módulo | Funciona entre processos sem broker (§V); não prende thread do pool por cliente |
| Corpos de saída (L3) | os mesmos `dict` dos serviços, sem `needs_reprocess` no `PATCH` | Igual ao JSON da CLI (ADR-0004); a web deduz o aviso de `status == "processed"` |
| Corpos de entrada (L9) | `POST /api/sermons {"url"}`; `PATCH {"start","end"}` obrigatórios, número em segundos (estrito); `process {"force": false}` opcional; `suggest {"preset_id": null}` opcional | Mesmo que a CLI recebe (docs/cli.md §4.3, §7) |
| Filtros (L10) | `status` e `kind` tipados com `Literal` das escolhas de `SERMON_STATES`, `TASK_STATES` e `TASK_KINDS`; fora delas → 400 com `details.choices` | A CLI recusa as mesmas escolhas; o serviço não valida |
| Erro de validação (L2) | `RequestValidationError` → 400 `invalid_argument` com `details.argument` (e `choices` quando houver), sem `input` nem texto do pydantic; 404 do Starlette → `not_found` | FR-004, ADR-0015 |
| YouTube (L5) | rotas chamam `deps.live_source()` na hora; guarda autouse nos testes da API troca a porta por dublê que falha | Sem rede real (ADR-0017) |
| Download | `FileResponse` com `filename` legível | Mesmo nome do `sermon download` |
| Documentação da API (L8, L13) | `docs/api.md` curto + OpenAPI em `/api/docs` e `/api/openapi.json` só com `DevIdentification`; com Access, 404 | Contrato legível sem expor o esquema sem identidade |
| `status` com a trava ocupada (L11) | testes comparam sem `elapsed_seconds` | O campo depende do relógio |
| Arquitetura (L7, L14) | fluxo "Processar uma pregação pela web" em docs/architecture; ADR-0020 com entrada no índice | ADR aceita não se edita (CONTRIBUTING §3.1) |

Decisões L1–L14 tomadas pelo orquestrador a partir das recomendações do QA (qa.md, Plano de QA),
antes da Rodada 1.

---

## Ordem de implementação

- [x] **Passo 1 — Dependências e pregações** — `deps.py`, rotas de pregações (criar, listar, detalhar, delimitar, vídeo).
- [x] **Passo 2 — Tarefas pela API** — processar e sugerir (admin) com 202; `GET /api/tasks`, `/api/tasks/{id}`, `/api/status`.
- [x] **Passo 3 — SSE** — eventos de progresso e fim; desconexão não afeta a tarefa.
- [x] **Passo 4 — Documentação** — `docs/api.md`, arquitetura, CHANGELOG.

---

## Verificação

- [x] Criar, listar, detalhar (`?transcript=true`), delimitar pela API com o corpo da CLI.
- [x] `process` → 202 com tarefa; ocupado → 409 `busy`; `suggest` de assistente → 403.
- [x] SSE emite `progress` e `done`/`failed` e fecha.
- [x] `video` envia o arquivo com nome legível; não processada → 409.
- [x] `status` e `tasks` iguais ao JSON da CLI.
- [x] Sem rede, sem runner pesado nos testes; quality gates limpos.
