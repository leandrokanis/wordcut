# QA — 1.1.e.1 — Ver e escolher cortes sugeridos (`cut list/show/choose/discard/restore`)

## Plano de QA — 2026-10-26

**baseline_commit**: ebbe27e191101f560f7c06ecea5272d3aead8c43
**Componentes em escopo**: `packages/core` (`wordcut.db.cuts`, `wordcut.cuts.assembly` (novo),
`wordcut.service.cuts` (novo)); `apps/cli` (`wordcut_cli.cut` (novo), `wordcut_cli.__init__`,
`wordcut_cli.legacy` (conflito do `cut`, ver L1)); documentação (`CHANGELOG.md`,
`docs/architecture/README.md` §4 e, se L1 renomear o comando antigo, `README.md` e
`skills/video-cortar-pregacao/SKILL.md`)
**Suítes que valem como prova**:
- core: `uv run pytest packages/core/tests/test_cuts_service.py -q` (e
  `packages/core/tests/test_cuts_repository.py`, se o repositório ganhar teste próprio)
- cli: `uv run pytest apps/cli/tests/test_cut_command.py apps/cli/tests/test_legacy_commands.py -q`
- suíte completa: `uv run pytest -q`
- checagem estática: `uv run ruff check . && uv run ruff format --check . && uv run mypy`

Fontes da barra: `spec.md`, `plan.md`, docs/requirements/features/1.1.e-choose-suggested-scripts.md,
docs/cli.md §4.3, §5, §8, §8.1, §8.2, §8.4, constituição §I, e o código no baseline
(`db/cuts.py`, `db/transcripts.py`, `service/sermons.py`, `suggestion/__init__.py`,
`apps/cli/src/wordcut_cli/`). Execução automatizada: onde a skill pediria decisão, foi
escolhida a opção mais conservadora, registrada como lacuna (L*).

### Divergências do plan.md com o código do baseline

| # | O plan.md diz | O código no baseline | Ajuste recomendado |
|---|---|---|---|
| D1 | Alterar `db/cuts.py` para criar `by_id`, `of_sermon`, `set_status` | `of_sermon` já existe (ordem por `id`, usado por `sermon show`); faltam `by_id` e `set_status` | Criar só `by_id` e `set_status`; não mudar a ordem de `of_sermon` (o `sermon show` depende dela, §7.2); a ordem "descartados por último" fica no serviço |
| D2 | Formato do corte: `segments`, `words`, `caption`, `render_options`, `renders` | O corte gravado tem `segments` só com `from_word`/`to_word` (JSON), `range_start_word`/`range_end_word`, `source`, `preset_id`, `edited`; `service.sermons.shown_cut` já serializa esse núcleo | Montar `cut show` e cada item de `cut list` como `shown_cut(row)` + `sermon_id` + `text` + `duration`; no `show`, trocar `segments` pelos enriquecidos (`from_word`, `to_word`, `start`, `end`, `text`) e acrescentar `words`, `caption`, `render_options`, `renders`. Assim os campos de §7.2 e §8.2 coincidem e a "faixa na pregação" sai de `range_start_word`/`range_end_word` |
| D3 | "correções de grafia aplicadas quando existirem (item 13)"; campo `corrected` sem tipo | Não há tabela nem coluna de correções no baseline (migrações 0001–0007) | Neste item, `words[].corrected` = `null` sempre e `text` = texto original; o plano fixa o tipo (`str \| None`, o texto corrigido) para o item 13 preencher. Não criar tabela de correções aqui |
| D4 | `caption: {}`, `render_options: {}` constantes | Colunas `caption`/`render_options` existem e são lidas como `dict \| None` | `row.caption or {}` e `row.render_options or {}` (spec, Pressupostos: nulo = padrões) — não constante, para os itens 14 e 15 não terem de mexer aqui |
| D5 | Trechos resolvidos "a partir das palavras" | `db.transcripts` só tem `words_of(conn, sermon_id)`; `word_id` é estável mas o que define a ordem é `position` | Resolver cada trecho por `position` (índice `id → posição` sobre `words_of`), não por aritmética de IDs; `from_word`/`to_word` inclusivos |
| D6 | Grupo `cut` registrado em `__init__.py` | `legacy.py:139` já registra o comando de topo `cut` (CLI anterior); no Python 3.11 do projeto, `add_parser("cut")` repetido levanta `ArgumentError: conflicting subparser: cut` | Ver L1 |
| D7 | Duração "soma de `end − start`" | `suggestion._estimated_duration` usa a mesma soma × 0,82 (`CLEANED_SHARE`) e arredonda a `MILLISECOND_DIGITS` | Duração bruta (sem ×0,82), arredondada a 3 casas como o resto do código |

