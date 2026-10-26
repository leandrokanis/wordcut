## Plano de QA

baseline_commit 7c8f45015d38e76a8ef8679e9f0b0cd8881f1abd

15:36  📐 BARRA   corpos iguais ao JSON da CLI
       resposta HTTP comparada com a função de serviço que a CLI chama,
       no formato que a CLI imprime; exceção acordada: sem path (L3)

15:36  📐 BARRA   tabela route → papel igual às rotas do app
       test_permissions percorre as APIRoute de routes.ROUTERS, não o
       OpenAPI; prova 401, 403 sem efeito e que não há rota de conteúdo

15:37  📐 BARRA   segredo fictício nunca volta
       valor inteiro procurado em corpo, cabeçalhos e caplog DEBUG, em
       sucesso, 400 e 409; a máscara mostra 4 caracteres de propósito

15:37  📐 BARRA   exportar → 202 sem renderizar
       harmless_tasks com a lista de processos; nenhum detached_tasks de
       render, que montaria ffmpeg real no processo filho

15:37  📐 BARRA   estimativa sem tarefa, sem salvar, sem trava
       GET /api/tasks vazio, render_options do corte igual e 200 com
       lock_owner segurando a trava

15:38  🧬 EXIGE   detach=False em POST /api/cuts/{id}/renders  ·  vermelha
       a tarefa rodaria na requisição e bateria em no_real_rendering

15:38  🧬 EXIGE   identidade fora da inclusão dos routers  ·  vermelha
       só morre se a identidade estiver num lugar só (L1)

15:38  🧬 EXIGE   rota include_in_schema=False fora de ROUTERS
       ·  vermelha
       o risco que o 20a deixou; a contagem de app.routes pega

15:38  🧬 EXIGE   require("admin") fora de members/presets/settings
       ·  vermelha
       assistente recebe 403 sem gravar segredo, preset ou membro

15:39  🧬 EXIGE   PUT de segredo devolvendo ou logando o corpo
       ·  vermelha
       procura do valor fictício inteiro nas respostas e no caplog

15:39  🧬 EXIGE   path da exportação vazando na resposta  ·  vermelha
       nenhuma resposta contém str(wordcut_home)

15:40  ⚠️ LACUNA  L1 identidade estrutural x padrão do 20a
       20a declara no APIRouter; app.routes traz _IncludedRouter e a
       varredura lê o OpenAPI; passo 4 PARCIAL sem ROUTERS e contagem

15:40  ⚠️ LACUNA  L2 papel das leituras de presets e critérios
       spec diz "escrita"; 1.2.a e cli §11 dizem admin; recomendado
       admin em tudo de settings/criteria/presets/members

15:40  ⚠️ LACUNA  L3 path absoluto da exportação na API
       shown_render expõe /data/…; recomendado tirar, como o
       needs_reprocess do 20a; passo 2 PARCIAL se vazar

15:41  ⚠️ LACUNA  L4 e-mail do membro na URL
       uvicorn, nginx e Cloudflare registram o caminho; recomendado
       e-mail só no corpo (POST add, set-role, remove)

15:41  ⚠️ LACUNA  L5 /config montado só leitura na api
       PUT de segredo dá sempre 409 config_not_writable no deploy;
       recomendado não mudar o Compose aqui, testar e documentar

15:41  ⚠️ LACUNA  L6 corpos de entrada não fixados
       extra=forbid, tipos estritos, escolhas como str para o serviço
       dar choices; PATCH {} da legenda hoje grava e marca editado

15:42  ⚠️ LACUNA  L7 extra_forbidden repete o nome digitado
       conferido no baseline: details.argument traz o campo; fere a
       ADR-0015; errors.py precisa tratar como não reconhecido

15:42  ⚠️ LACUNA  L8 status de sucesso não fixados
       201 em criar preset e membro; 200 com corpo nos DELETE

15:42  ⚠️ LACUNA  L9 guarda de rede não cobre a renderização
       render destacado real rodaria ffmpeg; só harmless_tasks; corte
       de teste pelos repositórios

15:43  ⚠️ LACUNA  L10 decisões novas sem ADR
       L1, L3, L4, L5 e L7 pedem ADR-0021; passo 5 PARCIAL sem ela

