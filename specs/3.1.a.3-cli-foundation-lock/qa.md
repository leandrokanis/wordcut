# QA — 3.1.a.3 — Base da CLI, trava de processamento e `wordcut status`

## Plano de QA — 2026-10-26

**baseline_commit**: 58acaa5c651e6595cdc7af6952d46ab8d968fea1
**Componentes em escopo**: `apps/cli/src/wordcut_cli/` (`__init__.py`, `contract.py`,
`legacy.py`, `status.py`); `packages/core/src/wordcut/` (`errors.py`, `home.py`, `db/`,
`db/migrations/0001_base.sql`, `lock.py`, `service/`); `packages/core/tests/`,
`apps/cli/tests/`; documentação (`README.md`, `docs/adr/0012-contrato-da-cli.md`,
`docs/adr/README.md`, `docs/architecture/README.md` §4, `docs/cli.md` se o contrato mudar).
**Suítes que valem como prova** (da raiz, após `uv sync --all-packages`):
- Python (core, cli): `uv run pytest -q`; por arquivo, `uv run pytest <arquivo> -q`.
- Checagem estática: `uv run ruff check . && uv run ruff format --check . && uv run mypy`.
- Smoke do executável real: `WORDCUT_HOME=$(mktemp -d) uv run wordcut status --json; echo $?`.
- Empacotamento dos `.sql`: `uv build --package wordcut-core` e listar o wheel.
- Estado dos gates no baseline (para separar dívida antiga de regressão): rodar os mesmos
  comandos numa `git worktree` temporária em `58acaa5`, fora da árvore de trabalho.

Fontes da barra: spec.md e plan.md desta pasta; docs/cli.md §3–§6.4, §10, §14; ADR-0004,
ADR-0005, ADR-0006; CLAUDE.md e CONTRIBUTING.md. Sem rastreador: os critérios saem dos
cenários do spec.md e da seção Verificação do plan.md. Diário em `tdd.md` (`## Plano de QA`).

Interpretações da barra (execução automatizada, opção mais conservadora, registradas):
- Onde o Passo 1/4 do plano diz `cli/` e `cli/status.py`, vale o Contexto de código:
  `apps/cli/src/wordcut_cli/`.
- `--version`: a distribuição `wordcut` não existe (`importlib.metadata.version("wordcut")`
  lança `PackageNotFoundError` no baseline); a barra aceita a versão de `wordcut-cli` e exige
  que o valor impresso seja igual ao do metadado, com saída 0.
- `busy`/saída 4: nenhum comando novo adquire a trava neste item; a prova é em duas metades,
  ambas obrigatórias: `acquire` no core falha com `WordcutError("busy")` e `details`, e um
  handler que lança esse erro sai por `main(argv)` com 4 e o objeto de erro (injeção por
  `monkeypatch` aceita, por ser o único caminho).
- `internal_error` e Ctrl+C: provados por handler injetado que lança `RuntimeError` e
  `KeyboardInterrupt`, pelo `main(argv)`.
- `invalid_argument`: `message` em português (não a mensagem padrão em inglês do `argparse`)
  e `details.argument` quando o argumento é identificável (docs/cli.md §5.3).
- Tempo decorrido no JSON: número em segundos (docs/cli.md §4.3); nome do campo livre em
  `snake_case`. `started_at`: ISO 8601 com fuso, sem fração de segundo.
- Trava livre: `lock` é exatamente `{"held": false}`, sem resto de dono antigo; outras chaves
  de topo são aceitas (§4.4).