### Matriz por passo

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Montagem | Texto montado = palavras de cada trecho na ordem do trecho (de `from_word` a `to_word`, inclusive), trechos na ordem em que o corte toca, unidos por um espaço. Duração = Σ (`end` da última palavra − `start` da primeira) por trecho, sem fator de limpeza, arredondada ao ms. Um corte com trecho fora de ordem (§8.10: `1201–1230` antes de `1188–1199`) monta o texto na ordem do corte. `words` e `segments` do `show` saem da mesma montagem | Teste de comportamento em `packages/core/tests/test_cuts_service.py` (via `show_cut`/`list_cuts`) ou teste direto do módulo `wordcut.cuts.assembly`, com palavras gravadas por `transcripts.replace` e cortes por `cuts.insert_many` num banco temporário. Valores esperados escritos à mão (não recalculados pela mesma fórmula). Mutações exigidas (vermelhas): inverter a ordem dos trechos; excluir `to_word` (off-by-one); aplicar ×0,82; unir trechos sem espaço; usar `start`/`end` do primeiro e último trecho em vez da soma |
| 2 — Serviço | `list_cuts`: `{"items": [...]}`; `suggested` e `chosen` intercalados por `id`, depois `discarded` por `id`; `status` filtra; pregação inexistente → `WordcutError("not_found")` com `details.sermon_id`; pregação sem cortes (ou não processada) → `items: []`. `show_cut`: formato de D2; corte inexistente → `not_found` com `details.cut_id`. `set_cut_status`: `choose` → `chosen`, `discard` → `discarded`, `restore` → `suggested` só a partir de `discarded`; repetição idempotente; nada além de `status`/`updated_at` muda (trechos, faixa, título, `source`, `preset_id`, `edited` = false, `caption`, `render_options`); ID inexistente → `not_found`, sem escrita | `packages/core/tests/test_cuts_service.py`, banco temporário. Conteúdo intocado: comparar a `CutRow` lida por `cuts.by_id` antes e depois, campo a campo, exceto `status`/`updated_at` (`dataclasses.replace`). Mutações exigidas (vermelhas): ordenar descartados primeiro; ordenar tudo por `id` ignorando estado; `set_status` marcar `edited = 1`; `restore` de `chosen` virar `suggested` (contraria spec, L2); omitir o filtro de `status` |
| 3 — CLI | `wordcut cut list --sermon <id> [--status S]`, `cut show <id>`, `cut choose|discard|restore <id>`: com `--json`, um único documento no stdout (objeto; listagem em `items`), saída 0; erro `{"error": {...}}` com `not_found` → 3, `--sermon` ausente/`id` mal formado/`--status` fora de `suggested|chosen|discarded` → 2 com `details.argument` (e `details.choices` no `--status`); `--json` antes ou depois da ação; sem `--json`, texto em português no stdout e erro no stderr com stdout vazio; `--help` de cada ação com exemplo pronto; o comando antigo continua acessível conforme L1 | `apps/cli/tests/test_cut_command.py` com `main(argv)` + `capsys` + `wordcut_home`, no padrão de `test_sermon_command.py`; dados semeados pelos repositórios do core. `apps/cli/tests/test_legacy_commands.py` continua verde. Mutação exigida (vermelha): trocar o código de saída de `not_found`; imprimir lista nua em vez de `{"items": ...}` |
| 4 — Documentação | `CHANGELOG.md` [Não lançado]/Adicionado cita `cut list/show/choose/discard/restore`; `docs/architecture/README.md` §4 cita `service.cuts`, `cuts.assembly` e os comandos `cut` (linhas "Camada de serviço" e "CLI"); se L1 renomear o comando antigo: `README.md` (linha 135), `skills/video-cortar-pregacao/SKILL.md` (linha 41) e CHANGELOG atualizados no mesmo commit | Leitura do diff contra o baseline (`git diff ebbe27e -- CHANGELOG.md docs/ README.md skills/`). Sem ADR exigida (nenhuma decisão de arquitetura nova), salvo se L1 for resolvida de modo que mude a política da CLI antiga |

