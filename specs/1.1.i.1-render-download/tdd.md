## Plano de QA

baseline_commit: 593a41c0c4e1b851d3ff692f0f62c9172056bcee

12:00  📐 BARRA   render list: mais recente primeiro, empate por id DESC
       teste de serviço com banco real e 3 linhas (2 no mesmo segundo);
       a ordem é regra da issue, e o banco é onde ela vive

12:00  🧬 EXIGE   ORDER BY ... DESC → ASC  ·  vermelha
       prova que a lista não sai na ordem de inserção por acaso

12:00  🧬 EXIGE   remover o desempate id DESC  ·  vermelha
       a tarefa grava created_at em segundos; empate é caso real

12:00  ⚠️ LACUNA  plan.md manda inverter db/renders.of_cut
       of_cut alimenta cut show, que docs/cli.md:469 diz "mais antiga
       primeiro"; nenhum teste tem 2 exportações no cut show. Passo 1
       PARCIAL sem consulta separada e teste que proteja o cut show

12:00  🧬 EXIGE   of_cut com ORDER BY id DESC  ·  vermelha
       sobreviver = cut show invertido sem ninguém ver

12:00  ⚠️ LACUNA  plan.md cria show_render em service/renders.py
       já existe em service/rendering.py:85, usado por cut render;
       duplicar é divergência. Reusar; mover só com imports ajustados

12:00  📐 BARRA   nome legível = folder_name(data do culto, título do CORTE)
       teste com título do corte ≠ título da pregação e com / : ? no
       título; é o único jeito de distinguir as duas fontes

12:00  🧬 EXIGE   trocar o título do corte pelo da pregação  ·  vermelha
       prova que o nome vem do corte (FR-003)

12:00  ⚠️ LACUNA  render_video não pode reusar sermon_video
       sermon_video exige processed e devolve o vídeo da pregação;
       reusar dá o arquivo errado. FAIL no passo 1 se acontecer

12:00  📐 BARRA   download = mesmo contrato do sermon download (item 6)
       test_render_command.py no molde de test_sermon_download_command:
       pasta atual, -o arquivo, -o pasta, " (2)", só o caminho sem --json

12:00  🧬 EXIGE   copy_without_overwrite → shutil.copyfile  ·  vermelha
       prova o " (2)" e que o primeiro arquivo fica intacto

12:00  ⚠️ LACUNA  plano não define a saída do download nem os itens do list
       barra adota {path, bytes} (item 6) e o formato de shown_render;
       sem docs/cli.md §9 atualizado, passos 2 e 3 PARCIAL

12:00  📐 BARRA   arquivo ausente → internal_error {"render_id": N}
       teste de serviço e de CLI com o .mp4 apagado; stdout sem a
       string de WORDCUT_HOME; saída 1

12:00  🧬 EXIGE   remover a checagem is_file  ·  vermelha
       sem ela, o erro vira FileNotFoundError com o caminho interno

12:00  📐 BARRA   nenhum dos três comandos pega a trava
       fixture lock_owner (conftest.py:115) segurando a trava em outro
       processo; os três comandos respondem com saída 0

12:00  🧬 EXIGE   envolver download na trava de processamento  ·  vermelha
       prova FR "sem trava" no nível em que o usuário sente: a CLI

12:00  ⚠️ LACUNA  render show com arquivo ausente não está especificado
       barra conservadora: show devolve o registro sem abrir o arquivo,
       como show_render faz hoje; só download dá internal_error

12:00  ⚠️ LACUNA  path "absoluto" depende de WORDCUT_HOME absoluto
       shown_render não chama .absolute(); fora da barra desta issue,
       registrado para não virar falso PASS

## Rodada 1 · implementador

12:04  --- Passo 1: Serviço ---

12:05  🔴 RED    test_the_exports_of_a_cut_are_listed_the_most_recent_first
       duas exportações do corte: a lista traz a mais nova antes
       matriz 1a; FR-001; cenário "histórico do corte"
       E   ModuleNotFoundError: No module named 'wordcut.service.renders'

12:05  🟢 GREEN  test_the_exports_of_a_cut_are_listed_the_most_recent_first  ·  1 passed

