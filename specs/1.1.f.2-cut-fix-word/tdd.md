## Plano de QA

baseline_commit: 928f8e09c4dae0618d4455a193813b88113feab3

09:51  📐 BARRA   trava pura: núcleo, Levenshtein e limite como no protótipo
       test_spelling.py com tabela escrita à mão; a fórmula repetida
       no teste não prova nada

09:51  🧬 EXIGE   0.34 → 0.5  ·  sem max(1, …)  ·  > virando >=  ·  vermelha
       prova o limite exato aceito e o limite + 1 barrado

09:51  🧬 EXIGE   núcleo sem minúsculas, sem tirar pontuação, sem hífen  ·
       vermelha
       prova que só a grafia conta pouco, não a palavra

09:51  📐 BARRA   fix_word grava, troca, desfaz e recusa sem escrever
       test_fix_word.py no core, banco temporário, leitura por show_cut
       e cuts.by_id

09:51  🧬 EXIGE   trava comparando com a correção atual  ·  vermelha
       sem o teste em cadeia, a palavra muda aos poucos (constituição §I)

09:51  🧬 EXIGE   correção sem cut_id na chave  ·  vermelha
       prova que a correção vale só para o corte

09:51  📐 BARRA   correção no texto de cut show, cut list e cut preview
       via serviço e ponta a ponta pela CLI; preview hoje sai sem ela

09:51  🧬 EXIGE   preview_cut sem correções  ·  vermelha
       é o estado do baseline; se sobreviver, FR-004 não está provado

09:51  ⚠️ LACUNA  resposta com corrected: bool
       cut show já usa corrected = texto ou null (1.1.e.1 D3); mesmo
       nome com dois tipos confunde agentes — barra: forma do words[]

09:51  ⚠️ LACUNA  FK de word_fixes sem ON DELETE CASCADE
       reprocessar e sermon suggest apagam cortes com foreign_keys ON;
       sem CASCADE quebram — Passo 2 fica PARCIAL

09:51  ⚠️ LACUNA  edited não decidido
       sermon suggest apaga sugeridos não editados e leva a correção
       junto — barra: sucesso marca edited = 1

09:51  ⚠️ LACUNA  Passo 5 só com CHANGELOG
       docs/cli.md §8.3 promete prévia sem correção até 1.1.f.2; §8.5 e
       a arquitetura §4 ficam desatualizados

09:51  ⚠️ LACUNA  sem NFC nem strip no texto recebido
       desfazer com entrada NFD gravaria correção invisível

## Rodada 1 · implementador

09:56  🔴 RED    test_spelling_lock_accepts_only_a_fix_within_a_third_of_the_
       original_word
       tabela à mão: distância, limite e aceite de 10 casos (acento,
       maiúscula, pontuação, hífen, troca, palavra curta, limite exato)
       FR-002; plano de QA Passo 1; L2, L3
       ModuleNotFoundError: No module named 'wordcut.cuts.spelling'

09:56  🟢 GREEN  test_spelling_lock_accepts_only_a_fix_within_a_third_of_the_
       original_word  ·  10 passed

09:57  🟢 GREEN  test_word_core_keeps_lower_case_letters_digits_and_hyphens_
       only  ·  15 passed
       caracteriza word_core, pública e criada no ciclo anterior; prova
       pela mutação: sem lower(), sem tirar pontuação, tirando o hífen

09:57  🟢 GREEN  test_levenshtein_counts_insertions_deletions_and_
       substitutions_as_one_edit_each  ·  20 passed
       caracteriza levenshtein do ciclo anterior; troca custando 2 fica
       vermelha (9 falhas)

09:57  🧬 MUTAÇÃO 0.34→0.5 · sem max(1,…) · <= virando < · sem lower() ·
       sem tirar pontuação · tirando hífen · troca custa 2 · sem NFC:
       todas vermelhas

09:57  ✅ PASSO 1/5 — Trava pura  ·  +20 testes  ·  suíte 961

09:58  🔴 RED    test_fixing_a_word_answers_the_word_as_cut_show_gives_it_
       with_its_cut
       "Jesús" → "Jesus" devolve a palavra no formato de words[], com o
       corte e corrected = "Jesus"
       Cenário: correção aceita; D1
       ImportError: cannot import name 'fix_word' from
       'wordcut.service.cuts'

