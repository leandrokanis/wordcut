## Plano de QA

baseline_commit: 0d6b5daf71007398c871e61857908f3428cda353

20:00  📐 BARRA   segredos nunca voltam: só máscara/presença, campo limpo
       componente + fakeApi com valor fictício; DOM e console sem ele

20:00  📐 BARRA   níveis por critério com PATCH só do critério mudado
       LevelControl por tabela + corpo exato do PATCH

20:00  📐 BARRA   valor inválido não salva e mostra motivo junto ao campo
       apiError 400/409 por rota; "Salvo" ausente após erro

20:00  📐 BARRA   rolagem contínua com menu que pula e acompanha
       dublê de IntersectionObserver + scrollIntoView stub

20:00  🧬 EXIGE   renderizar o valor enviado em vez da máscara  ·  vermelha
       prova que a chave nunca aparece de volta

20:00  🧬 EXIGE   e-mail no caminho do set-role/remove  ·  vermelha
       prova ADR-0021 (e-mail só no corpo)

20:00  🧬 EXIGE   gravação pendente perdida na troca de preset  ·  vermelha
       prova o flush do debounce

20:00  ⚠️ LACUNA  seções do plan ≠ menu do item 21 (7 links do protótipo)
       sem decidir, Passo 1 fica PARCIAL; seguir o protótipo (L1)

20:00  ⚠️ LACUNA  plan não trata 409 config_not_writable nem cookies
       sem isso, Passo 2 fica PARCIAL (L5)

20:00  ⚠️ LACUNA  client.ts/types.ts fora do Contexto; SettingRow já existe
       FormRow novo duplicaria; extrair (L2)

## Rodada 1 · implementador

20:04  🔴 RED    gives the administrator a navigation of its own over the prototype's sections
       menu com as seis seções do protótipo, sem Processamentos; uma h2 por link
       L1; spec Navegação; teste do item 21 ajustado explicitamente
       expected [ 'Voltar às pregações', …(7) ] to deeply equal [ …(6) ]

20:05  🟢 GREEN  gives the administrator a navigation … / lays every section out …  ·  3 passed

20:05  🔴 RED    jumps to the section a menu entry names and marks only that entry
       clicar num link rola até a seção dele e só esse link fica aria-current
       spec Navegação; QA Passo 1 (b)
       AssertionError: expected [ [], [] ] to deeply equal [ …(2) ]

20:05  🟢 GREEN  jumps to the section a menu entry names and marks only that entry  ·  4 passed

20:05  🔴 RED    follows the scroll: the menu marks the first section in the reading band
       o observador avisa as seções na faixa de leitura; vale a primeira na ordem
       spec Navegação; QA Passo 1 (c); L10
       AssertionError: expected [ [], [] ] to deeply equal [ [ 'Filtros' ], [ 'Valor' ] ]

20:05  🟢 GREEN  follows the scroll: the menu marks the first section in the reading band  ·  5 passed

20:06  🔴 RED    marks the last section once the scroll reaches the bottom, short as it may be
       no fim da rolagem a última seção é a atual, mesmo curta demais para a faixa
       L10; protótipo spyScroll (atEnd); QA Passo 1 (c)
       AssertionError: expected [ 'Formato' ] to deeply equal [ 'Pessoas' ]

20:06  🟢 GREEN  marks the last section once the scroll reaches the bottom …  ·  6 passed

20:06  🔴 RED    stops watching the scroll when the settings close
       ao sair da tela os observadores são desconectados (mutação 9)
       QA Passo 1 (c); mutação 9
       passou de primeira (disconnect já veio no GREEN anterior); RED provado
       pela mutação sem band.disconnect(): expected [ false, true ] to deeply
       equal [ true, true ]

20:06  🟢 GREEN  stops watching the scroll when the settings close  ·  7 passed

20:06  🔴 RED    names the control by the row's label and describes it beside
       a linha do formulário dá ao controle o nome do rótulo, descrição ao lado
       L2; QA Passo 1 (d)
       Failed to resolve import "./FormRow" from "src/ui/FormRow.test.tsx"

20:07  🟢 GREEN  names the control by the row's label and describes it beside  ·  20 passed
       ExportDialog passou a usar FormRow; SettingRow removido (sem duplicação)

20:08  ✅ PASSO 1/5 — Estrutura (parcial: (e)(f) e "Salvo" único seguem com as seções)

20:08  --- Passo 2: Modelo e segredos ---