15:43  ⚠️ LACUNA  L11 contexto de código incompleto
       faltam routes/__init__.py, errors.py, conftest, test_auth e os
       routers do 20a

## Rodada 1 · implementador

15:44  📝 PLANO   decisões L1–L11 registradas no plan.md
       Decisões técnicas e Contexto de código, antes do código

--- Passo 1: Cortes ---

15:45  🔴 RED    test_listing_answers_the_cuts_as_the_cli_lists_them_the_discarded_last
       GET /api/sermons/{id}/cuts é list_cuts, descartados por último
       Passo 1 (a); FR-001
       AssertionError: assert (404, …) == (200, {'items' …}, [2, 1])

15:45  🟢 GREEN  test_listing_answers_the_cuts_as_the_cli_lists_them_the_discarded_last  ·  1 passed

15:45  🔧 REFAC  routes.ROUTERS incluídos num laço com current_member
       a identidade sai dos APIRouter do 20a (L1); suíte da API 119 passed

15:46  🟢 GREEN  test_listing_by_status_answers_only_the_cuts_in_that_status  ·  4 passed
       verde de saída: o filtro entrou no GREEN anterior; a mutação abaixo
       prova que o teste o cobre
       + status fora das escolhas (400 com choices, sem eco) e pregação
       inexistente (404 com sermon_id), pelo Literal e pelo serviço

15:46  🧬 MUTANTE ?status ignorado (list_cuts com None)  ·  morto
       test_listing_by_status… vermelho; desfeito, 4 passed

15:46  🔴 RED    test_showing_a_cut_answers_it_as_the_cli_shows_it_without_the_local_paths
       GET /api/cuts/{id} é show_cut sem o path das exportações
       Passo 1 (b); FR-001, FR-004, L3
       AssertionError: assert (404, …) == (200, {'id': …}, 1, False)

15:46  🟢 GREEN  test_showing_a_cut_answers_it_as_the_cli_shows_it_without_the_local_paths  ·  5 passed

15:46  🟢 GREEN  test_showing_a_missing_cut_is_not_found_with_its_id  ·  7 passed
       verde de saída, pelo serviço (404 cut_id) e pela validação do
       caminho (400 sem eco); entram como contrato da rota

15:46  🔴 RED    test_the_preview_answers_the_sequence_the_cli_previews_even_with_the_lock_held
       GET /api/cuts/{id}/preview é preview_cut, com a trava ocupada
       Passo 1 (c); FR-001
       AssertionError: assert (404, …) == (200, {'cut_id' …})

15:46  🟢 GREEN  test_the_preview_answers_the_sequence_the_cli_previews_even_with_the_lock_held  ·  8 passed

15:47  🔴 RED    test_a_transition_answers_200_with_the_cut_as_the_next_show_gives_it_same_segments
       choose e discard dão 200 com o corte do GET seguinte, trechos iguais
       Passo 1 (d); FR-001, constituição §I, L8
       AssertionError: assert (404, …) == (200, {'id': …})

15:47  🟢 GREEN  test_a_transition_answers_200_with_the_cut_as_the_next_show_gives_it_same_segments  ·  10 passed

15:47  🟢 GREEN  test_restoring_undoes_a_discard_only  ·  12 passed
       verde de saída: restore entrou com as transições; descartado volta a
       sugerido, escolhido fica escolhido

15:47  🧬 MUTANTE discard ligado a choose_cut  ·  morto
       a transição discard fica vermelha; desfeito

15:47  🧬 MUTANTE show_cut sem o path removido (L3)  ·  morto
       3 vermelhos (GET do corte e transições); desfeito, 12 passed

15:48  🔴 RED    test_fixing_a_word_answers_the_word_as_the_cli_fixes_it
       PUT /api/cuts/{id}/words/{word_id} {"text"} é fix_word
       Passo 1 (e); cenário escolher e ajustar; FR-001
       AssertionError: assert (404, …) == (200, {'cut_id' …}, 'Graça')

15:48  🟢 GREEN  test_fixing_a_word_answers_the_word_as_the_cli_fixes_it  ·  13 passed

