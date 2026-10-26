## Plano de QA

baseline_commit: d5ac68d80b1844baaebb8b0652df93ea3271834f

03:40  📐 BARRA   pipeline baixa só a faixa e a janela de áudio
       dublê de ProcessingGateways grava as chamadas; prova FR-002

03:40  📐 BARRA   sincronia soma o início da janela ao offset
       dublê de locate com offset conhecido e janela com início != 0

03:40  📐 BARRA   palavras e frases em tempo da pregação (1ª em 0,3 s)
       relidas do SQLite real; o contrato é o banco, não a chamada

03:40  📐 BARRA   corte real produz 16:9 com a duração calculada
       ffmpeg real em clipe lavfi de 3 s; único ffmpeg permitido

03:40  📐 BARRA   pré-condição falha sem criar tarefa
       contagem da tabela tasks antes e depois; pregação relida igual

03:40  📐 BARRA   processo morto -> pregação failed na leitura
       tarefa running com PID de subprocesso já colhido

03:40  📐 BARRA   sem --wait: tarefa running na hora, sem filho real
       Popen trocado por processo inofensivo; YouTube nunca alcançado

03:40  🧬 EXIGE   LEAD_IN_S ou TAIL_S trocados ou com sinal invertido  ·  vermelha
       prova o ajuste às palavras [primeira - 0,3, última + 1,5]

03:40  🧬 EXIGE   1ª palavra com `>` no lugar de `>=` live_start  ·  vermelha
       palavra exatamente na borda tem de entrar

03:40  🧬 EXIGE   ignorar o início da janela na sincronia  ·  vermelha
       sem isso o corte cai 50 s fora da pregação

03:40  🧬 EXIGE   gravar palavras em tempo da live  ·  vermelha
       docs/cli.md §3.4: tempo da pregação, t = 0 em sermon_start

03:40  🧬 EXIGE   pausa `>` trocada por `>=` 1,5 s nas frases  ·  vermelha
       fronteira da regra de overview.py

03:40  🧬 EXIGE   remover a checagem de would_discard_edits  ·  vermelha
       FR-006: processed sem --force não pode refazer

03:40  🧬 EXIGE   --force sem apagar palavras e frases  ·  vermelha
       contagem dobraria; prova a substituição

03:40  🧬 EXIGE   remover o failed da pregação no erro  ·  vermelha
       FR-005: falha deixa a pregação reprocessável

03:40  🧬 EXIGE   remover a reconciliação da pregação na leitura  ·  vermelha
       processing eterno depois de processo morto

03:40  🧬 EXIGE   YouTubeError mapeado para internal_error  ·  vermelha
       contrato: youtube_error, saída 6

03:40  🧬 EXIGE   não apagar work/ no sucesso  ·  vermelha
       FR-008 e decisão de mídias do plano

03:40  ⚠️ LACUNA  filho destacado chamaria default_gateways real
       monkeypatch não atravessa processo; sem L1 o passo 5 fica PARCIAL

03:40  ⚠️ LACUNA  processing só quando o filho começa
       corrida logo após o retorno; sem L2 a Verificação 3 fica PARCIAL

03:40  ⚠️ LACUNA  cut_with_fades não sobrescreve; yt-dlp reaproveita
       --force e refazer falham ou usam faixa velha; passo 4 PARCIAL

03:40  ⚠️ LACUNA  base de tempo da janela e limites em 0/duração
       quem converte e o clamp não decididos; passo 2 PARCIAL sem teste

03:40  ⚠️ LACUNA  palavras na margem de 0,3 s fora das bordas
       between() as incluiria; barra: só primeira..última nas bordas

03:40  ⚠️ LACUNA  sem palavras nas bordas / corte fora da faixa
       código de erro não decidido; exige teste e code do contrato

03:40  ⚠️ LACUNA  resultado de --wait e formato de --transcript
       campos não decididos; barra em qa.md L7, L8; documentar §7.2

03:40  ⚠️ LACUNA  show_sermon sem Home; list sem reconciliação
       last_task e failed na leitura exigem Home; ver L9

03:40  ⚠️ LACUNA  pré-condição checada fora da trava
       tarefa revalida would_discard_edits sob a trava; ver L10

