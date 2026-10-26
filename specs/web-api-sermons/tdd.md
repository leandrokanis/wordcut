## Plano de QA

baseline_commit 3c2adf0b215acb2f80292c05d76ae7cf9b8a5c73

14:55  📐 BARRA   corpos iguais ao JSON da CLI
       resposta HTTP comparada com a função de serviço que a CLI chama,
       no formato que a CLI imprime; testes da API não importam a CLI

14:55  📐 BARRA   identidade em toda rota, menos /api/health
       teste percorre app.routes com ApiSettings() e exige 401 de cada
       APIRoute sob /api/; rota esquecida falha sozinha

14:55  📐 BARRA   tarefa lançada destacada, 202, sem runner pesado
       process/suggest com harmless_tasks e a lista de processos
       conferida; runner real só do tipo diagnostic

14:56  📐 BARRA   SSE com progress e done/failed, e o fluxo fecha
       diagnostic real de 1 s com detached_tasks; TestClient do Starlette
       1.10 lê o fluxo aos poucos e fecha cedo (conferido no baseline)

14:56  📐 BARRA   desconectar do SSE não interrompe a tarefa
       ler o primeiro progress de um diagnostic de 2 s, fechar o cliente
       e exigir succeeded com o resultado inteiro por wait_task

14:56  🧬 EXIGE   detach=False na rota de process  ·  vermelha
       a tarefa rodaria na requisição e bateria em no_real_processing

14:56  🧬 EXIGE   require("admin") trocado por CurrentMember no suggest
       ·  vermelha
       prova que o assistente recebe 403 sem tarefa gravada

14:56  🧬 EXIGE   SSE sem encerrar no estado final  ·  vermelha
       a leitura estoura o time_limit em vez de terminar

14:56  🧬 EXIGE   needs_reprocess vazando no PATCH  ·  vermelha
       PATCH de pregação processada igual ao GET seguinte

14:57  ⚠️ LACUNA  L1 conexão por Depends com yield
       auth.py:103 e ADR-0019 abrem e fecham na mesma chamada (threads);
       passo 1 fica PARCIAL se uma Depends entregar a conexão

14:57  ⚠️ LACUNA  L2 validação do FastAPI dá 422 e ecoa o input
       conferido no baseline; fere FR-004 e ADR-0015; sem handler 400
       invalid_argument os passos 1 e 2 ficam PARCIAL

14:57  ⚠️ LACUNA  L5 YouTube.info sem guarda de rede
       sem guarda autouse em apps/api/tests, um teste esquecido chama o
       yt-dlp de verdade; a borda "sem rede" fica descoberta

14:57  ⚠️ LACUNA  L6 data dos eventos SSE indefinido
       recomendado: JSON de show_task em todo evento; sem decisão o
       passo 3 é julgado pelo que docs/api.md registrar

14:57  ⚠️ LACUNA  L7 diagrama 5.2 citado é o da CLI
       fluxo web com SSE falta; passo 4 PARCIAL sem ele

14:57  ⚠️ LACUNA  L8 /docs e /openapi.json abertos sem identidade
       "modo dev" indefinido; recomendado só com DevIdentification

14:58  ⚠️ LACUNA  L14 decisões novas sem ADR
       SSE por polling, 400 sem eco e OpenAPI só em dev pedem ADR-0020

       Demais lacunas (L3, L4, L9–L13) em qa.md.

## Rodada 1 · implementador

15:02  ⚙️ DECISÕES  L1–L14 registradas em plan.md (Decisões técnicas)
       Contexto de código ajustado: conexão no corpo da rota, SSE
       assíncrono, errors.py, conftest e ADR-0020

--- Passo 1: Dependências e pregações ---

15:02  🔴 RED    test_creating_a_sermon_answers_201_with_the_sermon_the_cli_shows
       POST /api/sermons {"url"} cria a pregação: 201 com o corpo de
       create_sermon e created: true
       Cenário "criar e delimitar"; FR-001; Passo 1 (a); L5, L9
       ImportError: cannot import name 'deps' from 'wordcut_api'