- Tarefas em andamento no `status` (§10) ficam para o item 4; não são cobradas.
- `apps/cli/tests/test_cli.py` pode mudar só para incluir `status` na lista de comandos.
- Teste que depende de outro processo segurar a trava DEVE ter limite de tempo; teste que
  pode travar a suíte conta como vermelho.

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Erros e contrato de saída | (a) `errors.py`: `WordcutError(code, message, details)` e tabela central código → saída com os códigos de docs/cli.md §5.1/§5.3 (`internal_error` 1, `invalid_argument` 2, `not_found` 3, `busy` 4, regra 5, falha externa 6). (b) `main(argv) -> int`, entrada `wordcut_cli:main` mantida. (c) `--json`/`--quiet` antes e depois do subcomando, mesmo resultado. (d) Com `--json`, stdout = um documento JSON; erro = `{"error": {"code","message","details"?}}`; sem `--json`, stdout vazio e `message` no stderr. (e) Erro de uso do `argparse` → `invalid_argument`, saída 2, JSON no stdout, `message` em português. (f) Exceção inesperada → `internal_error`, saída 1, mensagem genérica, sem traceback no stdout nem no stderr, salvo `WORDCUT_DEBUG=1` (traceback só no stderr). (g) `KeyboardInterrupt` → 130, sem JSON. (h) `--version` → versão de `wordcut-cli`, saída 0. (i) Comandos antigos em `legacy.py` sem mudança de comportamento, registrados no mesmo parser. | `apps/cli/tests/test_cli_contract.py` por `main(argv)` com `capsys` e `json.loads` do stdout; teste de unidade da tabela em `packages/core/tests/` (ou no próprio contrato) cobrindo todo código de §5.3. Diff contra o baseline: `legacy.py` igual ao `__init__.py` antigo, salvo imports/registro. `test_cli.py` verde. Mutações exigidas: tabela `busy`→3; remover o `error()` da subclasse (o `argparse` já sai com 2, então só o JSON mata); `--json` só no parser raiz; traceback no stdout; remover o tratamento de `KeyboardInterrupt`. Smoke `uv run wordcut --version; echo $?`. |
| 2 — `Home` e banco | (a) `Home` resolve `WORDCUT_HOME` ou, sem ela, `~/.local/share/wordcut`; cria a pasta (com pais) em modo `0700`. (b) `connect(home)` cria o banco no primeiro uso, aplica `0001_base.sql`, deixa `user_version` = último número, cria `app_info` com a versão que criou o banco. (c) Conexão com `foreign_keys=1`, `journal_mode=wal`, `busy_timeout=5000`. (d) Idempotente: abrir de novo não reaplica nem falha. (e) Banco antigo (`user_version` menor, com dados) recebe só as migrações pendentes e mantém os dados. (f) Uma transação por arquivo: migração com erro não deixa esquema parcial nem avança `user_version`. (g) Os `.sql` entram no wheel do `wordcut-core`. | `packages/core/tests/test_db.py` com `monkeypatch.setenv("WORDCUT_HOME", tmp_path/…)` e, para o padrão, `HOME` apontado para `tmp_path` sem `WORDCUT_HOME`; `os.stat(...).st_mode & 0o777 == 0o700`; `PRAGMA` lidos na conexão devolvida. (e) arquivo SQLite pré-criado com `user_version` 0 e tabela/linhas próprias → `connect` → linhas intactas e versão atual. (f) exige migrações injetáveis (diretório de teste com `0002` quebrado); sem esse meio, (f) fica PARCIAL. (g) `uv build --package wordcut-core` e conferir `wordcut/db/migrations/0001_base.sql` no wheel. Mutações: não gravar `user_version`; `foreign_keys` OFF. Atenção à armadilha de `sqlite3.executescript`, que faz `COMMIT` implícito: a atomicidade precisa de teste, não de leitura. |
| 3 — Trava global | (a) `acquire(kind, resource)` como context manager: `flock(LOCK_EX \| LOCK_NB)` em `<home>/processing.lock`; grava `{kind, resource, pid, started_at}`. (b) Ocupada → `WordcutError` `busy` na hora, `details` com `kind`, `resource`, `pid`, `started_at` do dono. (c) A tentativa recusada não apaga nem altera a descrição do dono. (d) `holder()`: livre → `None`/livre, ignorando conteúdo velho; ocupada → descrição do dono. (e) Processo dono morto (SIGKILL) → trava livre e `acquire` volta a funcionar. (f) Saída do context manager libera a trava. (g) `started_at` ISO 8601 com fuso local, `timespec="seconds"`. (h) `holder()` não quebra se ler o arquivo vazio ou pela metade (janela entre o `flock` e a gravação). | `packages/core/tests/test_lock.py` com subprocesso Python (`sys.executable -c …`) que adquire a trava, sinaliza pronto (stdout/arquivo) e espera; o teste chama `acquire`/`holder()` e depois `kill -9`; limite de tempo em toda espera. Regex `^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$`. (c) ler `holder()` depois do `busy` e comparar com o dono. (h) por leitura do código (tratamento de JSON inválido); se ausente, PARCIAL. Mutações: abrir a trava com `"w"` (trunca); `holder()` sem o teste `LOCK_SH`; `acquire` sem `LOCK_NB` (vermelha ou timeout). |
| 4 — `wordcut status` | (a) `service/status.py`: `machine_status(home) -> dict` puro, sem I/O de CLI (ADR-0004). (b) Livre → `{"lock": {"held": false}}`. (c) Ocupada → `held: true`, `kind`, `resource`, `pid`, `started_at`, tempo decorrido em segundos (número). (d) Nunca bloqueado pela trava: responde com outro processo segurando, saída 0. (e) Texto legível em português sem `--json`; JSON com `--json`, nas duas posições. (f) Primeira chamada num `WORDCUT_HOME` vazio cria pasta e banco. (g) Dono morto → livre. | `packages/core/tests/test_status.py` (serviço, com subprocesso dono) e `apps/cli/tests/test_status_command.py` (`main(["status","--json"])`, `main(["--json","status"])`, sem `--json`); comparar os dois JSON da opção global, com `elapsed` desconsiderado ou tolerado. Tempo decorrido: maior ou igual à espera feita antes do `status`, ou relógio injetado. Smoke `WORDCUT_HOME=$(mktemp -d) uv run wordcut status --json; echo $?` e `ls` do banco criado. Mutações: serviço responder livre com a trava ocupada; `elapsed` fixo em 0. |
| 5 — Documentação | README com seção curta da CLI nova (`wordcut status`, `WORDCUT_HOME`, aviso de disco local para o `flock`); `docs/adr/0012-contrato-da-cli.md` (opções globais, JSON, códigos) no formato das demais e no índice `docs/adr/README.md`; `docs/architecture/README.md` §4 atualizado; `docs/cli.md` alterado só se o contrato mudou, e então coerente com o código. Texto em português; nenhum dado pessoal ou segredo. | Leitura do diff contra o baseline (`git diff 58acaa5 -- README.md docs/`); conferir que o que a ADR-0012 afirma (códigos, saídas, posições de `--json`) bate com a tabela de `errors.py` e com os testes do contrato. ADRs aceitas (0004–0006) não editadas. |

