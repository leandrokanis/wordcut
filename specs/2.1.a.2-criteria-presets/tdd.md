## Plano de QA

baseline_commit: aa687faf634cf2911d54c553d19ea62ad5316687

06:23  📐 BARRA   catálogo real: 11 IDs, tipos e níveis padrão exatos
       test_criteria_catalog.py carrega o pacote, não um dublê

06:23  📐 BARRA   texto teológico só de sugerir-cortes.md + frases do protótipo
       QA compara descrições e frases; sem exemplos.md, sem critério novo

06:23  📐 BARRA   instalação nova: um "Padrão" com os valores da spec
       serviço sobre SQLite real; níveis comparados com catalog()

06:24  📐 BARRA   nenhum texto de prompt em stdout/stderr da CLI
       busca das 6 frases de nível e de "Stone-Campbell" em toda saída

06:24  📐 BARRA   build_prompt: nível do preset entra, os outros dois não
       fragmentos lidos de catalog(), não strings copiadas no teste

06:24  📐 BARRA   critério novo/removido pela linha gravada no banco
       levels inserido por SQL sem um ID e com um ID desconhecido

06:24  🧬 EXIGE   build_prompt usando sempre default_level  ·  vermelha
       prova que o nível do preset chega ao prompt

06:24  🧬 EXIGE   build_prompt ignorando instructions  ·  vermelha
       prova 2.1.a.3 (instruções adicionais no prompt)

06:24  🧬 EXIGE   leitura sem completar IDs ausentes  ·  vermelha
       prova FR-006, critério novo com nível padrão

06:24  🧬 EXIGE   leitura sem descartar IDs desconhecidos  ·  vermelha
       prova FR-006, critério removido ignorado

06:25  🧬 EXIGE   delete_preset sem checar is_default  ·  vermelha
       prova default_preset, saída 5

06:25  🧬 EXIGE   set_default sem desmarcar o anterior  ·  vermelha
       prova exatamente um padrão (índice parcial ou contagem)

06:25  🧬 EXIGE   create copiando a fábrica em vez do padrão atual  ·  vermelha
       prova "copia do padrão" depois de o padrão ter sido editado

06:25  🧬 EXIGE   checagem "ideal dentro do permitido" removida  ·  vermelha
       inclusive quando só a faixa permitida muda

06:25  🧬 EXIGE   min <= max trocado por min < max  ·  vermelha
       60-60 tem de ser aceito; se sobreviver, a fronteira não é testada

06:25  🧬 EXIGE   limite de instruções 4000 com > trocado por >=  ·  vermelha
       4000 aceito, 4001 recusado

06:25  🧬 EXIGE   validação dos três níveis do catálogo removida  ·  vermelha
       diretório de teste com critério sem "## strict"

06:25  🧬 EXIGE   criteria list incluindo fragments no item  ·  vermelha
       prova FR-002 e constituição §I

06:26  ⚠️ LACUNA  bônus de sugerir-cortes.md sem destino no plano
       protótipo os põe nas instruções; spec quer instruções vazias.
       Sem os bônus no base.md, conteúdo da fonte some: passo 1 PARCIAL

06:26  ⚠️ LACUNA  salvaguardas de colagem/reordenação fora do base.md
       plano não as lista; ficam no base ou no bloco de edição do
       build_prompt (reorder ligado). Ausentes → passos 1/3 PARCIAL

06:26  ⚠️ LACUNA  números do formato no base.md duplicam o preset
       40–75/55–65 fixos no base contradizem preset editado → FAIL do
       build_prompt (c). Vêm só do preset

06:26  ⚠️ LACUNA  gancho (3 s), ideias por pregação (3–5) e as chaves
       autônomo/fechamento/limpo do protótipo não estão no preset da
       spec. Barra segue a spec: ficam como texto fixo do base.md

06:27  ⚠️ LACUNA  "Padrão" semeado na migração com níveis em JSON
       duplica default_level dos .md e diverge no primeiro ajuste.
       Recomendado semear levels '{}' e deixar FR-006 completar

06:27  ⚠️ LACUNA  default_preset_id do settings show sem passo dono
       consta no Contexto, não na Ordem; testes de 2.1.a.1 afirmam
       None e vão quebrar. Cobrado no passo 3 (k)

06:27  ⚠️ LACUNA  catalog() sem diretório injetável
       sem ele o caso "falta de nível" não tem teste negativo;
       passo 1 (d) fica PARCIAL

06:27  ⚠️ LACUNA  forma do JSON do preset não decidida
       durações como par [min,max] ou {min,max}; barra exige os nomes
       da entidade da spec e a forma fixada em teste e em cli.md §11.3

