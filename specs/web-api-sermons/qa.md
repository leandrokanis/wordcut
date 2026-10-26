# QA — web-api-sermons — Rotas da API para pregações, tarefas e estado, com progresso por SSE

## Plano de QA — 2026-10-26

**baseline_commit**: 3c2adf0b215acb2f80292c05d76ae7cf9b8a5c73
**Componentes em escopo**: `apps/api` (`deps.py`, `routes/sermons.py`, `routes/tasks.py`,
`routes/status.py`, `sse.py`, `app.py`; `errors.py` se L2 for adotada; testes novos e
`tests/conftest.py`); `apps/web/nginx.conf` (só conferir: já tem `proxy_buffering off` no
baseline, linha 13); documentação (`docs/api.md` novo, `docs/architecture/README.md` §4 e
fluxos, `CHANGELOG.md`, ADR nova se L2/L6/L8 forem decididas). `packages/core` fora de escopo:
só leitura; mudança nele exige justificativa no plano.
**Suítes que valem como prova**:

| Componente | Comando |
|---|---|
| API (passos 1–3) | `uv run pytest apps/api/tests -q` |
| Um arquivo | `uv run pytest apps/api/tests/<arquivo> -q` |
| Monorepo inteiro (regressão) | `uv run pytest -q` |
| Checagem estática | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

**Fontes da barra**: `spec.md` e `plan.md` desta pasta; feature 1.2.a (tabela de
permissões); `docs/cli.md` §4.3, §5, §6, §7, §10; ADR-0004, ADR-0007, ADR-0013, ADR-0015,
ADR-0017, ADR-0019; código do item 19 (`apps/api/src/wordcut_api/{app,auth,errors}.py`) e
os serviços `packages/core/src/wordcut/service/{sermons,processing,suggestion,tasks,status}.py`.
Sem rastreador: os critérios saem dos cenários do spec e da Verificação do plano.

**Regras da barra** (valem para todos os passos):

- Teste de comportamento por HTTP: `fastapi.testclient.TestClient` sobre
  `create_app(settings=…, keys=…)`. Identidade por `ApiSettings(dev_email=…)` ou por token
  assinado com a fixture `sign`; membro incluído por `service.members.add_member`, nunca
  por SQL. E-mails fictícios (`assistente@exemplo.org`, `admin@exemplo.org`).
- "Corpo igual ao JSON da CLI" se prova comparando a resposta com a função de serviço que a
  CLI chama, sobre o mesmo banco e no mesmo formato que a CLI imprime (ex.: `trim` sem
  `needs_reprocess`; tarefa lançada por `service.tasks.launched_task`). Os testes da API não
  importam `wordcut_cli`.
- Nada de rede: `no_network`, `no_real_processing`, `no_real_rendering` e `no_real_llm`
  continuam autouse; nenhum teste chega ao `YouTube` real (L5).
- Nada de runner pesado real: toda rota que lança `process` ou `suggest` destacado roda com
  `harmless_tasks`, e o teste confere a lista de processos lançados. O único runner real
  permitido é o do tipo `diagnostic` (com `detached_tasks`), ou tarefa falsa gravada no banco
  por `db.tasks` (`insert`, `record_progress`, `finish_succeeded`, `finish_failed`).
- Teste que espera outro processo ou um fluxo SSE usa `time_limit` (20 s): fluxo que não
  fecha vira falha, não suíte travada.
- Mutação manual, desfeita na hora, nas linhas 🧬 do `tdd.md`; mutação que sobrevive é
  achado (PARCIAL do passo).
