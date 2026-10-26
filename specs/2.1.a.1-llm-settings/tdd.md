## Plano de QA

baseline_commit 9b946d77005e523f5857fcee683a02ab553a6d3f

05:08  📐 BARRA   segredo gravado com 600, pasta 700, atômico
       test_secrets.py com os.stat e umask aberta no teste; sem a
       umask aberta a do ambiente esconde o modo errado

05:08  🧬 EXIGE   os.open sem 0o600 (modo padrão)  ·  vermelha
       prova que o modo vem do código e não da umask

05:08  🧬 EXIGE   escrita no lugar, sem temporário + os.replace  ·  vermelha
       prova a atomicidade: os.replace falhando mantém o conteúdo antigo

05:08  📐 BARRA   máscara "••••"+4 últimos; "••••" abaixo de 8 caracteres
       unidade pela interface pública; fronteira 7 e 8 caracteres

05:08  🧬 EXIGE   len >= 8 trocado por len > 8  ·  vermelha
       sobreviver = fronteira sem teste

05:08  📐 BARRA   show de instalação nova igual ao dict do cenário 1
       igualdade exata no serviço e no settings show --json

05:08  🧬 EXIGE   chave gravada também no SQLite  ·  vermelha
       teste procura a chave fictícia nos bytes do .db e do -wal (§VI)

05:08  📐 BARRA   chave fora de stdout e stderr em todo caminho
       CLI por main(argv) + capsys; sucesso, erro, --json e texto

05:08  🧬 EXIGE   render do show imprimindo a chave  ·  vermelha
       sobreviver = vazamento sem teste

05:08  📐 BARRA   terminal → getpass; redirecionado → stdin.read
       dublês de sys.stdin.isatty e getpass.getpass

05:08  🧬 EXIGE   ler sempre sys.stdin.read()  ·  vermelha
       prova que o caminho sem eco existe

05:08  📐 BARRA   processamento usa whisper_model(conn)
       dublê de default_gateways captura o modelo: "medium" e o padrão

05:08  🧬 EXIGE   "large-v3" fixo no processamento  ·  vermelha
       sobreviver = FR-005 sem cobertura

05:08  ⚠️ LACUNA  config_not_writable fora de EXIT_CODES e de cli.md §5.3
       WordcutError rejeita código desconhecido (ValueError); sem o
       código e a doc, Passos 1 e 5 ficam PARCIAL

05:08  ⚠️ LACUNA  erro de uso ecoa o argumento recusado
       contract._usage_error põe o valor na mensagem e em details;
       settings set-key <chave> vazaria a chave; ecoar = FAIL no Passo 3

05:08  ⚠️ LACUNA  set-cookies com terminal via getpass lê uma linha só
       conservador: recusar com invalid_argument pedindo o redirecionamento
       (ou ler até EOF sem eco); truncar = FAIL no Passo 3

05:08  ⚠️ LACUNA  settings set sem opção ou com valor vazio não decidido
       conservador: invalid_argument com details.argument, nada alterado

05:08  ⚠️ LACUNA  ponto de uso do modelo do WhisperX sem assinatura
       mudar default_gateways() quebra dublês sem argumento (conftest
       raiz, test_process_task, test_processing_service, CLI process);
       Passo 4 só PASS com os dublês ajustados e a suíte verde

05:08  ⚠️ LACUNA  nome do temporário do O_EXCL não definido
       nome fixo falha após queda anterior; temporário órfão não pode
       bloquear a gravação (Passo 1)

05:08  ⚠️ LACUNA  read_llm_key() sem chamador nesta issue
       código morto pelo CONTRIBUTING §4; entra com teste de ida e volta
       ou fica para 2.1.b.1

05:08  ⚠️ LACUNA  nenhuma fixture isola WORDCUT_CONFIG em toda a suíte
       wordcut_home não é autouse e não cobre a pasta de segredos;
       pedir fixture autouse no conftest raiz; tocar ~/.config = FAIL

05:08  ⚠️ LACUNA  formato Netscape dos cookies não definido
       barra: ao menos uma linha não comentada com 7 campos por TAB;
       cabeçalho não exigido

05:08  ⚠️ LACUNA  test_cli.py::COMMANDS lista os comandos fixos
       registrar settings exige atualizar o teste; help de admin com
       "administrador" e exemplo (cli.md §3.2, §3.5) fora do plano

## Rodada 1 · implementador

05:12  🔴 RED    test_a_secret_is_written_readable_only_by_its_owner
       write_secret grava o segredo com modo 0o600 mesmo com umask 0o022
       Passo 1 (a); FR-003; plano: arquivos de segredo com 600
       ImportError: cannot import name 'write_secret' from 'wordcut.config'

05:12  🟢 GREEN  test_a_secret_is_written_readable_only_by_its_owner  ·  1 passed

05:12  🔴 RED    test_a_missing_secrets_folder_is_created_private_to_its_owner
       WORDCUT_CONFIG ausente é criada com 0o700 ao gravar o segredo
       Passo 1 (b); plano: pasta criada com 0700
       AssertionError: assert 493 == 448

05:12  🟢 GREEN  test_a_missing_secrets_folder_is_created_private_to_its_owner  ·  2 passed

05:12  🔴 RED    test_rewriting_an_open_secret_leaves_only_the_new_content_private
       sobrescrever arquivo 0o644 deixa o conteúdo novo e o modo 0o600
       Passo 1 (c); FR-003
       passou sem produção nova: o temporário + os.replace do 1º ciclo já
       cobre; mutação "escrita no lugar" deixa este teste vermelho (2 failed)

05:12  🟢 GREEN  test_rewriting_an_open_secret_leaves_only_the_new_content_private  ·  3 passed

