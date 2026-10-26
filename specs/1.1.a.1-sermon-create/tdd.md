## Plano de QA

baseline_commit: 9b8d7204d7d3fba9d79408794888db72de32bf58

02:06  📐 BARRA   video_id aceita os 4 formatos e rejeita o resto
       tabela em test_video_id.py; invalid_argument com argument=link

02:06  📐 BARRA   YouTube.info traduz falhas em YouTubeError
       subprocess.run substituído; sem yt-dlp real, sem caminho na msg

02:07  📐 BARRA   tabela sermons: UNIQUE, CHECK, ordem, migração 1→2
       SQLite real em tmp_path pela API do repositório

02:07  📐 BARRA   create idempotente sem nova consulta ao YouTube
       dublê de LiveSource que conta chamadas; serviço e CLI

02:07  📐 BARRA   contrato da CLI: JSON único, canais, saídas 2/3/6
       wordcut_cli.main com capsys, wordcut_home e deps substituído

02:08  🧬 EXIGE   remover busca por youtube_id antes de info()  ·  vermelha
       prova que repetir o link não chama o YouTube

02:08  🧬 EXIGE   remover tratamento de IntegrityError  ·  vermelha
       prova a corrida de dois create do mesmo vídeo

02:08  🧬 EXIGE   ORDER BY ASC no list  ·  vermelha
       prova "mais recente primeiro"

02:08  🧬 EXIGE   Context.warn respeitando --quiet  ·  vermelha
       prova que o aviso de live no ar não some

02:08  🧬 EXIGE   video_id aceitando qualquer host  ·  vermelha
       prova a rejeição antes de consultar o YouTube

02:09  ⚠️ LACUNA  live no ar sem duration no metadado do yt-dlp
       sem decisão, 1.1.a.2 pode virar internal_error; PARCIAL

02:09  ⚠️ LACUNA  cookies ausentes viram FileNotFoundError com caminho
       vira internal_error e expõe caminho; passo 1 PARCIAL sem isso

02:09  ⚠️ LACUNA  DEFAULT_COOKIES calculado na importação
       WORDCUT_CONFIG definido depois seria ignorado

02:10  ⚠️ LACUNA  nome e chaves das contagens de cortes não decididos
       FR-004 PARCIAL sem nome registrado no plano

02:10  ⚠️ LACUNA  docs/cli.md §7.2: duração (list) e última tarefa (show)
       omitidas no plano; FR-004/FR-005 PARCIAL sem null ou adiamento

02:10  ⚠️ LACUNA  formato do ID e comparação do host não decididos
       barra: host em lista exata e ID de 11 caracteres

02:10  ⚠️ LACUNA  nenhuma guarda impede teste de chamar o yt-dlp real
       barra: fixture autouse que troca deps.live_source

## Rodada 1 · implementador

02:09  --- Passo 1: ID do vídeo e erros do YouTube ---

02:09  🔴 RED    test_every_link_format_of_the_same_video_gives_its_id
       watch?v=, youtu.be/, /live/, /shorts/ dão o mesmo ID do vídeo
       FR-002; QA passo 1a; decisão 6 (hosts e ID)
       ImportError: cannot import name 'video_id' from 'wordcut.youtube'

02:09  🟢 GREEN  test_every_link_format_of_the_same_video_gives_its_id  ·  10 passed

02:09  🔴 RED    test_link_that_does_not_name_a_youtube_video_is_an_invalid_argument
       outro host, host parecido, YouTube sem ID e texto → invalid_argument
       QA passo 1b; decisão 6; prova a mutação 'aceitar qualquer host'
       Failed: DID NOT RAISE WordcutError  (vimeo, youtube.com.golpe.example, ftp)

02:09  🟢 GREEN  test_link_that_does_not_name_a_youtube_video_is_an_invalid_argument  ·  24 passed

02:10  🔴 RED    test_secrets_folder_is_wordcut_config_when_it_is_set
       WORDCUT_CONFIG define a pasta dos segredos (contêiner: /config)
       QA passo 1d; plano: config.py; ADR-0003
       ModuleNotFoundError: No module named 'wordcut.config'

02:10  🟢 GREEN  test_secrets_folder_is_wordcut_config_when_it_is_set  ·  1 passed