15:02  🟢 GREEN  test_creating_a_sermon_answers_201_with_the_sermon_the_cli_shows  ·  1 passed

15:03  🔴 RED    test_the_same_video_again_answers_200_with_created_false_without_asking_youtube
       o mesmo vídeo de novo devolve a pregação existente, 200, sem YouTube
       Cenário "criar e delimitar"; Passo 1 (a)
       AssertionError: At index 0 diff: 201 != 200

15:03  🟢 GREEN  test_the_same_video_again_answers_200_with_created_false_without_asking_youtube  ·  2 passed

15:03  🟢 GREEN  test_youtube_failing_to_answer_is_a_bad_gateway_with_youtube_error
       ·  3 passed
       verde de saída: o 502 youtube_error já vem de create_sermon e
       errors.install (item 19); o teste fixa o contrato da rota (1 (a))

15:03  🔴 RED    test_listing_answers_the_sermons_as_the_cli_lists_them_latest_service_first
       GET /api/sermons = list_sermons, da mais recente para a mais antiga
       Passo 1 (b); FR-001, FR-004
       AssertionError: At index 0 diff: 405 != 200

15:03  🟢 GREEN  test_listing_answers_the_sermons_as_the_cli_lists_them_latest_service_first  ·  4 passed

15:03  🔴 RED    test_listing_by_status_answers_only_the_sermons_in_that_status
       ?status=created devolve só as pregações nesse estado
       Passo 1 (b); FR-001
       assert [2, 1] == [1]

15:04  🟢 GREEN  test_listing_by_status_answers_only_the_sermons_in_that_status  ·  5 passed

15:04  🔴 RED    test_a_status_outside_the_choices_is_invalid_argument_with_the_choices_without_echo
       status fora de SERMON_STATES: 400 invalid_argument com argument e
       choices, sem repetir o valor digitado
       Passo 1 (b); L2, L10; FR-004; ADR-0015
       AssertionError: At index 0 diff: 200 != 400

15:04  🟢 GREEN  test_a_status_outside_the_choices_is_invalid_argument_with_the_choices_without_echo  ·  7 passed

15:04  🔴 RED    test_showing_a_sermon_answers_it_as_the_cli_shows_it
       GET /api/sermons/{id} = show_sermon
       Passo 1 (c); FR-001, FR-004
       AssertionError: At index 0 diff: 404 != 200

15:05  🟢 GREEN  test_showing_a_sermon_answers_it_as_the_cli_shows_it  ·  7 passed

15:05  🔴 RED    test_showing_with_the_transcript_adds_the_sentences_as_the_cli_shows_them
       ?transcript=true acrescenta sentences, como sermon show --transcript
       Passo 1 (c); FR-001; Verificação
       KeyError: 'sentences'

15:05  🟢 GREEN  test_showing_with_the_transcript_adds_the_sentences_as_the_cli_shows_them  ·  8 passed

15:05  🟢 GREEN  test_showing_a_missing_sermon_is_not_found_with_its_id
       test_an_id_that_is_not_a_number_is_invalid_argument_without_echo
       ·  10 passed
       verdes de saída: o 404 vem de show_sermon e o 400 sem eco do
       handler de validação do ciclo anterior; fixam 1 (c) e L2

15:05  🔴 RED    test_trimming_answers_the_trimmed_sermon_as_the_next_show_gives_it
       PATCH {start, end} em segundos leva a trimmed; corpo = GET seguinte
       Cenário "criar e delimitar"; Passo 1 (d); L9
       AssertionError: At index 0 diff: 405 != 200

15:06  🟢 GREEN  test_trimming_answers_the_trimmed_sermon_as_the_next_show_gives_it  ·  11 passed

15:06  🟢 GREEN  test_trimming_a_processed_sermon_answers_it_without_needs_reprocess
       ·  12 passed
       verde de saída: o del do ciclo anterior já tira o campo; fixa L3
       numa pregação processada (needs_reprocess seria true)

