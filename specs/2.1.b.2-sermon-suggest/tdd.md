## Plano de QA

baseline_commit 470a85696cd41a5bb662dabb9aa9cc3b09c5f94f

07:52  📐 BARRA   passo 1: só os sugeridos não editados são trocados
       suggest() com ScriptedModel no core; os cortes conferidos por ID
       e por campo, não por contagem

07:52  🧬 EXIGE   tirar o filtro edited = 0 do delete  ·  vermelha
       prova que o corte editado sobrevive à nova sugestão

07:52  🧬 EXIGE   tirar o filtro sermon_id do delete  ·  vermelha
       prova que a sugestão não apaga cortes de outra pregação

07:52  🧬 EXIGE   apagar antes de chamar o LLM  ·  vermelha
       prova o "só no sucesso": falha deixa os cortes antigos

07:52  📐 BARRA   passo 2: suggest sem trava global, por pregação
       start_suggestion com lock_owner; tipo resolvido num
       interpretador novo, como faz o runner destacado

07:52  🧬 EXIGE   tirar suggest de BUILTIN_KIND_MODULES  ·  vermelha
       sem isso, a tarefa destacada morre com internal_error

07:52  🧬 EXIGE   tirar o reconcile da exclusão  ·  vermelha
       uma tarefa órfã bloquearia a pregação para sempre

07:52  📐 BARRA   passo 3: contrato da CLI e códigos de saída
       main([...]) com capsys; sem --wait só com harmless_tasks

07:52  ⚠️ LACUNA  o dublê não alcança o processo destacado
       detached_tasks com chave chamaria o OpenRouter; o plano não
       avisa; teste assim é FAIL imediato do passo

07:52  ⚠️ LACUNA  o resultado "igual ao do process" não existe
       o process devolve suggestion_warnings, não suggested_cuts e
       discarded; sem decisão, o passo 2 fica PARCIAL

07:52  ⚠️ LACUNA  llm_not_configured grava suggestion_error
       contraria "nada muda"; a barra exige pré-condição sem tarefa

07:52  ⚠️ LACUNA  exclusão por pregação tem corrida
       admit roda sem trava e _create em outra conexão; a barra só
       cobra o caso sequencial, e o risco precisa ficar escrito

07:52  ⚠️ LACUNA  resposta válida sem corte aproveitável
       saved = 0 apaga os sugeridos sem pôr outros; a barra trata
       como sucesso e exige teste que fixe isso

07:52  ⚠️ LACUNA  process --force no meio de uma suggest
       os IDs de palavra ficam em JSON sem FK; o plano não decide;
       fica fora da barra

## Rodada 1 · implementador

07:57  🔴 RED    test_deleting_the_unedited_suggestions_keeps_edited_chos…
       só os sugeridos não editados da pregação saem; editado,
       escolhido, descartado e outra pregação ficam iguais
       passo 1 (FR-003); matriz 1(a), 1(c)
       AttributeError: module 'wordcut.db.cuts' has no attribute
       'delete_unedited_suggestions'

07:58  🟢 GREEN  test_deleting_the_unedited_suggestions_keeps_edited_chos…  ·  9 passed

07:58  🔴 RED    test_a_replacing_suggestion_swaps_the_unedited_suggestio…
       com replace_suggested, o sugerido não editado dá lugar ao novo
       (suggested, llm, preset usado); os outros ficam iguais por ID e
       campo; suggestion_error limpo; o resultado traz o ID novo
       passo 1 (FR-003, L1, L2, L6); matriz 1(a)
       TypeError: suggest() got an unexpected keyword argument
       'replace_suggested'

07:58  🟢 GREEN  test_a_replacing_suggestion_swaps_the_unedited_suggestio…  ·  25 passed

07:59  🔴 RED    test_a_failed_replacing_suggestion_leaves_every_cut_as_i…
       duas respostas fora do esquema, erro de transporte e LLM não
       configurado: nenhum corte muda, o erro fica na pregação
       passo 1 (FR-003, L6); matriz 1(b)
       verde de saída: o GREEN anterior já apaga depois da resposta;
       RED provado pela mutação "apagar antes de chamar o LLM":
       3 failed, 16 passed

