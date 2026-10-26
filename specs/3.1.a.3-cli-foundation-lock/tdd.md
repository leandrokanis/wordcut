## Plano de QA

baseline_commit 58acaa5c651e6595cdc7af6952d46ab8d968fea1

01:28  📐 BARRA   contrato da CLI provado por main(argv) -> int
       teste em processo: exit code, stdout e stderr via capsys; o
       executável real só como smoke (uv run wordcut ...) na rodada

01:28  📐 BARRA   trava provada entre processos reais
       subprocesso Python segura a trava; o teste lê holder()/status e
       depois mata o processo (SIGKILL); flock só se prova assim

01:28  📐 BARRA   banco provado por sqlite3 no arquivo de WORDCUT_HOME
       PRAGMA user_version, foreign_keys, journal_mode e busy_timeout
       lidos na conexão devolvida por connect(home)

01:28  🧬 EXIGE   tabela de saídas: busy -> 3  ·  vermelha
       prova que o mapeamento central é o que o teste lê

01:28  🧬 EXIGE   sem o error() da subclasse do argparse  ·  vermelha
       o argparse já sai com 2; só o JSON no stdout mata esta mutação

01:28  🧬 EXIGE   --json só no parser raiz  ·  vermelha
       prova a opção global depois do subcomando

01:28  🧬 EXIGE   traceback no stdout em internal_error  ·  vermelha
       prova stdout limpo em falha não prevista

01:28  🧬 EXIGE   KeyboardInterrupt não tratado  ·  vermelha
       prova a saída 130

01:28  🧬 EXIGE   acquire abre a trava com "w" (trunca)  ·  vermelha
       a segunda tentativa apagaria a descrição do dono; o teste deve
       ler o dono intacto depois de um busy

01:28  🧬 EXIGE   holder() lê o arquivo sem o teste LOCK_SH  ·  vermelha
       conteúdo de processo morto apareceria como dono

01:28  🧬 EXIGE   acquire sem LOCK_NB  ·  vermelha (ou timeout)
       sem fila: o segundo pedido falha na hora; teste precisa de limite
       de tempo para não travar a suíte

01:28  🧬 EXIGE   connect() sem gravar user_version  ·  vermelha
       prova migração idempotente e versão registrada

01:28  🧬 EXIGE   foreign_keys OFF na conexão  ·  vermelha
       prova a decisão de conexão do plano (ADR-0005)

01:28  🧬 EXIGE   elapsed fixo em 0  ·  vermelha
       prova o tempo decorrido do dono, não só a presença do campo

01:28  ⚠️ LACUNA  --version por importlib.metadata.version("wordcut")
       não existe distribuição "wordcut" (só wordcut-cli e wordcut-core):
       PackageNotFoundError; a barra aceita a versão de wordcut-cli

01:28  ⚠️ LACUNA  nenhum comando novo adquire a trava neste item
       busy/saída 4 "pelo contrato" não tem caminho real pela CLI; prova
       em duas metades (core + handler injetado); sem a segunda, PARCIAL

01:28  ⚠️ LACUNA  --quiet sem progresso para suprimir
       só dá para provar que é aceito nas duas posições; a supressão em
       si fica não observável, salvo se o contrato expuser o emissor

01:28  ⚠️ LACUNA  como o teste injeta uma migração extra
       plano não decide; sem migrations injetáveis, migração incremental
       só se prova de user_version 0 com dados; atomicidade fica PARCIAL

01:28  ⚠️ LACUNA  janela entre flock e gravar o JSON do dono
       holder() pode ler arquivo vazio ou pela metade; status não pode
       virar internal_error nessa janela (verificado por leitura)

01:28  ⚠️ LACUNA  apps/cli/tests/test_cli.py fixa a lista de comandos
       adicionar status quebra o teste; plano não o lista; só pode mudar
       para incluir status, sem afrouxar

01:28  ⚠️ LACUNA  details.argument (docs/cli.md §5.3) fora do plano
       a barra cobra, por ser a fonte do contrato; ausência é PARCIAL

