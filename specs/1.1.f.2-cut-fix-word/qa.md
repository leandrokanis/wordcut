# QA — 1.1.f.2 — Corrigir a grafia de uma palavra da legenda (`cut fix-word`)

## Plano de QA — 2026-10-26

**baseline_commit**: 928f8e09c4dae0618d4455a193813b88113feab3
**Componentes em escopo**: `packages/core` (`wordcut.cuts.spelling` (novo),
`wordcut.cuts.assembly`, `wordcut.db.cuts`, migração `0008_word_fixes.sql` (nova),
`wordcut.service.cuts`); `apps/cli` (`wordcut_cli.cut`); documentação (`CHANGELOG.md`,
`docs/cli.md` §8.2, §8.3 e §8.5, `docs/architecture/README.md` §4)
**Suítes que valem como prova**:
- core: `uv run pytest packages/core/tests/test_spelling.py packages/core/tests/test_fix_word.py packages/core/tests/test_cuts_service.py packages/core/tests/test_cut_preview.py -q`
- regressão da exclusão de cortes com correção: `uv run pytest packages/core/tests/test_suggestion.py packages/core/tests/test_process_task.py packages/core/tests/test_cuts_repository.py -q`
- cli: `uv run pytest apps/cli/tests/test_cut_fix_word_command.py apps/cli/tests/test_cut_command.py apps/cli/tests/test_cut_preview_command.py -q`
- suíte completa: `uv run pytest -q`
- checagem estática: `uv run ruff check . && uv run ruff format --check . && uv run mypy`
  (CONTRIBUTING.md §3.2; o `mypy` lê a lista de `pyproject.toml`)

Fontes da barra: `spec.md`, `plan.md`, docs/requirements/features/1.1.f-adjust-form.md
(1.1.f.2, 1.1.f.3), docs/cli.md §3.5, §4.3, §5.3, §8.1–§8.3, §8.5, ADR-0015, constituição §I,
protótipo `docs/prototype/wordcut.html` (`lev` l. 585, `core` l. 592, `checkWord` l. 749,
`editCapWord` l. 755–766) e o código no baseline (`cuts/assembly.py`, `service/cuts.py`,
`db/cuts.py`, `db/migrations/0007_cuts.sql`, `suggestion/__init__.py`, `tasks/process.py`,
`apps/cli/src/wordcut_cli/cut.py`) e o plano de QA de 1.1.e.1 (D3). Execução automatizada:
onde a skill pediria decisão, foi escolhida a opção mais conservadora, registrada como lacuna.

### Divergências do plan.md com o código do baseline

O plan.md foi escrito antes dos itens 11 (1.1.e.1) e 12 (1.1.g.1).

| # | O plan.md diz | O código no baseline | Ajuste recomendado (barra) |
|---|---|---|---|
| D1 | Resposta `{"cut_id", "word_id", "original", "text", "corrected": bool}` | `cut show` já publica `words[].corrected` como `str \| None` (o texto corrigido) e `words[].text` como o original (`service/cuts.py` `_word`; QA 1.1.e.1 D3 fixou o tipo) | Mesmo nome, mesmo tipo: a resposta é a palavra como `cut show` a dá, mais o corte: `{"cut_id", "word_id", "text" (original), "start", "end", "corrected" (texto ou null)}`. Documentar em §8.5 |
| D2 | "`assembly.py` aplica correções" | `assemble(segments, words)` tem três chamadores (`list_cuts`, `show_cut`, `preview_cut`) e `AssembledSegment.text` une `word.text` | `assemble(segments, words, fixes)` com `fixes: Mapping[int, str]` (word_id → texto) **obrigatório**, para o `mypy` acusar o chamador esquecido; `AssembledSegment.text` e `AssembledCut.text` usam o texto corrigido; tempos e duração não mudam |
| D3 | Correção no "texto, prévia e `cut show`" | `cut list` (§8.1) também traz o texto montado, pela mesma `assemble` | `list_cuts` também aplica as correções, lidas numa consulta por pregação (não uma por corte) |
| D4 | `cut show` reflete a correção (sem dizer onde) | §8.2: `words` com "texto ... e correção aplicada, se houver"; o comentário em `_word` ("until then no word has one") fica falso | `words[].text` continua o original; `words[].corrected` = texto corrigido ou `null`; `segments[].text` e `text` com a correção. Remover o comentário de `_word` (política de comentários) |
| D5 | Passo 5: só CHANGELOG | docs/cli.md §8.3 diz "sem correção de grafia até 1.1.f.2"; §8.5 não tem resposta nem erros de uso; docs/architecture/README.md §4 (l. 102 e 106) lista `service.cuts` e os comandos `cut` | Passo 5 também atualiza §8.3 (texto com a correção), §8.5 (resposta de D1, `invalid_argument` com `word_id`/`text`, saídas) e a arquitetura §4 (`cuts.spelling`, tabela `word_fixes` na migração 0008, `cut fix-word`) |
| D6 | Migração `<próximo>_word_fixes.sql` "com FKs" | Migrações 0001–0007; `PRAGMA foreign_keys = ON` (`db/__init__.py:40`); `tasks/process.py:49–50` apaga cortes e depois palavras; `suggestion/__init__.py:101` apaga sugeridos não editados; `sermon delete` em cascata | `0008_word_fixes.sql`; `cut_id REFERENCES cuts (id) ON DELETE CASCADE` e `word_id REFERENCES words (id) ON DELETE CASCADE`. Sem CASCADE, reprocessar e `sermon suggest` quebram com erro de FK quando houver correção |
| D7 | Nada sobre `edited` | `sermon suggest` (2.1.b.2) apaga os `suggested` com `edited = 0` | Ver L1 |