05:13  🔴 RED    test_a_failed_replace_keeps_the_previous_secret_and_leaves_no_temporary_file
       com os.replace falhando, o segredo anterior fica e nenhum temporário sobra
       Passo 1 (d); FR-003 (atômico)
       AssertionError: assert [('openrouter...ia-0000abcd')] == [('openrouter...antiga-1111')]

05:13  🟢 GREEN  test_a_failed_replace_keeps_the_previous_secret_and_leaves_no_temporary_file  ·  4 passed

05:13  🔴 RED    test_a_temporary_file_left_by_an_interrupted_write_does_not_block_the_next_one
       um temporário órfão de gravação anterior não impede a próxima
       Passo 1 (d); decisão 6 do orquestrador (mkstemp, nome único)
       passou sem produção nova: mkstemp já dá nome único; a mutação
       "nome fixo .tmp com O_EXCL" o deixa vermelho (FileExistsError)

05:13  🟢 GREEN  test_a_temporary_file_left_by_an_interrupted_write_does_not_block_the_next_one  ·  5 passed

05:13  🔴 RED    test_every_documented_error_code_maps_to_its_exit_code[config_not_writable-5]
       o código config_not_writable existe e sai com 5
       Passo 1 (h); decisão 1 do orquestrador
       ValueError: unknown error code: config_not_writable

05:13  🟢 GREEN  test_every_documented_error_code_maps_to_its_exit_code[config_not_writable-5]  ·  20 passed

05:13  🔴 RED    test_a_read_only_secrets_folder_is_a_clear_error_without_the_secret
       pasta sem escrita (0o500) → WordcutError config_not_writable, saída 5,
       sem o segredo no erro
       Passo 1 (h); caso de borda "pasta somente leitura"; Verificação 6
       PermissionError: [Errno 13] Permission denied: '.../config/tmpzkvpetuz'

05:13  🟢 GREEN  test_a_read_only_secrets_folder_is_a_clear_error_without_the_secret  ·  6 passed

05:14  🔴 RED    test_llm_key_file_is_in_the_secrets_folder
       a chave do LLM fica em WORDCUT_CONFIG/openrouter-key
       Passo 1 (e); plano: arquivos de segredo
       ImportError: cannot import name 'llm_key_file' from 'wordcut.config'

05:14  🟢 GREEN  test_llm_key_file_is_in_the_secrets_folder  ·  4 passed

05:14  🔴 RED    test_the_masked_key_shows_only_its_last_four_characters
       a chave gravada aparece só como "••••" + 4 últimos
       Passo 1 (f); FR-004; cenário "gravar a chave pelo stdin"
       ImportError: cannot import name 'masked_llm_key' from 'wordcut.config'

05:14  🟢 GREEN  test_the_masked_key_shows_only_its_last_four_characters  ·  7 passed

05:14  🔴 RED    test_without_a_stored_key_there_is_no_masked_key
       sem chave gravada, a máscara é None
       Passo 1 (f); cenário "ver as configurações" (llm_key: null)
       FileNotFoundError: [Errno 2] No such file or directory: '.../config/openrouter-key'

05:14  🟢 GREEN  test_without_a_stored_key_there_is_no_masked_key  ·  8 passed

05:14  🔴 RED    test_a_key_shorter_than_eight_characters_is_masked_whole[7 chars]
       chave com 7 caracteres vira só "••••"; com 8, "••••" + 4 últimos
       Passo 1 (f); plano: máscara; fronteira 7/8 (mutação >= 8 → > 8)
       AssertionError: assert '••••1234' == '••••'

05:14  🟢 GREEN  test_a_key_shorter_than_eight_characters_is_masked_whole  ·  10 passed
       mutação "< 8" → "<= 8" conferida: 1 failed

05:14  🔴 RED    test_cookies_are_present_only_once_stored
       has_youtube_cookies é falso numa instalação nova e verdadeiro depois
       Passo 1 (g); FR-001 (presença dos cookies)
       ImportError: cannot import name 'has_youtube_cookies' from 'wordcut.config'

05:14  🟢 GREEN  test_cookies_are_present_only_once_stored  ·  11 passed

05:15  🔧 REFACTOR  docstring de config.py corrigida (lê a chave só para mascarar
       e chamar o LLM); fd aberto antes do fchmod; teste de atomicidade espera
       WordcutError. Mutação "sem except OSError" conferida: 2 failed.
       Nota: o 0o600 vem do fchmod explícito e também do mkstemp; tirar só o
       fchmod não muda o modo (mkstemp já cria 0o600), então essa mutação
       sobrevive por construção, não por falta de teste.

05:15  ✅ PASSO 1/5 — Segredos  ·  +13 testes  ·  suíte 529

05:16  🔴 RED    test_a_new_installation_has_only_the_whisperx_model_set
       show_settings numa instalação nova devolve exatamente o dict do cenário 1
       Passo 2 (b); cenário "ver as configurações"; FR-001
       ModuleNotFoundError: No module named 'wordcut.service.settings'

05:16  🟢 GREEN  test_a_new_installation_has_only_the_whisperx_model_set  ·  1 passed
       migração 0005_settings.sql (tabela settings chave-valor) e db/settings.py

05:16  🔴 RED    test_a_changed_model_is_kept_after_reopening_and_the_other_stays
       update_settings parcial muda só o campo dado e persiste ao reabrir
       Passo 2 (c); FR-002; cenário "trocar modelos"
       ImportError: cannot import name 'update_settings' from 'wordcut.service.settings'

05:17  🟢 GREEN  test_a_changed_model_is_kept_after_reopening_and_the_other_stays  ·  2 passed