15:06  🔴 RED    test_trimming_without_the_end_is_invalid_argument_naming_it
       PATCH sem end: 400 com a mensagem de argumento ausente da CLI
       Passo 1 (d); L2, L9; ADR-0015
       message 'Valor inválido para end.' != 'Argumento obrigatório ausente: end.'

15:06  🟢 GREEN  test_trimming_without_the_end_is_invalid_argument_naming_it  ·  13 passed

15:06  🟢 GREEN  test_trimming_refuses_borders_the_cli_refuses[3 casos]
       test_trimming_a_sermon_being_processed_is_busy  ·  17 passed
       verdes de saída: 409 sermon_too_short, 400 fora da live e 409
       busy vêm de trim_sermon; o texto como segundos é recusado pelo
       StrictFloat do ciclo do PATCH (L9); fixam 1 (d)

15:07  🔴 RED    test_the_video_of_a_processed_sermon_downloads_with_the_readable_name
       GET …/video envia os bytes do vídeo, video/mp4, attachment com
       AAAA-MM-DD - Título.mp4
       Borda "video com Content-Disposition legível"; Passo 1 (e)
       KeyError: 'content-disposition' (a rota não existe: 404)

15:07  🔴 RED    test_the_video_of_a_processed_sermon_downloads_with_the_readable_name
       expectativa corrigida: o Starlette põe o nome com espaço ou acento
       em filename*=utf-8''… (RFC 6266); parametrizado com título
       acentuado, como pede 1 (e)

15:07  🟢 GREEN  test_the_video_of_a_processed_sermon_downloads_with_the_readable_name[2]  ·  19 passed

15:08  🟢 GREEN  test_the_video_of_a_sermon_not_processed_is_refused  ·  20 passed
       verde de saída: 409 sermon_not_processed vem de sermon_video

15:08  🔴 RED    test_every_route_but_health_requires_someone_identified
       toda rota sob /api/ menos health dá 401 sem identidade; rota nova
       esquecida falha sozinha
       Borda "toda rota exige identidade"; Passo 1 (f)
       assert (False, {401}): erro do teste, não da produção — o FastAPI
       0.162 guarda o router incluído como _IncludedRouter, fora de
       app.routes; o teste passa a ler as rotas do esquema OpenAPI

15:08  🟢 GREEN  test_every_route_but_health_requires_someone_identified  ·  45 passed

15:08  🧬 MUTAÇÃO tirar a identidade do router de pregações  ·  morta
       test_every_route_but_health_requires_someone_identified falha;
       desfeita

15:08  🔴 RED    test_with_access_the_api_schema_and_its_pages_are_not_served
       com o Access, /docs, /openapi.json, /redoc, /api/docs e
       /api/openapi.json dão 404 not_found
       L8, L2 (404 do Starlette vira not_found)
       JSONDecodeError: /docs responde a página HTML do Swagger

15:08  🔴 RED    test_in_development_the_api_schema_is_served_under_api
       com WORDCUT_DEV_EMAIL, o esquema sai em /api/docs e /api/openapi.json
       L8
       assert [404, 404] == [200, 200]

15:09  🟢 GREEN  test_with_access_the_api_schema_and_its_pages_are_not_served
       test_in_development_the_api_schema_is_served_under_api
       ·  89 passed

15:09  🧬 MUTAÇÃO needs_reprocess vazando no PATCH  ·  morta (2 testes)
       transcript ignorado  ·  morta; 201↔200 invertidos  ·  morta (2);
       filename trocado pelo nome interno  ·  morta (2); todas desfeitas

15:09  ♻️ REFACTOR imports organizados (ruff --fix), ruff format; ruff,
       format e mypy limpos

15:09  ✅ PASSO 1/4 — Dependências e pregações  ·  +23 testes  ·  suíte 89

15:10  🧪 PASSO 2 — Tarefas pela API