12:05  🔴 RED    test_exports_recorded_in_the_same_second_are_listed_the_last_recorded_first
       duas exportações no mesmo segundo: a gravada por último vem antes
       matriz 1a; QA L2; decisão "empate por id DESC"
       E       assert [2, 3, 1] == [3, 2, 1]

12:05  🟢 GREEN  test_exports_recorded_in_the_same_second_are_listed_the_last_recorded_first  ·  2 passed

12:05  ⚪ GUARDA test_a_listed_export_is_given_as_render_show_gives_it_with_its_options_as_recorded
       item da lista = objeto do render show, path absoluto, opções como
       gravadas; passou sem produção nova (shown_render já monta o item)
       matriz 1b; QA D8

12:05  🔴 RED    test_an_export_shown_from_a_relative_data_folder_has_an_absolute_path
       WORDCUT_HOME relativo: render show devolve o path absoluto do arquivo
       matriz 1b; FR-002; QA L5 (decisão do orquestrador)
       E       AssertionError: assert 'data/media/cuts/1/1.mp4' == '/tmp/pytest-.../cuts/1/1.mp4'

12:05  🟢 GREEN  test_an_export_shown_from_a_relative_data_folder_has_an_absolute_path  ·  4 passed
       shown_render passa a dar (home.root / path).absolute(); vale também
       para cut show e cut render --wait

12:06  🔧 REFACTOR  teste do WORDCUT_HOME relativo sem o ID do corte fixo
       4 passed

12:06  ⚪ GUARDA test_listing_the_exports_of_a_cut_that_does_not_exist_is_not_found
       corte inexistente → not_found {"cut_id"}; passou porque o primeiro
       GREEN já chamava existing_cut; tirar a chamada deixa a lista vazia
       e o teste vermelho (conferido)
       matriz 1c; borda "corte inexistente"

12:06  ⚪ GUARDA test_a_cut_never_exported_lists_no_exports
       corte sem exportações → {"items": []}; passou sem produção nova
       matriz 1c

12:06  ⚪ GUARDA test_showing_an_export_that_does_not_exist_is_not_found
       show_render reaproveitado: exportação inexistente → not_found
       {"render_id"}; passou sem produção nova (função já existia)
       matriz 1d; QA D1

12:06  🔴 RED    test_the_video_of_an_export_is_its_file_named_after_the_service_date_and_the_cut_title
       o arquivo da exportação e o nome AAAA-MM-DD - <título do corte>.mp4,
       título do corte ≠ da pregação, com / : ? " removidos, pregação
       não processada
       matriz 1e; FR-003; QA D4, D7, L6
       E   ImportError: cannot import name 'render_video' from 'wordcut.service.renders'

12:07  🟢 GREEN  test_the_video_of_an_export_is_its_file_named_after_the_service_date_and_the_cut_title  ·  8 passed
       RenderVideo(path, suggested_name); lê corte e pregação, sem
       sermon_video e sem exigir processed

12:07  🔧 REFACTOR  show_render usa existing_render de service/renders
       um só not_found {"render_id"} para show e download; 22 passed
       (test_renders_service + test_render_task)

12:07  ⚪ GUARDA test_the_video_of_an_export_that_does_not_exist_is_not_found
       render_video de exportação inexistente → not_found {"render_id"};
       passou porque o GREEN anterior já usava existing_render
       matriz 1d

12:07  🔴 RED    test_an_export_whose_file_left_the_disk_has_no_video_and_says_so_without_the_data_folder
       .mp4 apagado: internal_error {"render_id": N}, mensagem sem home.root
       matriz 1f; borda "arquivo ausente"; QA D6
       E       Failed: DID NOT RAISE WordcutError

12:07  🟢 GREEN  test_an_export_whose_file_left_the_disk_has_no_video_and_says_so_without_the_data_folder  ·  10 passed

12:07  🔧 REFACTOR  _render_file depois das funções públicas

12:07  ⚪ GUARDA test_an_export_whose_file_left_the_disk_is_still_shown_from_its_record
       show não abre o arquivo: com o .mp4 apagado, devolve o registro
       matriz 1d; QA L4 (decisão do orquestrador)

12:07  ⚪ GUARDA test_listing_showing_and_locating_exports_work_while_another_process_holds_the_lock
       lock_owner segura a trava; list, show e render_video respondem
       matriz 1g; borda "nenhum comando pega a trava"

