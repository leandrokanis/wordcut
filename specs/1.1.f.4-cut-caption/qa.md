# QA — 1.1.f.4 — Estilo da legenda de um corte (`cut caption`)

## Plano de QA — 2026-10-26

**baseline_commit**: b0af62e9f463c430a015a749b1e88096ebeb329f
**Componentes em escopo**: `packages/core` (`wordcut/cuts/caption.py` novo,
`wordcut/vertical/fonts.py` novo, `wordcut/vertical/captions.py`, `wordcut/service/cuts.py`,
`wordcut/db/cuts.py`); `apps/cli` (`wordcut_cli/cut.py`); documentação (`CHANGELOG.md`,
`docs/cli.md` §8.6)
**Suítes que valem como prova**:
- Python (core e cli): `uv run pytest -q` na raiz (testpaths de core, cli e api); um arquivo:
  `uv run pytest <arquivo> -q`
- Checagem estática: `uv run ruff check . && uv run ruff format --check . && uv run mypy`
  (o mypy lê `files` do `pyproject.toml`; equivale ao `mypy src` do roadmap)

Diff de cada rodada: `git diff b0af62e9f463c430a015a749b1e88096ebeb329f` mais os arquivos
novos de `git status --short`. Desenho provado em pixels com Pillow, sem vídeo (roadmap: nenhum
vídeo real é renderizado).

### Decisões que o QA tomou no lugar do plano

O plan.md não decidiu estes pontos. A execução automatizada não admite perguntas, então o QA
adotou a opção mais conservadora. Cada uma vale como barra até o plano ser corrigido:

1. **`edited`**: alterar, desligar, ligar ou restaurar o estilo marca o corte como editado
   (`cuts.mark_edited`), como o `fix-word` (docs/cli.md §8.5). Sem isso, `sermon suggest`
   (`delete_unedited_suggestions`) apaga o estilo de um corte sugerido.
2. **Legenda dentro do quadro**: para qualquer `offset` de 0 a 100, a imagem desenhada fica
   inteira no quadro (`0 ≤ top` e `top + altura ≤ frame_height`). O centro fica na altura
   pedida e só é encostado na borda quando sairia do quadro. O plano justifica a faixa com
   "cabe no quadro", e o `_overlay` de `vertical/render.py` fatia linhas com `top` negativo.
3. **`--position` junto com `--offset`**: o `--offset` informado vence. `--offset` sozinho
   não muda o `position`.
4. **`--reset` com outra opção de estilo**: `invalid_argument`, porque o pedido é ambíguo.
5. **Estilo gravado incompleto ou com chave antiga** (por exemplo, o `{"font_size": 72}` dos
   testes atuais): o estilo efetivo é o padrão completado pelas chaves conhecidas, e as
   desconhecidas são ignoradas. Nunca é erro.
6. **Validação sem gravação**: uma alteração recusada não grava nada; a linha e o
   `updated_at` ficam como estavam. Sem opções, o comando só mostra o estilo e não grava.