### Matriz por passo

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Trava pura | `word_core`: minúsculas (L2), remove o que não é letra, número ou hífen (Unicode), depois de NFC (L3). `levenshtein` clássico (inserção, remoção, troca = 1). `spelling_limit(original) = max(1, floor(0,34 × len(núcleo)))`. `check_spelling(original, proposto)` aceita se distância ≤ limite e devolve distância e limite (o serviço monta `details` com eles). Tabela à mão: "Jesús"→"Jesus" (d 1, lim 1, aceita); "não"→"sim" (d 3, lim 1, barra); "deus"→"Deus" (d 0); "paz."→"paz" (d 0); "e"→"é" (lim 1 pelo `max`, aceita); "e"→"ou" (d 2, barra); "guarda-chuva"→"guardachuva" (d 1, hífen conta); limite exato aceito e limite + 1 barrado numa palavra longa ("misericórdia", núcleo 12, lim 4) | `packages/core/tests/test_spelling.py`, funções públicas do módulo, valores esperados escritos à mão (não recalculados pela fórmula). Mutações exigidas (vermelhas): `0.34` → `0.5`; sem o `max(1, …)`; `>` trocado por `>=`; núcleo sem minúsculas; núcleo sem remover pontuação; núcleo removendo o hífen; troca custando 2 |
| 2 — Persistência e serviço | `fix_word(conn, cut_id, word_id, text, now)`: grava; segunda correção substitui a primeira; texto igual ao original apaga (L5); a trava compara sempre com o **original**, nunca com a correção atual ("Jesús"→"Jesus" e depois "Jesu" barra com d 2, lim 1; L4); barrada ou inválida → nada muda (linhas de `word_fixes` e `CutRow` idênticas antes e depois); corte inexistente → `not_found` com `details.cut_id`; palavra fora dos trechos do corte (inexistente, de outra pregação, ou dentro de `range_start_word..range_end_word` mas fora de todo trecho) → `invalid_argument` com `details.argument = "word_id"`; vazio, só espaços ou mais de uma palavra → `invalid_argument` com `details.argument = "text"` (L6); `spelling_too_different` com `details.distance`, `details.limit`, `details.original`, sem o texto digitado na mensagem (L6); ordem das recusas de L7; a correção vale só para o corte (dois cortes da mesma pregação com a mesma palavra: só um muda); sucesso marca `edited = 1` e `updated_at = now` (L1); exclusão do corte, reprocessamento (`cuts.delete_of` + `transcripts.delete_of`) e `delete_unedited_suggestions` não falham com correção gravada e não deixam linha órfã (D6) | `packages/core/tests/test_fix_word.py`, banco temporário, dados por `transcripts.replace` e `cuts.insert_many` (padrão de `test_cuts_service.py`); verificação pelo `show_cut` e por `cuts.by_id`, não por SQL cru do teste. Mutações exigidas (vermelhas): comparar com a correção atual; gravar antes de checar a trava; desfazer gravando o original em vez de apagar (`corrected` viraria a string original); chave da correção sem `cut_id`; aceitar palavra pela faixa e não pelos trechos; não marcar `edited`; FK sem CASCADE |
| 3 — Montagem | Com uma correção gravada: `show_cut` → `text`, `segments[].text` e `words[].corrected` com a correção e `words[].text` original; `preview_cut` → `segments[].text` com a correção, tempos, `out_of_order` e `duration` iguais aos de antes; `list_cuts` → `text` com a correção (D3). Sem correção, as saídas do baseline ficam idênticas (testes existentes de `test_cuts_service.py` e `test_cut_preview.py` verdes sem edição de valores). Um corte que toca a mesma palavra em dois trechos mostra a correção nos dois | `packages/core/tests/test_fix_word.py` (ou `test_cuts_service.py`/`test_cut_preview.py`), via serviço, strings esperadas à mão. Mutações exigidas (vermelhas): `preview_cut` sem correções (o estado atual do baseline); `list_cuts` sem correções; `words[].text` trocado pelo corrigido; correção aplicada só ao `text` do corte e não ao do trecho |
| 4 — CLI | `wordcut cut fix-word <id> <word_id> <texto> [--json]`: sucesso → saída 0 e um objeto JSON no formato de D1; `spelling_too_different` → 5 com `{"error": {"code", "message", "details": {"distance", "limit", "original"}}}`; `invalid_argument` → 2 (`word_id`, `text`, `word_id` não inteiro pelo parser, sem eco do valor; ADR-0015); `not_found` → 3; `--json` antes ou depois da ação; sem `--json`, texto em português no stdout e erro no stderr com stdout vazio (L8); `--help` com exemplo; ponta a ponta: depois do `fix-word`, `cut show --json` e `cut preview --json` trazem a correção, e `cut preview` legível também | `apps/cli/tests/test_cut_fix_word_command.py` com `main(argv)` + `capsys` + `wordcut_home`, semeando como `test_cut_preview_command.py` (`cut_playing`). Mutações exigidas (vermelhas): trocar a saída de `spelling_too_different`; omitir `details.limit`; mensagem com o texto digitado (asserção de que o texto proposto não aparece em `message`) |
| 5 — Documentação | `CHANGELOG.md` [Não lançado]/Adicionado cita `cut fix-word`, a trava de grafia e a migração 0008; docs/cli.md §8.3 sem a ressalva "sem correção de grafia até 1.1.f.2"; §8.5 com resposta e erros; docs/architecture/README.md §4 atualizado (D5); docstring do módulo `wordcut_cli.cut` e ajuda do grupo `cut` incluem a correção | Leitura do diff contra o baseline (`git diff 928f8e0 -- CHANGELOG.md docs/ apps/cli/src/wordcut_cli/cut.py`). Sem ADR exigida (nenhuma decisão de arquitetura nova) |