06:28  ⚠️ LACUNA  bordas não decididas no plano
       update sem campos, arquivo de instruções inexistente, nome
       vazio, --level repetido. Barra: invalid_argument (2), sem eco
       do valor (ADR-0015); --level repetido, o último vale

06:28  ⚠️ LACUNA  texto teológico precisa de revisão humana
       QA prova procedência, não doutrina; o PASS não valida o texto.
       Revisão por pessoa qualificada antes do merge (§I)

## Rodada 1 · implementador

06:28  📝 DECISÃO decisões 1–10 do orquestrador registradas no plan.md
       (lacunas do QA); texto teológico pendente de revisão humana

06:28  🔴 RED    test_the_packaged_catalog_has_the_eight_filters_and_three_values_with_their_defaults
       catalog() real: 11 IDs, tipos e níveis padrão na ordem da fonte
       Passo 1 (a)(c); spec Pressupostos; protótipo
       ImportError: cannot import name 'catalog' from 'wordcut.criteria'

06:30  🟢 GREEN  test_the_packaged_catalog_has_the_eight_filters_and_three_values_with_their_defaults  ·  1 passed
       textos gerados verbatim de sugerir-cortes.md + frases LEVELS_F/V

06:30  🔴 RED    test_a_criterion_without_the_strict_level_is_a_programming_error_naming_its_file
       critério sem "## strict" num diretório de teste → CatalogError
       Passo 1 (d); spec borda "falta de nível é erro de programação"
       Failed: DID NOT RAISE CatalogError

06:30  🟢 GREEN  test_a_criterion_without_the_strict_level_is_a_programming_error_naming_its_file  ·  2 passed

06:30  🔴 RED    test_a_malformed_criterion_header_is_a_programming_error_naming_its_file
       type inválido, default_level inválido e ID repetido → CatalogError
       Passo 1 (d); decisão "validação do catálogo"
       Failed: DID NOT RAISE CatalogError (3 casos)

06:30  🟢 GREEN  test_a_malformed_criterion_header_is_a_programming_error_naming_its_file  ·  5 passed

06:31  🔴 RED    test_a_criterion_with_a_section_that_is_not_a_level_is_a_programming_error
       seção "## extreme" num critério → CatalogError
       Passo 1 (d); decisão "validação do catálogo"
       Failed: DID NOT RAISE CatalogError

06:31  🔴 RED    test_a_base_prompt_that_is_empty_or_lacks_a_slot_is_a_programming_error
       base.md vazio ou sem as vagas dos critérios e durações → CatalogError
       Passo 1 (e); decisão 3 (durações só do preset)
       Failed: DID NOT RAISE CatalogError (2 casos)

06:31  🟢 GREEN  test_a_criterion_with_a_section_that_is_not_a_level_is_a_programming_error  ·  8 passed

06:31  🟢 GREEN  test_a_base_prompt_that_is_empty_or_lacks_a_slot_is_a_programming_error  ·  8 passed

06:31  🟢 GREEN  test_every_packaged_criterion_has_a_name_and_a_distinct_text_for_each_level  ·  10 passed
       guarda de dados sobre os textos reais (sem produção nova); passo 1 (b)

06:31  🟢 GREEN  test_the_texts_ship_inside_the_package_next_to_the_module  ·  10 passed
       guarda de empacotamento (packages = ["src/wordcut"]); passo 1 (f)

06:31  🔴 RED    test_a_missing_option_text_is_a_programming_error_naming_its_file
       texto de opção ausente → CatalogError, não FileNotFoundError
       Passo 1 (d); decisão "validação do catálogo"
       FileNotFoundError: [Errno 2] No such file or directory: '.../options/reorder.md'

06:31  🟢 GREEN  test_a_missing_option_text_is_a_programming_error_naming_its_file  ·  11 passed

06:31  ✅ PASSO 1/5 — Catálogo  ·  +11 testes  ·  suíte 624
       textos: base.md (vagas de critérios e durações; bônus, gancho,
       autônomo, colagem, fechamento e limpo fixos), options/ (salvaguardas
       com reordenar; regra de "não/mas/se" ligada às palavras protegidas),
       11 critérios. Revisão humana qualificada do texto pendente

06:32  🔴 RED    test_a_new_installation_has_only_the_factory_default_preset
       banco novo: só o "Padrão", padrão, 40–75, 55–65, reordenar,
       "não, mas, se", instruções vazias, levels '{}' (decisão 5)
       Passo 2 (b); cenário "preset padrão de fábrica"
       ImportError: cannot import name 'presets' from 'wordcut.db'

06:32  🟢 GREEN  test_a_new_installation_has_only_the_factory_default_preset  ·  11 passed
       inclui test_db.py: banco novo na migração 0006

