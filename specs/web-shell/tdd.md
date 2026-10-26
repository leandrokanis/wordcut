## Plano de QA

baseline_commit a052cd8ddb38006579fd758428c56591592c653b

16:27  📐 BARRA   cliente HTTP: sucesso, erro {"error"}, 401/403, API fora do ar
       Vitest com fetch dublê que responde 404 a URL não prevista; sem rede

16:27  🧬 EXIGE   response.ok trocado por true  ·  vermelha
       prova que um erro da API não passa como dado

16:27  📐 BARRA   rotas e caminho nos três níveis, títulos vindos da API
       MemoryRouter sobre a mesma tabela de rotas; asserções por papel

16:27  📐 BARRA   nível 1 e diálogo: corpo {"url"}, aviso de live, erro no campo
       userEvent + dublê que registra método, URL e corpo

16:27  🧬 EXIGE   ramo live_finished === false apagado  ·  vermelha
       prova que o aviso de 1.1.a.2 depende do dado da API

16:27  📐 BARRA   barra de status atualiza sozinha e para ao desmontar
       fake timers: 3 s → nova chamada; unmount → nenhuma

16:27  🧬 EXIGE   clearInterval removido  ·  vermelha
       sem ele, o polling vaza entre telas

16:27  📐 BARRA   configurações só para admin; 401/403 sem dados
       GET /api/me dublê nos dois papéis e nos dois erros

16:27  ⚠️ LACUNA  papel do usuário: o plano não diz de onde vem
       sem GET /api/me (item 19), o passo 4 (f) fica PARCIAL

16:27  ⚠️ LACUNA  link inválido sai com details.argument "link", não "url"
       erro associado só a "url" não aparece junto ao campo

16:27  ⚠️ LACUNA  POST /api/sermons não traz duration; lista traz null
       antes das bordas
       sem tipos separados, a duração some ou quebra o typecheck

16:27  ⚠️ LACUNA  FR-004 pede eventos (SSE); o plano só faz polling
       sem registrar o adiamento para o item 22, FR-004 fica descoberto

16:27  ⚠️ LACUNA  indicador "Salvo" (FR-005) sem passo nem teste
       sem teste próprio, FR-005 fica descoberto

16:27  ⚠️ LACUNA  390 px não se mede em jsdom
       sem verificação manual registrada, o critério fica PARCIAL

## Rodada 1 · implementador

16:32  ▶ PASSOS  1 a 5 do plan.md; decisões L1 a L20 registradas no plano

16:32  🔴 RED    client > returns the body the API sends on success
       listSermons devolve os itens que GET /api/sermons manda
       Passo 1 (a); FR-003
       Failed to resolve import "./client" from "src/api/client.test.ts"

16:32  🟢 GREEN  client > returns the body the API sends on success  ·  1 passed

16:33  🔴 RED    client > turns an error body into an error with its
       status, code, message and details
       resposta não-2xx com {"error"} vira ApiError com o objeto da API
       Passo 1 (b); docs/api.md §1
       TypeError: (0 , createSermon) is not a function

16:33  🟢 GREEN  client > turns an error body into an error with its
       status, code, message and details  ·  2 passed

16:33  🔴 RED    client > reports a body that is not the API's JSON as
       the API being unavailable
       502 HTML do nginx vira ApiError "unavailable", nunca exceção crua
       Passo 1 (c); L10; borda "API fora do ar"
       SyntaxError: Unexpected token '<', "<html>502 "... is not valid JSON

16:33  🔴 RED    client > reports a request that never reached the API as
       a network error
       fetch rejeitado vira ApiError "network_error"
       Passo 1 (c); L10
       expected the call to fail (TypeError: Failed to fetch escapou cru)

16:33  🟢 GREEN  client > unavailable + network error  ·  4 passed

16:33  🔴 RED    client > reads who is calling from GET /api/me
       o papel vem de GET /api/me, sem o "Ver como" do protótipo
       Passo 1 (f); L5
       TypeError: (0 , getMe) is not a function

16:33  🟢 GREEN  client > reads who is calling from GET /api/me  ·  5 passed

16:34  ⚪ PASSA  client > tells a 401/403 from the other identity failure
       by its code  ·  7 passed
       caracterização exigida pela matriz (Passo 1 d); já coberta pelo
       ramo de erro da fatia (b), sem produção nova

16:34  🔴 RED    client > posts the link as JSON with only the url field
       POST envia Content-Type JSON e corpo exatamente {"url"} (ADR-0021)
       Passo 1 (e); FR-003
       AssertionError: expected [ null, …(1) ] to deeply equal
       [ 'application/json', …(1) ]

