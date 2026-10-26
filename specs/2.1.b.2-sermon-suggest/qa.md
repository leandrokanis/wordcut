# QA — 2.1.b.2 — Pedir nova sugestão de cortes (`sermon suggest`)

## Plano de QA — 2026-10-26

**baseline_commit**: 470a85696cd41a5bb662dabb9aa9cc3b09c5f94f
**Componentes em escopo**:
- `packages/core` — `wordcut.tasks.suggest` (novo), `wordcut.tasks` (`BUILTIN_KIND_MODULES`),
  `wordcut.service.suggestion` (novo), `wordcut.suggestion` (`suggest`), `wordcut.db.cuts`.
- `apps/cli` — `wordcut_cli.sermon` (`sermon suggest`).
- Documentação — `CHANGELOG.md`, `docs/cli.md` §5.3 e §7.6.

**Suítes que valem como prova** (da raiz, depois de `uv sync --all-packages`):
- core: `uv run pytest packages/core/tests -q`
- cli: `uv run pytest apps/cli/tests -q`
- tudo: `uv run pytest -q`
- estática: `uv run ruff check . && uv run ruff format --check . && uv run mypy`

**Regras da barra, válidas para todos os passos**:
- O LLM é sempre dublê: `monkeypatch.setattr(suggestion, "default_model", <fábrica>)`, como em
  `packages/core/tests/test_process_suggests.py`. A fixture `no_real_llm` (`conftest.py`) só
  protege o processo do pytest. Um processo destacado de verdade (`detached_tasks`) não vê o
  dublê e chamaria o OpenRouter se houvesse chave. Por isso, todo teste sem `--wait` usa
  `harmless_tasks`. Um teste que rode o `runner` destacado com chave configurada é FAIL
  imediato do passo.
- Uma pré-condição recusada não cria tarefa: o teste confere `tasks.newest_first` (ou
  `task list --json`) vazio.
- "Cortes intactos" quer dizer mesmos IDs e mesmos campos (`cuts.of_sermon` igual antes e
  depois), não só a mesma contagem.
- Para montar o cenário, os cortes `chosen` e `discarded` entram por `cuts.insert_many` e o
  `edited = 1` por `UPDATE` direto. Ainda não há serviço para escolher, descartar ou editar
  (1.1.e.1 e 1.1.f.* não foram implementados). Esse SQL só vale no *arrange*. A verificação
  passa pela interface pública (`suggest`, `start_suggestion`, `sermon show`, CLI).