20:08  🔴 RED    shows the models, the key only masked and whether the cookies are there
       GET /api/settings vira os campos de modelo, a máscara e a presença dos cookies
       spec Modelos e segredos; QA Passo 2 (a)
       Unable to find role="textbox" and name "Modelo"

20:09  🟢 GREEN  shows the models, the key only masked and whether the cookies are there  ·  298 passed
       test-setup ganhou um IntersectionObserver inerte (jsdom não tem); telas de
       outros testes que abrem /settings voltaram a renderizar

20:10  🔴 RED    shows the API's reason where a section could not load, keeping the others
       erro de carga numa seção mostra a mensagem da API ali; as outras seguem
       QA Passo 1 (f)
       Unable to find role="alert"

20:10  🟢 GREEN  shows the API's reason where a section could not load …  ·  10 passed
       asks the API nothing of the administrator's for an assistant: passou de
       primeira (o gate já existia); RED provado pela mutação 11 (seção montada
       para o assistente)

20:10  🔴 RED    saves a changed model once it is confirmed with Enter, and says Salvo
       Enter no Modelo manda um PATCH só com llm_model e o Salvo único aparece
       spec mudar o modelo salva sozinho; L6; L11; QA Passo 2 (b)
       Unable to find an element with the text: Salvo.

20:11  🟢 GREEN  saves a changed model once it is confirmed with Enter, and says Salvo  ·  11 passed

20:11  ✅ PASSO 1/5 — Estrutura  ·  +9 testes  ·  suíte 300

20:11  nota: a suíte do fechamento do Passo 1 é 301 (+10 testes), não 300

20:11  🔴 RED    keeps a blank model unsaved, with the API's reason beside the field and no Salvo
       branco → 400 → motivo ligado ao campo por aria-describedby, sem Salvo
       spec borda Valor inválido; FR-002; mutação 5
       passou de primeira (CommitInput do ciclo anterior já tratava o erro);
       RED provado pela mutação 5 (onSaved no finally)

20:11  🔴 RED    leaves an unchanged model alone when the field loses focus
       sair do campo sem mudança não grava
       L6; QA Passo 2 (b)
       passou de primeira; RED provado pela mutação sem a guarda draft === value

20:11  🟢 GREEN  keeps a blank model unsaved … / leaves an unchanged model alone …  ·  4 passed

20:12  🔴 RED    sends a pasted key with Enter and shows only the mask the API answers
       Enter manda PUT {value} exato, limpa o campo e mostra só a máscara da resposta;
       a chave fictícia nunca no DOM nem no console
       spec chave mostra só •••• + 4; FR-002; mutações 1 e 2; QA Passo 2 (c)
       Unable to find a label with the text of: Nova chave

20:12  🟢 GREEN  sends a pasted key with Enter and shows only the mask the API answers  ·  5 passed
       mutações 1 (campo não limpo) e 2 (valor no lugar da máscara) deixam o teste vermelho

20:12  🔴 RED    sends no key when Enter finds the field blank
       Enter com o campo em branco não envia nada
       QA Passo 2 (c) (vazio não envia)
       passou de primeira; RED provado pela mutação sem a guarda de branco

20:12  🔴 RED    explains how to store the key on the host when the API cannot write it
       409 config_not_writable: mensagem da API + comando da CLI no host; campo
       limpo; máscara inalterada; chave fora do DOM
       L5; docs/api.md §2; QA Passo 2 (e)
       AssertionError: expected [ …(4) ] to deeply equal [ …(4) ] (sem a orientação)

20:12  🟢 GREEN  explains how to store the key on the host when the API cannot write it  ·  7 passed

20:13  🔴 RED    sends the chosen cookies file as it is and then only says they are there
       escolher o arquivo manda PUT {value} com o conteúdo inteiro; depois só
       "Presentes"; o conteúdo fictício nunca no DOM; seletor limpo
       L5; spec cookies mostram presentes; FR-004; QA Passo 2 (d)
       Unable to find a label with the text of: Arquivo de cookies

20:13  🟢 GREEN  sends the chosen cookies file as it is and then only says they are there  ·  8 passed
       leitura por FileReader (jsdom não tem Blob.text())

20:14  🔴 RED    tells why the cookies were refused, keeping them absent and unseen (×2)
       400 fora do formato e 409 config_not_writable: motivo junto ao campo,
       orientação set-cookies no host, presença inalterada, conteúdo fora do DOM
       L5; QA Passo 2 (e)
       passou de primeira (CookiesForm já tratava o erro); RED provado pela
       mutação sem a mensagem de erro dos cookies

