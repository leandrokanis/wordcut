# QA — 2.1.a (web, item 26) — Configurações e equipe na web

## Plano de QA — 2026-10-26

**baseline_commit**: 0d6b5daf71007398c871e61857908f3428cda353
**Componentes em escopo**: `apps/web` — `src/features/settings/` (alterar `SettingsPage.tsx` e
`SettingsPage.test.tsx`; criar as seções, `LevelControl.tsx`, `useScrollSpy.ts`), `src/ui/`
(`FormRow.tsx`, ou a extração do `SettingRow` de `ExportDialog.tsx` — L2), `src/api/client.ts`
e `src/api/types.ts` (L2), dublês e fixtures em `src/test/`; documentação (`CHANGELOG.md`,
"Não lançado"; `docs/architecture/README.md` se descrever a web por feature — L12). Fora:
`apps/api` e `packages/core` (as rotas de admin já existem, docs/api.md §2, ADR-0021; nenhum
arquivo deles deve aparecer no diff), busca no menu do protótipo (`sn-search`) e os campos do
protótipo sem rota na API (L3).
**Suítes que valem como prova**:
- `apps/web`: `npm --prefix apps/web test` (Vitest + Testing Library, jsdom; `fakeApi`/
  `fakeShellApi` para `fetch`, dublê de `IntersectionObserver`; nenhuma rede).
- Um arquivo: `npm --prefix apps/web test -- <arquivo>`.
- Estática: `npm --prefix apps/web run typecheck && npm --prefix apps/web run lint && npm --prefix apps/web run build`.
- Regressão: a suíte inteira da web continua verde (níveis 1–3, exportação, `routes.test.tsx`,
  `StatusBar.test.tsx`, `Saved.test.tsx`).

**Fontes da barra**: spec.md e plan.md desta pasta; features 2.1.a (chave só gravada, últimos
4; texto dos critérios nunca aparece; presets com nome, editáveis, padrão não apagável) e
1.2.a (configurações e equipe só do administrador; da pessoa só o e-mail); protótipo
`docs/prototype/wordcut.html` (`SPAGES`, `SPG`, `srow`, `levels`, `LEVELS_F`/`LEVELS_V`,
`secHtml`, `settingsScreen`, `spyScroll`, `jumpTo`, ações `pdup`/`pdel`/`pdefault`/`trole`/
`trm`, formulários `key` e `team`); docs/api.md §1–§2 (rotas de settings, segredos,
criteria, presets, members; 409 `config_not_writable`, `default_preset`, `last_admin`);
docs/cli.md §11–§12; ADR-0015 (erro não repete valor), ADR-0021 (admin no router; e-mail só
no corpo), ADR-0022 (cliente próprio, `useResource`, `/settings` recusa o assistente).

**Regras de dados de teste**: chave e cookies de teste são fictícios (ex.: `sk-teste-ficticia-9f3a`,
cookies Netscape inventados) e a prova exige que **nunca** apareçam no DOM depois do envio
(`container.innerHTML` não contém o valor; o campo volta vazio). E-mails só `@exemplo.org`.

**Mapa de campos que a barra cobra** (protótipo → API):