- Mutação manual cobrada (desfeita na hora): cada 🧬 abaixo precisa ficar **vermelha**.

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Substituição no core | (a) Com `replace_suggested=True` e resposta válida: os `suggested` com `edited = 0` da pregação somem; `suggested` editado, `chosen` e `discarded` ficam com os mesmos IDs e campos; os novos entram `suggested`, `source = llm`, `preset_id` do preset usado; `suggestion_error` fica limpo. (b) A falha não toca em nenhum corte: duas respostas fora do esquema (`llm_error`), erro de transporte (`llm_error`) e `llm_not_configured`. (c) Os sugeridos de **outra** pregação ficam. (d) Sem `replace_suggested`, o comportamento do `process` não muda. (e) Apagar e inserir acontecem numa só transação, depois da resposta válida. | pytest core, por `suggestion.suggest(...)` com `ScriptedModel` em `packages/core/tests/test_suggest_task.py` (ou `test_suggestion.py`). Função nova de `db.cuts` em `test_cuts_repository.py`, pela função pública. (d) `test_process_suggests.py` e `test_suggestion.py` verdes sem alteração de asserção. 🧬 tirar o filtro `edited = 0` · tirar o filtro `status = 'suggested'` · tirar o filtro `sermon_id` · apagar antes de chamar o LLM. |
| 2 — Tipo de tarefa e serviço | (a) O tipo `suggest` está em `BUILTIN_KIND_MODULES` com `needs_lock=False` e é resolvido num interpretador novo, que é o que o `runner` destacado faz. (b) Com a trava presa por outro processo (`lock_owner`), `start_suggestion(detach=False)` termina `succeeded` e o dono da trava continua o mesmo. (c) As pré-condições recusam **antes** de criar a tarefa: pregação inexistente → `not_found` (`details.sermon_id`); não `processed` (`created`, `trimmed`, `processing`, `failed`) → `sermon_not_processed` (`details.sermon_id`, `status`); preset inexistente → `not_found` (`details.preset_id`). (d) Sem `preset_id`, o `system` recebido pelo dublê é `build_prompt(default_preset(...))`; com `preset_id=p`, é `build_prompt(show_preset(..., p))`, e os cortes novos têm `preset_id = p`. (e) Exclusão por pregação: uma tarefa `suggest` `running` da mesma pregação → `busy` com `details.task_id` dela, sem tarefa nova. Uma `suggest` `running` de outra pregação, uma `suggest` terminada ou uma órfã (processo morto, reconciliada) não bloqueiam. (f) Falha do LLM → tarefa `failed` com `error_code = llm_error`; `wait_task` levanta esse erro. (g) O resultado gravado na tarefa tem o formato decidido (ver lacuna L2). | pytest core em `packages/core/tests/test_suggest_task.py`, pela interface pública `start_suggestion` e `service.tasks`. (a) `subprocess.run([sys.executable, "-c", "from wordcut.tasks import kind; assert not kind('suggest').needs_lock"])`. (e) A tarefa viva vem de `start_suggestion(detach=True)` com `harmless_tasks`; a órfã, de uma tarefa com PID morto. 🧬 tirar `wordcut.tasks.suggest` de `BUILTIN_KIND_MODULES` · `needs_lock=True` · ignorar `preset_id` (usar sempre o padrão) · tirar o `reconcile` da exclusão · tirar o filtro de recurso da exclusão. |
| 3 — CLI | (a) `sermon suggest <id> --preset p --wait --json` devolve saída 0 e um único JSON no stdout com o resultado; progresso `[suggest] …` no stderr, que `--quiet` cala. (b) Sem `--wait`, a resposta é `{"task_id", "kind": "suggest", "status": "running", "sermon_id"}` com saída 0. (c) Os códigos de saída seguem o contrato: `sermon_not_processed` 5, `not_found` 3 (pregação e preset), `llm_not_configured` 5, `llm_error` 6, `busy` 4. (d) Com `lock_owner` segurando a trava, saída 0. (e) O `--help` de `sermon suggest` diz "administrador" e está em português (FR-004). (f) Sem `--json`, a saída é legível, tanto a da tarefa lançada quanto a do resultado. (g) Nenhuma saída, de sucesso ou de erro, contém a chave sentinela. | pytest cli em `apps/cli/tests/test_sermon_suggest_command.py`, com `main([...])` e `capsys`, como em `test_sermon_process_command.py`. (b) com `harmless_tasks`. (d) com a fixture `lock_owner`. (e) asserção sobre a ajuda do subcomando. 🧬 trocar `wait=args.wait` por `False` · tirar o repasse de `--preset`. |
| 4 — Documentação | `CHANGELOG.md` ganha a entrada de `sermon suggest` em `[Não lançado]`. `docs/cli.md` §7.6 descreve o formato do resultado, as etapas de progresso, o `busy` por pregação, o `llm_not_configured` e o efeito em `suggestion_error`. §5.3 amplia a linha de `busy` para a exclusão por pregação. Nada do que foi documentado contradiz o código. | Leitura do diff contra o baseline (`git diff 470a856 -- CHANGELOG.md docs/`), comparada com os testes dos passos 2 e 3. Se a exclusão por pregação virar ADR, conferir também o índice de `docs/adr/` e `docs/architecture/` (CLAUDE.md). |