- Passo que dependa de uma lacuna (L1–L14) não resolvida no código fica PARCIAL, salvo se o
  `plan.md` registrar outra decisão antes da Rodada 1; nesse caso vale a decisão registrada.

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Dependências e pregações | (a) `POST /api/sermons {"url"}` → 201 com o corpo de `create_sermon` (`created: true`); o mesmo vídeo de novo → 200, `created: false`, sem consultar o dublê do YouTube; falha do dublê → 502 `youtube_error`. (b) `GET /api/sermons` → `{"items": […]}` da mais recente para a mais antiga; `?status=` filtra; valor fora de `SERMON_STATES` → 400 `invalid_argument` com `details.argument` e `details.choices`, sem eco do valor (L2, L10). (c) `GET /api/sermons/{id}` = `show_sermon`; `?transcript=true` acrescenta `sentences`; inexistente → 404 `not_found` com `details.sermon_id`; ID não inteiro → 400, sem eco (L2). (d) `PATCH /api/sermons/{id} {"start","end"}` (segundos, número) → 200 com a pregação `trimmed`, corpo igual ao `GET` seguinte, sem `needs_reprocess` (L3); faixa < 60 s → 409 `sermon_too_short`; fora da live → 400 `invalid_argument`; `processing` → 409 `busy`; campo faltando → 400 com `details.argument`. (e) `GET /api/sermons/{id}/video` → 200, bytes iguais ao arquivo, `video/mp4`, `Content-Disposition: attachment` com `AAAA-MM-DD - Título.mp4` (título acentuado sai em `filename*=utf-8''…`); não processada → 409 `sermon_not_processed`. (f) Assistente passa em todas; sem identidade → 401. (g) Nenhuma `Depends` entrega `sqlite3.Connection` atravessando threads (L1); o YouTube vem de `deps.live_source()`, trocado por dublê com guarda autouse (L5). | `uv run pytest apps/api/tests/test_sermons_routes.py -q`. Pregação processada fabricada pelo repositório (`db.sermons`) com o arquivo de vídeo em `WORDCUT_HOME`, como `apps/cli/tests/test_sermon_download_command.py`. Leitura do diff para (g). 🧬 201↔200 invertidos; `transcript` ignorado; `needs_reprocess` vazando; `filename` trocado pelo caminho interno; `CurrentMember` removido de uma rota. |
| 2 — Tarefas pela API | (a) `POST /api/sermons/{id}/process` → 202 com exatamente `{"task_id","kind":"process","status":"running","sermon_id"}` (§6.2, `launched_task`), um processo em `harmless_tasks`, e o `GET` da pregação mostra `processing` e `last_task`. (b) `{"force": true}` repassado: processada sem `force` → 409 `would_discard_edits`, com `force` → 202. (c) Sem bordas → 409 `sermon_not_trimmed`; live no ar pelo dublê → 409 `live_not_finished`. (d) Máquina ocupada (primeira tarefa em `harmless_tasks` ou `lock_owner`) → 409 `busy` com `details` da dona; nenhuma tarefa nova gravada e nenhum processo novo. (e) `POST /api/sermons/{id}/suggest` com admin, modelo e chave fictícios (`update_settings`, `store_llm_key`) → 202 `kind: "suggest"`; `preset_id` repassado (inexistente → 404 com `details.preset_id`); não processada → 409 `sermon_not_processed`; sem LLM → 409 `llm_not_configured`; assistente → 403 `forbidden` sem tarefa gravada, também para pregação inexistente. (f) `GET /api/tasks` = `list_tasks` (com `?status=` e `?kind=`; `diagnostic` e valores fora das escolhas → 400, L10); `GET /api/tasks/{id}` = `show_task`; inexistente → 404. (g) `GET /api/status` = `machine_status`, livre e com a trava ocupada (comparando sem `elapsed_seconds`, que depende do relógio, L11). | `uv run pytest apps/api/tests/test_sermons_routes.py apps/api/tests/test_tasks_routes.py -q` (ou o arquivo que o implementador criar para estado). 🧬 `detach=False` (a tarefa roda na requisição e bate em `no_real_processing`); `force` fixo em `False`; `require("admin")` trocado por `CurrentMember` no `suggest`; 202→200; `?kind` ignorado. |
| 3 — SSE | (a) `GET /api/tasks/{id}/events` → `text/event-stream`. (b) Tarefa `diagnostic` real e leve (`execution.start(..., "diagnostic", …, {"seconds": 1}, detach=True)` com `detached_tasks`): ao menos um `event: progress` e, por último, `event: done` com o `data` acordado (L6), e o fluxo fecha sozinho (a leitura termina dentro do `time_limit`). (c) `{"fail_with": "youtube_error"}` → `event: failed` com o objeto de erro; nenhum `done`. (d) Tarefa falsa já terminada no banco → `done`/`failed` imediato e fecha. (e) Tarefa órfã (PID morto gravado) → `failed` com `interrupted` (reconciliação de `show_task`). (f) Inexistente → 404 JSON antes do fluxo; sem identidade → 401. (g) Desconexão: ler o primeiro `progress` de um `diagnostic` de 2 s e fechar o cliente; a tarefa termina `succeeded` com o resultado inteiro (`wait_task`). (h) Progresso igual não se repete em eventos seguidos; heartbeat é comentário SSE (`:`), visto com o intervalo baixado por `monkeypatch` numa tarefa falsa `running` com o PID do próprio teste. | `uv run pytest apps/api/tests/test_sse.py -q`. O `TestClient` do Starlette 1.10 entrega o fluxo aos poucos e fecha cedo (conferido no baseline). 🧬 não encerrar após o estado final (estoura o `time_limit`); `failed` emitido como `done`; nome de evento trocado; emitir a cada polling sem conferir mudança. |
| 4 — Documentação | `docs/api.md` com cada rota deste item: método, caminho, corpo, status de sucesso, erros possíveis, papel mínimo, eventos SSE com o formato do `data` e a regra de o cliente fechar o `EventSource` no `done`/`failed` (L13). `CHANGELOG.md` em `[Não lançado] › Adicionado`. `docs/architecture/README.md` §4 (linha API) com as rotas novas e um fluxo coerente com SSE (L7). ADR nova para as decisões de arquitetura que o item tomar (L14). Nenhum nome ou e-mail real nos exemplos. | Leitura do diff contra o baseline; `git diff 3c2adf0 -- docs CHANGELOG.md`. |

