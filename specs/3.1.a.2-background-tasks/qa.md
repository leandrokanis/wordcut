# QA — 3.1.a.2 — Tarefas em segundo plano, `--wait` e `task`

## Plano de QA — 2026-10-26

**baseline_commit**: 5249c8b0d1e7d5b92aa2ddfe268973924c089c93
**Componentes em escopo**: `packages/core/src/wordcut/` (`db/migrations/0003_tasks.sql`,
`db/tasks.py`, `tasks/` — `__init__.py`, `execution.py`, `runner.py`, `diagnostic.py` —,
`service/tasks.py`, `service/status.py`, `lock.py`, `errors.py`); `apps/cli/src/wordcut_cli/`
(`task.py`, `tasks_support.py`, `status.py`, `__init__.py` para o registro); `conftest.py` da
raiz (fixture de tarefas destacadas); `packages/core/tests/`, `apps/cli/tests/`; documentação
(`docs/architecture/README.md` §4 e §5.1, `docs/cli.md` §5.3 e, se o formato mudar, §6.2/§10,
`CHANGELOG.md`).
**Suítes que valem como prova** (da raiz, após `uv sync --all-packages`):
- Python (core, cli): `uv run pytest -q`; por arquivo, `uv run pytest <arquivo> -q`.
- Checagem estática: `uv run ruff check . && uv run ruff format --check . && uv run mypy`.
- Processos órfãos: antes e depois da suíte, `pgrep -af 'wordcut.tasks.runner'` vazio; a
  suíte inteira termina sem pendurar (limite externo `timeout 600 uv run pytest -q`).
- Estabilidade: os três arquivos novos rodados 5 vezes seguidas
  (`for i in 1 2 3 4 5; do uv run pytest packages/core/tests/test_task_detached.py apps/cli/tests/test_task_command.py -q || break; done`).
- Empacotamento: `uv build --package wordcut-core` e conferir `0003_tasks.sql` e
  `wordcut/tasks/runner.py` no wheel.
- Estado dos gates no baseline (para separar dívida antiga de regressão): os mesmos comandos
  numa `git worktree` temporária em `5249c8b`, fora da árvore de trabalho.

Fontes da barra: spec.md e plan.md desta pasta; docs/cli.md §4.3–§4.5, §5, §6, §10;
ADR-0006, ADR-0007; código do baseline (`lock.py`, `errors.py`, `home.py`, `db/`,
`service/status.py`, `wordcut_cli/contract.py`, `wordcut_cli/status.py`, `conftest.py`);
CLAUDE.md e CONTRIBUTING.md. Sem rastreador: critérios dos cenários do spec.md e da
Verificação do plan.md. Diário em `tdd.md` (`## Plano de QA`).

Interpretações da barra (execução automatizada, opção mais conservadora, registradas):
- **Processos destacados nos testes**: todo teste que lança tarefa destacada usa uma fixture
  da raiz que (1) aplica limite de tempo (`SIGALRM`, como `lock_owner`) e (2) no teardown mata
  o grupo de cada tarefa lançada (`os.killpg`, o filho é líder de sessão) e o colhe
  (`waitpid`). Teste que pendura conta como vermelho; processo `wordcut.tasks.runner` vivo
  depois da suíte é FAIL do passo 2. A fixture `wordcut_home` sozinha não tem limite de tempo
  no baseline — usá-la sem a nova fixture não atende a barra.
- **Espera nos testes**: por estado no banco/trava com prazo (polling), nunca `sleep` fixo como
  única sincronização; `diagnostic` com `seconds` pequeno (≤ 2 s) no caminho feliz.
- **Trava livre depois**: assim que `wait_task` (ou `task wait`) devolve `succeeded`/`failed`,
  a primeira leitura de `holder()` é `None` — sem polling. É o que permite encadear
  `task wait 9 && <outra operação com trava>` sem `busy` espúrio (história 3.1.a.2).