15:48  🟢 GREEN  test_a_fixed_word_shows_corrected_in_the_cut_and_in_the_preview_even_with_the_lock_held  ·  19 passed
       verdes de saída, pelo serviço: correção no GET e na prévia com a
       trava ocupada; 409 spelling_too_different sem eco e sem mudança;
       texto original desfaz; vazio e duas palavras → 400 text; palavra fora
       dos trechos → 400 word_id

15:48  🧬 MUTANTE texto digitado repetido no erro da correção  ·  morto
       409 e 'duas palavras' vermelhos; desfeito, 19 passed

15:48  🔴 RED    test_the_caption_answers_the_style_as_the_cli_shows_it
       GET /api/cuts/{id}/caption é caption_of
       Passo 1 (f); FR-001
       AssertionError: assert (404, …) == (200, {'enabled' …})

15:49  🟢 GREEN  test_the_caption_answers_the_style_as_the_cli_shows_it  ·  20 passed

15:49  🔴 RED    test_changing_part_of_the_caption_answers_the_whole_style_as_the_cli_changes_it
       PATCH parcial da legenda dá o estilo inteiro de update_caption e marca
       o corte editado; Passo 1 (f); cenário escolher e ajustar; L6
       AssertionError: assert (405, …, False) == (200, {'enabled' …}, True)

15:49  🟢 GREEN  test_changing_part_of_the_caption_answers_the_whole_style_as_the_cli_changes_it  ·  21 passed

15:49  🔴 RED    test_changing_the_caption_with_no_field_is_invalid_argument_and_leaves_the_cut_unedited
       PATCH {} da legenda dá 400 sem marcar o corte editado
       Passo 1 (f); L6
       KeyError: 'error' (a rota respondeu 200 e gravou)

15:50  🟢 GREEN  test_changing_the_caption_with_no_field_is_invalid_argument_and_leaves_the_cut_unedited  ·  22 passed

15:50  🟢 GREEN  test_a_caption_value_out_of_range_is_refused_with_the_range_storing_nothing  ·  30 passed
       verdes de saída: faixa (min/max, nada gravado) e escolhas (choices)
       pelo serviço; tipo errado, null e decimal → 400 pelo corpo estrito

15:50  🔴 RED    test_an_unknown_caption_field_is_refused_without_repeating_its_name
       campo desconhecido → 400 'Argumento não reconhecido', sem o nome
       Passo 1 (f); L7, ADR-0015
       AssertionError: assert (400, {'error' …}, True, False) == (400, …, False, False)

15:50  🟢 GREEN  test_an_unknown_caption_field_is_refused_without_repeating_its_name  ·  149 passed (API)

15:51  🔴 RED    test_resetting_the_caption_answers_200_with_the_default_style_turned_on
       DELETE da legenda → 200 com o estilo padrão ligado, e o GET o mostra
       Passo 1 (f); L8
       AssertionError: assert (405, …) == (200, {'enabled' …})

15:51  🟢 GREEN  test_resetting_the_caption_answers_200_with_the_default_style_turned_on  ·  32 passed

15:51  🧬 MUTANTE PATCH {} da legenda gravando e marcando o corte editado  ·  morto
       teste do {} vermelho; desfeito

15:51  🧬 MUTANTE DELETE da legenda sem chamar reset_caption  ·  morto
       o GET seguinte segue com o estilo antigo; desfeito, 32 passed

15:52  🟢 GREEN  test_the_assistant_changes_a_cut_while_the_machine_is_busy  ·  37 passed
       verde de saída: transições e legenda não tomam a trava (Passo 1 (g))

15:52  ✅ PASSO 1/5 — Cortes  ·  +37 testes  ·  suíte API 155

--- Passo 2: Exportações ---

15:52  🔴 RED    test_exporting_answers_202_with_the_launched_task_found_among_the_tasks
       POST /api/cuts/{id}/renders → 202 launched_task, um processo inofensivo
       e a tarefa em GET /api/tasks/{id}; Passo 2 (a); cenário exportar; L8, L9
       KeyError: 'task_id' (a rota não existe)

15:52  🟢 GREEN  test_exporting_answers_202_with_the_launched_task_found_among_the_tasks  ·  1 passed