| Critério de aceite | O que o cobre |
|---|---|
| Spec — status com a máquina livre (`lock: {held: false}`, saída 0) | `test_status_command.py` com `WORDCUT_HOME` vazio + smoke do executável |
| Spec — status com a máquina ocupada (`held: true`, tipo, recurso, PID, início, saída 0) | `test_status_command.py`/`test_status.py` com subprocesso dono |
| Spec — segunda operação pesada recusada (`busy`, saída 4, `details`, sem fila) (3.1.a.1) | `test_lock.py` (busy na hora, `details`, dono intacto) + `test_cli_contract.py` (handler com `busy` → 4 e objeto de erro); as duas metades obrigatórias |
| Spec — trava liberada quando o processo morre | `test_lock.py` e `test_status.py` com `SIGKILL` no dono |
| Spec — erro em JSON (`invalid_argument`, `message` em português, saída 2) | `test_cli_contract.py` (stdout só com o objeto de erro; `message` não é a padrão em inglês do `argparse`) |
| Spec — primeira execução cria o banco (sem `wordcut init`) | `test_db.py` + `test_status_command.py` (pasta e banco criados, `user_version` atual) |
| Borda — `--json` antes ou depois dá o mesmo resultado | `test_cli_contract.py`/`test_status_command.py` comparando as duas posições |
| Borda — sem `--json`, erro no stderr e stdout vazio | `test_cli_contract.py` |
| Borda — erro não previsto → `internal_error`, saída 1, sem traceback no stdout | `test_cli_contract.py` com handler injetado |
| Borda — Ctrl+C sai com 130 | `test_cli_contract.py` com `KeyboardInterrupt` injetado |
| Borda — banco de esquema anterior migrado sem perder dados | `test_db.py` (banco pré-criado com dados e `user_version` antigo) |
| Borda — `--version` imprime a versão e sai com 0 | `test_cli_contract.py` + smoke |
| FR-001 — opções globais `--json`, `--quiet`, `--version`, `--help` nas posições previstas | `test_cli_contract.py`; `--help` com saída 0 e a lista de comandos (`test_cli.py`) |
| FR-002 — um único documento JSON no stdout | `json.loads` do stdout inteiro em todo teste com `--json` |
| FR-003 — stdout só com resultado; `--quiet` suprime progresso | `test_cli_contract.py`; supressão só verificável se o contrato expuser o emissor de progresso (lacuna) |
| FR-004 — objeto de erro e códigos de saída de §5.1 | teste da tabela central + `test_cli_contract.py` |
| FR-005 — mapeamento central código → saída | leitura: um único ponto (`errors.py`) consultado pelo contrato; mutação da tabela vermelha |
| FR-006 — `~/.local/share/wordcut/` ou `WORDCUT_HOME`; banco criado e migrado | `test_db.py` (os dois caminhos, modo `0700`) |
| FR-007 — trava global do SO, liberada se o processo morrer | `test_lock.py` entre processos |
| FR-008 — trava ocupada falha na hora com `busy` (4) e `details` | `test_lock.py` + `test_cli_contract.py` |
| FR-009 — `status` livre ou dono com tempo decorrido, texto ou JSON | `test_status.py` + `test_status_command.py` |
| FR-010 — `status` não bloqueado pela trava | `test_status_command.py` com dono vivo e limite de tempo |
| Verificação — `WORDCUT_HOME` vazio → `status --json` cria o banco, `{"lock": {"held": false}}`, 0 | `test_status_command.py` + smoke |
| Verificação — outro processo segura → `held`, `kind`, `resource`, `pid`, `started_at`, tempo decorrido; 0 | `test_status_command.py` |
| Verificação — outro processo segura → `acquire` falha com `busy`, 4 pelo contrato, com `details` | `test_lock.py` + `test_cli_contract.py` |
| Verificação — dono morto → `status` livre | `test_status.py`/`test_status_command.py` |
| Verificação — `wordcut --json status` = `wordcut status --json` | `test_status_command.py` |
| Verificação — argumento inválido com e sem `--json` | `test_cli_contract.py` |
| Verificação — exceção inesperada → `internal_error`, 1, sem traceback no stdout | `test_cli_contract.py` |
| Verificação — `KeyboardInterrupt` → 130 | `test_cli_contract.py` |
| Verificação — `--version` → versão, 0 | `test_cli_contract.py` + smoke |
| Verificação — `user_version` antigo → migrações pendentes sem perder dados | `test_db.py` |
| Verificação — `wordcut overview <arquivo>` continua funcionando | teste em `apps/cli/tests/` por `main(["overview", <transcrição fictícia>])` com saída 0; na rodada, comparar a saída com a do baseline (worktree em `58acaa5`) no mesmo arquivo |
| Verificação — quality gates limpos | `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` verdes; diferença em relação ao baseline registrada |