| Seção | Rótulo | Controle | Campo / rota | Gravação |
|---|---|---|---|---|
| Modelo | Modelo | texto (L6) | `PATCH /api/settings` `llm_model` | Enter/blur; branco → 400, motivo junto ao campo |
| Modelo | Modelo do WhisperX | texto | `PATCH /api/settings` `whisper_model` | idem |
| Modelo | Chave da API | senha, `autocomplete="off"` | `PUT /api/settings/llm-key` `{"value"}` | Enter; mostra `llm_key` da resposta (`••••` + 4) ou "sem chave" |
| Modelo | Cookies do YouTube | arquivo ou área de colar (L5) | `PUT /api/settings/youtube-cookies` `{"value"}` | envio explícito; mostra "presentes"/"ausentes" |
| Presets | Preset (seletor) | `select`, "· padrão" no padrão | `GET /api/presets` | — |
| Presets | Nome | texto | `PATCH /api/presets/{id}` `name` | Enter/blur; vazio/repetido → 400 |
| Presets | Padrão | botão "Tornar padrão" / chip | `POST /api/presets/{id}/set-default` | imediato |
| Presets | Duplicar / Apagar | botões; Apagar desabilitado no padrão | `POST /api/presets` `{name, from_id}` / `DELETE` | imediato; 409 `default_preset` |
| Presets | Instruções adicionais | `textarea` | `instructions` | debounce |
| Filtros | um por critério `type: "filter"` | `Choice` Brando/Moderado/Rigoroso | `levels: {"<id>": "lenient"\|"moderate"\|"strict"}` | imediato ao clicar |
| Valor | um por critério `type: "value"` | idem | idem | idem |
| Formato | Duração final / ideal | par de números | `duration_allowed` / `duration_ideal` `{min,max}` | debounce/blur; mín > máx ou ideal fora → 400, nada salvo |
| Formato | Permitir reordenar | Não/Sim | `reorder` | imediato |
| Formato | Palavras protegidas | texto separado por vírgula | `protected_words` (lista) | debounce/blur |
| Pessoas | e-mail + papel | `select` Assistente/Administrador | `POST /api/members/set-role` | imediato; 409 `last_admin` |
| Pessoas | Remover | botão | `POST /api/members/remove` `{email}` | imediato; 409 `last_admin` |
| Pessoas | Liberar acesso | e-mail + papel | `POST /api/members` `{email, role}` | Enter; 400 com motivo |