09:59  🟢 GREEN  test_fixing_a_word_answers_the_word_as_cut_show_gives_it_
       with_its_cut  ·  1 passed

09:59  🔴 RED    test_a_fixed_word_shows_its_fix_in_cut_show_and_keeps_its_
       original_text
       a correção fica gravada: cut show traz corrected e text original
       FR-001; Cenário: correção aceita; D4
       At index 1 diff: ('Jesús', None) != ('Jesús', 'Jesus')

09:59  🟢 GREEN  test_a_fixed_word_shows_its_fix_in_cut_show_and_keeps_its_
       original_text  ·  23 passed

09:59  🔴 RED    test_a_fix_that_changes_the_word_is_too_different_and_says_
       how_far_without_the_typed_text
       "não" → "sim" barra com distância 3, limite 1 e o original, sem
       repetir o texto digitado
       Cenário: troca bloqueada (1.1.f.3); L6
       Failed: DID NOT RAISE WordcutError

09:59  🟢 GREEN  test_a_fix_that_changes_the_word_is_too_different_and_says_
       how_far_without_the_typed_text  ·  3 passed

10:00  🔴 RED    test_fixing_a_word_back_to_its_original_spelling_removes_
       the_fix
       texto igual ao original (digitado em NFD, com espaços) apaga a
       correção: corrected volta a null
       FR-003; Cenário: desfazer; L3
       AssertionError: assert ('Jesús', 'Jesús') == (None, None)

10:00  🟢 GREEN  test_fixing_a_word_back_to_its_original_spelling_removes_
       the_fix  ·  4 passed

10:00  🔴 RED    test_a_successful_fix_or_undo_marks_the_cut_edited_at_that_
       moment
       gravar ou desfazer marca edited = 1 e updated_at = now, para o
       sermon suggest não levar a correção
       L1
       assert (False, datet...) == (True, dateti...)

10:00  🟢 GREEN  test_a_successful_fix_or_undo_marks_the_cut_edited_at_that_
       moment  ·  6 passed

10:00  🔴 RED    test_a_word_the_cut_does_not_play_is_an_invalid_word_id
       palavra inexistente, de outra pregação, ou na faixa mas fora dos
       trechos → invalid_argument com argument = word_id
       Borda: palavra fora do corte
       KeyError: 999999 · KeyError: 8 · KeyError: 3

10:00  🟢 GREEN  test_a_word_the_cut_does_not_play_is_an_invalid_word_id
       ·  9 passed

10:00  🔴 RED    test_a_text_that_is_not_one_word_is_an_invalid_text_
       without_echoing_it
       vazio, só espaços, duas palavras ou tabulação no meio →
       invalid_argument com argument = text, sem repetir o texto
       Borda: mais de uma palavra; L6
       'spelling_too_different' != 'invalid_argument' (4 falhas)

10:01  🟢 GREEN  test_a_text_that_is_not_one_word_is_an_invalid_text_
       without_echoing_it  ·  13 passed

10:02  🟢 GREEN  guardas do Passo 2 (já passam com o código dos ciclos
       acima; cada um tem a mutação que o deixa vermelho)  ·  28 passed
       not_found com cut_id · nova correção substitui · trava compara
       com o original ("Jesus" e depois "Jesu" barra; L4) · recusa não
       muda show_cut nem CutRow · vale só no corte · desfazer sem
       correção é sucesso (L5) · ordem das recusas (L7) · exclusões com
       correção gravada (D6)

10:02  🧬 MUTAÇÃO comparar com a correção atual · desfazer gravando o
       original · sem mark_edited · FK de cut_id sem CASCADE · FK de
       word_id sem CASCADE · chave sem cut_id · leitura sem filtro de
       corte: todas vermelhas

10:02  🔧 AJUSTE  test_cuts_repository: user_version == 7 vira >= 7, como
       os testes de migração vizinhos; a 0008 sobe a versão

10:03  ✅ PASSO 2/5 — Persistência e serviço  ·  +28 testes  ·  suíte 989

