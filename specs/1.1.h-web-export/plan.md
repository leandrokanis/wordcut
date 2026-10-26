# Plan: Caixa de exportação e downloads na web

**Issue**: 1.1.h (web) · **Feature**: specs/1.1.h-web-export · **Data**: 2026-10-26

## Resumo
Diálogo com as opções de `RenderOptions`, estimativa com debounce, exportação com SSE e lista
de exportações com download.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

## Contexto de código
| Situação | Path |
|---|---|
| Criar | `apps/web/src/features/cut/ExportDialog.tsx`, `RendersList.tsx`, `useEstimate.ts`, `ExportButton.tsx` (botão, menu e acompanhamento da tarefa), `exportSummary.ts` (resumo das opções, função pura), `useCutExports.ts` (opções e lista do corte), `src/ui/Choice.tsx` (controle segmentado, extraído do `CaptionTab`) |
| Alterar | `CutPage.tsx` (barra do nível com o botão Exportar, dentro do `CutLevel`), `useCaptionStyle.ts` e `useWordFixes.ts` (gravação pendente; legenda gravada pelo `POST`), `ProcessButton.tsx` e `status/StatusBar.tsx` (`otherWork` compartilhado), `CaptionTab.tsx` (usa `Choice`), `src/ui/format.ts` (data e hora), `src/api/types.ts` (`RenderOptions`, `Render` sem `path`, `Cut.render_options`/`renders`), `src/api/client.ts` (`estimateRender`, `startRender`, `listRenders`, `renderFileUrl`), `src/ui/app.css` (menu e caixa do protótipo), `src/test/fakeApi.ts` (expõe `signal`), `src/test/fixtures.ts` e `src/test/cutLevel.ts` (abre a caixa), testes, CHANGELOG, `docs/architecture/README.md` (web por feature e §5.3) |

## Comandos de verificação
| Componente | Um arquivo | Suíte | Estática |
|---|---|---|---|
| `apps/web` | `npm --prefix apps/web test -- <arquivo>` | `npm --prefix apps/web test` | `npm --prefix apps/web run typecheck && npm --prefix apps/web run lint && npm --prefix apps/web run build` |

## Decisões técnicas
| Decisão | Escolha | Justificativa |
|---|---|---|
| Estimativa | `GET` com debounce 300 ms; requisição anterior cancelada (`AbortController`) | Sem corrida de respostas |
| Opções | grupos e rótulos do protótipo; padrões vindos do corte | Fidelidade |
| Download | link `<a href download>` para a rota de arquivo | Simples |
| L1 — Escopo | `types.ts`, `client.ts` e `test/fixtures.ts` entram no escopo | `Cut` não trazia `render_options`/`renders` |
| L2 — Resumo | função pura `exportSummary(options)`, testada por tabela: resolução, com/sem legenda e o que foge do padrão | A API devolve objeto (`xSummary` do protótipo) |
| L3 — Botão | botão Exportar no `CutLevel`, como o `ProcessButton`, reaproveitando `useTaskEvents`; retoma a tarefa por `running_tasks` (`kind: "render"`, `cut_id`); não exporta de novo com o lock em `cut {id}` | `.top` é do `Layout` |
| L4 — Legenda | o controle parte de `caption.style.enabled`; aceito o `POST`, a aba Legenda e a prévia refletem o valor enviado | O `POST` muda o mesmo estado de `cut caption` |
| L5 — Cancelamento | `fakeApi` expõe `signal`; testes provam `aborted` e a corrida com resposta segurada | Prova do `AbortController` |
| L6 — Depois do `done` | recarrega o corte (`render_options`) e a lista (`GET /api/cuts/{id}/renders`) | A caixa reabre com as opções usadas |
| L7 — Autosave | Exportar da caixa desabilitado, com "Salvando…", enquanto houver gravação pendente da legenda ou da grafia | Não renderizar estado anterior |
| L8 — Lista | no nível 3, a lista fica no menu do botão Exportar, como no protótipo | Fidelidade |

## Ordem de implementação
- [x] **Passo 1 — Caixa e estimativa**.
- [x] **Passo 2 — Exportar com progresso**.
- [x] **Passo 3 — Lista e download**.
- [x] **Passo 4 — Documentação**.

## Fora de escopo
- L8: "Exportado" e "Baixar exportação" no card do nível 2 (protótipo). Vai para o Registro do
  `specs/roadmap.md`, na linha do item 25, quando ela existir.
- L9: a cor da estimativa fora da meta (verde em 40–75 s, amarelo fora).

## Verificação
- [x] Caixa abre com as opções do corte; estimativa atualiza.
- [x] Exportar mostra progresso e registra a exportação; ocupado e falha com mensagem.
- [x] Baixar entrega o arquivo.
- [x] typecheck, lint, testes, build limpos.