### Matriz por passo

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Modelo e validação | `DEFAULT_CAPTION` é exatamente o JSON do cenário 1 (9 chaves: enabled, font "Open Sans Bold", size 60, color "#FFD600", position "center", offset 50, border 3, border_color "#000000", shadow "soft"). A alteração parcial muda só as chaves informadas sobre o estilo atual (não sobre o padrão). Faixas testadas nas duas bordas: size 24/160 aceitos e 23/161 recusados; offset 0/100 e −1/101; border 0/12 e −1/13. Cor `#RRGGBB` aceita em minúsculas e guardada em maiúsculas; `#FFF`, `FFFFFF`, `#GGGGGG` e texto vazio recusados. `position` muda o `offset` para 15/50/80; com `offset` explícito, vence o `offset` (decisão 3). `position` e `shadow` fora dos valores são recusados também no core, não só pelo argparse. Fonte desconhecida dá `invalid_argument` com as fontes disponíveis em `details`. O catálogo lista as fontes de `assets/fonts` (hoje só "Open Sans Bold" → `OpenSans-Bold.ttf`, que existe) e ignora `OFL.txt`. | `packages/core/tests/test_caption_settings.py`, unitário, pela interface pública (`DEFAULT_CAPTION`, função de validação, catálogo de `vertical/fonts.py`). Erros conferidos por `WordcutError.code == "invalid_argument"` e `details`. Mutações cobradas: limite 160→161, `upper()` removido, `position` sem ajustar `offset`; as três precisam ser mortas. |
| 2 — Desenho | `to_style(settings, frame_height)` leva cada campo ao `CaptionStyle`: tamanho, cor RGB, borda, `outline_color`, sombra (none com alpha 0; soft com alpha 140 e deslocamento 3; strong com alpha 220 e deslocamento 5), altura e arquivo da fonte do catálogo. Em pixels, numa legenda curta com texto `#00FF00` e borda `#FF0000`: há pixels opacos exatamente da cor do texto e da cor da borda; com `border 0` não sobra pixel da cor da borda. Sombra: com texto e borda não pretos, `none` não deixa pixel preto puro com alpha ≥ 0,5; `soft` deixa, com alpha máximo de cerca de 140/255; `strong` deixa, com alpha maior que o do `soft`. Altura: o centro da imagem fica a ±1 px de 15 %, 50 % e 80 % de 1920 (288, 960, 1536). Nas pontas (offset 0 e 100, size 160 em duas linhas), a imagem cabe no quadro (decisão 2). O tamanho maior gera uma imagem mais alta. Regressão: `render(to_style(DEFAULT_CAPTION, 1920))` é idêntico, pixel a pixel, ao `CaptionRenderer(1080)` com `DEFAULT_STYLE`, e o `test_captions.py` continua verde sem alteração. | `packages/core/tests/test_caption_render_style.py` com Pillow e NumPy sobre `CaptionImage` (`bgr`, `alpha`, `top`), sem ffmpeg nem vídeo. Mutações cobradas: `stroke_fill` fixo em preto, alpha da sombra fixo em 140, `centre_y` fixo em 960, retirada do encosto na borda; todas precisam ser mortas. A fonte só é provável pelo caminho que `to_style` entrega, porque há uma fonte só; trocar o catálogo pelo `DEFAULT_FONT` fixo pode sobreviver sem virar achado. |
| 3 — Serviço | `caption_of` de um corte sem estilo devolve o padrão completo. `update_caption` grava o JSON completo (as 9 chaves em `cuts.by_id(...).caption`), muda só o informado, atualiza `updated_at`, marca `edited` (decisão 1) e devolve o estilo efetivo. Desligar e ligar mudam só `enabled`. `reset_caption` grava `NULL` (`row.caption is None`), devolve o padrão ligado e marca `edited`. Uma alteração recusada não grava nada (decisão 6). `show_cut(...)["caption"]` é o estilo efetivo: o padrão completo quando `NULL`, nunca `{}`. Um estilo gravado incompleto é completado pelo padrão (decisão 5). Corte inexistente → `not_found` nas três funções. A gravação fica num novo `db.cuts` (`set_caption` ou equivalente) na transação do serviço (ADR-0004). | Teste de serviço no core sobre SQLite real, como `test_cuts_service.py` (por exemplo, `packages/core/tests/test_cut_caption_service.py`). As asserções de `test_cuts_service.py:147` (`"caption": {}`) e `:166` (`{"font_size": 72}`) mudam com este item. O QA aceita a mudança se ela só trocar o marcador provisório pelo estilo efetivo, sem tirar asserção de outro campo. Mutações cobradas: `mark_edited` removido, `or {}` mantido no `show_cut`; as duas precisam ser mortas. |
| 4 — CLI | `cut caption <id> --json` num corte novo devolve exatamente o JSON do cenário 1, com saída 0. Cenário 2: `--size 72 --color "#FFFFFF" --position bottom --shadow strong` muda só esses campos (e o `offset` para 80), e `cut show <id> --json` traz o mesmo `caption`. Cenário 3: `--off` deixa `enabled: false` e o resto intacto; depois, `--reset` devolve o padrão com `enabled: true`. `--on` religa. Casos de borda com saída 2 (`invalid_argument`): `--on --off`, fonte inexistente (com `details` listando as fontes), `--color FFF`, `--size 23`, `--offset 101`, `--border 13`, `--position middle`, `--shadow hard`, `--reset --size 72` (decisão 4). Corte inexistente → `not_found`, saída 3. Sem `--json`, a saída em texto mostra o estilo e sai com 0. O comando fica registrado com `help` e `example`, como os outros de `cut`. | `apps/cli/tests/test_cut_caption_command.py` chamando `wordcut_cli.main(argv)` com `wordcut_home` e `capsys`, no padrão de `test_cut_fix_word_command.py`. O JSON é lido do stdout, e erro e código de saída seguem o contrato (ADR-0012). `test_cli_contract.py` continua verde. |
| 5 — Documentação | O `CHANGELOG.md` ganha, em "Não lançado › Adicionado", o `cut caption` com o estilo por corte, `--on/--off/--reset` e o desenho com cor da borda e sombra. O `docs/cli.md` §8.6 traz as faixas, os valores de posição (15/50/80), o formato JSON da saída e as regras de combinação (decisões 3 e 4), e o §8.2 diz que `caption` é o estilo efetivo. Os valores do documento batem com o código. | Leitura do diff de `CHANGELOG.md` e de `docs/cli.md`, conferida contra as constantes do código. Não há teste. |

