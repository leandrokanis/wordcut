## Plano de QA

baseline_commit: 80e64ff34df99cb5f4389d5888672e852536f2f0

11:00  📐 BARRA   padrões de §8.7 em RenderOptions()
       teste unitário com igualdade de todos os campos; o caption vem
       do corte, não de RenderOptions

11:01  📐 BARRA   opções padrão = timeline atual
       Timeline == entre a chamada sem opções e a chamada com os padrões
       explícitos; test_timeline/test_cleanup/test_assemble intocados

11:02  📐 BARRA   cada opção visível no comando gerado ou na timeline
       asserção sobre argumentos do ffmpeg (-s, -crf, loudnorm, fade,
       afade); sem rodar ffmpeg, a não ser na integração

11:03  📐 BARRA   integração real só no clipe lavfi de 2 s
       ffprobe: 720x1280, com áudio, duração da timeline ±1 quadro mais a
       folga do AAC; não pode sair skipped com o ffmpeg instalado

11:04  📐 BARRA   cut render --wait --json com dublês
       stdout com as seis chaves de §9, stderr com [render], arquivo
       existente em path absoluto, linha em renders

11:05  📐 BARRA   --estimate sem tarefa, sem trava e sem gravar
       lock_owner segurando a trava; task list vazio; render_options
       e caption do corte iguais antes e depois

11:06  🧬 EXIGE   padrão pauses trocado para short  ·  vermelha
       prova que a regressão da timeline padrão é cobrada

11:06  🧬 EXIGE   flag fillers ignorada  ·  vermelha
       "hã" precisa ficar com --fillers keep

11:07  🧬 EXIGE   flag stammers ignorada  ·  vermelha
       "o, o Senhor" precisa ficar com --stammers keep

11:07  🧬 EXIGE   CRF fixo em 18  ·  vermelha
       --quality small precisa gerar -crf 26

11:08  🧬 EXIGE   resolução fixa em 1080x1920  ·  vermelha
       a integração em 720x1280 tem de falhar

11:08  🧬 EXIGE   loudnorm sempre aplicado  ·  vermelha
       --no-normalize precisa tirar o loudnorm do filtro

11:09  🧬 EXIGE   fade nunca aplicado  ·  vermelha
       --fade (padrão) precisa pôr fade e afade de 0,5 s

11:09  🧬 EXIGE   correções ignoradas na legenda  ·  vermelha
       uma palavra corrigida tem de chegar corrigida ao render dublê

11:10  🧬 EXIGE   opções gravadas antes da trava  ·  vermelha
       com busy, render_options tem de ficar igual

11:10  🧬 EXIGE   linha inserida antes do sucesso do render  ·  vermelha
       com falha do gateway, renders fica vazio e a pasta do corte vazia

11:11  🧬 EXIGE   estimate gravando opções  ·  vermelha
       --estimate --pauses short não muda o render_options do corte

11:12  ⚠️ LACUNA  correções de grafia por word_id × EditList.corrections
       o plano manda montar o EditList, cuja correção é por texto;
       sem a decisão 1, os passos 4 e 6 ficam PARCIAL

11:13  ⚠️ LACUNA  taxa de quadros da estimativa sem mídia
       plan_timeline exige fps e o banco não guarda; sem constante
       nominal ou porta, o passo 2 (estimate) fica PARCIAL

11:14  ⚠️ LACUNA  onde fica o render_id no task show
       shown_task só expõe cut_id e result; decisão 6 adota
       result.render_id; sem ela o cenário em segundo plano fica PARCIAL

11:15  ⚠️ LACUNA  momento de gravar as opções e o caption
       o plano diz "ao iniciar" sem dizer se é antes ou depois da trava;
       decisões 2 e 3; sem elas o passo 5 fica PARCIAL

11:16  ⚠️ LACUNA  legenda em 720x1280
       to_style só escala centre_y; size, contorno e max_width ficam em
       px de 1080; cuts/caption.py fora do Contexto de código

11:17  ⚠️ LACUNA  vídeo ausente em pregação processed
       o spec diz sermon_not_processed e sermon download dá
       internal_error; decisão 8 segue o código existente

11:18  ⚠️ LACUNA  runner render destacado em teste
       a guarda da ADR-0017 não barra ffmpeg/OpenCV; decisão 12 exige
       harmless_tasks e nenhum detached_tasks com render

11:19  ⚠️ LACUNA  ADR da porta RenderGateways
       o passo 7 não prevê ADR; CLAUDE.md pede ADR para decisão de
       arquitetura nova; o passo 7 fica PARCIAL sem ADR ou justificativa

## Rodada 1 · implementador

