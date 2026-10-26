# QA — 1.1.b.2 — Delimitar a pregação pela CLI (`sermon trim`)

## Plano de QA — 2026-10-26

**baseline_commit**: aef33ce865e3df33508b8268c2afa22a98517b9a
**Componentes em escopo**: `packages/core` (`wordcut.service.sermons`, `wordcut.db.sermons`,
`wordcut.timefmt`); `apps/cli` (`wordcut_cli.sermon`); `CHANGELOG.md` (e `docs/cli.md` só se o
contrato mudar).
**Suítes que valem como prova**:
- core: `uv run pytest packages/core/tests/test_sermon_trim.py -q` (+ `test_timefmt.py`,
  `test_sermons_service.py`, `test_sermons_repository.py` como regressão)
- cli: `uv run pytest apps/cli/tests/test_sermon_trim_command.py -q` (+ `test_sermon_command.py`,
  `test_cli_contract.py` como regressão)
- suíte completa: `uv run pytest -q`
- estática: `uv run ruff check . && uv run ruff format --check . && uv run mypy`

Fontes da barra: `spec.md`, `plan.md`, docs/cli.md §2 (formato de `T`), §3.4, §5.3, §7.1, §7.3;
código no baseline. Sem rastreador: os critérios saem dos cenários do spec e da Verificação do
plano. Onde o plano não decidiu, a barra adota a opção mais conservadora e a registra em
**Lacunas** (execução automatizada aprovada pelo administrador; sem perguntas).

Prova aceita: teste de comportamento pela interface pública — `trim_sermon`/`create_sermon`
com SQLite real em `WORDCUT_HOME` temporário no core; `wordcut_cli.main([...])` com `capsys`
e `FakeLive` na CLI. Não vale: teste que só verifica chamada de mock, nem asserção sobre
`message`. Erros são julgados por `code`, saída e `details` (docs/cli.md §5.2).

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Regras no serviço | (a) `created`, `trimmed` e `failed` → `trimmed`, com `live_start`/`live_end` gravados e relidos do banco; (b) `processed` grava as bordas, mantém `processed` e devolve `needs_reprocess: true` (e `false`/ausente nos outros estados); (c) `processing` → `busy` (saída 4), nada muda; (d) faixa < 60 s → `sermon_too_short` (saída 5), nada muda; **60,000 s exatos é aceito**, 59,999 s é recusado; (e) `start < 0`, `start ≥ end`, `end > live_duration` → `invalid_argument` com `details` `start`, `end`, `live_duration`, nada muda; `end == live_duration` e `start == 0` aceitos; (f) ID inexistente → `not_found` com `details.sermon_id`; (g) bordas arredondadas a ms; (h) a resposta tem o formato de `show_sermon` com `duration = live_end − live_start` (L1); (i) `update_range` atualiza `updated_at` (L9) | pytest em `packages/core/tests/test_sermon_trim.py`, banco real, relendo por `show_sermon` após cada erro para provar "nada muda". Mutações cobradas no `tdd.md` (fronteira 60 s, `<`/`≤` dos limites, transição de estado, `needs_reprocess`) |
| 2 — `sermon trim` na CLI | (a) `sermon trim <id> --start 1:02:10 --end 1:48:30 --json` numa live de 2 h → saída 0, JSON igual ao de `sermon show <id> --json` (status `trimmed`, `live_start 3730.0`, `live_end 6510.0`, `duration 2780.0`); (b) os três formatos (`HH:MM:SS[.mmm]`, `MM:SS[.mmm]`, `754.2`) aceitos; (c) formato inválido → `invalid_argument`, saída 2, `details.argument` = `--start` ou `--end`; (d) `--start`/`--end` ausentes → `invalid_argument`; (e) `processed` → aviso no stderr contendo `sermon process --force`, stdout continua JSON válido, e o aviso sai também com `--quiet`; (f) erros do serviço chegam com o `code`/saída do contrato (`not_found` 3, `sermon_too_short` 5, `busy` 4); (g) saída legível sem `--json` mostra estado `delimitada` e as bordas | pytest em `apps/cli/tests/test_sermon_trim_command.py` via `main([...])`, `capsys` separando stdout/stderr, pregação criada pelo próprio `sermon create` com `FakeLive` de 7200 s |
| 3 — `create` com bordas | (a) `sermon create <link> --start … --end … --json` → saída 0, pregação `trimmed`, bordas gravadas, `created: true`; (b) só `--start` ou só `--end` → `invalid_argument` com `details.argument` do que falta, **e nenhuma pregação criada** (`sermon list` vazio); (c) bordas inválidas (curta, fora da live, início ≥ fim) → erro do trim **e nenhuma pregação criada** (L2); (d) vídeo já existente com bordas → comportamento de L3, testado; (e) `create` sem bordas inalterado (regressão de `test_sermon_command.py`) | pytest no core (`create_sermon(..., start, end)`) e na CLI; "nada criado" provado por `list_sermons`/`sermon list --json` |
| 4 — Documentação | CHANGELOG em `[Não lançado] › Adicionado` cita `sermon trim` e `--start/--end` no `create`; docs/cli.md só muda se o contrato mudar (ex.: campo `needs_reprocess` exposto ou regra de `live_duration` desconhecida, L5/L13) | leitura do diff contra o baseline |

