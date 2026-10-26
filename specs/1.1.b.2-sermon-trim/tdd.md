## Plano de QA

baseline_commit: aef33ce865e3df33508b8268c2afa22a98517b9a

02:31  📐 BARRA   trim grava bordas e leva created/trimmed/failed a trimmed
       pytest no core com SQLite real; relê por show_sermon

02:31  📐 BARRA   erro de regra não muda nada (estado e bordas iguais)
       relê a pregação depois de cada erro; prova o "nada muda" do spec

02:31  📐 BARRA   trim --json == show --json, com duration 2780.0
       main([...]) + capsys; contrato é a saída, não a chamada interna

02:31  📐 BARRA   create com bordas inválidas não cria pregação
       sermon list --json vazio depois do erro

02:31  🧬 EXIGE   MIN_SERMON_SECONDS: `<` trocado por `<=`  ·  vermelha
       60,000 s exatos aceito; se sobreviver, a fronteira não é testada

02:31  🧬 EXIGE   limite end <= live_duration trocado por `<`  ·  vermelha
       end == live_duration aceito; prova a borda fechada da live

02:31  🧬 EXIGE   start >= end trocado por start > end  ·  vermelha
       start == end recusado com invalid_argument

02:31  🧬 EXIGE   processed passa a virar trimmed  ·  vermelha
       prova que o estado processed é mantido (FR-005)

02:31  🧬 EXIGE   needs_reprocess sempre false / aviso removido  ·  vermelha
       stderr com `sermon process --force` só em processed

02:31  🧬 EXIGE   remover o bloqueio de processing  ·  vermelha
       busy, saída 4, bordas intactas

02:31  🧬 EXIGE   tirar a validação de bordas antes do insert  ·  vermelha
       create inválido deixaria pregação órfã no banco

02:31  ⚠️ LACUNA  duration fixo em None em _listed; plano não o muda
       cenário 1 exige 2780.0; sem isso o passo 2 fica PARCIAL

02:31  ⚠️ LACUNA  "mesma transação" sem mecanismo; insert faz commit
       sem validar antes, passo 3 fica FAIL se sobrar pregação

02:31  ⚠️ LACUNA  create de vídeo existente com --start/--end
       barra: aplicar trim à existente; ignorar em silêncio é FAIL

02:31  ⚠️ LACUNA  parse_timestamp aceita nan, inf, 1:-5, 1_0
       inf vira Infinity no JSON; sem rejeição, passo 2 fica PARCIAL

02:31  ⚠️ LACUNA  live_duration nula sem regra de limite superior
       barra: só 0 <= start < end e 60 s; sem teste fica PARCIAL

02:31  ⚠️ LACUNA  busy sem tabela de tarefas (3.1.a.2 pendente)
       details pode faltar; estado processing posto por SQL no teste

02:31  ⚠️ LACUNA  ordem das validações e arredondamento a ms
       barra: limites antes de too_short; validar valor arredondado

02:31  ⚠️ LACUNA  update_range não toca updated_at
       barra: atualizar com relógio injetável e testar no repositório

02:31  ⚠️ LACUNA  needs_reprocess vazaria no JSON do trim
       barra: trim --json == show --json; expor exige docs/cli.md

## Rodada 1 · implementador

--- Passo 1: Regras no serviço ---

02:35  🔴 RED    test_trimming_a_created_sermon_records_the_borders_and_makes_it_trimmed
       pregação created recebe as bordas e passa a trimmed, relida por show
       FR-001; matriz 1(a)
       ImportError: cannot import name 'trim_sermon'

02:35  🟢 GREEN  test_trimming_a_created_sermon_records_the_borders_and_makes_it_trimmed  ·  1 passed

02:36  🔴 RED    test_trimming_an_unknown_sermon_is_not_found
       ID inexistente → not_found (saída 3) com details.sermon_id
       Casos de borda (spec); matriz 1(f)
       passou sem produção: show_sermon já levanta not_found depois do
       UPDATE vazio; mantido como guarda da ordem L7 (lookup antes)

02:36  🟢 GREEN  test_trimming_an_unknown_sermon_is_not_found  ·  2 passed

02:36  🔴 RED    test_trimming_a_sermon_being_processed_is_busy_and_changes_nothing
       pregação processing não aceita bordas: busy (saída 4), nada muda
       Decisões técnicas (transição); L6; matriz 1(c)
       Failed: DID NOT RAISE WordcutError

02:36  🟢 GREEN  test_trimming_a_sermon_being_processed_is_busy_and_changes_nothing  ·  3 passed

