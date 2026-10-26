# QA — 1.2.a.1 — Equipe e papéis (`member`)

## Plano de QA — 2026-10-26

**baseline_commit**: 18acfe5dcdf7d9d8ac1b268743abf1fdbcb1e6d2
**Componentes em escopo**:
- core: `packages/core/src/wordcut/db/migrations/0010_members.sql` (novo),
  `packages/core/src/wordcut/db/members.py` (novo), `packages/core/src/wordcut/service/members.py`
  (novo); `packages/core/src/wordcut/errors.py` só leitura (`last_admin` já existe);
- cli: `apps/cli/src/wordcut_cli/member.py` (novo), `apps/cli/src/wordcut_cli/__init__.py`;
- testes: `packages/core/tests/test_members_service.py`, `apps/cli/tests/test_member_command.py`;
- docs: `CHANGELOG.md`, `docs/architecture/README.md` §4 e, pela barra, `docs/cli.md` §12 e §17
  (ver D4).

**Suítes que valem como prova**:
- core: `uv run pytest packages/core/tests -q` (arquivo do passo:
  `packages/core/tests/test_members_service.py`; `packages/core/tests/test_db.py` continua verde
  com a migração 0010);
- cli: `uv run pytest apps/cli/tests -q` (arquivo do passo: `apps/cli/tests/test_member_command.py`);
- completa: `uv run pytest -q`;
- checagem estática: `uv run ruff check . && uv run ruff format --check . && uv run mypy`.

### Divergências do plan.md com o código no baseline

O plan.md foi escrito antes dos itens 7 a 16. A barra abaixo já considera o código real.

| # | O plan.md diz | O código no baseline tem | Recomendação (a barra cobra isto) |
|---|---|---|---|
| D1 | Migração `<próximo>_members.sql` | Última migração é `0009_renders.sql` (item 15); `test_db.py` lê a última do pacote | Criar `0010_members.sql`, sem `BEGIN`/`COMMIT` (docstring de `db.connect`), com comentário de cabeçalho no padrão das demais (`-- 1.2.a.1: ...`). `user_version` passa a 10. |
| D2 | Nada sobre `errors.py` | `last_admin` já está em `EXIT_CODES` com saída 5 (`errors.py:27`) e em `docs/cli.md` §5.3 | Não acrescentar nem alterar código de erro; usar `WordcutError("last_admin", ...)`. Diff em `errors.py` é divergência. |
| D3 | "Regra checada numa transação" | O código só usa `with connection:` (transação implícita, aberta no primeiro DML; nenhum `BEGIN IMMEDIATE` no repositório). Uma leitura da contagem de admins antes do `DELETE`/`UPDATE` roda fora da transação de escrita, e CLI e API gravam no mesmo arquivo (ADR-0005) | Checagem e escrita na mesma transação de escrita: `BEGIN IMMEDIATE` explícito antes de contar, ou um único `DELETE`/`UPDATE` condicional (subconsulta da contagem) com conferência de `rowcount`. Ver L1. |
| D4 | Passo 3 só em `CHANGELOG.md` e arquitetura §4 | `docs/cli.md` §12 não diz o formato da saída, a ordem da lista nem o retorno de `remove`; §17 diz "guarda e mostra só o e-mail e o papel", mas o cenário da spec mostra a data de inclusão e o FR-002 guarda datas | Passo 3 também atualiza `docs/cli.md` §12 (campos do item, ordem, saída de `remove`) e alinha §17 ("de dado pessoal, só o e-mail; além dele, papel e datas"). A spec prevalece (requisito da feature); o documento acompanha. |
| D5 | `member.py` sem detalhes de ajuda | `docs/cli.md` §3.5: o `--help` de comando de administrador MUST dizer isso; padrão `add_group`/`add_command(..., example=...)` com "— administrador" (`preset.py`), e `test_settings_command.py:338` já testa | Grupo e as quatro ações com "administrador" na ajuda e um `example=` pronto para copiar, com e-mail `@exemplo.org`. |
| D6 | Formato de saída não definido | `preset`: listagem `{"items": [...]}`, item único como objeto, apagar → `{"id", "deleted": true}`; datas por `datetime.now().astimezone().isoformat()` com `now` injetável | `list` → `{"items": [{email, role, created_at, updated_at}]}` em ordem estável (por `email`); `add` e `set-role` → o objeto do membro; `remove` → `{"email": <normalizado>, "removed": true}`. Datas ISO 8601 com fuso (§4.3). Serviço aceita `now` opcional, como `service.presets`. |
| D7 | `member add <email> --role assistant\|admin` sem dizer se `--role` é obrigatório | Notação de `docs/cli.md` §2: sem colchetes = obrigatório; `choices` do argparse já viram `invalid_argument` com `details.choices` (ADR-0015) | `--role` obrigatório, com `choices=("assistant", "admin")`; `set-role` com o papel posicional e as mesmas `choices`. O serviço valida o papel de novo (a API chama o serviço direto). |
| D8 | "Exemplos e testes: só e-mails `@exemplo.org`"; a spec usa `ana@exemplo.org` | CONTRIBUTING.md §6 e constituição §VI: dados fictícios, **sem nomes de pessoas** | Parte local por função, sem prenome: `admin@exemplo.org`, `assistente@exemplo.org`, `editor2@exemplo.org`. Vale para testes, `--help`, CHANGELOG e docs. |
| D9 | Nada sobre eco do e-mail em erro | ADR-0015: nenhum erro de uso repete valor digitado; o e-mail é dado pessoal (§17) | Nenhuma mensagem nem `details` de `invalid_argument`, `not_found` ou `last_admin` traz o e-mail; `details` no máximo `{"argument": "email"}` / `{"argument": "role", "choices": [...]}`. |

