# Plan: Base da CLI, trava de processamento e `wordcut status`

**Issue**: 3.1.a.3
**Feature**: specs/3.1.a.3-cli-foundation-lock
**Data**: 2026-10-26

---

## Resumo

Cria a fundação da nova CLI: caminhos (`WORDCUT_HOME`), banco SQLite com migrações por
`PRAGMA user_version`, erros de domínio com código e saída centralizados, contrato de saída
(`--json`, stdout/stderr, 130 no Ctrl+C), trava global com `fcntl.flock` e o comando
`wordcut status`. O `cli.py` vira um pacote; os comandos antigos vão para um módulo
`legacy` e continuam no mesmo executável até o item `cli-migration`.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Componentes em escopo

- `apps/cli/src/wordcut_cli/` — pacote novo da CLI (contrato, `status`, comandos antigos).
- `packages/core/src/wordcut/` — `errors.py`, `home.py`, `db/`, `lock.py`, `service/`.
- `packages/core/tests/`, `apps/cli/tests/` — testes de comportamento pela interface pública (`main(argv)` e serviço).

---

## Contexto de código

| Situação | Path |
|---|---|
| Remover | `apps/cli/src/wordcut_cli/__init__.py` — a CLI atual vira `legacy.py`; o `__init__` passa a ter o contrato novo |
| Criar | `apps/cli/src/wordcut_cli/__init__.py` — `main(argv) -> int`, `build_parser()`; ponto de entrada `wordcut_cli:main` mantido |
| Criar | `apps/cli/src/wordcut_cli/contract.py` — opções globais, emissão de resultado/erro, mapeamento de exceções para saídas |
| Criar | `apps/cli/src/wordcut_cli/legacy.py` — comandos antigos movidos sem mudança de comportamento |
| Criar | `apps/cli/src/wordcut_cli/status.py` — subcomando `status` (registro no parser e formatação legível) |
| Criar | `packages/core/src/wordcut/errors.py` — `WordcutError(code, message, details)` e a tabela código → saída |
| Criar | `packages/core/src/wordcut/home.py` — `Home`: raiz (`WORDCUT_HOME` ou `~/.local/share/wordcut`), banco, trava, mídias |
| Criar | `packages/core/src/wordcut/db/__init__.py` — `connect(home)`: abre, liga `foreign_keys` e WAL, aplica migrações pendentes |
| Criar | `packages/core/src/wordcut/db/migrations/0001_base.sql` — primeira migração (tabela `app_info` com a versão que criou o banco) |
| Criar | `packages/core/src/wordcut/lock.py` — `ProcessingLock`: `acquire(kind, resource)` (context manager) e `holder()` |
| Criar | `packages/core/src/wordcut/service/__init__.py`, `packages/core/src/wordcut/service/status.py` — `machine_status(home) -> dict` |
| Criar | `apps/cli/tests/test_cli_contract.py`, `packages/core/tests/test_db.py`, `packages/core/tests/test_lock.py`, `packages/core/tests/test_status.py`, `apps/cli/tests/test_status_command.py` |
| Alterar | `packages/core/pyproject.toml` — nada de dependência nova; conferir que os `.sql` entram no pacote |
| Criar | `docs/adr/0012-contrato-da-cli.md` — contrato de saída e erros (opções globais, JSON, códigos) e índice atualizado |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python (core, cli) | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