01:28  ⚠️ LACUNA  "qualquer comando cria o banco" (spec) vs só status
       barra cobra no contrato novo (status); legado fora do contrato

01:28  ⚠️ LACUNA  §10 status inclui tarefas em andamento
       fora do escopo (item 4, spec Pressupostos); não é cobrado aqui

## Rodada 1 · implementador

01:33  ▶️ PASSOS  1, 2, 3, 4, 5 (todos os - [ ] do plan.md)
       qa.md sem rodada anterior: nada reaberto

01:34  🔴 RED    test_every_documented_error_code_maps_to_its_exit_code
       cada code de docs/cli.md §5.3 sai pelo código de §5.1
       FR-004, FR-005; passo 1 (a)
       E   ModuleNotFoundError: No module named 'wordcut.errors'

01:34  🟢 GREEN  test_every_documented_error_code_maps_to_its_exit_code  ·  15 passed

01:34  🔴 RED    test_an_unlisted_code_is_rejected_so_every_error_has_an_exit_code
       código fora da tabela central é recusado na criação
       FR-005 (mapeamento central)
       E       Failed: DID NOT RAISE ValueError

01:34  🟢 GREEN  test_an_unlisted_code_is_rejected_so_every_error_has_an_exit_code  ·  16 passed

01:34  🔴 RED    test_json_option_after_the_command_prints_the_result_as_one_json_document
       --json depois do subcomando: stdout é um único documento JSON, saída 0
       FR-001, FR-002; passo 1 (c)(d)
       E   ModuleNotFoundError: No module named 'wordcut_cli.contract'

01:35  🟢 GREEN  test_json_option_after_the_command_prints_the_result_as_one_json_document  ·  1 passed

01:35  🔴 RED    test_without_json_the_result_is_printed_as_readable_text
       sem --json, o stdout traz o texto legível do comando
       docs/cli.md §4.2; passo 1 (d)
       E       assert '{"answer": "sim"}\n' == 'pronto\n'

01:35  🟢 GREEN  test_without_json_the_result_is_printed_as_readable_text  ·  2 passed

01:35  🔴 RED    test_json_option_before_the_command_gives_the_same_output_as_after
       --json antes ou depois do subcomando dá o mesmo resultado
       FR-001; caso de borda do spec; passo 1 (c)
       E       SystemExit: 2

01:35  🟢 GREEN  test_json_option_before_the_command_gives_the_same_output_as_after  ·  3 passed

01:35  🔴 RED    test_quiet_option_reaches_the_handler_before_or_after_the_command
       --quiet aceito nas duas posições e visível no contexto do handler
       FR-001, FR-003; decisão 3 do orquestrador
       E       SystemExit: 2

01:35  🟢 GREEN  test_quiet_option_reaches_the_handler_before_or_after_the_command  ·  5 passed

01:36  🔴 RED    test_domain_error_with_json_prints_only_the_error_object_and_exits_with_its_code
       WordcutError com --json: stdout só com {"error": …}, saída pela tabela
       FR-004; docs/cli.md §5.2; passo 1 (d)
       E       wordcut.errors.WordcutError: Pregação 7 não existe.

01:36  🟢 GREEN  test_domain_error_with_json_prints_only_the_error_object_and_exits_with_its_code  ·  6 passed

01:36  🔴 RED    test_domain_error_without_json_leaves_stdout_empty_and_writes_the_message_to_stderr
       sem --json, erro só no stderr como texto; stdout vazio
       caso de borda do spec; docs/cli.md §5.2; passo 1 (d)
       E       assert (3, '{"error"...: 7}}}\n', '') == (3, '', 'erro...ão existe.\n')

01:36  🟢 GREEN  test_domain_error_without_json_leaves_stdout_empty_and_writes_the_message_to_stderr  ·  7 passed

01:36  🔴 RED    test_unexpected_failure_becomes_internal_error_without_any_traceback
       exceção não prevista: internal_error, saída 1, mensagem genérica, sem traceback
       caso de borda do spec; plano (Exceção inesperada); passo 1 (f)
       E       RuntimeError: segredo interno