| Critério de aceite | O que o cobre |
|---|---|
| Cenário "delimitar uma pregação criada" / Verificação 1 (FR-001, FR-006) | CLI 2(a): JSON completo comparado, incluindo `duration 2780.0` e saída 0 |
| Cenário "delimitar na criação" / Verificação 2 (FR-004) | CLI 3(a) + core 3(a) |
| Cenário "faixa curta demais" / Verificação 3 (FR-002) | core 1(d) com fronteira 60 s; CLI 2(f) com saída 5 e estado relido igual |
| Cenário "pregação já processada" / Verificação 4 (FR-005) | core 1(b) (pregação posta em `processed` por SQL direto, pois o item 5 não existe); CLI 2(e) |
| Borda: formatos aceitos e formato inválido → `invalid_argument` + `details.argument` | `test_timefmt.py` (incluindo L4) + CLI 2(b), 2(c) |
| Borda: `--start ≥ --end` → `invalid_argument` (FR-003) | core 1(e) com `start == end` e `start > end` |
| Borda: borda fora da live → `invalid_argument` (FR-003) | core 1(e) com `end = live_duration + 0.001` e `start < 0` (via serviço) |
| Borda: só uma borda no `create` → `invalid_argument` | CLI 3(b) |
| Borda / Verificação 6: ID inexistente → `not_found` | core 1(f) + CLI 2(f) |
| Transição `processing` → `busy` (Decisões técnicas) | core 1(c) |
| Verificação 5 (agregada) | soma das linhas de borda acima |
| Verificação 7: quality gates limpos | `uv run pytest -q`, `ruff check`, `ruff format --check`, `mypy` verdes |

### Lacunas (o plano não decidiu; barra adotada)