07:59  🟢 GREEN  test_a_failed_replacing_suggestion_leaves_every_cut_as_i…  ·  19 passed
       mutações do repositório (edited = 0, status, sermon_id) todas
       vermelhas

07:59  🔴 RED    test_a_replacing_suggestion_keeps_the_suggestions_of_ano…
       a substituição não toca nos sugeridos de outra pregação
       passo 1 (FR-003); matriz 1(c)
       verde de saída; RED pela mutação "tirar o filtro sermon_id":
       1 failed, 19 passed

07:59  🟢 GREEN  test_a_replacing_suggestion_keeps_the_suggestions_of_ano…  ·  20 passed

07:59  🔴 RED    test_a_valid_answer_without_cuts_to_keep_still_replaces_…
       resposta válida sem corte aproveitável é sucesso: o sugerido
       não editado sai, cut_ids vazio, aviso presente, sem erro
       passo 1, decisão L7
       verde de saída; RED pela mutação "só apagar com cortes novos":
       1 failed, 20 passed

07:59  🟢 GREEN  test_a_valid_answer_without_cuts_to_keep_still_replaces_…  ·  21 passed

08:00  🔴 RED    test_a_replacing_suggestion_saves_nothing_when_the_sermo…
       reprocessada (outro processed_at) ou processando durante a
       chamada ao LLM: sermon_not_processed, cortes e
       suggestion_error iguais
       passo 1, decisão L9
       Failed: DID NOT RAISE WordcutError (x2)

08:01  🟢 GREEN  test_a_replacing_suggestion_saves_nothing_when_the_sermo…  ·  566 passed
       refactor: processed_row em service.sermons, reaproveitado por
       sermon_video

08:01  ✅ PASSO 1/4 — Substituição no core  ·  +9 testes  ·  suíte 834 passed

08:01  🔴 RED    test_a_suggestion_in_the_foreground_replaces_the_suggest…
       start_suggestion em primeiro plano: tarefa suggest succeeded,
       resultado {sermon_id, preset_id, suggested_cuts,
       suggestion_warnings}, prompt do preset padrão
       passo 2 (FR-001, FR-002, L1, L2); matriz 2(d), 2(g)
       ModuleNotFoundError: No module named 'wordcut.service.suggestion'

08:02  🟢 GREEN  test_a_suggestion_in_the_foreground_replaces_the_suggest…  ·  1 passed

08:02  🔴 RED    test_a_suggestion_with_a_preset_asks_with_its_prompt_and…
       com --preset p, o system é o de show_preset(p) e os cortes
       novos levam preset_id p
       passo 2 (FR-002); matriz 2(d)
       verde de saída (o GREEN anterior já resolve o preset); RED pela
       mutação "ignorar preset_id": 1 failed, 1 passed

08:02  🟢 GREEN  test_a_suggestion_with_a_preset_asks_with_its_prompt_and…  ·  2 passed

08:02  🔴 RED    test_suggest_is_a_kind_without_the_lock_that_a_new_inter…
       um interpretador novo, como o runner destacado, acha o tipo
       suggest com needs_lock=False
       passo 2 (FR-001, L5); matriz 2(a)
       verde de saída (registro feito no tracer); RED pelas mutações
       "tirar de BUILTIN_KIND_MODULES" e "needs_lock=True": 1 failed

08:02  🟢 GREEN  test_suggest_is_a_kind_without_the_lock_that_a_new_inter…  ·  3 passed

08:03  🔴 RED    test_a_suggestion_runs_while_another_process_holds_the_p…
       com a trava presa por outro processo, a suggest termina
       succeeded e o dono da trava continua o mesmo
       passo 2 (FR-001); matriz 2(b)
       verde de saída (needs_lock=False do tracer); RED pela mutação
       "needs_lock=True": 2 failed

08:03  🟢 GREEN  test_a_suggestion_runs_while_another_process_holds_the_p…  ·  4 passed

