## Plano de QA

baseline_commit: 5448fb0ee8adea0c591f948935277fa20df9466e

17:08  📐 BARRA   a tela /sermons/:id troca o LevelPlaceholder pelo nível 2
       teste de rota com renderRoute + fakeShellApi; o teste "Pregação não
       encontrada." do routes.test.tsx continua verde

17:08  📐 BARRA   player por porta, sem YouTube real
       PlayerLike dublê injetado (contexto ou prop); nenhum <script> nem
       <iframe> de youtube.com no DOM dos testes

17:08  📐 BARRA   bordas por arraste e por I/O, salvas sozinhas
       pointerdown/move/up com getBoundingClientRect stubado; teclado com
       userEvent; PATCH conferido no RecordedCall do fakeApi; fake timers
       para o debounce de 500 ms

17:08  📐 BARRA   progresso por SSE e fechamento do fluxo
       FakeEventSource em src/test (vi.stubGlobal), com emit(event, data) e
       close() espionado; progress muda o botão, done/failed fecham

17:08  🧬 EXIGE   remover o close() no done  ·  vermelha
       o cliente DEVE fechar o EventSource (docs/api.md §3)

17:08  🧬 EXIGE   trocar o mínimo de 60 s por 0  ·  vermelha
       a borda não pode passar da outra menos 1 min, nem por I/O

17:08  🧬 EXIGE   mandar force: false no Reprocessar  ·  vermelha
       sem force o POST dá 409 would_discard_edits

17:08  🧬 EXIGE   PATCH a cada pointermove em vez de no pointerup  ·  vermelha
       um arraste gera um PATCH só

17:08  🧬 EXIGE   mostrar "Salvo" antes da resposta do PATCH  ·  vermelha
       "Salvo" só com 200; 409/400 mostram o motivo e não "Salvo"

17:08  ⚠️ LACUNA  Sermon em api/types.ts não tem live_start, live_end,
       sermon_start, sermon_end, processed_at, last_task nem cuts
       sem estender o tipo (e a fixture) não há bordas a desenhar

17:08  ⚠️ LACUNA  api/client.ts não tem PATCH nem processSermon, e não
       existe dublê de EventSource
       plan.md não lista client.ts, types.ts, fixtures.ts nem um
       test/fakeEventSource.ts

17:08  ⚠️ LACUNA  a API não diz se as bordas mudaram desde o processamento
       (PATCH sem needs_reprocess; sermon_start/end ajustados às palavras)
       Reprocessar só pode vir do estado da sessão; fica PARCIAL sem regra

17:08  ⚠️ LACUNA  live_finished só é atualizado pelo próprio process
       desabilitar Processar pelo campo trava a pregação para sempre

17:08  ⚠️ LACUNA  a API não tem miniaturas nem forma de onda
       FR-001 e 1.1.b pedem; o plano não diz o que a timeline mostra

17:08  ⚠️ LACUNA  o vídeo processado começa em sermon_start; o player em
       <video> precisa converter tempo da live; borda fora do trecho
       processado não tem quadro no <video>
       plan.md não decide a conversão nem o quadro fora do trecho

17:08  ⚠️ LACUNA  YouTube IFrame vem de outro host
       ADR-0022: "Nenhum recurso vem de outro host"; precisa de ADR nova

17:08  ⚠️ LACUNA  "termina com a lista de cortes" contra "Fora: painel de
       cortes (item 23)"
       o critério precisa ser reescrito para o que este item entrega

17:08  ⚠️ LACUNA  tarefa já em andamento ao abrir a página (status
       processing, last_task running) e processamento que falhou (1.1.c.3)
       plan.md não diz se o SSE reabre por last_task.id nem se failed
       volta a oferecer Processar

## Rodada 1 · implementador

17:13  ▶️ PASSOS  1, 2, 3, 4 (todos os - [ ] do plan.md); decisões L1-L12
       registradas no plan.md e no spec.md antes do código

--- Passo 1: Player e timeline ---

17:14  🔴 RED    shows the sermon's level, with the timeline, instead of
       the placeholder
       /sermons/:id mostra o nível 2 (região Timeline) no lugar do placeholder
       matriz passo 1 (a); FR-001; L2
       Failed to resolve import "../features/sermon/Player"

17:15  🟢 GREEN  shows the sermon's level, with the timeline, instead of
       the placeholder  ·  1 passed

