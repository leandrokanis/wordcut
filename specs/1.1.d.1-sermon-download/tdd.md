## Plano de QA

baseline_commit: 53fc42b7dd4812ece1a0b251462933971f5584da

04:43  📐 BARRA   cópia idêntica, sem sobrescrever, sem temporário sobrando
       test_files.py com arquivos reais em tmp_path; read_bytes() ==, não
       só existência; dublê de shutil.copyfile que falha no meio

04:43  🧬 EXIGE   gravar direto no destino, sem laço de sufixo  ·  vermelha
       prova que o original sobrevive a um destino já ocupado

04:43  🧬 EXIGE   apagar o temporário só no sucesso  ·  vermelha
       sobreviver = pasta do usuário com lixo após falha de cópia

04:43  📐 BARRA   sermon_video: estado, not_found, vídeo ausente, nome
       test_sermon_video.py com SQLite real em wordcut_home, os quatro
       estados não processados parametrizados (saída 5)

04:43  🧬 EXIGE   aceitar qualquer estado no sermon_video  ·  vermelha
       sem isso uma pregação created baixaria o vídeo de outra rodada

04:43  🧬 EXIGE   folder_name trocado por title + ".mp4"  ·  vermelha
       prova a regra de caracteres proibidos do spec

04:43  📐 BARRA   CLI via main(argv) com chdir; JSON {path, bytes}
       path absoluto, nome legível, bytes == tamanho, segunda execução (2)

04:43  📐 BARRA   FR-005: download com a trava segurada por outro processo
       fixture lock_owner da raiz; saída 0 é a prova

04:43  ⚠️ LACUNA  posição do sufixo " (2)" não decidida
       fechado em D1: antes da extensão. Sem isso, 1d/3d ficam PARCIAL

04:43  ⚠️ LACUNA  -o arquivo existente: sobrescreve ou sufixa?
       fechado em D2: sufixa (FR-003 não abre exceção)

04:43  ⚠️ LACUNA  -o terminado em "/" inexistente: pasta ou arquivo?
       fechado em D3: pasta, criada; nome legível dentro

04:43  ⚠️ LACUNA  os.replace sobrescreve se o destino surgir entre a
       checagem e a troca (TOCTOU) — contradiz "sem sobrescrever"
       recomendado os.link(temp, final) + unlink, ou open(..., "x");
       race não é testável de forma determinística: não vira FAIL

04:43  ⚠️ LACUNA  video_path nulo em pregação processed não previsto
       fechado em D4: mesmo internal_error do vídeo ausente

04:43  ⚠️ LACUNA  internal_error: plano não diz o que vai em details
       fechado em D4: só sermon_id; sem WORDCUT_HOME na saída

04:43  ⚠️ LACUNA  FR-005 sem linha na Verificação do plan.md
       coberto na matriz (2f, 3g); sem teste, passo 2/3 fica PARCIAL

04:43  ⚠️ LACUNA  formato da saída em texto não decidido
       fechado em D5: o caminho absoluto de destino

## Rodada 1 · implementador

04:46  --- Passo 1: Cópia segura ---

04:47  🔴 RED    test_copy_to_a_file_path_writes_identical_bytes_and_returns_that_absolute_path
       cópia para um arquivo grava os mesmos bytes e devolve o caminho absoluto
       matriz 1a; FR-001
       E   ModuleNotFoundError: No module named 'wordcut.files'

04:47  🟢 GREEN  test_copy_to_a_file_path_writes_identical_bytes_and_returns_that_absolute_path  ·  1 passed

04:47  🔴 RED    test_copy_creates_the_missing_folders_of_the_destination
       destino em pastas inexistentes: as pastas são criadas
       matriz 1b; cenário "destino escolhido"
       E   FileNotFoundError: [Errno 2] No such file or directory: '.../x/y/pregacao.mp4'