03:40  ⚠️ LACUNA  live_finished gravado no create nunca é atualizado
       live criada no ar fica improcessável; decisão pendente (L11)

03:40  ⚠️ LACUNA  create --process: falhas parciais e processed
       barra em qa.md L12

03:40  ⚠️ LACUNA  spec, cli.md §5.1, §6.5 e §7.4 divergem do plano
       barra segue docs/cli.md; atualizar §5.1 e marcar item 9 (L13)

03:40  ⚠️ LACUNA  IDs reaproveitados e gravação não atômica
       AUTOINCREMENT e uma transação; ver L14

## Rodada 1 · implementador

--- Passo 1: Frases ---

03:47  🔴 RED    test_a_word_ending_in_a_full_stop_closes_the_sentence_with_its_times_text_and_words
       fim de frase fecha a frase com início, fim, texto e 1ª/última palavra
       FR-004; plano: Frases; qa.md 1(a)(b)
       ModuleNotFoundError: No module named 'wordcut.processing'

03:48  🟢 GREEN  test_a_word_ending_in_a_full_stop_closes_the_sentence_with_its_times_text_and_words  ·  1 passed

03:48  🔴 RED    test_a_pause_longer_than_one_and_a_half_seconds_starts_a_new_sentence
       pausa de 1,501 s quebra a frase; 1,5 s exatos não quebra
       plano: Frases (pausa > 1,5 s); qa.md 1(a); EXIGE mutação > → >=
       assert [0.0] == [0.0, 2.501]

03:48  🟢 GREEN  test_a_pause_longer_than_one_and_a_half_seconds_starts_a_new_sentence  ·  2 passed

03:48  🔴 RED    test_the_twenty_fifth_word_closes_the_sentence
       a 25ª palavra fecha a frase; 24 não fecham; lista vazia → nenhuma frase
       plano: Frases (25 palavras); qa.md 1(a)(d); EXIGE mutação >= → >
       assert [(0, 25)] == [(0, 24), (25, 25)]

03:48  🟢 GREEN  test_the_twenty_fifth_word_closes_the_sentence  ·  5 passed

03:48  📝 NOTA   REFACTOR overview_lines usa split_sentences; test_overview.py sem diff
       test_overview + test_sentences + test_legacy_commands  ·  10 passed

03:48  ✅ PASSO 1/6 — Frases  ·  +5 testes  ·  suíte 391

--- Passo 2: Pipeline ---

03:49  🔴 RED    test_the_cut_spans_from_before_the_first_word_to_after_the_last_in_the_section_time
       tracer: baixa, sincroniza, transcreve, ajusta às palavras e corta [1ª − 0,3, última + 1,5] em tempo do arquivo
       plano: Sincronia, Ajuste às palavras; qa.md 2(b)(d)(e); EXIGE LEAD_IN/TAIL, >=, início da janela
       ImportError: cannot import name 'pipeline' from 'wordcut.processing'

03:50  🟢 GREEN  test_the_cut_spans_from_before_the_first_word_to_after_the_last_in_the_section_time  ·  1 passed

03:50  🔴 RED    test_only_the_section_around_the_borders_and_the_sync_window_are_downloaded_within_the_live
       baixa só [início − 30, fim + 30] e a janela [início − 50, início + 40], limitados a 0 e à duração da live
       FR-002; L4; qa.md 2(a) com live_start = 10
       ('download_section', …, -20.0, 130.0) != ('download_section', …, 0.0, 120.0)

03:50  🟢 GREEN  test_only_the_section_around_the_borders_and_the_sync_window_are_downloaded_within_the_live  ·  4 passed

03:51  📝 NOTA   guardas que já passam pela fatia do tracer: locate na janela (expected 20 e 0), bordas em tempo da live
       qa.md 2(b)(d)

03:51  🔴 RED    test_words_are_kept_from_the_first_to_the_last_inside_the_borders_in_sermon_time_to_the_ms
       palavras da 1ª à última dentro das bordas, em tempo da pregação (1ª em 0,3 s), ao milissegundo, com score e estimated; frases idem
       FR-004; L5; qa.md 2(f); EXIGE gravar em tempo da live
       (0, 1, 'Irmãos graça.', 0.2999999999999545, …) != (0, 1, 'Irmãos graça.', 0.3, 1.3)