- **`busy`**: o `details` traz o `task_id` do dono quando a trava é de tarefa (docs/cli.md
  §5.2, §5.3 "details traz a tarefa"); dono sem tarefa (fixture `lock_owner`) → `task_id`
  nulo/ausente, sem quebrar.
- **Sem processo lançado no `busy`**: provado por espião em `subprocess.Popen` no módulo de
  execução (`monkeypatch` que falha se chamado) e por contagem de linhas de `tasks`
  antes/depois; ausência de `<home>/tasks/*.log` novo como reforço.
- **`--wait` pela CLI**: `diagnostic` não aparece na CLI; a prova passa por um comando de teste
  registrado com `add_command` + `add_wait_option` + `launch` num parser próprio e rodado por
  `execute(parser, argv)`, para provar canal (stdout/stderr), saída e 130 pelo contrato real.
  Chamar `launch` fora do contrato prova só metade (PARCIAL).
- **Ctrl+C em primeiro plano**: provocado com a tarefa em execução (p. ex.
  `threading.Timer` + `_thread.interrupt_main()` durante um `diagnostic` longo), não por
  `KeyboardInterrupt` lançado antes do `start`; exige linha `failed`/`interrupted` com
  `finished_at`, trava livre e saída 130.
- **Ctrl+C em `task wait`**: a espera para com 130 e a tarefa destacada continua `running` e
  termina `succeeded` depois.
- **`--quiet`**: com `--wait` e `task wait`, suprime as linhas de progresso no stderr
  (docs/cli.md §4.5); o resultado no stdout não muda.
- **Formato da saída do lançamento**: vale o plano (`task_id`, `kind`, `status`,
  `resource_type`, `resource_id`) desde que o Passo 5 deixe docs/cli.md §6.2 coerente com o
  código (o exemplo atual traz `sermon_id`); incoerência entre doc e código → Passo 5 PARCIAL.
- **Erro de tarefa na CLI**: `--wait`/`task wait` de tarefa `failed` → stdout com
  `{"error": {"code", "message", "details"?}}` (com `--json`) e saída = `EXIT_CODES[code]`;
  `interrupted` → 1.
- **Tipo `diagnostic` no core**: aceito como no plano (o runner precisa importá-lo), apesar do
  pressuposto do spec ("registrado só nos testes"); não pode aparecer em `wordcut --help` nem
  em nenhum comando da CLI.
- **Testes existentes** (`test_status.py`, `test_status_command.py`, `test_errors.py`,
  `test_cli.py`) podem mudar só para acrescentar `lock.task_id`, `running_tasks`, o código
  `interrupted` e o comando `task`; as asserções anteriores ficam.