01:36  🟢 GREEN  test_unexpected_failure_becomes_internal_error_without_any_traceback  ·  8 passed

01:36  🔴 RED    test_debug_mode_writes_the_traceback_to_stderr_and_keeps_stdout_clean
       WORDCUT_DEBUG=1: traceback só no stderr; stdout segue com o objeto de erro
       plano (Exceção inesperada); passo 1 (f)
       E       AssertionError: assert ('internal_error', False) == ('internal_error', True)

01:36  🟢 GREEN  test_debug_mode_writes_the_traceback_to_stderr_and_keeps_stdout_clean  ·  9 passed

01:37  🔴 RED    test_ctrl_c_exits_with_130_and_prints_no_result
       KeyboardInterrupt no handler: saída 130, sem JSON no stdout
       caso de borda do spec; docs/cli.md §5.1; passo 1 (g)
       !!!! KeyboardInterrupt !!!! test_cli_contract.py:26: KeyboardInterrupt (sessão interrompida)

01:37  🟢 GREEN  test_ctrl_c_exits_with_130_and_prints_no_result  ·  10 passed

01:37  🔴 RED    test_unknown_option_with_json_is_an_invalid_argument_error_in_portuguese
       erro de uso com --json: invalid_argument, saída 2, message em português
       cenário 'erro em JSON'; decisão 7 (details.argument); passo 1 (e)
       E       SystemExit: 2

01:38  🟢 GREEN  test_unknown_option_with_json_is_an_invalid_argument_error_in_portuguese  ·  11 passed