### Matriz por critério de aceite

| Critério de aceite | O que o cobre |
|---|---|
| Spec · Cenário "ver o estilo padrão" (JSON exato num corte novo) | Passo 4: teste de CLI com igualdade exata do JSON. Passo 1: `DEFAULT_CAPTION`. Passo 3: `caption_of` com `NULL`. |
| Spec · Cenário "mudar o estilo" (só os campos informados mudam; `cut show` reflete) | Passo 4: teste de CLI com o comando literal do spec, seguido de `cut show --json`. Passo 3: alteração parcial sobre um estilo já alterado. |
| Spec · Cenário "desligar e restaurar" | Passo 4: `--off` e depois `--reset` na CLI. Passo 3: `reset_caption` grava `NULL` e devolve o padrão ligado. |
| Spec · Cenário "estilo vira imagem" (estilo exato e altura da posição) | Passo 2: testes de pixels (cor do texto, borda, cor da borda, três níveis de sombra, altura de top, center e bottom, tamanho) e regressão do padrão. |
| Spec · Borda: fonte inexistente → `invalid_argument` com as fontes em `details` | Passo 1 (core) e passo 4 (CLI, saída 2 e `details`). |
| Spec · Borda: cor fora de `#RRGGBB` → `invalid_argument` | Passo 1 (casos de cor) e passo 4 (`--color FFF`). |
| Spec · Borda: tamanho, altura ou borda fora da faixa → `invalid_argument` | Passo 1 (as duas bordas de cada faixa) e passo 4 (um caso de cada na CLI). |
| Spec · Borda: `--on` e `--off` juntos → `invalid_argument` | Passo 4: saída 2 pelo parser do contrato. |
| Spec · Borda: corte inexistente → `not_found` | Passo 3 (serviço) e passo 4 (CLI, saída 3). |
| FR-001: estilo gravado no corte; ausência significa o padrão | Passo 3: JSON completo em `cuts.by_id(...).caption`; `NULL` leva ao padrão em `caption_of` e no `show_cut`. |
| FR-002: sem opções mostra; com opções altera só o informado | Passo 4 (sem opções não grava: `updated_at` igual) e passo 3 (alteração parcial). |
| FR-003: `--reset` volta ao padrão; `--off`/`--on` desligam e ligam | Passos 3 e 4. |
| FR-004: o desenho aplica fonte, tamanho, cor, borda, cor da borda, sombra e posição | Passo 2. A fonte é provada pelo caminho do catálogo em `to_style`, e não em pixels, porque há uma fonte só. |
| Verificação · Corte novo → estilo padrão completo | Passos 3 e 4 (igualdade exata). |
| Verificação · Alterar alguns campos → só eles mudam; `cut show` reflete | Passos 3 e 4. |
| Verificação · `--off`, `--on`, `--reset` funcionam | Passo 4, com o efeito no banco conferido no passo 3. |
| Verificação · O desenho aplica cor, borda, cor da borda, sombra e altura (pixels) | Passo 2. |
| Verificação · Fonte, cor e faixas inválidas e `--on --off` → `invalid_argument`; corte inexistente → `not_found` | Passos 1, 3 e 4. |
| Verificação · Quality gates limpos | `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .` e `uv run mypy` (strict), todos verdes. |
| Decisões 1 a 6 do QA (não estão no spec) | Passos 2, 3 e 4, como na matriz. Um teste que faltar deixa o passo PARCIAL, não FAIL, até o plano ser corrigido. |

### Divergências do plan.md com o código atual (escrito antes dos itens 11 a 13)