### Matriz por critério de aceite

| Critério de aceite | O que o cobre |
|---|---|
| Spec — Cenário: correção aceita ("Jesús" → "Jesus" gravada, em `cut show` (`corrected`) e no texto montado, saída 0) | Passo 2 (gravação) + Passo 3 (`show_cut`) + Passo 4 (`fix-word --json` → 0 e `cut show --json`) |
| Spec — Cenário: troca bloqueada ("não" → "sim" → `spelling_too_different`, saída 5, `details.distance`/`limit`, nada muda) | Passo 1 (d 3, lim 1) + Passo 2 (nada muda: `word_fixes` e `CutRow` idênticas) + Passo 4 (saída 5 e `details`) |
| Spec — Cenário: desfazer (texto original remove a correção) | Passo 2 (`corrected` volta a `null`, linha apagada) + Passo 4 |
| Spec — Borda: mais de uma palavra → `invalid_argument` | Passo 2 (`details.argument = "text"`) + Passo 4 (saída 2) |
| Spec — Borda: palavra fora do corte → `invalid_argument` com `details.argument = "word_id"` | Passo 2 (inexistente, de outra pregação, na faixa mas fora dos trechos) + Passo 4 |
| Spec — Borda: corte inexistente → `not_found` | Passo 2 + Passo 4 (saída 3) |
| Spec — Borda: maiúsculas, acentos e pontuação contam pouco (núcleo) | Passo 1 (tabela: "deus"→"Deus", "paz."→"paz", "Jesús"→"Jesus") |
| Spec — Borda: a correção vale só para aquele corte | Passo 2 (dois cortes com a mesma palavra) |
| FR-001 — `cut fix-word` grava a correção no corte | Passo 2 + Passo 4 |
| FR-002 — aceita só se distância ≤ `max(1, floor(0,34 × len))` | Passo 1 (limite exato aceito, limite + 1 barrado; mutações de `0.34`, `max`, `>=`) + Passo 2 (compara com o original, L4) |
| FR-003 — texto igual ao original remove a correção | Passo 2 + Passo 4 |
| FR-004 — texto montado, prévia e `cut show` refletem a correção | Passo 3 (`show_cut`, `preview_cut`, `list_cuts`) + Passo 4 (ponta a ponta pela CLI) |
| Verificação — "Jesús" → "Jesus" aceito, em `cut show`, texto montado e prévia | Passo 3 + Passo 4 |
| Verificação — "não" → "sim" → `spelling_too_different` com distância e limite; nada muda | Passo 1 + Passo 2 + Passo 4 |
| Verificação — texto original remove a correção | Passo 2 + Passo 4 |
| Verificação — duas palavras / palavra fora do corte → `invalid_argument`; corte inexistente → `not_found` | Passo 2 + Passo 4 |
| Verificação — correção vale só para o corte | Passo 2 |
| Verificação — quality gates limpos | `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` |
| Requisito 1.1.f — CLI não interativa, `--json`, saídas consistentes (constituição §II) | Passo 4 |
| Constituição §I — o assistente não muda o conteúdo; a trava vale também para o administrador na CLI (spec, Pressupostos) | Passo 1 + Passo 2 (não há caminho de serviço que pule a trava; `fix_word` não recebe papel) + Passo 2 (trechos e faixa da `CutRow` intocados) |