02:10  🟢 GREEN  test_secrets_folder_defaults_to_the_user_config_folder,
       test_youtube_cookies_file_is_in_the_secrets_folder  ·  3 passed
       verdes sem RED: o GREEN anterior já trouxe o padrão e o nome do
       arquivo (não foi o mínimo); ficam como prova de QA 1d

02:10  🔴 RED    test_youtube_without_cookies_argument_uses_the_secrets_folder_set_after_import
       YouTube() resolve os cookies ao ser construído, não na importação
       QA passo 1d; decisão 3 (lacuna QA 3)
       AssertionError: '~/.config/wordcut/youtube-cookies.txt' != '<tmp>/segredos/...'

02:10  🟢 GREEN  test_youtube_without_cookies_argument_uses_the_secrets_folder_set_after_import  ·  8 passed

02:10  🔴 RED    test_failed_yt_dlp_call_is_a_youtube_error_that_hides_the_command_and_cookies
       falha do yt-dlp vira YouTubeError sem o comando nem o caminho dos cookies
       QA passo 1c; plano: erros do YouTube; constituição §VI
       ImportError: cannot import name 'YouTubeError' from 'wordcut.youtube'

02:11  🟢 GREEN  test_failed_yt_dlp_call_is_a_youtube_error_that_hides_the_command_and_cookies  ·  9 passed

02:11  🔴 RED    test_unreadable_yt_dlp_answer_is_a_youtube_error
       resposta do yt-dlp que não é JSON vira YouTubeError
       QA passo 1c
       json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)

02:11  🟢 GREEN  test_unreadable_yt_dlp_answer_is_a_youtube_error  ·  10 passed

02:11  🔴 RED    test_video_without_start_time_is_a_youtube_error_that_says_so
       metadado sem release_timestamp/timestamp → YouTubeError com mensagem clara
       spec: borda 'vídeo sem horário de início'; QA passo 1c
       ValueError: vídeo sem horário de início; informe a data manualmente

02:11  🟢 GREEN  test_video_without_start_time_is_a_youtube_error_that_says_so  ·  11 passed

02:11  🔴 RED    test_missing_cookies_file_is_a_youtube_error_explained_without_its_path
       cookies ausentes → YouTubeError, mensagem sem o caminho (substitui
       test_missing_cookies_file_is_explained, que esperava FileNotFoundError)
       decisão 2 (lacuna QA 2); constituição §VI
       FileNotFoundError: arquivo de cookies não encontrado: <tmp>/none.txt

02:11  🟢 GREEN  test_missing_cookies_file_is_a_youtube_error_explained_without_its_path  ·  11 passed

02:11  🔴 RED    test_live_in_progress_without_duration_has_unknown_duration
       live no ar sem duration no metadado → duração desconhecida (None)
       decisão 1 (lacuna QA 1); cenário 1.1.a.2
       KeyError: 'duration'

02:12  🟢 GREEN  test_live_in_progress_without_duration_has_unknown_duration  ·  12 passed

02:12  🔵 REFACTOR  fixture autouse no_real_yt_dlp em test_youtube.py (decisão 9);
       YouTubeError sem encadear o CalledProcessError (from None), para o
       traceback de WORDCUT_DEBUG não mostrar o comando com o caminho dos cookies

02:12  ✅ PASSO 1/5 — ID do vídeo e erros do YouTube  ·  +32 testes  ·  suíte 201

02:12  --- Passo 2: Tabela e repositório ---

02:13  🔴 RED    test_inserted_sermon_is_read_back_by_its_id_with_every_field
       insert → by_id devolve a pregação com todos os campos da entidade
       QA passo 2b; spec: Entidades e dados
       ImportError: cannot import name 'sermons' from 'wordcut.db'

02:13  🟢 GREEN  test_inserted_sermon_is_read_back_by_its_id_with_every_field  ·  1 passed

02:13  🔴 RED    test_inserted_sermon_is_found_by_its_video_id
       a pregação é achada pelo ID do vídeo (base da idempotência)
       QA passo 2b; FR-002
       AttributeError: module 'wordcut.db.sermons' has no attribute 'by_youtube_id'