16:34  🟢 GREEN  client > posts the link as JSON with only the url field
       ·  8 passed

16:34  ✅ PASSO 1/5 — Cliente e tipos  ·  +8 testes  ·  suíte 10

16:34  🔴 RED    routes > shows only Pregações, as the current level, on
       the sermon list
       em /, o caminho tem só "Pregações", com aria-current
       Passo 2 (a)(b); FR-001, FR-002; cenário "lista de pregações"
       Failed to resolve import "../app/routes"

16:35  🟢 GREEN  routes > shows only Pregações, as the current level  ·  1 passed

16:35  🔴 RED    routes > shows the sermon's title from the API after
       Pregações inside a sermon
       em /sermons/:id, "Pregações / <título>" com o título de GET
       /api/sermons/{id}; "Pregações" é link para /
       Passo 2 (b); FR-002; L16
       Unable to find an accessible element with the role "navigation"
       and name "Caminho" (rota inexistente)

16:35  🟢 GREEN  routes > shows the sermon's title … inside a sermon  ·  2 passed

16:35  🔴 RED    routes > shows the sermon and the cut after Pregações
       inside a cut
       em /cuts/:id, "Pregações / <pregação> / <corte>" via GET
       /api/cuts/{id} → sermon_id → GET /api/sermons/{sermon_id}
       Passo 2 (a)(b); FR-001, FR-002; L16
       Unable to find role "navigation" "Caminho" (rota /cuts/:id ausente)

16:36  🟢 GREEN  routes > shows the sermon and the cut … inside a cut  ·  3 passed

16:37  🔴 RED    routes > goes back to the sermon / to the sermon list by
       clicking the path
       clicar num item anterior do caminho leva ao nível dele
       Passo 2 (c); FR-002; cenário "navegação pelo caminho"
       AssertionError: expected '/cuts/34' to be '/sermons/12' — o data
       router (createMemoryRouter) cria Request com o AbortSignal do jsdom,
       e o Request do Node recusa: "RequestInit: Expected signal … to be an
       instance of AbortSignal"; a navegação não acontece no teste

16:37  🔧 DECISÃO roteamento passa a BrowserRouter + useRoutes(routes)
       (sem data router; nenhum loader é usado). Registrado em Decisões
       técnicas do plan.md. Os testes usam MemoryRouter sobre a mesma tabela

16:37  🟢 GREEN  routes > navegação pelo caminho, item atual sem link,
       pregação 404 com o caminho intacto  ·  7 passed

16:37  🔴 RED    routes > opens the settings as a screen of their own,
       without the path
       /settings é tela inteira, fora do caminho de níveis
       Passo 2 (a); FR-001; cenário "configurações"
       Unable to find role="heading" and name "Configurações"

16:37  🟢 GREEN  routes > opens the settings as a screen of their own  ·  8 passed

16:39  🔴 RED    tokens > declares the prototype's colours and fonts with
       the same values; loads nothing from another host
       tokens.css repete o :root do protótipo (cores, fontes, --r,
       color-scheme dark); index.html e CSS sem URL externa
       Passo 2 (e)(f); FR-006; L18
       Failed to resolve import "./app.css?raw"; depois "Denied ID
       …/wordcut.html?raw" (fs.allow) e ?raw de CSS vazio (css: false)

16:39  🟢 GREEN  tokens > 2 testes  ·  2 passed
       vite.config: fs.allow com a pasta do protótipo; test.css: true

16:39  🔴 RED    Saved > announces Salvo politely each time something is
       saved, then hides it; stays quiet before anything is saved
       indicador reutilizável: role=status, aria-live=polite, some em 1,5 s
       Passo 2; FR-005; L12
       Failed to resolve import "./Saved"

16:39  🟢 GREEN  Saved > 2 testes  ·  2 passed

16:39  🧹 L11    src/api.ts e App.test.tsx removidos; App passa a
       BrowserRouter + AppRoutes; main.tsx carrega Geist e Geist Mono do
       npm (@fontsource/geist, @fontsource/geist-mono), tokens.css e app.css

16:39  ✅ PASSO 2/5 — Layout e rotas  ·  +12 testes  ·  suíte 20
       (d) barra de status em todas as rotas fica no passo 4, com a barra;
       (g) 390 px medido no fim, com a tela completa

16:40  🔴 RED    SermonList > lists each sermon in the API's order …;
       opens a sermon from its item
       um item por pregação, na ordem da API: data DD/MM/AAAA, título,
       estado em português, duração; o item abre /sermons/:id
       Passo 3 (a); FR-003; cenário "lista de pregações"; L19
       Unable to find role="listitem"