08:03  🔴 RED    test_a_sermon_{that_does_not_exist,not_processed}_is_ref…
       pregação inexistente (not_found) e não processed (created,
       trimmed, processing, failed → sermon_not_processed com status)
       recusadas antes de criar tarefa; preset inexistente (not_found,
       details.preset_id) já verde
       passo 2; matriz 2(c)
       AssertionError: At index 2 diff: [TaskRow(... status='failed',
       error_code='sermon_not_processed' ...)] != [] (5 failed)

08:03  🟢 GREEN  test_a_sermon_{that_does_not_exist,not_processed}_is_ref…  ·  10 passed

08:03  🔴 RED    test_without_the_llm_configured_nothing_changes_and_no_t…
       sem modelo ou sem chave: llm_not_configured com
       details.missing, sem tarefa, pregação (suggestion_error
       incluído) igual
       passo 2, decisão L3; critério "nada muda"
       AssertionError: ... [TaskRow(... error_code='llm_not_configured'
       ...)] (2 failed)

08:03  🟢 GREEN  test_without_the_llm_configured_nothing_changes_and_no_t…  ·  35 passed
       refactor: require_configured público em wordcut.suggestion;
       _configured_model passa a usá-lo

08:04  🔴 RED    test_a_second_suggestion_of_a_sermon_while_one_runs_is_b…
       com uma suggest running da mesma pregação, a segunda é busy
       com task_id, kind e started_at dela, sem tarefa nova
       passo 2, decisão L8; matriz 2(e); critério "duas simultâneas"
       At index 0 diff: ('internal_error', None) != ('busy', {...})

08:04  🟢 GREEN  test_a_second_suggestion_of_a_sermon_while_one_runs_is_b…  ·  13 passed