15:53  🟢 GREEN  test_the_options_of_an_export_are_saved_on_the_cut  ·  4 passed
       verdes de saída, pelo serviço: opções salvas no corte; caption false
       desliga a legenda e marca editado; sem corpo repete as salvas

15:53  🧬 MUTANTE corpo de opções descartado antes de start_render  ·  morto
       opções salvas e caption false vermelhos; desfeito

15:53  🧬 MUTANTE detach=False na exportação  ·  morto
       a tarefa roda na requisição e bate em no_real_rendering; desfeito

15:53  🧬 MUTANTE 202 → 200 na exportação  ·  morto
       2 vermelhos; desfeito, 4 passed; nenhum processo órfão

15:53  🟢 GREEN  test_an_export_option_outside_its_choices_is_refused_with_them_launching_and_saving_nothing  ·  11 passed
       verdes de saída: escolha fora (choices, sem tarefa, nada salvo); corpo
       malformado (campo desconhecido, texto, null) → 400 sem eco; busy 409
       sem tarefa, processo nem mudança; sermon_not_processed 409; 404 cut_id

15:54  🔴 RED    test_the_estimate_answers_as_the_cli_estimates_without_a_task_saving_nor_the_lock
       GET …/renders/estimate?fade=false&pauses=short é estimate_render, sem
       tarefa, sem salvar e com a trava ocupada; Passo 2 (e); cenário exportar
       AssertionError: assert (404, …) == (200, {'duration' …})

15:54  🟢 GREEN  test_the_estimate_answers_as_the_cli_estimates_without_a_task_saving_nor_the_lock  ·  12 passed

15:54  🟢 GREEN  test_an_estimate_option_outside_its_choices_is_refused_with_them  ·  14 passed
       verdes de saída: escolha fora → choices, pelo serviço; parâmetro
       desconhecido → 400 sem eco, pelo modelo extra=forbid e pela L7

15:54  🧬 MUTANTE estimativa chamando start_render  ·  morto
       a trava ocupada dá 409 e o teste da estimativa fica vermelho; desfeito

15:54  🧬 MUTANTE query da estimativa sem extra=forbid  ·  morto
       parâmetro desconhecido passa; vermelho; desfeito, 14 passed

15:54  🔴 RED    test_the_exports_of_a_cut_answer_as_the_cli_lists_them_newest_first_without_paths
       GET /api/cuts/{id}/renders é list_renders sem path, mais recente antes
       Passo 2 (f); FR-002, L3
       AssertionError: assert (405, …) == (200, {'items' …}, [2, 1], False)

15:55  🟢 GREEN  test_the_exports_of_a_cut_answer_as_the_cli_lists_them_newest_first_without_paths  ·  15 passed

15:55  🔴 RED    test_an_export_answers_as_the_cli_shows_it_without_its_path
       GET /api/renders/{id} é show_render sem path; Passo 2 (f); FR-002, L3
       AssertionError: assert (404, …) == (200, {'id' …}, False)

15:55  🟢 GREEN  test_an_export_answers_as_the_cli_shows_it_without_its_path  ·  16 passed

15:55  🔴 RED    test_the_file_of_an_export_downloads_with_the_readable_name_even_with_the_lock_held
       GET /api/renders/{id}/file → 200, bytes do arquivo, video/mp4 e nome
       AAAA-MM-DD - Título.mp4 em filename*; Passo 2 (g); cenário baixar
       AssertionError: 404 (a rota não existe; o 404 render_id também vermelho)

15:56  🟢 GREEN  test_the_file_of_an_export_downloads_with_the_readable_name_even_with_the_lock_held  ·  21 passed

15:56  🟢 GREEN  test_an_export_whose_file_is_gone_is_an_internal_error_without_the_path  ·  22 passed
       verde de saída, pelo serviço: 500 internal_error com render_id, sem
       caminho (spec 1.1.i.1)

15:56  🧬 MUTANTE filename trocado pelo caminho interno  ·  morto
       os 2 downloads vermelhos; desfeito

15:56  🧬 MUTANTE path vazando em GET /api/renders/{id}  ·  morto
       vermelho; desfeito, 22 passed

