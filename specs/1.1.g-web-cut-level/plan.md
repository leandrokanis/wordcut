# Plan: Nível 3 — prévia 9:16, abas Texto e Legenda, grafia na prévia

**Issue**: 1.1.g (web) · **Feature**: specs/1.1.g-web-cut-level · **Data**: 2026-10-26

## Resumo
Tela do corte com player que salta entre trechos (porta `PlayerLike` do item 22), recorte
9:16 por CSS, legenda sobreposta com o estilo do corte (posição, cor, borda por
`-webkit-text-stroke`, sombra), abas Texto/Legenda com o formulário em linhas e edição de
palavra por clique duplo.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

## Contexto de código
| Situação | Path |
|---|---|
| Criar | `apps/web/src/features/cut/CutPage.tsx`, `CutPreview.tsx` (sequência de trechos), `CaptionOverlay.tsx`, `TextTab.tsx`, `CaptionTab.tsx`, `WordEditor.tsx`, `CutTimeline.tsx`, `sequence.ts` (controlador e conversão de tempo), `captions.ts` (blocos, palavra atual, `captionCss`), `useCaptionStyle.ts` (autosave) |
| Criar | testes Vitest (sequência com relógio falso, abas, autosave, clique duplo, bloqueio) |
| Alterar | `app/routes.tsx` (`/cuts/:id` → `CutPage`, passo 1), `api/client.ts` e `api/types.ts` (`Cut` estendido, preview, caption, words), `test/fixtures.ts`, `main.tsx` (Open Sans 700), `ui/app.css`, CHANGELOG e `docs/architecture/README.md` (passo 5) |

## Comandos de verificação
| Componente | Um arquivo | Suíte | Estática |
|---|---|---|---|
| `apps/web` | `npm --prefix apps/web test -- <arquivo>` | `npm --prefix apps/web test` | `npm --prefix apps/web run typecheck && npm --prefix apps/web run lint && npm --prefix apps/web run build` |

## Decisões técnicas
| Decisão | Escolha | Justificativa |
|---|---|---|
| Sequência | controlador puro com índice (`next(segments, index, t)`) testado sem DOM, com o exemplo fora de ordem de docs/cli.md §8.3 | Só pelo tempo é ambíguo com `out_of_order` (QA, lacuna 2) |
| Tempo | trechos e palavras em tempo da pregação; o player em tempo da live; `sermon_start` vem da pregação carregada (`GET /api/sermons/{id}`) e a conversão `live = sermon_start + t` fica só em `sequence.ts` (ADR-0023) | Um só lugar para o erro de fuso |
| Palavras | `words`, `segments` e `caption` de `GET /api/cuts/{id}`; tipo `Cut` estendido | `/preview` não traz `word_id` (QA, lacuna 3) |
| Player | só o `<video>` de `GET /api/sermons/{sermon_id}/video` por `PlayerFactoryContext`; o nível 3 nunca carrega o YouTube (ADR-0023); testes com `fakePlayers` | Reaproveita a porta do item 22 |
| Fonte | Open Sans 700 pelo `@fontsource/open-sans` (ADR-0022, sem outro host); o seletor lista as fontes conhecidas pela API, hoje "Open Sans Bold" | Pacote só traz essa fonte |
| Escalas | faixas da API (`size` 24–160, `border` 0–12, `offset` 10–90); a prévia converte px do quadro 1080 em `cqw` do quadro: `px / 1080 × 100` | A API fala em px no quadro 1080×1920 |
| Estilo como valor | `captionCss(style)` puro devolve as custom properties (`--cap-size`, `--cap-stroke`, `--cap-top`…), testado por valor | jsdom descarta `-webkit-text-stroke`/`cqw` |
| Correções de grafia | lista "Correções de grafia" com Desfazer na aba Legenda (passo 4): desfazer é `PUT` com o texto original | Protótipo; api.md |
| Fora | botão olho da camada Legenda e alternância 9:16/16:9 | Spec pede só 9:16; o Sim/Não do formulário liga e desliga |
| Bloqueio | no erro da grafia o campo continua aberto, a mensagem aparece junto à legenda sem repetir o texto digitado (ADR-0015) e Esc fecha | Spec: "mensagem no lugar" |
| Salvo | indicador "Salvo" no cabeçalho do painel, no autosave do estilo (passo 3) e na grafia (passo 4) | Requisitos gerais |
| Recorte 9:16 | `object-fit: cover` centrado; seguir o pregador fica para a exportação | Prévia sem renderizar (1.1.g) |
| Legenda | blocos por frase/pausa no navegador, palavra atual destacada | Aproximação; o render é a verdade |
| Autosave | `PATCH` com debounce 400 ms por campo; erro junto ao campo | Requisito geral |
| Grafia | `PUT` ao Enter/blur; `spelling_too_different` mostra o bloqueio | 1.1.f.3 |

## Ordem de implementação
- [x] **Passo 1 — Prévia** — rota `/cuts/:id`, sequência de trechos, recorte 9:16, timeline do corte.
- [x] **Passo 2 — Legenda na prévia** — sobreposição com o estilo, palavra atual.
- [x] **Passo 3 — Abas e formulário** — Texto/Legenda, regras de abrir/fechar, autosave, restaurar.
- [x] **Passo 4 — Grafia na prévia** — clique duplo, pausa, Enter/blur/Esc, bloqueio, "Salvo", lista "Correções de grafia" com Desfazer.
- [x] **Passo 5 — Documentação** — CHANGELOG e `docs/architecture/README.md`.

## Verificação
- [x] Prévia percorre trechos na ordem; legenda acompanha com o estilo.
- [x] Abas seguem as regras; formulário salva sozinho e restaura.
- [x] Clique duplo edita a palavra; bloqueio aparece; Esc cancela.
- [x] typecheck, lint, testes, build limpos.