### Matriz por passo

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Banco e serviço | (a) migração 0010 cria `members` só com `email` (PK), `role` (CHECK `assistant`/`admin`), `created_at`, `updated_at` — nenhuma outra coluna (FR-002, LGPD); `test_db.py` verde. (b) `add_member` normaliza o e-mail (`strip` + minúsculas) e devolve `{email, role, created_at, updated_at}` com datas ISO 8601 com fuso; primeiro membro pode ser `assistant` sem admin existente. (c) `list_members` devolve todos, ordem estável por e-mail, com exatamente as quatro chaves. (d) `set_role` e `remove_member` acham o membro com o e-mail em outra caixa/espaços; `set_role` muda `role` e `updated_at`, mantém `created_at`; `remove_member` some da lista. (e) Último admin: remover ou rebaixar o único admin → `last_admin` (saída 5), também com assistentes presentes e também quando é o único membro; com dois admins, rebaixar ou remover um funciona; remover assistente quando nunca houve admin funciona. Nada muda no banco depois do `last_admin`. (f) Bordas: e-mail inválido (vazio, sem `@`, sem domínio com ponto, com espaço interno, dois `@`) → `invalid_argument` `{"argument": "email"}`; e-mail repetido (mesmo em outra caixa) → `invalid_argument`, sem duplicar; papel fora de `assistant\|admin` → `invalid_argument` com `choices`, antes do banco (nunca `IntegrityError`/`internal_error`); membro inexistente em `set_role`/`remove_member` → `not_found`. (g) Nenhuma mensagem nem `details` contém o e-mail (D9). (h) `role_of(conn, email)` → papel com e-mail em outra caixa; `None` para inexistente e para e-mail malformado ou vazio, sem exceção. (i) Checagem do último admin e escrita na mesma transação de escrita (D3, L1). | Testes de comportamento em `packages/core/tests/test_members_service.py` pela interface pública de `wordcut.service.members`, com banco real (`connect(Home(wordcut_home))`, molde de `test_presets_service.py`) e `now` fixo. (a) por `PRAGMA table_info(members)` num teste (de serviço ou de `test_db.py`). (i) por teste com segunda conexão que rebaixa o outro admin entre a leitura e a escrita, ou por inspeção de `BEGIN IMMEDIATE`/statement único + mutação. Mutações exigidas no `tdd.md`. Suíte core verde. |
| 2 — CLI | (a) grupo `member` registrado em `wordcut_cli/__init__.py`. (b) `member add admin@exemplo.org --role admin --json` → saída 0 e o objeto do membro; `member list --json` → `{"items": [...]}` com e-mail normalizado, papel e `created_at`; lista vazia → `{"items": []}` e texto legível sem erro. (c) `member set-role <email> admin` e `member remove <email>` funcionam, `remove` → `{"email", "removed": true}`. (d) Último admin → `{"error": {"code": "last_admin"}}`, saída 5. (e) E-mail inválido ou repetido → saída 2 `invalid_argument`; papel inválido em `--role` e em `set-role` → saída 2 com `details.choices == ["assistant", "admin"]`; `--role` ausente → saída 2; inexistente → saída 3 `not_found`. (f) Nenhuma saída de erro (stdout e stderr) repete o e-mail digitado. (g) `--help` do grupo e das quatro ações traz "administrador" e um exemplo com `@exemplo.org`. (h) `--json` antes e depois da ação; sem `--json`, resultado legível no stdout e erro só no stderr. | Testes em `apps/cli/tests/test_member_command.py` via `main([...])` e `capsys`, no molde de `test_preset_command.py` e do teste de ajuda de `test_settings_command.py:338`. Suíte cli verde. |
| 3 — Documentação | `CHANGELOG.md` em `[Não lançado] / Adicionado` cita `member list/add/set-role/remove`, a tabela `members` (migração 0010), `last_admin` e o que se guarda (LGPD). `docs/architecture/README.md` §4: `service.members` (com `role_of` para o item 19) na linha "Camada de serviço", os quatro comandos na linha "CLI" e a tabela/migração/repositório `db.members`. `docs/cli.md` §12 com campos, ordem e saída de `remove`; §17 alinhado (D4). Nenhum e-mail fora de `@exemplo.org`, nenhum prenome. | Inspeção de `git diff 18acfe5 -- CHANGELOG.md docs/`, conferida contra o comportamento que os testes dos passos 1 e 2 provam. `git diff 18acfe5 \| grep -nE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+' \| grep -v '@exemplo\.org'` vazio (fora `noreply`/atribuição). |