15:56  ✅ PASSO 2/5 — Exportações  ·  +22 testes  ·  suíte API 177

--- Passo 3: Administração ---

15:57  🔴 RED    test_the_settings_answer_as_the_cli_shows_them
       GET /api/settings é show_settings; Passo 3 (a); FR-003, FR-004
       AssertionError: assert (404, …) == (200, {'llm_model' …})

15:57  🟢 GREEN  test_the_settings_answer_as_the_cli_shows_them  ·  1 passed

15:57  🔴 RED    test_changing_the_models_answers_the_settings_as_the_cli_changes_them
       PATCH /api/settings {llm_model, whisper_model} é update_settings
       Passo 3 (a); FR-003; L6
       AssertionError: assert (405, …) == (200, {'llm_model' …}, 'medium')

15:57  🟢 GREEN  test_changing_the_models_answers_the_settings_as_the_cli_changes_them  ·  2 passed

15:58  🟢 GREEN  test_changing_no_model_or_a_blank_one_is_invalid_argument  ·  4 passed
       verde de saída, pelo serviço: {} e modelo em branco → 400

15:58  🔴 RED    test_storing_the_llm_key_answers_the_settings_with_the_key_masked_never_in_clear
       PUT /api/settings/llm-key {value} → 200 show_settings com ••••WXYZ;
       valor inteiro fora de corpo, cabeçalhos e log DEBUG; arquivo sem brancos,
       modo 600; Passo 3 (b); borda segredos; FR-004
       FileNotFoundError: …/config/openrouter-key (a rota não existe)

15:58  🟢 GREEN  test_storing_the_llm_key_answers_the_settings_with_the_key_masked_never_in_clear  ·  5 passed

15:58  🔴 RED    test_an_empty_llm_key_is_invalid_argument_naming_value
       chave vazia → 400 com argument value, o campo do corpo; Passo 3 (b); L5
       AssertionError: assert (400, {'argument': 'key'}) == (400, {'argument': 'value'})

15:58  🟢 GREEN  test_an_empty_llm_key_is_invalid_argument_naming_value  ·  6 passed

15:59  🟢 GREEN  test_a_secret_into_a_read_only_folder_is_config_not_writable_without_the_secret[llm-key]  ·  7 passed
       verde de saída, pelo serviço: 409 sem o valor (L5)

15:59  🔴 RED    test_a_secret_into_a_read_only_folder_is_config_not_writable_without_the_secret[youtube-cookies]
       PUT /api/settings/youtube-cookies com a pasta só leitura → 409 sem o
       valor; Passo 3 (b), (c); L5
       AssertionError: assert (404, 'not_found', False) == (409, …, False)

15:59  🟢 GREEN  test_a_secret_into_a_read_only_folder_is_config_not_writable_without_the_secret[youtube-cookies]  ·  8 passed

15:59  🟢 GREEN  test_storing_the_cookies_answers_the_settings_with_them_present_never_in_clear  ·  18 passed
       verdes de saída: cookies → youtube_cookies true, sem cookie em resposta
       ou log; corpo malformado (tipo, null, ausente, campo desconhecido) → 400
       sem gravar; formato fora do Netscape → 400 value sem eco

15:59  🧬 MUTANTE valor do PUT da chave logado em DEBUG  ·  morto
       2 vermelhos; desfeito

15:59  🧬 MUTANTE valor do PUT da chave devolvido no corpo  ·  morto
       vermelho; desfeito

15:59  🧬 MUTANTE store_llm_key não chamado  ·  morto
       3 vermelhos (o teste lê o arquivo); desfeito

15:59  🧬 MUTANTE whisper_model ignorado no PATCH  ·  morto
       2 vermelhos; desfeito, 18 passed

16:00  🔴 RED    test_the_criteria_answer_as_the_cli_lists_them_without_prompt_text
       GET /api/criteria → {items: list_criteria()}, sem texto de prompt
       Passo 3 (d); FR-003
       KeyError: 'items' (a rota não existe)

16:00  🟢 GREEN  test_the_criteria_answer_as_the_cli_lists_them_without_prompt_text  ·  1 passed