05:17  🔴 RED    test_setting_no_model_or_an_empty_one_is_refused_and_changes_nothing
       set sem modelo, ou com modelo vazio/em branco → invalid_argument com
       details.argument, configurações intactas
       Passo 2 (c); decisão 4 do orquestrador
       Failed: DID NOT RAISE WordcutError (3 casos)

05:17  🟢 GREEN  test_setting_no_model_or_an_empty_one_is_refused_and_changes_nothing  ·  5 passed

05:17  🔴 RED    test_a_stored_key_is_shown_masked_without_the_blanks_around_it
       store_llm_key grava sem brancos das pontas; show traz só "••••abcd"
       Passo 2 (d); cenário "gravar a chave pelo stdin"; FR-004
       ImportError: cannot import name 'store_llm_key' from 'wordcut.service.settings'

05:17  🟢 GREEN  test_a_stored_key_is_shown_masked_without_the_blanks_around_it  ·  6 passed
       mutação "strip() removido" conferida: 1 failed

05:17  🔴 RED    test_an_empty_key_is_refused_and_nothing_is_stored
       chave vazia ou em branco → invalid_argument; nada gravado
       Passo 2; caso de borda "set-key sem nada no stdin"; Verificação 5
       Failed: DID NOT RAISE WordcutError (2 casos)

05:17  🟢 GREEN  test_an_empty_key_is_refused_and_nothing_is_stored  ·  8 passed

05:18  🔴 RED    test_the_key_stays_out_of_the_shown_settings_and_of_the_database
       a chave não aparece em nenhum valor do show nem nos bytes do .db/-wal
       Passo 2 (d); FR-004; constituição §VI
       passou sem produção nova (a chave nunca passa pelo banco); mutação
       "chave gravada no SQLite" conferida: 1 failed

05:18  🟢 GREEN  test_the_key_stays_out_of_the_shown_settings_and_of_the_database  ·  9 passed

05:18  🔴 RED    test_stored_cookies_are_kept_as_they_came_and_shown_only_as_present
       cookies válidos gravados byte a byte (com \r\n) e show com youtube_cookies true
       Passo 2 (e); cenário "gravar os cookies pelo stdin"
       ImportError: cannot import name 'store_youtube_cookies' from 'wordcut.service.settings'

05:18  🟢 GREEN  test_stored_cookies_are_kept_as_they_came_and_shown_only_as_present  ·  10 passed

05:18  🔴 RED    test_cookies_without_a_netscape_line_are_refused_and_nothing_is_stored
       cookies vazios, em branco, só comentários, em formato de cabeçalho ou
       com 6 campos → invalid_argument; nada gravado
       Passo 2 (e); decisão 9 do orquestrador (7 campos por TAB)
       Failed: DID NOT RAISE WordcutError (5 casos)

05:18  🟢 GREEN  test_cookies_without_a_netscape_line_are_refused_and_nothing_is_stored  ·  15 passed

05:18  🔴 RED    test_the_whisperx_model_to_use_is_large_v3_until_another_is_set
       whisper_model(conn) = "large-v3" por padrão e o valor gravado depois
       Passo 2 (f); FR-005 (base do Passo 4)
       ImportError: cannot import name 'whisper_model' from 'wordcut.service.settings'

05:19  🟢 GREEN  test_the_whisperx_model_to_use_is_large_v3_until_another_is_set  ·  16 passed

05:19  🔧 REFACTOR  show_settings passa por llm_model()/whisper_model(); comentário
       da fonte do formato Netscape; ruff format. Mutação "validação Netscape
       removida" derruba os 5 casos de recusa.

05:19  ✅ PASSO 2/5 — Tabela e serviço  ·  +16 testes  ·  suíte 545

05:20  🔴 RED    test_show_of_a_new_installation_has_only_the_whisperx_model_set
       wordcut settings show --json numa instalação nova → saída 0 e o dict exato
       Passo 3 (a); cenário "ver as configurações"; Verificação 1
       AssertionError: At index 0 diff: 2 != 0 (comando inexistente)

05:20  🟢 GREEN  test_show_of_a_new_installation_has_only_the_whisperx_model_set  ·  1 passed
       test_cli.py::COMMANDS passa a listar settings (decisão 10)

05:21  🔴 RED    test_set_changes_both_models_and_show_reflects_them
       settings set --model x --whisper-model y → saída 0 e refletido no show
       Passo 3 (b); cenário "trocar modelos"; FR-002; Verificação 2
       AssertionError: At index 0 diff: 2 != 0 (ação set inexistente)

05:21  🟢 GREEN  test_set_changes_both_models_and_show_reflects_them  ·  2 passed

05:21  🔴 RED    test_set_key_reads_the_key_from_redirected_stdin_into_a_private_file
       set-key < arquivo → saída 0, arquivo 0o600 e show com "••••abcd"
       Passo 3 (c); cenário "gravar a chave pelo stdin"; FR-003; Verificação 3
       FileNotFoundError: ... '.../config/openrouter-key' (ação set-key inexistente)

05:21  🟢 GREEN  test_set_key_reads_the_key_from_redirected_stdin_into_a_private_file  ·  3 passed

05:21  🔴 RED    test_set_key_on_a_terminal_reads_the_key_without_echo
       com stdin de terminal, set-key lê por getpass (sem eco), não por read
       Passo 3 (e); caso de borda "stdin de terminal"; docs/cli.md §3.2
       AssertionError: assert (1, None) == (0, '••••abcd')

05:22  🟢 GREEN  test_set_key_on_a_terminal_reads_the_key_without_echo  ·  4 passed

05:22  🔴 RED    test_the_key_appears_in_no_output_of_set_key_nor_of_show[json|text]
       a chave fictícia não aparece em stdout nem stderr de set-key e show
       Passo 3 (c); FR-004; caso de borda "chave nunca em saída"
       passou sem produção nova (o serviço só devolve a máscara); a mutação
       do render vem com o próximo teste