03:51  🟢 GREEN  test_words_are_kept_from_the_first_to_the_last_inside_the_borders_in_sermon_time_to_the_ms  ·  9 passed

03:51  🔴 RED    test_no_word_inside_the_borders_is_a_processing_error_without_a_cut
       sem palavra nas bordas (vazio, só fora, palavra que atravessa) → processing_error, saída 1, sem corte
       L6; qa.md 2(g)
       StopIteration / IndexError em _within

03:51  🟢 GREEN  test_no_word_inside_the_borders_is_a_processing_error_without_a_cut  ·  30 passed

03:51  🔴 RED    test_a_cut_outside_the_downloaded_section_is_a_processing_error_without_a_cut
       corte além do fim da faixa ou antes do seu início → processing_error, sem corte
       L6; risco do plano (sincronia ruim); qa.md 2(g)
       Failed: DID NOT RAISE WordcutError

03:52  🟢 GREEN  test_a_cut_outside_the_downloaded_section_is_a_processing_error_without_a_cut  ·  14 passed

03:52  🔴 RED    test_a_youtube_failure_is_a_youtube_error_with_exit_6 + test_a_transcriber_failure_is_a_transcription_error_with_exit_6
       YouTubeError → youtube_error (6); FileNotFoundError/CalledProcessError do transcritor → transcription_error (6)
       plano: Erros do pipeline; qa.md 2(h); EXIGE YouTubeError → internal_error vermelha
       YouTubeError / CalledProcessError sem tradução

03:52  🟢 GREEN  test_a_youtube_failure_… + test_a_transcriber_failure_…  ·  36 passed

03:52  🔴 RED    test_progress_names_each_stage_in_portuguese_within_the_planned_fractions
       baixando 0, sincronizando 0,3, transcrevendo 0,35, cortando 0,85 (gravando 0,95 fica na tarefa)
       plano: Progresso; docs/cli.md §4.5; qa.md 2(i)
       assert [] == [(0.0, 'baixando'), …]

03:53  🟢 GREEN  test_progress_names_each_stage_in_portuguese_within_the_planned_fractions  ·  18 passed
       REFACTOR: etapas _download/_cut; ruff e mypy limpos

03:53  🔴 RED    test_audio_window_args_ask_only_the_audio_of_the_section_in_seconds
       download_audio_window pede só áudio com --download-sections, sem executar yt-dlp
       plano: download_audio_window; qa.md 2 (test_youtube.py)
       AttributeError: type object 'YouTube' has no attribute 'audio_window_args'

03:53  🟢 GREEN  test_audio_window_args_ask_only_the_audio_of_the_section_in_seconds  ·  13 passed

03:54  🔴 RED    test_the_cut_sermon_lasts_from_its_start_to_its_end_in_the_source_geometry_with_audio
       ffmpeg real em clipe lavfi de 3 s 320x180: duração = sermon_end − sermon_start (± 1 quadro), 16:9 da fonte, com áudio
       plano: Comandos de verificação; qa.md 2(j)
       ImportError: cannot import name 'LocalGateways' from 'wordcut.processing'

03:54  🟢 GREEN  test_the_cut_sermon_lasts_from_its_start_to_its_end_in_the_source_geometry_with_audio  ·  1 passed

03:54  📝 NOTA   fixture autouse no_real_processing (conftest da raiz): default_gateways falha se alcançada (L1)

03:54  ✅ PASSO 2/6 — Pipeline  ·  +22 testes  ·  suíte 413

--- Passo 3: Persistência ---

03:55  🔴 RED    test_a_database_at_schema_3_keeps_its_sermons_and_gains_empty_transcripts
       banco no esquema 3 com pregação migra para 4 sem perdê-la; colunas novas nulas; sem palavras nem frases
       plano: migração 0004; qa.md 3(a)(b)
       ImportError: cannot import name 'transcripts' from 'wordcut.db'

03:55  🟢 GREEN  test_a_database_at_schema_3_keeps_its_sermons_and_gains_empty_transcripts  ·  26 passed

