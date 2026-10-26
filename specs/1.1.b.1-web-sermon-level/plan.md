# Plan: Nível 2 — prévia 16:9, timeline, delimitar e processar

**Issue**: 1.1.b.1 (web) · **Feature**: specs/1.1.b.1-web-sermon-level · **Data**: 2026-10-26

## Resumo
Tela da pregação com player (YouTube IFrame antes do processamento; `<video>` do arquivo
processado depois), timeline com o clipe e bordas arrastáveis, atalhos I/O, salvamento
automático das bordas, Processar/Reprocessar com SSE.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

## Contexto de código
| Situação | Path |
|---|---|
| Criar | `apps/web/src/features/sermon/SermonPage.tsx`, `Timeline.tsx`, `ClipEdges.tsx`, `Player.tsx` (porta `PlayerLike` com YouTube e `<video>`), `ProcessButton.tsx`, `useTaskEvents.ts` (EventSource fecha no fim) |
| Criar | testes Vitest dos componentes (arraste por eventos de ponteiro, teclado I/O, SSE dublê) |
| Criar | `apps/web/src/test/fakeEventSource.ts` (dublê de `EventSource`), `apps/web/src/test/fakePlayers.ts` (dublê da porta `PlayerLike`), `docs/adr/0023-*.md` |
| Alterar | `apps/web/src/app/routes.tsx` (só o `element` de `/sermons/:id`), `apps/web/src/api/types.ts` (`SermonShown`, `TaskLaunched`), `apps/web/src/api/client.ts` (`showSermon`, `trimSermon` com `PATCH`, `processSermon`), `apps/web/src/test/fixtures.ts`, `apps/web/src/test/renderRoute.tsx`, `apps/web/src/test-setup.ts`, `apps/web/src/ui/app.css`, `docs/architecture/README.md`, `docs/adr/README.md`, `README.md`, `CHANGELOG.md` |

## Comandos de verificação
| Componente | Um arquivo | Suíte | Estática |
|---|---|---|---|
| `apps/web` | `npm --prefix apps/web test -- <arquivo>` | `npm --prefix apps/web test` | `npm --prefix apps/web run typecheck && npm --prefix apps/web run lint && npm --prefix apps/web run build` |

## Decisões técnicas
| Decisão | Escolha | Justificativa |
|---|---|---|
| Player | interface `PlayerLike` (tempo atual, seek, play/pause); implementações YouTube IFrame e `<video>` | Testável com dublê |
| Salvamento | `PATCH` imediato ao soltar a borda; debounce de 500 ms só para I/O; "Salvo" ao confirmar (QA L10) | Soltar já é um evento único |
| Erro no salvamento | motivo da API junto à timeline, sem "Salvo", borda volta ao último valor salvo (QA L11) | Requisito geral: valor inválido não é salvo e mostra o motivo |
| Progresso | `EventSource` em `/api/tasks/{id}/events`, fechado no `done`/`failed` e ao desmontar; só no botão; a barra de status continua com a consulta de 3 s (QA L8) | ADR-0020, ADR-0022 |
| Vídeo processado | rota `GET /api/sermons/{id}/video` já existente | Sem rota nova |
| Tipos e cliente | `SermonShown` (corpo de `sermon show`) em `types.ts`; `client.ts` com `showSermon`, `trimSermon` (`PATCH`) e `processSermon` (QA L1) | O `Sermon` da lista fica como está |
| Rota e carga | troca só o `element` de `/sermons/:id` por `SermonPage`, que carrega o corpo completo com um `useResource` próprio e chama `reload` após `done`/`failed` (QA L2) | A trilha continua buscando só o título |
| Reprocessar | aparece numa pregação `processed` depois de um `PATCH` 200 nesta sessão; some ao recarregar a página (QA L3) | A API não diz se as bordas mudaram; pendência de API no roadmap |
| Live no ar | `live_finished: false` mostra aviso sem travar; indisponível com o motivo só depois do 409 `live_not_finished` (QA L4) | `live_finished` só é atualizado pelo próprio `process` |
| Embed do YouTube | ADR-0023: `youtube-nocookie.com`, IFrame API carregada só no nível 2 quando a prévia precisa da live; carregador atrás da porta (QA L5) | ADR-0022 não permitia recurso de outro host |
| Tempo no `<video>` | a implementação `<video>` do `PlayerLike` converte tempo da live em tempo do vídeo (`t − sermon_start`); fora de `[sermon_start, sermon_end]`, a prévia usa o YouTube (QA L6) | O vídeo processado começa em `sermon_start` |
| Fim do processamento | o critério passa a ser "recarrega como processada"; a lista de cortes é do item 23 (QA L7) | Fora de escopo |
| Tarefa em andamento e falha | abrir uma pregação `processing` com `last_task` `running` abre o fluxo por `last_task.id`; `failed` mostra o motivo e volta a Processar (1.1.c.3, QA L9) | Recarregar a página não perde o progresso |
| Timeline | régua em tempo da live, faixa "Vídeo" com a live esmaecida atrás e o clipe entre as bordas, cursor; sem miniaturas nem forma de onda (decisão do plano de QA) | A API não as serve |
| Conferência do `<video>` | manual, registrada no tdd.md (QA L12) | O seek depende de `Range`, que a suíte não prova |

## Ordem de implementação
- [x] **Passo 1 — Player e timeline** — player com porta, timeline com clipe e cursor.
- [x] **Passo 2 — Bordas** — arraste com quadro da borda, I/O, esmaecido, autosave, mínimo de 1 min.
- [x] **Passo 3 — Processar/Reprocessar** — botão, progresso por SSE, avisos (ocupado, live no ar, perda de edições), tarefa em andamento por `last_task` e falha.
- [x] **Passo 4 — Documentação** — CHANGELOG, arquitetura, ADR-0023 com entrada no índice, README.

## Verificação
- [x] Arrastar e I/O mudam as bordas e salvam sozinhos.
- [x] Processar mostra progresso e termina com a pregação recarregada como processada.
- [x] Reprocessar aparece ao mudar bordas de pregação processada.
- [x] Ocupado e live no ar com motivo; typecheck, lint, testes, build limpos.