15:10  🔴 RED    test_processing_answers_202_with_the_launched_task_and_the_sermon_is_processing
       POST …/process: 202 com o corpo de launched_task, um processo
       destacado (harmless_tasks), pregação processing com last_task
       Cenário "processar e acompanhar"; Passo 2 (a); FR-003; L4
       TypeError: 'NoneType' object is not subscriptable (last_task None:
       a rota não existe)

15:10  🟢 GREEN  test_processing_answers_202_with_the_launched_task_and_the_sermon_is_processing  ·  21 passed

15:10  🟢 GREEN  test_processing_a_processed_sermon_again_needs_force  ·  22 passed
       escrito depois do GREEN anterior, que já repassava force (passou
       do mínimo); a prova vem da mutação abaixo

15:10  🧬 MUTAÇÃO force fixo em False  ·  morta; desfeita

15:11  🟢 GREEN  test_processing_a_sermon_without_borders_is_refused
       test_processing_while_the_live_is_still_on_air_is_refused
       test_processing_while_the_machine_is_busy_records_no_task
       test_processing_while_another_processing_runs_is_busy_naming_that_task
       ·  26 passed
       verdes de saída: sermon_not_trimmed, live_not_finished (dublê do
       YouTube por deps.live_source na hora, L5) e busy vêm de
       start_processing e execution.start; fixam 2 (c), 2 (d) e o cenário
       "máquina ocupada" — nenhuma tarefa nem processo novo

15:11  🔴 RED    test_an_admin_asking_for_a_suggestion_gets_202_with_the_launched_task
       POST …/suggest de administrador, LLM configurado: 202 kind suggest,
       um processo destacado (harmless_tasks)
       Passo 2 (e); FR-001, FR-003; L4
       KeyError: 'task_id' (a rota não existe: 404)

15:11  🟢 GREEN  test_an_admin_asking_for_a_suggestion_gets_202_with_the_launched_task  ·  27 passed

15:12  🟢 GREEN  test_an_assistant_asking_for_a_suggestion_is_forbidden_and_no_task_is_recorded[2]
       test_a_suggestion_with_a_missing_preset_is_not_found_naming_the_preset
       test_a_suggestion_for_a_sermon_not_processed_is_refused
       test_a_suggestion_without_the_llm_configured_is_refused  ·  32 passed
       escritos depois do GREEN da rota, que já trazia require("admin")
       e preset_id (passou do mínimo); a prova vem das mutações abaixo

15:12  🧬 MUTAÇÃO require("admin") trocado por CurrentMember no suggest
       ·  morta (2); preset_id fixo em None  ·  morta; detach=False no
       process  ·  morta (3: a tarefa roda na requisição e bate em
       no_real_processing); todas desfeitas

15:12  🔴 RED    test_listing_the_tasks_answers_them_as_task_list_does
       GET /api/tasks = list_tasks (task list --json)
       Cenário "estado e tarefas"; Passo 2 (f); FR-002, FR-004
       KeyError: 'items' (a rota não existe: 404)

15:12  🟢 GREEN  test_listing_the_tasks_answers_them_as_task_list_does  ·  1 passed

15:12  🔴 RED    test_listing_by_status_and_kind_answers_only_those_tasks
       ?status=running&kind=suggest = list_tasks com os dois filtros
       Passo 2 (f); FR-002
       AssertionError: [3, 2, 1] != [2]

15:13  🟢 GREEN  test_listing_by_status_and_kind_answers_only_those_tasks  ·  2 passed

15:13  🟢 GREEN  test_a_filter_outside_the_choices_is_invalid_argument_with_the_choices[3]
       verdes de saída: Literal do ciclo anterior + handler de validação
       (L2, L10); diagnostic fora das escolhas, como na CLI

15:13  🔴 RED    test_showing_a_task_answers_it_as_task_show_does
       GET /api/tasks/{id} = show_task
       Passo 2 (f); FR-002, FR-004
       AssertionError: At index 0 diff: 404 != 200

15:13  🟢 GREEN  test_showing_a_task_answers_it_as_task_show_does  ·  6 passed

