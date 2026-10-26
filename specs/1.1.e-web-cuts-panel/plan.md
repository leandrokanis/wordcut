# Plan: Nível 2 — painel de cortes

**Issue**: 1.1.e (web) · **Feature**: specs/1.1.e-web-cuts-panel · **Data**: 2026-10-26

## Resumo
Painel lateral com cards e menu, camadas de cortes na timeline (somente leitura), escolha ao
abrir e transições pela API.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

## Contexto de código
| Situação | Path |
|---|---|
| Criar | `apps/web/src/features/sermon/CutsPanel.tsx`, `CutCard.tsx`, `CutLayers.tsx` |
| Alterar | `apps/web/src/features/sermon/SermonPage.tsx` (painel `.side` + `.work`, recarga no `done`), `Timeline.tsx` (prop `layers`) |
| Alterar | `apps/web/src/api/types.ts` (item de `cut list`), `apps/web/src/api/client.ts` (`listCuts`, `chooseCut`, `discardCut`, `restoreCut`) |
| Alterar | `apps/web/src/test/fixtures.ts` (`listedCut`), `apps/web/src/ui/app.css` (painel, cards, menu, camadas, 390 px) |
| Alterar | `packages/core/src/wordcut/service/cuts.py` (`list_cuts` com `start`/`end`) |
| Criar/alterar | testes Vitest; `packages/core/tests/test_cuts_service.py`, `apps/cli/tests/test_cut_command.py`, `apps/api/tests/test_cuts_routes.py` |
| Alterar | `docs/cli.md` §8.1, `docs/api.md`, `docs/architecture/README.md`, `CHANGELOG.md` |

## Comandos de verificação
| Componente | Um arquivo | Suíte | Estática |
|---|---|---|---|
| `apps/web` | `npm --prefix apps/web test -- <arquivo>` | `npm --prefix apps/web test` | `npm --prefix apps/web run typecheck && npm --prefix apps/web run lint && npm --prefix apps/web run build` |
| Python (core, CLI, API) | `uv run pytest <arquivo>` | `uv run pytest` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

## Decisões técnicas
| Decisão | Escolha | Justificativa |
|---|---|---|
| Ordem | a do serviço (descartados por último) | Uma regra só |
| Abrir | `POST choose` e navegação para `/cuts/:id` | Requisito 1.1.e |
| Camadas | uma faixa por corte, sem alça nem arraste para nenhum papel | 2.1.c é da onda 6 |
| Tempo da camada (L1, orquestrador) | cada item de `cut list` traz `start` e `end`: menor início e maior fim dos trechos, em tempo da pregação, ao milissegundo (`list_cuts` no core; teste no core, na CLI JSON e na API); a web desenha em `sermon_start + start` … `sermon_start + end` | Evita uma prévia por corte; `docs/cli.md` §8.1 e `docs/api.md` atualizados |
| Lugar do painel (D1) | `.side` de 340 px à esquerda do `.work`; em 390 px empilha abaixo da timeline; sem botão de ocultar nesta onda | Protótipo |
| Camadas na `Timeline` (D2) | prop `layers` (vazia por padrão), uma `.th` + `.lane` por corte acima de "Vídeo"; testes antigos sem alteração | Não mexer no arraste das bordas |
| Recarga (D3) | painel e camadas pedem `GET /cuts` de novo quando a pregação recarrega (chave com `status`/`processed_at`) | Após `done` o painel não fica vazio |
| Cliente e tipos (D4) | `listCuts`, `chooseCut`, `discardCut`, `restoreCut` e tipo `ListedCut`; `suggestion_error` vem de `GET /api/sermons/{id}` | FR-001 |
| Abrir (L6) | `choose` só em `suggested`; `chosen` navega sem `POST`; `discarded` não abre; navega depois do 200; erro fica no painel | Barra de QA |
| Depois de descartar/restaurar (L7) | pede `GET /cuts` de novo, sem reordenar no cliente | Ordem do serviço |
| Textos (L8) | do protótipo: "Os cortes aparecem depois do processamento.", "Nenhum corte nesta pregação." | Protótipo `cortesPanel` |
| Cor (L9) | por índice na lista (`COLORS` do protótipo), a mesma no card e na camada; descartado marcado com `data-discarded` | Protótipo `cutColor` |
| Clique (L10) | um clique no card abre (spec e feature 1.1.e); diverge do protótipo (selecionar/expandir + duplo clique, grupo "Descartados (N)"), sem zoom no corte | Spec prevalece |
| Menu (L11) | `button` "Mais ações" com `aria-haspopup="menu"`/`aria-expanded`, `role="menu"` com `menuitem`; Escape e clique fora fecham; um menu aberto por vez | Acessibilidade |
| Documentação (L12) | `CHANGELOG.md`, `docs/architecture/README.md`, `docs/cli.md` §8.1, `docs/api.md` | Pendência de API do L1 resolvida neste item |

## Ordem de implementação
- [x] **Passo 1 — Painel e cards** — lista, estados, menu, erro da sugestão.
- [x] **Passo 2 — Abrir, descartar, restaurar** — transições e navegação.
- [x] **Passo 3 — Camadas na timeline** — `start`/`end` em `cut list` (core, CLI, API) e faixas somente leitura.
- [x] **Passo 4 — Documentação** — CHANGELOG, arquitetura, `docs/cli.md` §8.1 e `docs/api.md`.

## Verificação
- [x] Cards com título, texto, duração e estado; descartados por último.
- [x] Abrir marca escolhido e navega; menu descarta e restaura.
- [x] Camadas na timeline; mensagem de `suggestion_error`.
- [x] typecheck, lint, testes, build limpos.