### Matriz por passo

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Estrutura | (a) Admin em `/settings` → `navigation` "Seções das configurações" com "Voltar às pregações" e os links das seções na ordem do protótipo (L1), e uma `section` por link, todas no mesmo rolar (sem paginação: todas presentes no DOM ao mesmo tempo, com `h2`). (b) Clicar num link chama a rolagem da seção certa (`scrollIntoView`/`scrollTo` com dublê) e marca o link com `aria-current="true"`; nenhum outro marcado. (c) Scroll-spy: o dublê de `IntersectionObserver` dispara a entrada visível de uma seção → só o link dela fica `aria-current`; no fim da rolagem, a última. O observador é desconectado ao sair da tela (`disconnect` chamado no unmount). (d) `FormRow`: rótulo à esquerda, descrição opcional e controle à direita (`.srow`/`.sl`/`.sd`/`.ctl`), e o controle tem nome acessível igual ao rótulo; um só componente reaproveitado pelo `ExportDialog` (L2). (e) Assistente → "Só o administrador acessa as configurações.", nenhuma chamada a rota de admin (`calls` sem `/api/settings`, `/api/presets`, `/api/criteria`, `/api/members`). (f) Erro de carga (403/500/rede) → mensagem da API, sem tela branca. | `SettingsPage.test.tsx` com `renderRoute("/settings")` + `fakeShellApi`; dublê de `IntersectionObserver` em `src/test/` (registra instâncias, `observe`, `disconnect`, e expõe `trigger(entries)`); `Element.prototype.scrollIntoView = vi.fn()`. O teste do item 21 que fixa os sete links é ajustado só pelo que L1 decidir. |
| 2 — Modelos e segredos | (a) Carrega `GET /api/settings` e mostra `llm_model`, `whisper_model`, a máscara `llm_key` (ou "Nenhuma chave gravada" com `null`) e cookies "presentes"/"ausentes". (b) Modelo: mudar e confirmar (Enter/blur) → um `PATCH /api/settings` com só o campo mudado; `Saved` mostra "Salvo"; branco → 400 → `role="alert"` junto ao campo com a mensagem da API e "Salvo" não aparece; o valor não é repetido na mensagem (ADR-0015). Sem mudança, blur não grava. (c) Chave: `input type="password"`, `autocomplete="off"`; Enter → `PUT /api/settings/llm-key` com corpo exato `{"value": "<fictícia>"}`; o campo volta vazio; a máscara passa a ser a da resposta; o valor fictício não está em `container.innerHTML` em momento nenhum depois do envio, nem em `console.*` (spy). Vazio não envia. (d) Cookies: envio → `PUT /api/settings/youtube-cookies` `{"value"}`; depois mostra "presentes"; o conteúdo nunca é renderizado. (e) 409 `config_not_writable` em qualquer segredo → a mensagem da API e a orientação de gravar pela CLI no host (L5), campo limpo, máscara/presença inalterada; 400 de cookies fora do formato → motivo junto ao campo, sem eco. | Componente via `renderRoute` + `fakeShellApi` com rotas exatas; `calls` filtradas por método/URL e corpo comparado por igualdade; `apiError(409, "config_not_writable", …)`; `vi.spyOn(console, "log"/"error")` sem o valor. |
| 3 — Presets | (a) Seletor com os presets de `GET /api/presets`, o padrão marcado "· padrão" e selecionado de início; trocar o preset troca todas as seções de preset (Presets, Filtros, Valor, Formato). (b) Níveis: `GET /api/criteria` separa Filtros (`type: "filter"`) e Valor (`type: "value"`), um `Choice` por critério com nome acessível "Rigidez: <name>", três botões Brando/Moderado/Rigoroso; o pressionado vem de `preset.levels[id]`; clicar outro → `PATCH /api/presets/{id}` com `{"levels": {"<id>": "<lenient\|moderate\|strict>"}}` exato (só o critério mudado); "Salvo". Mapa de rótulo → valor provado nos três sentidos. (c) Texto dos critérios nunca aparece: o DOM só tem `name` do critério; nenhum campo `text`/`prompt` é pedido ou exibido (fixture com um campo `text` espúrio que não pode aparecer). (d) Formato: durações → `PATCH` com `duration_allowed`/`duration_ideal` `{min,max}` inteiros; mín > máx ou ideal fora da permitida → 400 da API → motivo junto ao campo, sem "Salvo" (o valor fica na tela para corrigir, mas o servidor não mudou). Reordenar Não/Sim → `{"reorder": bool}`. Palavras protegidas "a, b ,c" → `{"protected_words": ["a","b","c"]}` (aparadas, sem vazias). (e) Instruções adicionais e nome com debounce: várias teclas em < intervalo → um `PATCH` com o último valor; nome vazio/repetido → 400 com motivo junto ao campo. (f) Troca de preset com gravação pendente: a gravação vai para o preset em que foi digitada (URL com o id original) ou é descarregada antes da troca (L7). (g) Criar/duplicar → `POST /api/presets` `{"name", "from_id"}`; o novo aparece e fica selecionado. (h) Tornar padrão → `POST …/set-default`; o chip e o "· padrão" mudam de preset. (i) Apagar: desabilitado no padrão; em outro → `DELETE /api/presets/{id}`, some da lista, seleção volta ao padrão; 409 `default_preset` (corrida) → mensagem, nada some. | Componente com fixtures `criteria()` (≥ 2 filtros e ≥ 2 valores) e `preset()`; `vi.useFakeTimers` + `userEvent.setup({ advanceTimers })` para o debounce (intervalo − 1 → 0 chamadas; +1 → 1); `LevelControl` testado também isolado por tabela (3 níveis × clique). |
| 4 — Equipe | (a) Lista de `GET /api/members` por e-mail, cada um com `select` "Papel de <e-mail>" (Assistente/Administrador ↔ `assistant`/`admin`) e Remover. (b) Mudar papel → `POST /api/members/set-role` `{"email","role"}` (e-mail só no corpo; nenhuma URL com o e-mail — ADR-0021); "Salvo". (c) Remover → `POST /api/members/remove` `{"email"}`; some da lista. (d) Último administrador: 409 `last_admin` no set-role e no remove → mensagem da API, a linha volta ao papel anterior / continua na lista (L9). (e) Liberar acesso: e-mail + papel → `POST /api/members` com o corpo exato; o membro aparece (e-mail da resposta, minúsculo); campo limpo. E-mail inválido ou repetido → 400 → motivo junto ao campo, sem eco do e-mail na mensagem, nada novo na lista. Nenhum dado além de e-mail e papel na tela (LGPD). | Componente com fixture de membros (1 admin + 1 assistente); `apiError(409, "last_admin", …)`, `apiError(400, "invalid_argument", …)`; asserção sobre todas as `calls.url` não conterem `@`. |
| 5 — Documentação | `CHANGELOG.md`, "Não lançado": configurações e equipe na web (item 26). `docs/architecture/README.md`, linha da web por feature, se ela lista as features. Sem ADR nova salvo decisão de arquitetura nova (o dublê de `IntersectionObserver` não é). Divergências do protótipo (L1, L3) registradas no Registro do roadmap. | Leitura do diff contra o baseline. |