| Critério de aceite | O que o cobre |
|---|---|
| Cenário "nova sugestão com outro preset" (spec) / Verificação 1 | CLI 3(a) com um dublê que guarda as mensagens: o `system` é igual a `build_prompt(show_preset(p))`; o `suggested` não editado sumiu; `chosen`, `discarded` e `suggested` editado ficaram iguais (via `sermon show --json`); o resultado lista os cortes novos, com IDs que existem em `sermon show` como `suggested` e `preset_id = p`. Reforçado por core 1(a) e 2(d). |
| Cenário "sem `--wait`" / Verificação 2 | CLI 3(b) com `harmless_tasks`. |
| Cenário "máquina ocupada não impede" / Verificação 3 / FR-001 (sem trava global) | CLI 3(d) e core 2(b) com `lock_owner`, mais core 2(a) (`needs_lock=False`, tipo registrado). |
| Cenário "pregação não processada" / Verificação 4 (1ª parte) | CLI 3(c): saída 5 `sermon_not_processed` e `task list --kind suggest --json` vazio; core 2(c) para cada estado não `processed`. |
| Borda "preset inexistente → `not_found`" / Verificação 4 (2ª parte) | CLI 3(c): saída 3 com `details.preset_id`, sem tarefa; core 2(c). |
| Borda "LLM falha duas vezes → `failed` com `llm_error`; cortes antigos intactos" / Verificação 5 | Core 1(b) e 2(f). CLI: saída 6 `llm_error` e cortes iguais em `sermon show`. A tarefa fica `failed` com `llm_error` em `task show`. |
| Borda "sem modelo ou chave → `llm_not_configured`; nada muda" | CLI 3(c): saída 5 com `details.missing`; cortes iguais; nenhuma tarefa e `suggestion_error` igual ao de antes (ver lacuna L3); chave sentinela ausente da saída. |
| Borda "duas simultâneas da mesma pregação → `busy`" / Verificação 6 | Core 2(e) e CLI 3(c): saída 4 `busy` com `details.task_id`, sem tarefa nova. A corrida real fica fora da barra (lacuna L4). |
| FR-002 — preset indicado ou padrão | Core 2(d), os dois ramos. |
| FR-003 — substitui só no sucesso; escolhidos, descartados e editados ficam | Core 1(a), 1(b) e 1(c), com as quatro mutações do passo 1. |
| FR-004 — `--help` diz administrador | CLI 3(e). |
| Verificação 7 — quality gates limpos | `uv run pytest -q` verde (core, cli e api), `uv run ruff check .`, `uv run ruff format --check .` e `uv run mypy` sem achado. |

### Divergências entre o plan.md e o código do baseline, e lacunas

Cada item traz a recomendação. Onde o plano não decide, a barra adota a recomendação, que é
a opção mais conservadora (execução automatizada, sem pergunta). Se o `plan.md` decidir de
outro jeito antes do código, a linha correspondente da matriz é revista e o baseline fica.

- **L1 — assinatura de `suggest`.** O plano escreve `suggest(..., replace_suggested=True)`. No
  baseline, a função é `suggest(connection, sermon_id, preset: Mapping)` e recebe o preset
  **já resolvido** (como `show_preset` o dá), não um ID. *Recomendação*: acrescentar
  `replace_suggested: bool = False`, só por palavra-chave. A tarefa resolve o preset com
  `show_preset` ou `default_preset`, e a chamada do `process` fica como está.
- **L2 — formato do resultado.** O plano diz `{"sermon_id", "preset_id", "suggested_cuts",
  "discarded"}`, "igual ao bloco de sugestão do `process`". O `process` não tem esse bloco: ele
  devolve a pregação com `suggestion_warnings`, em que cada item é `{"title",
  "estimated_duration", "message"}` (docs/cli.md §7.4). E `SuggestionResult` só traz `saved` e
  `warnings`, sem os cortes novos. A chave `discarded` também se confunde com o estado
  `discarded`. *Recomendação*: `{"sermon_id", "preset_id", "suggested_cuts": [<corte como
  sermon show>], "suggestion_warnings": [...]}`. Para isso, `SuggestionResult` passa a
  devolver os IDs gravados. Documentar o formato em §7.6.
- **L3 — `llm_not_configured` "nada muda".** No baseline, `suggest` grava `suggestion_error`
  na pregação para **qualquer** `WordcutError`, e isso inclui `llm_not_configured`. Se a
  verificação só acontecer dentro da tarefa, nasce uma tarefa `failed` e a pregação muda, o
  que contraria o spec. *Recomendação*: `start_suggestion` confere modelo e chave como
  pré-condição, sem criar tarefa e sem tocar em `suggestion_error`. A verificação de dentro de
  `suggest` continua como rede para a configuração que mudar entre o lançamento e a execução.
  Para não duplicar regra, expor o que hoje é `_configured_model`.