08:04  🔴 RED    test_a_suggestion_{running_for_another_sermon,finished,w…
       não bloqueiam: suggest running de outra pregação, suggest
       terminada e suggest órfã (PID morto, reconciliada)
       passo 2; matriz 2(e)
       verde de saída; RED pelas mutações "tirar o reconcile" (órfã)
       e "tirar o filtro de recurso" (outra pregação): 1 failed cada

08:04  🟢 GREEN  test_a_suggestion_{running_for_another_sermon,finished,w…  ·  16 passed

08:04  🔴 RED    test_the_suggestion_reports_its_stage
       a tarefa informa a etapa sugerindo
       passo 2, decisão L10
       AssertionError: assert [] == [('suggest', 'sugerindo')]

08:04  🟢 GREEN  test_the_suggestion_reports_its_stage  ·  17 passed

08:05  🔴 RED    test_an_llm_failure_fails_the_task_with_llm_error_and_le…
       duas respostas fora do esquema: tarefa failed com llm_error,
       wait_task levanta llm_error (saída 6), cortes iguais,
       suggestion_error llm_error
       passo 2 (L6); matriz 2(f); borda "LLM falha duas vezes"
       verde de saída; RED pela mutação "engolir o erro na tarefa":
       1 failed

08:05  🟢 GREEN  test_an_llm_failure_fails_the_task_with_llm_error_and_le…  ·  18 passed

08:05  🔴 RED    test_a_preset_deleted_before_the_task_runs_fails_it_as_n…
       params guardam o preset resolvido; apagado entre o lançamento
       e a execução (runner via execution.resume), a tarefa termina
       failed com not_found e details.preset_id
       passo 2, decisão L11
       verde de saída; RED pela mutação "usar o padrão na tarefa":
       1 failed

08:05  🟢 GREEN  test_a_preset_deleted_before_the_task_runs_fails_it_as_n…  ·  19 passed

08:06  🔴 RED    test_a_sermon_reprocessed_during_the_suggestion_fails_th…
       reprocessada durante a chamada ao LLM: tarefa failed com
       sermon_not_processed, cortes e suggestion_error iguais
       passo 2, decisão L9
       verde de saída (passo 1); RED pela mutação "tirar a conferência
       de processed_at": 3 failed (core e tarefa)

08:06  🟢 GREEN  test_a_sermon_reprocessed_during_the_suggestion_fails_th…  ·  20 passed
       refactor: busy por pregação com next(); ruff e mypy limpos

08:06  ✅ PASSO 2/4 — Tipo de tarefa e serviço  ·  +20 testes  ·  suíte 854 passed

08:07  🔴 RED    test_suggest_with_a_preset_and_wait_replaces_the_unedite…
       sermon suggest <id> --preset p --wait --json: saída 0, um JSON
       com o resultado, prompt de p, sugerido não editado trocado,
       outros iguais em sermon show, progresso [suggest] no stderr
       passo 3; matriz 3(a); cenário "nova sugestão com outro preset"
       IndexError: list index out of range (comando inexistente, sem
       chamada ao LLM)

08:08  🟢 GREEN  test_suggest_with_a_preset_and_wait_replaces_the_unedite…  ·  1 passed
       mutações "wait=False" e "sem repasse de --preset": vermelhas

08:08  ⚠️ INCIDENTE  a mutação "wait=False", rodada antes da guarda,
       lançou o runner destacado real com a chave fictícia sentinela;
       ele chamou o OpenRouter e recebeu HTTP 401 (tarefa failed
       llm_error). Nenhum processo ficou vivo. Correção: fixture
       autouse no_real_task_process (harmless_tasks) nos dois módulos
       novos; a mesma mutação, refeita, deixa a tarefa running inofensiva

08:08  🔴 RED    test_quiet_…, test_suggest_without_wait_…,
       test_suggest_runs_while_another_process_holds_the_…
       --quiet cala o progresso; sem --wait, {task_id, kind suggest,
       running, sermon_id}; com a trava presa, saída 0
       passo 3; matriz 3(a), 3(b), 3(d)
       verdes de saída (contrato herdado de tasks_support e do passo 2)

08:08  🟢 GREEN  test_quiet_…, test_suggest_without_wait_…, …lock  ·  4 passed

08:09  🔴 RED    test_a_refused_suggestion_exits_…, …llm_configured_…,
       …llm_failure_exits_6_…, …second_suggestion_…_exits_4_busy_…
       saídas do contrato: not_found 3 (pregação, preset),
       sermon_not_processed 5, llm_not_configured 5 (nada muda),
       llm_error 6 (cortes iguais, tarefa failed), busy 4 (task_id, sem
       tarefa nova); nenhuma recusa cria tarefa
       passo 3; matriz 3(c); bordas do spec
       primeira rodada vermelha por erro do arranjo (status trimmed no
       caso do preset); arranjo corrigido, sem mudança de produção

08:09  🟢 GREEN  test_a_refused_suggestion_exits_… e demais  ·  10 passed

08:09  🔴 RED    test_suggest_without_json_tells_the_new_cuts_and_the_lau…
       sem --json: "1 corte sugerido para a pregação X com o preset
       P.", um corte por linha, e "Tarefa N iniciada: sugestão de
       cortes…" para a lançada
       passo 3, decisão L10; matriz 3(f)
       At index 0 diff: ['1 cortes sugeridos …'] != ['1 corte sugerido …']

08:09  🟢 GREEN  test_suggest_without_json_tells_the_new_cuts_and_the_lau…  ·  12 passed

08:12  🔴 RED    test_no_output_of_suggest_carries_the_llm_key
       sucesso, llm_error (modelo real em transporte falso que ecoa a
       chave), llm_not_configured, lançada e busy, com e sem --json:
       saídas esperadas e a chave sentinela ausente
       passo 3; matriz 3(g)
       verde de saída (o contrato já não repete a chave)

08:12  🟢 GREEN  test_no_output_of_suggest_carries_the_llm_key  ·  17 passed
       test_sermon_command: ajuda do grupo e exemplo por ação passam a
       listar suggest (mudança intencional do contrato)

08:12  ✅ PASSO 3/4 — CLI  ·  +17 testes (+1 parâmetro em teste existente)  ·  suíte 872 passed 

08:14  📝 DOCS   CHANGELOG [Não lançado]: sermon suggest; docs/cli.md §5.3
       (busy por pregação, details task_id/kind/started_at) e §7.6
       (recusas, corrida aceita, preset resolvido, suggestion_error,
       resposta sem corte aproveitável, reprocessamento no meio,
       etapa sugerindo, formato do resultado); docs/architecture
       (tabela de módulos). Sem ADR nova (decisão L8)

08:14  ✅ PASSO 4/4 — Documentação  ·  +0 testes  ·  suíte 872 passed
       ruff check, ruff format --check e mypy limpos; nenhum processo
       de teste vivo

## Rodada 1 · QA

08:15  📊 SUÍTE  872 passed  ·  0 failed
       core 586, cli 285; ruff check, ruff format --check e mypy limpos

08:16  🔎 QA     guarda global contra rede (decisão do orquestrador)
       conftest.py da raiz sem variável herdável; default_model e
       default_gateways sem recusa; só no_real_task_process nos dois
       módulos novos

08:18  🧬 MUTAÇÕES · cópia no scratchpad, URL do OpenRouter neutralizada
       e só módulos com harmless_tasks ou sem processo destacado  ·
       18 de 18 mortas
       ☠️  tirar edited = 0 / status / sermon_id do delete      1 teste cada
       ☠️  apagar antes do LLM                                  1 teste
       ☠️  L7 só apagar com cortes novos                        1 teste
       ☠️  L9 tirar a conferência de processed_at               1 teste
       ☠️  tirar suggest de BUILTIN_KIND_MODULES                1 teste
       ☠️  needs_lock=True                                      1 teste
       ☠️  ignorar preset_id / L11 tarefa usa o padrão          1 teste cada
       ☠️  tirar reconcile / filtro de recurso / a exclusão     1 teste cada
       ☠️  L3 tirar require_configured do lançamento            1 teste
       ☠️  L10 tirar a etapa sugerindo                          1 teste
       ☠️  wait=False / sem repasse de --preset / plural fixo   1 teste cada

08:19  🔎 QA     passo 1/4 — Substituição no core  ·  ✅ PASS
       filtros, ordem e transação provados por ID e campo

08:19  🔎 QA     passo 2/4 — Tipo de tarefa e serviço  ·  ⚠️ PARCIAL
       comportamento e mutações completos; falta a guarda global
       contra rede exigida pelo orquestrador (itens 1, 2 e 3)

08:19  🔎 QA     passo 3/4 — CLI  ·  ✅ PASS
       códigos de saída, --quiet, legível, sem chave, lock_owner

08:19  🔎 QA     passo 4/4 — Documentação  ·  ✅ PASS
       CHANGELOG, §5.3, §7.6 e tabela de módulos batem com o código

## Rodada 2 · implementador

08:55  🔁 REABRE passo 2 (QA rodada 1: PARCIAL) — guarda global contra
       rede: variável herdável no conftest.py da raiz, default_model e
       default_gateways recusam, runner destacado real sem rede
       toda rodada de teste desta volta roda em `unshare -rn` (sem
       interface de rede): nenhuma requisição sai da máquina

08:55  🔴 RED    test_a_real_detached_suggestion_meets_the_network_guard_…
       um runner destacado real (detached_tasks, sem harmless_tasks),
       com chave e modelo fictícios, termina failed com o erro da
       guarda (network_error, details.forbidden_by) e o processo sai
       passo 2; decisão do orquestrador, itens 1–3
       a autouse no_real_task_process saiu do módulo: trocava o Popen
       e escondia o runner real; os testes destacados já pedem
       harmless_tasks
       AssertionError: ('llm_error', None, 0) == ('network_error', …)
       (o runner chamou o OpenRouter de verdade; a falta de rede do
       namespace deu llm_error)

08:56  🟢 GREEN  test_a_real_detached_suggestion_meets_the_network_guard_…  ·  21 passed
       wordcut.network.refuse_when_forbidden (network_error,
       details.forbidden_by); default_model e default_gateways a chamam
       antes de montar o mundo real; conftest.py da raiz: autouse
       no_network com monkeypatch.setenv(WORDCUT_FORBID_NETWORK, "1")
       código existente (network_error, saída 6): sem código novo

08:57  🔴 RED    test_the_real_outside_world_refuses_to_be_built_…[processing]
       num interpretador novo, que herda o ambiente da suíte e não os
       dublês, default_gateways e default_model recusam com
       network_error
       passo 2; decisão do orquestrador, item 2 (as duas fábricas)
       guarda de default_gateways retirada para o RED; [suggestion]
       já verde pelo ciclo anterior
       AssertionError: assert None == ['network_error', {…}]

08:57  🟢 GREEN  test_the_real_outside_world_refuses_to_be_built_…  ·  2 passed

08:58  ♻️  REFACTOR  no_real_task_process saiu também de
       test_sermon_suggest_command.py; os quatro testes que lançam sem
       --wait pedem harmless_tasks (a tarefa precisa ficar running).
       Auditoria temporária do runner (desfeita) na suíte inteira: só
       o teste novo lança um runner real de tipo com rede; os demais
       são diagnostic. "# Fictitious: no test ever reaches OpenRouter."
       dos dois módulos novos passa a dizer só o que a guarda garante
       ·  38 passed

08:59  🧬 MUTAÇÃO  cópia no scratchpad, OPENROUTER_URL → 127.0.0.1:9,
       PYTHONPATH da cópia herdado pelo runner, tudo em unshare -rn
       ☠️  default_model sem refuse_when_forbidden    runner real
           vermelho: ('llm_error', None, 0) != ('network_error', …);
           [suggestion] da fábrica também
       ☠️  conftest.py sem o setenv                   runner real e as
           duas fábricas vermelhos
       nenhum processo wordcut.tasks.runner vivo depois

09:01  📝 DOCS   ADR-0017 "Testes sem rede real" e índice; decisão na
       tabela do plan.md (e linha no Contexto de código);
       CONTRIBUTING §3, README (Desenvolvimento), docs/architecture
       (linha da sugestão), docs/cli.md §5.3 (network_error também é
       a rede proibida, details.forbidden_by) e CHANGELOG. Sem código
       de erro novo: errors.py e test_errors.py intactos

09:01  ✅ PASSO 2/4 — Tipo de tarefa e serviço (reaberto)  ·  +3 testes  ·  suíte 875
       unshare -rn: 871 passed, 4 skipped (só o root do namespace
       pula os de pasta somente leitura; os 59 dos dois módulos
       passam fora dele); ruff check, ruff format --check e mypy
       limpos; nenhum processo wordcut.tasks.runner vivo

## Rodada 2 · QA

09:02  📊 SUÍTE  875 passed  ·  0 failed
       ruff check, ruff format --check e mypy limpos

09:03  📊 SUÍTE  871 passed  ·  0 failed  ·  unshare -rn (só lo)
       4 skipped: root do namespace escreve em pasta somente
       leitura, sem relação com rede

09:05  🧬 MUTAÇÕES · guarda contra rede, cópia no scratchpad,
       OPENROUTER_URL → 127.0.0.1:9, PYTHONPATH da cópia, unshare -rn
       ·  6 de 6 mortas
       ☠️  default_model sem refuse_when_forbidden    fábrica e runner
           runner real: ('llm_error', None, 0) != network_error
       ☠️  default_gateways sem refuse_when_forbidden fábrica
       ☠️  conftest.py sem o setenv                   fábrica (1ª)
       ☠️  refuse_when_forbidden nunca recusa         fábrica (1ª)
       ☠️  execution.Popen sem a variável no env      runner real
       ☠️  guarda com código llm_error                fábrica (1ª)
       nenhum processo wordcut.tasks.runner vivo depois

09:06  🔎 QA     passo 2/4 — Tipo de tarefa e serviço  ·  ✅ PASS
       autouse no_network na raiz, as duas fábricas recusam, runner
       real termina failed com network_error e sai; autouse locais
       fora; ADR-0017, plan.md e CONTRIBUTING §3

09:06  🔎 QA     passos 1, 3 e 4  ·  ✅ PASS
       sem regressão; §5.3 e CHANGELOG citam a guarda