- ADR-0006 e ADR-0007 aceitas não são editadas no lugar.

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Modelo e execução em primeiro plano | (a) Migração `0003_tasks.sql` cria `tasks` com as colunas do plano (inclusive `params` e `result` JSON), `user_version` = 3; banco no esquema 2 com pregações migra sem perder dados. (b) Repositório grava/lê a tarefa com todos os campos do FR-001. (c) Registro: `register(kind)`/`kind(name)`; nome desconhecido falha. (d) `start(home, kind, resource, params, detach=False, on_progress)`: tipo com trava adquire a trava com `task_id` no dono durante a execução e a solta no fim; cria a linha `running` com `pid` = processo atual e `started_at`; termina `succeeded` com `result` e `finished_at`. (e) Progresso: `TaskContext.progress(fraction, message)` chama `on_progress` e grava `progress`/`progress_message` no banco (lido de outra conexão durante a execução). (f) `fail_with=<código>` → `failed` com `error_code`/`message`/`details` e a exceção sobe como `WordcutError` do mesmo código. (g) Exceção não `WordcutError` → `failed`/`internal_error`, sem traceback no banco. (h) Trava ocupada → `busy` antes de criar a linha. | `packages/core/tests/test_tasks.py` pela interface pública (`start`, `register`/`kind`, repositório) com `wordcut_home`; leitura de `PRAGMA user_version` e `PRAGMA table_info(tasks)`; `holder()` lido dentro do `on_progress` (trava com `task_id`) e depois do `start` (`None`); banco antigo pré-criado com `user_version` 2 e linhas em `sermons`. Mutações exigidas: não gravar progresso no banco; `internal_error` com a mensagem da exceção original; criar a linha antes de adquirir a trava; não soltar a trava em falha. |
| 2 — Processo destacado | (a) `start(..., detach=True)` volta na hora (bem antes de `seconds`) com a tarefa `running`. (b) O filho roda em sessão própria (`os.getsid(pid) == pid`) com `stdin` nulo e saída em `<home>/tasks/<id>.log`. (c) Durante a execução, `holder()` (lido pelo teste) mostra `pid` = `pid` do filho gravado na tarefa e o `task_id`. (d) O processo que lançou não segura mais a trava: termina a tarefa e a primeira leitura de `holder()` é `None`. (e) A tarefa termina `succeeded` sozinha, com `result`. (f) Trava ocupada → `busy` (com `details.task_id` quando o dono é tarefa), nenhuma linha nova e `Popen` não chamado. (g) `internal_error` no filho: traceback só no log. (h) Nenhum processo `wordcut.tasks.runner` sobra depois do teste. | `packages/core/tests/test_task_detached.py` com a fixture de limite de tempo e limpeza; espera por estado no banco com prazo; `os.getsid`; leitura do `.log`; espião em `subprocess.Popen` para o `busy`; `pgrep -af wordcut.tasks.runner` antes/depois da suíte na rodada. Mutações exigidas: sem `start_new_session` (vermelha pelo `getsid`); o pai não fecha o descritor (vermelha em "trava livre depois"); o filho não reescreve o dono (vermelha no `pid` do dono); `busy` checado depois de criar a tarefa (vermelha na contagem). |
| 3 — Consulta, espera e órfãs | (a) `list_tasks` com filtros `status` e `kind`, ordem estável (mais recentes primeiro). (b) `show_task` com tipo, estado, recurso, início, fim, progresso, erro e resultado; ID inexistente → `not_found` (saída 3) com `details` do ID. (c) `wait_task` devolve `succeeded` com `result`, ou levanta o `WordcutError` do `error_code` da tarefa; tarefa já terminada volta na hora; chama `on_progress` a cada mudança. (d) Órfã: `running` com processo morto → `failed`, `error_code = "interrupted"`, `finished_at` gravado, em `show`, `list`, `wait` e `status`; processo vivo (inclusive `PermissionError` no `os.kill`) não é órfão. (e) `interrupted` em `EXIT_CODES` com saída 1. | `packages/core/tests/test_tasks.py` (serviço sobre linhas criadas por `start` ou pelo repositório) e `test_task_detached.py` para órfã real: matar o grupo do filho (`os.killpg`, `SIGKILL`), colher (`waitpid`) e ler. Linha `running` com `pid` de processo inexistente (filho já colhido) como caso barato. `test_errors.py` com `interrupted: 1`. Mutações exigidas: sem reconciliação em `show` (vermelha); `wait_task` devolve sucesso em `failed` (vermelha); `interrupted` → 5 (vermelha). |
| 4 — CLI | (a) `task list [--status S] [--kind K]` → `{"items": [...]}`; valor fora das escolhas → `invalid_argument` (2). (b) `task show <id>` → objeto da tarefa; inexistente → `not_found` (3) com objeto de erro. (c) `task wait <id>` de tarefa destacada → progresso no stderr, resultado no stdout, saída 0; tarefa `failed` → objeto de erro e saída do código; Ctrl+C → 130 e a tarefa segue. (d) `launch` sem `--wait` → `{"task_id","kind","status": "running","resource_type","resource_id"}` na hora; com `--wait` → progresso no stderr (`[<kind>] …`), `result` no stdout, saída 0; `fail_with` → saída do código; Ctrl+C → 130, `failed`/`interrupted`, trava livre. (e) `--quiet` sem linhas de progresso. (f) `status` com `lock.task_id` e `running_tasks` (JSON) e texto em português que cita a tarefa e as em andamento; trava livre → `{"lock": {"held": false}, "running_tasks": [...]}`. (g) `--json` antes ou depois dá o mesmo resultado em `task`. | `apps/cli/tests/test_task_command.py` por `main(argv)` com `capsys` (`json.loads` do stdout inteiro) e por `execute(parser, argv)` com o comando de teste que usa `add_wait_option` + `launch`; tarefas destacadas lançadas pelo core com a fixture de limite e limpeza; `test_status_command.py` ampliado. Mutações exigidas: progresso no stdout (vermelha pelo `json.loads`); `--quiet` ignorado; `task wait` com Ctrl+C marcando `failed` (vermelha). |
| 5 — Documentação | `docs/architecture/README.md` §4 com Tarefas "existe" e o diagrama §5.1 coerente com o pai que trava e o filho que herda; `docs/cli.md` §5.3 com `interrupted` (saída 1) e §6.2/§10 coerentes com o formato implementado; `CHANGELOG.md` com `task list/show/wait`, `--wait` e `interrupted`; registro da mudança de ADR-0007 (o filho herda a trava em vez de adquiri-la) por ADR nova ou nota, sem editar a aceita. Texto em português, sem segredo nem dado pessoal. | Leitura de `git diff 5249c8b -- docs/ CHANGELOG.md README.md`; conferir que §5.3 bate com `EXIT_CODES` e que o JSON de §6.2/§10 bate com os testes do Passo 4. |

