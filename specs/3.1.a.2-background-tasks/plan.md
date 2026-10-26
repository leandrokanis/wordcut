# Plan: Tarefas em segundo plano, `--wait` e `task`

**Issue**: 3.1.a.2
**Feature**: specs/3.1.a.2-background-tasks
**Data**: 2026-10-26

---

## Resumo

Cria o mecanismo de tarefas do core (ADR-0007): tabela `tasks`, registro de tipos de tarefa,
execução em primeiro plano ou em processo destacado que herda a trava, detecção de órfãs e
o serviço de consulta e espera. A CLI ganha `task list/show/wait`, um auxiliar para comandos
que lançam tarefa (`--wait`) e o `status` com as tarefas. Um tipo interno `diagnostic`
(dorme e reporta progresso) permite testar tudo sem YouTube nem GPU.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Componentes em escopo

- `packages/core/src/wordcut/` — `tasks/` (modelo, registro, execução, runner), migração,
  trava, serviço de tarefas e de status.
- `apps/cli/src/wordcut_cli/` — `task`, auxiliar de `--wait`, `status`.
- `packages/core/tests/`, `apps/cli/tests/`.

---

## Contexto de código

| Situação | Path |
|---|---|
| Criar | `packages/core/src/wordcut/db/migrations/0003_tasks.sql` — tabela `tasks` (kind, resource_type, resource_id, status, progress, progress_message, pid, started_at, finished_at, error_code, error_message, error_details, result) |
| Criar | `packages/core/src/wordcut/db/tasks.py` — repositório |
| Criar | `packages/core/src/wordcut/tasks/__init__.py` — `TaskKind`, `TaskContext` (`progress(fraction, message)`), registro `register(kind)` / `kind(name)` |
| Criar | `packages/core/src/wordcut/tasks/execution.py` — `start(home, kind, resource, params, *, detach, on_progress)`; em primeiro plano ou destacado |
| Criar | `packages/core/src/wordcut/tasks/runner.py` — ponto de entrada do processo destacado (`python -m wordcut.tasks.runner <task_id> <lock_fd>`) |
| Criar | `packages/core/src/wordcut/tasks/diagnostic.py` — tipo `diagnostic` (dorme, reporta progresso, falha sob pedido); não exposto na CLI |
| Criar | `packages/core/src/wordcut/service/tasks.py` — `list_tasks`, `show_task`, `wait_task(poll, on_progress)`, reconciliação de órfãs |
| Alterar | `packages/core/src/wordcut/lock.py` — `acquire(..., task_id=None)` grava `task_id` no dono; posse transferível para o filho por descritor herdado |
| Alterar | `packages/core/src/wordcut/service/status.py` — `lock.task_id` e `running_tasks` |
| Criar | `apps/cli/src/wordcut_cli/task.py` — `task list [--status] [--kind]`, `task show`, `task wait` |
| Criar | `apps/cli/src/wordcut_cli/tasks_support.py` — `add_wait_option(parser)` e `launch(ctx, start, wait)`: progresso no stderr, resultado no stdout, 130 no Ctrl+C |
| Alterar | `apps/cli/src/wordcut_cli/status.py` — mostra a tarefa e as em andamento |
| Criar | `packages/core/tests/test_tasks.py`, `packages/core/tests/test_task_detached.py`, `apps/cli/tests/test_task_command.py` |
| Alterar | `docs/architecture/README.md` (§4 e diagrama 5.1 se mudar), `CHANGELOG.md` |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python (core, cli) | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