02:36  🔴 RED    test_range_shorter_than_a_minute_is_too_short_and_changes_nothing
       faixa de 59,999 s → sermon_too_short (saída 5), nada muda
       FR-002; matriz 1(d)
       Failed: DID NOT RAISE WordcutError

02:37  🟢 GREEN  test_range_shorter_than_a_minute_is_too_short_and_changes_nothing  ·  5 passed

02:36  🔴 RED    test_range_of_exactly_one_minute_is_accepted
       60,000 s exatos aceitos, inclusive quando a subtração em float dá
       59,9999… (4043.757 → 4103.757)
       FR-002; L8; mutação exigida `<` → `<=`
       passou sem produção (o arredondamento já estava em _duration);
       mutação `<` → `<=` aplicada à mão: 2 failed; revertida

02:37  🟢 GREEN  test_range_of_exactly_one_minute_is_accepted  ·  7 passed

02:36  🔴 RED    test_borders_outside_the_live_or_out_of_order_are_invalid_and_change_nothing
       start < 0, start == end, start > end, end > live_duration →
       invalid_argument com details start/end/live_duration, nada muda;
       limites vêm antes da faixa mínima
       FR-003; L7; matriz 1(e)
       AssertionError: 'sermon_too_short' != 'invalid_argument'

02:37  🟢 GREEN  test_borders_outside_the_live_or_out_of_order_are_invalid_and_change_nothing  ·  11 passed

02:37  🔴 RED    test_borders_may_touch_both_ends_of_the_live
       start == 0 e end == live_duration são aceitos (bordas fechadas)
       FR-003; matriz 1(e); mutação exigida `end <= live_duration` → `<`
       passou sem produção (guarda de fronteira); mutações aplicadas à
       mão: `<=`→`<` no fim 1 failed; `start < end`→`<=` 1 failed;
       revertidas

02:37  🟢 GREEN  test_borders_may_touch_both_ends_of_the_live  ·  12 passed

02:37  🔴 RED    test_borders_are_kept_to_the_millisecond_before_they_are_checked
       bordas arredondadas a ms na entrada; 7200.0004 numa live de 7200 s
       vira 7200.000 e é aceito
       L8; matriz 1(g)
       assert (0.0004, 60.0004) == (0.0, 60.0); 2 failed

02:37  🟢 GREEN  test_borders_are_kept_to_the_millisecond_before_they_are_checked  ·  14 passed

02:37  🔴 RED    test_trimming_again_or_after_a_failure_makes_the_sermon_trimmed_without_reprocess_warning
       trimmed e failed → trimmed, needs_reprocess false
       Decisões técnicas (transição); matriz 1(a), 1(b)
       KeyError: 'needs_reprocess'

02:37  🔴 RED    test_trimming_a_processed_sermon_keeps_it_processed_and_asks_for_a_reprocess
       processed grava as bordas, continua processed, needs_reprocess true
       FR-005; matriz 1(b); mutação exigida "processed vira trimmed"
       KeyError: 'needs_reprocess' (mesma execução do RED anterior)

02:38  🟢 GREEN  test_trimming_a_processed_sermon_keeps_it_processed_and_asks_for_a_reprocess  ·  17 passed

02:37  🔴 RED    test_trimmed_sermon_is_answered_as_shown_with_the_duration_between_its_borders
       resposta do trim = show + needs_reprocess; duration 2780.0
       FR-006; L1; cenário 1; matriz 1(h)
       AssertionError: None != 2780.0 (duration fixo em None)

02:38  🟢 GREEN  test_trimmed_sermon_is_answered_as_shown_with_the_duration_between_its_borders  ·  214 passed (core)

02:38  🔴 RED    test_listed_sermon_shows_the_duration_between_its_borders
       sermon list também traz duration = live_end − live_start
       L1; matriz 1(h)
       passou sem produção: _listed é compartilhado por list e show
       (GREEN anterior); fica como guarda do list

02:38  🔴 RED    test_live_of_unknown_duration_accepts_any_ordered_range_of_at_least_a_minute
       live sem duração conhecida: sem limite superior
       L5
       passou sem produção (_within_live já trata None); sem o ramo None
       a comparação end <= None levanta TypeError

02:38  🔴 RED    test_live_of_unknown_duration_still_refuses_borders_out_of_order
       live sem duração: start > end → invalid_argument, live_duration null
       L5
       passou sem produção; guarda dos details com null

02:38  🔴 RED    test_sermon_being_processed_is_busy_before_its_borders_are_checked
       processing com bordas inválidas → busy, não invalid_argument
       L7
       passou sem produção (busy é checado antes); guarda da ordem