### Matriz por critério de aceite

| Critério de aceite | O que o cobre |
|---|---|
| Spec — Cenário: listar (`items` com id, título, texto, duração e estado; descartados por último; `--status` filtra) | Passo 2 (ordem, filtro, campos) + Passo 3 (`cut list --json`, envelope `items`, `--status`) |
| Spec — Cenário: detalhar (texto, duração, estado, faixa, `segments` com tempos e texto, `words` com `word_id`/texto/tempos/correção, `caption`, `render_options`, `renders: []`) | Passo 1 (valores) + Passo 2 (chaves exatas de D2/D3/D4) + Passo 3 (`cut show --json`) |
| Spec — Cenário: escolher, descartar, restaurar sem mudar trechos | Passo 2 (comparação da `CutRow` antes/depois em `choose` → `discard` → `restore`) + Passo 3 (estados no JSON das três ações) |
| Spec — Borda: ID inexistente → `not_found` | Passo 2 (`show_cut`, `set_cut_status`) + Passo 3 (saída 3, `{"error": {"code": "not_found"}}`) para `show`, `choose`, `discard`, `restore` |
| Spec — Borda: pregação inexistente no `list` → `not_found` | Passo 2 + Passo 3 (`cut list --sermon 999 --json` → 3) |
| Spec — Borda: repetir transição é idempotente (saída 0) | Passo 2 (mesmo estado, conteúdo igual) + Passo 3 (segundo `choose`/`discard` sai 0) |
| Spec — Borda: `restore` de corte não descartado → idempotente, devolve o corte | Passo 2 (`restore` de `suggested` e de `chosen` mantém o estado, L2) + Passo 3 (saída 0, corte no stdout) |
| FR-001 — `list` com texto, duração e estado, descartados por último | Passo 1 + Passo 2 + Passo 3 |
| FR-002 — `show` conforme §8.2 | Passo 2 + Passo 3 (asserção das chaves completas, não por subconjunto) |
| FR-003 — `choose`/`discard`/`restore` mudam só o estado | Passo 2 (comparação campo a campo; mutação `edited = 1` morre) |
| FR-004 — texto = concatenação dos trechos em ordem; duração = soma das faixas, sem limpeza | Passo 1 (trecho fora de ordem; mutação ×0,82 morre) |
| Verificação — `cut list --json` com texto/duração/estado, descartados por último, `--status`, pregação inexistente → `not_found` | Passo 3 |
| Verificação — `cut show --json` no formato de §8.2 | Passo 3 |
| Verificação — `choose` → `discard` → `restore` mudam só o estado; trechos idênticos | Passo 2 + Passo 3 |
| Verificação — repetição idempotente; ID inexistente → `not_found` | Passo 2 + Passo 3 |
| Verificação — quality gates limpos | `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` |
| Constituição §I — o assistente não altera o conteúdo | Mesmo teste de FR-003; `show` e `list` não escrevem (L3) |

### Lacunas do plan.md (decisão conservadora adotada como barra)

- **L1 — conflito com o `cut` da CLI anterior.** `legacy.py:139` registra `cut`; registrar o
  grupo novo quebra o parser inteiro (todos os comandos, não só `cut`). README (l. 135) e a
  skill `video-cortar-pregacao` (l. 41) usam `wordcut cut <link> --dir …`. Barra: o plano
  decide e registra; o mais conservador é **renomear** o comando antigo (p. ex. `cut-sermon`),
  mantendo comportamento e teste, e atualizar README, skill e CHANGELOG no mesmo commit — não
  removê-lo antes do item 18. Sem decisão, Passo 3 fica PARCIAL.
- **L2 — `restore` de corte `chosen`.** Plano: "`restore` → `suggested`" (sem condição);
  spec e §8.4: só um descartado volta a `suggested`, o resto é idempotente. Barra: a spec —
  `restore` só mexe em `discarded`.