### Lacunas do plan.md (decisão conservadora adotada como barra)

- **L1 — `edited` e `updated_at`.** O plano não diz se corrigir é editar. `sermon suggest`
  apaga os `suggested` com `edited = 0` (2.1.b.2; docs/cli.md §7.6: "editados permanecem"):
  sem marcar, a correção some sem aviso. Barra: sucesso (gravar, trocar ou desfazer) marca
  `edited = 1` e `updated_at = now`; recusa não escreve nada. Sem decisão, Passo 2 fica
  PARCIAL.
- **L2 — `casefold` ou minúsculas.** O protótipo usa `toLowerCase`; `casefold` muda o tamanho
  ("ß" → "ss") e, com ele, distância e limite. Barra: `str.lower()`, como a fonte da regra.
- **L3 — normalização Unicode e espaços.** O plano não normaliza. "Jesús" digitado em NFD não
  seria igual ao original em NFC no desfazer, e gravaria uma "correção" invisível. Barra: o
  texto recebido passa por `strip()` e NFC antes de tudo (comparação, desfazer, gravação); o
  teste de desfazer usa entrada NFD.
- **L4 — comparar com o original.** O protótipo chama `checkWord(orig, v)` com o original da
  transcrição, não com a correção corrente. Sem isso, correções em cadeia mudariam a palavra
  aos poucos. Barra: teste em cadeia ("Jesus" aceito, depois "Jesu" barrado).
- **L5 — desfazer sem correção.** Texto igual ao original sem correção gravada: sucesso,
  `corrected = null`, sem erro.
- **L6 — `details` e eco.** O plano só nomeia `word_id`. Barra: mais de uma palavra, vazio ou só
  espaços → `details.argument = "text"` (o `dest` do posicional no parser); nenhuma mensagem
  (`invalid_argument` nem `spelling_too_different`) repete o texto digitado (ADR-0015, estendida
  por conservadorismo); `details.original` pode trazer o original, que é dado gravado.
- **L7 — ordem das recusas.** Barra, para os testes serem determinísticos: corte inexistente
  (`not_found`) → palavra fora do corte (`word_id`) → texto que não é uma palavra (`text`) →
  desfazer se igual ao original → trava (`spelling_too_different`).
- **L8 — saída legível.** O plano não define. Barra: sem `--json`, uma linha em português no
  stdout com o número da palavra, o original e a correção (ou que a correção foi removida);
  formato livre, testado só por presença e por não ser JSON.
- **L9 — palavra que sai do corte depois.** Quando `cut segments` (2.1.c) existir, uma correção
  pode ficar sem palavra no corte. Barra deste item: a montagem só consulta correções das
  palavras que toca, e `words` lista só as palavras do corte; nada além disso.
- **L10 — trava de processamento.** §3.5: `cut fix-word` não é tarefa e não pega a trava, como
  `cut choose`. Não exigido por teste; se o implementador envolver o comando na trava, é FAIL.

## Rodada 1 — 2026-10-26 — working tree sobre 928f8e0