Testes de processo destacado usam a fixture `wordcut_home` e limite de tempo (`conftest.py`).

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Atomicidade trava × lançamento | o pai adquire a trava, cria a tarefa, lança o filho com o descritor da trava em `pass_fds` e fecha o seu; o filho reescreve o dono com o próprio PID | Sem janela entre checar e travar; `busy` sai antes de criar tarefa (ADR-0006, ADR-0007) |
| Processo destacado | `subprocess.Popen([sys.executable, "-m", "wordcut.tasks.runner", id, fd], start_new_session=True, stdin=DEVNULL, stdout/stderr → <home>/tasks/<id>.log)` | Sobrevive ao fim da CLI e a SIGHUP do terminal |
| Tipos de tarefa | registro por nome em `wordcut.tasks`; módulos dos tipos importados pelo runner a partir de uma lista fixa no core | O filho reconstrói a tarefa só com o ID |
| Parâmetros e resultado | JSON nas colunas `params` e `result` | Simples; inspecionável |
| Progresso | `TaskContext.progress(fraction, message)` grava no banco (no máximo a cada 0,5 s ou quando a mensagem muda) e chama `on_progress` em primeiro plano | Espera por polling lê o banco; sem flood de escrita |
| Erro na tarefa | `WordcutError` → `error_code`/`message`/`details`; outra exceção → `internal_error` (traceback só no log) | Mesmo contrato da CLI |
| Órfãs | `running` com `pid` inexistente (`os.kill(pid, 0)`) → `failed`, `error_code = "interrupted"`, ao ler tarefa, listar ou `status` | FR-006; sem daemon |
| `interrupted` | novo código na tabela de erros, saída 1 | Tarefa morta não é erro de uso nem regra violada |
| Espera (`wait_task`) | polling a cada 0,5 s; termina em `succeeded` (saída 0) ou `failed` (saída do `error_code`) | Simples; funciona entre processos e contêineres |
| Ctrl+C | em primeiro plano: marca `failed`/`interrupted`, solta a trava, 130; em `task wait`: só para de esperar, 130 | docs/cli.md §6.5 |
| Saída do lançamento | sem `--wait`: `{"task_id", "kind", "status", "<resource_type>_id": N}` (ex.: `sermon_id`); com `--wait`: o `result` da tarefa | docs/cli.md §4.3, §6.2, §6.3 (decisão do orquestrador 9, rodada 1) |
| Tipo `diagnostic` | parâmetros `seconds` e `fail_with` (código); não aparece na CLI | Teste de ponta a ponta sem dependência externa |
| Coluna `params` (orquestrador 1) | a migração 0003 inclui `params` (JSON) | o filho reconstrói a tarefa só pelo ID |
| Fixture de tarefas destacadas (orquestrador 2) | fixture na raiz (`conftest.py`): prazo por `SIGALRM`, `os.killpg` e espera de cada tarefa lançada no teardown | nenhum processo órfão depois da suíte |
| Zumbi (orquestrador 3) | processo em estado `Z` (`/proc/<pid>/stat`) conta como morto; o lançador colhe o filho quando possível | `os.kill(pid, 0)` vê zumbi como vivo |
| Host (orquestrador 4) | a tarefa grava `host` (`socket.gethostname()`); órfã só é julgada pelo PID no mesmo host; tarefa cujo `task_id` é o dono atual da trava está sempre viva | PID de outro contêiner não diz nada |
| PID na criação (orquestrador 5) | a linha nasce com o PID do pai; `Popen.pid` é gravado antes de devolver | sem janela em que a tarefa pareça órfã |
| Ordem no fim (orquestrador 6) | o filho (e o primeiro plano) solta a trava **antes** de gravar o estado final; `wait` só termina no estado final | `task wait N && <outra>` sem `busy` espúrio |
| Tipo sem trava (orquestrador 7) | `TaskKind.needs_lock`; teste com um tipo sem trava enquanto `lock_owner` segura a trava | borda do spec (`suggest`) |
| `task_id` no dono (orquestrador 8) | `LockHolder.task_id`, refletido nos `details` do `busy` | docs/cli.md §5.2, §5.3 |
| ADR (orquestrador 10) | ADR-0013 "Trava herdada pelo processo da tarefa" complementa a ADR-0007 sem editá-la; índice e `docs/architecture/README.md` §4 e §5.1 | CONTRIBUTING.md §3.1 |
| Ctrl+C e progresso (orquestrador 11) | nos testes, `threading.Timer` + `_thread.interrupt_main()`; linha `[<kind>] <mensagem> <pct>%` no stderr, suprimida por `ctx.quiet` | docs/cli.md §4.5 |
| `diagnostic` (orquestrador 12) | fica no core, sem `CHECK` em `kind` que o barre e sem exposição na CLI | o runner precisa importá-lo |
| Ordem de `task list` (orquestrador 13) | mais recentes primeiro, `started_at DESC, id DESC`, sem limite | ordem estável |

---

## Ordem de implementação

- [x] **Passo 1 — Modelo e execução em primeiro plano** — migração, repositório, registro,
  `TaskContext`, `start(detach=False)` com trava, progresso e erros; tipo `diagnostic`.
- [x] **Passo 2 — Processo destacado** — runner, herança do descritor da trava, log por tarefa,
  `busy` antes de criar a tarefa.
- [x] **Passo 3 — Consulta, espera e órfãs** — `service/tasks.py` com `list`, `show`, `wait`,
  reconciliação; `interrupted` na tabela de erros.
- [x] **Passo 4 — CLI** — `task list/show/wait`, `tasks_support.launch` com `--wait` e 130,
  `status` com `task_id` e tarefas em andamento.
- [x] **Passo 5 — Documentação** — `docs/architecture/README.md` (§4; diagrama 5.1 coerente
  com a herança da trava), CHANGELOG, docs/cli.md §5.3 com `interrupted`.

---

## Riscos

- **Teste de processo destacado instável**: limite de tempo da fixture e espera por estado no
  banco em vez de `sleep` fixo.
- **PID reaproveitado** marcar órfã como viva: aceito no MVP; anotado. Mitigado em parte: tarefa
  com trava cujo `task_id` é o dono atual da trava é viva, e a do dono morto perde a trava.
- **Tarefa de outro host** (outro contêiner) nunca é julgada órfã pelo PID: fica `running` até o
  próprio processo gravar o fim.

---

## Fora de escopo

- Operações reais (`process`, `suggest`, `render`).
- Cancelamento de tarefa.

---

## Verificação

- [x] Lançar `diagnostic` destacado → volta na hora com `task_id` e `running`; tarefa termina
  `succeeded` sozinha; trava livre depois.
- [x] Durante a tarefa destacada, `status` mostra `held: true` com o `task_id` e a tarefa em
  `running_tasks`.
- [x] Com a trava ocupada, lançar outra tarefa com trava → `busy` (saída 4), nenhuma tarefa nova
  no banco, nenhum processo lançado.
- [x] `--wait` (via `launch`) → progresso no stderr, resultado no stdout, saída 0; tarefa que
  falha com `fail_with` → saída do código.
- [x] `task wait <id>` de tarefa destacada → termina com o resultado e a saída da tarefa.
- [x] Matar o processo da tarefa → próxima leitura mostra `failed`/`interrupted`.
- [x] Ctrl+C em primeiro plano → `failed`/`interrupted`, trava livre, saída 130.
- [x] `task show` de ID inexistente → `not_found`.
- [x] Quality gates limpos.