10:03  🔴 RED    test_cut_show_assembles_the_fixed_spelling_into_the_cut_
       and_segment_text
       com a correção, o text do corte e o do trecho trazem "Jesus"
       FR-004; D2, D4
       'Deus governa. Irmãos, Jesús' != 'Deus governa. Irmãos, Jesus'

10:04  🟢 GREEN  test_cut_show_assembles_the_fixed_spelling_into_the_cut_
       and_segment_text  ·  54 passed
       assemble(segments, words, fixes) com fixes obrigatório; list e
       preview passam {} até os próximos ciclos

10:04  ♻️ REFACTOR fix_word quebrado em _played_word e _one_word  ·  verde

10:04  🔴 RED    test_preview_plays_the_fixed_spelling_with_the_same_times_
       order_and_duration
       a prévia toca "Irmãos, Jesus"; tempos, out_of_order e duração
       iguais aos de antes
       FR-004; Verificação: refletido na prévia
       AssertionError: segments[1].text 'Irmãos, Jesús'

10:04  🟢 GREEN  test_preview_plays_the_fixed_spelling_with_the_same_times_
       order_and_duration  ·  34 passed

10:04  🔴 RED    test_cut_list_assembles_each_cut_with_its_own_fixes
       cut list traz o texto com a correção só no corte corrigido
       D3; FR-004
       'Irmãos, Jesús não falha.' != 'Irmãos, Jesus não falha.'

10:04  🟢 GREEN  test_cut_list_assembles_each_cut_with_its_own_fixes
       ·  52 passed

10:05  🟢 GREEN  test_a_word_the_cut_plays_twice_shows_its_fix_in_both_
       segments  ·  32 passed
       guarda: já passa, a correção é por palavra do trecho

10:05  🧬 MUTAÇÃO preview sem correções · list sem correções · words[].text
       com o corrigido · trecho sem correção: todas vermelhas; testes de
       test_cuts_service e test_cut_preview verdes sem editar valores

10:05  ✅ PASSO 3/5 — Montagem  ·  +4 testes  ·  suíte 993

10:06  🔴 RED    test_fix_word_with_json_prints_the_fixed_word_with_its_
       cut_and_exits_0
       wordcut cut fix-word <id> <word_id> Jesus --json → 0 e a palavra
       no formato de words[], com o corte
       Cenário: correção aceita; FR-001; D1
       At index 0 diff: 2 != 0 (invalid choice: fix-word)

10:06  🟢 GREEN  test_fix_word_with_json_prints_the_fixed_word_with_its_
       cut_and_exits_0  ·  1 passed

10:08  🟢 GREEN  guardas do Passo 4 (o contrato da CLI já mapeia erros e
       saídas)  ·  14 passed
       spelling_too_different → 5 com details e sem o texto · word_id
       fora do corte e texto que não é uma palavra → 2 · word_id não
       numérico → 2 sem eco · not_found → 3 · desfazer · --json antes,
       entre e depois · uma linha legível · erro só no stderr · ponta a
       ponta: cut show, preview --json e preview legível com a correção

10:08  🔧 AJUSTE  test_cut_command: fix-word na lista de ações do --help e
       no teste de exemplo por ação

10:08  🧬 MUTAÇÃO saída de spelling_too_different · sem details.limit ·
       mensagem com o texto digitado: todas vermelhas

10:08  ✅ PASSO 4/5 — CLI  ·  +14 testes  ·  suíte 1008

10:10  📝 DOCS   sem TDD: CHANGELOG (cut fix-word, trava, migração 0008);
       docs/cli.md §8.2 (words.text original e corrected), §8.3 (texto
       com a correção), §8.5 (regra, erros, resposta, saída legível);
       arquitetura §4 (cuts.spelling, word_fixes, cut fix-word); ajuda
       do grupo cut e docstring do módulo

10:10  ✅ PASSO 5/5 — Documentação  ·  +0 testes  ·  suíte 1008

10:10  🏁 FIM     suíte 1008 passed · ruff check, ruff format --check e
       mypy limpos · sem commit (override do orquestrador)

## Rodada 1 · QA

10:12  📊 SUÍTE  1008 passed  ·  0 failed
       ruff check, ruff format --check e mypy limpos; suítes do plano
       de QA: core 77, regressão 37, cli 55, todas verdes