05:22  🟢 GREEN  test_the_key_appears_in_no_output_of_set_key_nor_of_show  ·  6 passed

05:22  🔴 RED    test_show_without_json_describes_a_new_installation_in_portuguese
       settings show sem --json descreve as configurações em português
       Passo 3; docs/cli.md §4.2
       AssertionError: assert (0, "{'llm_model': None, ...}\n") == (0, 'Modelo do LLM: ...')

05:22  🟢 GREEN  test_show_without_json_describes_a_new_installation_in_portuguese  ·  7 passed
       mutação "render imprime a chave" conferida: 2 failed (vazamento em texto)

05:22  🔴 RED    test_set_cookies_reads_the_cookies_from_redirected_stdin_into_a_private_file
       set-cookies < arquivo → saída 0, arquivo 0o600 e youtube_cookies true
       Passo 3 (f); cenário "gravar os cookies pelo stdin"; Verificação 4
       FileNotFoundError: ... '.../config/youtube-cookies.txt' (ação inexistente)

05:23  🟢 GREEN  test_set_cookies_reads_the_cookies_from_redirected_stdin_into_a_private_file  ·  8 passed

05:23  🔴 RED    test_set_cookies_on_a_terminal_asks_for_the_file_to_be_redirected
       set-cookies com stdin de terminal → invalid_argument pedindo
       "wordcut settings set-cookies < arquivo"; nada truncado em uma linha
       Passo 3; decisão 3 do orquestrador
       AssertionError: assert (1, 'internal_error', False) == (2, 'invalid_argument', True)

05:23  🟢 GREEN  test_set_cookies_on_a_terminal_asks_for_the_file_to_be_redirected  ·  9 passed

05:23  🔴 RED    test_an_empty_stdin_is_refused_and_nothing_is_stored[set-key|set-cookies × empty|blank]
       stdin vazio ou só espaços → saída 2, invalid_argument, arquivo inexistente
       Passo 3 (d); caso de borda "set-key sem nada no stdin"; Verificação 5
       passou sem produção nova: a recusa está no serviço (Passo 2)

05:23  🟢 GREEN  test_an_empty_stdin_is_refused_and_nothing_is_stored  ·  13 passed

05:23  🔴 RED    test_a_secret_given_as_argument_is_refused_without_being_echoed
       segredo como argumento (posicional, --key x, --key=x) em set-key e
       set-cookies → saída 2, nada gravado, valor ausente de stdout e stderr
       Passo 3 (g); decisão 2 do orquestrador; docs/cli.md §16
       assert (2, True, False) == (2, False, False)  ·  8 failed (posicional e
       --key=x ecoam o valor em "Argumento não reconhecido")

05:24  🟢 GREEN  test_a_secret_given_as_argument_is_refused_without_being_echoed  ·  25 passed
       contract.execute usa parse_known_args; comando com reads_secret recusa
       argumento sobrando com mensagem genérica e details {"argument": "stdin"}

05:24  🔴 RED    test_set_key_into_a_read_only_folder_is_a_config_not_writable_error
       + test_the_read_only_folder_error_does_not_carry_the_key[json|text]
       pasta somente leitura → saída 5, {"error": {"code": "config_not_writable"}},
       chave ausente de stdout e stderr
       Passo 3 (h); caso de borda "pasta somente leitura"; Verificação 6
       passou sem produção nova: write_secret (Passo 1) já converte o OSError

05:24  🟢 GREEN  test_the_read_only_folder_error_does_not_carry_the_key  ·  28 passed

05:25  🔴 RED    test_each_settings_action_help_says_it_is_for_the_administrator_with_an_example
       + test_set_without_any_model_is_an_invalid_argument_naming_the_options
       --help de cada ação diz "administrador" e traz exemplo; set sem opção →
       saída 2, invalid_argument com details.argument
       Passo 3 (i); decisões 4 e 10; docs/cli.md §3.2, §3.5
       passaram sem produção nova: ajuda escrita junto com cada ação; a recusa
       do set está no serviço (Passo 2)

05:25  🟢 GREEN  test_each_settings_action_help_..., test_set_without_any_model_...  ·  33 passed

05:25  🔧 REFACTOR  testes de pasta somente leitura separados (código e vazamento);
       ruff format. Mutações conferidas no passo: render imprimindo a chave
       (2 failed); ler sempre sys.stdin.read() derruba o teste do terminal
       (Terminal.read falha).

05:25  ✅ PASSO 3/5 — CLI  ·  +33 testes  ·  suíte 578

05:26  🔴 RED    test_the_task_transcribes_with_the_configured_whisperx_model[default|set]
       a tarefa process monta os gateways com whisper_model(conn): "large-v3"
       sem configuração, "medium" depois de settings set --whisper-model medium
       Passo 4; FR-005; decisão 5 do orquestrador
       WordcutError: Erro interno inesperado na tarefa. (TypeError: o dublê
       exige o modelo e default_gateways() é chamado sem ele)  ·  2 failed

05:27  🟢 GREEN  test_the_task_transcribes_with_the_configured_whisperx_model  ·  5 passed
       default_gateways(whisper_model) → LocalTranscriber(whisper_model); a
       tarefa lê whisper_model(conn); dublês ajustados em conftest.py,
       test_process_task.py, test_processing_service.py e
       test_sermon_process_command.py (aceitam o modelo)

05:27  🔧 REFACTOR  o modelo é lido antes de a pregação virar "processing";
       parâmetro renomeado (transcription_model) para não esconder a função;
       docstrings de default_gateways e de tasks/process.py sem "large-v3" fixo.
       Mutação "large-v3" fixo na tarefa conferida: 1 failed.