03:56  🔴 RED    test_recorded_words_and_sentences_are_read_back_in_order_pointing_to_their_words
       gravar e reler devolve palavras e frases em ordem; first/last_word_id apontam para as palavras
       FR-004; qa.md 3(b)(c)
       AttributeError: module 'wordcut.db.transcripts' has no attribute 'replace'

03:56  🟢 GREEN  test_recorded_words_and_sentences_are_read_back_in_order_pointing_to_their_words  ·  2 passed

03:56  📝 NOTA   guardas: outra pregação intocada (mutação sem WHERE sermon_id → vermelha, conferido) e IDs AUTOINCREMENT nunca reaproveitados
       qa.md 3(d)(e); L14  ·  4 passed

03:57  📝 NOTA   test_tasks_repository fixava user_version == 3; passa a >= 3, como os testes de sermons (>= 2)

03:58  ✅ PASSO 3/6 — Persistência  ·  +4 testes  ·  suíte 417

--- Passo 4: Tipo de tarefa e serviço ---

03:59  🔴 RED    test_processing_in_the_foreground_leaves_the_sermon_processed_with_borders_fitted_to_words
       tracer: start_processing em primeiro plano → pregação processed, sermon_start/sermon_end em tempo da live, processed_at
       FR-001, FR-005; L7; qa.md 4(a)
       ModuleNotFoundError: No module named 'wordcut.service.processing'

04:00  🟢 GREEN  test_processing_in_the_foreground_leaves_the_sermon_processed_with_borders_fitted_to_words  ·  1 passed
       show_sermon passa a receber home (L9); chamadas existentes atualizadas; JSON do show cresce com sermon_start, sermon_end, processed_at
       suíte 418 passed

04:00  🔴 RED    test_show_with_transcript_lists_the_sentences_in_sermon_time_with_their_words
       show --transcript: sentences em ordem com id, start, end, text, first_word_id, last_word_id em tempo da pregação; sem a opção, nada
       FR-004, FR-007; L8; qa.md 4(a), 5(f)
       KeyError: 'sentences'

04:01  🟢 GREEN  test_show_with_transcript_lists_the_sentences_in_sermon_time_with_their_words  ·  3 passed

04:01  📝 NOTA   guardas pela fatia do tracer: sermon.mp4 na pasta da pregação e work/ apagado (EXIGE não apagar work/); processing durante a transcrição
       FR-008; qa.md 4(a)(b)

04:01  🔴 RED    test_a_detached_processing_answers_at_once_with_the_sermon_already_processing
       sem --wait, com o filho trocado por processo inofensivo: tarefa running e pregação já processing
       L1, L2; qa.md 4(b), 5(b)
       ('running', 'process', 'trimmed') != ('running', 'process', 'processing')

04:01  🟢 GREEN  test_a_detached_processing_answers_at_once_with_the_sermon_already_processing  ·  6 passed
       gancho admit em tasks.execution.start: roda sob a trava antes de gravar a tarefa

04:01  📝 NOTA   guarda: falha (youtube_error 6, transcription_error 6, internal_error 1) → tarefa e pregação failed
       mutação sem failed na pregação → 3 vermelhas (conferido); qa.md 4(c)

04:02  🔴 RED    test_a_sermon_that_cannot_be_processed_is_refused_without_a_task_and_unchanged
       sem bordas → sermon_not_trimmed; live no ar → live_not_finished; processed sem force → would_discard_edits; sem tarefa, pregação igual
       spec: pré-condições; FR-006; qa.md 4(d); EXIGE remover would_discard_edits
       Failed: DID NOT RAISE WordcutError

04:02  🟢 GREEN  test_a_sermon_that_cannot_be_processed_is_refused_without_a_task_and_unchanged  ·  13 passed

04:02  📝 NOTA   guardas L11: live terminada depois da criação é consultada uma vez e processada; live já terminada não consulta o YouTube
       qa.md L11

04:02  📝 NOTA   guardas: trava de outro (busy 4, details.kind, sem tarefa, pregação igual); pregação em processamento → busy com task_id; failed refeita → processed; work/ antigo não é reaproveitado (mutação sem limpar → vermelha)
       qa.md 4(d)(e), L3