| Critério de aceite | O que o cobre |
|---|---|
| Spec — lançar e voltar na hora (`task_id`, `kind`, `running`; processo destacado segura a trava) | `test_task_detached.py` (volta antes de `seconds`, `getsid`, dono = filho) + `test_task_command.py` (`launch` sem `--wait`) |
| Spec — esperar com `--wait` (progresso no stderr, resultado no stdout, 0 ou código do erro) | `test_task_command.py` pelo comando de teste via `execute` (sucesso e `fail_with`) |
| Spec — esperar tarefa lançada (`task wait <id>` com resultado e saída da tarefa) | `test_task_command.py` com tarefa destacada (sucesso e falha) |
| Spec — máquina ocupada (`busy`, 4, sem processo nem tarefa) | `test_task_detached.py`/`test_tasks.py` (contagem de linhas, espião em `Popen`, `details.task_id`) + `test_task_command.py` (saída 4 pelo contrato) |
| Spec — tarefa órfã (`failed` com erro de interrupção em consulta e `status`) | `test_task_detached.py` (kill do grupo, `show` e `status` → `failed`/`interrupted`) |
| Spec — status mostra a tarefa (`task_id` na trava e lista em andamento) | `test_status.py` + `test_status_command.py` com tarefa destacada em execução |
| Borda — Ctrl+C no `--wait` → `failed`, 130 | `test_task_command.py` com interrupção durante a execução |
| Borda — Ctrl+C no `task wait` só para a espera | `test_task_command.py` (130, tarefa segue e termina `succeeded`) |
| Borda — tarefa sem trava roda com a máquina ocupada | teste com tipo sem trava (registrado no teste ou `diagnostic` configurável) enquanto `lock_owner` segura; sem esse teste, ❌ |
| Borda — `task show` de ID inexistente → `not_found` | `test_task_command.py` (saída 3, objeto de erro) |
| FR-001 — campos da tarefa no SQLite | `test_tasks.py` (`PRAGMA table_info`, ida e volta pelo repositório) |
| FR-002 — sessão própria e trava até terminar | `test_task_detached.py` (`getsid`, dono durante a execução, livre depois) |
| FR-003 — trava antes da tarefa; ocupada → `busy` | `test_tasks.py`/`test_task_detached.py` (contagem de linhas) |
| FR-004 — `--wait` em primeiro plano com progresso no stderr | `test_task_command.py` (`pid` da tarefa = processo do teste; stderr com `[diagnostic]`) |
| FR-005 — `task list/show/wait`; `wait` com a saída da tarefa | `test_task_command.py` |
| FR-006 — `running` sem processo → `failed` na leitura | `test_tasks.py` + `test_task_detached.py` |
| FR-007 — `status` com `task_id` e tarefas em andamento | `test_status.py` + `test_status_command.py` |
| Verificação — destacada volta na hora, termina `succeeded`, trava livre | `test_task_detached.py` (primeira leitura de `holder()` após o fim = `None`) |
| Verificação — `status` com `held: true`, `task_id` e `running_tasks` | `test_status_command.py` |
| Verificação — trava ocupada → `busy` (4), sem tarefa nova, sem processo | ver "máquina ocupada" |
| Verificação — `--wait` via `launch`: stderr/stdout/0; `fail_with` → código | ver "esperar com `--wait`" |
| Verificação — `task wait <id>` com resultado e saída | ver "esperar tarefa lançada" |
| Verificação — matar o processo → `failed`/`interrupted` | ver "tarefa órfã" |
| Verificação — Ctrl+C em primeiro plano → `failed`/`interrupted`, trava livre, 130 | ver borda Ctrl+C no `--wait` |
| Verificação — `task show` inexistente → `not_found` | ver borda |
| Verificação — quality gates limpos | `uv run pytest -q`, `ruff check`, `ruff format --check`, `mypy` verdes; `pgrep` vazio; 5 repetições estáveis |

