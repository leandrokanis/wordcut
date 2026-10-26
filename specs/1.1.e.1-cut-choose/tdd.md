## Plano de QA

baseline_commit: ebbe27e191101f560f7c06ecea5272d3aead8c43

09:08  📐 BARRA   texto montado e duração saem das palavras, na ordem do
       corte, sem limpeza
       teste no core com valores escritos à mão e trecho fora de ordem;
       a mesma fórmula no teste não prova nada

09:08  🧬 EXIGE   duração × 0,82 (CLEANED_SHARE)  ·  vermelha
       prova que a duração do corte é a bruta, não a estimada da sugestão

09:08  🧬 EXIGE   inverter a ordem dos trechos  ·  vermelha
       prova que o texto segue a ordem em que o corte toca

09:08  📐 BARRA   choose/discard/restore mudam só status (e updated_at)
       CutRow antes e depois, campo a campo; constituição §I

09:08  🧬 EXIGE   set_status gravar edited = 1  ·  vermelha
       se sobreviver, o sermon suggest deixa de substituir o corte

09:08  📐 BARRA   descartados por último, suggested e chosen por id
       lista com estados intercalados; filtro --status

09:08  📐 BARRA   contrato da CLI: items, códigos 0/2/3, stdout só resultado
       main(argv) + capsys, no padrão de test_sermon_command.py

09:08  ⚠️ LACUNA  legacy.py registra o comando de topo cut
       add_parser("cut") repetido derruba o parser no Python 3.11;
       sem decisão (renomear o antigo e atualizar README e skill),
       o passo 3 fica PARCIAL

09:08  ⚠️ LACUNA  plano: restore → suggested de qualquer estado
       spec e §8.4: só o descartado volta; barra segue a spec

09:08  ⚠️ LACUNA  plano cria of_sermon, que já existe
       criar só by_id e set_status; a ordem do list fica no serviço

09:08  ⚠️ LACUNA  correções de grafia sem armazenamento no baseline
       words[].corrected = null e caption/render_options = row or {}

## Rodada 1 · implementador

09:12  ▶️ INÍCIO  4 passos: montagem, serviço, CLI, documentação
       baseline verde: 875 passed
       plan.md: Decisões técnicas com D1–D7 e L1–L10; Contexto de código
       com os nomes reais (by_id, set_status, shown_cut, position)

09:13  --- Passo 1: Montagem ---

09:13  🔴 RED    test_cut_text_joins_its_segments_in_the_order_it_plays_and_
       duration_adds_their_spans
       corte com trecho fora de ordem: texto na ordem do corte, to_word
       inclusivo, duração = soma das faixas, sem ×0,82, ao ms (1,9 à mão)
       FR-004; plano: Texto montado, Duração; QA D5, D7
       ModuleNotFoundError: No module named 'wordcut.service.cuts'

09:13  🟢 GREEN  test_cut_text_joins_its_segments_in_the_order_it_plays_and_
       duration_adds_their_spans  ·  1 passed

09:13  🔴 RED    test_cut_segments_carry_their_times_and_text_and_its_words_
       follow_the_segments
       segments do show com início, fim e texto de cada trecho; words na
       ordem do corte com word_id, tempos e corrected null
       FR-002; docs/cli.md §8.2; plano: Formato do show; QA D3
       KeyError: 'segments'

09:13  🟢 GREEN  test_cut_segments_carry_their_times_and_text_and_its_words_
       follow_the_segments  ·  2 passed

09:13  ♻️ REFACTOR  ruff format no teste; nada a extrair

09:13  ✅ PASSO 1/4 — Montagem  ·  +2 testes  ·  suíte 877

09:14  --- Passo 2: Serviço ---

09:14  🔴 RED    test_shown_cut_has_the_sermon_cut_fields_plus_assembly_and_
       default_style_and_no_renders
       chaves completas do show: shown_cut + sermon_id, text, duration,
       segments enriquecidos, words, caption {}, render_options {}, renders []
       FR-002; docs/cli.md §7.2, §8.2; QA D2, D4
       AssertionError: Right contains 12 more items

09:14  🟢 GREEN  test_shown_cut_has_the_sermon_cut_fields_plus_assembly_and_
       default_style_and_no_renders  ·  3 passed
       (caption e render_options constantes: o mínimo para este teste)

