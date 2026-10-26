## Plano de QA

baseline_commit: 13ce97aa833e6c81e29f409299a45745e29ecc90

17:55  📐 BARRA   cards com título, texto, duração e estado, na ordem do serviço
       teste de rota com renderRoute + fakeShellApi e corpo de cuts.py::_listed;
       o descartado da resposta tem de aparecer por último sem sort no cliente

17:55  📐 BARRA   abrir um sugerido marca chosen e só então navega
       fakeApi com resposta segurada por promessa: a rota /cuts/34 só aparece
       depois do 200 do POST choose; RecordedCall confere método e URL

17:55  📐 BARRA   descartar e restaurar pelo menu, com a lista pedida de novo
       userEvent no botão "Mais ações" e nos menuitems; segundo GET /cuts no
       RecordedCall; Escape fecha o menu

17:55  📐 BARRA   camadas em tempo da live, somente leitura
       style da faixa contra sermon_start 1801.2 da fixture processedSermon;
       nenhum slider nas camadas, inclusive como admin

17:55  🧬 EXIGE   remover o POST choose ao abrir  ·  vermelha
       abrir um sugerido DEVE marcá-lo escolhido (feature 1.1.e)

17:55  🧬 EXIGE   navegar antes do 200 do choose  ·  vermelha
       erro no choose não pode levar ao nível 3 com o estado errado

17:55  🧬 EXIGE   mandar choose para chosen ou discarded  ·  vermelha
       a API transforma discarded em chosen; só sugerido é escolhido ao abrir

17:55  🧬 EXIGE   não pedir a lista de novo após discard  ·  vermelha
       a ordem é a do serviço; sem o novo GET o card não vai para o fim

17:55  🧬 EXIGE   omitir sermon_start na posição da camada  ·  vermelha
       os tempos de corte são em tempo da pregação, a timeline em tempo da live

17:55  🧬 EXIGE   esconder suggestion_error  ·  vermelha
       a pregação sem cortes precisa dizer o motivo

17:55  🧬 EXIGE   desenhar alça na camada para admin  ·  vermelha
       2.1.c é da onda 6; nesta onda nenhuma edição

17:55  🧬 EXIGE   não recarregar cortes no done do processamento  ·  vermelha
       sem isso o painel fica vazio depois de processar

17:55  ⚠️ LACUNA  cut list não traz tempo; a faixa só tem ids de palavra
       sem decidir a fonte, o passo 3 fica PARCIAL; barra aceita o vão dos
       trechos de GET /cuts/{id}/preview + sermon_start e pendência de API

17:55  ⚠️ LACUNA  plano anterior ao item 22: sem painel .side, Timeline só
       com "Vídeo", ProcessButton recarrega só a pregação
       painel em .side, prop layers na Timeline, cortes recarregados com a
       pregação; testes do item 22 sem alteração

17:55  ⚠️ LACUNA  types.ts e client.ts fora do Contexto de código
       sem listCuts/chooseCut/discardCut/restoreCut e o tipo do item, o
       typecheck dos passos 1–2 não fecha

17:55  ⚠️ LACUNA  choose para chosen/discarded e erro do choose não decididos
       barra: choose só em suggested, discarded não abre, navega após 200

17:55  ⚠️ LACUNA  cor da camada "por estado" diverge do protótipo (por índice)
       recomenda cor por índice, a mesma no card e na camada

17:55  ⚠️ LACUNA  passo 4 só cita CHANGELOG
       incluir docs/architecture/README.md e a pendência de API no roadmap

## Rodada 1 · implementador

17:59  ▶️ PASSOS   1, 2, 3, 4 (todos os `- [ ]`; qa.md sem rodada anterior)
       decisões do orquestrador registradas no plan.md (L1 alterada:
       `start`/`end` em `cut list`; D1–D5, L2–L12 pelo QA)

18:00  --- Passo 1: Painel e cards ---

18:00  🔴 RED    shows one card per cut of the processed sermon, with
       title, text, duration and state
       pregação processada: um card por item de GET /cuts, com título,
       texto montado, duração e estado legível
       spec · Listar; FR-001; barra passo 1 (a)
       Unable to find role="complementary" and name "Cortes"