## Rodada 1 — 2026-10-26 — working tree sobre 5249c8b

**baseline_commit**: 5249c8b0d1e7d5b92aa2ddfe268973924c089c93
**Componentes avaliados**: `packages/core` (migração 0003, `db/tasks.py`, `tasks/`, `service/tasks.py`,
`service/status.py`, `lock.py`, `errors.py`, `home.py`), `apps/cli` (`task.py`, `tasks_support.py`,
`status.py`, `__init__.py`), `conftest.py` da raiz, documentação (ADR-0013, `docs/adr/README.md`,
`docs/architecture/README.md`, `docs/cli.md`, `CHANGELOG.md`, `README.md`)
**Suítes**: Python (core, cli) ✅ (386 / 0 falhas; baseline 320 / 0) · `ruff check` ✅ ·
`ruff format --check` ✅ · `mypy` ✅ (iguais no baseline) · `pgrep -af wordcut.tasks.runner` vazio
antes e depois da suíte, das repetições e das mutações · 5 repetições dos três arquivos de tarefa
✅ (56 / 0 em cada) · wheel do core com `0003_tasks.sql` e `wordcut/tasks/runner.py` ✅

Mutações: 14 de 14 exigidas pela barra mortas; 10 de 12 sobre as decisões do orquestrador mortas.
Rodadas numa cópia da árvore no scratchpad (a permissão do ambiente recusou mutar os arquivos não
commitados no lugar); a árvore real foi conferida por sha256 depois e está intacta. Detalhe no
`tdd.md`, `## Rodada 1 · QA`.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Modelo e execução em primeiro plano | PASS | `test_tasks_repository.py` (colunas FR-001 com `params` e `host`, `user_version` 3, esquema 2 com pregações migra, ida e volta, ordem `started_at DESC, id DESC`); `test_tasks.py` (registro, trava com `task_id` lida dentro da tarefa e livre depois, progresso no banco antes do ouvinte, limite de gravação, `fail_with`, `internal_error` sem o texto, `busy` antes da linha, `details.task_id`, tipo `needs_lock=False` com `lock_owner`). Mutações exigidas mortas |
| 2 — Processo destacado | PASS | `test_task_detached.py` com a fixture `detached_tasks` (`SIGALRM`, `killpg`, `wait`): volta < 2 s, `getsid == pid`, `stdin` em `/dev/null`, dono = PID do filho com `task_id`, trava livre na 1ª leitura após o fim, traceback só no log, `busy` com espião em `Popen`, sem linha nem log, `Popen` falho → `failed`, PID do filho na tarefa devolvida. Mutações `start_new_session`, pai com cópia do descritor, dono não reescrito e `busy` depois da linha: mortas |
| 3 — Consulta, espera e órfãs | PASS | `test_tasks.py` (`show_task` com `sermon_id`, `not_found` 3 com `details.task_id`, filtros e ordem, `wait_task` sucesso/falha, órfã em `show`/`list`/`wait` com `interrupted` 1, PID de outro usuário, outro host, dono da trava, zumbi); `test_task_detached.py` (órfã real por `killpg` + `wait`; `wait_task` com progresso e trava livre antes); `test_status.py` (órfã some de `running_tasks`); `test_errors.py` (`interrupted: 1`) |
| 4 — CLI | PASS | `test_task_command.py` por `main` e por `execute` com comando de teste `add_wait_option` + `launch`: `task list/show/wait`, escolhas inválidas → 2, `--json` antes/depois, `diagnostic` fora do `--help` e do `--kind`, `task wait` (stderr `[diagnostic] … %`, stdout JSON, falha → 6, Ctrl+C → 130 e a tarefa termina `succeeded`, `--quiet`), `launch` sem `--wait` → `{"task_id","kind","status","sermon_id"}`, com `--wait` (pid = pytest), `fail_with` → 5, Ctrl+C → 130 com `failed`/`interrupted` e trava livre, `busy` → 4 sem tarefa; `test_status_command.py` (JSON e texto com a tarefa e as em andamento) |
| 5 — Documentação | PASS | ADR-0013 nova, ADR-0007 intacta, índice; arquitetura §4 (Tarefas existe) e §5.1 (lançador trava, filho herda, solta antes de gravar o fim); `docs/cli.md` §5.1/§5.3 com `interrupted` 1 = `EXIT_CODES`, §6.2 (`sermon_id`) = saída testada, §6.5, §10, §14 (`tasks/<id>.log`); CHANGELOG e README. Português, sem segredo nem dado pessoal |