- **L4 — exclusão por pregação não é atômica.** Em `tasks.execution.start`, o `admit` roda
  **sem trava** quando `needs_lock=False`, e `_create` abre outra conexão. Conferir e depois
  inserir deixa uma janela em que duas chamadas simultâneas passam as duas. Isso contradiz o
  "evita gravação concorrente" do plano. O pressuposto proíbe mudar o esquema, então um
  índice único fica de fora. *Recomendação*: registrar a janela como risco aceito nas Decisões
  técnicas e em §7.6, ou fazer a conferência e a inserção numa só transação `BEGIN IMMEDIATE`
  (o que muda `execution.start` e precisa entrar no Contexto de código). A barra cobra só o
  caso sequencial.
- **L5 — dublê e processo destacado.** `default_model` só é substituído no processo do pytest
  (`conftest.py`, ADR-0016). O plano não avisa que o `runner` destacado chamaria o OpenRouter
  de verdade. *Recomendação*: dizer no plano que os testes sem `--wait` usam `harmless_tasks`
  e que o registro do tipo se prova num interpretador novo, como em 2(a).
- **L6 — `llm_error` e `suggestion_error`.** O spec só pede "cortes antigos intactos". O
  `suggest` grava o erro na pregação, e a ADR-0016 diz que o resultado da última sugestão fica
  ali. *Recomendação*: manter, registrar no plano e em §7.6. A barra cobra
  `suggestion_error.code == "llm_error"` depois da falha e `null` depois de um sucesso.
- **L7 — resposta válida sem corte aproveitável.** Quando o LLM responde no esquema, mas todo
  corte sai da duração permitida, `saved = 0` (hoje isso não é erro, ver
  `test_a_valid_answer_without_cuts_to_keep_saves_nothing_and_is_no_error`). Com
  substituição, os sugeridos antigos somem e nada entra no lugar. *Recomendação*: tratar como
  sucesso, por coerência com o "só no sucesso" do plano e com o contrato atual. Registrar no
  plano e no §7.6 e exigir um teste que fixe isso (sugeridos não editados apagados,
  `suggested_cuts: []`, avisos presentes).
- **L8 — `busy` por pregação no contrato.** §5.3 define `busy` como "outra tarefa segura a
  trava". O plano só diz `details.task_id`. *Recomendação*: `details` igual ao `busy` da
  trava (`task_id`, `kind`, `started_at`), uma mensagem que nomeie a sugestão em andamento,
  §5.3 e §7.6 atualizados no passo 4, e decidir se a regra vira ADR complementar à ADR-0013
  (CLAUDE.md).
- **L9 — `process --force` durante uma `suggest`.** Os IDs de palavra dos cortes ficam em JSON,
  sem chave estrangeira (migração 0007). Um reprocessamento no meio de uma sugestão deixaria a
  `suggest` gravar cortes que apontam para palavras apagadas. Nem o spec nem o plano tratam
  disso. *Recomendação*: na transação de substituição, conferir de novo se a pregação continua
  `processed` com o mesmo `processed_at`; se não, falhar sem gravar. Fica fora da barra até o
  plano decidir.
- **L10 — saída legível e etapa de progresso não definidas.** *Recomendação*: a etapa
  `sugerindo` (a mesma do `process`) e um renderizador próprio, como "Tarefa N iniciada:
  sugestão de cortes da pregação X. Acompanhe com wordcut task wait N." e "K cortes sugeridos
  para a pregação X com o preset P.". A barra cobra a saída legível sem fixar o texto exato.
- **L11 — preset gravado na tarefa.** *Recomendação*: `params` guardam o `preset_id` já
  resolvido (o ID do padrão quando a opção falta). Assim, `task show` e o resultado dizem qual
  preset valeu, e trocar o padrão entre o lançamento e a execução não muda nada. Um preset
  apagado nesse intervalo faz a tarefa terminar `failed` com `not_found`.

## Rodada 1 — 2026-10-26 — working tree sobre 470a856