06:32  🔴 RED    test_an_inserted_preset_is_read_back_by_its_id_with_every_field
       repositório grava e relê todos os campos da entidade da spec
       Passo 2 (d); FR-003
       ImportError: cannot import name 'PresetFields' from 'wordcut.db.presets'

06:32  🟢 GREEN  test_an_inserted_preset_is_read_back_by_its_id_with_every_field  ·  2 passed

06:33  🔴 RED    test_an_updated_preset_is_read_back_with_the_new_fields_and_update_time
       update grava os campos editáveis e o updated_at
       Passo 2 (d); FR-003
       AttributeError: module 'wordcut.db.presets' has no attribute 'update'

06:33  🟢 GREEN  test_an_updated_preset_is_read_back_with_the_new_fields_and_update_time  ·  3 passed

06:33  🔴 RED    test_the_database_refuses_a_second_default_preset
       índice único parcial: segundo is_default = 1 recusado pelo SQLite
       Passo 2 (c); FR-005
       AttributeError: ... has no attribute 'set_default_flag'

06:33  🔴 RED    test_the_default_moves_once_the_previous_one_is_cleared
       desmarcar o anterior e marcar o novo deixa um só padrão
       Passo 2 (c); decisão "preset padrão"
       AttributeError: ... has no attribute 'set_default_flag'

06:33  🟢 GREEN  test_the_database_refuses_a_repeated_preset_name  ·  passou sem produção
       guarda do UNIQUE(name) já escrito na migração 0006; passo 2 (c)

06:33  🔴 RED    test_a_deleted_preset_is_no_longer_found
       delete remove a linha
       Passo 2 (d)
       AttributeError: module 'wordcut.db.presets' has no attribute 'delete'

06:33  🟢 GREEN  test_the_database_refuses_a_second_default_preset  ·  7 passed

06:33  🟢 GREEN  test_the_default_moves_once_the_previous_one_is_cleared  ·  7 passed

06:33  🟢 GREEN  test_a_deleted_preset_is_no_longer_found  ·  7 passed

06:33  🟢 GREEN  test_a_database_of_the_previous_version_gains_the_factory_preset_and_keeps_its_data  ·  passou sem produção
       guarda de migração 5 → 6 sem perder settings; passo 2 (a).
       0006_presets.sql sem BEGIN/COMMIT (grep vazio); passo 2 (e)

06:34  ✅ PASSO 2/5 — Presets no banco  ·  +8 testes  ·  suíte 632
       migração 0006 (UNIQUE(name), índice parcial is_default, "Padrão"
       com levels '{}'); db.presets sem regra de negócio

06:35  🔴 RED    test_a_new_installation_lists_the_factory_preset_with_every_criterion_at_its_default
       list_presets: "Padrão" com os 11 níveis padrão do catálogo e o JSON
       da decisão 8 (durações {min,max}, palavras em lista)
       Passo 3 (a)(b); cenário "preset padrão de fábrica"; FR-006
       ModuleNotFoundError: No module named 'wordcut.service.presets'

06:35  🟢 GREEN  test_a_new_installation_lists_the_factory_preset_with_every_criterion_at_its_default  ·  1 passed

06:35  🔴 RED    test_show_gives_the_same_preset_the_list_gives
       show_preset devolve o mesmo objeto da listagem
       Passo 3 (a); FR-004
       ImportError: cannot import name 'show_preset'

06:35  🔴 RED    test_showing_an_unknown_preset_is_not_found
       ID inexistente → not_found com details.preset_id
       Passo 3 (i)
       ImportError: cannot import name 'show_preset'

06:35  🟢 GREEN  test_show_gives_the_same_preset_the_list_gives  ·  3 passed

06:35  🟢 GREEN  test_showing_an_unknown_preset_is_not_found  ·  3 passed

06:35  🟢 GREEN  test_a_criterion_the_stored_preset_lacks_is_read_with_its_default_level  ·  passou sem produção
       FR-006 com levels gravado por SQL; a leitura pelo catálogo, escrita
       para o "Padrão" semeado com '{}', já completa. Passo 3 (g)

06:35  🟢 GREEN  test_a_criterion_removed_from_the_code_is_left_out_of_show_and_list  ·  passou sem produção
       FR-006: ID desconhecido gravado some de show e list. Passo 3 (g)

06:35  🔴 RED    test_a_created_preset_is_a_copy_of_the_default_that_is_not_the_default
       create_preset(nome) copia o padrão e nasce não padrão
       Passo 3 (c); cenário "criar e editar"
       ImportError: cannot import name 'create_preset'