05:27  ✅ PASSO 4/5 — Uso  ·  +2 testes  ·  suíte 580

05:28  📝 DOCS   Passo 5 sem TDD (documentação): docs/architecture/README.md §4
       (tabela settings/migração 0005, service.settings, wordcut settings,
       default_gateways(whisper_model)), docs/cli.md §5.3 (config_not_writable,
       saída 5), CHANGELOG (Adicionado e Alterado), SECURITY.md (openrouter-key,
       youtube-cookies.txt, 600, só stdin); docstring de config.py já corrigida
       no Passo 1

05:28  ✅ PASSO 5/5 — Documentação  ·  +0 testes  ·  suíte 580

## Rodada 1 · QA

05:29  📊 SUÍTE  580 passed  ·  0 failed
       uv run pytest -q; ruff check, ruff format --check e mypy limpos

05:31  🧬 MUTAÇÕES · passo 1 (config.py, cópia no scratchpad)  ·  11 de 12 mortas
       ☠️  fchmod 0o644 no lugar do 0o600                     1 teste
       ☠️  escrita no lugar, sem temporário + os.replace      1 teste
       ☠️  temporário de nome fixo com O_EXCL                 1 teste
       ☠️  sem unlink do temporário na falha                  1 teste
       ☠️  pasta criada sem 0o700                             1 teste
       ☠️  máscara < 8 → <= 8 e < 8 → < 7                     1 teste cada
       ☠️  máscara devolve a chave inteira                    1 teste
       ☠️  sem except OSError                                 1 teste
       ☠️  erro de pasta sem escrita carrega o conteúdo       1 teste
       ☠️  has_youtube_cookies sempre verdadeiro              1 teste
       🚨  tirar o fchmod     SOBREVIVEU — equivalente aceita pelo orquestrador:
       mkstemp já cria 0o600; as duas provas exigidas existem (umask 0o022
       → 0o600; 644 sobrescrito → 600). Só difere com umask que tira bits
       do dono (ex.: 0o277), fora da barra

05:31  🔎 QA     passo 1/5 — Segredos  ·  ✅ PASS
       matriz (a)–(h) coberta em test_secrets.py, test_config.py e
       test_errors.py; decisão 6 (mkstemp) atendida

05:32  🧬 MUTAÇÕES · passo 2 (service/settings.py)  ·  10 de 10 mortas
       ☠️  padrão do WhisperX trocado                         1 teste
       ☠️  chave gravada também no SQLite                     1 teste
       ☠️  strip() removido                                   1 teste
       ☠️  validação Netscape removida                        5 casos
       ☠️  Netscape aceita linha comentada                    1 teste
       ☠️  set sem checar vazio / sem checar nenhum           1 teste cada
       ☠️  update grava só o primeiro modelo                  1 teste
       ☠️  llm_model com padrão; default_preset_id não nulo   1 teste cada

05:32  🔎 QA     passo 2/5 — Tabela e serviço  ·  ✅ PASS
       banco novo em user_version 5 com a tabela; test_db verde; dict exato

05:34  🧬 MUTAÇÕES · passo 3 (settings.py da CLI, contract.py)  ·  9 de 10 mortas
       ☠️  ler sempre sys.stdin.read()                        1 teste
       ☠️  render de texto imprime a chave                    1 teste
       ☠️  run devolve a chave no --json                      1 teste
       ☠️  set-cookies aceita terminal                        1 teste
       ☠️  set-key / set-cookies sem reads_secret             1 teste cada
       ☠️  aceitar e usar --key / posicional                  1 teste cada
       ☠️  contrato ignora sobra em todo comando              2 testes
       🚨  comando de segredo ignora a sobra   SOBREVIVEU — suíte inteira
       verde: o teste do argumento extra usa stdin vazio, e a saída 2 vem
       do stdin vazio, não da recusa; com stdin cheio a chave do stdin
       seria gravada com saída 0 (decisão 2 sem prova)

05:35  🔎 QA     passo 3/5 — CLI  ·  ❌ FAIL
       wordcut settings --key <chave> set-key ecoa a chave: "Valor inválido
       para action: '<chave>'" no stderr e no message do --json (o grupo
       settings trata a chave como ação); lacuna 2: ecoar = FAIL

05:35  🔎 QA     passo 4/5 — Uso  ·  ✅ PASS
       "large-v3" fixo na tarefa → 1 failed; LocalTranscriber() sem o modelo
       dentro de default_gateways sobrevive, mas fica atrás do dublê que a
       barra escolheu como instrumento

05:36  🔎 QA     passo 5/5 — Documentação  ·  ✅ PASS
       §4, CHANGELOG, SECURITY, cli.md §5.3 e docstring presentes; notas:
       linha em branco no meio da lista "Alterado" do CHANGELOG; a doc diz
       "argumento sobrando recusado sem eco", que o passo 3 desmente no grupo

05:36  📊 SUÍTE  veredito geral  ·  ❌ FAIL
       passo 3 FAIL; critérios "chave nunca em erro" e FR-004 descobertos

## Rodada 2 · implementador