| Plano | Código no baseline | Ajuste recomendado |
|---|---|---|
| `db/cuts.py`: "ler/gravar `caption` (JSON)" | A leitura já existe: `CutRow.caption: dict \| None` e `_json_or_none`. Falta só gravar. | Acrescentar só a gravação (por exemplo, `set_caption(conn, cut_id, caption \| None, updated_at)`), sem refazer a leitura. |
| `service/cuts.py`: "`cut show` com o estilo efetivo" | `show_cut` devolve `row.caption or {}`, e os testes `test_cuts_service.py:147/166` cravam esse comportamento provisório. | Trocar pelo estilo efetivo e atualizar as duas asserções. `_existing` (`not_found`) já existe e deve ser reaproveitado. |
| O plano não fala de `edited` | `fix_word` chama `cuts.mark_edited`, e `sermon suggest` apaga os sugeridos não editados. | Marcar `edited` ao alterar ou restaurar o estilo (decisão 1) e registrar isso no §8.6. |
| Arquivos de teste: modelo, desenho e CLI | O passo 3 (serviço) fica sem teste previsto. | Incluir um teste de serviço no core. |
| `validated(changes)` | Assinatura sem o estilo atual. | `validated(current, changes)` ou equivalente; a barra cobra o comportamento. |
| "Posição → altura: igual ao protótipo" (15/50/80; 0–100 %) | O protótipo usa Topo 20, Centro 50, Base 78, altura 10–90 %, tamanho padrão 6,4 cqw (cerca de 69 px) e borda de cerca de 5 px. | Corrigir a justificativa no plan.md ou alinhar ao protótipo. O spec fixa o padrão em 60 px e borda 3, então o padrão fica como está. A barra segue o plano. |
| "Faixas… cabe no quadro" | `CaptionImage.top = centre_y − altura/2` sem encosto na borda; `vertical/render.py::_overlay` fatia `image[top:...]`. | Encostar a imagem na borda dentro do `CaptionRenderer` (decisão 2). Vale também para 10–90 %. |
| Catálogo `name → arquivo` | O Pillow lê `('Open Sans', 'Bold')` do `OpenSans-Bold.ttf`. | Derivar o nome dos metadados da fonte (`getname()`), sem tabela fixa. |
| `CaptionStyle` "com `outline_color` e `shadow_alpha`" | `CaptionStyle` já tem `shadow_offset`, `centre_y` fixo em 960, sem campo de fonte; `CaptionRenderer` recebe `font: Path`. | Manter `DEFAULT_STYLE` igual em pixels (regressão do passo 2) e levar o arquivo da fonte pelo parâmetro `font` que já existe ou por um campo novo. |

## Rodada 1 — 2026-10-26 — working tree sobre b0af62e

**baseline_commit**: b0af62e9f463c430a015a749b1e88096ebeb329f
**Componentes avaliados**: `packages/core`, `apps/cli`, documentação (`CHANGELOG.md`, `docs/cli.md`)
**Suítes**: Python (core, cli, api) ✅ (1097 / 0 falhas) · ruff check ✅ · ruff format --check ✅ · mypy strict ✅ (84 arquivos)

Barra: a matriz do topo com a decisão 5 do orquestrador (posições 20/50/78 %, `offset` 10–90 %;
extremos testados 10 e 90; o `--offset 101` da matriz equivale ao `--offset 91`).
Mutações numa cópia no scratchpad: 25 de 27 mortas. As duas que sobreviveram não são achados:
"catálogo → `DEFAULT_FONT`" (prevista como verde na barra) e "`if shadow_alpha` removido"
(equivalente, porque alpha 0 não desenha nada).

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Modelo e validação | PASS | `test_caption_settings.py` (38 casos): padrão exato, faixas nas duas bordas (24/160, 10/90, 0/12 aceitos; 23/161, 9/91, −1/13 recusados com `min`/`max`), cor em maiúsculas e 5 formas inválidas, 20/50/78, `offset` explícito vence, `offset` sozinho mantém `position`, `position`/`shadow`/fonte recusados no core com `choices`, catálogo `{"Open Sans Bold": "OpenSans-Bold.ttf"}` sem o `OFL.txt`. Mutações cobradas (160→161, `upper()`, `position` sem `offset`) mortas. |
| 2 — Desenho | PASS | `test_caption_render_style.py`: `to_style` campo a campo, pixels de `#00FF00` e `#FF0000`, sem pixel de borda com `border 0`, sombras 0/140/220 (±5/255), centro a ±1 px de 384/960/1498, encosto em 10 e 90 com 160 px em duas linhas, tamanho maior gera imagem mais alta, regressão pixel a pixel com `DEFAULT_STYLE`. `test_captions.py` sem alteração. Mutações cobradas (`stroke_fill` preto, alpha fixo 140, `centre_y` 960, encosto retirado) mortas. Pontos do implementador: o soft mede 137/255 por anti-aliasing, e a tolerância de 5/255 cabe no "cerca de 140" da matriz; o deslocamento 0 da sombra `none` não contraria a barra, que fixa só o alpha 0. |
| 3 — Serviço | PASS | `test_cut_caption_service.py`: padrão num corte novo, alteração parcial sobre o estilo atual, JSON completo em `cuts.by_id(...).caption`, `edited` e `updated_at`, reset grava `NULL` e marca `edited`, recusa não grava nada, estilo incompleto completado, `show_cut` com o estilo efetivo, `not_found` em `caption_of`/`update_caption`/`reset_caption`, `--off`/`--on` mudam só `enabled`. `db.cuts.set_caption` na transação do serviço (`service/cuts.py::_store_caption`). `test_cuts_service.py` só trocou as asserções das linhas 147 e 166 pelo estilo efetivo. Mutações cobradas (`mark_edited` fora, `or {}` mantido) mortas. |
| 4 — CLI | PASS | `test_cut_caption_command.py`: cenário 1 com JSON exato e saída 0; cenário 2 literal e `cut show --json`; cenário 3 (`--off` e depois `--reset`); `--on` religa; nove recusas com saída 2, `details` e estilo intacto; `--reset --size 72` sai 2; corte inexistente sai 3; sem opções não grava; texto em português; `--help` com exemplo. `test_cut_command.py` só ganhou `caption` na lista de ações. `test_cli_contract.py` verde. |
| 5 — Documentação | PASS | `CHANGELOG.md` em "Não lançado › Adicionado" (`cut caption` e desenho) e "Alterado" (`cut show`). `docs/cli.md` §8.2 (estilo efetivo) e §8.6 (faixas, 20/50/78, 10–90, combinações, `edited`, JSON). Os valores batem com `RANGES`, `POSITIONS` e `SHADOW_LOOKS`. |