18:00  🟢 GREEN  shows one card per cut of the processed sermon, with
       title, text, duration and state  ·  1 passed

18:01  🔴 RED    keeps the service's order, the discarded cut last and
       marked as discarded
       a ordem é a da resposta; o descartado vem marcado (data-discarded)
       spec · Listar (descartados por último); barra passo 1 (b)
       expected [ 'Fé no deserto', true ], received [ …, false ]

18:01  🟢 GREEN  keeps the service's order, the discarded cut last and
       marked as discarded  ·  2 passed

18:01  🔴 RED    offers Descartar in the menu of a kept cut and Restaurar in
       that of a discarded one
       "Mais ações" abre um menu com o item certo para o estado do corte
       spec · Descartar/restaurar pelo menu; barra passo 1 (c); L11
       Unable to find … role "button" and name "Mais ações"

18:01  🟢 GREEN  offers Descartar in the menu of a kept cut and Restaurar in
       that of a discarded one  ·  3 passed

18:02  🔴 RED    closes the menu on Escape / on a click outside
       o menu fecha com Escape e com clique fora; um menu aberto por vez
       (este último já vale pelo estado único do painel)
       barra passo 1 (c); L11
       expected <div class="cmenu" role="menu">…(1)</div> to be null

18:02  🟢 GREEN  closes the menu on Escape / on a click outside; keeps one
       menu open at a time  ·  6 passed

18:02  🔴 RED    says why a processed sermon has no cuts when the
       suggestion failed
       sem cortes e com suggestion_error: a message da API no painel
       borda da spec; barra passo 1 (d)
       Unable to find an element with the text: /O LLM não está configurado…/

18:02  🟢 GREEN  says why a processed sermon has no cuts when the
       suggestion failed  ·  7 passed

18:02  🔴 RED    says so when the processed sermon has no cuts and no
       suggestion error
       zero cortes sem erro: "Nenhum corte nesta pregação." (protótipo)
       barra passo 1 (e); L8
       Unable to find an element with the text: Nenhum corte nesta pregação.

18:02  🟢 GREEN  says so when the processed sermon has no cuts and no
       suggestion error  ·  8 passed

18:03  🔴 RED    tells a created/trimmed/processing/failed sermon that the
       cuts come after processing, without asking for them
       antes de processed: texto do protótipo e nenhum GET /cuts
       barra passo 1 (f); FR-001; L8
       Unable to find an element with the text: Os cortes aparecem depois…

18:03  🔴 RED    shows the API's message when the cuts cannot be loaded
       GET /cuts 502: a mensagem no painel, sem tela branca
       barra passo 1 (g)
       Unable to find role="alert"

18:03  🟢 GREEN  tells a … sermon that the cuts come after processing;
       shows the API's message when the cuts cannot be loaded  ·  13 passed

18:03  🔵 REFACTOR  corpo do painel em PanelBody/EmptyPanel; helper
       titleOf no teste de ordem  ·  13 passed

18:03  ✅ PASSO 1/4 — Painel e cards  ·  +13 testes  ·  suíte 137

18:03  --- Passo 2: Abrir, descartar, restaurar ---

18:04  🔴 RED    opens a suggested cut by choosing it, and goes to its level
       once the API answers
       clicar num sugerido: POST choose e, só depois do 200, a rota /cuts/34
       spec · Abrir; FR-002; barra passo 2 (a); L6
       Unable to find an element with the text: Esta tela está em construção.

18:04  🟢 GREEN  opens a suggested cut by choosing it, and goes to its level
       once the API answers  ·  14 passed

18:04  🔴 RED    opens a chosen cut without choosing it again; does not open
       a discarded cut
       escolhido navega sem POST; descartado não abre nem chama a API
       barra passo 2 (b)(c); L6
       Unable to find … Esta tela está em construção. / sent [POST …choose]

18:04  🟢 GREEN  opens a chosen cut without choosing it again; does not open
       a discarded cut  ·  16 passed

18:05  🔴 RED    stays on the sermon with the API's message when choosing the
       cut fails
       erro no choose: mensagem no painel, sem navegar
       barra passo 2 (d); L6
       Unable to find role="alert"

