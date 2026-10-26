## Plano de QA

baseline_commit: 2956c4c758f3a2dffc0209f07cdc41aeb40546f9

07:04  📐 BARRA   nenhum teste toca o OpenRouter de verdade
       fixture autouse que recusa o modelo real (como no_real_processing);
       OpenRouterModel só com httpx.MockTransport

07:04  📐 BARRA   a chave nunca sai: erro, details, log, resultado, show, CLI
       chave sentinela fictícia procurada em str/to_dict, linha tasks,
       caplog DEBUG, stdout/stderr; e o header Bearer chega ao transport

07:05  📐 BARRA   tabela cuts com a entidade da spec e contagens reais
       SQLite real em tmp_path; cortes em três estados contados no list

07:05  📐 BARRA   entrada = build_prompt(preset) + frases numeradas sem tempo
       system comparado com build_prompt(), não string copiada; nenhum
       start/end no texto do usuário

07:05  📐 BARRA   esquema validado; uma nova tentativa; depois llm_error
       dublê de SuggestionModel com respostas roteirizadas e contagem

07:06  📐 BARRA   trechos e faixa saem das frases certas
       pregação cujos IDs de frase não começam em 1; caso com quebra de
       sequência e caso reordenado

07:06  📐 BARRA   falha da sugestão não desfaz o processamento (FR-005)
       process com FakeGateways + dublê: tarefa succeeded, pregação
       processed, suggestion_error no show e no resultado

07:06  🧬 EXIGE   sem nova tentativa (uma chamada só)  ·  vermelha
       prova o cenário "inválida, depois válida"

07:06  🧬 EXIGE   duas novas tentativas (três chamadas)  ·  vermelha
       prova "duas chamadas no total" e §III

07:06  🧬 EXIGE   checagem de frase inexistente removida  ·  vermelha
       prova a borda "frase citada que não existe"

07:07  🧬 EXIGE   frase repetida no corte aceita  ·  vermelha
       prova a validação do esquema do plano

07:07  🧬 EXIGE   fator 0,82 trocado por 1,0  ·  vermelha
       corte bruto acima do máximo e estimado dentro tem de ficar

07:07  🧬 EXIGE   descarte por duração removido  ·  vermelha
       prova "descartado com aviso; os outros ficam"

07:07  🧬 EXIGE   limite máximo com > trocado por >=  ·  vermelha
       duração estimada igual ao máximo é aceita

07:07  🧬 EXIGE   todas as frases num trecho só  ·  vermelha
       quebra de sequência abre trecho novo

07:08  🧬 EXIGE   faixa pela ordem da resposta, não da pregação  ·  vermelha
       caso reordenado [9, 10, 3]

07:08  🧬 EXIGE   preset_id não gravado / status diferente de suggested
       vermelha; prova 2.1.b.3 e FR-004

07:08  🧬 EXIGE   tempos incluídos nas linhas do usuário  ·  vermelha
       prova FR-002 (sem tempos)

07:08  🧬 EXIGE   Authorization omitido do POST  ·  vermelha
       prova FR-006 (chave configurada usada)

07:08  🧬 EXIGE   corpo da resposta HTTP na mensagem de erro  ·  vermelha
       resposta 401 que ecoa a chave sentinela

07:09  🧬 EXIGE   process sem capturar o erro da sugestão  ·  vermelha
       pregação tem de ficar processed

07:09  🧬 EXIGE   chamada ao LLM sem modelo ou sem chave  ·  vermelha
       dublê conta zero chamadas

07:09  🧬 EXIGE   cut_counts fixo em zero  ·  vermelha
       prova "sermon show traz cut_counts reais"

07:09  🧬 EXIGE   --force sem apagar os cortes antigos  ·  vermelha
       reprocesso grava só os novos, sem IntegrityError

07:09  🧬 EXIGE   suggestion_error não limpo na sugestão seguinte
       vermelha

07:10  ⚠️ LACUNA  ponto de troca do dublê no process não decidido
       sem fábrica patchável (como processing.default_gateways) e sem
       guarda autouse, o passo 5 fica PARCIAL

07:10  ⚠️ LACUNA  config.py só lê a chave mascarada
       falta um leitor em claro; o plano não lista config.py