Política de comentários (CONTRIBUTING.md §5): os comentários novos são de formato
(`RANGES`, `POSITIONS`, `SHADOW_LOOKS`, regex `#RRGGBB`, `shadow_alpha`), referência
(protótipo) ou intenção/alerta (encosto na borda, cores do teste de pixels). Todos estão em
inglês. Nenhum comentário fica fora dos tipos permitidos.

### Critérios de aceite
- ✅ Cenário "ver o estilo padrão" — `test_caption_of_a_new_cut_prints_the_church_style_and_exits_0`, `test_default_caption_is_the_church_style`, `test_a_new_cut_has_the_church_style`
- ✅ Cenário "mudar o estilo" — `test_caption_with_options_changes_only_those_and_cut_show_carries_the_new_style`, `test_a_change_alters_only_the_given_fields_over_the_current_style`
- ✅ Cenário "desligar e restaurar" — `test_caption_off_then_reset_turns_it_off_and_back_to_the_church_style`, `test_resetting_brings_back_the_church_style_turned_on`
- ✅ Cenário "estilo vira imagem" — `test_caption_render_style.py` (pixels, sombras, alturas, regressão)
- ✅ Fonte inexistente → `invalid_argument` com `details.choices` — core e CLI
- ✅ Cor fora de `#RRGGBB` → `invalid_argument` — core (5 formas × 2 campos) e CLI (`--color`, `--border-color`)
- ✅ Tamanho, altura ou borda fora da faixa → `invalid_argument` — core (duas bordas) e CLI
- ✅ `--on --off` e `--reset` com outra opção → `invalid_argument` — CLI
- ✅ Corte inexistente → `not_found` — serviço (três funções) e CLI (saída 3)
- ✅ FR-001 — `test_a_change_stores_the_whole_style_in_the_cut`, `test_resetting_stores_no_style_and_marks_the_cut_edited`, `test_the_shown_cut_carries_its_effective_style`
- ✅ FR-002 — `test_caption_without_options_does_not_touch_the_cut`, alteração parcial no core e no serviço
- ✅ FR-003 — reset, `--off` e `--on` no serviço e na CLI
- ✅ FR-004 — `test_caption_render_style.py`; a fonte é provada pelo caminho que `to_style` entrega, como a barra prevê
- ✅ Verificação do plan.md (6 itens) — os testes acima; quality gates limpos
- ✅ Decisões do QA e do orquestrador (`edited`, imagem dentro do quadro, combinações, estilo incompleto, recusa sem gravação) — testes de serviço, desenho e CLI

### Veredito geral: PASS
Os 5 passos passam, os critérios estão cobertos e as suítes e checagens estão verdes. As
mutações que a barra cobrava foram mortas.