04:03  🔴 RED    test_force_discards_the_old_transcript_at_the_start_and_records_a_new_one
       --force numa processed: palavras e frases apagadas no início; ao fim, novas, sem IDs antigos, com sermon.mp4 pré-existente
       FR-006; plano: --force; qa.md 4(f); EXIGE --force sem apagar
       during == [[1, 2]] em vez de [[]]

04:03  🟢 GREEN  test_force_discards_the_old_transcript_at_the_start_and_records_a_new_one  ·  20 passed
       REFACTOR: set_status na transação de quem chama

04:04  🔴 RED    test_a_sermon_whose_task_process_died_… + test_listing_processing_sermons_leaves_out_… + test_last_task_is_the_sermons_latest_task_…
       processo da tarefa morto → pregação failed e last_task failed/interrupted na leitura; list --status processing não a mostra; last_task no formato de task show
       FR-005; docs/cli.md §6.5; L9, L13; qa.md 4(g)(h); EXIGE remover a reconciliação
       TypeError: 'NoneType' object is not subscriptable (last_task None)

04:07  🟢 GREEN  test_a_sermon_whose_task_process_died_… + list + last_task  ·  23 passed
       list_sermons recebe home; testes de trim de pregação processing passam a segurar a trava da pregação (sem trava nem tarefa viva ela é reconciliada failed)
       mutação sem reconciliação → 2 vermelhas (conferido); suíte 440 passed

04:07  📝 NOTA   test_process_task.py — guardas: process em BUILTIN_KIND_MODULES com trava; a tarefa revalida would_discard_edits sob a trava e deixa a pregação processed (L10); progresso até gravando 0,95; resultado = pregação do show sem last_task (L7)
       mutação sem would_discard_edits → 2 vermelhas (conferido); qa.md 4(j), L10  ·  4 passed

04:08  ✅ PASSO 4/6 — Tipo de tarefa e serviço  ·  +27 testes  ·  suíte 444

--- Passo 5: CLI ---

04:09  🔴 RED    test_process_with_wait_prints_the_processed_sermon_and_the_stages_on_stderr
       sermon process --wait --json: saída 0, stdout = pregação processed do show, stderr com [process] <etapa> NN% em ordem
       cenário processar; docs/cli.md §4.5, §6.3; L7; qa.md 5(a)
       KeyError: 'id' (invalid_argument: process não existe)

04:09  🟢 GREEN  test_process_with_wait_prints_the_processed_sermon_and_the_stages_on_stderr  ·  1 passed

04:09  📝 NOTA   guardas pela fatia do tracer + serviço: --quiet sem progresso; sem --wait → objeto de §6.2 e show processing (filho inofensivo, L1/L2); --force repassado; youtube_error/transcription_error 6 e pregação failed; not_found 3, sermon_not_trimmed/live_not_finished/would_discard_edits 5 sem tarefa; busy 4
       qa.md 5(a)-(d)  ·  11 passed

04:10  🔴 RED    test_create_with_borders_and_process_with_wait_does_everything_in_one_command
       create <link> --start --end --process --wait: cria, delimita e processa; saída 0
       spec: borda create --process; docs/cli.md §7.1; L12; qa.md 5(e)
       KeyError: 'status' (--process não reconhecido)

04:10  🟢 GREEN  test_create_with_borders_and_process_with_wait_does_everything_in_one_command  ·  12 passed

04:10  🔴 RED    test_create_refuses_process_without_borders_and_wait_without_process_creating_nothing
       --process sem bordas → invalid_argument (--start); --wait sem --process → invalid_argument (--process); nenhuma pregação criada
       docs/cli.md §7.1; L12; qa.md 5(e)
       KeyError: 'error' (a pregação foi criada)

04:10  🟢 GREEN  test_create_refuses_process_without_borders_and_wait_without_process_creating_nothing  ·  15 passed

04:10  📝 NOTA   guardas L12: live no ar mantém a pregação trimmed e sai 5; processed → would_discard_edits; sem --wait → tarefa running
       qa.md 5(e)  ·  18 passed