07:10  ⚠️ LACUNA  llm_not_configured não existe em errors.EXIT_CODES
       WordcutError levanta ValueError hoje; falta errors.py,
       test_errors.py e docs/cli.md §5.3 como obrigatórios

07:11  ⚠️ LACUNA  --force apaga as palavras antes; cortes ficam órfãos
       ou o FK quebra a tarefa; o plano não diz que os cortes saem
       junto, na mesma transação

07:11  ⚠️ LACUNA  FK de preset_id bloqueia apagar preset antigo
       ON DELETE SET NULL ou sem FK; senão preset delete vira
       internal_error depois de uma sugestão

07:11  ⚠️ LACUNA  estado da tarefa quando a sugestão falha
       fixado: tarefa succeeded, error_code nulo, suggestion_error no
       resultado (FR-005)

07:11  ⚠️ LACUNA  suggested_cuts no resultado diverge de §7.4
       §7.4: resultado = show sem last_task; avisos de descarte sem
       campo; fixado suggestion_warnings documentado

07:12  ⚠️ LACUNA  forma de cada item de cuts e de suggestion_error
       fixada pelos campos da entidade e {code, message} | null

07:12  ⚠️ LACUNA  exceção não WordcutError na sugestão marca failed
       o except BaseException de _run pega httpx.HTTPError e envelope
       malformado; OpenRouterModel tem de convertê-los em llm_error

07:12  ⚠️ LACUNA  nova tentativa em erro HTTP não decidida
       fixado: só erro de esquema tem nova tentativa (§III)

07:12  ⚠️ LACUNA  numeração das frases (ID ou posição) não decidida
       barra aceita qualquer, com teste de IDs diferentes da posição

07:13  ⚠️ LACUNA  reorder=false e resposta fora de ordem
       fixado: inválida, conta tentativa

07:13  ⚠️ LACUNA  JSON dentro de cerca markdown
       fixado: inválida; tirar a cerca é conserto heurístico (§III)

07:13  ⚠️ LACUNA  docs: §7.4 diz "chega no item 9"; §7.2 sem o erro
       passo 6 só cita §5.3 "se surgir"; fica PARCIAL sem §7.2/§7.4

07:13  ⚠️ LACUNA  sermon show legível não mostra o erro da sugestão
       apps/cli fora do escopo do plano; fixado: uma linha no texto

07:14  ⚠️ LACUNA  etapa de progresso da sugestão não definida
       nova etapa só documentada em §7.4; o teste de etapas acompanha

07:14  ⚠️ LACUNA  teste do repositório de cortes não listado
       passo 1 sem arquivo de teste próprio no Contexto de código

07:14  ⚠️ LACUNA  base.md admite corte dentro da frase; esquema é por frase
       instrução de formato diz "frases inteiras"; base.md intocado

07:14  ⚠️ LACUNA  "soma das faixas" sem unidade exata
       fixado: fim da última palavra − início da primeira, por trecho,
       em tempo da pregação; fronteiras min e max inclusivas

## Rodada 1 · implementador

--- Passo 1: Cortes no banco ---

07:10  🔴 RED    test_stored_cuts_are_read_back_with_every_field_in_insertion_order
       Cortes gravados em lote voltam com todos os campos, em ordem.
       Passo 1 (b) da matriz; entidade Corte da spec.
       E   ImportError: cannot import name 'cuts' from 'wordcut.db'

07:11  🟢 GREEN  test_stored_cuts_are_read_back_with_every_field_in_insertion_order  ·  1 passed

07:11  🔴 RED    test_counts_tell_how_many_cuts_of_the_sermon_are_in_each_state
       Contagem por estado só da pregação pedida, nos três estados.
       Passo 1 (b); Verificação 8 (cut_counts reais).
       E       AttributeError: module 'wordcut.db.cuts' has no attribute
       'counts_of'

07:11  🟢 GREEN  test_counts_tell_how_many_cuts_of_the_sermon_are_in_each_state  ·  2 passed

07:11  🔴 RED    test_deleting_the_cuts_of_one_sermon_keeps_the_other_sermons_ones
       Apagar por pregação tira só os cortes dela.
       Passo 1 (b); decisão 4 (reprocesso apaga os cortes).
       E           AttributeError: module 'wordcut.db.cuts' has no attribute
       'delete_of'