- **L3 — `show` não muda estado.** A feature diz que, na interface, abrir um corte o marca
  escolhido; a CLI `show` é leitura (§8.2). Barra: `cut show` e `cut list` não escrevem.
- **L4 — retorno de `choose`/`discard`/`restore`.** Não decidido no plano. Barra: o mesmo
  objeto de `cut show`.
- **L5 — `updated_at` na repetição.** Não decidido. Barra recomendada: transição sem mudança
  não escreve (`updated_at` intacto); se o plano escolher reescrever, registrar.
- **L6 — campos de `list`.** O plano não fixa o item. Barra: `shown_cut` + `sermon_id` +
  `text` + `duration` (D2), sem `words`.
- **L7 — `details` do `not_found`.** Barra: `{"cut_id": N}` no corte e `{"sermon_id": N}` na
  pregação, como `service.sermons._existing`.
- **L8 — pregação sem transcrição ou palavra ausente.** Um corte cujo `from_word`/`to_word`
  não está entre as palavras da pregação não deveria existir (reprocessar apaga os cortes),
  mas o plano não diz o que acontece. Barra: `internal_error` com mensagem em português, sem
  traceback; não exigir teste se o plano registrar que é invariante do banco.
- **L9 — texto sem `--json`.** Não definido. Barra: uma linha por corte com id, estado em
  português (sugerido/escolhido/descartado), duração e título; erro só no stderr.
- **L10 — arquivos de teste.** O plano não lista teste para `cuts.assembly` nem para
  `db.cuts.by_id`/`set_status`. Aceito testar pelo serviço (interface pública); o repositório
  pode ganhar caso em `test_cuts_repository.py`.

## Rodada 1 — 2026-10-26 — working tree sobre ebbe27e

**baseline_commit**: ebbe27e191101f560f7c06ecea5272d3aead8c43
**Componentes avaliados**: `packages/core` (`db.cuts`, `cuts.assembly`, `service.cuts`,
`service.sermons`), `apps/cli` (`cut`, `legacy`, `__init__`), documentação
**Suítes**: suíte completa ✅ (927 / 0 falhas; core 610, cli 316) ·
`test_cuts_service.py` ✅ (21) · `test_cut_command.py` + `test_legacy_commands.py` +
`test_cli.py` ✅ (34) · ruff check ✅ · ruff format --check ✅ · mypy ✅
**Mutações** (cópia no scratchpad, árvore de trabalho intocada): 23 de 23 mortas no conjunto
exigido pela matriz e complementares; fora dele, `list` regravando só `updated_at` sobrevive
(ver Observações).

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Montagem | PASS | `test_cut_text_joins_its_segments_in_the_order_it_plays_and_duration_adds_their_spans` (trecho fora de ordem, 1,9 à mão), `test_cut_segments_carry_their_times_and_text_…`; mortas: ordem invertida, `to_word` exclusivo, ×0,82, sem espaço, primeiro/último em vez da soma, sem arredondar; `cuts/assembly.py` resolve por posição (D5) |
| 2 — Serviço | PASS | `service/cuts.py` com `choose_cut`/`discard_cut`/`restore_cut`, os nomes do Contexto de código do plan.md; a matriz julga o comportamento, não o nome `set_cut_status`, e serve. Ordem, filtro, `not_found` com `cut_id`/`sermon_id` (L7), L2, L4, L5, D2–D4 cobertos; conteúdo intocado por `replace(before, updated_at=LATER)`; mortas: descartados primeiro, tudo por id, `edited = 1`, restore de `chosen`, filtro ignorado, repetição grava, `caption` constante, `corrected` preenchido |
| 3 — CLI | PASS | `test_cut_command.py` (30): envelope `items`, 0/2/3 com `details.argument`/`choices`, `--json` antes/entre/depois, texto em português (L9), erro só no stderr, `--help` com exemplo; L1 resolvida como `cut-sermon` com teste que fica vermelho com o `legacy.py` do baseline; mortas: código do `not_found`, lista nua, `--status` não repassado, `restore` → `choose` |
| 4 — Documentação | PASS | `CHANGELOG.md` (Adicionado e Alterado), `docs/architecture/README.md` §4 (serviço e CLI), `README.md` l. 135 e `skills/video-cortar-pregacao/SKILL.md` l. 41 com `cut-sermon`; nenhuma outra referência ao `cut <link>` fora de `specs/`. "Mesmo commit" não verificável: sem commit por decisão do orquestrador |