02:13  🟢 GREEN  test_inserted_sermon_is_found_by_its_video_id  ·  2 passed

02:13  🟢 GREEN  test_second_sermon_of_the_same_video_is_refused,
       test_database_accepts_each_sermon_status,
       test_database_refuses_a_status_outside_the_sermon_states,
       test_unknown_id_or_video_finds_no_sermon  ·  10 passed
       verdes sem RED: a migração 0002 já trouxe UNIQUE e CHECK; RED provado por
       mutação: sem UNIQUE → 1 failed; sem CHECK → 1 failed (QA 2c, 2d)

02:13  🔴 RED    test_sermons_come_newest_service_first_and_the_later_one_first_on_the_same_day
       lista por service_date DESC, id DESC (nomeada newest_first: 'list'
       sombrearia o tipo embutido nas anotações do módulo)
       QA passo 2e; FR-004; decisão 'Ordenação do list'
       AttributeError: module 'wordcut.db.sermons' has no attribute 'newest_first'

02:13  🟢 GREEN  test_sermons_come_newest_service_first_and_the_later_one_first_on_the_same_day  ·  11 passed

02:14  🔴 RED    test_listing_with_a_status_keeps_only_the_sermons_in_that_state
       newest_first(status=...) filtra pelo estado
       QA passo 2e; FR-004 (--status)
       TypeError: newest_first() got an unexpected keyword argument 'status'

02:14  🟢 GREEN  test_listing_with_a_status_keeps_only_the_sermons_in_that_state  ·  12 passed

02:14  🟢 GREEN  test_new_database_has_schema_version_2_with_an_empty_sermons_table,
       test_database_at_schema_version_1_gains_the_sermons_table_and_keeps_its_data
       ·  14 passed; verdes sem RED (migração já escrita), QA 2a
       mutações: sem 'id DESC' → 1 failed; 'service_date ASC' → 1 failed

02:14  🔵 REFACTOR  by_id e by_youtube_id usam _one(condition, value)  ·  14 passed

02:14  ✅ PASSO 2/5 — Tabela e repositório  ·  +14 testes  ·  suíte 215

02:15  --- Passo 3: Serviço de pregações ---

02:15  🔴 RED    test_first_sermon_of_a_finished_live_is_created_with_the_live_data
       create_sermon grava e devolve id inteiro, dados da live, status created,
       created: true e created_at ISO 8601 com fuso (now injetado)
       FR-001; QA passo 3a; decisão 10 (now)
       ModuleNotFoundError: No module named 'wordcut.service.sermons'

02:15  🟢 GREEN  test_first_sermon_of_a_finished_live_is_created_with_the_live_data  ·  1 passed

02:15  🔴 RED    test_same_video_through_another_link_returns_the_existing_sermon_without_asking_youtube
       mesmo vídeo por outro link → mesma pregação, created: false, 1 consulta
       FR-002; QA passo 3b; decisão 'Idempotência'
       sqlite3.IntegrityError: UNIQUE constraint failed: sermons.youtube_id

02:15  🟢 GREEN  test_same_video_through_another_link_returns_the_existing_sermon_without_asking_youtube  ·  2 passed

02:15  🟢 GREEN  test_live_still_on_air_without_duration_is_created_unfinished_with_unknown_duration,
       test_link_without_a_video_is_refused_before_asking_youtube  ·  4 passed
       verdes sem RED: saem de LiveInfo (passo 1) e de video_id antes de info()
       QA 3c, 3d; decisão 1; FR-003

02:16  🔴 RED    test_sermons_are_listed_newest_service_first_with_zeroed_cut_counts
       list_sermons → {items}, mais recente primeiro, duration null e
       cut_counts zerado (suggested/chosen/discarded)
       FR-004; QA passo 3g; decisões 4 e 5
       ImportError: cannot import name 'list_sermons' from 'wordcut.service.sermons'

02:16  🟢 GREEN  test_sermons_are_listed_newest_service_first_with_zeroed_cut_counts  ·  5 passed

02:16  🔴 RED    test_listing_by_status_keeps_only_the_sermons_in_that_state
       list_sermons(status) filtra; estado sem pregações → items vazio
       FR-004 (--status); QA passo 3g
       TypeError: list_sermons() takes 1 positional argument but 2 were given