### Matriz por critério de aceite

| Critério de aceite | O que o cobre |
|---|---|
| Spec · Cenário "liberar e listar": `member add <email> --role assistant` + `member list --json` → e-mail em minúsculas, papel e data de inclusão | Passo 2 (b) com e-mail digitado em caixa mista + Passo 1 (b, c); mutação "sem `.lower()`" vermelha |
| Spec · Cenário "mudar papel e remover": `set-role <email> admin` e depois `remove` → papel muda, membro some | Passo 2 (c) + Passo 1 (d) |
| Spec · Cenário "último administrador": remover ou rebaixar o único admin → `last_admin`, saída 5 | Passo 2 (d) + Passo 1 (e, i); as duas operações, cada uma com sua mutação |
| Borda: e-mail inválido → `invalid_argument` | Passo 1 (f) + Passo 2 (e), sem eco (Passo 1 g, Passo 2 f) |
| Borda: e-mail já liberado → `invalid_argument`, sem duplicar | Passo 1 (f) com caixa diferente; contagem da lista inalterada |
| Borda: membro inexistente → `not_found` | Passo 1 (f) + Passo 2 (e), em `set-role` e `remove` |
| Borda: papel fora de `assistant\|admin` → `invalid_argument` | Passo 1 (f) (serviço) + Passo 2 (e) (`--role` e `set-role`, com `choices`) |
| FR-001: `member list/add/set-role/remove` conforme `docs/cli.md` §12 | Passo 2 (a–e, g) |
| FR-002: só e-mail, papel e datas guardados | Passo 1 (a) (colunas da tabela) + Passo 1 (c) / Passo 2 (b) (chaves do item) |
| FR-003: nunca sem administrador depois do primeiro | Passo 1 (e, i) |
| FR-004: `role_of(email)` para a API | Passo 1 (h) |
| Verificação · `member add` + `member list --json` → e-mail normalizado, papel, data | = Cenário "liberar e listar" |
| Verificação · `set-role` e `remove` funcionam; último admin → `last_admin` | = Cenários "mudar papel e remover" e "último administrador" |
| Verificação · e-mail inválido, repetido ou papel inválido → `invalid_argument`; inexistente → `not_found` | = Bordas acima |
| Verificação · `role_of` devolve o papel ou `None` | Passo 1 (h) |
| Verificação · quality gates limpos | `uv run pytest -q` e `uv run ruff check . && uv run ruff format --check . && uv run mypy` verdes |