17:15  🔴 RED    tells a missing sermon apart without losing the path
       (routes.test.tsx, já existente) quebrou com a troca do element
       matriz passo 1 (a): not_found continua "Pregação não encontrada."
       Unable to find an element with the text: Pregação não encontrada.

17:15  🟢 GREEN  tells a missing sermon apart without losing the path
       ·  9 passed

17:15  🔴 RED    previews the live on YouTube from the sermon's start
       before processing
       antes de processar, a prévia é o YouTube da live, a partir de live_start
       matriz passo 1 (b); spec, casos de borda (prévia antes do processamento)
       expected [] to deeply equal [ [ 'youtube', 'abcdefghijk', 1800 ] ]

17:15  🟢 GREEN  previews the live on YouTube from the sermon's start
       before processing  ·  2 passed

17:16  🔴 RED    previews the processed video, served by the API, once the
       sermon is processed
       processada: <video src="/api/sermons/12/video">, com offset sermon_start
       matriz passo 1 (b); L6
       Unable to find a label with the text of: Prévia da pregação processada

17:16  🟢 GREEN  previews the processed video, served by the API, once
       the sermon is processed  ·  3 passed

17:16  🔴 RED    seeks the video to the live time minus the sermon's start;
       tells the video's position as live time (videoPlayer.test.ts)
       o <video> do PlayerLike converte tempo da live em tempo do vídeo
       matriz passo 1 (c); L6
       passou de primeira: videoPlayer.ts entrou no GREEN do primeiro teste
       (adiantado). Prova pela mutação: sem o offset, as duas ficam vermelhas
       expected 1900 to be 100 // expected [ 50, 50 ] to deeply equal
       [ 1850, 1850 ]

17:16  🟢 GREEN  videoPlayer: conversão de tempo  ·  2 passed

17:17  🔴 RED    labels the clip as the sermon, with its length, once it
       has borders
       com bordas, o clipe da faixa Vídeo diz "Pregação · 41:15"
       matriz passo 1 (d); decisão do plano de QA (timeline sem miniaturas)
       Unable to find an element with the text: Pregação · 41:15

17:17  🟢 GREEN  labels the clip as the sermon, with its length, once it
       has borders  ·  1 passed

17:17  🔴 RED    labels the clip as the whole live while the sermon has no
       borders
       sem bordas, o clipe é a live inteira, "Live inteira · 1:58:00"
       matriz passo 1 (d)
       passou de primeira (o ramo entrou no GREEN anterior); mutação
       "label = true" deixa vermelho: Unable to find ... Live inteira

17:17  🟢 GREEN  labels the clip as the whole live while the sermon has
       no borders  ·  2 passed

17:18  🔴 RED    draws the clip between the borders, over the whole live
       faded behind it
       o clipe vai de live_start a live_end; a live inteira, esmaecida atrás
       (data-faded), cobre 0-100%
       matriz passo 1 (d); spec "parte cortada esmaecida"
       Unable to find an accessible element with the role "group" and name
       "Pregação na live"

17:18  🟢 GREEN  draws the clip between the borders, over the whole live
       faded behind it  ·  3 passed

17:18  🔴 RED    marks the ruler in time of the live, every 15 minutes of a
       two-hour live
       a régua marca o tempo da live (0:00 a 1:45:00 numa live de 1:58:00)
       matriz passo 1 (d); decisão do plano de QA (régua em tempo da live)
       Unable to find a label with the text of: Régua da live

17:18  🟢 GREEN  marks the ruler in time of the live  ·  4 passed

17:18  🛡️ GUARDA draws no thumbnails nor waveform, which the API does not
       serve
       sem <img>/<canvas> e sem rota fora de docs/api.md
       decisão do plano de QA; matriz passo 1 (e)
       passa por construção: nenhuma produção nova; prende a decisão

17:18  🔴 RED    keeps the screen when the live's duration is unknown
       live_duration nulo mostra "Duração da live indisponível." na timeline
       matriz passo 1 (f)
       Unable to find an element with the text: Duração da live indisponível.

17:18  🟢 GREEN  keeps the screen when the live's duration is unknown
       ·  11 passed

17:19  🔴 RED    moves the cursor as the player plays; seeks the player to
       the time clicked on the ruler (os dois escritos juntos)
       o cursor segue o PlayerLike; clicar na régua chama seek no tempo da live
       matriz passo 1 (d)
       Unable to find a label with the text of: Cursor
       expected [] to deeply equal [ 1770 ]