02:16  🟢 GREEN  test_listing_by_status_keeps_only_the_sermons_in_that_state  ·  6 passed

02:16  🔴 RED    test_youtube_failure_is_a_youtube_error_and_creates_nothing
       YouTubeError vira WordcutError youtube_error (saída 6), nada gravado
       spec: borda 'falha do YouTube'; QA passo 3e
       wordcut.youtube.YouTubeError: O YouTube recusou o pedido.

02:16  🟢 GREEN  test_youtube_failure_is_a_youtube_error_and_creates_nothing  ·  7 passed

02:16  🔴 RED    test_create_that_loses_a_race_for_the_same_video_returns_the_winner
       dublê cujo info() grava o mesmo vídeo antes de responder → created: false
       QA passo 3f; decisão 7; decisão 'Corrida de dois create iguais'
       sqlite3.IntegrityError: UNIQUE constraint failed: sermons.youtube_id

02:16  🟢 GREEN  test_create_that_loses_a_race_for_the_same_video_returns_the_winner  ·  8 passed

02:17  🔵 REFACTOR  _created(row, created=...) no lugar dos três {**_sermon, created}  ·  8 passed

02:17  🔴 RED    test_shown_sermon_has_empty_borders_no_task_and_no_cuts
       show_sermon → dados do list + live_start/live_end null, last_task null,
       cuts []
       FR-005; QA passo 3h; decisão 5
       ImportError: cannot import name 'show_sermon' from 'wordcut.service.sermons'

02:17  🟢 GREEN  test_shown_sermon_has_empty_borders_no_task_and_no_cuts  ·  9 passed

02:17  🔴 RED    test_showing_an_unknown_sermon_is_not_found
       ID inexistente → not_found (saída 3) com details.sermon_id
       spec: borda 'show de ID inexistente'; QA passo 3h
       AssertionError  (assert row is not None)

02:17  🟢 GREEN  test_showing_an_unknown_sermon_is_not_found  ·  10 passed

02:17  🧬 MUTAÇÃO  sem busca antes de info(); sem tratar IntegrityError; ignorar
       status; sem traduzir YouTubeError  ·  cada uma: 1 failed, 9 passed
       serviço sem argparse, print ou wordcut_cli (ADR-0004, QA 3i)

02:17  ✅ PASSO 3/5 — Serviço de pregações  ·  +10 testes  ·  suíte 225

02:18  --- Passo 4: CLI sermon ---

02:18  🔴 RED    test_create_with_json_prints_the_new_sermon_and_exits_0
       wordcut sermon create <link> --json → saída 0 e um documento JSON
       FR-001, FR-006; QA passo 4a; Verificação 1
       ImportError: cannot import name 'deps' from 'wordcut_cli'

02:18  🟢 GREEN  test_create_with_json_prints_the_new_sermon_and_exits_0  ·  1 passed

02:18  🟢 GREEN  test_help_lists_every_command  ·  29 passed
       test_cli.py passou a esperar 'sermon' na lista (QA 4g); quebrou ao
       registrar o grupo, como o plano previa

02:18  🔵 REFACTOR  conftest.py da CLI com fixture autouse no_real_youtube (decisão 9)

02:19  🟢 GREEN  test_json_option_is_accepted_before_between_and_after_the_sermon_action  ·  4 passed
       verde sem RED: add_group já repete as opções globais; mutação sem
       repetir → 1 failed (posição intermediária), QA 4b

02:19  🔴 RED    test_live_still_on_air_warns_on_stderr_even_when_quiet_and_stdout_keeps_only_the_json
       live no ar: aviso no stderr com e sem --quiet; stdout só o JSON
       FR-003; QA passo 4c; decisão 'Aviso de live no ar'
       AssertionError: assert (0, False, '') == (0, False, 'aviso: A live ainda...')

02:19  🟢 GREEN  test_live_still_on_air_warns_on_stderr_even_when_quiet_and_stdout_keeps_only_the_json  ·  6 passed
       mutações: warn respeitando --quiet → 1 failed; warn no stdout → 2 failed

02:19  🟢 GREEN  test_same_video_through_another_link_returns_the_existing_sermon  ·  verde sem RED
       (regra no serviço, passo 3); QA 4a com dois formatos de link, FR-002