20:14  🟢 GREEN  tells why the cookies were refused … (×2)  ·  10 passed

20:14  ✅ PASSO 2/5 — Modelo e segredos  ·  +10 testes  ·  suíte 309

20:14  --- Passo 3: Presets ---

20:14  🔴 RED    presses %s for the level %s / picks %s as %s (×3 cada)
       Brando/Moderado/Rigoroso ↔ lenient/moderate/strict nos dois sentidos
       L4; spec níveis por critério; mutação 3; QA Passo 3 (b)
       Failed to resolve import "./LevelControl"

20:15  🟢 GREEN  presses … / picks … (×3 cada)  ·  6 passed
       mutação 3 (Brando → strict) deixa 4 vermelhos

20:15  🔴 RED    opens on the default preset … / shows the chosen preset in every preset section
       seletor com "· padrão" no padrão, selecionado de início; trocar o preset
       troca Presets, Filtros e Formato
       spec Presets: escolher preset; QA Passo 3 (a)
       Unable to find role="combobox" and name "Preset"

20:15  🟢 GREEN  opens on the default preset … / shows the chosen preset in every preset section  ·  27 passed

20:16  🔴 RED    saves only the level picked for one criterion, and says Salvo
       clicar Rigoroso na Alegoria → PATCH {levels: {allegory: strict}} exato; Salvo
       spec níveis por critério; mutação 4; QA Passo 3 (b)
       Unable to find an element with the text: Salvo.

20:16  🟢 GREEN  saves only the level picked for one criterion, and says Salvo  ·  3 passed
       usePresetDrafts: rascunho e erro por preset e chave; mutação 4 (todos os
       critérios no PATCH) deixa o teste vermelho

20:17  🔴 RED    shows each criterion only by its name, even if a prompt text came along
       fixture com campo text espúrio: só o nome do critério na tela
       spec borda O texto dos critérios nunca aparece; QA Passo 3 (c)
       passou de primeira (LevelControl só usa name); RED provado pela mutação
       que mostra o text como descrição

20:17  🟢 GREEN  shows each criterion only by its name …  ·  4 passed

20:17  🔴 RED    saves the additional instructions once, 400 ms after the last key
       várias teclas → nenhum PATCH em 399 ms; um PATCH com o último valor em 400
       spec instruções com autosave; L7; QA Passo 3 (e)
       Unable to find … role "textbox" and name "Instruções adicionais"

20:17  🟢 GREEN  saves the additional instructions once, 400 ms after the last key  ·  5 passed
       teclas simuladas com fireEvent.change e relógio falso, como CaptionTab.test

20:18  🔴 RED    saves a duration range as whole seconds once the typing pauses
       máximo da duração ideal 70 → após 400 ms PATCH {duration_ideal: {min, max}}
       spec formato com autosave; QA Passo 3 (d)
       Unable to find … role "spinbutton" and name "Duração ideal, máximo"

20:18  🟢 GREEN  saves a duration range as whole seconds once the typing pauses  ·  6 passed

20:18  🔴 RED    keeps a refused duration on screen with the API's reason, and no Salvo
       ideal fora da permitida → 400 → motivo no Formato, valor fica, sem Salvo
       spec borda Valor inválido; QA Passo 3 (d)
       passou de primeira (usePresetDrafts já guardava o erro); RED provado pela
       mutação que descarta a mensagem do erro

20:18  🟢 GREEN  keeps a refused duration on screen …  ·  7 passed

20:18  🔴 RED    saves Permitir reordenar as soon as it is picked / saves the protected words as a trimmed list, without empty ones
       Não → PATCH {reorder: false} na hora; "a, b ,c,, " → [a, b, c] após 400 ms
       spec reordenar e palavras protegidas; QA Passo 3 (d)
       Unable to find … text: Salvo / … textbox "Palavras protegidas"

20:19  🟢 GREEN  saves Permitir reordenar … / saves the protected words …  ·  9 passed

20:19  🔴 RED    renames the preset with Enter, in the picker too / keeps a repeated name unsaved, with the API's reason beside it
       nome por Enter → PATCH {name}; o seletor mostra o novo; repetido → 400 junto ao campo
       spec renomear; L6; QA Passo 3 (e)
       clear() is only supported on editable elements (campo só de leitura)