04:47  🟢 GREEN  test_copy_creates_the_missing_folders_of_the_destination  ·  2 passed

04:47  🔴 RED    test_copy_to_an_existing_folder_writes_the_suggested_name_inside_it
       pasta existente como destino: grava pasta/<nome sugerido>; o nome
       sugerido chega pelo terceiro argumento da assinatura
       matriz 1c; borda "-o pasta existente"
       E   IsADirectoryError: [Errno 21] Is a directory: '.../downloads'

04:47  🟢 GREEN  test_copy_to_an_existing_folder_writes_the_suggested_name_inside_it  ·  3 passed

04:47  🔴 RED    test_existing_destination_is_kept_and_the_copy_gets_2_before_the_extension
       destino ocupado: o original fica intacto e a cópia vira "Nome (2).mp4"
       matriz 1d; FR-003; D1, D2
       E   At index 0 diff: '2026-10-18 - Culto de domingo.mp4' != '... (2).mp4'

04:47  🟢 GREEN  test_existing_destination_is_kept_and_the_copy_gets_2_before_the_extension  ·  4 passed

04:48  ⚪ GUARDA test_with_2_taken_too_the_copy_gets_3_and_both_earlier_files_are_kept
       segundo nível do sufixo; passou sem produção nova (o laço do passo
       anterior já cobre); fica como guarda da mutação "sem laço de sufixo"
       matriz 1d; D1

04:48  ⚪ GUARDA test_after_a_copy_the_destination_folder_holds_only_the_copied_file
       após sucesso só o arquivo final na pasta; passou sem produção nova
       (o finally já apaga o temporário); guarda da mutação "não apagar"
       matriz 1f; D6

04:48  🔴 RED    test_a_copy_that_fails_midway_leaves_neither_the_final_name_nor_a_temporary_file
       dublê de shutil.copyfile grava metade e lança: a exceção propaga, o
       nome final não existe e o temporário não sobra
       matriz 1e; D6; decisão "nunca arquivo pela metade com o nome final"
       E   AssertionError: assert [PosixPath('/...2998e8.part')] == []

04:48  🟢 GREEN  test_a_copy_that_fails_midway_leaves_neither_the_final_name_nor_a_temporary_file  ·  7 passed

04:48  🔴 RED    test_a_relative_destination_is_resolved_against_the_current_folder
       destino relativo vale a partir da pasta atual; o retorno é absoluto
       matriz 1g; decisão "destino relativo" do plano
       E   At index 0 diff: PosixPath('sub/pregacao.mp4') != PosixPath('/tmp/.../current/sub/pregacao.mp4')

04:48  🟢 GREEN  test_a_relative_destination_is_resolved_against_the_current_folder  ·  8 passed

04:48  🔴 RED    test_a_missing_destination_ending_in_a_separator_is_a_folder_created_with_the_name_inside
       "-o saida/" inexistente é pasta: criada, com o nome legível dentro;
       o destino passa a chegar como texto para o separador final valer
       D3
       E   AttributeError: 'str' object has no attribute 'absolute'

04:48  🟢 GREEN  test_a_missing_destination_ending_in_a_separator_is_a_folder_created_with_the_name_inside  ·  9 passed

04:49  🔧 REFACTOR  _linked em while/next, sem AssertionError de código morto
       9 passed

04:49  🧬 MUTAÇÃO  troca direta no destino, sem laço de sufixo  ·  2 failed
04:49  🧬 MUTAÇÃO  mkdir(parents=True) removido  ·  4 failed
04:49  🧬 MUTAÇÃO  temporário não apagado  ·  2 failed
04:49  🧬 MUTAÇÃO  cópia direto no nome final, sem temporário  ·  1 failed (1e)

04:49  ✅ PASSO 1/4 — Cópia segura  ·  +9 testes  ·  suíte 481

04:49  --- Passo 2: Serviço ---