02:38  🟢 GREEN  4 guardas acima  ·  22 passed

02:38  🔴 RED    test_recorded_range_is_read_back_with_its_status_and_update_time
       update_range grava bordas, estado e updated_at do relógio injetado
       L9; matriz 1(i)
       passou sem produção (update_range nasceu com updated_at no 1º
       GREEN); mutação "não gravar updated_at" aplicada à mão: 1 failed;
       revertida

02:38  🟢 GREEN  test_recorded_range_is_read_back_with_its_status_and_update_time  ·  15 passed

02:39  ♻️ REFACTOR  trim_sermon ao lado de show_sermon; _existing compartilhado
       por show e trim; ruff format  ·  219 passed (core)

02:39  ✅ PASSO 1/4 — Regras no serviço  ·  +23 testes  ·  suíte 219 (core)

--- Passo 2: `sermon trim` na CLI ---

02:39  🔴 RED    test_trim_with_json_answers_the_trimmed_sermon_as_show_does
       sermon trim <id> --start 1:02:10 --end 1:48:30 --json numa live de
       2 h → saída 0, JSON igual ao de show (trimmed, 3730, 6510, 2780)
       Cenário 1; FR-001, FR-006; L11; matriz 2(a)
       AssertionError: 2 != 0 (invalid choice: 'trim')

02:39  🟢 GREEN  test_trim_with_json_answers_the_trimmed_sermon_as_show_does  ·  1 passed

02:39  🔴 RED    test_trimming_a_processed_sermon_warns_on_stderr_even_when_quiet_and_keeps_stdout_json
       processed → aviso com `sermon process --force` no stderr, também com
       --quiet; stdout continua JSON com status processed
       Cenário 4; FR-005; matriz 2(e)
       AssertionError: '' != 'aviso: A pregação já foi processada; …'

02:40  🟢 GREEN  test_trimming_a_processed_sermon_warns_on_stderr_even_when_quiet_and_keeps_stdout_json  ·  3 passed

02:40  🔴 RED    test_trimming_a_sermon_not_yet_processed_warns_nothing
       sem processed, stderr vazio (o aviso é só para processed)
       FR-005; mutação exigida "aviso sempre/nunca"
       passou sem produção; guarda do lado negativo do aviso

02:40  🔴 RED    test_borders_are_accepted_as_hours_minutes_or_seconds
       HH:MM:SS[.mmm], MM:SS[.mmm] e segundos aceitos
       Casos de borda (spec); docs/cli.md §2; matriz 2(b)
       passou sem produção (parse_timestamp já aceitava os três)

02:40  🔴 RED    test_border_in_an_unknown_format_is_an_invalid_argument_naming_the_option
       abc, inf, 1:-5 → invalid_argument, saída 2, details.argument
       Casos de borda (spec); L4; matriz 2(c)
       inf: details {'start':…, 'end': inf} (chegou ao serviço); 1:-5:
       KeyError 'error' (virou 55 s e foi aceito); 2 failed

02:40  🔴 RED    test_parse_timestamp_rejects_values_outside_the_clock
       nan, inf, negativos, minutos/segundos ≥ 60 depois do 1º componente,
       1e3 e 1_0 → ValueError
       L4 (orquestrador); test_timefmt.py
       9 failed (nan, inf, 1:-5, 0:60, 0:99, 1:60:00, 1e3, 1_0, ١٠ aceitos)

02:40  🟢 GREEN  test_parse_timestamp_rejects_values_outside_the_clock  ·  33 passed
       (timefmt + trim CLI; os dois RED de formato da CLI ficaram verdes)

02:41  ♻️ REFACTOR  parse_timestamp por regex ASCII com constantes de
       unidade; test_sermon_command.py: ajuda do grupo agora lista
       {create,list,show,trim} e o exemplo de trim entra no parametrize
       (mudança de comportamento esperada, não regressão)  ·  suíte 298

02:41  🔴 RED    test_trim_without_both_borders_is_an_invalid_argument_naming_the_missing_one
       --start ou --end ausente → invalid_argument com details.argument
       matriz 2(d)
       passou sem produção (required=True + contrato do argparse)

02:41  🔴 RED    test_refused_trim_exits_with_the_contract_code_and_leaves_the_sermon_as_it_was
       not_found 3, sermon_too_short 5, busy 4, borda fora da live 2;
       show antes == show depois
       Cenários 3; casos de borda; matriz 2(f)
       passou sem produção (erros do serviço já seguem o contrato)

02:41  🔴 RED    test_trim_without_json_describes_the_sermon_as_show_does
       texto sem --json = render do show, estado "delimitada" e bordas
       L10; matriz 2(g)
       passou sem produção (render=_render_shown desde o 1º GREEN)