06:36  🟢 GREEN  test_a_created_preset_is_a_copy_of_the_default_that_is_not_the_default  ·  6 passed

06:36  🔴 RED    test_an_update_changes_every_field_given_and_is_kept_after_reopening
       update_preset muda nome, níveis, durações, reordenar, palavras e
       instruções, com updated_at, e persiste ao reabrir
       Passo 3 (d); cenário "criar e editar"; FR-003
       ImportError: cannot import name 'update_preset'

06:36  🔴 RED    test_an_update_leaves_the_fields_not_given_as_they_were
       só os campos dados mudam
       Passo 3 (d)
       ImportError: cannot import name 'update_preset'

06:36  🟢 GREEN  test_an_update_changes_every_field_given_and_is_kept_after_reopening  ·  8 passed

06:36  🟢 GREEN  test_an_update_leaves_the_fields_not_given_as_they_were  ·  8 passed

06:36  🔴 RED    test_set_default_makes_the_preset_the_only_default
       set_default troca o padrão; exatamente um padrão depois
       Passo 3 (e); FR-005; cenário "escolher o padrão"
       ImportError: cannot import name 'default_preset'

06:36  🔴 RED    test_a_new_preset_copies_the_current_default_not_the_factory_one
       com o padrão trocado e editado, create copia o padrão atual
       Passo 3 (c); 🧬 "create copiando a fábrica"
       ImportError: cannot import name 'default_preset'

06:36  🔴 RED    test_a_new_preset_copies_the_preset_given_as_its_source
       from_id copia o indicado, que nasce não padrão
       Passo 3 (c); docs/cli.md §11.3 "--from"
       ImportError: cannot import name 'default_preset'

06:36  🟢 GREEN  test_set_default_makes_the_preset_the_only_default  ·  11 passed

06:36  🟢 GREEN  test_a_new_preset_copies_the_current_default_not_the_factory_one  ·  11 passed

06:36  🟢 GREEN  test_a_new_preset_copies_the_preset_given_as_its_source  ·  11 passed

06:36  🔴 RED    test_deleting_the_default_preset_is_refused_and_deletes_nothing
       delete do padrão → default_preset (saída 5), nada apagado
       Passo 3 (f); FR-005; 🧬 "delete_preset sem checar is_default"
       ImportError: cannot import name 'delete_preset'

06:36  🔴 RED    test_a_preset_that_is_not_the_default_is_deleted
       apagar um preset que não é o padrão funciona
       Passo 3 (f)
       ImportError: cannot import name 'delete_preset'

06:37  🟢 GREEN  test_deleting_the_default_preset_is_refused_and_deletes_nothing  ·  13 passed

06:37  🟢 GREEN  test_a_preset_that_is_not_the_default_is_deleted  ·  13 passed

06:37  🟢 GREEN  test_an_unknown_preset_is_not_found_in_every_action  ·  passou sem produção
       guarda: update, set-default, delete e create --from passam por
       _existing. Passo 3 (i)

06:37  🔴 RED    test_an_invalid_update_is_refused_naming_the_argument_and_changes_nothing
       update sem campos, critério/nível inexistente, nome repetido ou
       vazio, min > max, ideal fora do permitido (inclusive só uma faixa
       mudando) e instruções > 4000 → invalid_argument, nada muda
       Passo 3 (h); bordas da spec; decisão 9; 🧬 ideal/min≤max/4000
       12 failed: DID NOT RAISE / sqlite3.IntegrityError (nome repetido)

06:37  🔴 RED    test_an_unknown_level_lists_the_valid_levels_without_repeating_the_typed_one
       nível inválido → details.choices, mensagem sem o valor (ADR-0015)
       Passo 3 (h); docs/cli.md §5.3
       Failed: DID NOT RAISE WordcutError

06:37  🔴 RED    test_a_preset_created_with_a_repeated_or_blank_name_is_refused
       create com nome repetido ou vazio → invalid_argument name
       Passo 3 (h); borda "nome repetido"
       sqlite3.IntegrityError: UNIQUE constraint failed / DID NOT RAISE

06:38  🟢 GREEN  test_an_invalid_update_is_refused_naming_the_argument_and_changes_nothing  ·  35 passed

06:38  🟢 GREEN  test_an_unknown_level_lists_the_valid_levels_without_repeating_the_typed_one  ·  35 passed

06:38  🟢 GREEN  test_a_preset_created_with_a_repeated_or_blank_name_is_refused  ·  35 passed
       test_an_update_at_the_boundary_is_accepted (60-60, 55-65, 4000)
       segue verde e segura as mutações de fronteira