### Lacunas do plano (registradas antes do código)

1. `--version` por `importlib.metadata.version("wordcut")` falha: não há distribuição
   `wordcut`. A barra aceita `wordcut-cli`.
2. Nenhum comando novo adquire a trava; `busy` saída 4 "pelo contrato" só se prova com
   handler injetado. Sem essa metade, o critério fica PARCIAL.
3. `--quiet` não tem progresso para suprimir neste item; só a aceitação nas duas posições é
   provável.
4. O plano não diz como o teste injeta uma migração extra; sem isso, a atomicidade por
   arquivo (Decisão técnica) fica PARCIAL.
5. Janela entre o `flock` e a gravação do JSON do dono: `holder()` pode ler arquivo vazio; o
   `status` não pode virar `internal_error` aí.
6. `apps/cli/tests/test_cli.py` fixa a lista de subcomandos e espera `SystemExit` no
   `--help`; o plano não o menciona. Pode mudar só para incluir `status` (e para aceitar
   `--help` com saída 0, se o `main` passar a devolver o código).
7. `details.argument` de docs/cli.md §5.3 não está no plano; a barra o cobra.
8. Spec diz "qualquer comando" cria o banco; o plano só verifica `status`. A barra cobra o
   contrato novo, não os comandos antigos.
9. docs/cli.md §10 inclui tarefas em andamento no `status`; fica para o item 4.
10. Passos 1 e 4 citam `cli/` e `cli/status.py`; vale o Contexto de código
    (`wordcut_cli/`).