02:41  🟢 GREEN  3 guardas acima  ·  17 passed

02:41  ♻️ REFACTOR  parametrize dos erros enxugado (alvo + fim); ruff, mypy
       limpos  ·  suíte 305

02:41  ✅ PASSO 2/4 — `sermon trim` na CLI  ·  +32 testes (17 CLI, 14 timefmt, 1 ajuda)  ·  suíte 305

--- Passo 3: `create` com bordas ---

02:42  🔴 RED    test_sermon_created_with_borders_is_already_trimmed
       create com start/end grava as bordas e deixa a pregação trimmed
       Cenário 2; FR-004; matriz 3(a)
       TypeError: create_sermon() got an unexpected keyword argument 'start'

02:42  🟢 GREEN  test_sermon_created_with_borders_is_already_trimmed  ·  234 passed (core)

02:42  🔴 RED    test_answer_of_a_create_with_borders_has_the_trimmed_status
       a resposta do create com bordas já traz status trimmed
       Cenário 2; matriz 3(a)
       AssertionError: assert 'created' == 'trimmed'

02:43  🟢 GREEN  test_answer_of_a_create_with_borders_has_the_trimmed_status  ·  235 passed (core)

02:43  ♻️ REFACTOR  _record_range (busy → ms → limites → mínimo → gravar)
       compartilhado por trim e create; _shown(row); dígitos árabes do
       teste de timefmt escapados (RUF001)

02:43  🔴 RED    test_create_with_refused_borders_fails_and_creates_no_sermon
       create com faixa curta, invertida ou fora da live falha com o erro
       do trim e não deixa pregação no banco
       L2; matriz 3(c); mutação exigida "tirar a validação antes do insert"
       AssertionError: {'items': [{… 'status': 'created' …}]} != {'items': []}

02:43  🟢 GREEN  test_create_with_refused_borders_fails_and_creates_no_sermon  ·  238 passed (core)

02:43  🔴 RED    test_create_with_borders_of_a_known_video_trims_the_existing_sermon
       vídeo já existente + bordas → trim na existente, created false
       L3; matriz 3(d)
       AssertionError: (1, False, 'created', None) != (1, False, 'trimmed', 3730.0)

02:44  🟢 GREEN  test_create_with_borders_of_a_known_video_trims_the_existing_sermon  ·  239 passed (core)

02:43  🔴 RED    test_create_with_borders_of_a_processed_sermon_keeps_it_and_asks_for_a_reprocess
       create com bordas numa existente processed: estado mantido,
       needs_reprocess true (para o aviso da CLI)
       L3 ("mesmas regras e aviso"); FR-005
       KeyError: 'needs_reprocess'

02:43  🔴 RED    test_create_with_a_single_border_is_refused_before_anything_is_created
       só start ou só end → invalid_argument com details.argument, nada criado
       Casos de borda (spec); Decisões técnicas; matriz 3(b)
       Failed: DID NOT RAISE WordcutError (2 casos)

02:44  🟢 GREEN  os 2 RED acima  ·  242 passed (core)

02:44  🔴 RED    test_create_with_borders_answers_a_new_trimmed_sermon
       sermon create <link> --start … --end … --json → saída 0, created
       true, trimmed, bordas no show, sem needs_reprocess no JSON
       Cenário 2; FR-004; L11; matriz 3(a)
       KeyError: 'id' (unrecognized arguments: --start)

02:44  🟢 GREEN  test_create_with_borders_answers_a_new_trimmed_sermon  ·  72 passed (cli)

02:44  🔴 RED    test_create_with_a_single_border_names_the_missing_one_and_creates_nothing
       create só com --start (ou --end) → invalid_argument com
       details.argument = a opção que falta, sermon list vazio
       Casos de borda (spec); matriz 3(b)
       AssertionError: {'argument': 'end'} != {'argument': '--end'}

02:45  🟢 GREEN  test_create_with_a_single_border_names_the_missing_one_and_creates_nothing  ·  74 passed (cli)

02:45  🔴 RED    test_create_with_refused_borders_exits_with_the_trim_error_and_creates_nothing
       create com faixa curta (5) ou fora da live (2) → erro do trim e
       sermon list vazio
       L2; matriz 3(c)
       passou sem produção (regra no core, GREEN de 02:43)

02:45  🔴 RED    test_create_with_borders_of_a_processed_sermon_warns_and_answers_the_existing_one
       create com bordas de vídeo já processed → created false, processed,
       aviso de reprocessar no stderr
       L3; FR-005
       passou sem produção (_warn_if_reprocess_needed já no create)