11:09  🔴 RED    test_the_options_default_to_those_of_the_export_dialog
       RenderOptions() traz os padrões de docs/cli.md §8.7
       FR-002; matriz do passo 1
       E   ModuleNotFoundError: No module named 'wordcut.rendering.options'

11:10  🟢 GREEN  test_the_options_default_to_those_of_the_export_dialog  ·  1 passed

11:10  🔴 RED    test_a_given_option_beats_the_saved_one_and_a_saved_one_beats_the_default
       o informado vence o salvo; o salvo vence o padrão
       FR-002; matriz do passo 1 (mutação: salvo vencendo o informado)
       E   ImportError: cannot import name 'merged' from 'wordcut.rendering.options'

11:10  🟢 GREEN  test_a_given_option_beats_the_saved_one_and_a_saved_one_beats_the_default  ·  2 passed

11:10  🔴 RED    test_saved_unknown_keys_are_ignored_and_saved_invalid_values_are_the_defaults
       chave salva desconhecida é ignorada; valor salvo inválido volta ao padrão
       QA, decisão 4; matriz do passo 1
       E       TypeError: RenderOptions.__init__() got an unexpected keyword argument 'speed'

11:10  🟢 GREEN  test_saved_unknown_keys_are_ignored_and_saved_invalid_values_are_the_defaults  ·  3 passed

11:10  🔴 RED    test_a_given_resolution_out_of_the_choices_is_an_invalid_argument_that_lists_them
       valor informado fora das escolhas dá invalid_argument com argument e choices, sem eco
       ADR-0015; matriz do passo 1 (mutação: validação de resolution removida)
       E       Failed: DID NOT RAISE <class 'wordcut.errors.WordcutError'>

11:11  🟢 GREEN  test_a_given_resolution_out_of_the_choices_is_an_invalid_argument_that_lists_them  ·  4 passed

11:11  🔴 RED    test_the_summary_has_the_nine_choices_with_the_caption_the_cut_shows
       summary() traz as nove escolhas, com o caption do corte
       QA, decisão 3; matriz do passo 1
       E       AttributeError: 'RenderOptions' object has no attribute 'summary'

11:11  🟢 GREEN  test_the_summary_has_the_nine_choices_with_the_caption_the_cut_shows  ·  5 passed

11:11  ✅ PASSO 1/7 — Opções  ·  +5 testes  ·  suíte 1102

11:11  🔴 RED    test_keeping_fillers_keeps_them_and_still_removes_the_stammers
       com fillers=False, hã e né ficam e os gaguejos saem
       FR-003; matriz do passo 2 (mutação: flag fillers ignorada)
       E       TypeError: remove_hesitations() got an unexpected keyword argument 'fillers'

11:11  🟢 GREEN  test_keeping_fillers_keeps_them_and_still_removes_the_stammers  ·  1 passed

11:12  🔴 RED    test_keeping_stammers_keeps_word_and_phrase_stammers_and_still_removes_the_fillers
       com stammers=False, 'o, o Senhor' e 'não teve, não teve' ficam e 'hã' sai
       FR-003; matriz do passo 2 (mutação: flag stammers ignorada)
       E       AssertionError: assert 'o Senhor não teve sonho?' == 'o, o Senhor ...o teve sonho?'

11:12  🟢 GREEN  test_keeping_stammers_keeps_word_and_phrase_stammers_and_still_removes_the_fillers  ·  2 passed

11:12  🟢 GREEN  test_keeping_both_removes_nothing  ·  3 passed
       passou sem produção: combinação das duas flags já provadas; fica como
       prova do critério 'com os dois False, nada sai' da matriz

11:12  🔴 RED    test_original_pauses_keep_a_long_pause_inside_a_segment_in_one_clip
       pausas original mantêm a pausa longa entre palavras do mesmo trecho, num clipe só
       FR-003; matriz do passo 2 (mutação: original caindo em natural)
       E   ImportError: cannot import name 'Cleanup' from 'wordcut.edit.timeline'

11:12  🟢 GREEN  test_original_pauses_keep_a_long_pause_inside_a_segment_in_one_clip  ·  1 passed

11:13  🔴 RED    test_short_pauses_keep_less_breath_inside_and_after_a_sentence
       pausas short: 0,08 s no meio da frase e 0,20 s depois de ponto
       FR-003; decisão do plano (Pausas); matriz do passo 2
       E       KeyError: 'short'

11:13  🟢 GREEN  test_short_pauses_keep_less_breath_inside_and_after_a_sentence  ·  2 passed