## Rodada 1 — 2026-10-26 — working tree sobre 58acaa5

**baseline_commit**: 58acaa5c651e6595cdc7af6952d46ab8d968fea1
**Componentes avaliados**: `apps/cli/src/wordcut_cli/`, `packages/core/src/wordcut/`
(`errors`, `home`, `db`, `lock`, `service`), `conftest.py`, testes de `apps/cli/tests/` e
`packages/core/tests/`, documentação.
**Suítes**: Python (core, cli) ✅ (168 / 0 falhas; baseline 97 / 0) · ruff check ✅ ·
ruff format --check ✅ · mypy ✅ (39 arquivos; baseline 30) · wheel do `wordcut-core` com
`wordcut/db/migrations/0001_base.sql` ✅ · smoke do executável ✅.

Mutações manuais, numa cópia da árvore no scratchpad (a árvore de trabalho não foi tocada):
25 de 26 mortas, incluindo todas as exigidas pela matriz. A sobrevivente (`_apply` sem
`ROLLBACK`) é equivalente: `connect` fecha a conexão na falha, e o fechamento desfaz a
transação aberta. Detalhe no `tdd.md`, `## Rodada 1 · QA`.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Erros e contrato de saída | PARCIAL | (a)–(h) provados: `test_errors.py` (15 códigos + código desconhecido recusado), `test_cli_contract.py` (JSON nas duas posições, erro no stdout/stderr, `invalid_argument` em português com `details.argument`, `internal_error` sem traceback, `WORDCUT_DEBUG=1` só no stderr, 130, `--version` = `wordcut-cli`, `busy` → 4 com handler injetado), `test_cli.py` com `status` e os 7 comandos antigos; mutações exigidas vermelhas. (i) falha em parte: `legacy.py` difere do `__init__.py` antigo só em registro e imports, e `overview` dá saída idêntica à do baseline, mas os subparsers antigos herdam a classe `Parser`, e o erro de uso de um comando antigo mudou: `wordcut overview` sem arquivo imprimia `usage:` e a mensagem do `argparse` em inglês, e agora imprime `erro: Argumento obrigatório ausente: transcript.` (saída 2 nas duas). O comentário em `contract.py:145-146` ("keep their own output and errors") e a ADR-0012 ("imprimem a própria saída, fora do contrato") afirmam o contrário. Falta preservar o comportamento antigo ou registrar a mudança no comentário, na ADR-0012 e num teste. |
| 2 — `Home` e banco | PASS | `test_db.py`: `WORDCUT_HOME` e padrão `~/.local/share/wordcut`, pasta `0700`, `user_version` = última migração, `app_info.created_by`, `foreign_keys=1`/`wal`/`5000`, reabertura idempotente, banco sem migrações com dados preservados, só a pendente aplicada (migração injetada `9001`), migração quebrada sem tabela parcial nem versão nova. Mutações sem `user_version`, `foreign_keys` OFF, sem `BEGIN`/`COMMIT`, reaplicar tudo, WAL off e sem `0700`: todas vermelhas. Wheel com o `.sql`. |
| 3 — Trava global | PASS | `test_lock.py` entre processos reais (`lock_owner` no `conftest.py`, `SIGALRM` de 20 s): dono descrito, `busy` na hora com `details` do dono, dono intacto após a recusa, livre e readquirível após `SIGKILL`, liberada ao sair do bloco, `started_at` com fuso e sem fração, arquivo vazio, JSON pela metade ou não-objeto → campos `None`. Mutações `O_TRUNC`, sem `LOCK_SH`, sem `LOCK_NB` (timeout), sem `close`, sem tratar JSON inválido: vermelhas. |
| 4 — `wordcut status` | PASS | `test_status.py` (serviço puro, sem I/O de CLI, relógio injetado → `elapsed_seconds` 90; dono morto → livre; dono sem descrição → `held: true` com `null`; banco criado) e `test_status_command.py` (livre em JSON, texto em português, `--json` nas duas posições, resposta com dono vivo, banco criado, `--help` com exemplo). Smoke: `WORDCUT_HOME` vazio → `{"lock": {"held": false}}`, 0, pasta `700` e `wordcut.db`; dono vivo → `held: true`, `elapsed_seconds` 3, 0. Mutações `elapsed` = 0, serviço sempre livre e sem criar o banco: vermelhas. |
| 5 — Documentação | PASS | README com a seção da CLI nova, `WORDCUT_HOME` e o aviso de disco local; ADR-0012 no formato das demais e no índice; `docs/architecture/README.md` §4 atualizado; `docs/cli.md` e ADRs 0004–0006 sem diff. Códigos, saídas e posições de `--json` da ADR batem com `errors.py` e os testes do contrato. Sem dado pessoal nem segredo. A frase da ADR sobre os comandos antigos entra no achado do passo 1. |