Sem serviço externo. Os testes usam `WORDCUT_HOME` num `tmp_path` (via `monkeypatch.setenv`).

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Parser da CLI | `argparse` (stdlib), como hoje | Sem dependência nova (§V); o projeto já usa |
| Opções globais antes ou depois do subcomando | parser "pai" com `--json`/`--quiet` (`default=SUPPRESS`) incluído no parser raiz e em cada subparser | Único jeito em `argparse` de aceitar nas duas posições |
| Erro de uso do `argparse` | subclasse de `ArgumentParser` cujo `error()` lança `WordcutError("invalid_argument")` | Erro de uso também segue o contrato JSON e sai com 2 |
| Forma dos handlers | `handler(args, ctx) -> dict` puro; o contrato serializa; cada comando tem uma função de texto legível | Mantém a regra de negócio fora da CLI (§II) e testa o JSON direto |
| `main` | `main(argv) -> int` com `sys.exit(main())` no script | Testável sem `SystemExit`; códigos de saída explícitos |
| Exceção inesperada | `internal_error`, saída 1, mensagem genérica; traceback só no stderr com `WORDCUT_DEBUG=1` | Não vaza detalhe (§VI) e não suja o stdout |
| Ctrl+C | `KeyboardInterrupt` → saída 130, sem JSON | Convenção de shell (docs/cli.md §5.1) |
| Banco | `sqlite3` da stdlib, sem ORM | Simplicidade (§V) |
| Migrações | arquivos `NNNN_nome.sql` ordenados, aplicados numa transação cada, com `PRAGMA user_version` = último número | Sem tabela de controle extra; idempotente na abertura |
| Conexão | `foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout=5000` | Web e CLI lendo ao mesmo tempo sem "database is locked" |
| Raiz de dados | `Home` resolvido de `WORDCUT_HOME` ou `~/.local/share/wordcut`, criado com `0700` | docs/cli.md §14 |
| Trava | `fcntl.flock(LOCK_EX \| LOCK_NB)` em `<home>/processing.lock`; o dono grava no próprio arquivo um JSON `{kind, resource, pid, started_at}` | Liberada pelo kernel quando o processo morre (§IV) |
| Saber se está livre | `holder()` tenta `LOCK_SH \| LOCK_NB`: se consegue, está livre (solta na hora) e ignora o conteúdo velho; senão, lê o JSON | Conteúdo de processo morto nunca aparece como dono |
| Datas | ISO 8601 com fuso local, `timespec="seconds"` | docs/cli.md §4.3 |
| `--version` | `importlib.metadata.version("wordcut")` | Uma fonte só da versão |
| Comandos antigos | movidos para `wordcut_cli/legacy.py`, registrados no mesmo parser, fora do contrato novo | Continuam utilizáveis até o item `cli-migration` |
| Testes de trava entre processos | subprocesso Python que adquire a trava e espera; o teste mata o processo para provar a liberação | Prova o comportamento real do `flock` |

---

## Ordem de implementação

- [ ] **Passo 1 — Erros e contrato de saída** — `errors.py` com a tabela código → saída;
  pacote `cli/` com `main(argv) -> int`, opções globais nas duas posições, emissão de
  resultado (`--json` e texto), erro (`{"error": …}` no stdout com `--json`, mensagem no
  stderr sem ele), `internal_error`, 130 e `--version`. Mover os comandos antigos para
  `wordcut_cli/legacy.py` sem mudar o comportamento.
- [ ] **Passo 2 — `Home` e banco** — `home.py` e `db/` com migrações por `user_version`,
  `0001_base.sql`, criação automática no primeiro uso, migração incremental de um banco
  antigo.
- [ ] **Passo 3 — Trava global** — `lock.py` com `acquire(kind, resource)` (falha com `busy`
  e `details`) e `holder()`; liberação quando o processo morre.
- [ ] **Passo 4 — `wordcut status`** — `service/status.py` e `cli/status.py`: trava livre ou
  dono com tempo decorrido; texto legível e JSON; nunca bloqueado pela trava.
- [ ] **Passo 5 — Documentação** — README: seção curta da CLI nova (`wordcut status`,
  `WORDCUT_HOME`); ADR-0012 (contrato da CLI) e índice; `docs/architecture/README.md` §4;
  docs/cli.md só se algo do contrato mudar.

---

## Riscos

- **`flock` em sistema de arquivos de rede**: não é garantido; `WORDCUT_HOME` fica em disco
  local, anotado no README.
- **Opções globais em dois lugares conflitarem com opções dos comandos antigos**: os
  antigos não usam `--json` nem `--quiet`; o teste do contrato cobre um comando antigo
  ainda funcionando.

---

## Fora de escopo

- Tarefas, `--wait` e `task` (item 4).
- Tabelas de domínio (pregação, corte…).
- Remover os comandos antigos (item `cli-migration`).

---

## Verificação

- [ ] `WORDCUT_HOME` vazio → `wordcut status --json` cria o banco e devolve
  `{"lock": {"held": false}}` com saída 0.
- [ ] Outro processo segura a trava → `wordcut status --json` traz `held: true`, `kind`,
  `resource`, `pid`, `started_at` e o tempo decorrido; saída 0.
- [ ] Outro processo segura a trava → `acquire` falha com `busy`, saída 4 pelo contrato, com
  `details`.
- [ ] Processo dono morto → `status` mostra a trava livre.
- [ ] `wordcut --json status` e `wordcut status --json` dão o mesmo resultado.
- [ ] Argumento inválido com `--json` → stdout só com `{"error": {"code": "invalid_argument", …}}`
  e saída 2; sem `--json`, stdout vazio e mensagem no stderr.
- [ ] Exceção inesperada → `internal_error`, saída 1, sem traceback no stdout.
- [ ] `KeyboardInterrupt` → saída 130.
- [ ] `--version` imprime a versão e sai com 0.
- [ ] Banco com `user_version` antigo → migrações pendentes aplicadas sem perder dados.
- [ ] Um comando antigo (`wordcut overview <arquivo>`) continua funcionando.
- [ ] Quality gates limpos.