### Lacunas do plan.md (o que fica PARCIAL sem a correção)

- **L1** — Concorrência do último admin (D3): com `with connection:` e a contagem lida antes do
  primeiro DML, a CLI e a API podem rebaixar admins diferentes ao mesmo tempo e zerar os admins,
  violando FR-003. Sem `BEGIN IMMEDIATE` (ou statement único condicional) e sem teste ou
  mutação que prove isso, o passo 1 fica PARCIAL.
- **L2** — Formato de saída e ordem da lista não decididos (D6); `docs/cli.md` §12 não os traz.
  Contrato diferente do da barra sem atualizar §12 deixa os passos 2 e 3 PARCIAL.
- **L3** — `docs/cli.md` §17 ("mostra só o e-mail e o papel") contradiz o cenário da spec, que
  mostra a data (D4). Sem alinhar §17, o passo 3 fica PARCIAL.
- **L4** — `role_of` com e-mail malformado ou vazio: o plano não diz. A barra é conservadora:
  `None`, sem exceção (a API decide "sem acesso"). Exceção aqui é FAIL no passo 1 (h).
- **L5** — Exemplo `ana@exemplo.org` da spec tem prenome (D8). Prenome em teste, ajuda ou doc
  deixa o passo correspondente PARCIAL.
- **L6** — Eco do e-mail em erro (D9) não está no plano. Mensagem ou `details` com o e-mail é
  FAIL no passo 1 (g) / passo 2 (f).
- **L7** — `set-role` para o mesmo papel: não decidido. A barra aceita sucesso idempotente
  (saída 0, objeto do membro); `last_admin` só quando o papel muda de `admin` para `assistant`.
  Erro nesse caso deixa o passo 1 PARCIAL.

## Rodada 1 — 2026-10-26 — working tree sobre 18acfe5

**baseline_commit**: 18acfe5dcdf7d9d8ac1b268743abf1fdbcb1e6d2
**Componentes avaliados**: core (migração 0010, `db.members`, `service.members`), cli (`member.py`,
`__init__.py`, `contract.py`), testes, docs (`CHANGELOG.md`, `docs/architecture/README.md` §4,
`docs/cli.md` §12 e §17)
**Suítes**: completa ✅ (1275 / 0 falhas; baseline 1204) · arquivos dos passos ✅ (82 / 0 falhas,
com `test_cli.py` e `test_db.py`) · `ruff check` ✅ · `ruff format --check` ✅ · `mypy` ✅

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Banco e serviço | PASS | (a) `test_the_members_table_keeps_only_the_email_the_role_and_the_dates`; (b, c) `test_an_added_member_is_listed_…`, `test_members_are_listed_by_email_…`; (d) `test_set_role_finds_the_member_in_another_case_…`, `test_removing_a_member_in_another_case_…`; (e) `test_removing_the_only_admin_…`, `test_demoting_the_only_admin_…` (sozinho e com assistente, banco inalterado), `test_with_two_admins_…`; (f) inválido (9 casos), repetido em outra caixa, papel inválido no add e no set_role, `not_found` no set_role e no remove; (g) `test_no_error_repeats_the_email` (6 casos); (h) `test_role_of_…` (5 casos de `None`); (i) `BEGIN IMMEDIATE` em `_writing` (`service/members.py:81-92`) e `test_two_admins_demoted_at_the_same_time_from_two_connections_…`. Todas as mutações exigidas no plano de QA vermelhas (22/22, a do `BEGIN IMMEDIATE` 6/6 execuções). `errors.py` intocado (D2); migração sem `BEGIN`/`COMMIT`, `user_version` 10 (D1) |
| 2 — CLI | PASS | `test_member_command.py` cobre (a)–(h): registro, `list`/`add` com caixa mista, `set-role` e `remove` → `{"email", "removed": true}`, `last_admin` saída 5 nas duas operações, bordas com saídas 2/3 e `details.choices`, `--role` ausente, nenhum eco do e-mail em stdout+stderr com e sem `--json`, ajuda com "— administrador" e `Exemplo:` no grupo e nas quatro ações, `--json` antes do grupo, lista vazia em texto. Smoke real com `WORDCUT_HOME` no scratchpad confere. Mutações 7/8 vermelhas; a sobrevivente (`set-role` sem `choices`) é equivalente na barra, porque o serviço revalida e devolve o mesmo erro (D7 está no código) |
| 3 — Documentação | PASS | `CHANGELOG.md` [Não lançado]/Adicionado com os quatro comandos, migração 0010, `last_admin`, LGPD e `role_of`; arquitetura §4 com a linha "Equipe" (tabela, migração, `db.members`), `service.members` na camada de serviço e os quatro comandos na CLI; `docs/cli.md` §12 com identidade normalizada, saídas, objeto do membro, ordem, idempotência e erros sem eco; §17 alinhado (D4/L3). Grep de e-mail da matriz vazio |