04:49  🔴 RED    test_video_of_a_processed_sermon_is_its_file_with_the_readable_name
       pregação processed: caminho absoluto sob WORDCUT_HOME e nome
       "2026-10-18 - Culto de domingo.mp4"
       matriz 2a; FR-002
       E   ImportError: cannot import name 'SermonVideo' from 'wordcut.service.sermons'

04:49  🟢 GREEN  test_video_of_a_processed_sermon_is_its_file_with_the_readable_name  ·  1 passed

04:50  🔴 RED    test_a_sermon_not_processed_has_no_video_to_download[created|trimmed|processing|failed]
       os quatro estados não processados falham com sermon_not_processed,
       saída 5
       matriz 2c; FR-004; cenário "pregação não processada"
       E       AssertionError  (x4, do assert de video_path; nenhum WordcutError)

04:50  🟢 GREEN  test_a_sermon_not_processed_has_no_video_to_download  ·  5 passed

04:50  🔴 RED    test_a_processed_sermon_whose_video_left_the_disk_is_an_internal_error_without_the_data_folder
       vídeo apagado do disco: internal_error "Vídeo da pregação N não
       encontrado." com details só {sermon_id}; nada de WORDCUT_HOME
       matriz 2e; borda "vídeo ausente"; D4
       E       Failed: DID NOT RAISE WordcutError

04:50  🟢 GREEN  test_a_processed_sermon_whose_video_left_the_disk_is_an_internal_error_without_the_data_folder  ·  6 passed

04:50  🔴 RED    test_a_processed_sermon_without_a_video_path_is_the_same_internal_error
       video_path nulo numa pregação processed: o mesmo internal_error,
       details só {sermon_id}
       matriz 2e; D4 (decisão do orquestrador)
       E       TypeError: unsupported operand type(s) for /: 'PosixPath' and 'NoneType'

04:50  🟢 GREEN  test_a_processed_sermon_without_a_video_path_is_the_same_internal_error  ·  7 passed

04:50  ⚪ GUARDA test_video_of_a_missing_sermon_is_not_found
       ID inexistente → not_found (3); passou sem produção nova (_existing)
       matriz 2d; borda "ID inexistente"

04:50  ⚪ GUARDA test_characters_forbidden_in_file_names_are_left_out_of_the_readable_name
       /\:*?"<>| saem do nome sugerido; passou sem produção nova
       (folder_name); guarda da mutação title + ".mp4"
       matriz 2b; borda "caracteres proibidos"

04:50  ⚪ GUARDA test_video_is_found_while_another_process_holds_the_processing_lock
       lock_owner segura a trava; sermon_video responde (um acquire daria
       busy); passou sem produção nova
       matriz 2f; FR-005 (decisão do orquestrador)

04:51  🔧 REFACTOR  _video_file extraído de sermon_video  ·  10 passed

04:51  🧬 MUTAÇÃO  aceitar qualquer estado  ·  4 failed
04:51  🧬 MUTAÇÃO  caminho sem home.root  ·  3 failed
04:51  🧬 MUTAÇÃO  folder_name trocado por title + ".mp4"  ·  2 failed
04:51  🧬 MUTAÇÃO  sem checar existência do arquivo  ·  1 failed (2e)

04:51  ✅ PASSO 2/4 — Serviço  ·  +10 testes  ·  suíte 491

04:51  --- Passo 3: CLI ---

04:52  🔴 RED    test_download_with_json_copies_the_video_to_the_current_folder_with_the_readable_name
       sermon download <id> --json na pasta atual vazia: saída 0, path
       absoluto "2026-10-18 - Culto de domingo.mp4", bytes idênticos e
       bytes == tamanho
       matriz 3a; cenário "baixar com nome legível"; FR-001, FR-002
       E       KeyError: 'path'  (a CLI respondeu invalid_argument: ação desconhecida)

04:52  🟢 GREEN  test_download_with_json_copies_the_video_to_the_current_folder_with_the_readable_name  ·  1 passed