17:19  🟢 GREEN  moves the cursor as the player plays; seeks the player
       to the time clicked on the ruler  ·  13 passed

17:19  🔴 RED    previews the live on YouTube outside the processed stretch
       pregação processada: seek fora de [sermon_start, sermon_end] troca a
       prévia para o YouTube, no tempo pedido
       matriz passo 1 (b)(c); L6
       passou de primeira (a troca entrou junto com o handle de seek);
       mutação "sem troca de fonte" deixa vermelho:
       expected [ 'video', …, 1801.2 ] to deeply equal [ 'youtube', … ]

17:19  🟢 GREEN  previews the live on YouTube outside the processed
       stretch  ·  4 passed

17:20  🛡️ GUARDA keeps the preview and the timeline on a <status> sermon,
       without the list's actions (5 estados)
       FR-001 em todos os estados; requisito geral "só as opções do nível"
       passa por construção; prende o comportamento

17:20  🔴 RED    plays the preview from the transport
       o botão Reproduzir toca a prévia pelo PlayerLike
       matriz passo 1 (d) (PlayerLike play/pause)
       Unable to find role="button" and name "Reproduzir"

17:20  🟢 GREEN  plays the preview from the transport  ·  20 passed

17:20  🔧 REFACTOR Transport recebe o ref da prévia, não o valor do
       render; typecheck e lint limpos  ·  85 passed

17:20  ✅ PASSO 1/4 — Player e timeline  ·  +20 testes  ·  suíte 85

--- Passo 2: Bordas ---

17:21  🔴 RED    shows the border's frame in the preview while dragging it
       cada pointermove da borda chama seek do PlayerLike na borda
       spec "a prévia mostra o quadro da borda durante o arraste"; passo 2 (a)
       Unable to find an accessible element with the role "slider" and name
       "Início da pregação"

17:21  🟢 GREEN  shows the border's frame in the preview while dragging it
       ·  21 passed

17:22  🔴 RED    saves the borders once, as numbers, when the dragged border
       is released
       soltar a borda gera um PATCH só, com {start, end} numéricos
       passo 2 (b); L10 (PATCH imediato ao soltar)
       expected [] to deeply equal [ [ '/api/sermons/12', …(1) ] ]

17:22  🔴 RED    (mesmo teste) dois PATCH: o arraste aberto do teste
       anterior seguia ouvindo a window depois de desmontar
       expected [ [ '/api/sermons/12', …(1) ], …(1) ] to deeply equal [ … ]

17:22  🟢 GREEN  saves the borders once, as numbers, when the dragged
       border is released  ·  22 passed
       a timeline solta os ouvintes da window ao desmontar

17:22  🧬 MUTAÇÃO PATCH a cada pointermove  ·  vermelha
       expected [ …, …(2) ] to deeply equal [ [ '/api/sermons/12', …(1) ] ]

17:22  🔴 RED    stops a dragged border a minute away from the other
       o arraste não deixa a faixa abaixo de 60 s
       passo 2 (d); core MIN_SERMON_SECONDS
       passou de primeira (o limite entrou no GREEN do arraste)

17:22  🧬 MUTAÇÃO mínimo de 60 s trocado por 0  ·  vermelha
       expect(element).toHaveAttribute("aria-valuenow", "4215")

17:22  🟢 GREEN  stops a dragged border a minute away from the other
       ·  3 passed

17:23  🔴 RED    says Salvo only once the API has saved the borders
       "Salvo" (ui/Saved) só depois do 200 do PATCH
       passo 2 (e); spec "salvas sozinhas (indicador Salvo)"
       Unable to find an element with the text: Salvo

17:23  🟢 GREEN  says Salvo only once the API has saved the borders
       ·  24 passed

17:23  🧬 MUTAÇÃO "Salvo" antes da resposta do PATCH  ·  vermelha
       expected [ …(2) ] to deeply equal [ null, Anything ]

17:24  🔴 RED    shows why the borders were not saved and puts them back
       (409 sermon_too_short, 409 busy, 400)
       erro do PATCH: motivo da API junto à timeline, sem "Salvo", borda volta
       passo 2 (e); L11; requisito geral "valor inválido não é salvo"
       Unable to find an element with the text: A pregação precisa ter pelo
       menos 60 s.