| Critério de aceite | O que o cobre |
|---|---|
| Cenário: criar e delimitar (201, ou 200 com `created: false`; depois `trimmed`) | Passo 1 (a), (d) |
| Cenário: processar e acompanhar (202 `{"task_id", …}` e SSE com `progress` e `done`/`failed`) | Passo 2 (a); Passo 3 (b), (c). Rota de `process` + SSE no mesmo teste não é exigida: o `process` real é pesado; a ligação se prova por `task_id` da resposta 202 existir em `GET /api/tasks/{id}` |
| Cenário: máquina ocupada → 409 `busy` | Passo 2 (d) |
| Cenário: estado e tarefas iguais a `status --json` e `task list --json` | Passo 2 (f), (g) |
| Borda: `suggest` só de administrador (403 para assistente) | Passo 2 (e) |
| Borda: `video` com `Content-Disposition` legível; não processada → 409 `sermon_not_processed` | Passo 1 (e) |
| Borda: desconectar do SSE não interrompe a tarefa | Passo 3 (g) |
| Borda: toda rota exige identidade, exceto `/api/health` | Teste que percorre `app.routes` (todas as `APIRoute` sob `/api/` menos `/api/health`) com `ApiSettings()` e exige 401 de cada uma; rota nova esquecida falha sozinha. 🧬 tirar `CurrentMember` de uma rota |
| Borda: testes sem YouTube, WhisperX, OpenRouter nem runner pesado real | Guardas autouse da raiz + guarda do YouTube na API (L5); leitura dos testes: toda rota de `process`/`suggest` com 202 usa `harmless_tasks`; runner real só `diagnostic` |
| FR-001 — rotas de pregações (`transcript`, `force`, `preset_id`) | Passos 1 e 2 |
| FR-002 — rotas de tarefas, eventos e estado | Passos 2 (f), (g) e 3 |
| FR-003 — tarefas destacadas, 202 | Passo 2 (a), com o processo em `harmless_tasks` |
| FR-004 — corpos iguais ao JSON da CLI; erros com o mapeamento do item 19 | Passos 1–2 (comparação com o serviço); erros de validação como 400 `invalid_argument` sem eco (L2) |
| FR-005 — nenhuma regra de negócio na API | Leitura do diff: rotas só traduzem requisição em chamada de serviço e resultado em resposta; validação de escolhas da query é contrato de entrada, como o `argparse` da CLI |
| Verificação: criar, listar, detalhar (`?transcript=true`), delimitar com o corpo da CLI | Passo 1 (a)–(d) |
| Verificação: `process` → 202; ocupado → 409 `busy`; `suggest` de assistente → 403 | Passo 2 (a), (d), (e) |
| Verificação: SSE emite `progress` e `done`/`failed` e fecha | Passo 3 (b)–(d) |
| Verificação: `video` com nome legível; não processada → 409 | Passo 1 (e) |
| Verificação: `status` e `tasks` iguais ao JSON da CLI | Passo 2 (f), (g) |
| Verificação: sem rede, sem runner pesado; quality gates limpos | `uv run pytest -q`, `ruff check`, `ruff format --check`, `mypy` verdes; regras da barra |