01:38  🔴 RED    test_missing_command_names_the_missing_argument
       argumento obrigatório ausente: invalid_argument com details.argument
       decisão 7; docs/cli.md §5.3; passo 1 (e)
       E       AssertionError: assert (2, {'code': ...cut --help.'}) == (2, {'code': ...: 'command'}})

01:38  🟢 GREEN  test_missing_command_names_the_missing_argument  ·  12 passed

01:38  🔴 RED    test_malformed_value_names_the_argument_it_belongs_to
       valor mal formado: invalid_argument com o argumento e o valor recusado
       decisão 7; docs/cli.md §5.3; passo 1 (e)
       E       assert (2, {'code': ...cut --help.'}) == (2, {'code': ...: '--count'}})

01:38  🟢 GREEN  test_malformed_value_names_the_argument_it_belongs_to  ·  13 passed

01:38  🔴 RED    test_option_without_its_value_names_the_argument
       qualquer outro erro de argumento do argparse ainda identifica o argumento
       decisão 7; docs/cli.md §5.3; passo 1 (e)
       E       AssertionError: assert (2, {'code': ...cut --help.'}) == (2, {'code': ...: '--count'}})

01:39  🟢 GREEN  test_option_without_its_value_names_the_argument  ·  14 passed

01:39  🟢 GREEN  test_usage_error_without_json_leaves_stdout_empty_and_explains_on_stderr  ·  15 passed
       verde já ao escrever: o caminho de erro sem --json é o mesmo da fatia de
       erro de domínio; fica como prova do caso de borda para erro de uso

01:39  🔴 RED    test_version_prints_the_installed_cli_version
       --version imprime a versão de wordcut-cli e sai com 0, pelo main(argv)
       caso de borda do spec; decisão 1 do orquestrador; passo 1 (b)(h)
       E       SystemExit: 2

01:40  🟢 GREEN  test_version_prints_the_installed_cli_version  ·  16 passed

01:40  🔁 AJUSTE  test_help_lists_every_command  (apps/cli/tests/test_cli.py)
       main agora devolve o código: --help sai com 0 em vez de SystemExit;
       os 7 comandos antigos seguem exigidos na mesma ordem (decisão 6)

01:40  🔴 RED    test_previous_overview_command_still_prints_the_transcript
       wordcut overview <arquivo> segue funcionando no mesmo executável
       plano, Verificação; passo 1 (i)
       E       AttributeError: 'Namespace' object has no attribute 'contract'

01:40  🟢 GREEN  test_previous_overview_command_still_prints_the_transcript  ·  18 passed

01:41  ✅ PASSO  1/5 — Erros e contrato de saída  ·  +33 testes  ·  suíte 130
       smoke: wordcut --version → 0.1.0, saída 0; wordcut --json bogus → saída 2

01:41  🔴 RED    test_data_root_is_wordcut_home_when_it_is_set
       WORDCUT_HOME definido: é a raiz de dados
       FR-006; docs/cli.md §14; passo 2 (a)
       E   ModuleNotFoundError: No module named 'wordcut.home'

01:41  🟢 GREEN  test_data_root_is_wordcut_home_when_it_is_set  ·  1 passed

01:41  🔴 RED    test_data_root_defaults_to_the_user_data_folder
       sem WORDCUT_HOME, a raiz é ~/.local/share/wordcut
       FR-006; docs/cli.md §14; passo 2 (a)
       E   KeyError: 'WORDCUT_HOME'

01:41  🟢 GREEN  test_data_root_defaults_to_the_user_data_folder  ·  2 passed

01:41  🔴 RED    test_first_connection_creates_the_data_folder_private_to_the_user
       primeira conexão cria a pasta de dados (com pais) em modo 0700
       FR-006; plano (Raiz de dados); passo 2 (a)
       E   ModuleNotFoundError: No module named 'wordcut.db'

01:41  🟢 GREEN  test_first_connection_creates_the_data_folder_private_to_the_user  ·  3 passed

01:42  🔴 RED    test_first_connection_applies_every_packaged_migration
       banco novo recebe todas as migrações; user_version = último número
       FR-006; ADR-0005; passo 2 (b)
       E   ImportError: cannot import name 'MIGRATIONS' from 'wordcut.db'

01:42  🟢 GREEN  test_first_connection_applies_every_packaged_migration  ·  4 passed

01:42  🔴 RED    test_new_database_records_the_version_that_created_it
       banco criado agora guarda em app_info a versão do wordcut-core que o criou
       plano, Contexto de código (0001_base.sql); passo 2 (b)
       E       AssertionError: assert None == ('wordcut-core 0.1.0',)

01:42  🟢 GREEN  test_new_database_records_the_version_that_created_it  ·  5 passed

01:42  🔴 RED    test_connection_enforces_foreign_keys_and_shares_the_file_with_other_processes
       conexão com foreign_keys=1, journal_mode=wal e busy_timeout=5000
       ADR-0005; plano (Conexão); passo 2 (c)
       E       AssertionError: assert (0, 'delete', 5000) == (1, 'wal', 5000)

01:43  🟢 GREEN  test_connection_enforces_foreign_keys_and_shares_the_file_with_other_processes  ·  6 passed

01:43  🟢 GREEN  reabertura, banco antigo, migração incremental e migração quebrada  ·  10 passed
       verdes ao escrever: o executor genérico da fatia anterior já os cumpria;
       mutações conferidas na hora: sem BEGIN/COMMIT → 1 vermelho; sem
       user_version → 5 vermelhos; foreign_keys OFF → 1 vermelho

01:44  🔁 REFACTOR  db: _apply com ROLLBACK explícito; connect fecha a conexão se migrar falha
       10 passed

01:44  ✅ PASSO  2/5 — Home e banco  ·  +10 testes  ·  suíte 140
       uv build --package wordcut-core: wordcut/db/migrations/0001_base.sql no wheel

01:44  🔴 RED    test_holder_describes_the_operation_holding_the_lock
       com a trava adquirida, holder() traz tipo, recurso e PID do dono
       FR-007, FR-009; ADR-0006; passo 3 (a)(d)
       E   ModuleNotFoundError: No module named 'wordcut.lock'

01:44  🟢 GREEN  test_holder_describes_the_operation_holding_the_lock  ·  1 passed

01:44  🟢 GREEN  test_holder_describes_another_process_holding_the_lock  ·  2 passed
       verde ao escrever: prova entre processos reais (fixture lock_owner no
       conftest.py da raiz, com limite de 20 s por SIGALRM)

01:45  🔴 RED    test_acquiring_a_held_lock_fails_at_once_with_busy_and_the_holder_details
       outro processo segura: acquire falha na hora com busy e details do dono
       cenário 3.1.a.1; FR-008; passo 3 (b)
       E           BlockingIOError: [Errno 11] Resource temporarily unavailable

01:45  🟢 GREEN  test_acquiring_a_held_lock_fails_at_once_with_busy_and_the_holder_details  ·  3 passed

01:45  🟢 GREEN  dono intacto após busy, livre após SIGKILL, readquirível após SIGKILL,
       liberada ao sair do bloco  ·  7 passed
       verdes ao escrever; mutações conferidas: abrir com O_TRUNC → 2 vermelhos;
       holder() sem LOCK_SH → 2 vermelhos

01:46  🧪 MUTAÇÃO  acquire sem LOCK_NB  ·  2 vermelhos por TimeoutError em 20 s cada
       o limite de tempo da fixture lock_owner impede a suíte de travar

01:46  🔴 RED    test_start_time_is_local_iso_8601_with_offset_and_whole_seconds
       started_at em ISO 8601 com fuso local e sem fração de segundo
       docs/cli.md §4.3; plano (Datas); passo 3 (g)
       E       AssertionError: assert None  ('2026-10-26T01:46:23.800832-03:00')

01:46  🟢 GREEN  test_start_time_is_local_iso_8601_with_offset_and_whole_seconds  ·  8 passed

01:46  🔴 RED    test_lock_that_was_never_taken_is_free
       sem arquivo de trava (WORDCUT_HOME novo), a trava está livre
       FR-009; cenário 'máquina livre'; passo 3 (d)
       E       FileNotFoundError: [Errno 2] No such file or directory: '…/nova/processing.lock'

01:46  🟢 GREEN  test_lock_that_was_never_taken_is_free  ·  9 passed

01:47  🔴 RED    test_lock_held_before_its_description_is_written_shows_an_unknown_holder
       trava ocupada com arquivo vazio, JSON pela metade ou não-objeto: dono
       desconhecido com campos None, sem exceção (janela entre flock e gravação)
       decisão 5 do orquestrador; passo 3 (h)
       E           json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)

01:47  🟢 GREEN  test_lock_held_before_its_description_is_written_shows_an_unknown_holder  ·  12 passed

01:47  🔁 REFACTOR  lock: _is_free, _describe, _now extraídos; modo do arquivo em constante
       12 passed

01:47  🟢 GREEN  test_command_refused_by_a_lock_held_elsewhere_exits_with_busy_and_the_holder
       verde ao escrever: segunda metade do critério busy (decisão 2), handler
       que adquire a trava de outro processo sai pelo main com 4 e o dono  ·  17 passed

01:47  ✅ PASSO  3/5 — Trava global  ·  +13 testes  ·  suíte 153

01:48  🔴 RED    test_machine_with_no_operation_running_reports_the_lock_free
       nenhuma operação rodando: o serviço devolve {"lock": {"held": false}}
       cenário 'status com a máquina livre'; FR-009; passo 4 (a)(b)
       E   ModuleNotFoundError: No module named 'wordcut.service'

01:48  🟢 GREEN  test_machine_with_no_operation_running_reports_the_lock_free  ·  1 passed

01:48  🔴 RED    test_machine_busy_elsewhere_reports_the_holder_and_how_long_it_has_run
       outro processo segura: held true, tipo, recurso, PID, início e tempo
       decorrido em segundos (relógio injetado: início + 90 s → 90)
       cenário 'máquina ocupada'; FR-009; passo 4 (c)
       E       TypeError: machine_status() got an unexpected keyword argument 'now'

01:48  🟢 GREEN  test_machine_busy_elsewhere_reports_the_holder_and_how_long_it_has_run  ·  2 passed

01:48  🟢 GREEN  dono morto → livre; dono ainda sem descrição → held com campos None  ·  4 passed
       verdes ao escrever; mutações conferidas: elapsed fixo em 0 → 1 vermelho;
       serviço sempre livre → 2 vermelhos

01:48  🔴 RED    test_first_status_call_creates_the_database
       WORDCUT_HOME vazio: o primeiro status cria pasta e banco, sem init
       cenário 'primeira execução cria o banco'; docs/cli.md §14; passo 4 (f)
       E       AssertionError: assert False  (where False = is_file())

01:48  🟢 GREEN  test_first_status_call_creates_the_database  ·  5 passed

01:49  🔴 RED    test_holder_with_an_unreadable_start_time_has_no_elapsed_time
       descrição com started_at ilegível: elapsed_seconds null, sem exceção
       decisão 5 do orquestrador (status nunca vira internal_error)
       E       ValueError: Invalid isoformat string: 'ontem'

01:49  🟢 GREEN  test_holder_with_an_unreadable_start_time_has_no_elapsed_time  ·  6 passed

01:49  🔴 RED    test_holder_with_an_unreadable_start_time_has_no_elapsed_time[2026-10-26T19:40:00]
       started_at sem fuso também não derruba o status
       decisão 5; docs/cli.md §4.3 (datas com fuso)
       E       TypeError: can't subtract offset-naive and offset-aware datetimes

01:49  🟢 GREEN  test_holder_with_an_unreadable_start_time_has_no_elapsed_time  ·  7 passed

01:49  🔴 RED    test_status_of_an_idle_machine_is_the_free_lock_in_json
       wordcut status --json num WORDCUT_HOME vazio: {"lock": {"held": false}}, 0
       cenário 'máquina livre'; Verificação 1; passo 4 (b)(e)
       E       AssertionError: assert (2, {'error':... 'command'}}}) == (0, {'lock': {'held': False}})

01:49  🟢 GREEN  test_status_of_an_idle_machine_is_the_free_lock_in_json  ·  1 passed

01:49  🔁 AJUSTE  test_help_lists_every_command  (apps/cli/tests/test_cli.py)
       COMMANDS passa a terminar em ,status}; os 7 antigos seguem exigidos na
       mesma ordem (decisão 6)  ·  apps/cli 20 passed

01:50  🔴 RED    test_status_without_json_describes_the_holder_in_portuguese
       sem --json: texto legível com tipo, recurso, PID, início e tempo decorrido
       FR-009; docs/cli.md §4.2; passo 4 (e)
       E       AssertionError: assert None  (… 'Máquina livre: nenhum processamento em andamento.\n')

01:50  🟢 GREEN  test_status_without_json_describes_the_holder_in_portuguese  ·  2 passed

01:50  🔴 RED    test_status_while_the_holder_has_not_described_itself_is_busy_with_unknowns
       trava segura com arquivo vazio: status sai com 0, ocupado, campos como ?
       decisão 5 do orquestrador (nunca internal_error); passo 4 (e)
       E       At index 1 diff: 'Máquina ocupada: None de None (PID None), desde None, há None s.\n'

01:50  🟢 GREEN  test_status_while_the_holder_has_not_described_itself_is_busy_with_unknowns  ·  3 passed

01:50  🟢 GREEN  status com dono vivo (FR-010), --json nas duas posições, banco criado,
       dono morto → livre  ·  7 passed  ·  verdes ao escrever (serviço e contrato
       das fatias anteriores)

01:51  🔴 RED    test_status_help_shows_an_example_ready_to_copy
       wordcut status --help traz ao menos um exemplo pronto para copiar
       docs/cli.md §3.2 (--help); FR-001
       E       At index 1 diff: False != True

01:51  🟢 GREEN  test_status_help_shows_an_example_ready_to_copy  ·  apps/cli 27 passed

01:51  ✅ PASSO  4/5 — wordcut status  ·  +15 testes  ·  suíte 168
       smoke: WORDCUT_HOME vazio → {"lock": {"held": false}}, saída 0, pasta 700
       e wordcut.db criados; com dono vivo → held true, elapsed_seconds 3, saída 0

01:53  ✅ PASSO  5/5 — Documentação  ·  +0 testes  ·  suíte 168
       README (seção da CLI nova, WORDCUT_HOME, disco local), ADR-0012 e índice,
       docs/architecture §4, CHANGELOG; docs/cli.md sem mudança de contrato

01:53  🏁 FINAL  suíte 168 passed  ·  ruff check/format limpos  ·  mypy limpo
       Verificação do plan.md toda marcada; sem commit (override do orquestrador)

## Rodada 1 · QA

01:54  📊 SUÍTE  168 passed  ·  0 failed
       ruff check, ruff format --check e mypy (39 arquivos) limpos;
       baseline 58acaa5 em worktree temporária: 97 passed, gates limpos,
       mesmo aviso do starlette

01:55  🔎 QA     smoke do executável real  ·  ✅
       --version → 0.1.0, 0; WORDCUT_HOME vazio → {"lock":{"held":false}},
       0, pasta 700 e wordcut.db; dono vivo → held, kind, resource, pid,
       started_at, elapsed_seconds 3, 0 (antes e depois); dono SIGKILL →
       livre; --json bogus → invalid_argument com details.argument, 2

01:56  🔎 QA     overview contra o baseline  ·  ✅
       mesma transcrição fictícia: saída idêntica e 0 nas duas árvores

01:56  🔎 QA     erro de uso de comando antigo  ·  ⚠️ mudou
       wordcut overview sem arquivo: baseline imprime usage + mensagem do
       argparse em inglês; agora "erro: Argumento obrigatório ausente:
       transcript." (saída 2 nas duas); contract.py:145 diz o contrário

01:57  🔎 QA     wheel do wordcut-core  ·  ✅
       wordcut/db/migrations/0001_base.sql presente

01:58  🧬 MUTAÇÕES · 26 mutações numa cópia da árvore no scratchpad  ·  25 de 26 mortas
       ☠️  tabela busy → 3                                    2 testes
       ☠️  sem error() da subclasse do argparse               5 testes
       ☠️  --json só no parser raiz                           7 testes
       ☠️  traceback no stdout                                2 testes
       ☠️  KeyboardInterrupt não tratado              sessão interrompida
       ☠️  traceback no stderr sem WORDCUT_DEBUG              1 teste
       ☠️  sem details.argument                               4 testes
       ☠️  --version de "wordcut"                            27 testes
       ☠️  erro de uso sempre em texto                        4 testes
       ☠️  acquire com O_TRUNC                                3 testes
       ☠️  holder() sem LOCK_SH                               4 testes
       ☠️  acquire sem LOCK_NB                   2 testes (timeout 20 s)
       ☠️  holder() sem tratar JSON inválido                  4 testes
       ☠️  acquire sem liberar ao sair                        1 teste
       ☠️  started_at com microssegundos                      1 teste
       ☠️  busy sem details                                   2 testes
       ☠️  sem gravar user_version                            5 testes
       ☠️  foreign_keys OFF                                   1 teste
       ☠️  migração sem BEGIN/COMMIT                          1 teste
       ☠️  reaplicar migrações já aplicadas                   3 testes
       ☠️  journal_mode DELETE                                1 teste
       ☠️  pasta sem modo 0700                                1 teste
       ☠️  elapsed fixo em 0                                  1 teste
       ☠️  serviço sempre livre                               8 testes
       ☠️  status sem criar o banco                           2 testes
       🚨  _apply sem ROLLBACK              SOBREVIVEU — equivalente:
       connect() fecha a conexão na falha e o fechamento desfaz a
       transação; não é achado

01:59  🔎 QA     passo 1/5 — Erros e contrato de saída  ·  ⚠️ PARCIAL
       (a)–(h) provados; (i) comando antigo mudou o erro de uso (stderr)
       e o comentário contract.py:145 e a ADR-0012 dizem que não

01:59  🔎 QA     passo 2/5 — Home e banco  ·  ✅ PASS
       (a)–(g) com teste de comportamento; atomicidade por migração
       injetada, mutação sem BEGIN/COMMIT vermelha

01:59  🔎 QA     passo 3/5 — Trava global  ·  ✅ PASS
       entre processos reais, com limite de 20 s; arquivo vazio ou
       inválido → campos None

01:59  🔎 QA     passo 4/5 — wordcut status  ·  ✅ PASS
       serviço puro com relógio injetado; CLI nas duas posições; smoke

01:59  🔎 QA     passo 5/5 — Documentação  ·  ✅ PASS
       README, ADR-0012 e índice, architecture §4; docs/cli.md e ADRs
       0004–0006 sem diff; códigos da ADR batem com errors.py

01:59  🔎 QA     política de comentários (CONTRIBUTING §5)  ·  ⚠️
       todos de tipo válido e em inglês; contract.py:145-146 é falso
       quanto aos erros dos comandos antigos

## Rodada 2 · implementador

02:00  ▶️ PASSOS  1 (reaberto como PARCIAL na Rodada 1 do qa.md, item (i))
       achado: erro de uso de comando antigo sai como invalid_argument em
       português; contract.py e ADR-0012 diziam que não. Decisão do
       orquestrador: manter o comportamento novo e documentá-lo

02:01  🔴 RED    test_previous_command_usage_error_follows_the_contract
       wordcut overview --json sem arquivo: saída 2 e só o objeto
       invalid_argument em português, com details.argument
       decisão do orquestrador, rodada 2; passo 1 (i)
       passou sem produção: fixa um comportamento que já existe e que a
       decisão mantém. Prova de que mata a regressão: mutação temporária
       add_subparsers(parser_class=argparse.ArgumentParser) →
       E           json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
       mutação desfeita

02:01  🟢 GREEN  test_previous_command_usage_error_follows_the_contract  ·  2 passed

02:02  ✅ PASSO  1/5 — Erros e contrato de saída (item (i))  ·  +1 teste  ·  suíte 169
       comentário de contract.py, docstring de legacy.py, ADR-0012 e
       docs/architecture §4 dizem que o erro de uso dos comandos antigos
       segue o contrato; saída de sucesso e erros de execução continuam
       deles. Decisão registrada no plan.md. Comandos antigos sem outra
       mudança

02:02  🏁 FINAL  suíte 169 passed  ·  ruff check/format limpos  ·  mypy limpo
       smoke: wordcut overview → "erro: Argumento obrigatório ausente:
       transcript.", saída 2; sem commit (override do orquestrador)

## Rodada 2 · QA

02:03  🔎 QA     passo 1/5 — Erros e contrato de saída (item (i))  ·  ✅ PASS
       decisão da rodada 2 cumprida: contract.py:145-146, docstring de
       legacy.py e ADR-0012 dizem que o erro de uso segue o contrato;
       test_previous_command_usage_error_follows_the_contract fixa
       overview --json → 2 e invalid_argument; legacy.py = baseline
       salvo imports e registro

02:03  🧬 MUTAÇÕES · erro de uso dos comandos antigos (cópia no scratchpad)
       ·  4 de 4 mortas
       ☠️  Parser.error delega ao argparse no subparser overview  1 teste
       ☠️  erro de uso ignora --json do argv                      1 teste
       ☠️  mensagem obrigatória volta ao inglês                   1 teste
       ☠️  sem details.argument                                   1 teste

02:04  🔎 QA     passos 2–5  ·  ✅ PASS
       sem regressão: suíte inteira, gates, wheel e smoke iguais à rodada 1

02:04  📊 SUÍTE  169 passed  ·  0 failed
       ruff check, ruff format --check e mypy (39 arquivos) limpos; smoke:
       overview sem arquivo → 2 (JSON com --json antes ou depois, stderr
       em português sem ele); status --json → held false, 0; --version
       0.1.0, 0; wheel com 0001_base.sql