07:11  🟢 GREEN  test_deleting_the_cuts_of_one_sermon_keeps_the_other_sermons_ones  ·  3 passed

07:12  🔴 RED    esquema da migração 0007 (cascata, SET NULL, CHECKs, versão 6→7)
       Apagar a pregação leva os cortes; apagar preset antigo deixa o corte
       sem preset; estado e origem fora da lista são recusados; banco na 6
       migra sem perder pregações, palavras e presets.
       Passo 1 (a)(c); decisão 5.
       Passaram de primeira: o esquema veio inteiro no GREEN do primeiro
       teste. RED provado por mutação, uma por vez: sem SET NULL, sem
       CASCADE, sem CHECK de status, sem CHECK de source, sem a coluna do
       erro → 1 failed cada.

07:12  🟢 GREEN  test_cuts_repository.py (esquema)  ·  8 passed

07:12  🔴 RED    test_shown_sermon_lists_its_cuts_with_their_segments_range_and_preset
       sermon show traz os cortes gravados na forma da barra.
       Passo 1 (d); decisão 8; Verificação 8.
       E       AssertionError: assert [] == [{'id': 1, 's...': 99}], ...}]

07:12  🟢 GREEN  test_shown_sermon_lists_its_cuts_with_their_segments_range_and_preset  ·  11 passed

