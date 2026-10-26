# QA — 1.1.g.1 — Sequência da prévia de um corte (`cut preview`)

## Plano de QA — 2026-10-26

**baseline_commit**: 8e972fc2ce7357ac96bed728b8cc09ac6a214cb1
**Componentes em escopo**: `packages/core` (`wordcut.service.cuts` — `preview_cut` novo;
`wordcut.cuts.assembly` — marca de fora de ordem, ver D1); `apps/cli` (`wordcut_cli.cut` —
ação `preview`); documentação (`CHANGELOG.md`, `docs/cli.md` §8.3)
**Suítes que valem como prova**:
- core: `uv run pytest packages/core/tests/test_cut_preview.py -q` (ou casos novos em
  `packages/core/tests/test_cuts_service.py`, se o implementador preferir o arquivo existente)
- cli: `uv run pytest apps/cli/tests/test_cut_preview_command.py -q` (ou casos novos em
  `apps/cli/tests/test_cut_command.py`)
- suíte completa: `uv run pytest -q`
- checagem estática: `uv run ruff check . && uv run ruff format --check . && uv run mypy`
  (CONTRIBUTING.md; o `specs/roadmap.md` escreve `uv run mypy src`, mas o `mypy` sem
  argumento é o que cobre `packages/core/src`, `apps/cli/src` e `apps/api/src`)

Fontes da barra: `spec.md`, `plan.md`,
docs/requirements/features/1.1.g-preview-without-render.md, docs/cli.md §3.4, §4.2, §4.3,
§4.4, §5.3, §6.4, §8.2, §8.3, constituição §IV, e o código no baseline
(`packages/core/src/wordcut/cuts/assembly.py`, `service/cuts.py`, `db/transcripts.py`,
`edit/edit_list.py`, `short.py`, `apps/cli/src/wordcut_cli/cut.py`, `conftest.py`
(`lock_owner`)). Execução automatizada: onde a skill pediria decisão, foi escolhida a opção
mais conservadora, registrada como lacuna (L*).

### Divergências do plan.md com o código do baseline (plano escrito antes do item 11)

| # | O plan.md diz | O código no baseline | Ajuste recomendado |
|---|---|---|---|
| D1 | Alterar `cuts/assembly.py` para marcar `out_of_order` | `AssembledSegment` é um trecho isolado (`from_word`, `to_word`, `words`) e não conhece o anterior; só `AssembledCut.segments` tem a sequência | Pôr a marca no nível do corte (p. ex. `AssembledCut.out_of_order -> tuple[bool, ...]`, um por trecho) ou calculá-la no serviço; não acrescentar campo ao `AssembledSegment` que dependa do vizinho |
| D2 | Fora de ordem: "mesmo critério do `preview` antigo (`↑`)" | O antigo (`edit/edit_list.py:43`, `EditList.reordered`) marca o trecho **antes** de algum trecho posterior que vem de mais cedo na pregação (o gancho puxado da conclusão), não o que volta no tempo; e compara inícios, não `start < previous.end` | A regra do plano (`segment.start < previous.end`) é a que casa com a spec ("o trecho que volta no tempo"); corrigir a justificativa no plan.md para "critério novo, alinhado à spec; difere do `reordered()` antigo". Barra: a regra do plano |
| D3 | "Reaproveita a montagem do item 11 (trechos com tempos e texto corrigido)" | A montagem do item 11 não aplica correção: `AssembledSegment.text` une `word.text`; `service/cuts.py:107` deixa `corrected = None` até o item 13 (1.1.f.2), e não há tabela de correções | Neste item, `text` = `AssembledSegment.text` (texto original). Registrar no plan.md que o item 13 deve fazer a prévia (e o `show`) usar a correção, e que nenhum gancho de correção é criado aqui |
| D4 | Tempos "em tempo da pregação" (§3.4) | `WordRow.start/end` já são tempo da pregação e o `cut show` usa os mesmos `AssembledSegment.start/end` | Nenhum ajuste; reaproveitar `AssembledSegment.start/end` sem deslocar |
| D5 | Duração "igual ao `cut show`" | `AssembledCut.duration` (soma das faixas, arredondada ao ms) já é o que `cut show` devolve | Usar `AssembledCut.duration`; não recalcular |
| D6 | `not_found` | `service/cuts.py:_existing` já levanta `WordcutError("not_found", …, {"cut_id": N})` | `preview_cut` usa `_existing`; `details.cut_id` como no `show` |
| D7 | Arquivos de teste novos `test_cut_preview.py` e `test_cut_preview_command.py` | Os fixtures de corte estão em `test_cuts_service.py` (`processed_sermon`, `stored_cut`) e `test_cut_command.py` (`sermon_with_cuts`, só dois trechos) | Aceito arquivo novo ou caso nos existentes; o cenário pede **três** trechos (ver L2), então o fixture de dois trechos não basta sozinho |