**baseline_commit**: 470a85696cd41a5bb662dabb9aa9cc3b09c5f94f
**Componentes avaliados**: `packages/core`, `apps/cli`, documentação
**Suítes**: tudo ✅ (872 / 0 falhas) · core ✅ (586 / 0) · cli ✅ (285 / 0) · ruff check ✅ ·
ruff format --check ✅ · mypy ✅

**Barra desta rodada**: a matriz do topo, as decisões L1–L11 do `plan.md` e, acrescentada
pelo orquestrador ao passo 2 depois do incidente do implementador (runner destacado real
chamou o OpenRouter com a chave fictícia e recebeu 401), a **guarda global contra rede**:
(1) fixture autouse no `conftest.py` da raiz que define uma variável de ambiente herdada pelo
processo filho; (2) `suggestion.default_model()` e `processing.default_gateways()` recusam com
erro claro quando ela está definida; (3) um teste prova que um runner destacado real, com a
chave fictícia, termina sem chamar a rede e sem deixar processo vivo.

**Mutações manuais** (cópia no scratchpad, com `OPENROUTER_URL` da cópia apontada para
`127.0.0.1:9` e só módulos com `harmless_tasks` autouse ou sem processo destacado): 18 de 18
mortas — `edited = 0`, `status = 'suggested'`, `sermon_id` do delete; apagar antes do LLM;
L7 (só apagar com cortes novos); L9 (sem conferência de `processed_at`); tirar `suggest` de
`BUILTIN_KIND_MODULES`; `needs_lock=True`; ignorar `preset_id` no lançamento; L11 (tarefa usa o
padrão); tirar `reconcile`, o filtro de recurso e a exclusão inteira; L3 (sem
`require_configured` no lançamento); L10 (sem a etapa `sugerindo`); `wait=False`; sem repasse
de `--preset`; plural fixo no renderizador. Nenhum processo `wordcut.tasks.runner` ficou vivo.

**Política de comentários** (CONTRIBUTING §5): os comentários novos estão em inglês e são de
intenção ou alerta (`suggestion/__init__.py`, `service/suggestion.py`, `tasks/suggest.py`).
Observação: o comentário `# Fictitious: no test ever reaches OpenRouter.` dos dois módulos de
teste novos afirma uma garantia que o repositório ainda não dá (o incidente mostrou o
contrário); passa a ser verdadeiro com a guarda global.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Substituição no core | PASS | `test_suggestion.py` (substituição por ID e campo, três falhas sem tocar em cortes, outra pregação, L7, L9) e `test_cuts_repository.py::test_deleting_the_unedited_suggestions_…`; `test_process_suggests.py` verde sem mudança; as quatro mutações da matriz, mais L7 e L9, vermelhas |
| 2 — Tipo de tarefa e serviço | PARCIAL | Matriz 2(a)–2(g) e L3, L8, L10, L11 cobertas em `test_suggest_task.py`, com as mutações vermelhas. Falta a guarda global contra rede: `conftest.py` da raiz não define variável herdável; `suggestion.default_model()` (`packages/core/src/wordcut/suggestion/__init__.py:54`) e `processing.default_gateways()` (`packages/core/src/wordcut/processing/__init__.py:73`) não recusam; não há teste com runner destacado real que termine sem rede. A fixture `no_real_task_process` só existe em `test_suggest_task.py:92` e `test_sermon_suggest_command.py:77` |
| 3 — CLI | PASS | `test_sermon_suggest_command.py`: 3(a)–3(g) (JSON e progresso, `--quiet`, sem `--wait`, saídas 3/5/5/6/4 sem tarefa, `lock_owner`, ajuda com "administrador", saída legível, sem chave sentinela); `wait=False` e sem `--preset` vermelhas |
| 4 — Documentação | PASS | `CHANGELOG.md` [Não lançado], `docs/cli.md` §5.3 (`busy` por pregação com `task_id`, `kind`, `started_at`) e §7.6 (recusas, corrida aceita, preset resolvido, `suggestion_error`, L7, L9, etapa, formato do resultado), `docs/architecture/README.md`; nada contradiz o código; sem ADR nova (L8) |