15:13  🟢 GREEN  test_showing_a_missing_task_is_not_found_with_its_id
       test_the_task_a_processing_launched_is_found_among_the_tasks
       verdes de saída: 404 de show_task; o task_id do 202 existe em
       GET /api/tasks/{id} (ligação do cenário "processar e acompanhar")

15:13  🔴 RED    test_the_status_of_a_free_machine_is_the_one_status_gives
       GET /api/status = machine_status com a máquina livre
       Cenário "estado e tarefas"; Passo 2 (g); FR-002
       AssertionError: At index 0 diff: 404 != 200

15:13  🟢 GREEN  test_the_status_of_a_free_machine_is_the_one_status_gives  ·  8 passed

15:13  🟢 GREEN  test_the_status_of_a_busy_machine_is_the_one_status_gives
       ·  9 passed
       verde de saída: a rota do ciclo anterior já repassa machine_status;
       fixa 2 (g) com a trava ocupada, comparando sem elapsed_seconds (L11)

15:13  🧬 MUTAÇÃO ?kind ignorado  ·  morta; desfeita

15:14  ♻️ REFACTOR ruff --fix e ruff format; ruff, format e mypy limpos;
       nenhum processo de teste sobrando

15:14  ✅ PASSO 2/4 — Tarefas pela API  ·  +22 testes  ·  suíte 111

15:14  🧪 PASSO 3 — SSE

15:14  🔴 RED    test_a_finished_task_streams_done_at_once_and_the_stream_closes
       tarefa já terminada: text/event-stream com um done (data = show_task)
       e o fluxo fecha
       Passo 3 (a), (d); FR-002; L6
       AssertionError: At index 0 diff: 404 != 200

15:15  🟢 GREEN  test_a_finished_task_streams_done_at_once_and_the_stream_closes  ·  1 passed

15:15  🔴 RED    test_a_running_task_streams_its_progress_and_then_done_and_the_stream_closes
       diagnostic real de 1 s destacado: progress primeiro, um done por
       último com show_task, e o fluxo fecha sozinho
       Cenário "processar e acompanhar"; Passo 3 (b); L6
       AttributeError: module 'wordcut_api.sse' has no attribute 'POLL_SECONDS'

15:15  🟢 GREEN  test_a_running_task_streams_its_progress_and_then_done_and_the_stream_closes  ·  2 passed

15:15  🟢 GREEN  test_a_task_that_fails_streams_failed_with_its_error_and_never_done
       test_a_task_whose_process_died_streams_failed_as_interrupted
       test_the_events_of_a_missing_task_are_a_json_not_found_before_any_stream
       ·  5 passed
       verdes de saída: FINAL_EVENTS do primeiro ciclo já separa failed de
       done; a reconciliação de show_task marca a órfã interrupted; o 404
       sai do show_task chamado antes de abrir o fluxo; fixam 3 (c)–(f)

15:16  🟢 GREEN  test_a_client_that_goes_away_leaves_the_task_running_to_its_end
       ·  6 passed
       verde de saída: a tarefa roda em processo destacado e o fluxo só
       lê o banco; fixa a borda "desconectar do SSE não interrompe" (3 (g))

15:16  🔴 RED    test_an_unchanged_progress_is_sent_once_and_silence_is_filled_with_heartbeats
       progresso igual não se repete; o silêncio vira comentário ': ping'
       tarefa falsa running com o PID do teste; intervalos baixados
       Passo 3 (h); L6
       AttributeError: module 'wordcut_api.sse' has no attribute 'HEARTBEAT_SECONDS'

15:16  🟢 GREEN  test_an_unchanged_progress_is_sent_once_and_silence_is_filled_with_heartbeats  ·  7 passed

15:18  🧬 MUTAÇÃO não encerrar após o estado final  ·  morta (TimeoutError
       do time_limit); failed emitido como done  ·  morta (2); nome do
       evento trocado  ·  morta (3); progress a cada polling sem conferir
       mudança  ·  morta; todas desfeitas