### Lacunas do plano (escrito antes do item 19)

- **L1 — Conexão por dependência com `yield`.** O plano decide `deps.connection()` com
  `yield`. O item 19 decidiu o contrário em `auth.py:103-106` e na ADR-0019: a conexão é
  aberta e fechada na mesma chamada, porque o FastAPI pode rodar a dependência e a rota em
  threads diferentes e a conexão `sqlite3` fica presa à thread em que foi aberta.
  **Recomendação**: a rota abre `with closing(db.connect(home))` no próprio corpo (ou chama
  um `deps.connection()` sem `yield`, como o da CLI). `start_processing`,
  `start_suggestion`, `list_tasks`, `show_task` e `machine_status` já recebem `home` e
  abrem a própria conexão.
- **L2 — Erro de validação do FastAPI.** No baseline, um ID não inteiro ou um valor fora das
  escolhas dá 422 `{"detail": [...]}` com `"input"` repetindo o valor digitado (conferido com
  FastAPI 0.162). Isso fere a FR-004 e a ADR-0015. Rota inexistente dá
  `{"detail": "Not Found"}`. **Recomendação**: `errors.install` passa a tratar
  `RequestValidationError` como 400 `invalid_argument`, com `details.argument` (o nome do
  campo) e, se houver, `details.choices`, sem `input` nem a mensagem do pydantic. Opcional,
  fora da barra: trocar também o corpo do 404 do Starlette por `not_found`.
- **L3 — `needs_reprocess`.** `trim_sermon` e `create_sermon` com bordas devolvem
  `needs_reprocess`. A CLI retira esse campo do JSON e o transforma em aviso
  (`apps/cli/.../sermon.py`, `_warn_if_reprocess_needed`). "Os mesmos `dict` dos serviços"
  deixaria o campo vazar. **Recomendação**: retirar o campo, para o corpo ficar igual ao
  JSON da CLI. A web deduz o aviso de `status == "processed"` logo depois do `PATCH`.
- **L4 — Corpo da tarefa lançada.** `start_processing` e `start_suggestion` devolvem
  `TaskRow`, não `dict`. **Recomendação**: a resposta 202 é
  `service.tasks.launched_task(row)`, o mesmo corpo da CLI sem `--wait` (§6.2).
- **L5 — Porta do YouTube sem guarda.** `YouTube.info` roda o yt-dlp sem
  `refuse_when_forbidden`, porque a ADR-0017 cobre só as duas fábricas. A CLI tem a guarda
  autouse `NoYouTube` em `apps/cli/tests/conftest.py`. O plano diz "dublê nos testes", sem
  guarda. **Recomendação**: as rotas chamam `deps.live_source()` na hora da requisição, como
  a CLI, e `apps/api/tests/conftest.py` ganha uma fixture autouse que troca essa porta por um
  dublê que falha com `AssertionError`. Com `Depends(deps.live_source)`, a função fica
  capturada quando a rota é definida e escapa do `monkeypatch`.
- **L6 — Formato dos eventos SSE.** O plano diz `progress`/`done`/`failed` e um heartbeat,
  mas não diz o que vai no `data`. **Recomendação**:
  - o `data` de todo evento é o JSON de `show_task`, o mesmo corpo de
    `GET /api/tasks/{id}`. `done` traz `result` (o fluxo 5.3 da arquitetura já mostra
    `done (render_id)`) e `failed` traz `error`;
  - `progress` só sai quando muda o par `(progress, progress_message)`, como em `wait_task`;
  - o heartbeat é um comentário SSE (`: ping`);
  - tarefa inexistente dá 404 JSON antes de abrir o fluxo;
  - o intervalo do polling e o do heartbeat ficam em constantes do módulo, para o teste
    poder baixá-los.