07:13  🔴 RED    test_listed_and_shown_sermons_count_their_cuts_by_state
       list e show contam os cortes por estado (1, 2, 1).
       Passo 1 (d); mutação EXIGE 'cut_counts fixo em zero'.
       E       AssertionError: assert ({'suggested'...iscarded': 0}) ==
       ({'suggested'...iscarded': 1})

07:13  🟢 GREEN  test_listed_and_shown_sermons_count_their_cuts_by_state  ·  12 passed

07:13  🔴 RED    test_shown_sermon_tells_the_last_suggestions_failure
       show traz suggestion_error {code, message}; null numa pregação sem
       falha.
       Passo 1 (d); decisão 8.
       E   ImportError: cannot import name 'SuggestionError' from
       'wordcut.db.sermons'

07:13  🟢 GREEN  test_shown_sermon_tells_the_last_suggestions_failure  ·  28 passed

       ajuste: test_presets_repository conferia user_version == 6 depois de
       migrar até a última; passa a conferir >= 6, como o de transcrições.
       O teste da migração 6→7 grava a pregação por SQL (o repositório já
       lê as colunas novas).

07:15  ✅ PASSO 1/6 — Cortes no banco  ·  +11 testes  ·  suíte 762

--- Passo 2: Entrada e resposta ---

07:16  🔴 RED    test_the_user_message_numbers_every_sentence_from_1_in_order_without_times
       Usuário recebe uma linha N: texto por frase, de 1 em diante, sem
       tempo.
       FR-002; Passo 2 (b); decisão 11; EXIGE 'tempos incluídos'.
       E   ModuleNotFoundError: No module named 'wordcut.suggestion'

07:16  🟢 GREEN  test_the_user_message_numbers_every_sentence_from_1_in_order_without_times  ·  1 passed

07:16  🔴 RED    test_the_system_message_is_the_preset_prompt_then_the_answer_schema_by_whole_sentences
       Sistema = build_prompt(preset) e depois o esquema da resposta, por
       frases inteiras.
       FR-002; Passo 2 (a); decisão 18.
       E       AssertionError: assert ('Objetivo: v... False, False) == ('',
       True, True, True, True)

07:16  🟢 GREEN  test_the_system_message_is_the_preset_prompt_then_the_answer_schema_by_whole_sentences  ·  2 passed

07:16  🔴 RED    test_an_answer_in_the_schema_gives_its_cuts[4 casos]
       Válidas: sem cortes, um, vários, mesma frase em dois cortes,
       reordenado com reorder.
       Passo 2 (d); FR-003.
       E   ModuleNotFoundError: No module named
       'wordcut.suggestion.response'

07:16  🟢 GREEN  test_an_answer_in_the_schema_gives_its_cuts  ·  4 passed

07:17  🔴 RED    test_an_answer_outside_the_schema_is_invalid_and_says_why[20 casos]
       Cada inválido da barra (não JSON, cerca markdown, raiz, cuts, title,
       sentences, ID booleano/float/string, inexistente, repetido, fora de
       ordem sem reorder) dá InvalidResponse com motivo.
       Passo 2 (e); FR-003; decisões 12 e 13; EXIGE 'frase inexistente' e
       'frase repetida'.
       20 failed: 12 DID NOT RAISE InvalidResponse; JSONDecodeError,
       KeyError, TypeError nos demais

07:17  🟢 GREEN  test_an_answer_outside_the_schema_is_invalid_and_says_why  ·  24 passed

07:17  ✅ PASSO 2/6 — Entrada e resposta  ·  +26 testes  ·  suíte 788

--- Passo 3: Modelo ---

07:18  🔴 RED    test_completing_posts_the_messages_to_openrouter_with_the_key_and_returns_the_content
       POST na URL do OpenRouter com Bearer da chave, modelo, mensagens,
       response_format JSON e timeout nomeado; devolve
       choices[0].message.content.
       FR-006; Passo 3 (a)(d); EXIGE 'Authorization omitido'.
       E   ModuleNotFoundError: No module named 'wordcut.suggestion.model'

07:18  🟢 GREEN  test_completing_posts_the_messages_to_openrouter_with_the_key_and_returns_the_content  ·  1 passed

07:18  🔴 RED    test_any_failure_to_get_an_answer_is_an_llm_error_without_key_messages_or_body[9 casos]
       401, 429, 500, timeout, conexão, 200 não JSON, sem choices, choices
       vazia e content nulo viram llm_error (saída 6), sem chave, prompt,
       frases nem corpo no erro e no log.
       Passo 3 (b); decisão 9; §VI; EXIGE 'corpo da resposta HTTP na
       mensagem'.
       9 failed: KeyError 'choices', httpx.ReadTimeout, httpx.ConnectError,
       JSONDecodeError, IndexError; nenhum WordcutError

07:18  🟢 GREEN  test_any_failure_to_get_an_answer_is_an_llm_error_without_key_messages_or_body  ·  10 passed

       httpx entra nas dependências do core; uv lock acrescenta 2 linhas e
       uv lock --check fica limpo.

07:20  ✅ PASSO 3/6 — Modelo  ·  +10 testes  ·  suíte 798

--- Passo 4: Orquestração ---

07:21  🔴 RED    test_the_llm_key_is_read_in_clear_only_once_stored
       config.llm_key() devolve a chave em claro, ou None sem chave.
       Decisão 2.
       E   ImportError: cannot import name 'llm_key' from 'wordcut.config'

07:21  🟢 GREEN  test_the_llm_key_is_read_in_clear_only_once_stored  ·  33 passed

07:21  🔴 RED    test_every_documented_error_code_maps_to_its_exit_code[llm_not_configured]
       llm_not_configured existe e sai com 5.
       Decisão 3; Cenário 'sem configuração do LLM'.
       E           ValueError: unknown error code: llm_not_configured

07:21  🟢 GREEN  test_every_documented_error_code_maps_to_its_exit_code  ·  33 passed

07:22  🔴 RED    test_a_valid_answer_is_saved_as_suggested_cuts_with_one_segment_per_run_of_sentences
       Resposta válida: uma chamada; corte suggested, llm, preset_id,
       título; [3,4,5,9,10] vira dois trechos; faixa da 3 à 10; IDs de frase
       diferentes da posição.
       Cenário 'sugestão automática'; FR-004; Passo 4 (a); decisão 11; EXIGE
       'todas as frases num trecho só', 'preset_id não gravado'.
       E   ImportError: cannot import name 'SuggestionModel' from
       'wordcut.suggestion'

07:22  🟢 GREEN  test_a_valid_answer_is_saved_as_suggested_cuts_with_one_segment_per_run_of_sentences  ·  1 passed

07:22  🔴 RED    test_the_real_model_is_refused_inside_the_test_suite
       A fixture autouse no_real_llm faz a fábrica real falhar em qualquer
       teste.
       Decisão 1; Passo 3 (c); borda 'testes nunca chamam o OpenRouter'.
       E       Failed: DID NOT RAISE AssertionError

07:22  🟢 GREEN  test_the_real_model_is_refused_inside_the_test_suite  ·  2 passed

07:22  🔴 RED    test_a_reordered_cut_keeps_its_play_order_and_spans_its_range_in_sermon_order + test_the_model_is_built_with_the_configured_model_and_key
       [9,10,3] com reorder: trechos 9–10 e 3, faixa da 3 à 10; a fábrica
       recebe o modelo e a chave das configurações.
       Passo 4 (a); FR-006; EXIGE 'faixa pela ordem da resposta'.
       Passaram de primeira (o GREEN anterior já ordena a faixa e passa a
       chave). RED provado por mutação: faixa pela ordem da resposta → 1
       failed; chave trocada → 1 failed.

07:22  🟢 GREEN  reorder + fábrica configurada  ·  4 passed

07:23  🔴 RED    test_an_answer_outside_the_schema_is_asked_again_once_with_the_reason + test_a_cited_sentence_that_does_not_exist_costs_an_attempt
       Inválida e depois válida: duas chamadas, mesma entrada mais o motivo;
       grava os cortes da segunda. Frase inexistente conta tentativa.
       Cenário 'resposta inválida, nova tentativa'; Passo 4 (b)(d); EXIGE
       'sem nova tentativa', 'checagem de frase inexistente removida'.
       E           wordcut.suggestion.response.InvalidResponse: a resposta
       não é um JSON válido

07:23  🟢 GREEN  nova tentativa  ·  6 passed

07:23  🔴 RED    test_two_answers_outside_the_schema_are_an_llm_error_kept_on_the_sermon_without_cuts
       Duas inválidas: exatamente duas chamadas, llm_error, nenhum corte,
       suggestion_error no show.
       Cenário 'duas respostas inválidas'; Passo 4 (c); EXIGE 'duas novas
       tentativas (três chamadas)'.
       E           wordcut.suggestion.response.InvalidResponse: a resposta
       não é um JSON válido

07:23  🟢 GREEN  test_two_answers_outside_the_schema_are_an_llm_error_kept_on_the_sermon_without_cuts  ·  7 passed

07:24  🔴 RED    test_without_the_model_or_the_key_the_llm_is_not_called_and_the_error_says_what_is_missing[3 casos]
       Sem modelo, sem chave ou sem os dois: llm_not_configured (5), fábrica
       nunca chamada, details.missing, chave fora do erro, erro no show.
       Cenário 'sem configuração'; Passo 4 (g); decisão 3; EXIGE 'chamada ao
       LLM sem modelo ou sem chave'.
       E       AssertionError (assert name is not None and key is not None)

07:24  🟢 GREEN  llm_not_configured  ·  11 passed

       test_an_llm_error_from_the_model_is_not_asked_again passou de
       primeira: só InvalidResponse dispara a nova tentativa (decisão 10).
       Provado na mutação abaixo.

07:25  🔴 RED    test_cuts_whose_estimated_duration_falls_outside_the_allowed_one_are_dropped_with_a_warning
       Bruto 100/estimado 82 (=máx) fica; 90,2 e 32,8 saem com aviso; 41
       (=mín) fica; dois trechos somam por trecho, não pela faixa.
       Borda 'fora da duração'; Passo 4 (e); decisão 19.
       E       AttributeError: 'NoneType' object has no attribute 'warnings'

07:25  🟢 GREEN  test_cuts_whose_estimated_duration_falls_outside_the_allowed_one_are_dropped_with_a_warning  ·  12 passed

       Os testes anteriores ganharam frases que cabem na duração do preset
       ("Segunda" com 6 frases; o reordenado com um preset de 10-600 s).
       Mutações, uma por vez, todas vermelhas (1 failed cada): fator 1,0;
       descarte removido; máximo exclusivo; mínimo exclusivo; nova
       tentativa também em llm_error; três chamadas.

07:26  🔴 RED    test_a_valid_answer_without_cuts_to_keep_saves_nothing_and_is_no_error + test_a_successful_suggestion_clears_the_previous_ones_error
       Sem cortes ou todos descartados: nada gravado, sem erro. A sugestão
       seguinte limpa o suggestion_error.
       Borda 'nenhum corte válido'; Passo 4 (f)(h); EXIGE 'suggestion_error
       não limpo'.
       E       At index 1 diff: {'code': 'llm_error', ...} != None

07:26  🟢 GREEN  limpa o erro anterior  ·  15 passed

07:26  ✅ PASSO 4/6 — Orquestração  ·  +17 testes  ·  suíte 815

--- Passo 5: Integração no process ---

07:27  🔴 RED    test_processing_ends_by_saving_the_cuts_the_llm_suggests_with_the_default_preset
       process com FakeGateways e dublê: processed, corte suggested com o
       preset padrão, uma chamada com o prompt do padrão e as 10 frases;
       resultado = show sem last_task mais suggestion_warnings.
       FR-001; Cenário 'sugestão automática'; Passo 5 (a); decisões 7 e 16.
       E       ValueError: not enough values to unpack (expected 1, got 0)

07:27  🟢 GREEN  test_processing_ends_by_saving_the_cuts_the_llm_suggests_with_the_default_preset  ·  6 passed

       test_process_task ajustado: etapa (0.96, "sugerindo") depois de
       gravando, e o resultado ganha suggestion_warnings (decisões 7, 16).
       O apagar dos cortes no --force entrou neste GREEN; o teste dele vem
       abaixo, com mutação.

07:28  🔴 RED    falha da sugestão no process (4 testes)
       Duas inválidas: tarefa succeeded sem error_code, pregação processed
       com frases, sem cortes, llm_error no show e no resultado. Sem
       configuração: sem chamada. ConnectError real: processed. --force
       troca os cortes.
       FR-005; Passo 5 (b)(c)(d)(e); decisões 4, 6 e 9; EXIGE 'process sem
       capturar', '--force sem apagar'.
       Passaram de primeira (o GREEN anterior já captura e já apaga). RED
       provado por mutação: sem capturar WordcutError → 3 failed; --force
       sem apagar cortes → 1 failed; ConnectError sem conversão → 1 failed.

07:28  🟢 GREEN  falha da sugestão no process  ·  5 passed

07:28  🔴 RED    test_the_llm_key_reaches_only_the_request_never_the_task_the_sermon_or_the_log
       Com o OpenRouterModel real e um 401 que ecoa a chave sentinela: o
       Bearer chega ao transport, e a chave não aparece na linha tasks, no
       show nem no log DEBUG.
       Borda 'a chave nunca aparece'; Passo 5 (f); §VI.
       Passou de primeira (o passo 3 já tira o corpo da mensagem). RED
       provado por mutação: corpo da resposta na mensagem → 1 failed.

07:28  🟢 GREEN  test_the_llm_key_reaches_only_the_request_never_the_task_the_sermon_or_the_log  ·  6 passed

07:31  🔴 RED    test_show_tells_why_the_last_suggestion_failed
       sermon show legível termina com a linha do erro da sugestão; o --json
       traz cuts, cut_counts e suggestion_error reais.
       Passo 5 (g); decisão 15.
       E       AssertionError: assert (0, 'Cortes: ...iscarded': 0}) == (0,
       'Sugestão...iscarded': 0})

07:31  🟢 GREEN  test_show_tells_why_the_last_suggestion_failed  ·  29 passed

       test_sermon_process_command ajustado: as etapas no stderr ganham
       "[process] sugerindo 96%" (decisão 16).

07:31  ✅ PASSO 5/6 — Integração no process  ·  +7 testes  ·  suíte 822

--- Passo 6: Documentação ---

       Sem TDD (texto). docs/cli.md §5.3 (llm_not_configured), §7.2 (cuts,
       suggestion_error, linha do show legível), §7.4 (sugestão ao fim, falha
       sem desfazer, --force apaga cortes, suggestion_warnings, etapa
       sugerindo); ADR-0016 (porta do LLM, falha gravada na pregação) e
       índice; docs/architecture §3, §4 e diagrama 5.1 com o OpenRouter;
       README; CHANGELOG.

07:33  ✅ PASSO 6/6 — Documentação  ·  +0 testes  ·  suíte 822

       Verificação final: pytest 822 passed; ruff check e format limpos;
       mypy limpo (73 arquivos); uv lock --check limpo; mypy --strict nos
       6 arquivos de teste novos limpo; base.md e textos dos critérios
       intocados; grep "openrouter.ai" nos testes vazio.

## Rodada 1 · QA

07:34  📊 SUÍTE  822 passed  ·  0 failed
       ruff check, ruff format --check e mypy limpos (73 arquivos);
       uv lock --check limpo; mypy --strict nos 6 testes novos limpo

07:35  🔎 QA     guarda do LLM e chave
       grep "openrouter.ai" nos testes vazio; OpenRouterModel só com
       MockTransport; no_real_llm troca suggestion.default_model; nenhuma
       leitura em claro da chave fora de _configured_model

07:40  🧬 MUTAÇÕES · EXIGE do plano + extras (cópia no scratchpad)  ·  31 de 34 mortas
       ☠️  sem nova tentativa                              4 testes
       ☠️  três chamadas                                   3 testes
       ☠️  frase inexistente aceita                        3 testes
       ☠️  fator 1,0 / descarte removido                   1 / 2 testes
       ☠️  máximo exclusivo / mínimo exclusivo             1 / 1 teste
       ☠️  um trecho só / faixa na ordem da resposta       2 / 1 testes
       ☠️  preset_id nulo / status chosen                  2 / 2 testes
       ☠️  tempos nas linhas do usuário                    1 teste
       ☠️  Authorization omitido                           2 testes
       ☠️  corpo HTTP na mensagem de erro                  4 testes
       ☠️  process sem capturar WordcutError               14 testes
       ☠️  chamada sem modelo ou chave                     14 testes
       ☠️  cut_counts zero / cuts vazio no show            2 / 10 testes
       ☠️  --force sem apagar cortes                       1 teste
       ☠️  suggestion_error não limpo                      1 teste
       ☠️  cerca markdown tirada / ordem sem reorder       1 / 1 teste
       ☠️  nova tentativa em llm_error                     2 testes
       ☠️  timeout omitido / envelope e HTTPError sem
           conversão                                       1 / 3 / 2 testes
       ☠️  duração pela faixa, não por trecho              1 teste
       ☠️  sistema sem build_prompt / show sem a linha     2 / 1 testes
       ☠️  chave na mensagem de llm_not_configured         1 teste
       🚨  título sem strip                    SOBREVIVEU — fora da barra
       🚨  campo extra no corte recusado       SOBREVIVEU — decisão do
           orquestrador (aceitar campos extras) sem teste; note de
           reorder.md invalidaria a resposta sem ninguém ver
       🚨  nova tentativa sem o motivo         SOBREVIVEU — o teste busca
           "JSON", que RETRY_NOTE já contém; Passo 4 (b) sem prova
       🚨  frase repetida aceita               SOBREVIVEU — EXIGE
           vermelha; [3, 4, 3] com reorder=false cai na checagem de
           ordem; o código recusa (sondado com reorder=true), o teste não

07:41  🔎 QA     passo 1/6 — Cortes no banco  ·  ✅ PASS
       migração 0007, repositório, cascata, SET NULL, CHECKs, 6→7 e
       show/list reais, com teste e mutações mortas

07:41  🔎 QA     passo 2/6 — Entrada e resposta  ·  ⚠️ PARCIAL
       mutação EXIGE "frase repetida aceita" sobrevive; campos extras
       aceitos (decisão do orquestrador) sem teste

07:41  🔎 QA     passo 3/6 — Modelo  ·  ✅ PASS
       URL, Bearer, modelo, response_format, timeout; 9 falhas viram
       llm_error sem chave, prompt nem corpo, também no caplog DEBUG

07:41  🔎 QA     passo 4/6 — Orquestração  ·  ⚠️ PARCIAL
       a nova tentativa sem o motivo passa no teste (4 b); o resto da
       matriz (a, c–i) provado

07:41  🔎 QA     passo 5/6 — Integração no process  ·  ✅ PASS
       succeeded/processed nas falhas, ConnectError real, --force, chave
       ausente de tasks/show/log, CLI legível e --json, etapa sugerindo

07:41  🔎 QA     passo 6/6 — Documentação  ·  ✅ PASS
       §5.3, §7.2, §7.4, arquitetura §4 e 5.1, CHANGELOG, ADR-0016 com
       índice; base.md e critérios intocados

## Rodada 2 · implementador

       Reabertos pela Rodada 1 do qa.md: Passo 2 e Passo 4 (b). A produção
       já tem o comportamento; o RED de cada teste é a mutação que o QA viu
       sobreviver, aplicada à mão e desfeita na hora (cmp com a cópia).

--- Passo 2: Entrada e resposta ---

07:43  🔴 RED    test_an_answer_in_the_schema_gives_its_cuts[note of the reorder option ignored] + [unknown field in the cut ignored]
       Campos além de title e sentences no corte (note de reorder.md, um
       desconhecido) são aceitos e ignorados; obrigatórios estritos.
       Decisão do orquestrador (Rodada 1, campos extras); Passo 2 (d).
       Sob a mutação "campo extra no corte recusado":
       E   InvalidResponse: o corte 1 tem campo extra  ·  2 failed

07:43  🟢 GREEN  mutação desfeita  ·  26 passed

07:43  🔴 RED    test_a_sentence_repeated_in_a_cut_is_invalid_even_when_reordering_is_allowed
       Frase repetida no corte é recusada por repetição mesmo com
       reorder = true, onde a checagem de ordem não a pegaria antes.
       Passo 2 (e); EXIGE 'frase repetida no corte aceita'.
       Sob a mutação (checagem de repetição removida):
       E   Failed: DID NOT RAISE InvalidResponse  ·  1 failed

07:43  🟢 GREEN  mutação desfeita  ·  27 passed

07:44  ✅ PASSO 2/6 — Entrada e resposta  ·  +3 testes  ·  suíte 825

--- Passo 4: Orquestração (b) ---

07:44  🔴 RED    test_an_answer_outside_the_schema_is_asked_again_once_with_the_reason
       A segunda mensagem leva o motivo específico da recusa: a primeira
       resposta cita a frase 13 de 12, e o texto exato que parse_response
       dá a ela ("cita frase inexistente; as frases vão de 1 a 12") tem
       de estar no acréscimo, não só o RETRY_NOTE fixo.
       Cenário 'resposta inválida, nova tentativa'; Passo 4 (b); decisão
       'nova tentativa ... mais uma mensagem curta dizendo o erro'.
       Sob a mutação RETRY_NOTE.format(reason=''):
       E   AssertionError: At index 2 diff: False != True  ·  1 failed

07:44  🟢 GREEN  mutação desfeita  ·  15 passed

07:45  ✅ PASSO 4/6 — Orquestração (b)  ·  +0 testes (1 reforçado)  ·  suíte 825

       Verificação final: pytest 825 passed; ruff check e format limpos;
       mypy limpo (73 arquivos); mypy --strict nos 2 testes alterados
       limpo; uv lock --check limpo. Produção intocada nesta rodada
       (response.py e __init__.py iguais às cópias após cada mutação).
       Decisão "Campos da resposta" registrada no plan.md.

## Rodada 2 · QA

07:46  📊 SUÍTE  825 passed  ·  0 failed
       ruff check, ruff format --check e mypy limpos (73 arquivos);
       uv lock --check limpo; mypy --strict nos 2 testes alterados
       limpo; grep "openrouter.ai" nos testes vazio

07:48  🔎 QA     produção desde a Rodada 1
       response.py e __init__.py iguais byte a byte à cópia da Rodada 1;
       só test_suggestion_response.py e test_suggestion.py mudaram

07:49  🧬 MUTAÇÕES · reabertos 2 e 4 (b) (cópia no scratchpad)  ·  10 de 11 mortas
       ☠️  frase repetida aceita (reorder=true)          1 teste
       ☠️  campo extra no corte recusado                 2 testes
       ☠️  só o note recusado                            1 teste
       ☠️  topo sem exigir cuts                          1 teste
       ☠️  nova tentativa sem o motivo (reason='')       1 teste
       ☠️  motivo genérico / nome do tipo                1 / 1 teste
       ☠️  segunda sem a entrada / motivo antes dela     1 / 1 teste
       ☠️  sem nova tentativa                            4 testes
       🚨  título sem strip                    SOBREVIVEU — fora da barra,
           como na Rodada 1

07:50  🔎 QA     passo 2/6 — Entrada e resposta  ·  ✅ PASS
       EXIGE "frase repetida aceita" vermelha com reorder=true; note e
       campo desconhecido aceitos e ignorados, com teste; topo exige cuts

07:50  🔎 QA     passo 4/6 — Orquestração  ·  ✅ PASS
       a segunda mensagem = mesma entrada + texto exato da recusa
       ("cita frase inexistente..."); reason='' e motivo genérico morrem

07:50  🔎 QA     passos 1, 3, 5, 6  ·  ✅ PASS
       produção e documentação intocadas desde a Rodada 1; suíte verde