### Matriz por critério de aceite

| Critério de aceite | O que o cobre |
|---|---|
| spec — Modelos e segredos: mudar o modelo salva sozinho | Passo 2 (b) |
| spec — colar a chave e confirmar mostra só `••••` + 4 últimos | Passo 2 (c): máscara da resposta, valor ausente do DOM |
| spec — cookies mostram "presentes" | Passo 2 (a)(d) |
| spec — Presets: escolher preset | Passo 3 (a) |
| spec — mudar níveis (brando/moderado/rigoroso) por critério | Passo 3 (b) |
| spec — formato, reordenar, palavras protegidas, instruções, com autosave | Passo 3 (d)(e) |
| spec — criar, renomear, apagar (menos o padrão) e definir padrão | Passo 3 (e)(g)(h)(i) |
| spec — Equipe: liberar e-mail com papel, mudar papel, remover | Passo 4 (b)(c)(e) |
| spec — último administrador protegido | Passo 4 (d) |
| spec — Navegação: rolagem contínua; o menu pula e acompanha a rolagem | Passo 1 (a)(b)(c) |
| spec borda — Assistente não acessa a tela | Passo 1 (e) (já coberto pelo item 21; regressão + nenhuma rota de admin chamada) |
| spec borda — Valor inválido não é salvo e mostra o motivo junto ao campo | Passo 2 (b)(e), Passo 3 (d)(e), Passo 4 (e): `role="alert"` associado ao campo (`aria-describedby` ou dentro da linha), sem "Salvo" |
| spec borda — O texto dos critérios nunca aparece | Passo 3 (c) |
| FR-001 — Seções sobre as rotas de admin do item 20b | Passos 2–4: `fakeApi` com as rotas exatas de docs/api.md; nenhuma rota fora da tabela |
| FR-002 — Autosave com "Salvo"; segredos só por envio, nunca exibidos | `Saved` após cada gravação bem-sucedida (Passos 2–4) e nunca após erro; Passo 2 (c)(d) |
| feature 2.1.a — chave nunca em resposta, log ou erro | Passo 2 (c)(e): spy de `console`, mensagem de erro sem o valor |
| feature 1.2.a — da pessoa só o e-mail | Passo 4 (a)(e) |
| plan Verificação — Modelos salvam sozinhos; segredos mostram só máscara/presença | = Passo 2 |
| plan Verificação — Presets editáveis com autosave; padrão protegido | = Passo 3 (b)(d)(e)(i) |
| plan Verificação — Equipe com último admin protegido; e-mail inválido com motivo | = Passo 4 (d)(e) |
| plan Verificação — Assistente sem acesso; typecheck, lint, testes, build limpos | Passo 1 (e) + suíte e estática acima, com regressão da web inteira |

### Mutações que a rodada vai cobrar

Cada uma tem de deixar ao menos um teste vermelho: (1) não limpar o campo da chave após o
envio; (2) renderizar o valor enviado em vez da máscara da resposta; (3) mapa de níveis
trocado (Brando → `strict`); (4) `PATCH` de nível mandando todos os critérios em vez do
mudado; (5) mostrar "Salvo" num 400; (6) habilitar Apagar no preset padrão; (7) não
reverter o papel após 409 `last_admin`; (8) e-mail na URL do set-role/remove; (9) scroll-spy
sem `disconnect`; (10) debounce sem descarregar a gravação pendente na troca de preset;
(11) carregar as rotas de admin para o assistente.