### Critérios de aceite
- ✅ Nova sugestão com outro preset / Verificação 1 — `test_suggest_with_a_preset_and_wait_replaces_…` (CLI), `test_a_suggestion_with_a_preset_asks_with_its_prompt_…`, `test_a_replacing_suggestion_swaps_…`
- ✅ Sem `--wait` / Verificação 2 — `test_suggest_without_wait_answers_the_running_task`
- ✅ Máquina ocupada não impede / Verificação 3 / FR-001 — `test_suggest_runs_while_another_process_holds_…`, `test_a_suggestion_runs_while_another_process_holds_…`, `test_suggest_is_a_kind_without_the_lock_…`
- ✅ Pregação não processada / Verificação 4 — `test_a_refused_suggestion_exits_…[sermon not processed]`, `test_a_sermon_not_processed_is_refused_without_a_task` (4 estados)
- ✅ Preset inexistente → `not_found` — `test_a_refused_suggestion_exits_…[preset not found]`, `test_a_preset_that_does_not_exist_…`
- ✅ LLM falha duas vezes → `llm_error`, cortes intactos / Verificação 5 — `test_an_llm_failure_exits_6_…`, `test_an_llm_failure_fails_the_task_…`, `test_a_failed_replacing_suggestion_…`
- ✅ Sem modelo ou chave → `llm_not_configured`, nada muda — `test_without_the_llm_configured_suggest_exits_5_…`, `test_without_the_llm_configured_nothing_changes_…`
- ✅ Duas simultâneas da mesma pregação → `busy` / Verificação 6 — `test_a_second_suggestion_while_one_runs_exits_4_busy_…`, `test_a_second_suggestion_of_a_sermon_while_one_runs_is_busy_…` (caso sequencial, L4)
- ✅ FR-002 — preset indicado ou padrão — `test_a_suggestion_in_the_foreground_…` e `test_a_suggestion_with_a_preset_…`
- ✅ FR-003 — substitui só no sucesso — passo 1, com as quatro mutações vermelhas
- ✅ FR-004 — `--help` diz administrador — `test_suggest_help_says_it_is_for_the_administrator_in_portuguese`
- ✅ Verificação 7 — quality gates limpos — pytest 872, ruff check, ruff format --check, mypy

### Veredito geral: PARCIAL
Passos 1, 3 e 4 PASS; passo 2 PARCIAL só pela guarda global contra rede (itens 1–3 da decisão
do orquestrador), que não existe. Reabrir o passo 2.

## Rodada 2 — 2026-10-26 — working tree sobre 470a856

**baseline_commit**: 470a85696cd41a5bb662dabb9aa9cc3b09c5f94f
**Componentes avaliados**: `packages/core`, `apps/cli`, documentação
**Suítes**: tudo ✅ (875 / 0 falhas) · tudo em `unshare -rn`, só `lo` ✅ (871 / 0 falhas, 4
skipped: root do namespace escreve em pasta somente leitura, sem relação com rede) · ruff
check ✅ · ruff format --check ✅ · mypy ✅

**Barra desta rodada**: a matriz do topo e a guarda global contra rede do orquestrador (passo
2): autouse na raiz com `WORDCUT_FORBID_NETWORK=1`, herdada pelo filho; `default_model` e
`default_gateways` recusam com a variável ligada; um teste com runner destacado real termina
`failed` sem rede e sem processo vivo; autouse locais redundantes fora e comentário corrigido;
decisão no `plan.md`, na ADR-0017 e no CONTRIBUTING §3.

**Mutações manuais** (cópia no scratchpad, `OPENROUTER_URL` da cópia em `127.0.0.1:9`,
`PYTHONPATH` da cópia herdado pelo runner, tudo em `unshare -rn`): 6 de 6 mortas —
`default_model` sem `refuse_when_forbidden` (runner real: `('llm_error', None, 0)` em vez de
`network_error`; e a fábrica no interpretador novo); `default_gateways` sem a guarda;
`conftest.py` sem o `setenv`; `refuse_when_forbidden` que nunca recusa; `execution.Popen` sem
a variável no `env` do filho; guarda com código `llm_error`. Nenhum processo
`wordcut.tasks.runner` ficou vivo.