02:45  🟢 GREEN  2 guardas acima  ·  23 passed (trim CLI)

02:46  ♻️ REFACTOR  Borders = tuple[float, float]; _requested_borders troca as
       checagens repetidas de start/end; ruff, mypy limpos  ·  suíte 320

02:46  🧬 MUTAÇÕES  as 7 exigidas pela barra, aplicadas e revertidas, suíte
       core + cli:
       MIN `<`→`<=`: 4 failed · end `<=`→`<`: 2 failed ·
       start `<`→`<=`: 1 failed · processed vira trimmed: 5 failed ·
       needs_reprocess sempre false: 5 failed · aviso removido: 3 failed ·
       sem bloqueio de processing: 3 failed · sem validação antes do
       insert: 5 failed (refeita após o refactor: 5 failed)

02:46  ✅ PASSO 3/4 — `create` com bordas  ·  +15 testes  ·  suíte 320

--- Passo 4: Documentação ---

02:47  📝 DOCS   CHANGELOG [Não lançado]: Adicionado (sermon trim, --start/--end no
       create, duração em list/show) e Alterado (parser de T estrito);
       docs/cli.md §7.1 (create com bordas: par, nada criado se recusar,
       vídeo existente) e §7.3 (limites e live sem duração). Sem TDD.

02:47  ✅ PASSO 4/4 — Documentação  ·  +0 testes  ·  suíte 320

02:47  🏁 VERIFICAÇÃO  uv run pytest -q: 320 passed · ruff check: limpo ·
       ruff format --check: limpo · mypy: sem erros (44 arquivos)

## Rodada 1 · QA

02:48  📊 SUÍTE  uv run pytest -q: 320 passed  ·  0 failed
       escopo (trim, timefmt, sermons, cli contract): 145 passed;
       ruff check, ruff format --check, mypy (44 arquivos): limpos

02:49  🔎 QA     passo 1/4 — Regras no serviço  ·  ✅ PASS
       1(a)–1(i) cobertos com SQLite real, relendo por show_sermon;
       L1, L5–L9 com teste

02:50  🔎 QA     passo 2/4 — `sermon trim` na CLI  ·  ✅ PASS
       2(a)–2(g) via main([...]); trim --json == show --json (L11),
       aviso também com --quiet; L4 com inf e 1:-5 na CLI

02:50  🔎 QA     passo 3/4 — `create` com bordas  ·  ✅ PASS
       valida antes do insert (L2, primeira opção da barra); dois
       commits não violam L2; L3 testado, inclusive em processed

02:51  🔎 QA     passo 4/4 — Documentação  ·  ✅ PASS
       CHANGELOG Adicionado + Alterado (parser); docs/cli.md §7.1/§7.3
       só registram L2, L3 e L5, que mudam o contrato

02:52  🧬 MUTAÇÕES · cópia da working tree no scratchpad  ·  18 de 18 mortas
       ☠️  MIN `<` → `<=`                                 4 testes
       ☠️  end `<=` live_duration → `<`                    2 testes
       ☠️  start `<` end → `<=`                            1 teste
       ☠️  `0 <= start` → `0 < start`                      2 testes
       ☠️  processed vira trimmed                          5 testes
       ☠️  needs_reprocess do trim sempre false            3 testes
       ☠️  sem bloqueio de processing                      3 testes
       ☠️  sem validação antes do insert (L2)              5 testes
       ☠️  sem arredondar na entrada (L8)                  2 testes
       ☠️  duration fixo em None (L1)                      3 testes
       ☠️  create de vídeo existente ignora bordas (L3)    3 testes
       ☠️  serviço aceita borda única                      2 testes
       ☠️  update_range mantém updated_at (L9)             1 teste
       ☠️  parser sem limite de minutos < 60 (L4)          1 teste
       ☠️  aviso de reprocessar removido                   3 testes
       ☠️  CLI vaza needs_reprocess (L11)                  2 testes
       ☠️  CLI sem _require_both_borders                   2 testes
       ☠️  trim renderiza como create (L10)                1 teste

02:53  🔎 QA     comentários (CONTRIBUTING.md §5)  ·  ✅ PASS
       todos classificáveis: referência, intenção, formato, contrato

02:53  🔎 QA     fato 2 do implementador: parser estrito vale para legacy
       L4 decide sobre parse_timestamp, não sobre o comando; legacy.py
       (live, overview, cut) usa a mesma função; test_legacy_commands
       verde; CHANGELOG › Alterado registra. Não contradiz a barra