20:19  🟢 GREEN  renames the preset with Enter … / keeps a repeated name unsaved …  ·  11 passed

20:19  🔴 RED    saves a waiting change on its own preset before showing another
       trocar de preset com instrução pendente grava na hora, no preset 1
       L7; mutação 10; QA Passo 3 (f)
       expected [ [], [ [ …(2) ] ] ] to deeply equal [ [ [ …(2) ] ], [ [ …(2) ] ] ]

20:19  🟢 GREEN  saves a waiting change on its own preset before showing another  ·  12 passed

20:20  🔴 RED    duplicates the shown preset as Cópia de <nome> and shows the copy
       Duplicar → POST {name: "Cópia de Padrão", from_id: 1}; a cópia fica selecionada
       L8; spec criar; QA Passo 3 (g)
       Unable to find … role "button" and name "Duplicar"

20:20  🟢 GREEN  duplicates the shown preset as Cópia de <nome> and shows the copy  ·  13 passed

20:20  🔴 RED    makes the shown preset the default, moving the mark from the old one
       Tornar padrão → POST set-default; chip "Preset padrão" e "· padrão" mudam de preset
       spec definir padrão; QA Passo 3 (h)
       Unable to find … role "button" and name "Tornar padrão"

20:20  🟢 GREEN  makes the shown preset the default …  ·  14 passed

20:20  🔴 RED    keeps the default preset from being deleted / deletes another preset … / keeps a preset the API refused to delete …
       Apagar desabilitado no padrão; em outro, DELETE, some e volta ao padrão;
       409 default_preset → motivo, nada some, sem Salvo
       spec apagar (menos o padrão); mutação 6; QA Passo 3 (i)
       Unable to find … role "button" and name "Apagar" (×3)

20:21  🟢 GREEN  keeps the default preset from being deleted / deletes another … / keeps a preset the API refused …  ·  17 passed
       mutação 6 (Apagar habilitado no padrão) deixa o primeiro vermelho

20:21  🔴 RED    tells why a copy could not be made, adding nothing
       Duplicar com nome repetido → 400 → motivo junto, lista igual
       L8; QA Passo 3 (g)
       passou de primeira (mesmo runAction do 409 de Apagar, provado acima)

20:21  🟢 GREEN  tells why a copy could not be made, adding nothing  ·  18 passed
       mutação 10 (sem flush na troca) deixa o teste do flush vermelho;
       fixture Curtos com níveis próprios para provar a troca também em Valor

20:21  ✅ PASSO 3/5 — Presets  ·  +24 testes  ·  suíte 333

20:21  --- Passo 4: Equipe ---

20:22  🔴 RED    lists the team by e-mail, each with its role and a way out
       cada membro: e-mail, seletor "Papel de <e-mail>" e Remover
       spec Equipe; feature 1.2.a; QA Passo 4 (a)
       Unable to find role="combobox" and name "Papel de admin@exemplo.org"

20:22  🟢 GREEN  lists the team by e-mail, each with its role and a way out  ·  1 passed

20:22  🔴 RED    changes a role by the e-mail in the body, and says Salvo
       Administrador no assistente → POST set-role {email, role: admin}; nenhuma URL com @
       spec mudar papel; ADR-0021; mutação 8; QA Passo 4 (b)
       Unable to find an element with the text: Salvo.

20:22  🟢 GREEN  changes a role by the e-mail in the body, and says Salvo  ·  2 passed

20:23  🔴 RED    puts the role back when the API keeps the last administrator
       409 last_admin no set-role → mensagem; o seletor volta a Administrador; sem Salvo
       spec último administrador protegido; L9; mutação 7; QA Passo 4 (d)
       passou de primeira (o seletor controlado só muda com a resposta); RED
       provado pela mutação 7 (papel otimista sem reverter)

20:23  🟢 GREEN  puts the role back when the API keeps the last administrator  ·  3 passed

20:23  🔴 RED    removes a member by the e-mail in the body / keeps the last administrator on the team when the API refuses to remove it
       Remover → POST remove {email}, some da lista; 409 last_admin → mensagem, fica
       spec remover; último admin; L9; QA Passo 4 (c)(d)
       Unable to find … text: Salvo / Unable to find role="alert"

20:23  🟢 GREEN  removes a member … / keeps the last administrator …  ·  5 passed