Política de comentários (CONTRIBUTING.md §5) no código novo: todos em inglês e de tipo
válido (restrição externa com fonte, alerta, intenção, referência, contrato público). Único
desvio: `contract.py:145-146` descreve um comportamento que o código não tem (passo 1).

### Critérios de aceite
- ✅ Spec — status com a máquina livre — `test_status_of_an_idle_machine_is_the_free_lock_in_json` + smoke
- ✅ Spec — status com a máquina ocupada — `test_status_answers_at_once_while_another_process_holds_the_lock`, `test_machine_busy_elsewhere_reports_the_holder_and_how_long_it_has_run`
- ✅ Spec — segunda operação recusada com `busy`, 4 e `details` — `test_acquiring_a_held_lock_fails_at_once_with_busy_and_the_holder_details`, `test_refused_attempt_leaves_the_holder_description_intact` + `test_command_refused_by_a_lock_held_elsewhere_exits_with_busy_and_the_holder`
- ✅ Spec — trava liberada quando o processo morre — `test_lock_is_free_again_once_its_holder_process_is_killed`, `test_machine_whose_lock_holder_was_killed_reports_the_lock_free`, `test_status_shows_the_lock_free_once_its_holder_process_is_killed`
- ✅ Spec — erro em JSON em português, saída 2 — `test_unknown_option_with_json_is_an_invalid_argument_error_in_portuguese`
- ✅ Spec — primeira execução cria o banco — `test_first_connection_applies_every_packaged_migration`, `test_first_status_in_an_empty_data_folder_creates_the_database`
- ✅ Borda — `--json` antes ou depois — `test_json_option_before_the_command_gives_the_same_output_as_after`, `test_json_option_before_or_after_status_gives_the_same_result`
- ✅ Borda — sem `--json`, erro no stderr e stdout vazio — `test_domain_error_without_json_leaves_stdout_empty_and_writes_the_message_to_stderr`, `test_usage_error_without_json_leaves_stdout_empty_and_explains_on_stderr`
- ✅ Borda — erro não previsto → `internal_error`, 1, sem traceback — `test_unexpected_failure_becomes_internal_error_without_any_traceback`
- ✅ Borda — Ctrl+C → 130 — `test_ctrl_c_exits_with_130_and_prints_no_result`
- ✅ Borda — banco antigo migrado sem perder dados — `test_database_from_before_the_migrations_is_migrated_without_losing_data`, `test_only_pending_migrations_are_applied_to_an_older_schema`
- ✅ Borda — `--version` → versão, 0 — `test_version_prints_the_installed_cli_version` + smoke
- ✅ FR-001 — opções globais nas posições previstas — `test_quiet_option_reaches_the_handler_before_or_after_the_command`, testes de `--json`, `test_help_lists_every_command`
- ✅ FR-002 — um documento JSON no stdout — `json.loads` do stdout inteiro em todo teste com `--json`
- ✅ FR-003 — stdout só com resultado; `--quiet` aceito nas duas posições (decisão 3) — testes do contrato
- ✅ FR-004 — objeto de erro e saídas de §5.1 — `test_every_documented_error_code_maps_to_its_exit_code` + `test_domain_error_with_json_prints_only_the_error_object_and_exits_with_its_code`
- ✅ FR-005 — mapeamento central — `EXIT_CODES` em `errors.py` é o único ponto; mutação `busy` → 3 vermelha; código desconhecido recusado
- ✅ FR-006 — raiz de dados, banco criado e migrado — `test_data_root_*`, `test_first_connection_creates_the_data_folder_private_to_the_user`
- ✅ FR-007 — trava do SO liberada na morte do processo — `test_lock_can_be_acquired_after_its_holder_process_is_killed`
- ✅ FR-008 — `busy` na hora com `details` — `test_acquiring_a_held_lock_fails_at_once_with_busy_and_the_holder_details` + mutação sem `LOCK_NB`
- ✅ FR-009 — `status` livre ou dono com tempo decorrido, texto ou JSON — `test_status.py` + `test_status_command.py`
- ✅ FR-010 — `status` não bloqueado pela trava — `test_status_answers_at_once_while_another_process_holds_the_lock` (com limite de 20 s)
- ✅ Verificação — `WORDCUT_HOME` vazio → banco e `{"lock": {"held": false}}`, 0 — teste + smoke
- ✅ Verificação — dono vivo → `held`, `kind`, `resource`, `pid`, `started_at`, tempo, 0 — teste + smoke
- ✅ Verificação — `acquire` com `busy`, 4 pelo contrato, `details` — `test_lock.py` + `test_cli_contract.py`
- ✅ Verificação — dono morto → livre — `test_status_shows_the_lock_free_once_its_holder_process_is_killed`
- ✅ Verificação — `--json status` = `status --json` — `test_json_option_before_or_after_status_gives_the_same_result`
- ✅ Verificação — argumento inválido com e sem `--json` — testes de erro de uso do contrato
- ✅ Verificação — exceção inesperada → `internal_error`, 1 — `test_unexpected_failure_becomes_internal_error_without_any_traceback`
- ✅ Verificação — `KeyboardInterrupt` → 130 — `test_ctrl_c_exits_with_130_and_prints_no_result`
- ✅ Verificação — `--version` → versão, 0 — teste + smoke
- ✅ Verificação — `user_version` antigo → pendentes sem perder dados — `test_only_pending_migrations_are_applied_to_an_older_schema`
- ✅ Verificação — `wordcut overview <arquivo>` funciona — `test_previous_overview_command_still_prints_the_transcript`; saída idêntica à do baseline no mesmo arquivo
- ✅ Verificação — quality gates limpos — pytest, ruff check, ruff format, mypy verdes; baseline também verde (sem dívida antiga)

