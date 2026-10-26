## Plano de QA

baseline_commit 5249c8b0d1e7d5b92aa2ddfe268973924c089c93

02:56  📐 BARRA   tarefa destacada provada entre processos reais
       start(detach=True) no teste; estado lido no SQLite e em holder();
       os.getsid(pid) == pid prova a sessão própria; flock só se prova assim

02:56  📐 BARRA   todo teste com filho destacado tem prazo e limpeza
       fixture da raiz: SIGALRM (como lock_owner) + killpg e waitpid de
       cada tarefa lançada; pgrep wordcut.tasks.runner vazio após a suíte

02:56  📐 BARRA   --wait provado pelo contrato real da CLI
       comando de teste com add_wait_option + launch rodado por
       execute(parser, argv): stdout, stderr, saída e 130 de uma vez

02:56  📐 BARRA   trava livre na primeira leitura após o fim da tarefa
       sem polling: é o que permite "task wait 9 && <outra>" sem busy
       espúrio, que é o propósito da história 3.1.a.2

02:56  📐 BARRA   Ctrl+C provocado com a tarefa rodando
       Timer + _thread.interrupt_main() durante diagnostic longo; exige
       failed/interrupted, finished_at, trava livre e 130

02:56  🧬 EXIGE   Popen sem start_new_session  ·  vermelha
       prova o FR-002; sem isso o SIGHUP do terminal mata a tarefa

02:56  🧬 EXIGE   pai não fecha o descritor da trava  ·  vermelha
       a trava ficaria presa ao processo que lançou após o fim da tarefa

02:56  🧬 EXIGE   filho não reescreve o dono com o próprio PID  ·  vermelha
       status mostraria o PID do pai, já morto, como dono

02:56  🧬 EXIGE   criar a tarefa antes de adquirir a trava  ·  vermelha
       busy deixaria linha órfã no banco; contagem antes/depois mata

02:56  🧬 EXIGE   remover a reconciliação de órfãs em show  ·  vermelha
       prova FR-006 na leitura, não só no status

02:56  🧬 EXIGE   wait_task devolve sucesso em failed  ·  vermelha
       prova que task wait termina com a saída da tarefa

02:56  🧬 EXIGE   Ctrl+C em task wait marca a tarefa failed  ·  vermelha
       a tarefa destacada deve seguir e terminar succeeded

02:56  🧬 EXIGE   progresso escrito no stdout  ·  vermelha
       json.loads do stdout inteiro quebra; prova os canais de §4.1

02:56  🧬 EXIGE   --quiet ignorado no --wait  ·  vermelha
       docs/cli.md §4.5; o plano não citou, a barra cobra

02:56  🧬 EXIGE   interrupted mapeado para 5  ·  vermelha
       tarefa morta não é regra violada; plano fixou saída 1

02:56  ⚠️ LACUNA  coluna params fora da lista da migração 0003
       a Decisão cita params JSON, o Contexto de código não; sem ela o
       filho não reconstrói a tarefa só pelo ID e o passo 2 fica FAIL

02:56  ⚠️ LACUNA  limite de tempo só existe na fixture lock_owner
       o plano diz que wordcut_home dá o prazo; não dá. Sem fixture nova
       com prazo e killpg, os passos 2 e 4 ficam PARCIAL

02:56  ⚠️ LACUNA  os.kill(pid, 0) vê zumbi como vivo
       lançador de vida longa (pytest, futura API) que não colhe o filho
       morto nunca o vê órfão; nos testes, colher antes de ler

02:56  ⚠️ LACUNA  PID de outro contêiner no os.kill(pid, 0)
       CLI no contêiner lendo tarefa lançada pela API marcaria tarefa
       viva como failed; nada no plano trata namespace de PID

02:56  ⚠️ LACUNA  quem grava o pid da tarefa e quando
       linha criada antes do Popen sem pid (ou com pid do pai que sai)
       pode ser lida como órfã na janela do lançamento

02:56  ⚠️ LACUNA  ordem entre soltar a trava e gravar o estado final
       filho que grava succeeded e só depois sai deixa busy espúrio a
       quem encadeia; "trava livre depois" fica PARCIAL sem a ordem