02:19  🔴 RED    test_show_with_json_prints_the_sermon_with_empty_borders_and_no_cuts
       sermon show <id> --json → pregação com bordas null e cuts []; o id do
       create é relido (estável)
       FR-005; QA passo 4 + critério 'detalhar'; Verificação 7
       KeyError: 'id'  (show inexistente: erro invalid_argument no lugar da pregação)

02:20  🟢 GREEN  test_show_with_json_prints_the_sermon_with_empty_borders_and_no_cuts  ·  8 passed

02:20  🔴 RED    test_list_with_json_prints_the_items_newest_service_first
       sermon list --json → {items}, mais recente primeiro
       FR-004; QA passo 4a/4e; Verificação 6
       KeyError: 'items'  (ação list inexistente → erro de uso)

02:20  🟢 GREEN  test_list_with_json_prints_the_items_newest_service_first  ·  9 passed

02:20  🟢 GREEN  test_list_with_status_keeps_only_the_sermons_in_that_state  ·  verde sem RED
       (filtro no serviço, passo 3)

02:20  🔴 RED    test_sermon_failures_follow_the_error_contract[--status arquivada]
       erros pelo contrato: link 2/link, show 999 3, show abc 2/id, --status
       fora dos cinco estados 2/--status, sermon sem ação 2/action; dublê 0 chamadas
       FR-006; QA passo 4d; decisão 8 (choices)
       KeyError: 'error'  (--status aceito sem choices; só este caso falha)

02:20  🟢 GREEN  test_sermon_failures_follow_the_error_contract  ·  15 passed

02:21  🟢 GREEN  test_youtube_failure_exits_6_and_creates_nothing,
       test_failure_without_json_leaves_stdout_empty_and_explains_on_stderr  ·  17 passed
       verdes sem RED: tradução no serviço (passo 3) e no contrato; QA 4d

02:21  🔴 RED    test_create_without_json_summarizes_the_sermon_in_portuguese
       sem --json: ID, título, data do culto e duração da live em português;
       stderr vazio no sucesso
       spec: borda 'sem --json'; QA passo 4e; Verificação 8
       AssertionError: 'Pregação 1: Culto de domingo\n' != 'Pregação 1 criada: ...'

02:21  🟢 GREEN  test_create_without_json_summarizes_the_sermon_in_portuguese  ·  18 passed

02:21  🔴 RED    test_list_without_json_prints_one_line_per_sermon_newest_first
       sem --json: uma linha por pregação com ID, data, estado e título
       QA passo 4e; FR-004
       AssertionError: '2 Culto\n1 Culto\n' != '2  18/10/2026  criada  Culto\n...'

02:21  🔴 RED    test_list_without_json_and_without_sermons_says_so
       lista vazia sem --json diz que não há pregações
       QA passo 4e
       AssertionError: '\n' != 'Nenhuma pregação.\n'

02:21  🟢 GREEN  test_list_without_json_prints_one_line_per_sermon_newest_first,
       test_list_without_json_and_without_sermons_says_so  ·  20 passed

02:21  🔴 RED    test_show_without_json_describes_the_sermon_in_portuguese
       sem --json: título, data, duração e situação da live, estado, bordas, cortes
       QA passo 4e; FR-005; Verificação 8
       AssertionError: 'Pregação 1: Culto de domingo\n' != '...Cortes: nenhum\n'

02:22  🟢 GREEN  test_show_without_json_describes_the_sermon_in_portuguese  ·  21 passed

02:22  🟢 GREEN  test_sermon_help_lists_its_actions,
       test_each_sermon_action_help_shows_an_example_ready_to_copy  ·  25 passed
       verdes sem RED: exemplos vieram com cada add_command; QA 4f

02:22  🔵 REFACTOR  sermon.py: renderizadores e auxiliares reordenados; docstring do
       módulo em inglês  ·  53 passed (CLI)

02:22  ✅ PASSO 4/5 — CLI sermon  ·  +25 testes  ·  suíte 250

02:23  --- Passo 5: Documentação ---