### Critérios de aceite
- ✅ Spec — lançar e voltar na hora — `test_detached_task_returns_at_once_while_it_keeps_running`, `test_detached_task_process_holds_the_lock_in_its_own_name`, `test_launch_without_wait_answers_at_once_with_the_running_task`
- ✅ Spec — esperar com `--wait` — `test_launch_with_wait_runs_here_with_progress_on_stderr_and_the_result_on_stdout`, `test_launch_with_wait_of_a_failing_task_exits_with_its_error_code`
- ✅ Spec — esperar tarefa lançada — `test_task_wait_shows_progress_on_stderr_and_the_result_on_stdout`, `test_task_wait_of_a_failed_task_prints_its_error_and_exits_with_its_code`
- ✅ Spec — máquina ocupada — `test_busy_machine_launches_no_process_and_records_no_task`, `test_busy_machine_refuses_a_locking_task_before_recording_it`, `test_busy_refusal_names_the_detached_task_holding_the_lock`, `test_launch_while_the_machine_is_busy_exits_4_without_a_task`
- ✅ Spec — tarefa órfã — `test_killed_task_process_is_shown_failed_as_interrupted_at_the_next_read`, `test_status_shows_no_running_task_whose_process_is_gone`
- ✅ Spec — status mostra a tarefa — `test_status_lists_the_running_detached_task_and_names_it_as_the_lock_holder`, `test_status_names_the_task_holding_the_lock_and_lists_the_running_ones`, `test_status_without_json_cites_the_task_and_the_running_tasks`
- ✅ Borda — Ctrl+C no `--wait` → `failed`, 130 — `test_ctrl_c_in_launch_with_wait_interrupts_the_task_and_exits_130`, `test_ctrl_c_during_a_foreground_task_ends_it_interrupted_and_frees_the_lock`
- ✅ Borda — Ctrl+C no `task wait` só para a espera — `test_ctrl_c_in_task_wait_stops_waiting_and_leaves_the_task_running`
- ✅ Borda — tarefa sem trava com a máquina ocupada — `test_task_without_lock_runs_while_another_process_holds_the_lock`
- ✅ Borda — `task show` inexistente → `not_found` — `test_task_show_of_a_missing_task_is_not_found_with_exit_3`, `test_showing_a_task_that_does_not_exist_is_not_found`
- ✅ FR-001 — `test_migration_creates_the_tasks_table_with_every_task_field`, `test_inserted_task_is_read_back_running_with_every_field`
- ✅ FR-002 — `test_detached_task_runs_in_a_session_of_its_own_without_input`, `test_detached_task_ends_succeeded_by_itself_and_frees_the_lock`
- ✅ FR-003 — `test_busy_machine_refuses_a_locking_task_before_recording_it`, `test_busy_machine_launches_no_process_and_records_no_task`
- ✅ FR-004 — `test_launch_with_wait_runs_here_with_progress_on_stderr_and_the_result_on_stdout`
- ✅ FR-005 — `test_task_list_*`, `test_task_show_*`, `test_task_wait_*`
- ✅ FR-006 — `test_running_task_whose_process_is_gone_is_*`, `test_killed_task_process_is_shown_failed_as_interrupted_at_the_next_read`
- ✅ FR-007 — `test_status_lists_the_running_detached_task_and_names_it_as_the_lock_holder`, `test_status_names_the_task_holding_the_lock_and_lists_the_running_ones`
- ✅ Verificação — destacada volta na hora, `succeeded`, trava livre — ver FR-002
- ✅ Verificação — `status` com `held: true`, `task_id`, `running_tasks` — ver FR-007
- ✅ Verificação — `busy` (4), sem tarefa, sem processo — ver "máquina ocupada"
- ✅ Verificação — `--wait` via `launch` — ver "esperar com `--wait`"
- ✅ Verificação — `task wait <id>` — ver "esperar tarefa lançada"
- ✅ Verificação — matar o processo → `failed`/`interrupted` — ver "tarefa órfã"
- ✅ Verificação — Ctrl+C em primeiro plano → `failed`/`interrupted`, trava livre, 130 — ver borda
- ✅ Verificação — `task show` inexistente → `not_found` — ver borda
- ✅ Verificação — quality gates limpos — suíte, ruff, format, mypy, `pgrep` vazio, 5 repetições