18:05  🟢 GREEN  stays on the sermon with the API's message when choosing the
       cut fails  ·  17 passed

18:06  🔴 RED    discards from the menu and shows the list as the service
       gives it again
       "Descartar" chama POST discard e pede GET /cuts de novo; o card fica
       descartado e no fim, conforme a resposta
       spec · Descartar/restaurar; FR-002; barra passo 2 (e); L7
       Unable to find an element with the text: Descartado

18:06  🟢 GREEN  discards from the menu and shows the list as the service
       gives it again  ·  18 passed

18:06  🧪 TESTE  restores from the menu and shows the cut suggested again;
       keeps the card as it was, with the API's message, when discarding
       fails; never asks the API to change a cut's content
       barra passo 2 (f)(g)(h); passaram de primeira porque o mesmo
       toggleDiscard serve aos dois sentidos — provados por mutação:
       restaurar com discardCut → 1 vermelho; engolir o erro → 1 vermelho

18:06  🧬 MUTAÇÃO  exigidas pela barra (passos 1 e 2), todas vermelhas:
       sem POST choose (3) · navega antes do 200 (2) · choose em chosen (1) ·
       abre descartado (1) · sem nova lista após discard (2) · esconde
       suggestion_error (1) · inverte Descartar/Restaurar (5) · GET /cuts
       com trimmed (4)

18:06  ✅ PASSO 2/4 — Abrir, descartar, restaurar  ·  +8 testes  ·  suíte 145

18:07  --- Passo 3: Camadas na timeline ---

18:07  🔴 RED    test_listed_cut_spans_from_its_earliest_start_to_its_latest_
       end_in_sermon_time
       cada item de cut list traz start/end: menor início e maior fim dos
       trechos, em tempo da pregação, ao milissegundo
       decisão L1 do orquestrador (plan.md)
       KeyError: 'start'

18:08  🟢 GREEN  test_listed_cut_spans_from_its_earliest_start_to_its_latest_
       end_in_sermon_time  ·  23 passed (+1 asserção antiga ajustada: o
       dict exato de cut list ganhou start/end, contrato novo da L1)

18:08  🧪 TESTE  test_listed_cut_span_is_kept_to_the_millisecond
       12.34567 → 12.346; passou de primeira (o round veio no GREEN);
       sem o round → 1 vermelho

18:08  🧪 TESTE  CLI test_list_with_json_gives_each_cut_its_span_in_sermon_
       time; API test_listing_gives_each_cut_its_span_in_sermon_time
       contrato nas duas bordas; passam pelo core; com list_cuts sem o
       span → 2 vermelhos  ·  73 passed

18:09  🔴 RED    draws one layer per cut, in the panel's order, above the
       video track
       pregação processada: uma camada (cabeçalho nº+título e faixa) por
       corte, acima de "Vídeo", na ordem do painel
       spec · Camadas; FR-003; barra passo 3 (a); D2
       expected { layers: [], heads: [ '', 'Vídeo' ] } to deeply equal …

18:09  🟢 GREEN  draws one layer per cut, in the panel's order, above the
       video track  ·  1 passed

18:09  🔴 RED    places each layer in time of the live, from the sermon's
       start in the live
       faixa em sermon_start + start, largura end − start (fixture 1801.2)
       barra passo 3 (b); D5; L1
       width '…%' ≠ '…%': a largura saía de (s+end)−(s+start), com erro de
       ponto flutuante

18:09  🟢 GREEN  places each layer in time of the live, from the sermon's
       start in the live  ·  2 passed