10:13  🧬 MUTAÇÕES · barra dos passos 1–4, cópia no scratchpad  ·  29 de 30
       mortas
       ☠️  0.34→0.5 · sem max(1) · <= vira <                 test_spelling
       ☠️  sem lower · sem pontuação · sem hífen            test_spelling
       ☠️  troca custa 2 · núcleo sem NFC                   test_spelling
       ☠️  comparar com a correção atual · gravar antes     test_fix_word
       ☠️  desfazer grava o original · sem mark_edited      test_fix_word
       ☠️  palavra pela faixa · leitura sem filtro de corte test_fix_word
       ☠️  FK cut_id e word_id sem CASCADE                  test_fix_word
       ☠️  preview e list sem correções · trecho sem ela    test_fix_word
       ☠️  words[].text corrigido · sem details.limit       test_fix_word
       ☠️  saída 5→1 · mensagem com o texto digitado        cli
       🚨  chave só por word_id (PK e ON CONFLICT juntos)
           SOBREVIVEU — corrigir o corte B tira ou sobrescreve a
           correção do corte A; o teste só corrige um dos dois cortes
       a versão do implementador (só a PK) morre por erro de SQL do
       ON CONFLICT, não por comportamento

10:13  🔎 QA     passo 1/5 — Trava pura  ·  ✅ PASS
       tabela à mão com os 10 casos da barra; 8 mutações vermelhas

10:13  🔎 QA     passo 2/5 — Persistência e serviço  ·  ⚠️ PARCIAL
       mutação exigida "chave sem cut_id" sobrevive na forma coerente;
       falta corrigir a mesma palavra em dois cortes e ver as duas

10:13  🔎 QA     passo 3/5 — Montagem  ·  ✅ PASS
       show, preview e list com a correção; testes do baseline sem edição

10:13  🔎 QA     passo 4/5 — CLI  ·  ✅ PASS
       saídas 0/2/3/5, details, sem eco, --json em três posições, ponta a
       ponta; sem trava (L10)

10:14  🔎 QA     passo 5/5 — Documentação  ·  ✅ PASS
       CHANGELOG, cli.md §8.2, §8.3, §8.5 e arquitetura §4 atualizados

10:14  🔎 QA     fatos do implementador  ·  ✅ conformes
       db/word_fixes.py está no Contexto de código do plan.md; == 7 → >= 7
       segue os vizinhos, e test_db fixa a última migração empacotada

## Rodada 2 · implementador

10:16  🔧 CORREÇÃO  entrada 10:02 da Rodada 1, "chave sem cut_id: vermelha"
       motivo errado: mudar só a PK quebrava o ON CONFLICT (cut_id,
       word_id) com erro de SQL; nenhum teste via o comportamento. Na
       forma coerente (PK e ON CONFLICT só por word_id) a mutação
       sobrevivia: o teste só corrigia um dos dois cortes

10:16  🟢 GREEN  test_two_cuts_fixing_the_same_word_each_keep_their_own_
       spelling[cut show, cut preview, cut list]  ·  3 passed
       guarda: a mesma palavra corrigida em dois cortes da pregação,
       "Jesus" num e "JESUS" no outro; cada corte mostra a sua em
       show_cut, preview_cut e list_cuts
       Borda: a correção vale só para aquele corte; QA Rodada 1 Passo 2

10:16  🧬 MUTAÇÃO chave só por word_id (PK e ON CONFLICT juntos)  ·
       vermelha pelo comportamento: 3 failed, 32 passed, só
       AssertionError, nenhum erro de SQL
       ['Irmãos, JES..., 'Jesús não'] == ['Irmãos, Jes..., 'JESUS não']
       o segundo corte sobrescreve o texto e a correção fica no primeiro

10:17  ✅ PASSO 2/5 — Persistência e serviço  ·  +3 testes  ·  suíte 1011
       ruff check, ruff format --check e mypy limpos · sem commit
       (override do orquestrador)

## Rodada 2 · QA

10:20  📊 SUÍTE  1011 passed  ·  0 failed
       barra core 80 · regressão de exclusão 37 · cli 55; ruff check,
       ruff format --check e mypy limpos