20:23  🔴 RED    gives access to a new e-mail with the role chosen, as the API stores it
       e-mail + papel + Enter → POST /api/members com o corpo exato; o membro da
       resposta (minúsculo) entra na lista; campo limpo
       spec liberar e-mail com papel; QA Passo 4 (e)
       Unable to find … role "textbox" and name "E-mail"

20:23  🟢 GREEN  gives access to a new e-mail with the role chosen, as the API stores it  ·  6 passed

20:24  🔴 RED    tells why an e-mail was refused, adding no one and not repeating it
       e-mail inválido → 400 → motivo junto ao formulário, lista igual, sem Salvo
       spec e-mail inválido com motivo; QA Passo 4 (e)
       passou de primeira (NewMember já tratava o erro); RED provado pela
       mutação que descarta a mensagem

20:24  🟢 GREEN  tells why an e-mail was refused …  ·  7 passed

20:24  🔴 RED    sends an administrator who gives up the role to the refusal, as an assistant
       admin (não o último) se rebaixa → GET /api/me de novo → tela de recusa
       L9; QA Passo 4
       Unable to find … text: Só o administrador acessa as configurações.

20:24  🟢 GREEN  sends an administrator who gives up the role to the refusal, as an assistant  ·  27 passed
       Identity expõe useReloadMe; o seletor só recarrega /api/me quando o papel é o próprio

20:25  ✅ PASSO 4/5 — Equipe  ·  +8 testes  ·  suíte 341
       mutação 8 (e-mail na URL) deixa 5 vermelhos

20:25  --- Passo 5: Documentação ---

20:27  ✅ PASSO 5/5 — Documentação  ·  +0 testes  ·  suíte 341
       CHANGELOG (Adicionado e Alterado), docs/architecture/README.md (linha da web),
       Registro do roadmap (item 26: L1, L3, L9, 409 dos segredos)

20:27  🖥️ 390 px  Chromium headless (playwright-core 1.58.2 já instalado na máquina, só biblioteca)
       sobre o build (dist), servidor estático + /api dublê local na porta 4396
       (e-mails @exemplo.org, segredos ausentes); /settings em dark e light:
       scrollWidth 390 = innerWidth, nenhum elemento fora da largura (exceto a
       faixa do menu, que rola sozinha); clicar Pessoas marca só Pessoas.
       Achado e corrigido no caminho: o ícone de Voltar do menu sem tamanho
       (.sn-back svg) e o textarea largo sem ocupar a linha. Arquivos só no
       scratchpad.

20:27  🏁 FINAL  web: 341 testes verdes; typecheck, lint e build limpos; nenhum
       arquivo Python, apps/api ou packages/core no diff. Mutações 1–11 da barra
       conferidas: cada uma deixa ao menos um teste vermelho.

## Rodada 1 · QA

20:28  📊 SUÍTE  web 341 passed  ·  0 failed (32 arquivos)
       typecheck, lint e build limpos; Python 1510 passed, 0 failed.

20:29  🔎 QA     comentários  ·  ✅ PASS
       Novos comentários são de intenção, referência, contorno ou contrato
       (CONTRIBUTING §5), em inglês; nenhum narra o código.

20:31  🧬 MUTAÇÕES · as 11 da barra (16 variantes)  ·  16 de 16 mortas
       ☠️  1 campo da chave não limpo                     2 testes
       ☠️  2 valor enviado no lugar da máscara            1 teste
       ☠️  3 Brando ↔ strict                              6 testes
       ☠️  4 PATCH com todos os níveis                    2 testes
       ☠️  5 "Salvo" em erro (modelo/preset/equipe)       1/2/1 testes
       ☠️  6 Apagar habilitado no padrão                  1 teste
       ☠️  7 papel não revertido após 409                 1 teste
       ☠️  8 e-mail na URL (cru e codificado, 2 rotas)    2–3 testes
       ☠️  9 scroll-spy sem disconnect                    1 teste
       ☠️  10 troca de preset sem flush                   1 teste
       ☠️  11 rotas de admin para o assistente            1 teste

20:33  🧬 MUTAÇÕES · vazamento de segredo, extra à barra  ·  3 de 4 mortas
       ☠️  console.log da chave no envio                  1 teste
       ☠️  chave repetida na mensagem de recusa           1 teste
       ☠️  cookies repetidos na mensagem de recusa        2 testes
       🚨  console.error da chave no 409      SOBREVIVEU — a matriz pede spy
       de console no caminho (e); o teste do 409 da chave não o tem.