02:23  📝 DOCS   docs/architecture/README.md §4 (service.sermons, db.sermons,
       config, sermon create/list/show) e CHANGELOG (Adicionado e Alterado);
       sem TDD (texto); nenhuma ADR editada

02:23  ✅ PASSO 5/5 — Documentação  ·  +0 testes  ·  suíte 250

02:23  🏁 VERIFICAÇÃO FINAL  pytest 250 passed  ·  ruff check/format limpos  ·  mypy limpo


## Rodada 1 · QA

02:24  📊 SUÍTE  250 passed  ·  0 failed
       ruff check, ruff format --check e mypy limpos

02:26  🧬 MUTAÇÕES · passo 1 (cópia da árvore no scratchpad)  ·  12 de 12 mortas
       ☠️  qualquer host em video_id                    3 testes
       ☠️  youtu.be por prefixo de host                 1 teste
       ☠️  sem formato de ID de 11 caracteres           2 testes
       ☠️  sem checagem de esquema http/https           1 teste
       ☠️  sem tradução de CalledProcessError           1 teste
       ☠️  sem tradução de JSON inválido                1 teste
       ☠️  sem tradução de vídeo sem horário            1 teste
       ☠️  caminho dos cookies na mensagem              1 teste
       ☠️  cookies ausentes voltam a FileNotFoundError  1 teste
       ☠️  config_dir ignora WORDCUT_CONFIG             3 testes
       ☠️  cookies resolvidos na importação             1 teste
       ☠️  duração obrigatória de novo                  2 testes

02:26  🧬 MUTAÇÕES · passo 2  ·  5 de 5 mortas
       ☠️  sem UNIQUE(youtube_id)                       2 testes
       ☠️  sem CHECK de status                          1 teste
       ☠️  ORDER BY service_date ASC                    4 testes
       ☠️  desempate id ASC                             1 teste
       ☠️  repositório ignora o filtro de status        3 testes

02:27  🧬 MUTAÇÕES · passo 3  ·  8 de 8 mortas
       ☠️  sem busca por youtube_id antes de info()     2 testes
       ☠️  sem tratamento de IntegrityError             1 teste
       ☠️  serviço ignora o filtro de status            2 testes
       ☠️  sem tradução de YouTubeError                 2 testes
       ☠️  created: true na pregação existente          2 testes
       ☠️  sem cut_counts                               2 testes
       ☠️  sem last_task                                1 teste
       ☠️  now ignorado                                 1 teste

02:27  🧬 MUTAÇÕES · passo 4  ·  6 de 6 mortas
       ☠️  warn respeitando --quiet                     1 teste
       ☠️  warn no stdout                               2 testes
       ☠️  add_group sem as opções globais              1 teste
       ☠️  sem aviso de live no ar                      2 testes
       ☠️  --status sem choices                         1 teste
       ☠️  subparsers do grupo sem required             1 teste

02:28  ⚖️ JULGADO  troca de test_missing_cookies_file_is_explained
       a matriz 1(e) e a decisão 2 se contradizem para esse teste; a
       decisão 2 é posterior e específica. O novo teste mantém "cookies"
       na mensagem e acrescenta a ausência do caminho. Aceito.

02:29  🔎 QA     passo 1/5 — ID do vídeo e erros do YouTube  ·  ✅ PASS
       tabela de formatos e rejeições, tradução em YouTubeError, cookies
       no construtor; 12 mutações mortas

02:29  🔎 QA     passo 2/5 — Tabela e repositório  ·  ✅ PASS
       migração 1→2 com app_info preservado, UNIQUE, CHECK, ordem e filtro;
       função chama newest_first, não list (só nome)

02:29  🔎 QA     passo 3/5 — Serviço de pregações  ·  ✅ PASS
       idempotência, corrida com dublê, live sem duração, youtube_error sem
       linha gravada, cut_counts, duration e last_task nulos; serviço puro

02:29  🔎 QA     passo 4/5 — CLI sermon  ·  ✅ PASS
       contrato de saída, --json em três posições, aviso com --quiet,
       choices, ajuda com exemplos; fixture autouse contra o YouTube

02:29  🔎 QA     passo 5/5 — Documentação  ·  ✅ PASS
       arquitetura §4 e CHANGELOG em português; nenhuma ADR editada