### Matriz por passo

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Serviço | `preview_cut(connection, cut_id)` devolve `{"cut_id", "duration", "segments": [{"start", "end", "text", "out_of_order"}]}`: trechos **na ordem de montagem** (não reordenados por tempo); `start`/`end` = início da primeira e fim da última palavra do trecho, em tempo da pregação; `text` = palavras do trecho unidas por espaço (sem correção, D3); `out_of_order` = `start < end` do trecho imediatamente anterior, `false` no primeiro; `duration` = a mesma do `show_cut` do mesmo corte. Corte inexistente → `WordcutError("not_found")` com `details.cut_id`. Não lê nem pega a trava, não abre mídia | Teste de comportamento no core (banco temporário, palavras por `transcripts.replace`, corte por `cuts.insert_many`), com valores escritos à mão. Corte de três trechos A(tarde) → B(cedo) → C(entre B e A, depois de B): esperado `[false, true, false]`. Mais um caso de fronteira: trecho que começa exatamente no `end` do anterior → `false`. Mutações exigidas (vermelhas): (a) critério antigo — marcar o trecho que precede um trecho mais cedo (`[true, false, false]`); (b) comparar com qualquer trecho anterior em vez do imediato (`C` vira `true`); (c) `<` → `<=` (fronteira vira `true`); (d) duração = fim do último − início do primeiro; (e) ordenar os trechos por `start`; (f) `out_of_order` sempre `false` |
| 2 — CLI | `wordcut cut preview <id> [--json]`: com `--json`, um único objeto no stdout, saída 0, mesmo conteúdo do Passo 1; `--json` antes ou depois da ação; inexistente → `{"error": {"code": "not_found", …}}`, saída 3; `id` mal formado → `invalid_argument`, saída 2; sem `--json`, uma linha por trecho com `início → fim` (em `format_timestamp`) e o texto, com `↑` só nos trechos `out_of_order`, erro só no stderr com stdout vazio; `--help` da ação com exemplo (`wordcut cut preview 34 --json`). Com outro processo segurando a trava (`lock_owner`), sai 0 com o resultado | `main(argv)` + `capsys` + `wordcut_home`, no padrão de `apps/cli/tests/test_cut_command.py`; trava pelo fixture `lock_owner("render", "cut 34")` de `conftest.py`. Texto legível verificado por linha (contém tempos, texto e `↑` só onde deve), sem fixar espaçamento (§4.2). Mutações exigidas (vermelhas): (g) envolver o `run` em `ProcessingLock(...).acquire(...)` → teste da trava fica vermelho (`busy`); (h) `↑` em todas as linhas ou em nenhuma; (i) trocar o código de saída do `not_found` |
| 3 — Documentação | `CHANGELOG.md` [Não lançado]/Adicionado cita `wordcut cut preview <id>`; `docs/cli.md` §8.3 passa a dizer o formato JSON (`cut_id`, `duration`, `segments[].start/end/text/out_of_order`), que `out_of_order` marca o trecho que começa antes do fim do anterior e que a duração é a do `cut show` (L4) | Leitura do diff contra o baseline (`git diff 8e972fc -- CHANGELOG.md docs/`). Sem ADR exigida (nenhuma decisão de arquitetura nova) |

### Matriz por critério de aceite