**Observação**: a guarda recusa com a variável **definida, com qualquer valor**
(`network.py:19`, `in os.environ`), não só com `=1`. É mais conservador que a barra e está
escrito assim na ADR-0017. O comentário `# Fictitious: no test ever reaches OpenRouter.`
segue em três módulos anteriores à issue (`test_process_suggests.py`, `test_openrouter_model.py`,
`test_suggestion.py`), que não lançam runner real; com a guarda, o que ele afirma passa a valer.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Substituição no core | PASS | sem regressão desde a Rodada 1; suíte verde |
| 2 — Tipo de tarefa e serviço | PASS | `conftest.py:35` autouse `no_network` (`setenv`); `wordcut/network.py` `refuse_when_forbidden` → `network_error` com `details.forbidden_by`; chamada em `suggestion/__init__.py` `default_model` e `processing/__init__.py` `default_gateways`; `tasks/execution.py:118` repassa `os.environ`; `test_network_guard.py` (as duas fábricas num interpretador novo); `test_suggest_task.py::test_a_real_detached_suggestion_meets_the_network_guard_and_leaves_no_process` (`detached_tasks`, runner real, `failed` com `network_error`, `process.wait() == 0`); `no_real_task_process` saiu dos dois módulos; comentário da chave fictícia corrigido nos dois módulos novos; decisão no `plan.md` (Decisões técnicas e Contexto de código), ADR-0017 e índice, CONTRIBUTING §3, README; 6 mutações vermelhas |
| 3 — CLI | PASS | sem regressão desde a Rodada 1; os quatro testes sem `--wait` pedem `harmless_tasks` |
| 4 — Documentação | PASS | §5.3 (`network_error` também a rede proibida), CHANGELOG e `docs/architecture/README.md` citam a guarda; nada contradiz o código |

### Critérios de aceite
- ✅ Nova sugestão com outro preset / Verificação 1 — `test_suggest_with_a_preset_and_wait_replaces_…` (CLI), `test_a_suggestion_with_a_preset_asks_with_its_prompt_…`, `test_a_replacing_suggestion_swaps_…`
- ✅ Sem `--wait` / Verificação 2 — `test_suggest_without_wait_answers_the_running_task`
- ✅ Máquina ocupada não impede / Verificação 3 / FR-001 — `test_suggest_runs_while_another_process_holds_…`, `test_a_suggestion_runs_while_another_process_holds_…`, `test_suggest_is_a_kind_without_the_lock_…`
- ✅ Pregação não processada / Verificação 4 — `test_a_refused_suggestion_exits_…[sermon not processed]`, `test_a_sermon_not_processed_is_refused_without_a_task`
- ✅ Preset inexistente → `not_found` — `test_a_refused_suggestion_exits_…[preset not found]`, `test_a_preset_that_does_not_exist_…`
- ✅ LLM falha duas vezes → `llm_error`, cortes intactos / Verificação 5 — `test_an_llm_failure_exits_6_…`, `test_an_llm_failure_fails_the_task_…`, `test_a_failed_replacing_suggestion_…`
- ✅ Sem modelo ou chave → `llm_not_configured`, nada muda — `test_without_the_llm_configured_suggest_exits_5_…`, `test_without_the_llm_configured_nothing_changes_…`
- ✅ Duas simultâneas da mesma pregação → `busy` / Verificação 6 — `test_a_second_suggestion_while_one_runs_exits_4_busy_…`, `test_a_second_suggestion_of_a_sermon_while_one_runs_is_busy_…` (caso sequencial, L4)
- ✅ FR-002 — preset indicado ou padrão — `test_a_suggestion_in_the_foreground_…` e `test_a_suggestion_with_a_preset_…`
- ✅ FR-003 — substitui só no sucesso — passo 1
- ✅ FR-004 — `--help` diz administrador — `test_suggest_help_says_it_is_for_the_administrator_in_portuguese`
- ✅ Verificação 7 — quality gates limpos — pytest 875 (871 + 4 skipped sem rede), ruff check, ruff format --check, mypy

### Veredito geral: PASS
Os quatro passos PASS, os 12 critérios cobertos, suítes e checagens verdes, inclusive sem
rede. A guarda global fecha o PARCIAL do passo 2 da Rodada 1.