11:13  🔴 RED    test_the_timeline_keeps_fillers_and_stammers_when_the_cleanup_keeps_them
       a timeline repassa fillers e stammers à limpeza
       FR-003; matriz do passo 2
       E       AssertionError: assert (['o', 'Senho...mated=False))) == (['o,', 'o', ... 'reina'], ())

11:13  🟢 GREEN  test_the_timeline_keeps_fillers_and_stammers_when_the_cleanup_keeps_them  ·  3 passed

11:13  🔴 RED    test_a_segment_given_by_its_words_may_be_one_word_that_starts_where_it_ends
       a timeline aceita trechos dados pelas palavras, inclusive uma palavra com start == end
       orquestrador, decisão 1; QA, divergências (Segment exige start < end)
       E   ImportError: cannot import name 'plan_segments' from 'wordcut.edit.timeline'

11:13  🟢 GREEN  test_a_segment_given_by_its_words_may_be_one_word_that_starts_where_it_ends  ·  4 passed

11:13  🟢 GREEN  test_the_default_cleanup_plans_the_same_timeline_as_before_the_options  ·  5 passed
       passou sem produção: é a regressão do padrão (hesitação, gaguejo, pausa
       longa e trechos fora de ordem); conferido que avermelha com o padrão
       de pausas trocado para short

11:14  🔴 RED    test_the_estimate_shortens_with_short_pauses_and_grows_when_fillers_stay
       a estimativa é a timeline com as opções, sem mídia; muda com pauses e fillers
       FR-009; QA, decisão 9; matriz do passo 2
       E   ModuleNotFoundError: No module named 'wordcut.rendering.estimate'

11:14  🟢 GREEN  test_the_estimate_shortens_with_short_pauses_and_grows_when_fillers_stay  ·  1 passed

11:14  🟢 GREEN  test_the_estimate_is_the_timeline_at_the_nominal_rate_without_audio_loudness  ·  2 passed
       passou sem produção: fixa a regra da decisão 9 (taxa nominal, energia
       ausente) como asserção da matriz do passo 2

11:15  ✅ PASSO 2/7 — Limpeza e pausas  ·  +10 testes  ·  suíte 1112
       mutações cobradas (fillers ignorada, stammers ignorada, original caindo
       em natural, padrão de pausas em short) conferidas: todas vermelhas

11:15  🔴 RED    test_joins_without_smoothing_have_no_audio_fade
       emendas sem suavização: nenhum afade na montagem
       FR-004; matriz do passo 3
       E       TypeError: montage_command() got an unexpected keyword argument 'smooth_joins'

11:15  🟢 GREEN  test_joins_without_smoothing_have_no_audio_fade  ·  1 passed

11:16  🟢 GREEN  test_smoothed_joins_fade_the_audio_out_and_in_at_every_clip  ·  2 passed
       passou sem produção: o ligado é o comportamento anterior; fica como
       prova do par ligado/desligado da matriz do passo 3

11:16  🔴 RED    test_the_encoder_takes_frames_in_the_chosen_resolution
       o codificador recebe quadros na resolução escolhida (-s 720x1280)
       FR-007; matriz do passo 3 (mutação: resolução fixa em 1080x1920)
       E   ImportError: cannot import name 'Encoding' from 'wordcut.vertical.render'

11:16  🟢 GREEN  test_the_encoder_takes_frames_in_the_chosen_resolution  ·  3 passed
       o reenquadramento usa a mesma geometria; provado na integração

11:16  🔴 RED    test_a_smaller_file_is_encoded_with_a_higher_crf
       qualidade small codifica com -crf 26
       FR-007; decisão do plano (Qualidade); mutação: CRF fixo em 18
       E       TypeError: Encoding.__init__() got an unexpected keyword argument 'crf'

11:16  🟢 GREEN  test_a_smaller_file_is_encoded_with_a_higher_crf  ·  4 passed

11:17  🔴 RED    test_without_normalization_the_audio_is_only_resampled
       sem normalização sai só o loudnorm; o aresample=48000 fica
       FR-005; orquestrador, decisão 14; mutação: loudnorm sempre aplicado
       E       TypeError: Encoding.__init__() got an unexpected keyword argument 'normalize'

11:17  🟢 GREEN  test_without_normalization_the_audio_is_only_resampled  ·  5 passed

11:17  🔴 RED    test_without_normalization_the_audio_is_only_resampled
       correção do diário: o GREEN acima foi registrado antes de conferir; a
       edição do Encoding não tinha entrado e a rodada saiu 3 failed
       E       AttributeError: 'Encoding' object has no attribute 'normalize'

11:17  🟢 GREEN  test_without_normalization_the_audio_is_only_resampled  ·  6 passed
       inclui test_normalization_brings_the_audio_to_minus_14_lufs, que passou
       sem produção: o ligado é o comportamento anterior

11:17  🔴 RED    test_a_fade_takes_half_a_second_in_and_out_of_video_and_audio
       fade de 0,5 s de vídeo e áudio no início e no fim; saída em duração − 0,5
       FR-004; decisão do plano (Fade); mutação: fade nunca aplicado
       E       TypeError: Encoding.__init__() got an unexpected keyword argument 'fade'

11:17  🟢 GREEN  test_a_fade_takes_half_a_second_in_and_out_of_video_and_audio  ·  7 passed

11:17  🔴 RED    test_a_cut_shorter_than_both_fades_fades_for_half_its_length_each_way
       corte com menos de 1 s: fade limitado à metade da duração, sem st negativo
       orquestrador, decisão 13; QA, decisão 13
       E       AssertionError: assert 'fade=t=in:st...ormat=yuv420p' == 'fade=t=in:st...ormat=yuv420p'

11:18  🟢 GREEN  test_a_cut_shorter_than_both_fades_fades_for_half_its_length_each_way  ·  8 passed

11:18  🔴 RED    test_on_a_720_by_1280_frame_the_style_shrinks_by_two_thirds
       em 720x1280 a legenda escala tamanho, contorno, sombra e max_width por 720/1080
       orquestrador, decisão 2; QA, decisão 15
       E       assert (72, 6, 5, 960, 640, 1280) == (48, 4, 3, 640, 640, 1280)

11:19  🟢 GREEN  test_on_a_720_by_1280_frame_the_style_shrinks_by_two_thirds  ·  passed

11:19  🔴 RED    test_the_cut_is_assembled_then_detected_then_rendered_into_the_output
       render_cut chama assemble, detect e render nessa ordem e entrega o arquivo
       FR-001; matriz do passo 4
       E   ModuleNotFoundError: No module named 'wordcut.rendering.pipeline'

11:19  🟢 GREEN  test_the_cut_is_assembled_then_detected_then_rendered_into_the_output  ·  1 passed

11:20  🔴 RED    test_the_captions_carry_the_fix_of_one_word_and_not_of_another_spelled_the_same
       a correção por word_id chega à legenda e não muda a outra palavra de mesma grafia
       FR-006; orquestrador, decisão 1; mutação: correções ignoradas na legenda
       E       AssertionError: assert '' == 'Esther orou. Ester jejuou.'

11:20  🟢 GREEN  test_the_captions_carry_the_fix_of_one_word_and_not_of_another_spelled_the_same  ·  2 passed
       edit/screen.caption_words nasce aqui (text.py não pode importar a
       timeline: ciclo edit_list → text → timeline)

11:21  🟢 GREEN  REFACTOR short.caption_words sobre edit.screen.caption_words  ·  765 passed
       equivalência conferida à parte (correções que cruzam clipes e trechos)

11:21  🔴 RED    test_with_the_caption_off_no_caption_reaches_the_render
       legenda desligada: nenhuma legenda chega ao render
       FR-006; mutação: caption desligado ignorado
       E       AssertionError: assert [CaptionImage...ype=float32))] == []