| Critério de aceite | O que o cobre |
|---|---|
| Spec — Cenário: sequência da prévia (três trechos, um fora de ordem; `--json` com `cut_id`, `duration`, `segments[start, end, text, out_of_order]` na ordem de montagem, tempos da pregação, `out_of_order: true` no que volta no tempo) | Passo 1 (valores, três trechos, mutações a–f) + Passo 2 (`cut preview <id> --json`, chaves e valores) |
| Spec — Cenário: nunca bloqueada (tarefa segurando a trava → sai normalmente) | Passo 2 (teste com `lock_owner`, saída 0 e resultado; mutação g) |
| Spec — Borda: corte inexistente → `not_found` | Passo 1 (`WordcutError`, `details.cut_id`) + Passo 2 (saída 3, `{"error": {"code": "not_found"}}`) |
| Spec — Borda: texto com correções de grafia (quando existirem, item 13) | Não aplicável neste item (D3): barra = texto original; coberto pelo item 13. Não conta como critério descoberto |
| Spec — Borda: sem `--json`, uma linha por trecho `[início → fim] texto`, `↑` nos fora de ordem | Passo 2 (texto legível; mutação h) |
| FR-001 — trechos na ordem de montagem, início/fim em tempo da pregação, texto, marca de fora de ordem e duração total | Passo 1 + Passo 2 |
| FR-002 — não toca vídeo, não renderiza, não pega a trava | Passo 2 (trava, mutação g) + revisão do diff: `preview_cut` e a ação `preview` não importam `wordcut.media`, `wordcut.edit.assemble`, `wordcut.lock`/`ProcessingLock` nem `wordcut.tasks`; o teste roda sem vídeo no `WORDCUT_HOME` |
| Verificação — corte com trecho fora de ordem → JSON na ordem de montagem com `out_of_order` certo e duração | Passo 1 + Passo 2 |
| Verificação — com `lock_owner` segurando a trava → sai normalmente | Passo 2 |
| Verificação — inexistente → `not_found`; texto legível com `↑` | Passo 1 + Passo 2 |
| Verificação — quality gates limpos | `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` |
| Constituição §IV — prévia nunca bloqueada pela trava | Mesmo teste do cenário "nunca bloqueada" |

### Lacunas do plan.md (decisão conservadora adotada como barra)

- **L1 — onde mora a marca.** O plano manda alterar `assembly.py`, mas o trecho não conhece
  o vizinho (D1). Barra: a marca vem do corte inteiro (propriedade de `AssembledCut` ou função
  no serviço); tanto faz o lugar, desde que testada pela interface pública (`preview_cut`).
- **L2 — vizinho imediato ou qualquer anterior.** `start < previous.end` compara só com o
  trecho anterior; um terceiro trecho que segue o fora de ordem mas ainda é anterior ao
  primeiro sai `false`. Barra: a regra do plano, literal, cobrada pelo caso de três trechos
  (mutação b). Recomendação: escrever o exemplo em docs/cli.md §8.3.
- **L3 — justificativa errada.** O plano diz "mesmo critério do `preview` antigo", e não é
  (D2). Barra: a regra do plano e da spec; recomenda-se corrigir a frase no plan.md.
- **L4 — §8.3 incompleto, não divergente.** O passo 3 diz "docs/cli.md §8.3 se divergir";
  §8.3 não traz o formato do JSON nem a regra da marca. Barra: atualizar §8.3 com o formato,
  a regra e a duração; sem isso, Passo 3 fica PARCIAL.
- **L5 — chaves extras no JSON.** A spec lista as chaves; o `show` traz também
  `from_word`/`to_word` nos trechos. Barra: as chaves da spec presentes com os valores certos;
  extras toleradas (§4.4: programas ignoram o que não conhecem), mas, se entrarem, devem estar
  em §8.3.
- **L6 — texto sem correção.** O plano promete "texto corrigido"; não há correção no
  baseline (D3). Barra: texto original, sem gancho de correção criado neste item.
- **L7 — fixture de três trechos.** O fixture da CLI tem dois trechos (`sermon_with_cuts`);
  com dois, as mutações a e b não morrem. Barra: o teste do cenário usa três trechos.
- **L8 — formato da linha legível.** A spec dá `[início → fim] texto` com `↑` sem dizer
  onde; §4.2 diz que o texto pode mudar. Barra: linha contém os dois tempos em
  `format_timestamp`, o texto e `↑` só se `out_of_order`; posição e espaçamento livres.
- **L9 — corte sem trechos.** Não previsto pela spec nem pelo plano; não deveria existir
  (`cuts.insert_many` grava sempre trechos). Não exigido teste; se o implementador tratar,
  registrar no plan.md.

## Rodada 1 — 2026-10-26 — working tree sobre 8e972fc

**baseline_commit**: 8e972fc2ce7357ac96bed728b8cc09ac6a214cb1
**Componentes avaliados**: `packages/core` (`service/cuts.py`, `cuts/assembly.py`); `apps/cli`
(`wordcut_cli/cut.py`); `CHANGELOG.md`; `docs/cli.md` §8.3
**Suítes**: suíte completa ✅ (941 / 0 falhas; 1 aviso do starlette, alheio) ·
`test_cut_preview.py` + `test_cut_preview_command.py` ✅ (13 / 0) · ruff check ✅ ·
ruff format --check ✅ · mypy ✅ (80 arquivos)