06:38  🔴 RED    test_protected_words_are_kept_without_blanks_empties_or_repetitions
       " não, mas,, se, não " → ["não", "mas", "se"]
       Passo 3 (j); decisão "palavras protegidas"
       ImportError: cannot import name 'parse_level'

06:38  🔴 RED    test_a_malformed_duration_is_refused_without_repeating_it
       "60", "a-b", negativa, decimal, vazio → invalid_argument sem eco;
       "60-75" → SecondsRange(60, 75)
       Passo 3 (h); decisão "durações"; ADR-0015
       ImportError: cannot import name 'parse_level'

06:38  🔴 RED    test_a_level_without_the_equals_sign_is_refused_without_repeating_it
       "criterio=nivel" lido; sem "=" → invalid_argument level sem eco
       Passo 3 (h); docs/cli.md §11.3
       ImportError: cannot import name 'parse_level'

06:38  🟢 GREEN  test_protected_words_are_kept_without_blanks_empties_or_repetitions  ·  45 passed

06:38  🟢 GREEN  test_a_malformed_duration_is_refused_without_repeating_it  ·  45 passed

06:38  🟢 GREEN  test_a_level_without_the_equals_sign_is_refused_without_repeating_it  ·  45 passed

06:38  🔴 RED    test_a_new_installation_has_only_the_whisperx_model_and_the_factory_preset_set
       settings show traz o ID do "Padrão" (antes None; teste de 2.1.a.1
       ajustado, decisão 6)
       Passo 3 (k)
       AssertionError: Differing items: {'default_preset_id': None} != {... 1}

06:38  🔴 RED    test_the_default_preset_shown_follows_set_default
       default_preset_id acompanha o set_default
       Passo 3 (k)
       AssertionError: assert None == 2

06:39  🟢 GREEN  test_a_new_installation_has_only_the_whisperx_model_and_the_factory_preset_set  ·  17 passed

06:39  🟢 GREEN  test_the_default_preset_shown_follows_set_default  ·  17 passed
       apps/cli/tests/test_settings_command.py ajustado de None para o ID
       semeado (1) no JSON e no texto; render sem o ramo "nenhum"

06:39  🔴 RED    test_the_prompt_has_the_piece_of_the_preset_level_of_each_criterion_and_no_other
       com níveis alternados, cada critério entra no nível do preset e os
       outros dois níveis ficam de fora; fragmentos lidos de catalog()
       Passo 3 build_prompt (b); FR-007; 🧬 "sempre default_level"
       ImportError: cannot import name 'build_prompt'

06:39  🟢 GREEN  test_the_prompt_has_the_piece_of_the_preset_level_of_each_criterion_and_no_other  ·  1 passed

06:39  🔴 RED    test_with_reorder_on_the_prompt_has_the_reordering_safeguards
       reordenar ligado → salvaguardas de sugerir-cortes.md (decisão 2)
       Passo 3 build_prompt (d)
       AssertionError: assert (False, False) == (True, False)

06:39  🔴 RED    test_with_reorder_off_the_prompt_forbids_reordering_instead
       reordenar desligado → texto diferente, sem as salvaguardas
       Passo 3 build_prompt (d)
       AssertionError: assert (False, False) == (False, True)

06:39  🔴 RED    test_the_prompt_lists_the_protected_words_of_the_preset
       palavras do preset no prompt; as de fábrica não, se foram trocadas
       Passo 3 build_prompt (d); decisão 2
       AssertionError: assert (False, False) == (True, False)

06:39  🔴 RED    test_the_instructions_come_labelled_as_the_administrator_s_after_the_criteria
       instruções rotuladas como do administrador, depois dos critérios
       Passo 3 build_prompt (e); 2.1.a.3; 🧬 "ignorando instructions"
       AssertionError: assert 1979 < -1

06:39  🟢 GREEN  test_without_instructions_the_prompt_has_no_empty_label  ·  passou sem produção
       guarda para quando o rótulo existir; passo 3 build_prompt (e)

06:39  🟢 GREEN  test_with_reorder_on_the_prompt_has_the_reordering_safeguards  ·  6 passed

06:39  🟢 GREEN  test_with_reorder_off_the_prompt_forbids_reordering_instead  ·  6 passed

06:39  🟢 GREEN  test_the_prompt_lists_the_protected_words_of_the_preset  ·  6 passed

06:39  🟢 GREEN  test_the_instructions_come_labelled_as_the_administrator_s_after_the_criteria  ·  6 passed

06:40  🟢 GREEN  test_the_prompt_has_every_line_of_the_base_prompt  ·  passou sem produção
       guarda: toda linha fixa de base.md no prompt; build_prompt (a)