16:00  🔴 RED    test_the_presets_answer_as_the_cli_lists_them
       GET /api/presets → {items: list_presets}; Passo 3 (e); FR-003
       AssertionError: assert (404, …) == (200, {'items' …}, 1)

16:00  🟢 GREEN  test_the_presets_answer_as_the_cli_lists_them  ·  2 passed

16:00  🔴 RED    test_a_preset_answers_as_the_cli_shows_it
       GET /api/presets/{id} é show_preset; Passo 3 (e)
       AssertionError: assert (404, …) == (200, {'id' …})

16:00  🟢 GREEN  test_a_preset_answers_as_the_cli_shows_it  ·  3 passed

16:01  🔴 RED    test_creating_a_preset_answers_201_with_a_copy_of_the_default_that_is_not_default
       POST /api/presets {name} → 201 com a cópia do padrão, não padrão
       Passo 3 (e); L8
       KeyError: 'id' (a rota não existe)

16:01  🟢 GREEN  test_creating_a_preset_answers_201_with_a_copy_of_the_default_that_is_not_default  ·  4 passed

16:01  🔴 RED    test_creating_a_preset_from_another_copies_that_one
       POST /api/presets {name, from_id} copia aquele preset; Passo 3 (e)
       AssertionError: assert '' == 'Prefira trechos curtos.' (o PATCH ainda
       não existe, e a cópia sai sem as instruções)

16:01  🟢 GREEN  test_creating_a_preset_from_another_copies_that_one  ·  6 passed
       PATCH /api/presets/{id} entrou junto; from_id inexistente → 404
       preset_id verde de saída, pelo serviço

16:02  🟢 GREEN  test_changing_a_preset_answers_it_as_the_cli_changes_it  ·  14 passed
       verdes de saída: o PATCH entrou no GREEN anterior; todos os campos no
       formato da saída; {} , nome repetido, critério inexistente (levels),
       ideal fora da permitida, texto, null → 400 sem mudar o preset (L6)

16:02  🧬 MUTANTE from_id ignorado na criação  ·  morto
       2 vermelhos; desfeito

16:02  🧬 MUTANTE level não renomeado para levels  ·  morto
       2 vermelhos ({} e critério inexistente); desfeito, 14 passed

16:02  🔴 RED    test_making_a_preset_the_default_answers_it_and_the_previous_one_stops_being
       POST /api/presets/{id}/set-default → 200; o padrão anterior deixa de ser
       Passo 3 (e)
       KeyError: 'is_default' (a rota não existe)

16:02  🟢 GREEN  test_making_a_preset_the_default_answers_it_and_the_previous_one_stops_being  ·  15 passed

16:03  🔴 RED    test_deleting_a_preset_answers_200_with_it_deleted
       DELETE /api/presets/{id} → 200 {id, deleted: true}; o padrão → 409
       default_preset; Passo 3 (e); L8
       AssertionError: assert (405, …) == (200, {'id' …, 'deleted': True}, 404)

16:03  🟢 GREEN  test_deleting_a_preset_answers_200_with_it_deleted  ·  17 passed
       o 409 default_preset do padrão, pelo serviço

16:03  🧬 MUTANTE set-default sem efeito  ·  morto
       vermelho; desfeito, 17 passed

16:03  🔴 RED    test_the_team_answers_as_the_cli_lists_it_by_email
       GET /api/members → {items: list_members}, por e-mail; Passo 3 (f)
       AssertionError: assert (404, …) == (200, {'items' …}, […])

16:03  🟢 GREEN  test_the_team_answers_as_the_cli_lists_it_by_email  ·  1 passed

16:03  🔴 RED    test_letting_an_email_in_answers_201_with_the_member_in_lower_case
       POST /api/members {email, role} → 201, e-mail em minúsculas
       Passo 3 (f); L4, L8
       KeyError: 'email' (a rota ainda não aceita POST)

16:04  🟢 GREEN  test_letting_an_email_in_answers_201_with_the_member_in_lower_case  ·  2 passed

16:04  🟢 GREEN  test_a_refused_member_is_invalid_argument_without_echo_and_the_team_stays  ·  6 passed
       verdes de saída, pelo serviço e pelo corpo: repetido, malformado sem eco,
       papel fora com choices, sem papel