- **L7 — Diagrama citado errado.** O plano manda deixar "coerente o diagrama 5.2", mas o 5.2 é
  "Exportar um corte pela CLI". O fluxo da web com SSE é o 5.3, das exportações, que é do
  item 20b. **Recomendação**: acrescentar um fluxo "Processar uma pregação pela web"
  (`POST …/process` → 202 → `GET /api/tasks/{id}/events`) e atualizar a linha API do §4.
- **L8 — OpenAPI "só em modo dev".** No baseline, `/docs` e `/openapi.json` respondem 200
  sem identificação, e o plano não define o que é "modo dev". **Recomendação**:
  `docs_url="/api/docs"` e `openapi_url="/api/openapi.json"` só quando a identificação for a
  `DevIdentification`; nos outros casos, `None`. Barra: com o Access configurado,
  `/docs`, `/openapi.json`, `/api/docs` e `/api/openapi.json` dão 404.
- **L9 — Corpos de entrada.** O plano não fixa os corpos. **Recomendação**:
  - `POST /api/sermons` recebe só `{"url"}`, como diz o spec; as bordas vão no `PATCH`;
  - o `PATCH` recebe `start` e `end` obrigatórios, em segundos e como número (§4.3);
  - o `process` recebe `{"force": false}` opcional;
  - o `suggest` recebe `{"preset_id": null}` opcional.
- **L10 — Filtros da query.** A CLI recusa `--status` e `--kind` fora das escolhas, mas o
  serviço não valida: `list_tasks(status="x")` devolve uma lista vazia. **Recomendação**:
  tipar `status` e `kind` com `Literal` a partir de `SERMON_STATES`, `TASK_STATES` e
  `TASK_KINDS` (que já excluem `diagnostic`). Com a L2, um valor fora vira 400 com
  `details.choices`.
- **L11 — Comparação com `status` quando a trava está ocupada.** `elapsed_seconds` depende
  do relógio. **Recomendação**: comparar sem esse campo, ou com tolerância de 1 s. O caso
  com a máquina livre é comparado inteiro.
- **L12 — SSE síncrono.** Um gerador com `time.sleep` prende uma thread do pool do anyio por
  cliente (40 por padrão) e pode atrasar as rotas síncronas. **Recomendação**: usar um gerador
  assíncrono com `asyncio.sleep` e `run_in_threadpool(show_task, …)`. Isso não entra na
  barra; o QA registra como risco se não for adotado.
- **L13 — Reconexão do `EventSource`.** Quando o servidor fecha o fluxo, o navegador
  reconecta sozinho e receberia de novo o `done`. **Recomendação**: `docs/api.md` diz que o
  cliente fecha o `EventSource` no `done` ou no `failed`.
- **L14 — ADR.** "SSE por polling do SQLite", "erro de validação como 400 sem eco" e
  "OpenAPI só em desenvolvimento" são decisões de arquitetura novas. A ADR-0019 já foi
  aceita e não se edita (CONTRIBUTING). **Recomendação**: registrar uma ADR-0020 e incluí-la
  no índice, no mesmo commit.
- **Nota (não é lacuna)**: o `apps/web/nginx.conf` já tem `proxy_buffering off` no baseline.
  O `proxy_read_timeout` padrão, de 60 s, é maior que o heartbeat de 15 s.

## Rodada 1 — 2026-10-26 — working tree sobre 3c2adf0