12:07  ⚪ GUARDA test_shown_cut_lists_its_exports_the_oldest_first
       cut show com duas exportações segue da mais antiga para a mais
       nova (docs/cli.md §8.2); protege of_cut da inversão
       matriz 1h; QA L1, D2

12:09  🧬 MUTAÇÃO  newest_of_cut ORDER BY ... DESC → ASC  ·  2 failed
12:09  🧬 MUTAÇÃO  newest_of_cut sem o desempate id DESC  ·  1 failed
12:09  🧬 MUTAÇÃO  of_cut com ORDER BY id DESC  ·  2 failed (cut show)
12:09  🧬 MUTAÇÃO  título da pregação no lugar do título do corte  ·  1 failed
12:09  🧬 MUTAÇÃO  sem a checagem is_file  ·  1 failed
12:09  🧬 MUTAÇÃO  shown_render sem .absolute()  ·  1 failed

12:09  ✅ PASSO 1/3 — Serviço  ·  +13 testes  ·  suíte core 802

12:09  --- Passo 2: CLI ---

12:09  🔴 RED    test_list_with_json_gives_the_exports_of_the_cut_the_most_recent_first
       render list --cut <id> --json → {"items"} da mais nova à mais antiga
       matriz 2a, 2b; cenário "histórico do corte"; FR-001
       E       KeyError: 'items'  (o grupo render não existe: erro de uso)

12:09  🟢 GREEN  test_list_with_json_gives_the_exports_of_the_cut_the_most_recent_first  ·  1 passed
       grupo render registrado em wordcut_cli/__init__.py

12:10  ⚪ GUARDA test_list_without_the_cut_is_a_usage_error_with_exit_2
       --cut obrigatório: erro de uso, saída 2; passou (argparse)
       matriz 2b

12:10  ⚪ GUARDA test_list_of_a_cut_that_does_not_exist_fails_with_not_found_and_exit_3
       corte inexistente → not_found, saída 3; passou (serviço do passo 1)
       matriz 2f; borda "corte inexistente"

12:10  🔴 RED    test_show_with_json_gives_the_export_with_the_absolute_path_of_its_file
       render show <id> --json → {id, cut_id, path, duration, created_at,
       options}, path absoluto que abre o arquivo da exportação
       matriz 2c; cenário "detalhar"; FR-002
       E       KeyError: 'path'  (ação show não existe: erro de uso)

12:10  🟢 GREEN  test_show_with_json_gives_the_export_with_the_absolute_path_of_its_file  ·  4 passed
       render show chama o show_render existente; o texto legível reusa o
       da exportação do cut render (describe_export, extraído em cut.py);
       test_cut_render_command segue verde (23 passed)

12:10  ⚪ GUARDA test_show_with_a_relative_data_folder_gives_the_absolute_path_of_the_file
       WORDCUT_HOME relativo na CLI: path absoluto; passou (shown_render do
       passo 1)
       matriz 2c; QA L5 (decisão do orquestrador)

12:10  🔴 RED    test_download_with_json_copies_the_export_to_the_current_folder_with_the_readable_name
       render download <id> na pasta atual: "2026-10-18 - Graça que
       alcança.mp4", bytes idênticos, {path, bytes}
       matriz 2d; cenário "baixar"; FR-003; QA D5
       E       KeyError: 'path'  (ação download não existe: erro de uso)

12:11  🟢 GREEN  test_download_with_json_copies_the_export_to_the_current_folder_with_the_readable_name  ·  6 passed
       _download igual ao do sermon: render_video + copy_without_overwrite,
       -o/--output com padrão os.curdir

12:12  ⚪ GUARDA test_download_to_a_file_path_creates_its_folders_and_answers_the_absolute_path
       -o arquivo (relativo e absoluto) cria as pastas; passou (item 6)
       matriz 2e; borda "-o"

12:12  ⚪ GUARDA test_download_without_json_prints_only_the_absolute_path_of_the_copy
       sem --json, só o caminho no stdout; stderr vazio
       matriz 2d

12:12  ⚪ GUARDA test_download_to_a_folder_writes_the_readable_name_inside_it
       -o pasta existente e -o terminado em "/" recebem o nome legível
       matriz 2e; borda "-o pasta"

12:12  ⚪ GUARDA test_a_second_download_gets_2_in_the_name_and_keeps_the_first_file
       segundo download → " (2)", primeiro arquivo intacto
       matriz 2e; cenário "baixar" (sem sobrescrever)