02:56  ⚠️ LACUNA  tarefa sem trava (suggest) sem mecanismo nem teste
       TaskKind não tem flag de trava; a borda do spec fica descoberta

02:56  ⚠️ LACUNA  busy sem task_id nos details
       docs/cli.md §5.2/§5.3 pedem a tarefa no busy; o plano só grava
       task_id no dono

02:56  ⚠️ LACUNA  saída do lançamento diverge de docs/cli.md §6.2
       plano: resource_type/resource_id; doc: sermon_id. Passo 5 não
       prevê mexer em §6.2

02:56  ⚠️ LACUNA  pai trava e filho herda contraria a ADR-0007
       a ADR aceita diz que o filho adquire a trava; decisão nova de
       arquitetura sem ADR (CLAUDE.md)

02:56  ⚠️ LACUNA  como provocar Ctrl+C e formato do progresso
       plano não fixa o meio de teste do 130 nem a linha "[kind] ..."
       nem o --quiet; a barra adotou os de docs/cli.md §4.5

02:56  ⚠️ LACUNA  diagnostic no core contraria o pressuposto do spec
       spec: registrado só nos testes; o filho precisa importá-lo. Aceito
       o plano; CHECK de kind na migração não pode barrar diagnostic

02:56  ⚠️ LACUNA  task list sem ordem nem limite definidos
       "tarefas recentes" (§10) sem critério; a barra cobra mais
       recentes primeiro e ordem estável

## Rodada 1 · implementador

03:04  📋 PLANO   5 passos - [ ]: 1 modelo e primeiro plano, 2 destacado,
       3 consulta/espera/órfãs, 4 CLI, 5 documentação; 13 decisões do
       orquestrador registradas no plan.md; baseline 320 passed

--- Passo 1: Modelo e execução em primeiro plano ---