17:24  🟢 GREEN  shows why the borders were not saved and puts them back
       ·  27 passed

17:24  🔴 RED    brings the start to the cursor with I and saves it half a
       second later
       I leva a borda inicial ao cursor; PATCH só depois de 500 ms
       passo 2 (c); FR-002; L10
       expected [ [], [] ] to deeply equal [ [], [ { start: 2000, end: 4275 } ] ]

17:24  🟢 GREEN  brings the start to the cursor with I and saves it half
       a second later  ·  28 passed

17:24  🔴 RED    saves I and O pressed in a row as one change
       várias teclas seguidas dão um PATCH só
       passo 2 (c); L10
       passou de primeira (o debounce entrou no GREEN anterior); mutação
       "sem clearTimeout" deixa vermelho: expected [ …, …(1) ] to deeply
       equal [ { start: 2000, end: 4000 } ]

17:24  🟢 GREEN  saves I and O pressed in a row as one change  ·  9 passed

17:25  🔴 RED    refuses i/o under a minute from the other border, saying
       why
       I/O não deixam a faixa abaixo de 1 min; dizem o motivo; sem PATCH
       passo 2 (d); protótipo A.markin/markout
       Unable to find an accessible element with the role "alert"

17:25  🟢 GREEN  refuses i/o under a minute from the other border  ·
       31 passed

17:25  🛡️ GUARDA leaves the borders alone while the sermon is processing
       sem alças e I/O ignorados com status processing
       passo 2 (f); passou de primeira (editable entrou com o I/O); mutação
       "editable = true" deixa vermelho: expected [ 2, [ … ] ] to deeply
       equal [ +0, [] ]

17:25  🔴 RED    ignores I typed into a text field; ignores I with a
       modifier held (Ctrl, Meta, Alt)
       passo 2 (f)(g)
       expected [ { start: 2000, end: 4275 } ] to deeply equal []

17:25  🟢 GREEN  ignores I typed into a text field / with a modifier
       ·  36 passed

17:25  🔴 RED    brings the end to the cursor with the Fim aqui button;
       disables Início aqui and Fim aqui while the sermon is processing
       os botões do transporte fazem o mesmo que O/I; indisponíveis em
       processing (protótipo transport())
       passo 2 (c)(f)
       Unable to find an accessible element with the role "button" and name
       `/Fim aqui/`

17:25  🟢 GREEN  Início aqui / Fim aqui  ·  38 passed

17:26  🔴 RED    labels the whole live as the sermon as soon as a border is
       marked
       sem bordas salvas, marcar uma borda já rotula o clipe como "Pregação"
       passo 2 (c); protótipo (trimclip "on" ao arrastar)
       Unable to find an element with the text: Pregação · 1:24:40

17:26  🟢 GREEN  labels the whole live as the sermon as soon as a border
       is marked  ·  104 passed

17:26  🔧 REFACTOR soltar a borda cancela um salvamento de I/O pendente
       ·  104 passed

17:26  ✅ PASSO 2/4 — Bordas  ·  +19 testes  ·  suíte 104

--- Passo 3: Processar/Reprocessar ---

17:26  🔴 RED    follows the task's events at its own address
       o gancho abre EventSource("/api/tasks/9/events")
       passo 3 (b); FR-003; ADR-0020
       Failed to resolve import "./useTaskEvents"

17:26  🟢 GREEN  follows the task's events at its own address  ·  1 passed

17:27  🔴 RED    keeps the task as its progress arrives
       o evento progress atualiza a tarefa (progress 0.35)
       passo 3 (c)
       Cannot read properties of undefined (reading 'task')

17:27  🟢 GREEN  keeps the task as its progress arrives  ·  2 passed

17:27  🔴 RED    closes the stream and tells the end on done/failed;
       closes the stream when the screen goes away
       done/failed fecham o EventSource e avisam o fim; desmontar fecha
       passo 3 (c)(h); docs/api.md §3 (o cliente DEVE fechar)
       expected [ +0, [] ] to deeply equal [ 1, [ [ { id: 9, …(10) } ] ] ]
       expected "spy" to be called 1 times, but got 0 times

17:27  🟢 GREEN  closes the stream on done/failed and on unmount
       ·  5 passed

17:27  🧬 MUTAÇÃO sem close() no done/failed  ·  vermelha
       expected [ +0, [ [ … ] ] ] to deeply equal [ 1, [ [ … ] ] ]