12:12  ⚪ GUARDA test_json_option_is_accepted_before_between_and_after_the_download_action
       --json antes do grupo, entre grupo e ação e depois da ação
       matriz 2h

12:12  ⚪ GUARDA test_list_show_and_download_work_while_another_process_holds_the_processing_lock
       lock_owner segura a trava; os três comandos saem com 0
       matriz 2g; borda "nenhum comando pega a trava"

12:12  ⚪ GUARDA test_an_export_that_does_not_exist_fails_with_not_found_and_exit_3
       show e download de exportação inexistente → not_found, saída 3,
       nada na pasta atual
       matriz 2f

12:12  ⚪ GUARDA test_a_non_numeric_id_is_a_usage_error_with_exit_2
       show e download com ID não numérico → invalid_argument, saída 2
       matriz 2f

12:12  ⚪ GUARDA test_download_of_an_export_whose_file_left_the_disk_is_the_service_internal_error
       .mp4 apagado: internal_error {"render_id"}, saída 1, stdout sem
       WORDCUT_HOME, nada copiado
       matriz 2f; borda "arquivo ausente"; QA D6

12:12  🧬 MUTAÇÃO  shutil.copyfile no lugar de copy_without_overwrite  ·  1 failed
12:12  🧬 MUTAÇÃO  download dentro da trava de processamento  ·  1 failed
12:12  🧬 MUTAÇÃO  shown_render sem .absolute()  ·  1 failed (WORDCUT_HOME relativo)

12:13  🔧 REFACTOR  test_help_lists_every_command passa a esperar o grupo render
       a lista de comandos do --help mudou com o registro; 401 passed

12:13  ✅ PASSO 2/3 — CLI  ·  +15 testes  ·  suíte cli 401

12:13  --- Passo 3: Documentação ---

12:15  📝 DOC    CHANGELOG [Não lançado]/Adicionado: render list --cut, render
       show, render download [-o]; Alterado: path absoluto com
       WORDCUT_HOME relativo. docs/cli.md §9: ordem, formato dos itens,
       saída {path, bytes}, internal_error, sem trava; §8.2 intocado
       matriz 3; QA L3

12:15  ✅ PASSO 3/3 — Documentação  ·  +0 testes  ·  suíte 1204

12:15  🏁 VERIFICAÇÃO  uv run pytest -q  ·  1204 passed (baseline 1170)
       ruff check, ruff format --check, mypy: limpos

## Rodada 1 · QA

12:16  📊 SUÍTE  1204 passed  ·  0 failed
       core 802 · cli 401; ruff check, ruff format --check, mypy limpos

12:17  🔎 QA     passo 1/3 — Serviço  ·  ✅ PASS
       newest_of_cut próprio (of_cut intocado), show_render reusado via
       existing_render, RenderVideo, sem sermon_video; 1a–1h com teste

12:18  🔎 QA     passo 2/3 — CLI  ·  ✅ PASS
       grupo render registrado; 2a–2h no molde do sermon download;
       saídas 2/3/1 e stdout sem WORDCUT_HOME conferidos

12:18  🔎 QA     passo 3/3 — Documentação  ·  ✅ PASS
       CHANGELOG cita os três comandos e o path absoluto; §9 com ordem,
       itens, {path, bytes}; §8.2 (cut show, mais antiga) intocado

12:19  🧬 MUTAÇÕES · cópia no scratchpad, 9 mutantes  ·  9 de 9 mortas
       ☠️  newest_of_cut DESC → ASC                       3 testes
       ☠️  newest_of_cut sem desempate id DESC            1 teste
       ☠️  of_cut com ORDER BY id DESC                    1 teste
       ☠️  título da pregação no lugar do do corte        10 testes
       ☠️  shutil.copyfile sobrescrevendo                 1 teste
       ☠️  sem a checagem is_file                         2 testes
       ☠️  download dentro da trava                       1 teste
       ☠️  shown_render sem .absolute() (L5)              2 testes
       ☠️  render_video com caminho errado do arquivo     13 testes

12:20  🔎 QA     comentários  ·  ✅ PASS
       renders.py:58 é intenção com referência; docstrings de contrato;
       VIDEO segue o padrão de test_sermon_download_command.py:27