04:10  🔴 RED    test_show_with_transcript_in_json_adds_the_sentences_in_sermon_time + …_in_text_prints_one_sentence_per_line
       show --transcript: JSON com sentences; texto com uma frase por linha (ID, tempo, texto, IDs das palavras)
       FR-007; docs/cli.md §7.2; L8; qa.md 5(f)
       KeyError: 'sentences' (--transcript não reconhecido)

04:11  🟢 GREEN  test_show_with_transcript_in_json_… + …_in_text_…  ·  20 passed

04:11  📝 NOTA   guarda: --help de process, create --process e show --transcript em português
       qa.md 5(g); o texto quebrado pelo argparse é normalizado no teste

04:12  📝 NOTA   test_sermon_command: a ajuda do grupo sermon lista process e o exemplo de process entra na verificação

04:13  ✅ PASSO 5/6 — CLI  ·  +23 testes  ·  suíte 468

--- Passo 6: Documentação ---

04:15  📝 NOTA   sem TDD (documentação): ADR-0014 e índice; arquitetura §3, §4 e §5.1 (item 9 marcado); docs/cli.md §5.1, §5.3 (processing_error 1, transcription_error 6), §7.1, §7.2 (campos do show, sentences), §7.4 (item 9, etapas, resultado de --wait), §14; CHANGELOG; README

04:15  ✅ PASSO 6/6 — Documentação  ·  +0 testes  ·  suíte 468

04:15  📝 NOTA   verificação final: ruff check, ruff format --check, mypy limpos; uv run pytest 468 passed; nenhum processo órfão

## Rodada 1 · QA

04:16  📊 SUÍTE  468 passed  ·  0 failed
       uv run pytest -q; ruff check, ruff format --check e mypy limpos

04:17  🔎 QA     passo 1/6 — Frases  ·  ✅ PASS
       regra de overview.py preservada; test_overview.py sem diff

04:18  🧬 MUTAÇÕES · pipeline e frases  ·  18 de 18 mortas
       ☠️  pausa > → >= ; 25 palavras >= → >                     1 teste cada
       ☠️  LEAD_IN/TAIL com sinal invertido ou trocados          1 teste cada
       ☠️  1ª palavra >= → > ; última <= → <                     1 teste cada
       ☠️  ignorar o início da janela ; expected_offset fixo     1 teste cada
       ☠️  gravar em tempo da live ; sem arredondar ao ms        1 teste cada
       ☠️  sem limite em 0 ; sem limite na duração da live       1 teste cada
       ☠️  sem checagem de duração ; só o fim checado            1 teste cada
       ☠️  margem de palavras fora das bordas (L5)               1 teste
       ☠️  YouTubeError → internal_error ; transcritor sem mapa  1 teste cada

04:18  🔎 QA     passo 2/6 — Pipeline  ·  ✅ PASS
       2(e) julgado por L3: corte em work/sermon.mp4, os.replace na tarefa

04:19  🔎 QA     passo 3/6 — Persistência  ·  ✅ PASS
       migração 3→4, ordem, isolamento e AUTOINCREMENT com mutação morta

04:20  🧬 MUTAÇÕES · tarefa, serviço, repositório e CLI  ·  27 de 31 mortas
       ☠️  DELETE sem WHERE (words, sentences) ; sem AUTOINCREMENT  1 cada
       ☠️  sem would_discard ; --force sem apagar ; sem rmtree(work)
       ☠️  work/ não limpo ; sem os.replace ; admit sem processing
       ☠️  sem admit ; sem reconciliação (show, list, tarefas)
       ☠️  last_task None ou a mais antiga ; live sem consulta/update
       ☠️  frases fora de ordem ; resultado com last_task
       ☠️  CLI: sem --force, sem checagens de --process/--wait,
           sem --transcript, create sempre espera, texto sem frases
       ⚪  apagar transcrição sem --force           equivalente
       ⚪  tarefa sem set_status processing         equivalente (admit, L2)
       🚨  tarefa sem set_status failed no erro      SOBREVIVEU — trim
           logo após a falha responde busy (sonda); a reconciliação
           de show/list mascara nos testes
       🚨  admit sem check_processable              SOBREVIVEU — L10:
           a checagem da tarefa vê processing e nunca recusa no fluxo
           real; a guarda efetiva não tem teste