03:04  🔴 RED    test_migration_creates_the_tasks_table_with_every_task_field
       o banco migra para o esquema 3 com a tabela tasks e todos os campos
       FR-001; orquestrador 1 (params) e 4 (host)
       AssertionError: assert (set(), 2) == ({'error_code...'id', ...}, 3)

03:04  🟢 GREEN  test_migration_creates_the_tasks_table_with_every_task_field  ·  1 passed

03:05  🟢 GUARDA test_database_in_schema_2_keeps_its_sermons_when_migrated  ·  2 passed
       banco no esquema 2 com pregações migra sem perder dados; passa de
       primeira porque a migração 0003 já existe (barra, passo 1 a)

03:05  🔴 RED    test_inserted_task_is_read_back_running_with_every_field
       o repositório grava a tarefa running e a lê de volta com cada campo
       FR-001; barra passo 1 (b)
       ImportError: cannot import name 'tasks' from 'wordcut.db'

03:05  🟢 GREEN  test_inserted_task_is_read_back_running_with_every_field  ·  3 passed

03:05  🔴 RED    test_a_registered_kind_is_found_by_its_name (+ unknown refused)
       o registro devolve o tipo pelo nome e recusa nome desconhecido
       barra passo 1 (c); decisão "tipos de tarefa" do plano
       ModuleNotFoundError: No module named 'wordcut.tasks'

03:05  🟢 GREEN  test_a_registered_kind_is_found_by_its_name (+ unknown refused)  ·  2 passed

03:06  🔴 RED    test_task_in_the_foreground_ends_succeeded_with_its_result
       start(detach=False) roda no processo atual e termina succeeded
       barra passo 1 (d); cenário "esperar com --wait" (núcleo)
       ModuleNotFoundError: No module named 'wordcut.tasks.execution'

03:06  🟢 GREEN  test_task_in_the_foreground_ends_succeeded_with_its_result  ·  3 passed

03:07  🔴 RED    test_task_holds_the_lock_in_its_own_name_while_it_runs (+ free after)
       durante a tarefa a trava é dela (task_id, tipo, recurso); no fim, livre
       barra passo 1 (d); orquestrador 8 (LockHolder.task_id)
       assert None is not None

03:07  🟢 GREEN  test_task_holds_the_lock_in_its_own_name_while_it_runs (+ free after)  ·  327 passed
       LockHolder.task_id e HeldLock.assign; pwrite no 0 para reescrever o
       dono; test_status ganha "task_id": None; test_sermons_repository
       passa a exigir esquema >= 2 (a 0003 sobe a versão para 3)

03:07  🔴 RED    test_progress_reaches_the_listener_once_it_is_stored_in_the_database
       cada progresso ouvido já está no banco, lido por outra conexão
       barra passo 1 (e); decisão "Progresso" do plano
       TypeError: start() got an unexpected keyword argument 'on_progress'

03:07  🟢 GREEN  test_progress_reaches_the_listener_once_it_is_stored_in_the_database  ·  6 passed

03:08  🟢 GUARDA test_quick_reports_with_the_same_message_are_stored_once  ·  7 passed
       20 relatos rápidos com a mesma mensagem viram uma gravação; passa
       de primeira (limite já no GREEN anterior); mutação sem o limite: vermelha

03:08  🔴 RED    test_task_that_fails_ends_failed_with_its_error_and_raises_it
       fail_with vira failed com código, mensagem e details, e a exceção sobe
       barra passo 1 (f); decisão "Erro na tarefa" do plano
       AssertionError: assert ('youtube_err..., None, False) == (...: True}, True)

03:08  🟢 GREEN  test_task_that_fails_ends_failed_with_its_error_and_raises_it  ·  8 passed

03:09  🔴 RED    test_unexpected_exception_ends_failed_as_internal_error_without_its_text
       exceção comum vira internal_error, sem o texto dela no banco
       barra passo 1 (g); decisão "Erro na tarefa" do plano
       RuntimeError: diagnostic crash on sermon 12

03:09  🟢 GREEN  test_unexpected_exception_ends_failed_as_internal_error_without_its_text  ·  9 passed

03:09  🔴 RED    test_tasks_are_listed_newest_first_and_in_insertion_order_on_a_tie (+ filtros)
       repositório lista mais recentes primeiro, empate pelo id, com filtros
       orquestrador 13; barra passo 3 (a) no nível do repositório
       AttributeError: module 'wordcut.db.tasks' has no attribute 'newest_first'

03:09  🟢 GREEN  test_tasks_are_listed_newest_first_and_in_insertion_order_on_a_tie (+ filtros)  ·  5 passed

03:09  🟢 GUARDA test_busy_machine_refuses_a_locking_task_before_recording_it  ·  13 passed
       trava ocupada → busy e nenhuma linha em tasks; passa de primeira (a
       trava já vinha antes da linha); mata "criar a linha antes da trava"

03:09  🟢 GUARDA test_busy_refusal_names_the_task_holding_the_lock
       o busy de uma tarefa contra outra traz details.task_id do dono
       orquestrador 8; passa de primeira (asdict do LockHolder)

03:09  🟢 GUARDA test_lock_is_free_once_a_task_fails
       fail_with também solta a trava; mata "não soltar a trava em falha"

03:09  🔴 RED    test_task_without_lock_runs_while_another_process_holds_the_lock
       tipo com needs_lock=False roda enquanto lock_owner segura a trava
       borda do spec (suggest); orquestrador 7
       wordcut.errors.WordcutError: A máquina está ocupada com outro processamento.

03:09  🟢 GREEN  test_task_without_lock_runs_while_another_process_holds_the_lock  ·  13 passed

03:10  🔧 REFACTOR  _record separa gravar o fim de levantar o erro; mypy e
       ruff limpos

03:10  ✅ PASSO 1/5 — Modelo e execução em primeiro plano  ·  +18 testes  ·  suíte 338

--- Passo 2: Processo destacado ---

03:11  🔴 RED    test_detached_task_returns_at_once_while_it_keeps_running
       start(detach=True) volta bem antes dos 5 s da tarefa, ainda running
       barra passo 2 (a); FR-002; cenário "lançar e voltar na hora"
       AttributeError: module 'wordcut.tasks.execution' has no attribute 'Popen'
       (fixture detached_tasks nova na raiz: prazo SIGALRM, killpg e wait)

03:11  🟢 GREEN  test_detached_task_returns_at_once_while_it_keeps_running  ·  1 passed
       Popen em sessão própria, pass_fds com a trava, runner e adopt

03:11  🟢 GUARDA test_detached_task_ends_succeeded_by_itself_and_frees_the_lock  ·  2 passed
       o filho termina succeeded com result e a 1ª leitura de holder() é None
       barra passo 2 (d)(e); passa de primeira (runner veio no GREEN anterior)

03:12  🟢 GUARDA test_detached_task_runs_in_a_session_of_its_own_without_input  ·  5 passed
       getsid(pid) == pid e stdin em /dev/null; mutação sem
       start_new_session: vermelha (barra passo 2 b)

03:12  🟢 GUARDA test_detached_task_process_holds_the_lock_in_its_own_name
       holder() traz o PID do filho e o task_id; mutação "filho não
       reescreve o dono": vermelha (barra passo 2 c)

03:12  🟢 GUARDA test_unexpected_exception_in_a_detached_task_goes_to_its_log_only
       traceback no <home>/tasks/<id>.log, internal_error no banco (2 g)
       mutação "pai nunca fecha o descritor": vermelha no teste da trava livre

03:13  🟢 GUARDA test_busy_machine_launches_no_process_and_records_no_task  ·  8 passed
       trava ocupada: busy, Popen (espião) não chamado, sem linha nem log
       barra passo 2 (f); FR-003; cenário "máquina ocupada"

03:13  🟢 GUARDA test_busy_refusal_names_the_detached_task_holding_the_lock
       busy contra tarefa destacada traz details.task_id e o PID do filho

03:13  🔴 RED    test_task_whose_process_cannot_start_ends_failed_and_frees_the_lock
       Popen falhando não deixa a tarefa running para sempre
       orquestrador 5 (pid gravado no lançamento); robustez do lançador
       AssertionError: assert ('running', None, None) == ('failed', 'i..._error', None)

03:13  🟢 GREEN  test_task_whose_process_cannot_start_ends_failed_and_frees_the_lock  ·  8 passed

03:13  🟢 GUARDA test_launched_task_carries_the_pid_of_its_own_process  ·  9 passed
       a tarefa devolvida já traz Popen.pid (orquestrador 5)

03:13  ✅ PASSO 2/5 — Processo destacado  ·  +9 testes  ·  suíte 347
       pgrep wordcut.tasks.runner vazio depois da suíte

--- Passo 3: Consulta, espera e órfãs ---

03:13  🔴 RED    test_every_documented_error_code_maps_to_its_exit_code[interrupted-1]
       interrupted existe e sai com 1
       decisão "interrupted" do plano; barra passo 3 (e)
       ValueError: unknown error code: interrupted

03:13  🟢 GREEN  test_every_documented_error_code_maps_to_its_exit_code[interrupted-1]  ·  17 passed

03:14  🔴 RED    test_ctrl_c_during_a_foreground_task_ends_it_interrupted_and_frees_the_lock
       Ctrl+C (Timer + interrupt_main) com a tarefa rodando: failed,
       interrupted, finished_at, trava livre e KeyboardInterrupt sobe
       docs/cli.md §6.5; orquestrador 11; barra passo 4 (d) no core
       AssertionError: assert ('running', None, False, None) == ('failed', 'i...', True, None)

03:14  🟢 GREEN  test_ctrl_c_during_a_foreground_task_ends_it_interrupted_and_frees_the_lock  ·  14 passed

03:14  🔴 RED    test_shown_task_has_kind_status_resource_times_progress_error_and_result
       show_task traz tipo, estado, <recurso>_id, tempos, progresso, erro e result
       barra passo 3 (b); docs/cli.md §10; orquestrador 9 (<resource_type>_id)
       ModuleNotFoundError: No module named 'wordcut.service.tasks'

03:14  🟢 GREEN  test_shown_task_has_kind_status_resource_times_progress_error_and_result  ·  15 passed

03:14  🔴 RED    test_showing_a_task_that_does_not_exist_is_not_found
       ID inexistente → not_found (saída 3) com details.task_id
       borda do spec; barra passo 3 (b)
       AssertionError (assert task is not None)

03:14  🟢 GREEN  test_showing_a_task_that_does_not_exist_is_not_found  ·  16 passed

03:14  🔴 RED    test_tasks_are_listed_newest_first_only_of_the_status_and_kind_asked_for
       list_tasks: mais recentes primeiro, filtros de estado e tipo
       barra passo 3 (a); FR-005; orquestrador 13
       ImportError: cannot import name 'list_tasks'

03:14  🟢 GREEN  test_tasks_are_listed_newest_first_only_of_the_status_and_kind_asked_for  ·  17 passed

03:15  🔴 RED    test_waiting_for_a_succeeded_task_gives_its_result_at_once (+ failed raises)
       wait_task devolve o result; de tarefa failed, levanta o erro dela
       barra passo 3 (c); FR-005; mata "wait_task devolve sucesso em failed"
       ImportError: cannot import name 'wait_task'

03:15  🟢 GREEN  test_waiting_for_a_succeeded_task_gives_its_result_at_once (+ failed raises)  ·  19 passed

03:15  🟢 GUARDA test_waiting_for_a_detached_task_follows_its_progress_and_frees_the_lock_first  ·  10 passed
       wait_task acompanha o progresso do filho, devolve o result e a 1ª
       leitura de holder() depois é None (orquestrador 6; barra "trava livre")

03:16  🔴 RED    test_running_task_whose_process_is_gone_is_shown_failed_as_interrupted
       running com PID morto no mesmo host → failed/interrupted com fim, no show
       FR-006; barra passo 3 (d); mata "sem reconciliação em show"
       TypeError: 'NoneType' object is not subscriptable

03:16  🟢 GREEN  test_running_task_whose_process_is_gone_is_shown_failed_as_interrupted  ·  20 passed
       tasks/processes.py (is_running com zumbi, this_host); orquestrador 3 e 4

03:16  🟢 GUARDA órfã em list, em wait (interrupted, saída 1), PID de outro usuário,
       outro host, dono da trava e zumbi  ·  26 passed
       passam de primeira (reconciliação veio no GREEN anterior); mutações
       sem zumbi, PermissionError→morto, sem dono da trava e sem host:
       todas vermelhas (orquestrador 3 e 4; barra passo 3 d)

03:17  🟢 GUARDA test_killed_task_process_is_shown_failed_as_interrupted_at_the_next_read  ·  11 passed
       killpg SIGKILL do filho, colhido, e o show seguinte dá failed/interrupted
       cenário "tarefa órfã"; barra passo 3 (d) com processo real

03:17  🔴 RED    test_status_lists_the_running_detached_task_and_names_it_as_the_lock_holder
       (+ test_status_shows_no_running_task_whose_process_is_gone)
       status traz lock.task_id e running_tasks, já sem as órfãs
       FR-007; barra passo 3 (d) "em status"; cenário "status mostra a tarefa"
       KeyError: 'running_tasks'

03:17  🟢 GREEN  test_status_lists_the_running_detached_task_and_names_it_as_the_lock_holder  ·  9 passed
       testes antigos de status só ganham "running_tasks": []

03:18  ✅ PASSO 3/5 — Consulta, espera e órfãs  ·  +17 testes  ·  suíte 365
       test_status_command ganha "running_tasks": [] nos dois JSON exatos

--- Passo 4: CLI ---

03:18  🔴 RED    test_task_show_prints_the_task_in_json
       wordcut task show <id> --json imprime o objeto da tarefa
       FR-005; barra passo 4 (b)
       AssertionError: assert (2, {'error':... 'command'}}}) == (0, {...})

03:18  🟢 GREEN  test_task_show_prints_the_task_in_json  ·  1 passed

03:19  🟢 GUARDA test_task_show_of_a_missing_task_is_not_found_with_exit_3 (+ texto)
       inexistente → objeto de erro not_found, saída 3; texto em português

03:19  🔴 RED    test_task_list_prints_the_tasks_of_the_status_and_kind_asked_for
       wordcut task list --status S --json → {"items": [...]}
       FR-005; barra passo 4 (a)
       KeyError: 'items'

03:19  🟢 GREEN  test_task_list_prints_the_tasks_of_the_status_and_kind_asked_for  ·  4 passed

03:19  🟢 GUARDA status/kind fora das escolhas → 2; --json antes ou depois; texto
       da lista; diagnostic fora do --help  ·  9 passed
       barra passo 4 (a)(g); orquestrador 12

03:19  🔴 RED    test_task_wait_shows_progress_on_stderr_and_the_result_on_stdout
       task wait de tarefa destacada: [diagnostic] … % no stderr, result no
       stdout (json.loads do stdout inteiro), saída 0
       cenário "esperar uma tarefa lançada"; barra passo 4 (c); orquestrador 11
       AssertionError: assert (2, {'error':...ion'}}}, None) == (0, {...}, <ANY>)

03:19  🟢 GREEN  test_task_wait_shows_progress_on_stderr_and_the_result_on_stdout  ·  10 passed
       (asserção trocada de ANY para "is not None": ANY aceitaria None)

03:20  🟢 GUARDA task wait de tarefa failed (objeto de erro, saída 6), Ctrl+C no
       task wait (130 e a tarefa termina succeeded), --quiet sem progresso
       ·  13 passed; borda do spec; barra passo 4 (c)(e)

03:20  🔴 RED    test_launch_without_wait_answers_at_once_with_the_running_task
       comando de teste (add_command + add_wait_option + launch via execute)
       sem --wait → {"task_id","kind","status":"running","sermon_id":12}
       docs/cli.md §6.2; orquestrador 9; barra passo 4 (d)
       ImportError: cannot import name 'add_wait_option'

03:20  🟢 GREEN  test_launch_without_wait_answers_at_once_with_the_running_task  ·  14 passed

03:21  🟢 GUARDA --wait: progresso no stderr e result no stdout, pid = pytest
       (FR-004); fail_with → 5; Ctrl+C → 130 com failed/interrupted e trava
       livre; --quiet; busy → 4 sem tarefa  ·  19 passed
       mutações "progresso no stdout" e "--quiet ignorado": vermelhas

03:22  🔴 RED    test_status_without_json_cites_the_task_and_the_running_tasks
       (+ JSON com lock.task_id e running_tasks: guarda)
       texto do status cita "tarefa N" e lista as tarefas em andamento
       FR-007; barra passo 4 (f); cenário "status mostra a tarefa"
       AssertionError: assert None (re.fullmatch sem "tarefa 1," nem a lista)

03:22  🟢 GREEN  test_status_without_json_cites_the_task_and_the_running_tasks  ·  98 passed
       test_cli: COMMANDS ganha "task" (o grupo novo aparece no --help)

03:23  🔧 REFACTOR  start ganha docstring de contrato e _create; resource_label
       e percent passam para tasks_support (task e status); suíte 386

03:23  ✅ PASSO 4/5 — CLI  ·  +21 testes  ·  suíte 386
       pgrep wordcut.tasks.runner vazio; ruff e mypy limpos

--- Passo 5: Documentação ---

03:25  📝 DOCS   ADR-0013 (complementa a 0007, sem editá-la) e índice;
       architecture §4 (Tarefas existe; serviço e CLI) e §5.1 (lançador trava,
       filho herda, solta antes de gravar o fim); cli.md §5.1/§5.3 com
       interrupted, §6.5, §10, §14 (tasks/<id>.log); CHANGELOG; README
       sem TDD: documentação (§6.2 já batia com o código: sermon_id)

03:25  ✅ PASSO 5/5 — Documentação  ·  +0 testes  ·  suíte 386

03:26  🏁 FIM     suíte 386 passed; ruff, format e mypy limpos; 5 repetições
       de test_task_detached + test_task_command + test_tasks verdes (56
       cada); pgrep wordcut.tasks.runner vazio antes e depois; wheel do
       core traz 0003_tasks.sql e wordcut/tasks/runner.py; sem commit
       (override do orquestrador)

## Rodada 1 · QA

03:27  📊 SUÍTE  386 passed  ·  0 failed  (baseline 5249c8b: 320 passed)
       ruff check, ruff format --check e mypy limpos aqui e no baseline;
       pgrep wordcut.tasks.runner vazio antes e depois; 18 s, sem pendurar

03:28  📊 SUÍTE  5 repetições de test_task_detached + test_task_command +
       test_tasks  ·  56 passed em cada, 0 failed; pgrep vazio depois

03:28  📊 SUÍTE  wheel do core traz db/migrations/0003_tasks.sql e
       wordcut/tasks/runner.py (e diagnostic, execution, processes)

03:29  ⚠️ LACUNA  mutação no lugar recusada pela permissão do ambiente
       os arquivos são não commitados; mutações rodadas numa cópia da
       árvore no scratchpad, com .venv própria; árvore real conferida
       por sha256 depois: intacta

03:31  🧬 MUTAÇÕES · exigidas pela barra  ·  14 de 14 mortas
       ☠️  progresso não gravado no banco                     1 teste
       ☠️  internal_error com o texto da exceção               1 teste
       ☠️  linha criada antes da trava (primeiro plano)        1 teste
       ☠️  linha criada antes da trava (destacado)             1 teste
       ☠️  trava não solta em falha (os.dup do descritor)      1 teste
       ☠️  Popen sem start_new_session                         1 teste
       ☠️  pai guarda cópia do descritor (os.dup)              1 teste
       ☠️  filho não reescreve o dono com o próprio PID        1 teste
       ☠️  show sem reconciliar órfã                           1 teste
       ☠️  wait_task devolve sucesso em failed                 1 teste
       ☠️  interrupted → 5                                     1 teste
       ☠️  progresso no stdout                                 1 teste
       ☠️  --quiet ignorado                                    1 teste
       ☠️  Ctrl+C em task wait marca failed                    1 teste
       "não soltar em falha" e "pai não fecha" na forma ingênua (tirar
       release) são equivalentes: o acquire fecha de novo no finally

03:33  🧬 MUTAÇÕES · decisões do orquestrador  ·  10 de 12 mortas
       ☠️  zumbi conta como vivo (3)                           1 teste
       ☠️  PermissionError conta como morto (3)                1 teste
       ☠️  host ignorado (4)                                   1 teste
       ☠️  dono da trava ignorado (4)                          1 teste
       ☠️  Popen.pid não gravado (5)                           2 testes
       ☠️  filho grava o fim e só solta 0,3 s depois (6)       1 teste
       ☠️  needs_lock ignorado (7)                             1 teste
       ☠️  task_id fora do dono e do busy (8)                  1 teste
       ☠️  saída resource_id em vez de <resource_type>_id (9)  1 teste
       ☠️  task list em ordem crescente (13)                   1 teste
       🚨  filho grava o fim e solta logo em seguida (6)  SOBREVIVEU — a
           janela é de microssegundos e o teste lê o banco a 50 ms; o
           código segue a ordem (resume grava fora do with), 3 de 3 vivas
       🚨  primeiro plano grava o fim antes de soltar (6)  SOBREVIVEU —
           start só volta depois das duas coisas; só outro processo
           veria a diferença, e nenhum teste observa isso

03:34  🔎 QA     passo 1/5 — Modelo e execução em primeiro plano  ·  ✅ PASS
       migração 3 com params e host, esquema 2 migra; registro, trava com
       task_id, progresso, erros, busy e needs_lock com testes que matam

03:34  🔎 QA     passo 2/5 — Processo destacado  ·  ✅ PASS
       getsid, stdin nulo, log, dono = filho, trava livre depois, busy sem
       Popen nem linha nem log; fixture detached_tasks com prazo e killpg

03:34  🔎 QA     passo 3/5 — Consulta, espera e órfãs  ·  ✅ PASS
       list/show/wait com filtros e ordem; órfã em show, list, wait e
       status, com zumbi, host, dono e PermissionError; interrupted → 1

03:34  🔎 QA     passo 4/5 — CLI  ·  ✅ PASS
       task list/show/wait, launch pelo execute com 130, --quiet, busy 4,
       status em JSON e texto; diagnostic fora do --help e do --kind

03:34  🔎 QA     passo 5/5 — Documentação  ·  ✅ PASS
       ADR-0013 nova (0007 intacta), índice, arquitetura §4 e §5.1,
       cli.md §5.1, §5.3, §6.5, §10, §14 e CHANGELOG batem com o código

03:35  🔎 QA     fato do implementador — test_sermons_repository == 2 → >= 2
       aceito: a barra exige user_version 3 (passo 1 a), o que quebra o
       == 2; a intenção (0002 aplicada, sermons legível) fica, e o 3 exato
       é provado em test_tasks_repository; o nome "schema_version_2" ficou