**baseline_commit**: 3c2adf0b215acb2f80292c05d76ae7cf9b8a5c73
**Componentes avaliados**: `apps/api` (`deps.py`, `sse.py`, `routes/{sermons,tasks,status}.py`,
`app.py`, `errors.py`, `tests/conftest.py`, `tests/test_auth.py` e os três arquivos de teste
novos); documentação (`docs/api.md`, ADR-0020 e índice, `docs/architecture/README.md`,
`CHANGELOG.md`, `README.md`, `CONTRIBUTING.md`). `packages/` e `apps/web/` sem mudança
(`proxy_buffering off` segue na linha 13 do `nginx.conf`).
**Suítes**: API ✅ (118 / 0 falhas) · monorepo ✅ (1390 / 0 falhas) · `ruff check` ✅ ·
`ruff format --check` ✅ · `mypy` ✅ · nenhum processo de teste sobrando.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Dependências e pregações | PASS | `test_sermons_routes.py` cobre 1 (a)–(e), comparando com `create_sermon`, `list_sermons` e `show_sermon`; 401 em toda rota por `test_auth.py::test_every_route_but_health_requires_someone_identified`; L8 pelos dois testes de esquema. (g) pelo diff: nenhuma `Depends` entrega conexão, e o YouTube vem de `deps.live_source()` na hora (guarda `no_real_youtube`). Mutações mortas: 201↔200, `transcript`, `needs_reprocess`, `filename`, identidade fora de um router, YouTube real no lugar de `deps`, eco do `input`, 422. |
| 2 — Tarefas pela API | PASS | 2 (a)–(e) em `test_sermons_routes.py`, todos com `harmless_tasks` e a lista de processos conferida; 2 (f)–(g) em `test_tasks_routes.py` contra `list_tasks`, `show_task` e `machine_status` (sem `elapsed_seconds` com a trava ocupada, L11). Mutações mortas: `detach=False`, `require("admin")` fora do `suggest`, `?kind` ignorado. |
| 3 — SSE | PASS | `test_sse.py` cobre 3 (a)–(h): `diagnostic` real e destacado com `detached_tasks` (que puxa o `time_limit`), falha `youtube_error`, tarefa terminada, órfã `interrupted`, 404 JSON, desconexão com `wait_task` e heartbeat `: ping`. Mutações mortas: sem encerrar (TimeoutError), `failed` como `done`, progresso sem conferir mudança e desconexão que mata a tarefa (mutação extra). L12 pela leitura do diff, como o orquestrador decidiu: `sse.task_events` é `async`, espera com `asyncio.sleep` e chama `show_task` só em `run_in_threadpool` (`sse.py:46`), a rota também (`routes/tasks.py:37`); `deps.home()` só lê o ambiente. Não há chamada bloqueante fora do pool. |
| 4 — Documentação | PASS | `docs/api.md` traz rota, corpo, sucesso, erros, papel, `data` dos eventos e o fechamento do `EventSource` no `done`/`failed` (L13). ADR-0020 nova, com entrada no índice, e ADR-0019 intocada (L14). §4 (linha API) e o fluxo 5.5 "Processar uma pregação pela web" (L7). `CHANGELOG` em `[Não lançado] › Adicionado`. Nenhum nome nem e-mail real. |

**Fato 1 do implementador (varredura de identidade)**: confirmado. No FastAPI 0.162,
`app.routes` traz `_IncludedRouter` no lugar das rotas incluídas. Por isso o instrumento da
matriz ("percorre `app.routes`") não serve como foi escrito. Julguei pelo que a matriz pede
que se observe: 401 em toda rota sob `/api/` menos `/api/health`, e a mutação 🧬 que tira a
identidade morre. A varredura pelo OpenAPI cobre as 13 operações de hoje. Nenhuma rota do
código usa `include_in_schema=False`. As únicas rotas fora do esquema são as do próprio
FastAPI (`/api/docs`, `/api/openapi.json`, `/docs/oauth2-redirect`), e elas só existem com
`WORDCUT_DEV_EMAIL`, nunca no app que o teste monta. Risco que fica: uma rota futura com
`include_in_schema=False` e sem identidade passaria. A mutação que acrescenta essa rota
sobreviveu.

**Achados fora da barra (não mudam o veredito)**:

- A cadência do heartbeat não é provada. A mutação que não reinicia o relógio depois de um
  `: ping` sobrevive: o ping passa a sair a cada polling depois do primeiro. A matriz, em
  3 (h), só exige que o heartbeat seja um comentário SSE.
- Com `WORDCUT_DEV_EMAIL`, o FastAPI também serve `/docs/oauth2-redirect`, fora de `/api/`.
  Só acontece em desenvolvimento.
