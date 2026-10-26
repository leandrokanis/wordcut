## Plano de QA

baseline_commit: b0af62e9f463c430a015a749b1e88096ebeb329f

10:32  📐 BARRA   padrão completo = JSON exato do cenário 1 do spec.md
       teste unitário de DEFAULT_CAPTION e teste de CLI `cut caption <id>
       --json` num corte novo; igualdade de dicionário, não subconjunto

10:32  📐 BARRA   faixas com as duas bordas de cada lado
       size 24/160 aceitos, 23/161 recusados; offset 0/100 e -1/101;
       border 0/12 e -1/13; cada recusa é invalid_argument (saída 2)

10:33  📐 BARRA   desenho provado em pixels com Pillow, sem vídeo
       CaptionRenderer.render de uma legenda curta com cores distintas
       (texto #00FF00, borda #FF0000) para os pixels não se confundirem

10:33  📐 BARRA   padrão novo desenha igual ao legado
       render(to_style(DEFAULT_CAPTION, 1920)) == render com DEFAULT_STYLE,
       pixel a pixel; protege short.py e test_captions.py

10:34  🧬 EXIGE   stroke_fill fixo em preto  ·  vermelha
       com border_color #FF0000 o teste de pixels tem de falhar

10:34  🧬 EXIGE   alpha da sombra fixo em 140  ·  vermelha
       none e strong precisam de testes que distinguem os três níveis

10:34  🧬 EXIGE   centre_y fixo em 960  ·  vermelha
       top e bottom precisam conferir a altura do centro da imagem

10:35  🧬 EXIGE   limite 160 trocado por 161  ·  vermelha
       prova que a borda da faixa é testada, não só um valor do meio

10:35  🧬 EXIGE   upper() removido da cor  ·  vermelha
       "#ffffff" tem de ser gravado "#FFFFFF"

10:35  🧬 EXIGE   --position sem ajustar offset  ·  vermelha
       `--position bottom` tem de levar offset a 80

10:36  🧬 EXIGE   mark_edited removido do update_caption  ·  vermelha
       sem isso `sermon suggest` apaga o estilo de um corte sugerido

10:36  🧬 EXIGE   catálogo de fontes ignorado (DEFAULT_FONT fixo)  ·  verde
       com uma fonte só, a escolha não aparece em pixel; a prova é o
       caminho que to_style entrega; sobreviver aqui não é falha

10:37  ⚠️ LACUNA  plan.md escrito antes dos itens 11–13
       db/cuts.py já lê `caption` (CutRow.caption); falta só gravar.
       service/cuts.py já tem _existing (not_found) e show_cut devolve
       `row.caption or {}`; test_cuts_service.py:147 e :166 cravam {} e
       {"font_size": 72}; mudam com este item, e a mudança é adaptação,
       não enfraquecimento

10:37  ⚠️ LACUNA  `edited` não decidido
       fix-word marca o corte editado (cli.md §8.5); sem isso `sermon
       suggest` apaga o estilo; barra conservadora: alterar e restaurar
       marcam edited; sem isso, passo 3 fica PARCIAL

10:38  ⚠️ LACUNA  "igual ao protótipo" não confere
       protótipo: Topo 20, Centro 50, Base 78, altura 10–90 %; plano:
       15/50/80 e 0–100 %; barra segue o plano, justificativa errada

10:38  ⚠️ LACUNA  offset nas pontas sai do quadro
       centro em 0 % ou 100 % põe meia legenda fora; render.py _overlay
       fatia linhas com top negativo; barra: imagem sempre dentro de
       0..frame_height (o plano diz "cabe no quadro"); sem isso, PARCIAL

10:39  ⚠️ LACUNA  validated(changes) sem base
       a alteração parcial precisa do estilo atual; barra cobra o
       comportamento, não a assinatura

10:39  ⚠️ LACUNA  combinações não decididas
       --position com --offset: offset explícito vence; --reset com
       outra opção: invalid_argument; --offset sozinho mantém position;
       decisões conservadoras do QA, a registrar em cli.md §8.6

10:40  ⚠️ LACUNA  plano não prevê teste de serviço
       só lista testes de modelo, desenho e CLI; passo 3 precisa de
       teste no core (persistência, edited, atomicidade)

## Rodada 1 · implementador

10:36  🔴 RED    test_default_caption_is_the_church_style
       corte sem estilo usa o padrão da igreja, as 9 chaves do cenário 1
       spec.md cenário "ver o estilo padrão"; plan.md decisão Padrão
       E   ModuleNotFoundError: No module named 'wordcut.cuts.caption'

10:37  🟢 GREEN  test_default_caption_is_the_church_style  ·  1 passed

10:37  🔴 RED    test_a_change_applies_only_the_given_fields_over_the_current_style
       a alteração parcial muda só as chaves dadas, sobre o estilo atual
       FR-002; decisão 8 (validated(current, changes))
       E   ImportError: cannot import name 'validated'

10:37  🟢 GREEN  test_a_change_applies_only_the_given_fields_over_the_current_style  ·  2 passed

10:37  🔴 RED    test_a_value_out_of_its_range_is_an_invalid_argument_naming_the_range
       tamanho, altura ou borda fora da faixa é recusado, nas duas bordas
       spec.md casos de borda; plan.md Faixas (24–160, 10–90, 0–12)
       Failed: DID NOT RAISE <class 'wordcut.errors.WordcutError'> (6 failed)

10:37  🟢 GREEN  test_a_value_out_of_its_range_is_an_invalid_argument_naming_the_range  ·  14 passed

10:37  🔴 RED    test_a_colour_is_kept_in_upper_case
       cor #rrggbb aceita em minúsculas e guardada em maiúsculas; fora da
       forma #RRGGBB é recusada (também a cor da borda)
       spec.md casos de borda; plan.md decisão Cor
       AssertionError: assert '#ffd6a0' == '#FFD6A0' (12 failed)

10:37  🟢 GREEN  test_a_colour_is_kept_in_upper_case  ·  26 passed

10:37  🔴 RED    test_choosing_a_position_moves_the_height_to_it
       --position leva o offset a 20/50/78; o offset explícito vence
       plan.md Posição → altura e Combinações (decisões 5 e 6)
       AssertionError: assert ('top', 35) == ('top', 20) (3 failed)

10:38  🟢 GREEN  test_choosing_a_position_moves_the_height_to_it  ·  31 passed

10:38  🔴 RED    test_a_position_or_shadow_out_of_its_choices_is_an_invalid_argument_listing_them
       posição e sombra fora dos valores são recusadas também no core
       qa.md matriz passo 1; FR-004 (nenhuma, suave, forte)
       E   KeyError: 'middle' / Failed: DID NOT RAISE (2 failed)

10:38  🟢 GREEN  test_a_position_or_shadow_out_of_its_choices_is_an_invalid_argument_listing_them  ·  33 passed

10:38  🔴 RED    test_the_font_catalogue_names_each_packaged_font_by_its_own_metadata
       o catálogo lista as fontes de assets/fonts pelo nome dos metadados
       ("Open Sans Bold") e ignora o OFL.txt
       decisão 10 (getname(), sem tabela fixa); spec.md Pressupostos
       E   ModuleNotFoundError: No module named 'wordcut.vertical.fonts'

10:38  🟢 GREEN  test_the_font_catalogue_names_each_packaged_font_by_its_own_metadata  ·  34 passed

10:38  🔴 RED    test_a_font_not_in_the_package_is_an_invalid_argument_listing_the_fonts
       fonte fora do pacote é recusada com as fontes disponíveis em details
       spec.md casos de borda (fonte que não existe no pacote)
       Failed: DID NOT RAISE <class 'wordcut.errors.WordcutError'>

10:38  🟢 GREEN  test_a_font_not_in_the_package_is_an_invalid_argument_listing_the_fonts  ·  36 passed

10:39  🔴 RED    test_an_incomplete_or_old_stored_style_is_completed_by_the_default
       estilo gravado ausente é o padrão; incompleto é completado pelo
       padrão, e chave desconhecida é ignorada, nunca erro
       FR-001; decisão 7
       E   ImportError: cannot import name 'stored_caption'

10:39  🟢 GREEN  test_an_incomplete_or_old_stored_style_is_completed_by_the_default  ·  38 passed

10:39  ✅ PASSO 1/5 — Modelo e validação  ·  +38 testes (15 funções)  ·  suíte 1052

10:39  🔴 RED    test_the_drawing_style_carries_every_chosen_field
       to_style leva tamanho, cor, borda, cor da borda, sombra forte,
       altura de bottom (78 % de 1920) e o arquivo da fonte do catálogo
       FR-004; decisões 5 e 11
       E   ImportError: cannot import name 'to_style'

10:39  🟢 GREEN  test_the_drawing_style_carries_every_chosen_field  ·  39 passed

10:40  🔴 RED    test_the_border_is_drawn_in_its_colour_around_text_in_its_colour
       texto #00FF00 com borda #FF0000: há pixels opacos das duas cores
       FR-004 (cor e cor da borda); qa.md mutação stroke_fill fixo
       E       assert (True, False) == (True, True)

10:40  🟢 GREEN  test_the_border_is_drawn_in_its_colour_around_text_in_its_colour  ·  12 passed

10:40  🔴 RED    test_each_shadow_level_draws_black_at_its_own_strength
       none não deixa preto; soft deixa preto com alpha ~140/255; strong
       com ~220/255; os três níveis se distinguem nos pixels
       FR-004 (nenhuma, suave, forte); qa.md mutação alpha fixo em 140
       E       assert 0.5490196347236633 == 0.86274509803...7 ± 0.0196 (strong)
       (a 1ª tentativa tinha tolerância de 1/255 e o soft mediu 137/255
       por anti-aliasing; tolerância ajustada para 5/255)

10:40  🟢 GREEN  test_each_shadow_level_draws_black_at_its_own_strength  ·  16 passed
       (com test_without_a_border_no_pixel_has_the_border_colour, guarda
       da matriz que já passava: stroke_width 0 não desenha borda)

10:40  🔴 RED    test_a_large_caption_at_either_end_of_the_frame_stays_inside_it
       legenda de 160 px em duas linhas, com altura 10 % ou 90 %, fica
       inteira no quadro (encostada na borda)
       decisão 4; render.py _overlay fatia linhas com top negativo
       E       assert (False, True) == (True, True)  (offset 10)
       E       assert (True, False) == (True, True)  (offset 90)
       (test_the_caption_is_centred_at_the_height_of_its_position, 20/50/78
       → 384/960/1498, já passa com o to_style do ciclo anterior)

10:41  🟢 GREEN  test_a_large_caption_at_either_end_of_the_frame_stays_inside_it  ·  21 passed

10:41  🟢 GREEN  test_the_default_caption_draws_exactly_like_the_legacy_default_style  ·  23 passed
       (com test_a_larger_size_draws_a_taller_caption; as duas são guardas
       da matriz, regressão do DEFAULT_STYLE, e passaram de primeira)

10:42  ✅ PASSO 2/5 — Desenho  ·  +13 testes  ·  suíte 1065

10:42  🔴 RED    test_a_new_cut_has_the_church_style
       o estilo de um corte sem estilo gravado é o padrão completo
       FR-001; spec.md cenário "ver o estilo padrão"
       E   ImportError: cannot import name 'caption_of'

10:42  🟢 GREEN  test_a_new_cut_has_the_church_style  ·  1 passed

10:42  🔴 RED    test_a_change_alters_only_the_given_fields_over_the_current_style
       alterar muda só o informado, sobre o estilo já alterado, e o estilo
       efetivo do corte passa a refletir a mudança
       FR-002; spec.md cenário "mudar o estilo"
       E   ImportError: cannot import name 'update_caption'

10:42  🟢 GREEN  test_a_change_alters_only_the_given_fields_over_the_current_style  ·  2 passed

10:42  🔴 RED    test_a_change_marks_the_cut_edited_at_that_moment
       alterar o estilo marca o corte editado e atualiza updated_at, para
       o sermon suggest não apagar o estilo de um sugerido
       decisão 3; qa.md mutação mark_edited removido
       E       assert (False, datet...) == (True, dateti...)
       (test_a_change_stores_the_whole_style_in_the_cut já passa: o
       set_caption do ciclo anterior grava o estilo completo)

10:43  🟢 GREEN  test_a_change_marks_the_cut_edited_at_that_moment  ·  4 passed

10:43  🔴 RED    test_resetting_brings_back_the_church_style_turned_on
       --reset volta ao padrão ligado, grava NULL e marca o corte editado
       FR-003; spec.md cenário "desligar e restaurar"; decisão 3
       E   ImportError: cannot import name 'reset_caption'

10:43  🟢 GREEN  test_resetting_brings_back_the_church_style_turned_on  ·  6 passed

10:43  🔴 RED    test_the_shown_cut_carries_its_effective_style
       cut show traz o estilo efetivo: o padrão completo quando NULL,
       nunca {}, e a alteração depois de feita
       decisão 2; docs/cli.md §8.2; qa.md mutação "or {}" mantido
       E       AssertionError: assert ({}, {'enable...FFD600', ...}) == ...

10:43  🟢 GREEN  test_the_shown_cut_carries_its_effective_style  ·  28 passed
       (test_cuts_service.py: só as asserções das linhas 147 e 166 trocaram
       {} e {"font_size": 72} pelo estilo efetivo, o padrão)

10:44  🟢 GREEN  guardas do passo 3  ·  13 passed
       recusa não grava nada; estilo gravado incompleto completado pelo
       padrão; not_found em caption_of, update_caption e reset_caption;
       --off/--on mudam só enabled; passaram sem produção nova

10:44  ✅ PASSO 3/5 — Serviço  ·  +13 testes  ·  suíte 1078

10:45  🔴 RED    test_caption_of_a_new_cut_prints_the_church_style_and_exits_0
       cut caption <id> --json num corte novo devolve o JSON exato do
       cenário 1, com saída 0
       spec.md cenário "ver o estilo padrão"; FR-002 (sem opções mostra)
       E       AssertionError: assert (2, {'error':...}) == (0, {...})

10:45  🟢 GREEN  test_caption_of_a_new_cut_prints_the_church_style_and_exits_0  ·  1 passed

10:45  🔴 RED    test_caption_with_options_changes_only_those_and_cut_show_carries_the_new_style
       o comando literal do cenário 2 muda só tamanho, cor, posição (e a
       altura para 78) e sombra; cut show --json traz o mesmo caption
       spec.md cenário "mudar o estilo"; FR-002
       E       ... (2, {'error': {'code': 'invalid_argument', 'message':
       'Argumento não reconhecido; veja wordcut cut caption --help.'}})

10:45  🟢 GREEN  test_caption_with_options_changes_only_those_and_cut_show_carries_the_new_style  ·  2 passed

10:45  🔴 RED    test_caption_off_then_reset_turns_it_off_and_back_to_the_church_style
       --off desliga e mantém o resto; --reset volta ao padrão ligado
       spec.md cenário "desligar e restaurar"; FR-003
       E       ... (2, {'error': ... 'Argumento não reconhecido; veja wordcut
       cut caption --help.'}}) para --reset

10:46  🟢 GREEN  test_caption_off_then_reset_turns_it_off_and_back_to_the_church_style  ·  3 passed

10:46  🔴 RED    test_caption_reset_with_another_option_exits_2_and_changes_nothing
       --reset com outra opção de estilo é ambíguo: invalid_argument
       (saída 2) e nada muda
       decisão 6; docs/cli.md §8.6
       E       KeyError: 'error'  (o --reset venceu e saiu 0)

10:46  🟢 GREEN  test_caption_reset_with_another_option_exits_2_and_changes_nothing  ·  4 passed

10:46  🔴 RED    test_caption_without_json_prints_the_style_in_words_and_exits_0
       sem --json, o estilo sai em texto legível, em português, saída 0
       qa.md matriz passo 4 (saída em texto); docs/cli.md §3.2
       E       assert (0, "{'enable...': 'soft'}\n") == (0, 'Legenda:...')

10:46  🟢 GREEN  test_caption_without_json_prints_the_style_in_words_and_exits_0  ·  5 passed

10:49  🟢 GREEN  guardas do passo 4  ·  18 passed
       saída 2 com details para --on --off, fonte, cores, tamanho 23,
       altura 91, borda 13, posição e sombra fora dos valores (nada muda);
       corte inexistente sai 3; --on religa; sem opções não grava; --help
       com exemplo. test_cut_command.py: a lista de ações do --help ganhou
       caption (adaptação, sem tirar asserção)

10:49  ✅ PASSO 4/5 — CLI  ·  +18 testes  ·  suíte 1097

10:51  ✅ PASSO 5/5 — Documentação  ·  +0 testes  ·  suíte 1097
       CHANGELOG (Adicionado: cut caption e desenho; Alterado: cut show);
       docs/cli.md §8.2 (estilo efetivo) e §8.6 (faixas, 20/50/78, 10–90,
       combinações, edited, JSON); sem TDD (documentação)

## Rodada 1 · QA

10:52  📊 SUÍTE  1097 passed  ·  0 failed
       ruff check, ruff format --check e mypy strict limpos

10:53  🔎 QA     passo 1/5 — Modelo e validação  ·  ✅ PASS
       padrão exato, faixas 24–160/10–90/0–12 nas duas bordas, cor em
       maiúsculas, 20/50/78, offset vence, catálogo pelos metadados

10:53  🔎 QA     passo 2/5 — Desenho  ·  ✅ PASS
       pixels de texto e borda, três sombras, centro 384/960/1498,
       encosto em 10/90, regressão pixel a pixel do padrão legado

10:53  🔎 QA     passo 3/5 — Serviço  ·  ✅ PASS
       JSON completo, edited e updated_at, reset grava NULL, recusa
       não grava, show_cut com o estilo efetivo, not_found nas três

10:54  🔎 QA     passo 4/5 — CLI  ·  ✅ PASS
       cenários 1–3 literais, nove recusas com saída 2 e nada muda,
       --reset com opção sai 2, not_found sai 3, texto e --help

10:54  🔎 QA     passo 5/5 — Documentação  ·  ✅ PASS
       CHANGELOG e cli.md §8.2/§8.6 batem com RANGES, POSITIONS e
       SHADOW_LOOKS do código

10:55  🧬 MUTAÇÕES · cobradas pela barra + extras  ·  25 de 27 mortas
       ☠️  limite 160→161, upper() fora, position sem offset    1 cada
       ☠️  stroke_fill preto, alpha fixo 140, centre_y 960     1 cada
       ☠️  encosto na borda fora, mark_edited fora, or {}      1 cada
       ☠️  soft 150, strong desloc. 3, size/cor/borda/offset   1 cada
       ☠️  grava sem validar, reset grava estilo, --reset+opç  1 cada
       ☠️  fonte/posição/sombra sem checar no core, 78→80     1 cada
       🚨  if shadow_alpha removido      SOBREVIVEU — equivalente:
       alpha 0 não desenha nada; não é achado
       🚨  catálogo → DEFAULT_FONT       SOBREVIVEU — previsto na barra
       (verde): com uma fonte só, a escolha não aparece

10:55  🔎 QA     pontos do implementador
       soft mede 137/255 por anti-aliasing; ±5/255 é o "cerca de 140"
       da matriz; strong mata o alpha fixo em 140, e soft 150 também
       morre; none com deslocamento 0 é inócuo (alpha 0) e não contraria
       a barra, que só fixa o alpha
