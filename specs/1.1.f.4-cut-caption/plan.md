# Plan: Estilo da legenda de um corte (`cut caption`)

**Issue**: 1.1.f.4
**Feature**: specs/1.1.f.4-cut-caption
**Data**: 2026-10-26

---

## Resumo

Modelo `CaptionSettings` (o que o usuário escolhe) com validação e conversão para o
`CaptionStyle` do desenho; `CaptionStyle`/`CaptionRenderer` ganham cor da borda, níveis de
sombra e fonte por arquivo; o estilo fica em JSON no corte; a CLI ganha `cut caption`.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md). As lacunas apontadas pelo plano de QA (qa.md) foram
fechadas pelo orquestrador na rodada 1 e estão na tabela de Decisões técnicas.

---

## Contexto de código

| Situação | Path |
|---|---|
| Criar | `packages/core/src/wordcut/cuts/caption.py` — `CaptionSettings` (enabled, font, size, color, position, offset, border, border_color, shadow), `DEFAULT_CAPTION`, `validated(current, changes)`, `stored_caption(stored)`, `to_style(settings, frame_height)` |
| Criar | `packages/core/src/wordcut/vertical/fonts.py` — catálogo `name → arquivo` a partir de `assets/fonts`, com o nome lido dos metadados da fonte |
| Alterar | `packages/core/src/wordcut/vertical/captions.py` — `CaptionStyle` com `outline_color`, `shadow_alpha` (0 = sem sombra), `frame_height` e `font`; `CaptionRenderer` usa todos e encosta a imagem na borda do quadro |
| Alterar | `packages/core/src/wordcut/service/cuts.py` — `caption_of(conn, cut_id)`, `update_caption(conn, cut_id, changes, now)`, `reset_caption`; `cut show` com o estilo efetivo; alterar e restaurar marcam `edited` |
| Alterar | `packages/core/src/wordcut/db/cuts.py` — só gravar `caption` (`set_caption`); a leitura já existe (`CutRow.caption`) |
| Alterar | `apps/cli/src/wordcut_cli/cut.py` — `cut caption <id> [opções]` |
| Criar | `packages/core/tests/test_caption_settings.py`, `test_caption_render_style.py`, `test_cut_caption_service.py`; `apps/cli/tests/test_cut_caption_command.py` |
| Alterar | `packages/core/tests/test_cuts_service.py` — só as duas asserções que fixavam `caption` em `{}` e `{"font_size": 72}` passam ao estilo efetivo |
| Alterar | `CHANGELOG.md`; `docs/cli.md` §8.2 e §8.6 |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python (core, cli) | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Padrão | Open Sans Bold, 60 px, `#FFD600`, centro, altura 50 %, borda 3 px preta, sombra suave | Estilo da igreja (1.1.f) e `DEFAULT_STYLE` atual |
| Faixas | tamanho 24–160 px; altura 10–90 %; borda 0–12 px | Altura igual ao protótipo (docs/prototype/wordcut.html, `range("pos", 10, 90)`); o desenho encosta na borda o que sairia do quadro |
| Posição → altura | `top` = 20 %, `center` = 50 %, `bottom` = 78 % do quadro; `offset` (10–90) é a altura final em %, e escolher `--position` ajusta `offset` para o valor da posição | Igual ao protótipo (Topo 20, Centro 50, Base 78) |
| Sombra | `none` alpha 0; `soft` alpha 140 (atual), deslocamento 3; `strong` alpha 220, deslocamento 5 | Mantém o padrão atual como "suave" |
| Cor | `#RRGGBB`, guardada em maiúsculas | Validação simples |
| Gravação | JSON só com o estilo completo; `NULL` = padrão; `--reset` grava `NULL` | Padrão muda no código sem migração |
| Combinações | `--offset` explícito vence `--position`; `--offset` sozinho mantém o `position`; `--reset` com outra opção → `invalid_argument`; `--on --off` → `invalid_argument` | Decisão do orquestrador (QA, decisões 3 e 4); documentado em docs/cli.md §8.6 |
| `edited` | alterar, desligar, ligar ou restaurar o estilo marca `edited` e atualiza `updated_at` (`cuts.mark_edited`) | Como o `fix-word`; `sermon suggest` não apaga o estilo de um sugerido |
| Dentro do quadro | o `CaptionRenderer` encosta a imagem na borda quando o centro pedido a poria fora do quadro | `vertical/render.py::_overlay` fatia linhas com `top` negativo |
| Estilo gravado | incompleto ou antigo é completado com o padrão; chaves desconhecidas são ignoradas | Padrão muda no código sem migração |
| `cut show` | `caption` é o estilo efetivo, nunca `{}` | docs/cli.md §8.2 |
| Validação | `validated(current, changes)` aplica as mudanças sobre o estilo atual; recusa não grava nada | Alteração parcial (FR-002) |
| Fonte | nome lido dos metadados do arquivo (Pillow `getname()` → "Open Sans Bold"), sem tabela fixa; provada pelo caminho que `to_style` entrega, não por pixels | Há uma fonte só no pacote |
| Desenho | teste com Pillow numa legenda curta: cor do texto, cor da borda e os três níveis de sombra conferidos nos pixels; centro na altura pedida; imagem dentro do quadro nos extremos | Prova FR-004 sem vídeo |

---

## Ordem de implementação

- [x] **Passo 1 — Modelo e validação** — `CaptionSettings`, padrão, faixas, catálogo de fontes.
- [x] **Passo 2 — Desenho** — `CaptionStyle`/`CaptionRenderer` com cor da borda, sombra e fonte; `to_style`.
- [x] **Passo 3 — Serviço** — mostrar, alterar parcialmente, desligar, restaurar, marcar `edited`; `cut show` com o estilo efetivo; teste de serviço no core.
- [x] **Passo 4 — CLI** — `cut caption` com as opções de docs/cli.md §8.6.
- [x] **Passo 5 — Documentação** — CHANGELOG; docs/cli.md §8.2 (estilo efetivo) e §8.6 (faixas, posições 20/50/78, JSON, combinações, `edited`).

---

## Verificação

- [x] Corte novo → estilo padrão completo.
- [x] Alterar alguns campos → só eles mudam; `cut show` reflete.
- [x] `--off`, `--on`, `--reset` funcionam.
- [x] Desenho aplica cor, borda, cor da borda, sombra e altura (pixels).
- [x] Fonte, cor e faixas inválidas, `--on --off`, `--reset` com outra opção → `invalid_argument`; corte inexistente → `not_found`.
- [x] Quality gates limpos.