### Veredito geral: PARCIAL
Sem FAIL; todos os critérios cobertos e gates verdes. Reaberto o passo 1, item (i): o erro de
uso dos comandos antigos mudou, e o comentário em `contract.py:145-146` e a ADR-0012 dizem que não.

## Rodada 2 — 2026-10-26 — working tree sobre 58acaa5

**baseline_commit**: 58acaa5c651e6595cdc7af6952d46ab8d968fea1
**Componentes avaliados**: `apps/cli/src/wordcut_cli/` (`contract.py`, `legacy.py`),
`apps/cli/tests/test_legacy_commands.py`, `docs/adr/0012-contrato-da-cli.md`,
`docs/architecture/README.md` §4; demais componentes da Rodada 1 por regressão.
**Suítes**: Python (core, cli) ✅ (169 / 0 falhas; Rodada 1: 168) · ruff check ✅ ·
ruff format --check ✅ · mypy ✅ (39 arquivos) · wheel do `wordcut-core` com
`wordcut/db/migrations/0001_base.sql` ✅ · smoke do executável ✅.

Barra desta rodada: a matriz do topo, com a decisão do orquestrador registrada no plan.md
(Decisões técnicas, "Erro de uso dos comandos antigos", rodada 2): o erro de uso de todos os
comandos segue o contrato; só a saída de sucesso e os erros de execução dos comandos antigos
ficam fora dele.