04:21  🔎 QA     passo 4/6 — Tipo de tarefa e serviço  ·  ⚠️ PARCIAL
       duas mutações exigidas sobrevivem (failed no erro; L10 no admit)

04:21  🔎 QA     passo 5/6 — CLI  ·  ✅ PASS
       7 de 7 mutações mortas; filho inofensivo (L1), §6.2, L7, L8, L12

04:22  🔎 QA     passo 6/6 — Documentação  ·  ✅ PASS
       cli.md §5.1/§5.3/§7.1/§7.2/§7.4/§14, arquitetura §4/§5.1, ADR-0014

04:22  📝 NOTA   nenhum processo wordcut.tasks.runner vivo; mutações e
       sonda só na cópia do scratchpad

## Rodada 2 · implementador

04:24  🔁 REABRE  passo 4/6 — Tipo de tarefa e serviço (QA Rodada 1:
       PARCIAL): failed gravado no erro; guarda de L10 no admit

04:26  🔴 RED    test_a_sermon_whose_processing_failed_can_be_trimmed_
       again_at_once
       falha do pipeline em primeiro plano deixa a pregação failed no
       banco: sermon trim logo depois aceita, sem busy
       plano: Estado da pregação (failed em erro); QA Rodada 1, achado 2
       produção já gravava failed: o teste nasceu verde; RED provado
       pela mutação exigida (sem set_status failed no erro):
       WordcutError: A pregação 1 está sendo processada. (busy)

04:26  🟢 GREEN  test_a_sermon_whose_processing_failed_can_be_trimmed_
       again_at_once  ·  1 passed

04:26  🔴 RED    test_a_sermon_whose_detached_processing_failed_can_be_
       trimmed_again_at_once
       a mesma falha no processo destacado (runner.main da tarefa
       lançada; filho inofensivo no lugar do Popen, L1) grava failed
       plano: Estado da pregação; QA Rodada 1, achado 2 (destacada)
       nasceu verde; RED pela mutação sem set_status failed no erro:
       WordcutError: A pregação 1 está sendo processada. (busy)

04:26  🟢 GREEN  test_a_sermon_whose_detached_processing_failed_can_be_
       trimmed_again_at_once  ·  2 passed

04:26  🔴 RED    test_a_sermon_processed_between_the_check_and_the_lock_
       is_refused_without_a_task
       outra tarefa termina processed entre a checagem e a trava; o
       start_processing recusa com would_discard_edits, sem 2ª tarefa
       plano: L10; QA Rodada 1, achado 1 (teste pelo fluxo real)
       nasceu verde (admit já revalidava); RED pela mutação exigida
       (admit sem check_processable): Failed: DID NOT RAISE WordcutError

04:27  🟢 GREEN  test_a_sermon_processed_between_the_check_and_the_lock_
       is_refused_without_a_task  ·  1 passed

04:27  🔧 REFACTOR checagem morta da tarefa removida (QA achado 1): a
       trava fica com a tarefa desde o admit até o fim, então a tarefa
       só lê a pregação e confirma processing; check_processable vira
       _processable em service/processing.py. Sai o teste que chamava
       a tarefa sem admit (test_the_task_refuses_a_sermon_processed_
       meanwhile…). ADR-0014 e diagrama §5.1 da arquitetura ajustados

04:28  🧬 MUTAÇÃO sem set_status failed no erro (tarefa)  ·  vermelha
       2 falhas: …processing_failed_can_be_trimmed_again_at_once e
       …detached_processing_failed_…; 467 passed

04:28  🧬 MUTAÇÃO admit sem _processable (L10)  ·  vermelha
       1 falha: …processed_between_the_check_and_the_lock_…;
       468 passed

04:28  ✅ PASSO 4/6 — Tipo de tarefa e serviço  ·  +3 −1 testes  ·
       suíte 470  ·  ruff, format e mypy limpos  ·  nenhum processo
       wordcut.tasks.runner nem filho inofensivo vivo

## Rodada 2 · QA

04:30  📊 SUÍTE  470 passed  ·  0 failed
       uv run pytest -q; ruff check, ruff format --check e mypy limpos;
       nenhum processo wordcut.tasks.runner nem filho inofensivo vivo