16:04  🔴 RED    test_changing_a_role_answers_the_member_with_the_new_role
       POST /api/members/set-role {email, role} → 200 com o papel novo
       Passo 3 (f); L4
       KeyError: 'role' (a rota não existe)

16:04  🟢 GREEN  test_changing_a_role_answers_the_member_with_the_new_role  ·  7 passed

16:04  🔴 RED    test_taking_a_member_off_answers_it_removed
       POST /api/members/remove {email} → 200 {email, removed: true}
       Passo 3 (f); L4
       AssertionError: assert (404, …) == (200, {'email' …, 'removed': True}, […])

16:04  🟢 GREEN  test_taking_a_member_off_answers_it_removed  ·  8 passed

16:04  🟢 GREEN  test_the_last_administrator_is_kept  ·  12 passed
       verdes de saída, pelo serviço: rebaixar ou remover o último admin → 409
       last_admin sem mudar a equipe; e-mail fora → 404 sem eco

16:05  ✅ PASSO 3/5 — Administração  ·  +47 testes  ·  suíte API 224

--- Passo 4: Permissões ---

16:07  🟢 GREEN  test_the_table_has_every_route_of_the_app_and_nothing_more  ·  8 passed
       verdes de saída: a estrutura (ROUTERS no laço com a identidade e
       require(admin) nos routers de administração) entrou nos passos 1–3;
       as mutações abaixo provam que cada teste a segura
       tabela = rotas de ROUTERS + /api/me; PUT …/segments → 404; 401 em
       toda linha; assistente 403 sem efeito (id existente e inexistente);
       assistente e admin passam; app.routes só com os routers de ROUTERS

16:07  🧬 MUTANTE identidade fora da inclusão dos routers  ·  morto
       a varredura 401 (test_permissions e test_auth) vermelha; desfeito

16:07  🧬 MUTANTE require(admin) fora do router de members  ·  morto
       os dois 403 sem efeito vermelhos; desfeito

16:07  🧬 MUTANTE rota include_in_schema=False num router fora de ROUTERS  ·  morto
       a contagem de app.routes vermelha; desfeito

16:07  🧬 MUTANTE rota oculta num router de admin sem linha na tabela  ·  morto
       a igualdade da tabela vermelha; desfeito, 35 passed

16:08  🔧 REFAC  test_auth: a varredura 401 lê as APIRoute de ROUTERS, não o OpenAPI
       L1; 35 passed em test_auth + test_permissions

16:08  ✅ PASSO 4/5 — Permissões  ·  +8 testes  ·  suíte API 232

--- Passo 5: Documentação ---

16:11  📝 DOCS   docs/api.md, CHANGELOG, arquitetura §4 e fluxo 5.3, README, ADR-0021
       rotas com corpo, status, erros e papel; segredos só pelo corpo; sem
       path (L3); e-mail fora da URL (L4); config_not_writable no Compose e a
       CLI no host (L5); campo desconhecido → 400 (L7); ADR-0021 no índice;
       ADR-0019 e ADR-0020 intocadas; só e-mails @exemplo.org

16:11  ✅ PASSO 5/5 — Documentação  ·  +0 testes  ·  suíte 1504 (monorepo)

16:11  🏁 FIM    Rodada 1  ·  5/5 passos  ·  API 118 → 232  ·  monorepo 1504 passed
       ruff check, ruff format --check e mypy limpos; nenhum processo órfão;
       sem commit (override do orquestrador)

## Rodada 1 · QA

16:12  📊 SUÍTE  1504 passed  ·  0 failed  (monorepo, uv run pytest -q)
       API 232 passed; ruff check, ruff format --check e mypy limpos