- **L1 — `duration` sempre `None`.** `_listed` (service/sermons.py) devolve `duration: None` fixo e o plano não lista essa mudança; o cenário exige `2780.0`. Barra: `duration = round(live_end − live_start, 3)` quando há bordas, em `list` e `show`.
- **L2 — "Mesma transação" sem mecanismo.** `db.sermons.insert` faz commit próprio (`with connection:`). Barra: `create` com bordas inválidas não deixa pregação no banco — validar as bordas contra `info.duration` antes do insert, ou insert + `update_range` numa transação só.
- **L3 — `create` de vídeo existente com bordas.** Não decidido. Barra: aplicar `trim_sermon` à existente (mesmas regras e aviso), devolvendo `created: false`; nunca ignorar as bordas em silêncio.
- **L4 — Parser frouxo.** No baseline, `parse_timestamp` aceita `nan`, `inf`, `1e3`, `1_0`, `1:-5` e `0:99`. `inf` gera JSON inválido (`Infinity`) e `nan` fura comparações. Barra: rejeitar valores não finitos e componentes negativos (`ValueError`) → `invalid_argument`; `0:99` e `1e3` ficam a critério, mas com teste.
- **L5 — `live_duration` nula.** É possível quando a live está no ar. Barra: sem duração conhecida, valer só `0 ≤ start < end` e o mínimo de 60 s, com `details.live_duration: null` nos erros e teste explícito; `sermon process` já barra live não terminada.
- **L6 — `busy` sem tarefa.** Não existe tabela de tarefas (3.1.a.2), e nada leva a pregação a `processing`. Barra: estado `processing` posto por SQL no teste → `busy`, saída 4, nada muda; `details` pode faltar até haver tarefa.
- **L7 — Ordem das validações.** Barra: `not_found` → `busy` → `invalid_argument` (limites) → `sermon_too_short`. Exemplo: `start > end` dá `invalid_argument`, não `sermon_too_short`.
- **L8 — Arredondar antes de validar.** Barra: arredondar a ms na entrada e validar o valor arredondado (`1:00.0004` vira 60,000 e é aceito).
- **L9 — `updated_at`.** A assinatura `update_range` não o atualiza. Barra: `updated_at` atualizado (relógio injetável) e provado pelo repositório.
- **L10 — Saída legível do `trim`.** Não definida. Barra: reaproveitar o render do `show`.
- **L11 — `needs_reprocess` no JSON.** FR-006 pede "formato de `sermon show`". Barra: `trim --json` igual a `show --json`; a CLI retira `needs_reprocess` antes de imprimir. Se decidir expor o campo, documentar em docs/cli.md §7.3.

## Rodada 1 — 2026-10-26 — working tree sobre aef33ce

**baseline_commit**: aef33ce865e3df33508b8268c2afa22a98517b9a
**Componentes avaliados**: `packages/core` (service/sermons, db/sermons, timefmt); `apps/cli` (sermon); `CHANGELOG.md`; `docs/cli.md`
**Suítes**: completa ✅ (320 / 0 falhas) · escopo core + cli ✅ (145 / 0 falhas) · ruff check ✅ · ruff format --check ✅ · mypy ✅ (44 arquivos)

Mutações (cópia da working tree no scratchpad, working tree intocada): 18 de 18 mortas, incluindo as 7 exigidas no plano de QA e L1, L3, L4, L8, L9, L10, L11 (detalhe no `tdd.md`, Rodada 1 · QA).

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Regras no serviço | PASS | `test_sermon_trim.py`: 1(a) `test_trimming_a_created_sermon_…`, `test_trimming_again_or_after_a_failure_…`; 1(b) `test_trimming_a_processed_sermon_keeps_it_processed_…`; 1(c) `…being_processed_is_busy_and_changes_nothing`; 1(d) fronteira 59,999/60,000 (inclusive 4043.757→4103.757); 1(e) `…outside_the_live_or_out_of_order…` + `…may_touch_both_ends…`; 1(f) `…unknown_sermon_is_not_found`; 1(g) `…kept_to_the_millisecond…`; 1(h) `…answered_as_shown_with_the_duration…` + list; 1(i) `test_sermons_repository.py::test_recorded_range_is_read_back_with_its_status_and_update_time`. L5 (`live_duration: null`), L6, L7 com teste |
| 2 — `sermon trim` na CLI | PASS | `test_sermon_trim_command.py`: 2(a) JSON == `show --json` com `duration 2780.0`, saída 0; 2(b) três formatos; 2(c) `abc`/`inf`/`1:-5` → saída 2, `details.argument`; 2(d) opção ausente; 2(e) aviso com e sem `--quiet`, stdout JSON; 2(f) 3/5/4/2 com `show` antes == depois; 2(g) texto = render do `show` (L10) |
| 3 — `create` com bordas | PASS | core e CLI: 3(a) `created: true`, `trimmed`, sem `needs_reprocess` no JSON; 3(b) borda única → `invalid_argument` com `details.argument` (`--start`/`--end` na CLI, `start`/`end` no serviço) e `list` vazio; 3(c) curta/invertida/fora da live → erro do trim e `list` vazio (validação antes do insert, `service/sermons.py` `_inserted`); 3(d) L3 com `created: false`, também em `processed` com aviso; 3(e) `test_sermon_command.py` verde |
| 4 — Documentação | PASS | CHANGELOG `[Não lançado]` › Adicionado (trim, `--start/--end`, duração) e › Alterado (parser estrito); docs/cli.md §7.1 (L2, L3) e §7.3 (limites, L5), mudanças de contrato previstas na barra |