04:52  🔴 RED    test_download_to_a_file_path_creates_its_folders_and_answers_the_absolute_path[relative|absolute]
       -o x/y/pregacao.mp4 (relativo e absoluto, pastas inexistentes): o
       arquivo vai a esse caminho e o path é absoluto
       matriz 3b; cenário "destino escolhido"
       E       KeyError: 'path'  (x2; -o é argumento não reconhecido)

04:52  🟢 GREEN  test_download_to_a_file_path_creates_its_folders_and_answers_the_absolute_path  ·  3 passed

04:52  🔴 RED    test_download_without_json_prints_only_the_absolute_path_of_the_copy
       sem --json: stdout é o caminho absoluto, stderr vazio
       matriz 3e; D5; docs/cli.md §7.5
       E       At index 1 diff: '\n' != '/tmp/.../here/2026-10-18 - Culto de domingo.mp4\n'

04:53  🟢 GREEN  test_download_without_json_prints_only_the_absolute_path_of_the_copy  ·  4 passed

04:53  ⚪ GUARDA test_download_to_an_existing_folder_writes_the_readable_name_inside_it
       -o pasta existente → pasta/<nome legível>; passou (regra do core)
       matriz 3c

04:53  ⚪ GUARDA test_a_second_download_gets_2_in_the_name_and_keeps_the_first_file
       segunda execução → "(2)", o primeiro arquivo fica intacto
       matriz 3d; FR-003

04:53  ⚪ GUARDA test_json_option_is_accepted_before_between_and_after_the_download_action
       --json antes, entre ou depois da ação dá o mesmo {path, bytes}
       matriz 3i

04:53  ⚪ GUARDA test_download_works_while_another_process_holds_the_processing_lock
       lock_owner segura a trava; download sai 0 com os bytes do vídeo
       matriz 3g; FR-005 (decisão do orquestrador)

04:53  ⚪ GUARDA test_download_of_a_sermon_not_processed_fails_with_sermon_not_processed_and_exit_5
       pregação created → sermon_not_processed, saída 5, nada na pasta
       matriz 3f; FR-004

04:53  ⚪ GUARDA test_download_of_a_missing_sermon_fails_with_not_found_and_exit_3
       matriz 3f; borda "ID inexistente"

04:53  ⚪ GUARDA test_download_of_a_non_numeric_id_is_a_usage_error_with_exit_2
       matriz 3f

04:53  ⚪ GUARDA test_download_of_a_sermon_whose_video_left_the_disk_is_the_service_internal_error
       saída 1, mensagem do serviço (não "Erro interno inesperado."), sem
       WORDCUT_HOME no stdout
       matriz 3f; D4

04:53  ⚪ GUARDA test_sermon_help_lists_download_and_download_help_shows_an_example
       matriz 3h

04:53  🧬 MUTAÇÃO  -o ignorado  ·  3 failed
04:53  🧬 MUTAÇÃO  path relativo  ·  8 failed
04:53  🧬 MUTAÇÃO  bytes fixo  ·  4 failed
04:53  🧬 MUTAÇÃO  texto sem o caminho  ·  1 failed (3e)

04:55  🔴 RED    test_sermon_help_lists_its_actions  (suíte completa)
       teste existente fixava "{create,list,show,trim,process}"; a ação nova
       muda a lista de propósito
       matriz 3h
       E       assert (0, False) == (0, True)

04:55  🔧 AJUSTE  lista do help com download; download entra no
       parametrize test_each_sermon_action_help_shows_an_example_ready_to_copy
       (test_sermon_command.py); o teste de help duplicado sai de
       test_sermon_download_command.py

04:55  🟢 GREEN  test_sermon_help_lists_its_actions  ·  506 passed

04:55  ✅ PASSO 3/4 — CLI  ·  +15 testes (14 no arquivo novo, +1 parâmetro em test_sermon_command.py)  ·  suíte 506