06:40  🟢 GREEN  test_the_prompt_has_the_durations_of_the_preset_and_not_the_factory_ones  ·  passou sem produção
       guarda: 45–80/60–75 entram, 40–75/55–65 não; build_prompt (c)

06:40  🟢 GREEN  test_the_prompt_takes_a_missing_criterion_at_its_default_and_ignores_a_removed_one  ·  passou sem produção
       guarda FR-006 no prompt; build_prompt (f)

06:40  🟢 GREEN  test_building_the_prompt_reaches_no_network  ·  10 passed
       socket bloqueado; build_prompt (g)

06:41  🔁 REFACTOR service.presets: CRUD primeiro, build_prompt e
       leitores de argumento depois; imports ordenados  ·  688 passed
       mutações manuais conferidas e desfeitas: build_prompt sempre no
       default_level, create copiando a primeira linha, set_default sem
       desmarcar → vermelhas

06:41  ✅ PASSO 3/5 — Serviço  ·  +44 testes  ·  suíte 688
       inclui test_settings_service.py e test_settings_command.py
       ajustados para o default_preset_id real (decisão 6)

06:41  🔴 RED    test_criteria_list_gives_the_eight_filters_and_three_values_with_id_name_type_and_level
       criteria list --json → 8 filter + 3 value, só id, name, type,
       default_level
       Passo 4 (a); cenário "listar critérios"; FR-002; 🧬 "fragments"
       KeyError: 'items' (comando inexistente → erro de uso)

06:41  🟢 GREEN  test_criteria_list_gives_the_eight_filters_and_three_values_with_id_name_type_and_level  ·  1 passed

06:42  🔴 RED    test_preset_list_of_a_new_installation_gives_the_factory_default
       preset list --json → {"items": [...]} com o "Padrão" padrão
       Passo 4 (b); cenário "preset padrão de fábrica"
       KeyError: 'items'

06:42  🔴 RED    test_preset_show_gives_the_preset_with_the_fields_of_the_entity
       preset show --json → exatamente os campos da decisão 8
       Passo 4 (b); FR-004
       KeyError: 'items'

06:42  🟢 GREEN  test_preset_list_of_a_new_installation_gives_the_factory_default  ·  3 passed

06:42  🟢 GREEN  test_preset_show_gives_the_preset_with_the_fields_of_the_entity  ·  3 passed

06:42  🔴 RED    test_preset_create_copies_the_default
       preset create "Estudo bíblico" → cópia do padrão, não padrão
       Passo 4 (c); cenário "criar e editar"
       KeyError: 'name' (comando inexistente)

06:42  🔴 RED    test_preset_create_from_copies_the_preset_given
       --from copia o indicado
       Passo 4 (c); docs/cli.md §11.3
       KeyError: 'id'

06:42  🟢 GREEN  test_preset_create_copies_the_default  ·  5 passed

06:42  🟢 GREEN  test_preset_create_from_copies_the_preset_given  ·  5 passed
       update com --name, --level, durações, --reorder/--no-reorder e
       --protected-words chega junto, por ser o meio do teste do --from

06:43  🔴 RED    test_preset_update_changes_the_fields_given_and_show_reflects_them
       update com todas as opções de §11.3 e --instructions-file - pelo
       stdin redirecionado; show reflete; instruções sem brancos nas pontas
       Passo 4 (d); cenário "criar e editar"
       Valor inválido para --instructions-file (opção inexistente)

06:43  🔴 RED    test_preset_update_reads_the_instructions_from_a_file
       --instructions-file <arquivo> lê do arquivo
       Passo 4 (d)
       KeyError: 'instructions' (erro de uso)

06:43  🔴 RED    test_preset_update_with_a_missing_instructions_file_is_refused_without_naming_it
       arquivo inexistente → invalid_argument instructions_file, sem eco do
       caminho (ADR-0015; decisão 9)
       Passo 4 (g)
       AssertionError: details sem instructions_file

06:43  🟢 GREEN  test_preset_update_changes_the_fields_given_and_show_reflects_them  ·  8 passed

06:43  🟢 GREEN  test_preset_update_reads_the_instructions_from_a_file  ·  8 passed

06:43  🟢 GREEN  test_preset_update_with_a_missing_instructions_file_is_refused_without_naming_it  ·  8 passed
       service: instruções guardadas sem brancos nas pontas; limite de
       4000 conta o texto já aparado

06:43  🔴 RED    test_preset_set_default_changes_the_default_preset_of_settings_show
       preset set-default → settings show traz o novo default_preset_id
       Passo 4 (e); cenário "escolher o padrão"
       KeyError (comando inexistente → erro de uso)