18:10  🔴 RED    colors each layer as its card, by place in the list, and
       marks the discarded one
       cor por índice, a mesma no card e na camada; descartado marcado
       barra passo 3 (c); L9
       card sem --c: layers [[#7b93ff,false],[#4cc38a,true]] ≠ cards [['',…]]

18:10  🟢 GREEN  colors each layer as its card, by place in the list, and
       marks the discarded one  ·  3 passed

18:11  🧪 TESTE  draws the layers without handles and changes nothing when
       one is pressed, as admin / as assistant; draws no layer before the
       sermon is processed; loads the cuts into the panel and the timeline
       once the processing is done
       barra passo 3 (d)(e)(f); D3; passaram de primeira (camada nasceu sem
       alça; useSermonCuts já tem status/processed_at na chave)

18:11  🧬 MUTAÇÃO  exigidas pela barra (passo 3), todas vermelhas:
       omite sermon_start (1) · alça na camada (2) · camada com trimmed,
       sem os portões de status e de busca (1) · sem recarga no done (1)

18:11  🎨 VISUAL  app.css: .l2 (.side 340 px + .work), cards, menu, rnum,
       .lane.cut/.clip.ct; em ≤ 860 px o painel empilha abaixo da timeline
       (D1); sem TDD

18:11  ✅ PASSO 3/4 — Camadas na timeline  ·  +11 testes (7 web, 4
       Python)  ·  suíte web 152; testes do item 22 sem alteração

18:14  --- Passo 4: Documentação ---

18:14  📝 DOCS   CHANGELOG (painel em Adicionado; start/end de cut list em
       Alterado), docs/architecture/README.md (CutsPanel, CutCard,
       CutLayers; itens 24 a 26), docs/cli.md §8.1 e docs/api.md (start/end);
       sem ADR nova (nenhuma biblioteca entrou); a pendência de API da L1
       não existe mais, resolvida neste item

18:14  ✅ PASSO 4/4 — Documentação  ·  +0 testes  ·  suíte web 152

18:14  🏁 FINAL   web 152 passed · typecheck, lint, build limpos ·
       pytest 1510 passed · ruff check/format e mypy limpos · sem commit
       (override do orquestrador)

## Rodada 1 · QA

18:15  📊 SUÍTE  web 152 passed · 0 failed  ·  typecheck, lint, build limpos

18:17  📊 SUÍTE  pytest 1510 passed · 0 failed  ·  ruff check/format e mypy
       limpos

18:25  🧬 MUTAÇÕES · web, cópia no scratchpad  ·  25 de 26 mortas
       ☠️  sem POST choose                                  3 testes
       ☠️  choose em qualquer estado                        1 teste
       ☠️  navega antes do 200 / mesmo com erro             2 / 1 testes
       ☠️  abre descartado                                  1 teste
       ☠️  sem nova lista após discard                      2 testes
       ☠️  restaurar chama discard / engole erro            1 / 1 teste
       ☠️  esconde suggestion_error                         1 teste
       ☠️  GET /cuts com trimmed                            5 testes
       ☠️  sem recarga no done                              1 teste
       ☠️  inverte Descartar/Restaurar                      5 testes
       ☠️  Escape / clique fora não fecham                  1 / 1 teste
       ☠️  ordena no cliente                                3 testes
       ☠️  omite sermon_start / largura end                 1 / 1 teste
       ☠️  alça na camada                                   2 testes
       ☠️  camadas abaixo de "Vídeo"                        1 teste
       ☠️  cor/data-discarded em card e camada              5 testes
       🚨  cutLayers sem o portão de status  SOBREVIVEU — equivalente: o
           useSermonCuts já devolve [] fora de processed; o portão só
           evita um quadro com a lista antiga ao reprocessar

18:27  🧬 MUTAÇÕES · core, cópia no scratchpad  ·  3 de 3 mortas
       ☠️  start/end sem round                              1 teste
       ☠️  start do primeiro trecho, não o menor            2 testes
       ☠️  list_cuts sem o span (_listed)                   5 testes

18:28  🔎 QA     passo 1/4 — Painel e cards  ·  ✅ PASS
       (a)–(g) da matriz por teste de rota; mutações exigidas vermelhas

18:28  🔎 QA     passo 2/4 — Abrir, descartar, restaurar  ·  ✅ PASS
       ordem choose→navegação, erro, discard/restore e (h) provados

18:28  🔎 QA     passo 3/4 — Camadas na timeline  ·  ✅ PASS
       start/end no core, CLI e API; camada em sermon_start + start;
       asserção antiga do core ajustada com justificativa (contrato L1)

18:28  🔎 QA     passo 4/4 — Documentação  ·  ✅ PASS
       CHANGELOG, arquitetura, cli.md §8.1, api.md; sem ADR nova