### Lacunas do plan.md (escrito antes dos itens 21 a 25)

- **L1 — Seções divergentes.** O plano fala em "Modelos, Segredos, Presets, Equipe"; o item 21
  já entregou o menu do protótipo (`SPAGES`): Modelo, Presets, Filtros, Valor, Formato,
  Pessoas, Processamentos, com um teste que fixa os sete links. Recomendação: seguir o
  protótipo e o item 21 — chave, WhisperX e cookies dentro de **Modelo**; Presets, Filtros,
  Valor e Formato num grupo com o seletor de preset no topo (`settingsScreen`); **Pessoas**
  para a equipe. **Processamentos** não está no spec: opção conservadora é retirá-lo do menu
  neste item (ajustando o teste do item 21 de forma explícita) e registrar no roadmap; o
  "Em construção" não pode ficar.
- **L2 — Contexto de código incompleto.** Faltam em "Alterar" `src/api/client.ts` (funções das
  ~17 rotas de admin), `src/api/types.ts` (`Settings`, `Criterion`, `Preset`, `Member`) e
  `src/test/fixtures.ts`/dublê de `IntersectionObserver`. E o `ExportDialog.tsx` já tem um
  `SettingRow` com `.srow`: criar `ui/FormRow.tsx` sem reaproveitá-lo duplica código.
  Recomendação: extrair o `SettingRow` para `ui/FormRow.tsx` e usá-lo nas duas telas.
- **L3 — Campos do protótipo sem rota.** O protótipo tem gancho, autônomo, fechamento, limpo,
  ideias por pregação e descrição por critério; a API do preset só aceita `name`, `levels`,
  `duration_allowed`, `duration_ideal`, `reorder`, `protected_words`, `instructions`, e
  `criteria list` não traz descrição. Recomendação: entregar só os campos com rota; não
  inventar descrição de critério (as dicas `LEVELS_F`/`LEVELS_V` podem ir no `title` dos
  botões); registrar o resto como fora.
- **L4 — Níveis.** O plano diz "nomes do catálogo" sem o mapa. Recomendação: rótulos
  Brando/Moderado/Rigoroso ↔ `lenient`/`moderate`/`strict`, agrupados por `type`, reusando
  `ui/Choice.tsx` (que já ignora clique no escolhido) dentro de `LevelControl`.
- **L5 — Segredos: cookies e 409.** O protótipo não tem campo de cookies, e o plano não trata
  o 409 `config_not_writable` (o caso do Docker Compose, pendência do administrador).
  Recomendação conservadora: cookies por `<input type="file">` lido no cliente e enviado em
  `{"value"}`, nunca renderizado; no 409, mostrar a mensagem da API e o comando da CLI no host
  (`wordcut settings set-key < chave.txt`, docs/api.md §2), limpar o campo e manter a
  máscara/presença. Teste com valores fictícios.
- **L6 — Modelo: lista ou texto.** O protótipo usa `select` com IDs de exemplo; a API aceita
  qualquer texto não vazio e não lista modelos. Recomendação: campo de texto com Enter/blur
  (campo validado), não debounce — o plano manda debounce "por campo" e Enter/blur só para
  "chave, e-mail"; vale o Enter/blur também para modelos e nome do preset, que dão 400.
- **L7 — Autosave e troca de preset.** O plano não diz o intervalo do debounce nem o que fazer
  com gravação pendente ao trocar de preset ou sair da tela. Recomendação: 400 ms como
  `useCaptionStyle`; descarregar (flush) a pendente antes da troca, gravando no id em que foi
  digitada; um `PATCH` só com o campo mudado.
- **L8 — Duplicar vs. criar.** O protótipo cria por "Duplicar" (`Cópia de <nome>`); o spec diz
  "criar". Recomendação: "Duplicar" com `POST /api/presets {name: "Cópia de <nome>", from_id}`;
  nome repetido → 400 mostrado (ou sufixo numérico), sem travar a tela.