**Mudanças fora da lista de escopo do plano de QA** (`contract.py`, `test_cli.py`): justificadas.
As duas estão no "Contexto de código" do plan.md. `add_group(example=)` é o meio de D5 e repete
o desenho de `add_command`; `member` na constante de `test_cli.py` é consequência direta de
FR-001 (a mutação "member não registrado" a derruba). Efeito colateral fora da matriz, não
bloqueante: `formatter_class=RawDescriptionHelpFormatter` passou a valer para **todos** os grupos,
com ou sem exemplo, e a descrição deixou de quebrar linha (`wordcut cut --help` imprime 102
colunas num terminal de 80; `criteria` e `settings` em terminal estreito). É o mesmo
comportamento que `add_command` já tinha nos comandos; nenhum teste cobre. Fica como sugestão
para quem revisar o PR: aplicar o formatador só quando houver `example`.

**LGPD**: código, testes, ajuda e docs usam só `admin@`, `assistente@` e `editor2@exemplo.org`
(e variantes de caixa ou propositalmente inválidas no mesmo domínio); nenhum prenome; a spec já
não traz `ana@` (D8/L5). Nenhum erro repete o e-mail (D9/L6).

**Comentários** (CONTRIBUTING §5): os novos são intenção (`_writing`, regex, rebaixamento),
referência (ADR-0004, ADR-0005, ADR-0015, FR-003, docs/cli.md §4.2), formato (regex) ou contrato
público (docstrings), todos em inglês; nenhum fora dos tipos.

### Critérios de aceite
- ✅ Cenário "liberar e listar" — `test_an_added_member_is_listed_…` (core e cli); mutação sem
  `.lower()` vermelha
- ✅ Cenário "mudar papel e remover" — `test_set_role_changes_the_role_and_remove_…` (cli) +
  passo 1 (d)
- ✅ Cenário "último administrador" — `test_removing_or_demoting_the_only_admin_is_last_admin_with_exit_code_5`
  + passo 1 (e, i); cada operação com sua mutação
- ✅ Borda e-mail inválido — `test_an_invalid_email_…` + cli `add-invalid-email`, sem eco
- ✅ Borda e-mail já liberado — `test_an_email_already_in_the_team_in_another_case_…` (lista com 1)
- ✅ Borda membro inexistente — `not_found` no set_role e no remove (core e cli)
- ✅ Borda papel inválido — serviço (add, set_role) e cli (`--role`, `set-role`) com `choices`
- ✅ FR-001 — `test_member_command.py` (a–e, g)
- ✅ FR-002 — `PRAGMA table_info(members)` + chaves do item no core e na cli
- ✅ FR-003 — último admin + teste das duas conexões
- ✅ FR-004 — `test_role_of_…` (papel em outra caixa; `None` para ausente, vazio e malformado)
- ✅ Verificação · `member add` + `member list --json` — = cenário "liberar e listar"
- ✅ Verificação · `set-role`, `remove`, `last_admin` — = cenários
- ✅ Verificação · `invalid_argument` / `not_found` — = bordas
- ✅ Verificação · `role_of` — FR-004
- ✅ Verificação · quality gates — `uv run pytest -q` 1275 ✅; ruff check/format e mypy ✅

### Veredito geral: PASS
Os três passos e os 16 critérios cobertos, suíte e checagens verdes. Não bloqueante: a quebra de
linha das descrições dos grupos (efeito do `contract.py`) e a mutação equivalente de `set-role`.