16:40  🟢 GREEN  SermonList > lista na ordem da API; item abre a pregação  ·  2 passed

16:41  🔴 RED    SermonList > duração a delimitar; estado vazio com
       "Nova pregação"; API fora do ar com mensagem; sem "Nova pregação"
       fora do nível 1
       Passo 3 (a)(b)(c)(i); L1; bordas "lista vazia" e "API fora do ar"
       toHaveTextContent "Duração a delimitar" falhou; Unable to find
       text "Nenhuma pregação ainda."; Unable to find role="alert"
       (rótulos de estado e ausência fora do nível 1 já passavam)

16:41  🟢 GREEN  SermonList > 13 passed

16:41  🔴 RED    NewSermonDialog > opens a modal dialog with the focus on
       the link field
       "Nova pregação" abre role=dialog, aria-modal, foco no campo rotulado
       Passo 3 (d); FR-003; cenário "Nova pregação"
       Unable to find role "dialog" and name "Nova pregação"

16:41  🟢 GREEN  NewSermonDialog > opens a modal dialog …  ·  14 passed
       a ação do topo só aparece com a lista carregada, para não trocar de
       botão sob o clique quando a lista chega vazia

16:42  🔴 RED    NewSermonDialog > closes with the close button / Esc
       o diálogo fecha por "Fechar" e por Esc, como no protótipo
       Passo 3 (d)
       Unable to find role "button" and name "Fechar"

16:42  🟢 GREEN  NewSermonDialog > closes with the close button / Esc  ·  3 passed

16:42  🔴 RED    NewSermonDialog > envio do link (8 testes): corpo só
       {"url"}; pregação na lista com título, data e duração da live;
       aviso de live no ar sem recusar; motivo junto ao campo (400 link,
       502 youtube_error); sem repetir o link; created:false sem duplicar;
       sem POST duplo
       Passo 3 (e)(f)(g)(h)(j); L1, L2, L3, L4, L14, L15; ADR-0015
       expected <div class="modal" …> to be null; Unable to find
       role="status"; Unable to find text "Link inválido."

16:43  🟢 GREEN  NewSermonDialog > 11 passed

16:43  ✅ PASSO 3/5 — Nível 1  ·  +24 testes  ·  suíte 44
       "Processando N%" ganha o progresso no passo 4, com /api/status

16:43  🔴 RED    StatusBar > says the machine is free when nobody holds
       the lock
       lock.held false → "Máquina livre" no rodapé
       Passo 4 (a); FR-004; cenário "barra de status"
       Failed to resolve import "./MachineStatus"

16:43  🟢 GREEN  StatusBar > says the machine is free …  ·  1 passed

16:44  🔴 RED    StatusBar > says what holds the machine, for how long
       and how far it got; keeps the machine free while only a suggestion
       runs
       lock.held → "Ocupada: <tarefa> · há N min" e o progresso da tarefa
       lock.task_id; suggest sem trava não marca a máquina ocupada
       Passo 4 (a); FR-004; L7
       toHaveTextContent falhou ("Máquina livre" fixo)

16:44  🟢 GREEN  StatusBar > ocupada com progresso; sugestão sem trava  ·  3 passed

16:44  🔴 RED    StatusBar > updates by itself every 3 seconds; says the
       status is unavailable while the API is down and recovers after
       polling de 3 s; falha mostra "indisponível" e o polling continua
       Passo 4 (b)(d); FR-004; L8, L9
       toHaveTextContent /^Ocupada/ falhou; Unable to find text "Estado
       da máquina indisponível" ("stops asking" já passava sem intervalo;
       ele vale contra a mutação do clearInterval)

16:44  🟢 GREEN  StatusBar > polling, parada ao desmontar, indisponível  ·  6 passed

16:45  🔴 RED    Identity > explains a 401/403 on GET /api/me without
       loading any sermon
       sem identidade ou fora da equipe: tela própria, nenhum dado pedido
       Passo 4 (g); L5, L6; borda "401 / 403"
       Unable to find role="heading" and name "Você não está identificado."

16:45  🟢 GREEN  Identity > 401/403 sem dados  ·  suíte 52 passed
       Shell = IdentityGate + MachineStatusProvider + StatusBar; testes de
       rota passam a esperar o caminho depois de GET /api/me

16:45  🔴 RED    Identity > offers Configurações to an administrator
       admin vê a entrada "Configurações" no topo; assistente não
       Passo 4 (f); L5; cenário "configurações"
       Unable to find role="link" and name "Configurações"
       (API fora do ar em /api/me, rodapé em todas as rotas e ausência
       para o assistente já passavam com o Shell)