**Mutações** (cópia no scratchpad, revertidas e conferidas byte a byte): a, b, c, d, e, f,
g, h (↑ em todas), h (↑ em nenhuma), i — 10 de 10 mortas. Extra, para a guarda do
`not_found` no core, que o tdd.md registrou sem mutação: `preview_cut` engolindo o
`not_found` e devolvendo prévia vazia — morta (3 testes).

**Guardas do implementador** (5 testes que passaram de primeira): fronteira morre com c;
duração com d; trava com g; contrato da CLI (not_found 3, stderr) com i; `not_found` do core
com a mutação extra acima. `invalid_argument` 2 e `--json` em três posições são contrato
comum da CLI, sem mutação exigida pela barra.

**Política de comentários** (CONTRIBUTING.md §5): docstrings de `preview_cut` e
`AssembledCut.out_of_order` são contrato público com referência a docs/cli.md §8.3; nos
testes, um comentário de formato (regex `HH:MM:SS.mmm`, §2) e comentários de intenção sobre
o cenário de três trechos e a fronteira. Nenhum comentário fora dos tipos.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Serviço | PASS | `test_cut_preview.py`: três trechos `[false, true, false]`, tempos, texto sem correção, duração 2,35 = `show_cut`; fronteira `false`; `not_found` com `details.cut_id`. Marca em `AssembledCut.out_of_order` (`assembly.py:55`), D1/L1. Mutações a–f vermelhas |
| 2 — CLI | PASS | `test_cut_preview_command.py`: `--json` com o objeto inteiro (três trechos), linha legível com `format_timestamp` e `↑` só no fora de ordem, `lock_owner` → saída 0, `not_found` 3 com stdout vazio sem `--json`, `invalid_argument` 2, `--json` em três posições; `--help` com `wordcut cut preview 34 --json` (`test_cut_command.py`). Ação não importa mídia, trava nem tarefas (FR-002). Mutações g, h, i vermelhas |
| 3 — Documentação | PASS | `CHANGELOG.md` [Não lançado]/Adicionado cita `wordcut cut preview <id>`; `docs/cli.md` §8.3 com chaves do JSON, regra da marca (só o anterior imediato, fronteira, exemplo de três trechos), duração do `cut show`, linha legível e `not_found` (L4) |

### Critérios de aceite
- ✅ Cenário: sequência da prévia — `test_preview_plays_the_segments_in_cut_order_and_marks_the_one_that_goes_back_in_time`, `test_preview_with_json_prints_the_segments_in_cut_order_marking_the_one_that_goes_back`
- ✅ Cenário: nunca bloqueada — `test_preview_is_never_blocked_by_a_lock_held_elsewhere`
- ✅ Borda: corte inexistente → `not_found` — `test_preview_of_a_cut_that_does_not_exist_is_not_found`, `test_preview_of_a_cut_that_does_not_exist_is_not_found_and_exits_3`
- — Borda: texto com correções de grafia — não aplicável neste item (D3/L6); item 13 (1.1.f.2)
- ✅ Borda: sem `--json`, uma linha por trecho com `↑` — `test_preview_without_json_prints_one_line_per_segment_with_an_arrow_only_on_the_jump_back`
- ✅ FR-001 — mesmos testes do cenário de sequência + `test_preview_lasts_as_long_as_the_shown_cut`
- ✅ FR-002 — teste da trava + revisão do diff (sem `wordcut.media`, `edit.assemble`, `lock`, `tasks`; teste sem vídeo)
- ✅ Verificação: fora de ordem → JSON na ordem de montagem, `out_of_order` e duração — testes do cenário
- ✅ Verificação: `lock_owner` segurando a trava → sai normalmente — teste da trava
- ✅ Verificação: inexistente → `not_found`; texto legível com `↑` — testes de `not_found` e da linha legível
- ✅ Verificação: quality gates limpos — pytest 941/0, ruff check, ruff format --check, mypy
- ✅ Constituição §IV — teste da trava (mutação g)

### Veredito geral: PASS
Três passos `[x]` em PASS, 11/11 critérios aplicáveis cobertos, suítes e checagens verdes,
mutações a–i mortas.