15:18  ♻️ REFACTOR comentário de intenção do gerador assíncrono (L12); ruff,
       format e mypy limpos
       L12 se prova pela leitura do diff: gerador async com asyncio.sleep e
       show_task em run_in_threadpool; não há teste de saturação do pool,
       que dependeria de latência

15:18  ✅ PASSO 3/4 — SSE  ·  +7 testes  ·  suíte 118

15:20  🧪 PASSO 4 — Documentação (sem TDD: só texto)

15:20  📝 DOCS    docs/api.md (rotas, corpos, status, papéis, eventos SSE com o
       data, fechar o EventSource no done/failed, L13; OpenAPI só em dev);
       ADR-0020 + índice (L14); arquitetura §4 (linha API) e fluxo 5.5
       "Processar uma pregação pela web" (L7); CHANGELOG [Não lançado] ›
       Adicionado; README (link e estado) e CONTRIBUTING (porta do YouTube
       nos testes); exemplos sem nome nem e-mail real

15:20  ✅ PASSO 4/4 — Documentação  ·  +0 testes  ·  suíte 118

15:22  🏁 FINAL   uv run pytest -q · 1390 passed; ruff check, ruff format
       --check e mypy limpos; nenhum processo de teste sobrando; sem
       commit (override do orquestrador)

## Rodada 1 · QA

15:24  📊 SUÍTE  apps/api/tests  ·  118 passed  ·  0 failed

15:26  📊 SUÍTE  uv run pytest -q  ·  1390 passed  ·  0 failed
       ruff check, ruff format --check e mypy limpos; nenhum processo
       de teste sobrando

15:27  🔎 QA     fato 1 — rotas incluídas fora de app.routes  ·  confirmado
       FastAPI 0.162: app.routes traz 3 _IncludedRouter; o OpenAPI lista
       as 13 operações; nenhuma rota do código usa include_in_schema=False

15:27  🔎 QA     L12 pela leitura do diff  ·  ✅ PASS
       task_events é async, espera com asyncio.sleep e lê show_task em
       run_in_threadpool; a rota events idem; deps.home() só lê o ambiente

15:28  🧬 MUTAÇÕES · cópia no scratchpad, apps/api  ·  15 de 17 mortas
       ☠️  SSE sem encerrar no estado final        TimeoutError
       ☠️  detach=False no process                 1 teste
       ☠️  require("admin") fora do suggest        1 teste
       ☠️  needs_reprocess vazando no PATCH        1 teste
       ☠️  identidade fora do router de status     varredura
       ☠️  progress a cada polling                 1 teste
       ☠️  failed emitido como done                1 teste
       ☠️  ?kind ignorado                          1 teste
       ☠️  201↔200 invertidos                      1 teste
       ☠️  transcript ignorado                     1 teste
       ☠️  validação ecoa o input                  1 teste
       ☠️  validação devolve 422                   1 teste
       ☠️  YouTube real no lugar de deps           1 teste
       ☠️  filename pelo nome interno              1 teste
       ☠️  desconexão mata a tarefa                1 teste
       🚨  heartbeat sem reiniciar o relógio  SOBREVIVEU — ping a cada
           polling depois do primeiro; fora da barra 3 (h)
       🚨  rota include_in_schema=False sem identidade  SOBREVIVEU —
           a varredura lê o OpenAPI; nenhuma rota assim existe hoje

15:29  🔎 QA     passo 1/4 — Dependências e pregações  ·  ✅ PASS
       1 (a)–(g) cobertos; L1, L2, L3, L5, L8, L9, L10 no código

15:29  🔎 QA     passo 2/4 — Tarefas pela API  ·  ✅ PASS
       2 (a)–(g) cobertos com harmless_tasks; L4, L10, L11

15:29  🔎 QA     passo 3/4 — SSE  ·  ✅ PASS
       3 (a)–(h) cobertos; L6 e L12 (diff) atendidas

15:29  🔎 QA     passo 4/4 — Documentação  ·  ✅ PASS
       docs/api.md, ADR-0020 + índice, §4 e fluxo 5.5, CHANGELOG; L7,
       L13, L14; sem nome nem e-mail real