16:45  🟢 GREEN  Identity > 9 passed

16:46  🔴 RED    SettingsPage > navigation of its own for the
       administrator; refused to an assistant who opens it directly
       tela inteira com navegação lateral e seções vazias; a rota recusa
       o assistente, não só esconde a entrada
       Passo 4 (e)(f); L5; cenário "configurações"
       Unable to find role="navigation" and name "Seções das configurações"

16:46  🟢 GREEN  SettingsPage > 2 passed  ·  suíte 61

16:46  🔴 RED    SermonList > shows how far a sermon being processed got,
       from the machine status
       "Processando N%" com o progresso da tarefa process da pregação
       Passo 3/4; L19
       Unable to find text "Processando 42%"

16:47  🟢 GREEN  SermonList > Processando N%  ·  suíte 62 passed

16:47  🧬 MUTAÇÃO  cobradas pela matriz, uma por vez, arquivo restaurado:
       response.ok → true: 9 vermelhos · message fixa: 3 · sem catch do
       fetch: 1 · "Pregações" com to="#": 2 · ramo live_finished
       apagado: 1 · erro fora do campo: 2 · created_at no lugar de
       service_date: 1 · campo extra no POST: 2 · sem clearInterval: 1
       · role invertido: 2 · filhos antes de /api/me: 44
       setInterval(…, Infinity) SOBREVIVEU (o navegador e os fake timers
       tratam Infinity como 1 ms; o teste de 3 s ainda passava)

16:47  🔴 RED    StatusBar > waits the 3 seconds before asking again
       (sob a mutação Infinity) nenhuma nova consulta antes de 3 s
       Passo 4 (b); mutação 🧬 do intervalo
       sob o mutante: Tests 1 failed | 6 passed (toHaveLength(1))

16:47  🟢 GREEN  StatusBar > waits the 3 seconds before asking again
       ·  7 passed; mutação Infinity agora vermelha (1 falha)

16:47  ✅ PASSO 4/5 — Barra de status e configurações vazias
       ·  +18 testes  ·  suíte 63