### Critérios de aceite
- ✅ Cenário "delimitar uma pregação criada" / Verificação 1 (FR-001, FR-006) — `test_trim_with_json_answers_the_trimmed_sermon_as_show_does`
- ✅ Cenário "delimitar na criação" / Verificação 2 (FR-004) — `test_create_with_borders_answers_a_new_trimmed_sermon`, `test_sermon_created_with_borders_is_already_trimmed`
- ✅ Cenário "faixa curta demais" / Verificação 3 (FR-002) — `test_range_shorter_than_a_minute_…`, `test_range_of_exactly_one_minute_…`, CLI `test_refused_trim_…[sermon_too_short]`
- ✅ Cenário "pregação já processada" / Verificação 4 (FR-005) — `test_trimming_a_processed_sermon_keeps_it_processed_…`, `test_trimming_a_processed_sermon_warns_on_stderr_even_when_quiet_…`
- ✅ Formatos aceitos e formato inválido → `invalid_argument` + `details.argument` — `test_timefmt.py` (L4), `test_borders_are_accepted_as_…`, `test_border_in_an_unknown_format_…`
- ✅ `--start ≥ --end` → `invalid_argument` (FR-003) — `test_borders_outside_the_live_or_out_of_order_…` (`start == end`, `start > end`)
- ✅ Borda fora da live → `invalid_argument` (FR-003) — mesmo teste (`-0.001`, `7200.001`) + CLI `2:00:01`
- ✅ Só uma borda no `create` → `invalid_argument` — `test_create_with_a_single_border_names_the_missing_one_and_creates_nothing`
- ✅ ID inexistente → `not_found` / Verificação 6 — `test_trimming_an_unknown_sermon_is_not_found`, CLI `test_refused_trim_…[not_found]`
- ✅ `processing` → `busy` — `test_trimming_a_sermon_being_processed_is_busy_…`, `test_sermon_being_processed_is_busy_before_…`
- ✅ Verificação 5 (agregada) — soma das linhas acima
- ✅ Verificação 7: quality gates — pytest 320, ruff check, ruff format --check, mypy limpos

### Fatos relatados pelo implementador
- **`create` valida antes do insert e grava em dois commits** (insert, depois `update_range`): conforme L2, que aceita "validar antes do insert" como alternativa à transação única; a mutação que remove a validação prévia é morta por 5 testes. Resíduo fora da barra: uma falha de I/O entre os dois commits deixaria a pregação `created` sem bordas; não há teste nem exigência para isso.
- **`parse_timestamp` estrito vale também para os comandos antigos** (`legacy.py`: `live --start/--end`, `overview`, `cut --first-word/--last-word`): L4 decide sobre a função, não sobre o comando; `test_legacy_commands.py` verde e o CHANGELOG › Alterado registra. Não contradiz a barra. Efeito colateral sem teste: `.5` e `5.` deixam de ser aceitos.

### Comentários (CONTRIBUTING.md §5)
PASS. Todos os comentários acrescentados se classificam: referência (`1.1.b`, `docs/cli.md §2`, `§5.2`), intenção (validação antes do insert; `put_in_state` no lugar do item 5), formato (regex de `T`, unidade de `Borders`) e contrato (docstrings). Nenhuma diretiva de ferramenta nova.

### Veredito geral: PASS
Os 4 passos PASS contra a matriz e L1–L11; 12/12 critérios cobertos; suítes e checagens verdes; nenhum dos dois fatos do implementador contradiz a barra.