05:39  📋 ESCOPO  só o Passo 3 — CLI, reaberto FAIL na Rodada 1 do qa.md
       achados: (1) erro de uso ecoa o valor digitado ("Valor inválido para
       action: '<chave>'"); (2) recusa do argumento extra provada só com
       stdin vazio. Regra global do orquestrador (ADR-0015): nenhum erro de
       uso repete valor digitado, em nenhum comando

05:39  🔴 RED    test_a_secret_given_as_argument_is_refused_without_being_echoed
       (stdin cheio) com um segredo válido esperando no stdin, o argumento
       extra em set-key/set-cookies → saída 2 e nada gravado
       Passo 3 (g); achado 2 da Rodada 1; decisão 2 do plano
       passou sem produção nova: a recusa já existe (reads_secret); o teste
       antigo só não a isolava do stdin vazio

05:39  🟢 GREEN  test_a_secret_given_as_argument_is_refused_without_being_echoed  ·  12 passed
       🧬 mutação "comando de segredo ignora a sobra" (if stray and not
       command.reads_secret) conferida: ☠️ 12 failed (antes sobrevivia)

05:40  🔴 RED    test_a_secret_given_where_the_action_goes_is_refused_without_being_echoed
       settings <chave>, settings --key <chave> set-key e settings <chave>
       set-key → saída 2, nada gravado, chave ausente de stdout e stderr
       (json e texto)
       Passo 3 (g); achado 1 da Rodada 1; ADR-0015 (escolha inválida)
       assert (2, True, False) == (2, False, False)  ·  6 failed ("Valor
       inválido para action: '<chave>'")

05:40  🟢 GREEN  test_a_secret_given_where_the_action_goes_is_refused_without_being_echoed  ·  56 passed
       contract._USAGE_ERRORS: escolha inválida e valor de tipo inválido
       viram "Valor inválido para <destino>.", sem o valor; ajustado
       test_malformed_value_names_the_argument_it_belongs_to (esperava
       "'muitos'" na mensagem), igualdade exata mantida

05:40  🔴 RED    test_invalid_choice_lists_the_choices_without_repeating_the_typed_value
       escolha inválida → "Valor inválido para <destino>; use um de: a, b."
       com details {"argument", "choices"}, sem o valor digitado
       Passo 3 (g); ADR-0015 (decisão do orquestrador, regra global)
       AssertionError: 'Valor inválido para command.' != 'Valor inválido
       para command; use um de: probe.' (sem "choices" nos details)

05:41  🟢 GREEN  test_invalid_choice_lists_the_choices_without_repeating_the_typed_value  ·  57 passed
       _INVALID_CHOICE lê a lista do "(choose from …)" do argparse, a última
       ocorrência, para que um valor digitado com "(choose from" não entre

05:41  🔴 RED    test_unrecognized_positional_value_is_refused_without_repeating_it
       argumento posicional sobrando → "Argumento não reconhecido.", sem o
       valor e sem details
       Passo 3 (g); ADR-0015 (argumento não reconhecido posicional)
       AssertionError: 'Argumento não reconhecido: valor-ficticio-9z.' !=
       'Argumento não reconhecido.'

05:42  🟢 GREEN  test_unrecognized_positional_value_is_refused_without_repeating_it  ·  178 passed
       _stray_arguments_error monta o erro direto da lista: opção (começa
       com "-") mantém o nome, posicional fica genérico; o padrão
       "unrecognized arguments" saiu de _USAGE_ERRORS (parse_known_args nunca
       o produz). test_unknown_option_* e test_usage_error_without_json_*
       seguem verdes com "--bogus"

05:42  🔴 RED    test_unrecognized_option_with_its_value_names_only_the_option
       --opcao=valor sobrando → só "--opcao" na mensagem e em
       details.argument
       Passo 3 (g); ADR-0015 (opção não reconhecida: parte antes do "=")
       AssertionError: 'Argumento não reconhecido: --bogus=valor-ficticio-9z.'
       != 'Argumento não reconhecido: --bogus.'

05:42  🟢 GREEN  test_unrecognized_option_with_its_value_names_only_the_option  ·  59 passed

05:42  🔴 RED    test_no_usage_error_repeats_a_value_the_user_typed
       sermon show <valor>, sermon list <valor>, sermon list --opcao=<valor>,
       wordcut <valor> e wordcut "x (choose from '<valor>')" → saída 2,
       valor ausente de stdout e stderr (json e texto)
       Passo 3 (g); ADR-0015 (regra global, "comando comum")
       passou sem produção nova: os ciclos anteriores já cobrem; vale como
       guarda por main(argv) com o parser real

05:43  🟢 GREEN  test_no_usage_error_repeats_a_value_the_user_typed  ·  10 passed

05:43  🧬 MUTAÇÕES · passo 3 (contract.py)  ·  5 de 5 mortas
       ☠️  comando de segredo ignora a sobra (stdin cheio)  12 testes
       ☠️  tipo inválido volta a ter "{value}" no template    3 testes
       ☠️  posicional sobrando ecoa o valor                   3 testes
       ☠️  opção sobrando sem cortar no "="                   3 testes
       ☠️  lista de escolhas sem âncora (".*?", "[^)]*", sem "$")  2 testes
       equivalente registrada: só ".*" → ".*?" sobrevive, porque "[^()]*"
       com "$" já força o último parêntese; comentário ajustado para dizer isso

05:44  🔧 REFACTOR  docstring de _stray_arguments_error descreve a regra nova;
       ruff format; suíte verde

05:45  📝 DOCS   ADR-0015 "Erro de uso não repete valor digitado" (complementa
       a ADR-0012, sem editar o texto aceito) e entrada no índice; plan.md
       com a decisão na tabela; docs/cli.md §5.3 (invalid_argument com
       details.choices, sem o valor); docs/architecture/README.md §4;
       CHANGELOG em "Alterado" (e a linha em branco no meio da lista,
       apontada pelo QA, removida); README cita a ADR-0015

05:46  ✅ PASSO 3/5 — CLI (reaberto)  ·  +11 testes  ·  suíte 599
       pytest 599 passed; ruff check, ruff format --check e mypy limpos

05:46  📝 CORREÇÃO  a linha acima conta funções; em casos coletados são
       +19 testes (580 → 599): 6 em test_settings_command.py e 13 em
       test_cli_contract.py; o teste do argumento extra (12 casos) mudou
       para stdin cheio

05:46  🔴 RED    test_a_value_glued_to_a_dash_is_not_taken_for_an_option_name
       wordcut sermon list -sk-ficticia → saída 2, "sk-ficticia" ausente de
       stdout e stderr (json e texto)
       Passo 3 (g); decisão do orquestrador: nome só para opção longa bem
       formada (^--[a-z][a-z0-9-]*$, antes do "=") ou curta isolada (^-[a-zA-Z]$)
       assert (2, True) == (2, False)  ·  2 failed

05:47  🟢 GREEN  test_a_value_glued_to_a_dash_is_not_taken_for_an_option_name  ·  191 passed
       _OPTION_NAME (--[a-z][a-z0-9-]* | -[a-zA-Z], fullmatch); o "=" só é
       cortado em opção longa; "-k=x", "--Opcao=v", "-sk-..." → genérico

05:48  🧬 MUTAÇÕES · regra do nome da opção  ·  2 de 2 mortas
       ☠️  _OPTION_NAME trocado por startswith("-")           2 testes
       ☠️  opção sem cortar no "="                            1 teste

05:48  📝 DOCS   ADR-0015 (ainda não commitada) e linha do plan.md com a
       regra do nome da opção

05:48  ✅ PASSO 3/5 — CLI (reaberto)  ·  +2 testes  ·  suíte 601
       pytest 601 passed; ruff check, ruff format --check e mypy limpos

## Rodada 2 · QA

05:50  📊 SUÍTE  601 passed  ·  0 failed
       uv run pytest -q; ruff check, ruff format --check e mypy (63
       arquivos) limpos; Python 3.11.15

05:53  🔎 QA     sondagem de eco · todo comando, grupo e raiz  ·  ✅ PASS
       16 272 execuções de main(argv) (8 valores fictícios × posicional,
       --x=, -valor, --json=, --quiet=, -k, -- , abreviação e opção real,
       com e sem --json, stdin cheio e vazio): 15 624 saídas 2, nenhuma com
       o valor em stdout ou stderr; sucessos de settings set e erros de
       execução do legado fora da conta (não são erro de uso)

05:55  🧬 MUTAÇÕES · contract.py (cópia no scratchpad, apps/cli/tests)  ·  13 de 16 mortas
       ☠️  comando de segredo ignora a sobra (stdin cheio)  12 testes
       ☠️  recusa de segredo põe a sobra no details           4 testes
       ☠️  escolha inválida sem lista                          1 teste
       ☠️  escolha inválida repete a mensagem do argparse    11 testes
       ☠️  tipo inválido repete o valor                       3 testes
       ☠️  posicional sobrando ecoa o valor                   5 testes
       ☠️  genérico com details do valor                      3 testes
       ☠️  nome da opção por startswith("-")                  2 testes
       ☠️  nome da opção com match em vez de fullmatch        2 testes
       ☠️  opção longa sem cortar no "="                      1 teste
       ☠️  curta aceita mais de uma letra                     2 testes
       ☠️  "Uso inválido de X" repete o resto                 1 teste
       ☠️  lista de escolhas sem âncora                       2 testes
       🚨  fallback "Uso inválido" repete a mensagem
           SOBREVIVEU — alcançável: transcribe --h=<valor> é "ambiguous
           option" com o valor; hoje sai genérico, sem teste que o guarde
       🚨  opção longa aceita maiúsculas
           SOBREVIVEU — a regra "^--[a-z][a-z0-9-]*$" não tem teste;
           --SK-<VALOR> passaria a ser repetido
       🚨  comando de segredo sem ramo próprio
           SOBREVIVEU — ADR-0015, último item, sem teste: sem o ramo,
           settings set-key --sk-or-v1-<chave> repete a chave inteira

05:58  🔎 QA     eco que a própria regra permite  ·  fato
       sermon list --sk-or-v1-<chave> e settings set --sk-or-v1-<chave> →
       "Argumento não reconhecido: --sk-or-v1-<chave>." com details; é
       opção longa bem formada pela barra; chave do OpenRouter é
       minúscula e casa a regra; docs/cli.md §5.3 diz "nunca repete"

05:59  🔎 QA     passo 3/5 — CLI  ·  ⚠️ PARCIAL
       os dois achados da Rodada 1 resolvidos (eco antes da ação; teste do
       argumento extra com stdin cheio, "ignora a sobra" vermelha); falta
       teste do item da ADR-0015 para comando de segredo e da regra de
       minúsculas

06:00  🔎 QA     passos 1, 2, 4  ·  ✅ PASS
       código sem mudança desde a Rodada 1 (mtime 05:13–05:26); suíte verde

06:00  🔎 QA     passo 5/5 — Documentação  ·  ✅ PASS
       ADR-0015 no índice, README, §4, cli.md §5.3, CHANGELOG em
       "Alterado"; linha em branco da lista removida

## Rodada 3 · implementador

06:03  🔁 REABERTO  Passo 3 — CLI  ·  PARCIAL na Rodada 2
       decisão final do orquestrador: argumento não reconhecido nunca é
       repetido, nem como nome de opção; nome de opção só quando a opção
       existe no parser e vem da definição dele

06:03  🔴 RED    test_a_secret_shaped_like_an_option_is_refused_without_being_repeated
       sermon list, settings set, settings set-key (stdin cheio) e a raiz
       com --sk-or-v1-ficticia → saída 2, valor ausente de stdout e stderr
       (json e texto), nada em WORDCUT_CONFIG, llm_model segue null
       Passo 3 (g); achado da Rodada 2 (eco que a regra permitia)
       assert (2, True, False, None) == (2, False, False, None)  ·  4 failed

06:04  🟢 GREEN  test_a_secret_shaped_like_an_option_is_refused_without_being_repeated  ·  200 passed
       _stray_arguments_error sempre genérico: "Argumento não reconhecido;
       veja wordcut <comando> --help.", sem details; <comando> vem de
       args.command/args.action (escolhas validadas pelo parser); regra
       _OPTION_NAME removida; ramo próprio dos comandos de segredo vira o
       caso geral (reads_secret removido de Command, add_command e
       settings.py)
       3 testes de contrato da regra antiga ("Argumento não reconhecido:
       --bogus." com details) trocados por
       test_an_unrecognized_argument_is_refused_in_portuguese_without_naming_it
       (--bogus, --bogus=valor, posicional, -b); o teste do stderr passa a
       esperar a mensagem nova

06:05  🛡️ GUARDA test_an_invalid_value_for_an_existing_option_names_it_as_the_parser_defines_it
       sermon list --status <fictício> e --stat <fictício> (abreviado) →
       "Valor inválido para --status; …" com details.argument "--status",
       valor ausente; o nome vem do parser, não do texto digitado
       decisão do orquestrador, teste 2; passa sem produção (comportamento
       mantido), provado pela mutação abaixo  ·  2 passed

06:06  🧬 MUTAÇÕES · contract.py (no lugar, restaurado), apps/cli/tests  ·  5 de 5 mortas
       ☠️  repetir o argumento não reconhecido                25 testes
       ☠️  tirar a proteção dos comandos de segredo           14 testes
           (set-key/set-cookies deixam passar a sobra)
       ☠️  voltar a regra do nome da opção (--[a-z]…)         10 testes
       ☠️  nome da opção com maiúsculas é repetido             1 teste
           (sobreviveu na 1ª volta; morto com o caso --BOGUS em
           test_an_unrecognized_argument_is_refused_in_portuguese_without_naming_it)
       ☠️  escolha inválida sem o nome do parser               4 testes

06:08  📝 DOCS   ADR-0015 (ainda não commitada), linha do plan.md, CHANGELOG
       ("Alterado") e docs/cli.md §5.3 com a regra final: argumento não
       reconhecido nunca repetido, nome de opção só do parser

06:09  ✅ PASSO 3/5 — CLI (reaberto)  ·  +12 testes  ·  suíte 613
       pytest 613 passed; ruff check, ruff format --check e mypy (63
       arquivos) limpos; +15 casos novos (8 de segredo em forma de opção,
       2 de guarda do nome do parser, 5 de argumento não reconhecido) e 3
       testes da regra antiga removidos; o do stderr mudou de mensagem

## Rodada 3 · QA

06:10  📊 SUÍTE  613 passed  ·  0 failed
       uv run pytest -q; ruff check, ruff format --check e mypy (63
       arquivos) limpos

06:13  🔎 QA     sondagem de eco · todo comando, grupo e raiz  ·  ✅ PASS
       14 700 execuções de main(argv), _run e handlers do legado trocados
       por dublê: 3 valores fictícios (minúsculo com hífens, MAIÚSCULO,
       curto) × 49 formas (--valor, -valor, ---valor, --VALOR, --valor=x,
       --x=valor, -k valor, -- valor, --json=, --h=, --help=, --version=,
       imitação de "(choose from …)" e de "argument x:", quebra de linha,
       --stat/--status/--kind/--start com o valor) × antes e depois do
       comando × com e sem --json, stdin cheio: 14 598 saídas 2, nenhuma
       com o valor (nem em maiúsculas/minúsculas) em stdout ou stderr

06:14  🔎 QA     wordcut --sk-or-v1-<fictícia> sem comando  ·  fato
       sai "Argumento obrigatório ausente: command." com details.argument
       "command": o argparse reclama do comando que falta antes da sobra;
       nome vem do parser, valor ausente; nada gravado em WORDCUT_CONFIG

06:17  🧬 MUTAÇÕES · contract.py (cópia no scratchpad, apps/cli/tests)  ·  10 de 13 mortas
       ☠️  repete o argumento não reconhecido                26 testes
       ☠️  comando de segredo deixa passar a sobra           14 testes
       ☠️  volta a regra do nome (--[a-z]…)                  10 testes
       ☠️  nome da opção com maiúsculas                       1 teste
       ☠️  sobra no details                                  15 testes
       ☠️  escolha inválida repete a mensagem do argparse    13 testes
       ☠️  tipo inválido repete o valor                       3 testes
       ☠️  "Uso inválido de X" repete o resto                 1 teste
       ☠️  lista de escolhas sem âncora                       2 testes
       ☠️  obrigatório ausente repete a mensagem              2 testes
       🚨  <comando> do --help sem a ação
           SOBREVIVEU — "veja wordcut settings --help" em vez de
           "settings set-key"; ainda vem do parser, sem eco
       🚨  legado ignora a sobra
           SOBREVIVEU — info u extra rodaria ignorando "extra"; sem eco,
           fora da barra do item
       🚨  fallback "Uso inválido" repete a mensagem
           SOBREVIVEU — o mesmo da Rodada 2 (transcribe --h=<valor>); hoje
           sai genérico, conferido na sondagem

06:18  🔎 QA     passo 3/5 — CLI  ·  ✅ PASS
       --sk-or-v1-<fictícia> não é repetido em sermon list, settings set,
       settings set-key nem na raiz; as duas sobreviventes cobradas na
       Rodada 2 agora morrem (14 e 1 testes); reads_secret e a regra do
       nome removidos, coerente com a ADR-0015

06:19  🔎 QA     passos 1, 2, 4, 5  ·  ✅ PASS
       core sem mudança desde a Rodada 1 (mtime 05:13–05:26); docs
       (ADR-0015, cli.md §5.3, CHANGELOG) com a regra final