11:21  🟢 GREEN  test_with_the_caption_off_no_caption_reaches_the_render  ·  3 passed

11:21  🔴 RED    test_the_options_reach_the_montage_and_the_encode
       smooth_joins chega à montagem; resolução, qualidade, normalização e fade ao render
       FR-004, FR-005, FR-007; matriz do passo 4; mutação: CRF fixo em 18
       E       assert (True, Encodi..., fade=False)) == (True, Encodi...e, fade=True))

11:21  🟢 GREEN  test_the_options_reach_the_montage_and_the_encode  ·  5 passed

11:22  🟢 GREEN  test_in_720_by_1280_the_captions_are_drawn_across_its_width_at_the_cut_s_height  ·  6 passed
       passou sem produção: o renderer já recebe a geometria do Encoding e o
       to_style escalado; fica como prova da decisão 15 no pipeline

11:22  🔴 RED    test_the_progress_goes_through_each_stage_in_order_always_forward
       o progresso passa por montando, detectando, legendas e renderizando, sempre para frente
       matriz do passo 4; docs/cli.md §4.5
       E       AssertionError: assert ([], True) == (['montando',...zando'], True)

11:22  🟢 GREEN  test_the_progress_goes_through_each_stage_in_order_always_forward  ·  7 passed

11:22  🔴 RED    test_the_camera_jumps_where_the_next_segment_starts_and_plays_in_the_cut_s_order
       os trechos tocam na ordem do corte e a câmera salta onde o trecho seguinte começa
       FR-001; matriz do passo 4 (trechos na ordem do corte)
       E       AssertionError: assert (['Esther', '... 'orou.'], []) == (['Esther', '...orou.'], [37])

11:22  🟢 GREEN  test_the_camera_jumps_where_the_next_segment_starts_and_plays_in_the_cut_s_order  ·  8 passed

11:23  🟢 GREEN  test_a_failed_render_raises_and_leaves_neither_the_output_nor_the_work_folder  ·  9 passed
       passou sem produção: o temporário na pasta de trabalho já existia
       mutações do passo 4 conferidas: output direto, correções ignoradas e
       caption desligado ignorado ficam vermelhas

11:23  🟢 GREEN  test_the_export_in_720_by_1280_has_that_size_audio_and_the_timeline_s_duration  ·  1 passed
       integração real (lavfi 2 s, 320x180 → 720x1280, small), detecção dublê;
       passou na primeira execução, com a produção dos ciclos unitários;
       mutações conferidas: resolução fixa em 1080x1920 no pipeline e no
       reenquadramento avermelham; nenhum ffmpeg sobrou

11:25  🔴 RED    test_a_test_that_reaches_the_real_rendering_gateways_fails
       a fixture autouse no_real_rendering faz a fábrica real falhar no teste
       orquestrador, decisão 9; QA, decisão 12
       E       Failed: DID NOT RAISE AssertionError

11:25  🟢 GREEN  test_a_test_that_reaches_the_real_rendering_gateways_fails  ·  11 passed

11:26  ✅ PASSO 3/7 — Montagem e codificação  ·  +9 testes  ·  suíte 1132
       fechado junto com o 4: a integração real passa pelo render_cut

11:26  ✅ PASSO 4/7 — Pipeline do corte  ·  +11 testes  ·  suíte 1132

11:26  🔴 RED    test_a_recorded_export_is_listed_with_its_cut_path_duration_options_and_date
       a exportação gravada é listada no corte com caminho, duração, opções e data
       FR-008; matriz do passo 5 (migração 0009 e repositório)
       E   ImportError: cannot import name 'renders' from 'wordcut.db'

11:26  🟢 GREEN  test_a_recorded_export_is_listed_with_its_cut_path_duration_options_and_date  ·  passed

11:26  🟢 GREEN  test_the_exports_go_with_their_cut  ·  passed
       passou sem produção: ON DELETE CASCADE da migração 0009

11:26  🔴 RED    test_an_export_s_path_can_be_changed_and_it_is_found_by_its_id
       o caminho da exportação muda na mesma transação e ela é achada pelo ID
       orquestrador, decisão 11 (arquivo <render_id>.mp4)
       E           AttributeError: module 'wordcut.db.renders' has no attribute 'set_path'

11:26  🟢 GREEN  test_an_export_s_path_can_be_changed_and_it_is_found_by_its_id  ·  3 passed

11:27  🔴 RED    test_the_export_options_stored_on_a_cut_are_read_back_and_nothing_else_changes
       set_render_options grava as opções no corte, sem marcar edited
       orquestrador, decisão 5
       E           AttributeError: module 'wordcut.db.cuts' has no attribute 'set_render_options'

11:27  🟢 GREEN  test_the_export_options_stored_on_a_cut_are_read_back_and_nothing_else_changes  ·  passed

11:28  🔴 RED    test_render_is_a_builtin_kind_that_holds_the_processing_lock
       o tipo render é nativo e segura a trava
       FR-001; docs/cli.md §6.1; matriz do passo 5
       E           ValueError: unknown task kind: render

11:28  🟢 GREEN  test_render_is_a_builtin_kind_that_holds_the_processing_lock  ·  1 passed

11:28  🔴 RED    test_an_export_in_the_foreground_is_recorded_with_its_file_named_after_it
       em primeiro plano, a exportação fica registrada com as seis chaves e o arquivo em
       media/cuts/<cut_id>/<render_id>.mp4
       FR-008; QA, decisões 5 e 6; matriz do passo 5
       E   ModuleNotFoundError: No module named 'wordcut.service.rendering'

11:28  🟢 GREEN  test_an_export_in_the_foreground_is_recorded_with_its_file_named_after_it  ·  2 passed

11:29  🟢 GREEN  test_a_second_export_without_options_repeats_the_options_of_the_first  ·  3 passed
       passou sem produção: o admit já grava as opções mescladas

11:29  🔴 RED    test_an_export_without_caption_turns_the_cut_s_caption_off_as_cut_caption_off_does
       --no-caption grava o enabled do estilo do corte, como cut caption --off
       orquestrador, decisão 3; QA, decisão 3
       E               KeyError: 'caption'

11:29  🟢 GREEN  test_an_export_without_caption_turns_the_cut_s_caption_off_as_cut_caption_off_does  ·  4 passed

11:29  🟢 GREEN  test_with_the_machine_busy_the_export_is_refused_without_a_task_and_saves_nothing  ·  5 passed
       passou sem produção: a trava vem antes do admit; mutação 'opções
       gravadas antes da trava' conferida: vermelha

11:29  🔴 RED    test_a_cut_that_does_not_exist_is_not_found_even_with_the_machine_busy
       corte inexistente dá not_found antes da trava
       QA, decisão 10 (ordem das recusas)
       E       AssertionError: assert ('busy', {'ki...-03:00', ...}) == ('not_found', {'cut_id': 999})

11:29  🟢 GREEN  test_a_cut_that_does_not_exist_is_not_found_even_with_the_machine_busy  ·  6 passed

11:30  🔴 RED    test_a_cut_of_a_sermon_being_processed_again_is_refused_as_not_processed
       pregação não processada dá sermon_not_processed (5), antes da trava
       spec, casos de borda; QA, decisões 8 e 10
       E       AssertionError: assert ('busy', 4) == ('sermon_not_processed', 5)

11:30  🟢 GREEN  test_a_cut_of_a_sermon_being_processed_again_is_refused_as_not_processed  ·  7 passed

11:30  🔴 RED    test_an_invalid_option_is_refused_before_the_cut_is_looked_up
       argumento inválido (2) vem antes de corte inexistente (3)
       QA, decisão 10
       E       AssertionError: assert ('not_found', {'cut_id': 999}) == ('invalid_arg...h', 'small']})

11:30  🟢 GREEN  test_an_invalid_option_is_refused_before_the_cut_is_looked_up  ·  8 passed

11:31  🟢 GREEN  test_a_failed_export_fails_the_task_and_leaves_no_export_and_no_file  ·  9 passed
       passou sem produção: temporário no pipeline e finally na tarefa; mutação
       'linha inserida antes do sucesso do render' conferida: vermelha

11:31  🟢 GREEN  test_an_interrupted_export_is_failed_as_interrupted_and_leaves_no_file  ·  10 passed
       passou sem produção: Ctrl+C segue o caminho existente (interrupted) e o
       finally limpa; prova da decisão 7

11:31  🔴 RED    test_an_estimate_gives_duration_and_options_saving_nothing_even_busy_and_without_video
       estimate_render dá duração e resumo, sem gravar, com a trava ocupada e sem o vídeo
       FR-009; QA, decisão 9; mutação: estimate gravando opções
       E   ImportError: cannot import name 'estimate_render' from 'wordcut.service.rendering'

11:31  🟢 GREEN  test_an_estimate_gives_duration_and_options_saving_nothing_even_busy_and_without_video  ·  11 passed

11:31  🔴 RED    test_shown_cut_has_the_sermon_cut_fields_plus_assembly_and_default_style_and_no_renders (e test_shown_cut_keeps_the_caption_style_and_export_options_stored_with_it)
       cut show traz as opções efetivas no lugar do marcador provisório
       orquestrador, decisão 4; QA, decisão 4 (só as duas asserções)
       E       AssertionError: assert {'id': 1, 'st...8, ...}], ...} == {'id': 1, 'se...alcança', ...}

11:32  🟢 GREEN  test_shown_cut_has_the_sermon_cut_fields_plus_assembly_and_default_style_and_no_renders  ·  passed

11:32  🟢 GREEN  test_cut_show_lists_the_exports_and_the_options_the_next_one_uses  ·  12 passed
       passou com a produção do ciclo anterior (show_cut com renders)

11:33  🟢 GREEN  REFACTOR _recorded: arquivo movido sem linha confirmada é apagado  ·  12 passed
       QA, decisão 16; o commit que falha depois do os.replace não tem dublê
       simples, então o caminho fica sem teste próprio

11:33  ✅ PASSO 5/7 — Persistência e tarefa  ·  +16 testes  ·  suíte 1148
       mutações conferidas: opções antes da trava, linha antes do render e
       estimate gravando: todas vermelhas

11:34  🔴 RED    test_render_with_wait_prints_the_export_and_the_stages_on_stderr
       cut render --wait --json: saída 0, seis chaves, path absoluto existente, [render] no stderr
       spec, cenário 'exportar com as opções padrão'; matriz do passo 6
       E       KeyError: 'cut_id'  (a ação render não existe: erro de uso no stdout)

11:34  🟢 GREEN  test_render_with_wait_prints_the_export_and_the_stages_on_stderr  ·  1 passed

11:35  🟢 GREEN  test_options_given_once_are_saved_and_the_next_render_without_options_repeats_them  ·  2 passed
       passou sem produção: o serviço já grava; prova o cenário 'opções salvas no corte'

11:35  🔴 RED    test_an_estimate_saves_nothing_creates_no_task_and_does_not_wait_for_the_lock
       --estimate --json com a trava ocupada: duração e opções, sem tarefa, sem gravar
       spec, cenário 'estimativa sem renderizar'; FR-009
       E       KeyError: 'options'  (sem --estimate, a exportação deu busy)

11:35  🟢 GREEN  test_an_estimate_saves_nothing_creates_no_task_and_does_not_wait_for_the_lock  ·  3 passed

11:35  🟢 GREEN  test_render_without_wait_answers_the_running_render_task  ·  4 passed
       passou sem produção: launch() já devolve a tarefa; harmless_tasks, sem processo sobrando

11:35  🟢 GREEN  test_task_show_of_a_finished_render_carries_the_render_id  ·  5 passed
       passou sem produção: o resultado da tarefa já é {render_id}

11:35  🟢 GREEN  test_render_without_caption_leaves_the_cut_caption_off, test_a_value_out_of_the_choices_is_refused_with_them_and_without_echo (4 casos), test_a_switch_given_both_ways_is_refused  ·  11 passed
       passaram sem produção: serviço (update_caption) e argparse com choices e
       grupo exclusivo, pelo contrato existente (ADR-0015)

11:36  🟢 GREEN  test_a_cut_that_does_not_exist_exits_3 (render e estimate), test_with_the_machine_busy_render_exits_4_and_creates_no_task, test_a_cut_of_a_sermon_not_processed_exits_5  ·  15 passed
       passaram sem produção: as recusas do serviço (passo 5) pelo contrato da CLI

11:36  🔴 RED    test_without_json_the_answer_is_readable[estimate], test_without_json_or_wait_the_launched_task_is_readable
       sem --json, estimativa e tarefa lançada têm saída legível com saída 0
       matriz do passo 6; docs/cli.md §4.2
       E       assert (1, False) == (0, True)  (o texto da exportação não serve aos outros formatos)

11:36  🟢 GREEN  test_without_json_the_answer_is_readable, test_without_json_or_wait_the_launched_task_is_readable  ·  18 passed

11:36  🔴 RED    test_an_estimate_does_not_wait_for_anything_so_wait_with_it_is_refused
       --estimate não cria tarefa, então --wait junto é erro de uso
       decisão desta rodada (sermon create recusa --wait sem --process do mesmo jeito)
       E       KeyError: 'error'

11:36  🟢 GREEN  test_an_estimate_does_not_wait_for_anything_so_wait_with_it_is_refused  ·  19 passed

11:38  🟢 GREEN  test_each_cut_action_help_shows_an_example_ready_to_copy[render], test_cut_help_lists_its_actions  ·  passed
       test_cut_command.py só ganhou render na lista de ações

11:38  ✅ PASSO 6/7 — CLI  ·  +20 testes  ·  suíte 1168
       nenhum processo sobrando (harmless_tasks e lock_owner recolhidos)

11:42  ✅ PASSO 7/7 — Documentação  ·  +0 testes  ·  suíte 1168
       ADR-0018 e índice; arquitetura (§3, §4, fluxo 5.2 da CLI); README;
       CONTRIBUTING; CHANGELOG; docs/cli.md §8.2, §8.7, §10 e §14; frase do
       vídeo ausente no spec.md; valores conferidos contra as constantes
       (CRF 18/26, pausas 0,15/0,40 e 0,08/0,20, fade 0,5 s, −14 LUFS, 30 q/s)

## Rodada 1 · QA

11:44  📊 SUÍTE  1168 passed  ·  0 failed
       integração -rs: 1 passed, 0 skipped; ruff, format e mypy limpos

11:45  🔎 QA     passo 1/7 — Opções  ·  ✅ PASS
       padrões de §8.7, mescla, validação sem eco e as nove escolhas

11:45  🔎 QA     passo 2/7 — Limpeza e pausas  ·  ✅ PASS
       flags separadas, três pausas, regressão Timeline ==, estimativa sem mídia

11:46  🔎 QA     passo 3/7 — Montagem e codificação  ·  ✅ PASS
       comandos gerados por opção; integração real 720x1280 sem skipped

11:46  🔎 QA     passo 4/7 — Pipeline do corte  ·  ✅ PASS
       ordem dos gateways, correção por word_id, falha sem output

11:47  🔎 QA     passo 5/7 — Persistência e tarefa  ·  ⚠️ PARCIAL
       decisão 16: o ramo do commit que falha em _recorded não tem teste

11:47  🔎 QA     passo 6/7 — CLI  ·  ✅ PASS
       seis chaves, estimate sem trava, recusas 2/3/4/5, render_id

11:48  🔎 QA     passo 7/7 — Documentação  ·  ✅ PASS
       ADR-0018 e índice, arquitetura, CHANGELOG, cli.md; valores conferem

11:48  🧬 MUTAÇÕES · matriz (16) + Cleanup short + reenquadramento + D16 + D8
       ·  18 de 20 mortas
       ☠️  pauses padrão → short (RenderOptions e Cleanup)      2 testes
       ☠️  mescla com o salvo vencendo o informado              1 teste
       ☠️  validação de resolution removida                     1 teste
       ☠️  flag fillers ignorada                                1 teste
       ☠️  flag stammers ignorada                               1 teste
       ☠️  original caindo em natural                           1 teste
       ☠️  CRF fixo em 18                                       1 teste
       ☠️  resolução fixa (pipeline; reenquadramento)  unitário + integração
       ☠️  loudnorm sempre aplicado                             1 teste
       ☠️  fade nunca aplicado                                  1 teste
       ☠️  correções ignoradas na legenda                       1 teste
       ☠️  caption desligado ignorado                           1 teste
       ☠️  output escrito direto, sem temporário                1 teste
       ☠️  opções gravadas antes da trava                       1 teste
       ☠️  linha inserida antes do sucesso do render            1 teste
       ☠️  estimate gravando opções                             1 teste
       🚨  _exportable sem conferir o vídeo   SOBREVIVEU — a saída
           continuaria internal_error; falta só o teste do render
       🚨  _recorded sem apagar o arquivo     SOBREVIVEU — decisão 16
           sem prova; passo 5 PARCIAL

11:48  ⚠️ LACUNA  comentários: cuts/caption.py:20–23 descolado de POSITIONS;
       rendering/pipeline.py:26 referencia specs/ em vez de docs/cli.md §8.7

## Rodada 2 · implementador

11:51  🔧 FIX    comentários: em cuts/caption.py, o de POSITIONS volta para cima
       da constante; em rendering/pipeline.py, QUALITY_CRF cita docs/cli.md
       §8.7; plan.md sem a tabela antiga do Contexto de código

11:51  🟢 GREEN  test_an_export_whose_record_is_not_committed_leaves_no_file  ·  13 passed
       o commit da linha falha depois do os.replace: internal_error, nenhuma
       linha em renders e a pasta do corte vazia
       QA, decisão 16; dublê: conexão de wordcut.tasks.render cujo commit
       levanta sqlite3.OperationalError (falha de disco)
       passou sem produção: o ramo de _recorded já existia

11:51  🧬 MUTAÇÃO D16  _recorded sem o moved.unlink  ·  🔴 vermelha
       E       AssertionError: assert ('internal_er...[], ['1.mp4']) ==
       ('internal_error', [], [])

11:52  🟢 GREEN  test_a_cut_whose_processed_sermon_lost_its_video_is_refused_as_an_internal_error  ·  14 passed
       pregação processed sem o arquivo do vídeo: internal_error antes da
       tarefa, sem tarefa, sem linha em renders e sem arquivo
       QA, decisões 8 e 10; docs/cli.md §8.7
       passou sem produção: _exportable já confere o vídeo com sermon_video

11:52  🧬 MUTAÇÃO D8  _exportable sem conferir o vídeo (só processed_row)  ·  🔴 vermelha
       E         At index 1 diff: [{'id': 1, 'kind': 'render', 'status':
       'failed', …}] != []

11:53  ✅ PASSO 5/7 — Persistência e tarefa  ·  +2 testes  ·  suíte 1170
       reaberto pelo QA (rodada 1); D16 e D8 vermelhas; ruff, format e mypy
       limpos; integração ffmpeg (lavfi 2 s) passou sem skip

## Rodada 2 · QA

11:54  📊 SUÍTE  1170 passed  ·  0 failed
       integração -rs: 1 passed, 0 skipped; ruff, format e mypy limpos

11:55  🔎 QA     passo 5/7 — Persistência e tarefa  ·  ✅ PASS
       D16 e D8 com teste; as cinco mutações do passo vermelhas

11:55  🧬 MUTAÇÕES · passo 5 (3 da matriz) + D16 + D8  ·  5 de 5 mortas
       ☠️  _recorded sem o moved.unlink (D16)                   1 teste
       ☠️  _exportable só com processed_row (D8)                1 teste
       ☠️  opções gravadas antes da trava                       1 teste
       ☠️  estimate gravando opções                            2 testes
       ☠️  linha inserida antes do render                      3 testes

11:56  🔎 QA     comentários e plan.md  ·  ✅ PASS
       POSITIONS com o seu comentário; QUALITY_CRF cita docs/cli.md §8.7;
       nenhum specs/ no código; plan.md sem a tabela antiga