16:13  🧬 MUTAÇÕES · cópia no scratchpad, 15 linhas de produção  ·  15 de 15 mortas
       ☠️  identidade fora da inclusão dos ROUTERS            test_permissions/test_auth
       ☠️  require("admin") fora de presets                   test_permissions
       ☠️  require("admin") fora de settings                  test_permissions
       ☠️  extra_forbidden sem tratamento (L7)                 suíte da API
       ☠️  path mantido nas transições (L3)                   test_cuts_routes
       ☠️  path mantido na lista de exportações (L3)          test_renders_routes
       ☠️  ?status ignorado na lista de cortes                test_cuts_routes
       ☠️  restore ligado a discard_cut                       test_cuts_routes
       ☠️  argument do segredo sem virar value (L5)           test_settings_routes
       ☠️  set-role chamando add_member                       test_members_routes
       ☠️  remove sem efeito                                  test_members_routes
       ☠️  DELETE de preset sem efeito                        test_presets_routes
       ☠️  size da legenda int em vez de StrictInt            test_cuts_routes
       ☠️  filename do download descartado                    test_renders_routes
       ☠️  null aceito em Changes                             suíte da API

16:13  🔎 QA     passo 1/5 — Cortes  ·  ✅ PASS
       rotas finas sobre o serviço, path tirado, PATCH {} 400, sem eco

16:13  🔎 QA     passo 2/5 — Exportações  ·  ✅ PASS
       202 launched_task com harmless_tasks em todo POST; sem path

16:14  🔎 QA     passo 3/5 — Administração  ·  ✅ PASS
       pela matriz; achado fora dela: 409 config_not_writable devolve
       o caminho da pasta de configuração (mensagem e details.path)

16:14  🔎 QA     passo 4/5 — Permissões  ·  ✅ PASS
       tabela = ROUTERS + /api/me; 401, 403 sem efeito, contagem L1

16:15  🔎 QA     passo 5/5 — Documentação  ·  ✅ PASS
       api.md, CHANGELOG, arquitetura, README e ADR-0021 no índice;
       ADR-0019/0020 intocadas; a ADR-0021 afirma que a web nunca vê
       a estrutura de pastas, o que o 409 acima desmente

## Rodada 2 · implementador

16:16  📝 PLANO   decisão do orquestrador: 409 config_not_writable sem
       caminho na rota (ADR-0021); linha nas Decisões técnicas

--- Passo 3: Administração (reaberto: Observação da Rodada 1) ---

16:17  🔴 RED    test_a_secret_into_a_read_only_folder_never_shows_the_configuration_folder
       PUT llm-key/youtube-cookies com a pasta só leitura: 409 sem
       str(config_dir), sem "/config" e sem details
       decisão do orquestrador, Rodada 2; ADR-0021
       assert (409, True, True) == (409, False, False)

16:17  🟢 GREEN  test_a_secret_into_a_read_only_folder_never_shows_the_configuration_folder  ·  20 passed

16:18  🧬 EXIGE   rota repassando config_not_writable do serviço sem
       limpar o caminho  ·  vermelha
       ☠️  2 failed (llm-key, youtube-cookies), desfeita na hora

16:19  📝 DOCS    docs/api.md e ADR-0021: 409 sem caminho nem details

16:19  ✅ PASSO 3/5 — Administração  ·  +2 testes  ·  suíte 1506
       ruff check, ruff format --check e mypy limpos

## Rodada 2 · QA

16:20  📊 SUÍTE  monorepo 1506 passed  ·  0 failed
       API 234 passed; ruff check, ruff format --check e mypy limpos

16:21  🧬 MUTAÇÕES · cópia no scratchpad, settings._stored  ·  4 de 4 mortas
       ☠️  config_not_writable do serviço repassado (raise)   2 testes
       ☠️  mensagem genérica com details do serviço          2 testes
       ☠️  mensagem do serviço (com caminho), sem details    2 testes
       ☠️  code trocado para internal_error                  4 testes

16:22  🔎 QA     varredura de caminho do servidor nas respostas
       core: só config.py:80-84 põe caminho em erro; vídeo e exportação
       ausentes saem sem caminho; path tirado de cortes e exportações;
       Exception → UNEXPECTED genérico; nada mais encontrado

16:23  🔎 QA     passo 3/5 — Administração  ·  ✅ PASS
       409 config_not_writable com a mensagem da L5b, sem details e sem
       caminho; a mutação que repassa o erro do serviço fica vermelha

16:23  🔎 QA     passos 1, 2, 4, 5  ·  ✅ PASS
       sem mudança desde a Rodada 1; suíte e checagens verdes