### Pontos levantados pelo implementador

1. **Nomes das transições** — aceito. O plan.md (Contexto de código) fixa
   `choose_cut`/`discard_cut`/`restore_cut`; `set_cut_status` na matriz descrevia o
   comportamento, que é o mesmo.
2. **L8** — aceito. O plan.md registra a invariante; sondado na cópia: corte com `to_word`
   inexistente → `cut show`/`cut list` saem 1 com `internal_error`, "Erro interno
   inesperado.", sem traceback, em JSON e em texto. É o que a L8 pede.
3. **Testes de guarda** — aceitos. Cada guarda morde: `change_only_the_status` mata `edited = 1`;
   os `not_found` matam `details` e código de saída; `cut-sermon` fica vermelho sem o rename;
   `not_processed_yet_lists_no_cuts` cobre `items: []` da matriz.

### Critérios de aceite
- ✅ Cenário listar — `test_list_with_json_prints_the_items_…_discarded_last`, `test_list_by_status_…` (cli); `test_cuts_are_listed_…`, `test_listed_cut_has_…` (core)
- ✅ Cenário detalhar — `test_shown_cut_has_the_sermon_cut_fields_…` (chaves completas), `test_show_with_json_prints_the_whole_cut`
- ✅ Cenário escolher/descartar/restaurar — `test_choosing_discarding_and_restoring_change_only_the_status_of_the_cut`, `test_choose_discard_and_restore_change_the_state_and_keep_the_segments`
- ✅ Borda: ID inexistente → `not_found` — `test_showing_a_cut_…`, `test_changing_the_state_of_a_cut_…`, `test_a_sermon_or_cut_that_does_not_exist_…_exits_3`
- ✅ Borda: pregação inexistente no `list` — `test_listing_the_cuts_of_a_sermon_that_does_not_exist_is_not_found` + caso CLI
- ✅ Borda: repetição idempotente — `test_repeating_a_transition_writes_nothing`, `test_a_transition_with_nothing_to_change_exits_0_…`
- ✅ Borda: `restore` não descartado — `test_restoring_a_cut_that_is_not_discarded_leaves_it_as_it_was` [suggested, chosen] + CLI
- ✅ FR-001 — listagem core + CLI (texto, duração, estado, ordem, filtro)
- ✅ FR-002 — asserção de igualdade completa no core; conjunto de chaves na CLI
- ✅ FR-003 — comparação da `CutRow` campo a campo; mutação `edited = 1` morre
- ✅ FR-004 — trecho fora de ordem; ×0,82 morre
- ✅ Verificação: `cut list --json` — testes CLI de listagem e `not_found`
- ✅ Verificação: `cut show --json` — `test_show_with_json_prints_the_whole_cut`
- ✅ Verificação: `choose` → `discard` → `restore` — teste CLI e core
- ✅ Verificação: idempotência e `not_found` — testes CLI e core
- ✅ Verificação: quality gates — pytest, ruff check, ruff format --check, mypy verdes
- ✅ Constituição §I — FR-003 e `show` sem escrita (mutação morre); ver Observações sobre o `list`

### Observações (não rebaixam o veredito)
- Mutação fora do conjunto exigido: `list_cuts` regravando só `updated_at` sobrevive; nenhum
  teste confere `updated_at` depois de um `list`. O conteúdo (§I) e o estado continuam
  protegidos (`list` marcando `chosen` morre em 4 testes). Vale um caso se a L3 for cobrada
  ao pé da letra numa rodada futura.
- Política de comentários (CONTRIBUTING §5): os comentários novos são de intenção, formato ou
  referência, em inglês, com fonte. `# fmt: skip` sem motivo segue a prática do baseline
  (10 ocorrências).

### Veredito geral: PASS
Os 4 passos PASS, 17/17 critérios cobertos, suítes e checagens verdes.