04:55  --- Passo 4: Documentação ---

04:55  📝 DOC    CHANGELOG [Não lançado] / Adicionado: sermon download;
       docs/cli.md §7.5 com pasta, sufixo, saída {path, bytes} e trava
       sem TDD: documentação

04:55  ✅ PASSO 4/4 — Documentação  ·  +0 testes  ·  suíte 506

04:56  ✅ FINAL  suíte 506 passed  ·  ruff check/format e mypy limpos  ·
       Verificação do plan.md marcada

## Rodada 1 · QA

05:00  📊 SUÍTE  506 passed  ·  0 failed
       33 nos 3 arquivos novos; ruff check, ruff format e mypy limpos

05:00  🧬 MUTAÇÕES · cópia, serviço e CLI (cópia no scratchpad)  ·  15 de 15 mortas
       ☠️  os.replace no destino, sem laço de sufixo        3 testes
       ☠️  mkdir(parents=True) removido                      6 testes
       ☠️  temporário apagado só no sucesso                  1 teste
       ☠️  cópia direto no nome final, sem temporário       17 testes
       ☠️  separador final ignorado (D3)                     1 teste
       ☠️  retorno sem absolute()                            8 testes
       ☠️  aceitar qualquer estado                           5 testes
       ☠️  caminho sem home.root                            13 testes
       ☠️  folder_name trocado por title + ".mp4"            9 testes
       ☠️  sem checar existência do vídeo                    2 testes
       ☠️  sermon_video toma a trava (FR-005)                2 testes
       ☠️  -o ignorado                                       3 testes
       ☠️  path relativo na resposta                         8 testes
       ☠️  bytes fixo                                        4 testes
       ☠️  texto sem o caminho                               1 teste

05:00  🔎 QA     passo 1/4 — Cópia segura  ·  ⚠️ PARCIAL
       os.link com EPERM/ENOTSUP/EXDEV propaga OSError (sondado com
       dublê): sem queda para open(final, "x") nem teste (files.py:58)

05:00  🔎 QA     passo 2/4 — Serviço  ·  ✅ PASS
       2a–2g cobertos; D4 com details só {sermon_id}; sem CLI no core

05:00  🔎 QA     passo 3/4 — CLI  ·  ✅ PASS
       3a–3i cobertos via main(argv); trava segurada por lock_owner

05:00  🔎 QA     passo 4/4 — Documentação  ·  ✅ PASS
       CHANGELOG em Adicionado; cli.md §7.5 documenta {path, bytes}

## Rodada 2 · implementador

05:01  🔴 RED    test_without_hard_links_the_copy_still_lands_with_identical_
       bytes_and_no_temporary_file[EPERM|ENOTSUP|EOPNOTSUPP|EXDEV]
       os.link recusado → a cópia cai para open(final, "x") com bytes
       idênticos e sem temporário na pasta
       qa.md Rodada 1, passo 1 PARCIAL (decisão do orquestrador)
       OSError: [Errno 18] Invalid cross-device link  ·  4 failed

05:01  🟢 GREEN  test_without_hard_links_the_copy_still_lands_with_identical_
       bytes_and_no_temporary_file[4 errno]  ·  13 passed

05:01  🔴 RED    test_without_hard_links_an_existing_destination_is_kept_and_
       the_copy_gets_2[4 errno]
       sem hard link, destino existente → "Nome (2).mp4", original intacto
       qa.md Rodada 1, passo 1 PARCIAL (sufixo na queda)
       passou na 1ª execução: o open(final, "x") da fatia anterior já dá
       FileExistsError. Prova pela mutação open("wb") → AssertionError
       '... domingo.mp4' != '... domingo (2).mp4'  ·  4 failed

05:01  🟢 GREEN  test_without_hard_links_an_existing_destination_is_kept_and_
       the_copy_gets_2[4 errno]  ·  17 passed  (mutação desfeita)