06:43  🔴 RED    test_preset_delete_of_the_default_is_a_default_preset_error_with_exit_5
       preset delete do padrão → saída 5, default_preset
       Passo 4 (f); cenário "proteger o padrão"
       AssertionError: (2, 'invalid_argument') != (5, 'default_preset')

06:43  🔴 RED    test_preset_delete_of_another_preset_deletes_it
       delete de outro preset apaga e devolve {"id", "deleted": true}
       Passo 4 (f)
       KeyError (comando inexistente)

06:44  🟢 GREEN  test_preset_set_default_changes_the_default_preset_of_settings_show  ·  11 passed

06:44  🟢 GREEN  test_preset_delete_of_the_default_is_a_default_preset_error_with_exit_5  ·  11 passed

06:44  🟢 GREEN  test_preset_delete_of_another_preset_deletes_it  ·  11 passed

06:44  🟢 GREEN  test_an_invalid_update_is_a_usage_error_naming_the_option_without_the_typed_value  ·  passou sem produção
       guarda do contrato na CLI (json e texto): saída 2, details.argument,
       choices no nível, valor digitado ausente (ADR-0015). Primeira
       execução vermelha por erro no próprio teste (expectativa do modo
       texto), corrigido sem tocar produção. Passo 4 (g)

06:44  🟢 GREEN  test_renaming_to_the_name_of_another_preset_is_a_usage_error  ·  passou sem produção
       Passo 4 (g)

06:44  🟢 GREEN  test_an_unknown_preset_id_is_not_found_with_exit_3  ·  passou sem produção
       Passo 4 (g)

06:44  🟢 GREEN  test_a_preset_id_that_is_not_a_number_is_refused_without_repeating_it  ·  36 passed
       Passo 4 (g)

06:44  🔴 RED    test_help_lists_every_command (test_cli.py)
       criteria e preset registrados mudam a lista do --help
       Passo 4 (h)
       AssertionError: COMMANDS sem criteria e preset

06:44  🟢 GREEN  test_help_lists_every_command  ·  COMMANDS atualizado

06:44  🟢 GREEN  test_each_criteria_and_preset_action_help_says_it_is_for_the_administrator_with_an_example  ·  44 passed
       passou sem produção: help e exemplo escritos com os comandos.
       Passo 4 (h); docs/cli.md §3.5

06:45  🟢 GREEN  test_no_criteria_or_preset_output_carries_prompt_text  ·  61 passed
       passou sem produção: nenhum comando monta prompt. Frases de nível
       e "Stone-Campbell" fora de stdout/stderr, json e texto, sucesso e
       erro. Passo 4 (i); constituição §I

06:45  ✅ PASSO 4/5 — CLI  ·  +61 testes  ·  suíte 749
       criteria list; preset list/show/create/update/set-default/delete;
       --instructions-file arquivo ou -; test_cli.py COMMANDS atualizado

06:47  ✅ PASSO 5/5 — Documentação  ·  +0 testes  ·  suíte 749
       CHANGELOG (criteria list, preset, default_preset_id; texto pendente
       de revisão humana qualificada), arquitetura §4 (wordcut.criteria,
       presets 0006, service.presets, comandos), cli.md §11.2–§11.3 (JSON
       do preset, limite de 4000, bordas do update)

06:47  🏁 VERIFICAÇÃO  pytest 749 passed · ruff check/format limpos ·
       mypy sem erros · wheel do core leva os 16 textos. Sem commit
       (override do orquestrador)

## Rodada 1 · QA

06:48  📊 SUÍTE  749 passed  ·  0 failed
       ruff check limpo · ruff format --check limpo · mypy sem erros

06:49  🔎 QA     passo 1/5 — Catálogo  ·  ✅ PASS
       11 IDs/tipos/níveis exatos; prompt padrão montado = fonte sem
       "Processo", salvo a linha da decisão 2; frases de nível do protótipo

06:49  🔎 QA     procedência — linha a linha contra sugerir-cortes.md
       não literais: reorder.md:6 (decisão 2, aceita) e no_reorder.md:3
       (operacional, sem fonte; a matriz não decide essa linha). Sem
       exemplos.md, sem calibração, sem 40–75/55–65 no base.md

06:50  🔎 QA     passo 2/5 — Presets no banco  ·  ✅ PASS
       0006 sem BEGIN/COMMIT; índice parcial e UNIQUE(name) pelo SQLite;
       5 → 6 mantém settings

06:50  🔎 QA     passo 3/5 — Serviço e build_prompt  ·  ✅ PASS
       todas as bordas (h) com details.argument; 60-60 e 4000 aceitos

06:51  🔎 QA     passo 4/5 — CLI  ·  ⚠️ PARCIAL
       limite de instruções dá argument "instructions", e o parser chama
       instructions_file (4(g)); --level repetido sem teste