20:34  🔎 QA     passo 1/5 — Estrutura  ·  ✅ PASS
       Menu L1, seções no mesmo rolar, jump, scroll-spy, fim, disconnect,
       FormRow no ExportDialog, assistente sem rota de admin, erro por seção.

20:34  🔎 QA     passo 2/5 — Modelo e segredos  ·  ⚠️ PARCIAL
       Código não registra a chave; falta o spy de console no teste do 409
       da chave, que a matriz cobra em (e) — mutação extra sobreviveu.

20:34  🔎 QA     passo 3/5 — Presets  ·  ✅ PASS
       Níveis exatos, texto espúrio oculto, debounce 399/400, flush no id de
       origem, duplicar, padrão, apagar e 409 default_preset.

20:34  🔎 QA     passo 4/5 — Equipe  ·  ✅ PASS
       E-mail só no corpo (URLs sem @), 409 last_admin reverte/mantém, 400 sem
       eco, autorrebaixamento cai na recusa.

20:35  🔎 QA     passo 5/5 — Documentação  ·  ✅ PASS
       CHANGELOG, linha da web na arquitetura, Registro com L1, L3 e L9.

## Rodada 2 · implementador

20:35  ↩️ REABERTO  passo 2/5 — Modelo e segredos  ·  PARCIAL na Rodada 1
       Achado: o teste do 409 da chave não espiona o console; a mutação
       console.error(key) na recusa sobreviveu.

20:35  🔴 RED    tells why the key was refused, never showing or logging the key
       Recusa da chave (409 config_not_writable e 400) com espiões em
       console.log/info/warn/error/debug: a chave fictícia não chega a eles.
       feature 2.1.a "chave nunca em log ou erro"; matriz, passo 2 (c)(e).
       Só teste, sem mudança de produção: o código já não registra a chave,
       então o RED vem por mutação. Com console.error(key) no catch da chave:
       × 409  ·  × 400  ·  AssertionError: expected [ …(5) ] to deeply
       equal [ …(5) ]  ·  2 failed | 9 passed

20:36  🟢 GREEN  tells why the key was refused, never showing or logging the key
       mutação desfeita  ·  11 passed

20:36  🔴 RED    tells why the cookies were refused, never showing or logging them
       Recusa dos cookies (400 formato e 409) com os mesmos espiões: o
       conteúdo fictício não chega ao console. Matriz, passo 2 (d)(e).
       Por mutação: console.error(text) na recusa dos cookies
       × 400  ·  × 409  ·  2 failed | 9 passed. Controle: registrar só o
       nome do arquivo não vaza conteúdo e passa (11 passed).

20:37  🟢 GREEN  tells why the cookies were refused, never showing or logging them
       mutação desfeita  ·  11 passed

20:37  🧬 MUTAÇÕES · vazamento no console, recusas  ·  2 de 2 mortas
       ☠️  console.error(key) na recusa da chave        2 testes (409, 400)
       ☠️  console.error(text) na recusa dos cookies    2 testes (400, 409)

20:37  ✅ PASSO 2/5 — Modelo e segredos  ·  +1 teste (400 da chave)  ·  suíte 342
       typecheck, lint e build verdes.

## Rodada 2 · QA

20:39  📊 SUÍTE  web 342 passed  ·  0 failed
       typecheck, lint e build verdes; regressão Python 1510 passed.

20:40  🧬 MUTAÇÕES · vazamento no console, recusas (cópia no scratchpad)
       ·  5 de 5 mortas
       ☠️  console.error(key) na recusa da chave        2 testes (409, 400)
       ☠️  console.warn("recusada", { key }) idem       2 testes
       ☠️  console.log(refusal, key) idem               2 testes
       ☠️  console.debug(`k=${key}`) idem               2 testes
       ☠️  console.error(text) na recusa dos cookies    2 testes (400, 409)
       Todas mortas pela asserção do console, com o alerta renderizado
       (mutação com rethrow, não curto-circuito). Controle: registrar só
       refusal.message passa (11 passed) — o teste não é frágil.

20:41  🔎 QA     passo 2/5 — Modelo e segredos  ·  ✅ PASS
       Espiões de console nos dois caminhos de recusa (chave e cookies);
       produção de settings sem nenhuma chamada a console.

20:41  🔎 QA     passos 1, 3, 4, 5  ·  ✅ PASS (mantidos)
       Mudança da rodada só em ModelSection.test.tsx; suíte inteira verde.