- Política de comentários (CONTRIBUTING §5): os comentários novos são de intenção,
  referência, restrição externa ou formato. Dois ficam no limite de narrar o código:
  `sse.py` "The event that ends the stream, by final status of the task." e `errors.py` "An
  optional parameter is a union with None: look inside it.". Achado leve.
- Os `Literal` de `routes/sermons.py` e `routes/tasks.py` repetem as tuplas
  `SERMON_STATES`, `TASK_STATES` e `TASK_KINDS` em vez de derivar delas. Se divergirem, os
  testes falham, porque comparam `details.choices` com as constantes.

### Critérios de aceite
- ✅ Cenário: criar e delimitar — `test_creating_a_sermon_answers_201…`, `test_the_same_video_again…`, `test_trimming_answers_the_trimmed_sermon…`
- ✅ Cenário: processar e acompanhar — `test_processing_answers_202…`, `test_the_task_a_processing_launched_is_found_among_the_tasks`, `test_a_running_task_streams_its_progress_and_then_done…`, `test_a_task_that_fails_streams_failed…`
- ✅ Cenário: máquina ocupada → 409 `busy` — `test_processing_while_the_machine_is_busy_records_no_task`, `test_processing_while_another_processing_runs_is_busy_naming_that_task`
- ✅ Cenário: estado e tarefas iguais ao JSON da CLI — `test_listing_the_tasks_answers_them_as_task_list_does`, `test_the_status_of_a_free_machine…`, `test_the_status_of_a_busy_machine…`
- ✅ Borda: `suggest` só de administrador — `test_an_assistant_asking_for_a_suggestion_is_forbidden_and_no_task_is_recorded[2]`
- ✅ Borda: `video` com nome legível; não processada → 409 — `test_the_video_of_a_processed_sermon_downloads_with_the_readable_name[2]`, `test_the_video_of_a_sermon_not_processed_is_refused`
- ✅ Borda: desconectar do SSE não interrompe a tarefa — `test_a_client_that_goes_away_leaves_the_task_running_to_its_end` (a mutação que mata a tarefa ao desconectar morre)
- ✅ Borda: toda rota exige identidade, menos `/api/health` — `test_every_route_but_health_requires_someone_identified`, pelo OpenAPI. Rota com `include_in_schema=False` fica fora; não existe nenhuma hoje
- ✅ Borda: testes sem YouTube, WhisperX, OpenRouter nem runner pesado real — guardas autouse da raiz e `no_real_youtube`; todo 202 de `process`/`suggest` com `harmless_tasks`; runner real só `diagnostic`
- ✅ FR-001 — passos 1 e 2 (`transcript`, `force`, `preset_id` com mutações mortas)
- ✅ FR-002 — passos 2 (f), (g) e 3
- ✅ FR-003 — `test_processing_answers_202…` e `test_an_admin_asking_for_a_suggestion_gets_202…` (`detach=False` morre)
- ✅ FR-004 — comparação com o serviço nos dois arquivos de rotas; 400 `invalid_argument` sem eco (`test_an_id_that_is_not_a_number…`, `test_a_status_outside_the_choices…`, `test_a_filter_outside_the_choices…[3]`)
- ✅ FR-005 — leitura do diff: as rotas só traduzem a requisição e a resposta; o `del needs_reprocess` é o formato da CLI
- ✅ Verificação: criar, listar, detalhar, delimitar — passo 1
- ✅ Verificação: `process` 202, `busy` 409, `suggest` 403 — passo 2
- ✅ Verificação: SSE com `progress` e `done`/`failed`, e o fluxo fecha — passo 3
- ✅ Verificação: `video` com nome legível; não processada → 409 — passo 1 (e)
- ✅ Verificação: `status` e `tasks` iguais ao JSON da CLI — passo 2 (f), (g)
- ✅ Verificação: sem rede, sem runner pesado; quality gates limpos — suíte do monorepo, `ruff`, `format` e `mypy` verdes

### Veredito geral: PASS
Os 4 passos têm PASS, os 20 critérios estão cobertos e as suítes e checagens estão verdes. A
L12 foi aceita pela leitura do diff. Ficam registrados dois riscos fora da barra: a cadência
do heartbeat e rota com `include_in_schema=False`.