16:48  📏 390 px  verificado em Chromium sem interface (playwright-core de
       outro projeto local, só como biblioteca), sobre o
       build servido por vite preview em 127.0.0.1, viewport 390×844, com
       /api/* respondido pelo próprio script (nenhuma chamada externa;
       pedidos a outro host abortados). scrollWidth = clientWidth = 390 em
       /, /sermons/12, /cuts/34, /settings e com o diálogo aberto; títulos
       longos na lista e no caminho. A fonte carregada é a Geist do build
       (document.fonts.check '14px "Geist"' = true). Ajuste visual: o
       primeiro item do caminho não encolhe

16:51  📝 DOCS   ADR-0022 "Arquitetura do cliente web" (React Router
       declarativo, cliente HTTP próprio, identidade antes das telas,
       polling de status, CSS com tokens do protótipo, Geist pelo npm);
       índice docs/adr/README.md; README; docs/architecture §4 linha Web;
       CHANGELOG [Não lançado] (Adicionado e Alterado)

16:51  ✅ PASSO 5/5 — Documentação  ·  +0 testes  ·  suíte 63

16:51  🏁 VERIFICAÇÃO  web: 63 passed, typecheck, lint e build limpos;
       Python: pytest 1506 passed, ruff check e format, mypy limpos;
       git diff a052cd8 -- packages apps/api apps/cli vazio. Sem commit
       (override do orquestrador)

## Rodada 1 · QA

16:52  📊 SUÍTE  web 63 passed  ·  0 failed
       typecheck, lint e build limpos; Python 1506 passed, ruff check,
       ruff format --check e mypy limpos; diff do servidor vazio

16:53  🔎 QA     passo 1/5 — Cliente e tipos  ·  ✅ PASS
       (a)–(f) em client.test.ts; tipos de (g) no typecheck

16:53  🔎 QA     passo 2/5 — Layout e rotas  ·  ✅ PASS
       App e testes montam a mesma tabela (AppRoutes); 390 px medido de
       novo pelo QA

16:53  🔎 QA     passo 3/5 — Nível 1  ·  ⚠️ PARCIAL
       (j) sem prova: o teste do duplo clique passa sem o disabled e sem
       a guarda sending

16:53  🔎 QA     passo 4/5 — Barra de status e configurações  ·  ✅ PASS
       mutações cobradas vermelhas

16:53  🔎 QA     passo 5/5 — Documentação  ·  ✅ PASS
       §4, CHANGELOG, ADR-0022 com índice e README coerentes com o código

16:57  🧬 MUTAÇÕES · cópia no scratchpad, uma por vez  ·  33 de 36 mortas
       ☠️  response.ok → true                               9 testes
       ☠️  message fixa · sem catch · sem Content-Type   3 · 1 · 1
       ☠️  "Pregações" to="#" · item atual como link        2 · 3
       ☠️  live_finished apagado · erro fora do campo       1 · 2
       ☠️  created_at · campo extra no POST · sem reload  1 · 2 · 1
       ☠️  Infinity · sem setInterval · sem clearInterval 1 · 2 · 1
       ☠️  role invertido (topo, /settings) · filhos antes  2 · 2 · 3
       🚨  disabled={!url.trim()} no "Carregar"   SOBREVIVEU — 3(j)
       🚨  sem a guarda if (sending)              SOBREVIVEU — 3(j)
       🚨  sem as duas proteções juntas           SOBREVIVEU — o dublê
           responde antes do 2º clique e o diálogo já fechou: o teste
           não chega a ver o envio em curso

16:58  📏 390 px  Chromium sem interface (playwright-core já instalado, só
       biblioteca) sobre vite preview em 127.0.0.1:4318; /api pelo dublê
       do script; nenhum pedido externo. scrollWidth = clientWidth = 390
       em /, /sermons/12, /cuts/34, /settings e com o diálogo; Geist
       carregada. Servidor encerrado

16:59  ⚠️ LACUNA  shot-*.png (5 arquivos) soltos na raiz do repo, da
       medição do implementador; não entram no commit

## Rodada 2 · implementador

17:00  🔁 REABERTO  passo 3 (j) — PARCIAL na rodada 1: o dublê respondia
       antes do 2º clique, e as três mutações sobreviviam

17:00  🧪 DUBLÊ  fakeApi aceita rota que responde com promessa, para
       segurar o POST até o teste soltar

17:01  🔴 RED    disables Carregar while the link is on its way
       com o POST segurado, "Carregar" fica desabilitado
       passo 3 (j) da barra; mutação disabled={!url.trim()}
       × expected element to be disabled  ·  1 failed | 12 passed

17:01  🔴 RED    sends the link once however many times it is confirmed
       com o POST segurado, 2º clique, Enter e submit do form não
       geram outro POST
       passo 3 (j) da barra; mutação sem a guarda if (sending)
       × expected [ …(2) ] to have a length of 1  ·  1 failed | 12 passed

17:01  🔴 RED    follows the normal flow once the held reply arrives
       solto o POST, o diálogo fecha e a pregação aparece na lista,
       com um único POST
       passo 3 (j) da barra; mutação sem as duas proteções
       × 3 failed | 10 passed (as três novas)

17:01  🟢 GREEN  NewSermonDialog.test.tsx (produção restaurada)
       ·  13 passed

17:02  🧬 MUTAÇÕES  passo 3 (j) · uma por vez, arquivo restaurado
       ☠️  disabled={!url.trim()}           1 teste
       ☠️  sem a guarda if (sending)        1 teste
       ☠️  sem as duas proteções            3 testes
       ⚠️  a guarda só é alcançável fora do botão: com o botão
           desabilitado, clique e Enter não submetem (jsdom e
           navegador); o teste a exerce com submit direto no form

17:02  ✅ PASSO 3/5 — Nível 1 (j)  ·  +2 testes  ·  suíte 65
       typecheck, lint e build limpos

## Rodada 2 · QA

17:04  📊 SUÍTE  web 65 passed  ·  0 failed; typecheck, lint e build
       limpos; pytest 1506 passed; ruff e mypy limpos; diff do
       servidor desde a052cd8 vazio

17:04  🧬 MUTAÇÕES · passo 3 (j), cópia no scratchpad  ·  5 de 5 mortas
       ☠️  disabled={!url.trim()}                          1 teste
       ☠️  sem a guarda if (sending)                       1 teste
       ☠️  sem as duas proteções juntas                    3 testes
       ☠️  setSending(true) removido                       3 testes
       ☠️  botão sempre desabilitado                       8 testes

17:04  🔎 QA     passo 3/5 — Nível 1  ·  ✅ PASS
       (j) provado com o POST segurado: botão desabilitado, um único
       POST; a guarda é exercida por submit direto (aceito)

17:04  🔎 QA     raiz do repositório sem arquivo solto novo; os
       shot-*.png da rodada 1 foram removidos