- **L9 — Último administrador.** O protótipo esconde Remover pelo prefixo `admin@`, o que não
  serve. Recomendação: não esconder por e-mail; a prova é o 409 `last_admin` da API com
  reversão do `select`. Rebaixar a si mesmo (não sendo o último) deve recarregar
  `GET /api/me` e cair na tela de recusa; registrar se ficar fora.
- **L10 — Scroll-spy.** O protótipo usa a posição de rolagem e força a última seção no fim; o
  plano escolhe `IntersectionObserver`, que o jsdom não tem e não há dublê em `src/test/`.
  Recomendação: dublê novo e reutilizável, e a regra "no fim, a última seção" mantida.
- **L11 — Indicador "Salvo".** Protótipo usa um só `.s-saved` no topo da tela. Recomendação:
  um `Saved` global da página, disparado por toda gravação bem-sucedida, e nunca por erro.
- **L12 — Documentação.** O Passo 5 não cita `docs/architecture/README.md` nem o Registro do
  roadmap. Recomendação: atualizar a linha da web por feature, se houver, e registrar L1, L3
  e L9 no Registro.

## Rodada 1 — 2026-10-26 — working tree sobre 0d6b5da

**baseline_commit**: 0d6b5daf71007398c871e61857908f3428cda353
**Componentes avaliados**: `apps/web` (settings, `ui/FormRow`, `ui/Choice`, `api/client`/`types`,
`app/Identity`, `cut/ExportDialog`, dublês), documentação. Nenhum arquivo de `apps/api`,
`packages/` ou `docs/adr/` no diff.
**Suítes**: web test ✅ (341 / 0 falhas) · typecheck ✅ · lint ✅ · build ✅ · regressão Python
`uv run pytest` ✅ (1510 / 0 falhas)
**Mutações da barra**: 11 de 11 mortas (16 variantes, numa cópia no scratchpad; e-mail na URL
testado cru e com `encodeURIComponent`, em set-role e remove).
**Mutações extras de segredo**: 3 de 4 mortas; sobreviveu `console.error(key)` no caminho de
recusa da chave (o código real não registra nada; a lacuna é do teste).
**Comentários**: conforme CONTRIBUTING §5.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Estrutura | PASS | `SettingsPage.test.tsx` (9 testes: menu L1, mesmo rolar, jump + `aria-current`, faixa de leitura, última no fim, `disconnect` ×2, assistente sem rota de admin, erro por seção); `FormRow.test.tsx`; `ExportDialog` usa `FormRow` |
| 2 — Modelo e segredos | PARCIAL | (a)–(d) e o 409/400 de (e) cobertos em `ModelSection.test.tsx`; a matriz pede spy de `console` também em (e) ("chave nunca em log ou erro"), e o teste "explains how to store the key on the host…" (`ModelSection.test.tsx:122`) não o tem — `console.error(key)` na recusa sobrevive. Falta só o spy nesse teste |
| 3 — Presets | PASS | `PresetSections.test.tsx` (17) + `LevelControl.test.tsx` (tabela 3×2): `levels` só do critério, texto espúrio fora do DOM, debounce 399→0 / 400→1, flush no preset 1 antes da troca, 400 sem "Salvo", duplicar, padrão, apagar desabilitado e 409 |
| 4 — Equipe | PASS | `TeamSection.test.tsx` (8): corpo exato, `urlsWithEmail` vazio, 409 `last_admin` reverte papel e mantém linha, 400 sem eco e sem novo membro, autorrebaixamento → recusa |
| 5 — Documentação | PASS | `CHANGELOG.md` "Não lançado", linha da web em `docs/architecture/README.md`, Registro do roadmap com L1, L3 e L9; sem ADR nova |