### Fato do implementador: `test_sermons_repository.py` de `== 2` para `>= 2`
Aceito. A própria barra exige `user_version` 3 (passo 1 a), o que torna `== 2` impossível; a
cláusula "testes existentes podem mudar só …" não previu este arquivo (lacuna da barra, não
desvio). A intenção do teste fica (0002 aplicada e `sermons` legível) e o 3 exato está provado em
`test_migration_creates_the_tasks_table_with_every_task_field`. Resta o nome
`test_new_database_has_schema_version_2_…`, que não diz mais o que a asserção prova (leve).

### Observações (não mudam o veredito; fora das mutações exigidas)
- Decisão 6 (trava solta antes do estado final): o código segue a ordem no filho (`resume`) e
  em primeiro plano (`start`). O teste mata o mutante com atraso de 0,3 s entre gravar e soltar,
  mas não o mutante realista (gravar e soltar em seguida, 3 de 3 vivos) nem a inversão em
  primeiro plano: a janela é de microssegundos. A ordem está provada pela leitura do código, não
  por teste.
- `execution.py` `_launch`: se `Popen` falha, grava `failed` ainda com a trava (dentro do `with`),
  ao contrário da decisão 6; borda sem efeito prático no teste.
- `wait_task` agora chama `holder()` a cada 0,5 s (reconciliação); `holder()` (do baseline) testa
  a trava com `LOCK_SH` momentâneo, que pode dar `busy` espúrio a um `start` concorrente nessa
  janela. Risco pequeno, anterior a este item, mais frequente agora.
- Política de comentários (CONTRIBUTING.md §5): os 13 comentários novos são de intenção,
  alerta, referência ou restrição externa (`proc(5)`), em inglês; sem diretiva de ferramenta
  nova. ✅

### Veredito geral: PASS
Cinco passos `[x]` PASS, 26/26 critérios cobertos, suítes e checagens verdes, sem processo
`wordcut.tasks.runner` vivo; observações acima não bloqueiam.