**baseline_commit**: 928f8e09c4dae0618d4455a193813b88113feab3
**Componentes avaliados**: `packages/core` (`cuts.spelling`, `cuts.assembly`, `db.cuts`,
`db.word_fixes`, migração 0008, `service.cuts`); `apps/cli` (`wordcut_cli.cut`); documentação
**Suítes**: core (barra) ✅ (77 / 0 falhas) · regressão de exclusão ✅ (37 / 0) · cli (barra) ✅
(55 / 0) · completa ✅ (1008 / 0) · `ruff check` ✅ · `ruff format --check` ✅ · `mypy` ✅

Mutações manuais numa cópia no scratchpad (código da worktree intocado): 29 de 30 mortas.
Sobreviveu a exigida pelo Passo 2, "chave da correção sem `cut_id`", na forma coerente:
`PRIMARY KEY (word_id)` com `ON CONFLICT (word_id)` (a correção do corte B tira ou sobrescreve
a do corte A) — 46/46 verdes em `test_fix_word.py` + `test_cut_fix_word_command.py`. Mudar só a
PK, como no diário do implementador, morre por erro de SQL do `ON CONFLICT`, não por
comportamento.

Fatos relatados pelo implementador:
- `db/word_fixes.py` como módulo novo: previsto no Contexto de código do plan.md ("Criar
  `packages/core/src/wordcut/db/word_fixes.py`"); repositório sem regra de negócio (ADR-0004).
  Conforme.
- `test_cuts_repository.py` `== 7` → `>= 7`: a 0008 sobe a versão; os testes vizinhos de
  migração usam `>=` (`test_transcripts_repository.py:61`, `test_presets_repository.py:148`,
  `test_tasks_repository.py:36`) e `test_db.py` fixa `== latest_packaged_migration()`. O teste
  continua provando o que prova (migrar de 6 preserva os dados). A barra só proibia editar
  valores de `test_cuts_service.py` e `test_cut_preview.py`, que estão intocados. Conforme.

Política de comentários (CONTRIBUTING.md §5): comentários novos em inglês, de intenção ou
referência (`spelling.py` limite do protótipo, cabeçalho da 0008, casos de teste); o comentário
obsoleto de `_word` foi removido (D4). Sem achado.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Trava pura | PASS | `test_spelling.py`: tabela à mão com os 10 casos da barra (inclui `misericórdia` 4/4 aceito e 5/4 barrado, entrada NFD); 8 mutações exigidas vermelhas (0,34, `max`, `<=`, `lower`, pontuação, hífen, troca 2, NFC) |
| 2 — Persistência e serviço | PARCIAL | Gravar, trocar, desfazer (NFD e espaços), L4 em cadeia, L5, L1, L6, L7, recusa sem escrita e CASCADE provados por `test_fix_word.py`; mutações vermelhas: comparar com a correção, gravar antes da trava, desfazer gravando, sem `mark_edited`, faixa no lugar dos trechos, FKs sem CASCADE. **Sobrevive** a mutação exigida "chave sem `cut_id`" (PK e `ON CONFLICT` só por `word_id`): `test_a_fix_holds_only_in_its_cut` (`test_fix_word.py`) corrige só um dos dois cortes. Falta teste que corrija a mesma palavra em dois cortes com grafias diferentes e veja cada corte com a sua |
| 3 — Montagem | PASS | `test_cut_show_assembles_…`, `test_preview_plays_…` (tempos, `out_of_order` e `duration` iguais), `test_cut_list_assembles_each_cut_with_its_own_fixes`, `test_a_word_the_cut_plays_twice_…`; `assemble(..., fixes)` obrigatório (`assembly.py:72`); `test_cuts_service.py` e `test_cut_preview.py` sem diff; mutações vermelhas: preview sem correções, list sem correções, `words[].text` corrigido, trecho sem correção |
| 4 — CLI | PASS | `test_cut_fix_word_command.py`: 0 com a forma de D1, 5 com `details` e sem eco, 2 para `word_id`/`text`/`word_id` não numérico sem eco, 3 para `not_found`, `--json` em três posições, linha legível, erro só no stderr, ponta a ponta `show`/`preview --json`/`preview` legível; `--help` e exemplo em `test_cut_command.py`; sem trava (L10, `cut.py`); mutações vermelhas: saída 5→1, sem `details.limit`, mensagem com o texto digitado, linha legível sem a correção |
| 5 — Documentação | PASS | `git diff 928f8e0`: CHANGELOG (comando, trava, migração 0008, CASCADE); docs/cli.md §8.2 (`text` original, `corrected`), §8.3 (sem a ressalva), §8.5 (regra, erros, NFC, `edited`, sem trava, resposta); arquitetura §4 (`cuts.spelling`, `db.word_fixes`, 0008, `fix-word`); docstring e ajuda do grupo `cut` |

### Critérios de aceite
- ✅ Cenário: correção aceita — `test_fixing_a_word_answers_…`, `test_a_fixed_word_shows_its_fix_…`, `test_fix_word_with_json_prints_…`, `test_after_fix_word_cut_show_and_preview_…`
- ✅ Cenário: troca bloqueada — `test_spelling` ("não"→"sim" 3/1), `test_a_fix_that_changes_the_word_is_too_different_…`, `test_a_refused_fix_changes_nothing_in_the_cut`, `test_fix_word_that_changes_the_word_is_too_different_exits_5_…`
- ✅ Cenário: desfazer — `test_fixing_a_word_back_to_its_original_spelling_removes_the_fix`, `test_fix_word_back_to_the_original_removes_the_fix`
- ✅ Borda: mais de uma palavra — `test_a_text_that_is_not_one_word_is_an_invalid_text_…`, `test_fix_word_of_a_word_out_of_the_cut_or_a_text_…_exits_2`
- ✅ Borda: palavra fora do corte — `test_a_word_the_cut_does_not_play_is_an_invalid_word_id` (inexistente, outra pregação, na faixa fora dos trechos)
- ✅ Borda: corte inexistente — `test_fixing_a_word_of_a_cut_that_does_not_exist_is_not_found`, `test_fix_word_of_a_cut_that_does_not_exist_…_exits_3`
- ✅ Borda: maiúsculas, acentos e pontuação contam pouco — `test_spelling` ("deus"→"Deus", "paz."→"paz", "Jesús"→"Jesus")
- ❌ Borda: a correção vale só para aquele corte — parcial: `test_a_fix_holds_only_in_its_cut` cobre um corte corrigido e outro não; a mutação de chave só por `word_id` sobrevive (ver Passo 2)
- ✅ FR-001 — `test_a_fixed_word_shows_its_fix_…`, `test_fix_word_with_json_prints_…`
- ✅ FR-002 — `test_spelling` (limite exato e limite + 1), `test_the_lock_compares_with_the_original_word_…`
- ✅ FR-003 — testes de desfazer (core e CLI), `test_undoing_a_word_that_has_no_fix_…`
- ✅ FR-004 — testes de montagem do Passo 3 + `test_after_fix_word_cut_show_and_preview_…`
- ✅ Verificação: "Jesús" → "Jesus" em `cut show`, texto montado e prévia — Passos 3 e 4
- ✅ Verificação: "não" → "sim" com distância e limite; nada muda — Passos 1, 2 e 4
- ✅ Verificação: texto original remove a correção — Passos 2 e 4
- ✅ Verificação: duas palavras / fora do corte / corte inexistente — Passos 2 e 4
- ❌ Verificação: correção vale só para o corte — parcial, mesmo motivo da borda acima
- ✅ Verificação: quality gates limpos — 1008 passed, `ruff check`, `ruff format --check`, `mypy`
- ✅ Requisito 1.1.f / constituição §II — Passo 4
- ✅ Constituição §I — `fix_word` sem caminho que pule a trava; recusa não muda `show_cut` nem `CutRow`

### Veredito geral: PARCIAL
Sem FAIL; Passo 2 PARCIAL por uma mutação exigida que sobrevive (chave da correção sem
`cut_id`). Reabrir o Passo 2 para um teste com a mesma palavra corrigida em dois cortes.

## Rodada 2 — 2026-10-26 — working tree sobre 928f8e0

**baseline_commit**: 928f8e09c4dae0618d4455a193813b88113feab3
**Componentes avaliados**: `packages/core` (`cuts.spelling`, `cuts.assembly`, `db.cuts`,
`db.word_fixes`, migração 0008, `service.cuts`); `apps/cli` (`wordcut_cli.cut`); documentação
**Suítes**: core (barra) ✅ (80 / 0 falhas) · regressão de exclusão ✅ (37 / 0) · cli (barra) ✅
(55 / 0) · completa ✅ (1011 / 0) · `ruff check` ✅ · `ruff format --check` ✅ · `mypy` ✅

Mudança da rodada: `test_two_cuts_fixing_the_same_word_each_keep_their_own_spelling`
(`test_fix_word.py:260`, parametrizado em `cut show`, `cut preview`, `cut list`): a mesma
palavra corrigida em dois cortes ("Jesus" e "JESUS"), cada corte com a sua. `test_cuts_service.py`
e `test_cut_preview.py` seguem sem diff contra o baseline.

Mutações manuais numa cópia no scratchpad (código da worktree intocado): 3 de 4 mortas.
- ☠️ `PRIMARY KEY (word_id)` + `ON CONFLICT (word_id)` (a exigida, forma coerente): 3 falhas,
  todas `AssertionError` em `test_fix_word.py:281`, nenhum erro de SQL.
- ☠️ `word_fixes.of_sermon` misturando as correções de todos os cortes: 1 falha (`cut list`).
- ☠️ `word_fixes.of_cut` sem filtro de corte: 3 falhas.
- 🚨 `word_fixes.delete` só por `word_id` (sem `cut_id`): **sobrevive** (49/49 em
  `test_fix_word.py` + `test_cut_fix_word_command.py`). Desfazer a correção no corte B apagaria
  a do corte A. O código atual está correto (`word_fixes.py:34` filtra por `cut_id`), mas
  nenhum teste desfaz num corte enquanto outro corte tem a mesma palavra corrigida.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Trava pura | PASS | Sem mudança desde a Rodada 1; `test_spelling.py` verde |
| 2 — Persistência e serviço | PARCIAL | Item da Rodada 1 resolvido: a mutação exigida "chave sem `cut_id`" (PK e `ON CONFLICT` só por `word_id`) morre pelo comportamento em `show_cut`, `preview_cut` e `list_cuts`. Achado novo (não é estagnação): a linha da matriz "a correção vale só para o corte (só um muda)" não está provada no desfazer — a mutação `delete` só por `word_id` sobrevive. Falta teste: corrigir a palavra nos cortes A e B, desfazer em B, e A mantém a sua |
| 3 — Montagem | PASS | Sem mudança; o teste novo reforça `list_cuts` por corte (mutação de `of_sermon` vermelha) |
| 4 — CLI | PASS | Sem mudança; `test_cut_fix_word_command.py` verde |
| 5 — Documentação | PASS | Sem mudança desde a Rodada 1 |

### Critérios de aceite
- ✅ Cenário: correção aceita — como na Rodada 1
- ✅ Cenário: troca bloqueada — como na Rodada 1
- ✅ Cenário: desfazer — como na Rodada 1
- ✅ Borda: mais de uma palavra — como na Rodada 1
- ✅ Borda: palavra fora do corte — como na Rodada 1
- ✅ Borda: corte inexistente — como na Rodada 1
- ✅ Borda: maiúsculas, acentos e pontuação contam pouco — como na Rodada 1
- ❌ Borda: a correção vale só para aquele corte — gravar e trocar provados por
  `test_two_cuts_fixing_the_same_word_each_keep_their_own_spelling`; desfazer não (mutação
  `delete` sem `cut_id` sobrevive)
- ✅ FR-001, FR-002, FR-003, FR-004 — como na Rodada 1
- ✅ Verificação: "Jesús" → "Jesus"; "não" → "sim"; desfazer; duas palavras / fora do corte /
  corte inexistente — como na Rodada 1
- ❌ Verificação: correção vale só para o corte — parcial, mesmo motivo da borda acima
- ✅ Verificação: quality gates limpos — 1011 passed, `ruff check`, `ruff format --check`, `mypy`
- ✅ Requisito 1.1.f / constituição §II — Passo 4
- ✅ Constituição §I — como na Rodada 1

### Veredito geral: PARCIAL
Sem FAIL. O item da Rodada 1 foi resolvido; o Passo 2 segue PARCIAL por achado novo: desfazer
a correção num corte não é provado isolado dos outros cortes. Reabrir o Passo 2 para esse teste.

## Rodada 3 — 2026-10-26 — working tree sobre 928f8e0

**baseline_commit**: 928f8e09c4dae0618d4455a193813b88113feab3
**Componentes avaliados**: `packages/core` (`cuts.spelling`, `cuts.assembly`, `db.cuts`,
`db.word_fixes`, migração 0008, `service.cuts`); `apps/cli` (`wordcut_cli.cut`); documentação
**Suítes**: core (barra) ✅ (83 / 0 falhas) · regressão de exclusão ✅ (37 / 0) · cli (barra) ✅
(55 / 0) · completa ✅ (1014 / 0) · `ruff check` ✅ · `ruff format --check` ✅ · `mypy` ✅

Mudança da rodada: `test_undoing_a_fix_in_one_cut_keeps_the_fix_of_the_same_word_in_another_cut`
(`test_fix_word.py:285`, parametrizado em `cut show`, `cut preview`, `cut list`): a mesma
palavra corrigida nos cortes A ("Jesus") e B ("JESUS"); desfazer em B volta B ao original e A
mantém a sua. `test_cuts_service.py` e `test_cut_preview.py` seguem sem diff contra o baseline.

Mutações manuais numa cópia no scratchpad (código da worktree intocado), rodando
`test_fix_word.py`, `test_cut_fix_word_command.py`, `test_cuts_service.py`,
`test_cut_preview.py` e `test_cuts_repository.py` (86 testes): 4 de 4 mortas, mais 1 equivalente.
- ☠️ `word_fixes.delete` só por `word_id` (a exigida): 3 falhas, todas `AssertionError` no teste
  novo, nenhum erro de SQL.
- ☠️ `word_fixes.of_cut` sem filtro de corte: 5 falhas.
- ☠️ `PRIMARY KEY (word_id)` + `ON CONFLICT (word_id)`: 6 falhas, só `AssertionError`.
- ☠️ desfazer gravando o original em vez de apagar: 3 falhas (core e CLI).
- ≡ `word_fixes.of_sermon` sem o filtro de pregação (relatada pelo implementador): 86/86 verdes.
  **Equivalente, julgado assim**: o único chamador é `list_cuts` (`service/cuts.py:31`), que só
  lê `fixes.get(row.id)` dos cortes da própria pregação; `cuts.id` é `AUTOINCREMENT`
  (`0007_cuts.sql:7`), então um id não se repete entre pregações nem é reusado depois de
  apagado; o `JOIN cuts` e o `ON DELETE CASCADE` não deixam correção de corte inexistente. A
  saída de `cut list` é idêntica. O que a mutação muda é o contrato do próprio repositório
  (docstring "every cut of the sermon") e o custo (lê as correções de todas as pregações); um
  teste de repositório a mataria, mas a barra prova pelo serviço (`show_cut`, `cuts.by_id`) e não
  exige teste de `db.word_fixes`. Não é achado contra a barra.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Trava pura | PASS | Sem mudança desde a Rodada 1; `test_spelling.py` verde |
| 2 — Persistência e serviço | PASS | Item da Rodada 2 resolvido: `test_undoing_a_fix_in_one_cut_keeps_the_fix_of_the_same_word_in_another_cut` mata `delete` só por `word_id` pelo comportamento em `show_cut`, `preview_cut` e `list_cuts`; as demais mutações exigidas do Passo 2 seguem vermelhas (Rodadas 1 e 2, e as de chave reconferidas acima) |
| 3 — Montagem | PASS | Sem mudança; `test_cuts_service.py` e `test_cut_preview.py` sem diff |
| 4 — CLI | PASS | Sem mudança; `test_cut_fix_word_command.py` verde |
| 5 — Documentação | PASS | Sem mudança desde a Rodada 1 |

### Critérios de aceite
- ✅ Cenário: correção aceita — como na Rodada 1
- ✅ Cenário: troca bloqueada — como na Rodada 1
- ✅ Cenário: desfazer — como na Rodada 1
- ✅ Borda: mais de uma palavra — como na Rodada 1
- ✅ Borda: palavra fora do corte — como na Rodada 1
- ✅ Borda: corte inexistente — como na Rodada 1
- ✅ Borda: maiúsculas, acentos e pontuação contam pouco — como na Rodada 1
- ✅ Borda: a correção vale só para aquele corte — gravar e trocar
  (`test_two_cuts_fixing_the_same_word_each_keep_their_own_spelling`) e desfazer
  (`test_undoing_a_fix_in_one_cut_keeps_the_fix_of_the_same_word_in_another_cut`)
- ✅ FR-001, FR-002, FR-003, FR-004 — como na Rodada 1
- ✅ Verificação: "Jesús" → "Jesus"; "não" → "sim"; desfazer; duas palavras / fora do corte /
  corte inexistente — como na Rodada 1
- ✅ Verificação: correção vale só para o corte — mesmos testes da borda acima
- ✅ Verificação: quality gates limpos — 1014 passed, `ruff check`, `ruff format --check`, `mypy`
- ✅ Requisito 1.1.f / constituição §II — Passo 4
- ✅ Constituição §I — como na Rodada 1

### Veredito geral: PASS
Todos os passos `[x]` e PASS, critérios cobertos, suítes e checagens verdes. A mutação de
`of_sermon` sem filtro de pregação é equivalente no comportamento e não é cobrada pela barra.