### Critérios de aceite
- ✅ Modelos: mudar o modelo salva sozinho — "saves a changed model once it is confirmed with Enter"
- ✅ Chave mostra só `••••` + 4 — "sends a pasted key with Enter and shows only the mask"
- ✅ Cookies mostram "presentes" — "sends the chosen cookies file … only says they are there"
- ✅ Escolher preset — "opens on the default preset…", "shows the chosen preset in every preset section"
- ✅ Níveis por critério — "saves only the level picked…", `LevelControl.test.tsx`
- ✅ Formato, reordenar, palavras protegidas, instruções com autosave — testes de duração, reordenar, palavras, instruções
- ✅ Criar, renomear, apagar (menos o padrão), definir padrão — testes de duplicar, renomear, apagar, padrão
- ✅ Equipe: liberar, mudar papel, remover — `TeamSection.test.tsx`
- ✅ Último administrador protegido — "puts the role back…", "keeps the last administrator on the team…"
- ✅ Navegação contínua com scroll-spy — `SettingsPage.test.tsx`
- ✅ Assistente não acessa — "refuses the settings…", "asks the API nothing of the administrator's…"
- ✅ Valor inválido não salvo, motivo junto ao campo — modelo branco, duração recusada, nome repetido, e-mail recusado, cookies 400
- ✅ Texto dos critérios nunca aparece — "shows each criterion only by its name, even if a prompt text came along"
- ✅ FR-001 — rotas exatas no `fakeSettingsApi`
- ✅ FR-002 — "Salvo" só após sucesso (mutações 5a–5c mortas); segredos só por envio
- ⚠️ feature 2.1.a — chave nunca em log ou erro: DOM e mensagem cobertos nos dois caminhos; `console` só no caminho de sucesso
- ✅ feature 1.2.a — da pessoa só o e-mail — "lists the team by e-mail…"
- ✅ plan Verificação — typecheck, lint, testes, build limpos

### Veredito geral: PARCIAL
Um só achado, de teste: falta o spy de `console` no teste do 409 da chave (Passo 2 (e)). O código
não expõe segredo no DOM nem no console, e nenhum e-mail vai para URL.

## Rodada 2 — 2026-10-26 — working tree sobre 0d6b5da

**baseline_commit**: 0d6b5daf71007398c871e61857908f3428cda353
**Componentes avaliados**: `apps/web` (reaberto só o Passo 2; a rodada mudou apenas
`ModelSection.test.tsx`, e `ModelSection.tsx` tem o mesmo conteúdo, sem nenhuma chamada a
`console` em `features/settings/`). Nenhum arquivo de `apps/api`, `packages/` ou `docs/adr/` no diff.
**Suítes**: web test ✅ (342 / 0 falhas) · typecheck ✅ · lint ✅ · build ✅ · regressão Python
`uv run pytest` ✅ (1510 / 0 falhas)
**Mutações da rodada** (cópia no scratchpad): 5 de 5 mortas — `console.error(key)`,
`console.warn(…, { key })`, `console.log(refusal, key)` e `console.debug` com a chave na recusa
da chave (2 testes cada: 409 e 400); `console.error(text)` na recusa dos cookies (2 testes: 400 e
409). Todas vermelhas pela asserção do console, com o alerta já na tela. Controle: registrar só
`refusal.message` continua verde.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Estrutura | PASS | mantido da Rodada 1; suíte verde |
| 2 — Modelo e segredos | PASS | `ModelSection.test.tsx`: "tells why the key was refused, never showing or logging the key" (409 e 400) e "tells why the cookies were refused, never showing or logging them" (400 e 409) com espiões em `console.log/info/warn/error/debug`; mutação `console.error(key)` vermelha |
| 3 — Presets | PASS | mantido da Rodada 1; suíte verde |
| 4 — Equipe | PASS | mantido da Rodada 1; suíte verde |
| 5 — Documentação | PASS | mantido da Rodada 1 |

### Critérios de aceite
- ✅ Todos os critérios da Rodada 1 continuam cobertos (suíte 342 verde).
- ✅ feature 2.1.a — chave nunca em resposta, log ou erro — DOM, mensagem e `console` cobertos nos
  caminhos de sucesso e de recusa (409 e 400), para a chave e para os cookies

### Veredito geral: PASS
O achado da Rodada 1 (spy de `console` na recusa da chave) está fechado, e também nos cookies.
Suítes e checagens estáticas verdes.