10:20  🧬 MUTAÇÕES · chave da correção por corte  ·  3 de 4 mortas
       ☠️  PK e ON CONFLICT só por word_id               3 (só Assertion)
       ☠️  of_sermon mistura as correções dos cortes      1 (cut list)
       ☠️  of_cut sem filtro de corte                     3
       🚨  delete sem filtro de corte (só word_id)
           SOBREVIVEU — desfazer a correção no corte B apaga a do
           corte A; nenhum teste desfaz num corte com o outro corrigido

10:20  🔎 QA     passo 2/5 — Persistência e serviço  ·  ⚠️ PARCIAL
       a mutação exigida (chave só por word_id) agora morre pelo
       comportamento; achado novo: o desfazer não é provado por corte

10:20  🔎 QA     passos 1, 3, 4 e 5  ·  ✅ PASS
       sem mudança desde a Rodada 1; suítes e checagens verdes

## Rodada 3 · implementador

10:21  🟢 GREEN  test_undoing_a_fix_in_one_cut_keeps_the_fix_of_the_same_
       word_in_another_cut[cut show, cut preview, cut list]  ·  3 passed
       guarda: a mesma palavra corrigida em dois cortes ("Jesus" em A,
       "JESUS" em B); desfazer em B (texto igual ao original, "Jesús")
       volta B ao original e A mantém "Jesus" em show_cut, preview_cut e
       list_cuts
       Borda: a correção vale só para aquele corte; QA Rodada 2 Passo 2

10:22  🧬 MUTAÇÃO word_fixes.delete só por word_id (sem cut_id)  ·
       vermelha pelo comportamento: 3 failed, 49 passed, só
       AssertionError, nenhum erro de SQL
       At index 0 diff: 'Irmãos, Jesús não falha.' !=
       'Irmãos, Jesus não falha.'
       desfazer no corte B apagava a correção do corte A

10:22  🧬 MUTAÇÕES · demais operações de db/word_fixes.py pelo par
       (cut_id, word_id)  ·  4 de 4 mortas, mais 1 equivalente
       ☠️  of_cut sem filtro de corte                      5
       ☠️  of_sermon com as correções de um corte em todos 3 (cut list)
       ☠️  put com PK e ON CONFLICT só por word_id         6
       ☠️  put gravando sob outro corte                    6
       ≡   of_sermon sem filtro de pregação: equivalente; list_cuts só
           lê fixes.get(row.id) dos cortes da própria pregação, e IDs de
           corte não se repetem entre pregações. Sem teste possível pela
           interface pública

10:23  ✅ PASSO 2/5 — Persistência e serviço  ·  +3 testes  ·  suíte 1014
       ruff check, ruff format --check e mypy limpos · sem commit
       (override do orquestrador)

## Rodada 3 · QA

10:28  📊 SUÍTE  1014 passed  ·  0 failed
       barra core 83 · regressão de exclusão 37 · cli 55; ruff check,
       ruff format --check e mypy limpos; test_cuts_service e
       test_cut_preview sem diff contra o baseline

10:28  🧬 MUTAÇÕES · db/word_fixes.py pelo par (cut_id, word_id)  ·
       4 de 4 mortas, mais 1 equivalente
       ☠️  delete só por word_id (a exigida)            3 (só Assertion)
       ☠️  of_cut sem filtro de corte                    5
       ☠️  PK e ON CONFLICT só por word_id               6
       ☠️  desfazer grava o original                     3
       ≡   of_sermon sem filtro de pregação: 86/86 verdes. Equivalente
           no comportamento: único chamador é list_cuts, que só lê
           fixes.get(row.id) dos cortes da pregação; cuts.id é
           AUTOINCREMENT (0007), não se reusa; o JOIN e o CASCADE não
           deixam correção de corte apagado. Só mudaria o contrato do
           próprio repositório (docstring) e o custo da consulta; a
           barra prova pelo serviço, não pelo repositório

10:28  🔎 QA     passo 2/5 — Persistência e serviço  ·  ✅ PASS
       desfazer num corte mantém a correção do outro; a mutação exigida
       morre pelo comportamento em show, preview e list

10:28  🔎 QA     passos 1, 3, 4 e 5  ·  ✅ PASS
       sem mudança desde a Rodada 1; suítes e checagens verdes