06:51  🔎 QA     passo 5/5 — Documentação  ·  ✅ PASS
       CHANGELOG, arquitetura §4 e cli.md §11.2–§11.3 coerentes

06:52  🧬 MUTAÇÕES · as 12 EXIGE + 10 extras + --level  ·  22 de 23 mortas
       ☠️  build_prompt sempre no default_level                1 teste
       ☠️  build_prompt ignorando instructions                 1 teste
       ☠️  leitura sem completar IDs ausentes                  1 teste
       ☠️  leitura sem descartar IDs desconhecidos             1 teste
       ☠️  delete_preset sem checar is_default                 1 teste
       ☠️  set_default sem desmarcar o anterior                1 teste
       ☠️  create copiando a primeira linha                    1 teste
       ☠️  checagem ideal dentro do permitido removida         1 teste
       ☠️  min <= max trocado por min < max                    1 teste
       ☠️  limite 4000 com > trocado por >=                    1 teste
       ☠️  validação dos três níveis removida                  1 teste
       ☠️  criteria list com fragments                         1 teste
       ☠️  extras: sem campos, dedup, nome, ideal cruzado, nível,
           critério, default_preset_id, rótulo, reorder, ordem   1 cada
       🚨  --level repetido: vale o primeiro      SOBREVIVEU — decisão 9
           sem teste; 61 passed

## Rodada 2 · implementador

06:54  🔁 REABRE  passo 4/5 — CLI (PARCIAL na Rodada 1)
       (1) details.argument "instructions_file" no limite e no update
       sem campos; (2) teste da decisão 9, --level repetido

06:54  🔴 RED    test_instructions_above_the_limit_are_refused_naming_the_option_of_the_parser
       4001 caracteres pelo stdin → argument com o nome do parser
       Passo 4 (g); docs/cli.md §5; achado (1) da Rodada 1
       At index 2 diff: {'argument': 'instructions'} != {'argument': 'instructions_file'}

06:56  🟢 GREEN  test_instructions_above_the_limit_are_refused_naming_the_option_of_the_parser  ·  62 passed
       a CLI traduz o argument do serviço (instructions → instructions_file)

06:57  🔴 RED    test_an_invalid_update_is_a_usage_error_naming_the_option_without_the_typed_value[json-no field]
       update sem campos → a lista de opções traz instructions_file
       Passo 4 (g); docs/cli.md §5 e §11.3; achado (1) da Rodada 1
       At index 1 diff: (... 'protected_words, instructions'}) != (...
       'protected_words, instructions_file'})

06:58  🟢 GREEN  test_an_invalid_update_is_a_usage_error_naming_the_option_without_the_typed_value[json-no field]  ·  62 passed
       a tradução renomeia cada nome da lista; o teste fixa a lista da
       CLI em vez de importar UPDATE_ARGUMENTS do serviço

06:58  🧹 REFACTOR  tradução do argument enxuta; 62 passed

06:59  🔴 RED    test_a_level_repeated_for_the_same_criterion_keeps_the_last
       --level allegory=lenient --level allegory=strict → show dá strict
       Passo 4 (d); decisão 9; docs/cli.md §11.3; achado (2) da Rodada 1
       comportamento já existia: passou sem produção nova (1 passed).
       RED provado pela mutação "vale o primeiro" (reversed na lista):
       AssertionError: assert 'lenient' == 'strict' · 1 failed, 62 passed
       mutação desfeita na hora

07:00  🟢 GREEN  test_a_level_repeated_for_the_same_criterion_keeps_the_last  ·  63 passed

07:01  ✅ PASSO 4/5 — CLI (reaberto)  ·  +2 testes  ·  suíte 751
       pytest 751 passed; ruff check/format e mypy limpos; sem commit
       (override da rodada)

## Rodada 2 · QA

07:02  📊 SUÍTE  751 passed  ·  0 failed
       ruff check, ruff format --check e mypy (68 arquivos) limpos

07:03  🧬 MUTAÇÕES · reabertura do passo 4  ·  5 de 5 mortas
       ☠️  --level repetido: vale o primeiro (reversed)       1 teste
       ☠️  sem tradução instructions → instructions_file      2 testes
       ☠️  tradução só de nome único, não da lista           1 teste
       ☠️  tradução descarta os outros details (choices)      1 teste
       ☠️  tradução sem o guarda de "argument" (not_found)    1 teste

07:04  🔎 QA     passo 4/5 — CLI  ·  ✅ PASS
       limite de 4000 e update sem campos dão instructions_file; decisão
       9 com teste que mata "vale o primeiro"; passos 1, 2, 3 e 5 sem
       mudança desde a Rodada 1