17:27  🔴 RED    offers Processar, not Exportar, on a trimmed sermon
       passo 3 (a); spec "Processar (no lugar de Exportar)"
       Unable to find an accessible element with the role "button" and name
       "Processar"

17:27  🟢 GREEN  offers Processar, not Exportar, on a trimmed sermon
       ·  1 passed

17:28  🔴 RED    keeps Processar off until the sermon has borders, saying so
       passo 3 (a): sem bordas, desabilitado com "Ajuste as bordas…"
       Unable to find an element with the text: Ajuste as bordas do vídeo para
       processar.

17:28  🟢 GREEN  keeps Processar off until the sermon has borders  ·
       2 passed

17:28  🔴 RED    launches the processing without force and follows its
       events
       clique → POST /process com {} (sem force); 202 abre o fluxo da tarefa 9
       passo 3 (b)
       expected { posts: [], streams: [] } to deeply equal { posts: [ {} ], … }

17:28  🟢 GREEN  launches the processing without force and follows its
       events  ·  3 passed

17:28  🔴 RED    shows the progress on the button as the events arrive
       progress muda o botão para "Processando 35%"
       passo 3 (c); spec "progresso aparece no botão"
       Unable to find … role "button" and name "Processando 35%"

17:28  🟢 GREEN  shows the progress on the button as the events arrive
       ·  4 passed

17:29  🔴 RED    reloads the sermon, now processed, when the task is done
       done → novo GET /api/sermons/12, que passa a processed (prévia <video>)
       passo 3 (c); L7 ("recarrega como processada")
       Unable to find a label with the text of: Prévia da pregação processada

17:29  🟢 GREEN  reloads the sermon, now processed, when the task is done
       ·  49 passed

17:29  🔴 RED    says why the processing failed and offers Processar again
       failed fecha o fluxo, mostra error.message e devolve Processar
       passo 3 (c); L9; 1.1.c.3
       Unable to find role="alert"

17:29  🟢 GREEN  says why the processing failed and offers Processar
       again  ·  50 passed
       o gancho guarda a tarefa com o id, para uma tarefa nova não herdar o
       progresso da anterior

17:30  🔴 RED    follows the task already running when the sermon opens
       pregação processing com last_task running abre o fluxo por
       last_task.id e mostra o progresso dela
       passo 3 (d); L9
       Unable to find … role "button" and name "Processando 35%"

17:30  🟢 GREEN  follows the task already running when the sermon opens
       ·  51 passed

17:30  🔴 RED    says what keeps the machine busy and launches nothing
       409 busy no POST mostra a mensagem da API; nenhum EventSource
       passo 3 (e); spec "Máquina ocupada: aviso com o que roda"
       Unable to find role="alert"

17:30  🟢 GREEN  says what keeps the machine busy and launches nothing
       ·  52 passed

17:30  🔴 RED    keeps Processar off while the machine works on another
       sermon, saying on what
       lock.held de outro recurso (GET /api/status) desabilita Processar com
       "Máquina ocupada: processando a pregação 7."
       passo 3 (e)
       Unable to find an element with the text: Máquina ocupada: processando a
       pregação 7.

17:30  🟢 GREEN  keeps Processar off while the machine works on another
       sermon  ·  118 passed (StatusBar exporta lockedWork; sem regressão)

17:31  🔴 RED    warns that the live may still be on, without locking
       Processar; locks Processar with the reason once the API says the live
       is on
       live_finished:false avisa sem travar; 409 live_not_finished trava com o
       motivo
       passo 3 (f); L4
       Unable to find an element with the text: /A live pode não ter terminado/
       expected [ …(2) ] to deeply equal [ …(2) ]

17:31  🟢 GREEN  live no ar: aviso e trava após o 409  ·  55 passed

17:34  🔴 RED    offers Reprocessar, warning that the cuts' edits are lost,
       once the borders change; reprocesses with force
       processada + PATCH 200 na sessão → Reprocessar com o aviso; o clique
       manda {"force": true}
       passo 3 (g); L3
       Unable to find role="button" and name "Reprocessar"

17:34  🟢 GREEN  Reprocessar  ·  57 passed

17:34  🧬 MUTAÇÃO force: false no Reprocessar  ·  vermelha
       expected [ {} ] to deeply equal [ { force: true } ]