09:14  🔴 RED    test_shown_cut_keeps_the_caption_style_and_export_options_
       stored_with_it
       caption e render_options gravados no corte saem no show; nulo vira {}
       spec, Pressupostos; QA D4
       AssertionError: assert ({}, {}) == ({'font_size'...ity': 'high'})

09:14  🟢 GREEN  test_shown_cut_keeps_the_caption_style_and_export_options_
       stored_with_it  ·  4 passed

09:15  🔴 RED    test_showing_a_cut_that_does_not_exist_is_not_found
       corte inexistente → not_found com details.cut_id
       spec, casos de borda; QA L7
       E       AssertionError (assert row is not None)

09:15  🟢 GREEN  test_showing_a_cut_that_does_not_exist_is_not_found  ·  5 passed

09:15  🔴 RED    test_cuts_are_listed_in_the_order_they_were_added_with_the_
       discarded_ones_last
       estados intercalados: suggested e chosen por id, depois discarded
       FR-001; docs/cli.md §8.1; plano: Ordem do list; QA D1
       ImportError: cannot import name 'list_cuts'

09:15  🟢 GREEN  test_cuts_are_listed_in_the_order_they_were_added_with_the_
       discarded_ones_last  ·  6 passed

09:15  🔴 RED    test_listed_cut_has_the_sermon_cut_fields_plus_its_text_and_
       duration_without_words
       item do list = shown_cut + sermon_id, text, duration; sem words
       FR-001; QA L6
       AssertionError: Differing items (sem sermon_id, text, duration)

09:15  🟢 GREEN  test_listed_cut_has_the_sermon_cut_fields_plus_its_text_and_
       duration_without_words  ·  7 passed

09:15  🔴 RED    test_listing_by_status_keeps_only_the_cuts_in_that_state
       --status filtra os cortes da pregação
       FR-001; spec, Cenário: listar
       TypeError: list_cuts() takes 2 positional arguments but 3 were given

09:15  🟢 GREEN  test_listing_by_status_keeps_only_the_cuts_in_that_state  ·  8 passed

09:15  🔴 RED    test_listing_the_cuts_of_a_sermon_that_does_not_exist_is_not_found
       pregação inexistente no list → not_found com details.sermon_id
       spec, casos de borda; QA L7
       Failed: DID NOT RAISE WordcutError

09:16  🟢 GREEN  test_listing_the_cuts_of_a_sermon_that_does_not_exist_is_not_
       found  ·  9 passed
       service.sermons._existing virou existing_sermon (público), para o
       not_found da pregação ter uma origem só

09:16  🛡️ GUARDA  test_a_sermon_not_processed_yet_lists_no_cuts  ·  10 passed
       verde de saída: pregação sem palavras nem cortes → items []
       QA, matriz do passo 2

09:16  🔴 RED    test_choosing_a_suggested_cut_makes_it_chosen_and_gives_it_as_
       show_does
       choose → chosen; a transição devolve o objeto de cut show
       spec, Cenário: escolher; QA L4
       ImportError: cannot import name 'choose_cut'

09:16  🟢 GREEN  test_choosing_a_suggested_cut_makes_it_chosen_and_gives_it_as_
       show_does  ·  11 passed

09:16  🔴 RED    test_discarding_a_chosen_cut_makes_it_discarded
       discard → discarded, a partir de qualquer estado
       spec, Cenário: descartar; plano: Transições
       ImportError: cannot import name 'discard_cut'

09:16  🟢 GREEN  test_discarding_a_chosen_cut_makes_it_discarded  ·  12 passed

09:16  🔴 RED    test_restoring_a_discarded_cut_makes_it_suggested_again
       restore devolve o descartado a suggested
       spec, Cenário: restaurar; docs/cli.md §8.4
       ImportError: cannot import name 'restore_cut'

09:16  🟢 GREEN  test_restoring_a_discarded_cut_makes_it_suggested_again  ·  13 passed

09:17  🔴 RED    test_restoring_a_cut_that_is_not_discarded_leaves_it_as_it_was
       [suggested, chosen]
       restore só mexe em discarded; nos outros estados nada é gravado
       spec, casos de borda; docs/cli.md §8.4; QA L2
       chosen: status 'suggested' != 'chosen'; suggested: updated_at mudou

09:17  🟢 GREEN  test_restoring_a_cut_that_is_not_discarded_leaves_it_as_it_was
       ·  15 passed

09:17  🔴 RED    test_repeating_a_transition_writes_nothing
       [chosen-choose_cut, discarded-discard_cut]
       repetir a transição é idempotente e não grava: updated_at intacto
       spec, casos de borda; QA L5
       AssertionError: CutRow.updated_at 2026-10-27 09:15 != 2026-10-26 22:40

09:17  🟢 GREEN  test_repeating_a_transition_writes_nothing  ·  17 passed
       ♻️ as três transições passam a ler o corte uma vez e gravar só
       quando o estado muda (_with_status)

09:18  🛡️ GUARDA  test_choosing_discarding_and_restoring_change_only_the_status_
       of_the_cut  ·  verde de saída
       CutRow antes e depois de choose → discard → restore = replace(before,
       updated_at=LATER); caption e render_options gravados
       FR-003; constituição §I

09:18  🛡️ GUARDA  test_changing_the_state_of_a_cut_that_does_not_exist_is_not_
       found [choose, discard, restore]  ·  verde de saída (_existing antes de
       gravar)  ·  21 passed

09:18  🧬 MUTAÇÕES  vermelhas, uma por vez, desfeitas em seguida:
       set_status grava edited = 1; descartados primeiro; restore de
       qualquer estado vira suggested; filtro de status ignorado

09:18  ✅ PASSO 2/4 — Serviço  ·  +19 testes  ·  core 610

09:18  --- Passo 3: CLI ---

09:18  🔴 RED    test_list_with_json_prints_the_items_with_text_duration_and_
       state_discarded_last
       cut list --sermon --json: envelope items, texto, duração, estado,
       descartados por último, saída 0
       FR-001; docs/cli.md §4.3, §8.1; spec, Cenário: listar
       KeyError: 'items' (o cut da CLI anterior respondeu com erro de uso)

09:19  🟢 GREEN  test_list_with_json_prints_the_items_with_text_duration_and_
       state_discarded_last  ·  1 passed
       L1: o cut da CLI anterior virou cut-sermon (legacy.py); test_cli.py
       passa a listar cut-sermon e cut no --help (cli 286 passed)

09:20  🛡️ GUARDA  test_previous_cut_command_is_now_cut_sermon_and_still_cuts_and_
       reports_the_sermon  ·  3 passed
       L1: cut-sermon recebe os mesmos argumentos e imprime o mesmo resumo;
       dublê em legacy.cut_sermon, que só baixa do YouTube e roda ffmpeg
       verde porque o rename veio no GREEN anterior; com legacy.py do
       baseline, os 3 testes do arquivo ficam vermelhos (parser em conflito)

09:20  🔴 RED    test_list_by_status_keeps_only_the_cuts_in_that_state
       cut list --status filtra
       FR-001; docs/cli.md §8.1
       KeyError: 'items' (--status não reconhecido)

09:20  🟢 GREEN  test_list_by_status_keeps_only_the_cuts_in_that_state  ·  2 passed

09:20  🔴 RED    test_show_with_json_prints_the_whole_cut
       cut show --json: as chaves completas de §8.2 (não um subconjunto)
       FR-002; docs/cli.md §8.2; spec, Cenário: detalhar
       KeyError: 'text' (show não existe: saiu o erro de uso)

09:20  🟢 GREEN  test_show_with_json_prints_the_whole_cut  ·  3 passed

09:20  🔴 RED    test_choose_discard_and_restore_change_the_state_and_keep_the_
       segments
       cut choose → discard → restore: chosen, discarded, suggested, saída 0,
       trechos iguais aos do show
       FR-003; spec, Cenário: escolher, descartar, restaurar; QA L4
       KeyError: 'status' (ações inexistentes)

09:21  🟢 GREEN  test_choose_discard_and_restore_change_the_state_and_keep_the_
       segments  ·  4 passed

09:21  🛡️ GUARDA  contrato da CLI, verde de saída (o contrato é compartilhado e o
       serviço já levanta os erros)  ·  20 passed
       test_a_sermon_or_cut_that_does_not_exist_is_not_found_and_exits_3 [5]
       test_missing_or_malformed_arguments_are_invalid_and_exit_2 [4]
       test_a_transition_with_nothing_to_change_exits_0_with_the_cut_as_it_
       was [4]
       test_json_option_is_accepted_before_between_and_after_the_cut_
       action [3]
       spec, casos de borda; docs/cli.md §4.3, §5; ADR-0015; QA L2, L7

09:21  🔴 RED    test_list_without_json_prints_one_line_per_cut_with_state_in_
       portuguese_and_duration
       texto legível: id, estado em português, duração, título
       docs/cli.md §4.2; QA L9
       AssertionError: '2  2 chosen\n…' != '2  escolhido  1,8 s  2 chosen\n…'

09:21  🟢 GREEN  test_list_without_json_prints_one_line_per_cut_with_state_in_
       portuguese_and_duration  ·  21 passed

09:21  🔴 RED    test_list_without_json_says_so_when_the_sermon_has_no_cuts
       pregação sem cortes: "Nenhum corte." em vez de linha vazia
       docs/cli.md §4.2; QA L9
       AssertionError: assert (0, '\n') == (0, 'Nenhum corte.\n')

09:21  🟢 GREEN  test_list_without_json_says_so_when_the_sermon_has_no_cuts  ·  22 passed

09:21  🔴 RED    test_show_without_json_prints_title_state_duration_range_
       segments_and_text
       texto legível do show e das transições: título, estado, duração,
       faixa, trechos com tempos e texto montado
       docs/cli.md §4.2, §8.2; QA L9
       AssertionError: 'Corte 1: 1 chosen\n' != 'Corte 1:…ãos, graça\n'

09:22  🟢 GREEN  test_show_without_json_prints_title_state_duration_range_
       segments_and_text  ·  23 passed

09:23  🛡️ GUARDA  verde de saída  ·  30 passed
       test_error_without_json_goes_to_stderr_in_portuguese_and_stdout_
       stays_empty (docs/cli.md §4.1, §5.2)
       test_cut_help_lists_its_actions
       test_each_cut_action_help_shows_an_example_ready_to_copy [5]

09:23  ♻️ REFACTOR  _listed_line extraído (linha > 100); ruff format no
       legacy.py; comentário do cut-sermon diz o motivo do nome

09:23  ✅ PASSO 3/4 — CLI  ·  +31 testes (30 em test_cut_command.py, 1 em
       test_legacy_commands.py)  ·  cli 316

09:24  --- Passo 4: Documentação ---

09:24  📝 DOCS   sem TDD (texto): CHANGELOG [Não lançado] Adicionado (cut list,
       show, choose, discard, restore) e Alterado (cut → cut-sermon);
       docs/architecture/README.md §4 (service.cuts, cuts.assembly, comandos
       cut, cut-sermon); README.md e skills/video-cortar-pregacao/SKILL.md
       com cut-sermon (L1)

09:24  ✅ PASSO 4/4 — Documentação  ·  +0 testes  ·  suíte 927

09:24  🏁 VERIFICAÇÃO  uv run pytest -q: 927 passed; ruff check, ruff format
       --check e mypy limpos; sem commit (override do orquestrador)

## Rodada 1 · QA

09:25  📊 SUÍTE  927 passed  ·  0 failed
       core 610, cli 316; ruff check, ruff format --check e mypy limpos

09:26  🧬 MUTAÇÕES · cópia no scratchpad, 23 do conjunto  ·  23 de 23 mortas
       ☠️  inverter a ordem dos trechos                        6 testes
       ☠️  excluir to_word (off-by-one)                        8 testes
       ☠️  duração × 0,82                                      6 testes
       ☠️  unir trechos sem espaço                             5 testes
       ☠️  duração = fim do último − início do primeiro        5 testes
       ☠️  descartados primeiro / tudo por id                  3 testes
       ☠️  set_status grava edited = 1                         1 teste
       ☠️  restore de chosen vira suggested                    2 testes
       ☠️  filtro de status ignorado                           2 testes
       ☠️  repetição grava updated_at (L5)                     4 testes
       ☠️  show grava updated_at (L3)                          5 testes
       ☠️  código de saída do not_found                        6 testes
       ☠️  lista nua em vez de items                           4 testes

09:28  🧬 MUTAÇÕES · L3 no list, fora do conjunto exigido  ·  1 de 2 mortas
       ☠️  list marca os sugeridos como chosen                 4 testes
       🚨  list regrava só updated_at       SOBREVIVEU — nenhum teste
       olha updated_at depois de um list; conteúdo (§I) intacto

09:28  🛡️ GUARDA  cut-sermon com legacy.py do baseline  ·  3 failed
       a guarda morde: sem o rename o parser inteiro cai

09:29  🔎 QA     L8: palavra ausente via CLI  ·  internal_error, saída 1
       "Erro interno inesperado.", sem traceback, em JSON e em texto

09:30  🔎 QA     passo 1/4 — Montagem  ·  ✅ PASS
       valores à mão, trecho fora de ordem; 6 mutações de montagem mortas

09:30  🔎 QA     passo 2/4 — Serviço  ·  ✅ PASS
       choose/discard/restore_cut no lugar de set_cut_status, como o
       plan.md nomeia; comportamento da matriz provado

09:30  🔎 QA     passo 3/4 — CLI  ·  ✅ PASS
       contrato 0/2/3, items, --json em 3 posições; L1 como cut-sermon

09:30  🔎 QA     passo 4/4 — Documentação  ·  ✅ PASS
       CHANGELOG, arquitetura §4, README e skill com cut-sermon