05:02  🔴 RED    test_another_link_error_propagates_and_leaves_the_destination_
       folder_empty
       os.link com outro errno (EIO) → OSError propaga, pasta vazia
       barra da Rodada 2: "outros OSError continuam propagando"
       passou na 1ª execução (o filtro de errno já existe). Prova pela
       mutação "queda para qualquer OSError" → Failed: DID NOT RAISE
       OSError  ·  1 failed

05:02  🟢 GREEN  test_another_link_error_propagates_and_leaves_the_destination_
       folder_empty  ·  18 passed  (mutação desfeita)

05:02  🔴 RED    test_without_hard_links_a_copy_that_fails_midway_leaves_
       neither_the_final_name_nor_a_temporary_file
       sem hard link, cópia que falha no meio → nem nome final pela metade
       nem temporário na pasta
       plan.md "nunca deixa arquivo pela metade com o nome final"; qa.md D6
       AssertionError: assert [PosixPath('/...regacao.mp4')] == []

05:02  🟢 GREEN  test_without_hard_links_a_failed_copy_leaves_no_final_name_
       and_no_temporary_file  ·  19 passed
       (o RED acima, renomeado para caber nas 100 colunas do ruff)

05:03  ♻️  REFACTOR  arquivo fechado antes do unlink; _linked → _placed;
       docstrings da queda  ·  19 passed

05:03  ✅ PASSO 1/4 — Cópia segura (reaberto)  ·  +10 testes  ·  suíte 516

05:03  ✅ FINAL  suíte 516 passed  ·  ruff check/format e mypy limpos  ·
       plan.md: Contexto de código com a assinatura real; decisão "Queda
       sem hard link" na tabela

## Rodada 2 · QA

05:05  📊 SUÍTE  516 passed  ·  0 failed
       issue: 43 passed (test_files 19, test_sermon_video, download cmd);
       ruff check, ruff format --check e mypy limpos

05:05  🧬 MUTAÇÕES · queda sem hard link (cópia no scratchpad)  ·  11 de 11
       ☠️  sem queda (todo OSError do link propaga)            9 testes
       ☠️  queda para qualquer OSError (sem filtro de errno)   1 teste
       ☠️  open("wb") no lugar de open("xb")                   4 testes
       ☠️  nome final não apagado quando a cópia falha         1 teste
       ☠️  EXDEV fora do conjunto                              3 testes
       ☠️  EPERM fora do conjunto                              3 testes
       ☠️  ENOTSUP/EOPNOTSUPP fora do conjunto                 4 testes
       ☠️  temporário não apagado no fim                       8 testes
       ☠️  cópia truncada na queda                             9 testes
       ☠️  open("xb") dentro do try (apagaria o existente)     4 testes
       ☠️  FileExistsError da queda não tenta o sufixo         6 testes

05:05  🧬 MUTAÇÕES · exigidas na matriz, passo 1 (regressão)  ·  4 de 4
       ☠️  mkdir(parents=True) removido                       10 testes
       ☠️  laço de sufixo trocado por só o destino             6 testes
       ☠️  gravação direta no nome final, sem temporário       9 testes
       ☠️  os.replace no lugar de os.link                      8 testes

05:05  🔎 QA     passo 1/4 — Cópia segura  ·  ✅ PASS
       queda EPERM/ENOTSUP/EOPNOTSUPP/EXDEV → open(final, "x") + cópia,
       sufixo, sem temporário; EIO propaga; assinatura real no plan.md

05:05  🔎 QA     passo 2/4 — Serviço  ·  ✅ PASS
       sem mudança desde a Rodada 1; suíte verde

05:05  🔎 QA     passo 3/4 — CLI  ·  ✅ PASS
       sem mudança desde a Rodada 1; suíte verde

05:05  🔎 QA     passo 4/4 — Documentação  ·  ✅ PASS
       sem mudança desde a Rodada 1