Mutações manuais numa cópia da árvore no scratchpad (a árvore de trabalho não foi tocada):
4 de 4 mortas por `test_previous_command_usage_error_follows_the_contract` — `Parser.error`
delegando ao `argparse` no subparser de `overview`, erro de uso ignorando `--json`, mensagem
em inglês, sem `details.argument`. Detalhe no `tdd.md`, `## Rodada 2 · QA`.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Erros e contrato de saída | PASS | (a)–(h) sem regressão (`test_errors.py`, `test_cli_contract.py`, `test_cli.py` verdes). (i) fechado conforme a decisão da rodada 2: o comentário em `contract.py:145-146` e a docstring de `legacy.py` dizem que os comandos antigos mantêm saída e erros de execução e que o erro de uso segue o contrato; a ADR-0012 (Decisão, último item) diz o mesmo; `test_previous_command_usage_error_follows_the_contract` fixa `wordcut overview --json` → saída 2 e só `{"error": {"code": "invalid_argument", "message": "Argumento obrigatório ausente: transcript.", "details": {"argument": "transcript"}}}`. `legacy.py` difere do `__init__.py` do baseline só em docstring, imports e `register`. Smoke: `wordcut overview` → 2 com `erro: …` em português no stderr e stdout vazio; `--json` antes ou depois → objeto de erro, 2. |
| 2 — `Home` e banco | PASS | sem regressão: `test_db.py` verde; wheel com o `.sql`; smoke cria a pasta `0700` e `wordcut.db`. |
| 3 — Trava global | PASS | sem regressão: `test_lock.py` verde. |
| 4 — `wordcut status` | PASS | sem regressão: `test_status.py`, `test_status_command.py` verdes; smoke `status --json` → `{"lock": {"held": false}}`, 0. |
| 5 — Documentação | PASS | ADR-0012 e `docs/architecture/README.md` §4 agora descrevem o erro de uso dos comandos antigos dentro do contrato; CHANGELOG com a entrada do item; `docs/cli.md` e ADRs 0004–0006 sem diff; sem dado pessoal nem segredo. |

Política de comentários (CONTRIBUTING.md §5): o desvio da Rodada 1 (`contract.py`) foi
corrigido; o comentário agora descreve o comportamento do código.

### Critérios de aceite
- ✅ Todos os 33 critérios da Rodada 1 seguem cobertos pelos mesmos testes, verdes.
- ✅ Verificação — `wordcut overview <arquivo>` funciona — `test_previous_overview_command_still_prints_the_transcript`
- ✅ Decisão da rodada 2 — erro de uso de comando antigo segue o contrato — `test_previous_command_usage_error_follows_the_contract` + smoke

### Veredito geral: PASS
Passo 1 (i) fechado conforme a decisão da rodada 2; todos os passos PASS, critérios cobertos,
suíte e gates verdes, sem regressão.