04:31  🔎 QA     passos 1, 2, 3, 5, 6  ·  ✅ PASS (sem regressão)
       arquivos desses passos sem mudança desde a Rodada 1; suíte verde;
       docs de arquitetura e ADR-0014 coerentes com a nova L10

04:34  🧬 MUTAÇÕES · passo 4 (tarefa e serviço)  ·  6 de 7 mortas
       ☠️  tarefa sem set_status failed no erro                3 testes
       ☠️  admit sem _processable (L10)                        1 teste
       ☠️  admit revalida com force=True (sem would_discard)   1 teste
       ☠️  _processable sem would_discard_edits                4 testes
       ☠️  show/list sem reconciliação                         2 testes
       ☠️  admit não grava processing (L2)                     3 testes
       ⚪  apagar transcrição sem force                        equivalente
       ⚪  tarefa sem set_status processing                    equivalente
       🚨  failed gravado só para WordcutError    SOBREVIVEU — com
           internal_error (exceção inesperada, 4(c)) a pregação fica
           processing no banco; sonda na cópia: trim logo depois
           responde busy (original: trimmed). O teste de trim após
           falha só usa youtube_error

04:36  🔎 QA     passo 4/6 — Tipo de tarefa e serviço  ·  ⚠️ PARCIAL
       os dois achados da Rodada 1 resolvidos pelo fluxo real; resta
       o failed gravado para internal_error, sem teste (4(c))

04:36  📝 NOTA   mutações e sonda só na cópia do scratchpad; working
       tree intocada; nenhum processo wordcut.tasks.runner vivo

## Rodada 3 · implementador

04:37  🔴 RED    test_a_sermon_whose_processing_failed_can_be_trimmed_
       again_at_once[RefusingYouTube|MissingWhisperX|BrokenCut]
       o trim logo após uma falha aceita as bordas novas nos três
       casos de 4(c): youtube_error, transcription_error e exceção
       inesperada (internal_error), em primeiro plano
       plano: matriz 4(c); QA Rodada 2, achado do passo 4
       nasceu verde (a tarefa já grava failed com except
       BaseException); RED pela mutação exigida (except BaseException
       → except WordcutError em tasks/process.py, aplicada e revertida
       na hora, cmp com a cópia = idêntico): 1 failed, 3 passed —
       FAILED …[BrokenCut]: WordcutError: A pregação 1 está sendo
       processada. (busy, service/sermons.py:218)

04:37  🟢 GREEN  test_a_sermon_whose_processing_failed_can_be_trimmed_
       again_at_once[RefusingYouTube|MissingWhisperX|BrokenCut]  ·
       3 passed (+ variante destacada, 4 passed)

04:38  ✅ PASSO 4/6 — Tipo de tarefa e serviço  ·  +2 testes
       (parametrização)  ·  suíte 472  ·  ruff, format e mypy limpos
       ·  produção intocada  ·  nenhum processo wordcut.tasks.runner
       nem filho inofensivo vivo

## Rodada 3 · QA

04:39  📊 SUÍTE  472 passed  ·  0 failed
       uv run pytest -q; ruff check, ruff format --check e mypy limpos;
       nenhum processo wordcut.tasks.runner vivo

04:40  🧬 MUTAÇÕES · passo 4 (falha da tarefa)  ·  2 de 2 exigidas mortas
       ☠️  except BaseException → except WordcutError       1 teste
       ☠️  tarefa sem set_status failed no erro             4 testes
       🚨  except BaseException → except Exception   SOBREVIVEU — fora
           da barra: 4(c) não pede KeyboardInterrupt; observação

04:41  🔎 QA     passo 4/6 — Tipo de tarefa e serviço  ·  ✅ PASS
       trim após falha parametrizado nos três casos de 4(c); a mutação
       except WordcutError fica vermelha em [BrokenCut]

04:41  🔎 QA     passos 1, 2, 3, 5, 6  ·  ✅ PASS (sem regressão)
       produção intocada desde a Rodada 2; suíte verde

04:41  📝 NOTA   mutações só na cópia do scratchpad; working tree
       intocada; nenhum processo wordcut.tasks.runner vivo