17:34  🔧 REFACTOR ProcessButton com um só retorno para Processar e
       Reprocessar (Reprocessar também mostra "Máquina ocupada")

17:34  ⚠️ INSTÁVEL 3 de 9 rodadas da suíte vermelhas (seek perdido,
       player ainda não criado): a região aparecia antes do useEffect que
       cria o player
       expected [ 2478 ] to deeply equal [ 2124, 2478 ]

17:34  🔧 REFACTOR o player nasce no useLayoutEffect, junto com a tela
       10 rodadas seguidas da suíte verdes · 122 passed; typecheck, lint e
       build limpos

17:34  ✅ PASSO 3/4 — Processar/Reprocessar  ·  +18 testes  ·  suíte 122

17:36  🔎 MANUAL L12 — <video> da pregação processada, fora da suíte
       build de apps/web servido por um dublê local de /api (Node, 127.0.0.1,
       sem rede externa) que imita o FileResponse da API: video/mp4,
       Content-Disposition: attachment, Accept-Ranges e 206 com Range.
       Chromium headless (Playwright 1223) por CDP abriu /sermons/12
       processada (sermon_start 1800) com um clipe H.264 sintético de 10 s
       (ffmpeg testsrc); depois o mesmo com VP9.
       Resultado nos dois: <video src="/api/sermons/12/video">, readyState 4,
       duration 10, sem erro; currentTime = 6 → seeked em 6; o transporte
       mostrou 30:06 / 1:58:00 (tempo da live = 1800 + 6). Pedido com
       "Range: bytes=0-" (o clipe inteiro coube no buffer, então o seek não
       pediu outro trecho). O attachment não impede a reprodução.
       Limite: com arquivo longo, o seek depende de 206 parcial; o dublê o
       serve e o Starlette do FileResponse (1.7/1.10, uv.lock) também.
       Scripts e captura no scratchpad da sessão, fora do repositório.

--- Passo 4: Documentação ---

17:37  📝 DOCS   ADR-0023 (prévia da live pelo embed do YouTube; substitui a
       ADR-0022 só no ponto "nenhum recurso de outro host", sem editá-la) com
       entrada no índice; docs/architecture/README.md (C4 com a prévia no
       navegador, estado da web com features/sermon, PlayerLike e SSE, fluxo
       5.5); README; CHANGELOG; specs/roadmap.md com a pendência de API
       sem teste: só documentação

17:37  ✅ PASSO 4/4 — Documentação  ·  +0 testes  ·  suíte 122

17:37  🏁 VERIFICAÇÃO  npm test 122 passed (3 rodadas seguidas);
       typecheck, lint e build limpos; checkboxes da Verificação marcados
       sem commit (override do orquestrador)

## Rodada 1 · QA

17:38  📊 SUÍTE  apps/web 122 passed  ·  0 failed
       typecheck, lint e build limpos (build em diretório temporário);
       stderr com avisos de act() em ClipEdges.test.tsx, sem falha

17:39  📊 SUÍTE  regressão Python 1506 passed  ·  0 failed
       ruff check, ruff format --check e mypy limpos

17:44  🧬 MUTAÇÕES · cópia de apps/web fora do repositório  ·  23 de 28 mortas
       ☠️  PATCH no pointermove                          1 teste
       ☠️  mínimo 0                                      3 testes
       ☠️  "Salvo" antes da resposta                     4 testes
       ☠️  sem close() no done/failed                    2 testes
       ☠️  force false no Reprocessar                    1 teste
       ☠️  offset do <video> com sinal trocado           1 teste
       ☠️  erro do PATCH não devolve a borda             3 testes
       ☠️  editável em processing / Ctrl / campo texto   2 / 3 / 1
       ☠️  SSE sem close ao desmontar; sem reload        1 / 1
       ☠️  prévia sempre YouTube; YouTube do 0           3 / 4
       ☠️  live_not_finished não trava; live_finished
           trava; Reprocessar sem PATCH; falha oculta;
           tarefa em andamento ignorada                  1 a 2 cada
       ☠️  seek no arraste removido; cursor preso        1 / 1
       🚨  borda inicial abaixo de 0     SOBREVIVEU — equivalente: liveTimeAt
           já prende o ponteiro em [0, live]
       🚨  borda final além da live      SOBREVIVEU — equivalente, idem
       🚨  lock da própria pregação conta como ocupada
                                         SOBREVIVEU — fora da matriz 3(e)
       🚨  I/O não reinicia o debounce   SOBREVIVEU — salva 300 ms depois
           do O; o teste só conta um PATCH, não o momento (2c)
       🚨  sem mínimo de 1 min na borda final arrastada
                                         SOBREVIVEU — nenhum teste arrasta a
           borda final; 2(a) e 2(d) provados só para a inicial

17:45  🔎 QA     passo 1/4 — Player e timeline  ·  ✅ PASS
       (a)–(f) cobertos pela rota; conversão do <video> em teste unitário

17:45  🔎 QA     passo 2/4 — Bordas  ·  ⚠️ PARCIAL
       a borda final nunca é arrastada nos testes: mínimo de 1 min no
       arraste dela sem prova (mutante vivo); debounce sem prova de tempo

17:46  🔎 QA     passo 3/4 — Processar/Reprocessar  ·  ✅ PASS
       (a)–(h) cobertos; as duas mutações exigidas morrem

17:46  🔎 QA     passo 4/4 — Documentação  ·  ✅ PASS
       ADR-0023 registra L5+L6 (script só no nível 2 quando a prévia
       precisa da live); índice, arquitetura, README, CHANGELOG; ADR-0022
       intocada

17:47  🔎 QA     comentários (CONTRIBUTING §5)  ·  ✅ PASS com ressalva
       docstring de fakePlayers.ts:3 diz que ``play`` move o tempo; quem
       move é ``moveTo``

## Rodada 2 · implementador

17:48  🔁 REABERTO  passo 2/4 — Bordas (QA rodada 1: PARCIAL)
       falta arrastar a borda final (mínimo de 1 min) e provar o momento
       do salvamento por I/O (500 ms após a última tecla)

17:50  🔴 RED    stops the dragged end border a minute after the start
       arrastar a borda final para antes do início a para 1 min depois
       dele (1860 com início em 1800)
       spec · Processar: bordas ≥ 1 min; passo 2(a)(d)
       comportamento já existia: RED provado por mutação — sem o mínimo
       em ClipEdges.ts `moved` (ramo end) → × aria-valuenow ≠ 1860

17:50  🟢 GREEN  stops the dragged end border a minute after the start
       · 21 passed

17:51  🔴 RED    saves half a second after the last press, not the first
       I, 400 ms, I de novo, 400 ms: nenhum PATCH; mais 100 ms: um PATCH
       com a borda da segunda tecla
       passo 2(c), decisão L10 (debounce de 500 ms no teclado)
       comportamento já existia: RED provado por mutação — sem o
       clearTimeout (ClipEdges.ts:79) → × PATCH aos 500 ms; com
       `pendingSave.current ??= setTimeout(...)` → × idem

17:51  🟢 GREEN  saves half a second after the last press, not the first
       · 21 passed

17:52  ☠️  mutações exigidas pela rodada 2 (cópia restaurada, cmp ok)
       ☠️  sem mínimo de 1 min na borda final arrastada     morta
       ☠️  I/O sem clearTimeout (não reinicia o debounce)   morta
       ☠️  I/O agenda só se não há timer pendente (??=)     morta

17:53  🧹 REFACTOR  docstring de test/fakePlayers.ts: quem move o player
       é ``moveTo``, não ``play``

17:53  ✅ PASSO 2/4 — Bordas  ·  +2 testes  ·  suíte 124
       typecheck, lint e build limpos

## Rodada 2 · QA

17:52  📊 SUÍTE  124 passed  ·  0 failed
       typecheck, lint, build limpos; pytest 1506 passed; ruff ok

17:52  🧬 MUTAÇÕES · passo 2, cópia no scratchpad  ·  8 de 8 mortas
       ☠️  sem mínimo de 1 min na borda final arrastada        1 teste
       ☠️  I/O sem clearTimeout                                 1 teste
       ☠️  I/O com ??= setTimeout                               1 teste
       ☠️  debounce de 300 ms                                   1 teste
       ☠️  debounce de 700 ms                                   4 testes
       ☠️  mínimo 0                                             4 testes
       ☠️  PATCH no pointermove                                 1 teste
       ☠️  "Salvo" antes da resposta                            4 testes

17:53  🔎 QA     passo 2/4 — Bordas  ·  ✅ PASS
       arraste da borda final para no mínimo de 1 min; I/O salva 500 ms
       após a última tecla; docstring de fakePlayers.ts corrigida
