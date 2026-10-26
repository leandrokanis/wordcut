# Plan: Esqueleto da interface web, lista de pregações e Nova pregação

**Issue**: web-shell
**Feature**: specs/web-shell
**Data**: 2026-10-26

---

## Resumo

React + Vite + TS com React Router, cliente HTTP tipado sobre `/api`, layout com caminho no
topo e barra de status no rodapé, nível 1 (lista + diálogo) e página de configurações vazia,
com os tokens visuais do protótipo.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Contexto de código

| Situação | Path |
|---|---|
| Alterar | `apps/web/package.json` — `react-router-dom` |
| Criar | `apps/web/src/api/client.ts` (fetch tipado, objeto de erro), `api/types.ts` (tipos dos corpos da API) |
| Criar | `apps/web/src/app/Layout.tsx` (topo com caminho, conteúdo, rodapé), `app/routes.tsx` |
| Criar | `apps/web/src/features/sermons/SermonList.tsx`, `NewSermonDialog.tsx` |
| Criar | `apps/web/src/features/status/StatusBar.tsx` (consulta `/api/status` a cada 3 s) |
| Criar | `apps/web/src/features/settings/SettingsPage.tsx` (navegação lateral e seções vazias) |
| Criar | `apps/web/src/ui/` — `Saved.tsx` (indicador), `tokens.css` (cores e tipografia do protótipo) |
| Remover | `apps/web/src/api.ts`, `apps/web/src/App.test.tsx` (L11) |
| Criar | `docs/adr/0022-arquitetura-do-cliente-web.md` (L20) |
| Alterar | `apps/web/src/App.tsx`, `main.tsx` |
| Criar | testes Vitest + Testing Library por componente, com `fetch` dublê |
| Alterar | `docs/architecture/README.md` §4, `CHANGELOG.md`, `docs/adr/README.md`, `README.md` |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| `apps/web` | `npm --prefix apps/web test -- <arquivo>` | `npm --prefix apps/web test` | `npm --prefix apps/web run typecheck && npm --prefix apps/web run lint && npm --prefix apps/web run build` |
| Python (regressão) | — | `uv run pytest -q` | `uv run ruff check . && uv run mypy` |

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Roteamento | React Router em modo declarativo (`BrowserRouter` + `useRoutes` sobre a tabela `routes`); nginx já faz fallback para `index.html`. Revisto na rodada 1: era `createBrowserRouter` | Padrão; URLs navegáveis. Sem loaders, o data router não traz ganho, e cada navegação dele cria um `Request` com o `AbortSignal` do jsdom, que o `Request` do Node recusa nos testes |
| Estado do servidor | `fetch` próprio com hooks simples (`useResource`), sem biblioteca de cache | Escopo pequeno, §V |
| Estilo | CSS com variáveis do protótipo (`:root`), sem framework de CSS | Fidelidade ao protótipo |
| Erros | componente único que lê `{"error": {code, message}}` | Mesmo contrato da CLI/API |
| Status | polling de 3 s em `/api/status` | Simples; SSE fica para a tela que acompanha tarefa |
| Duração e corpos (L1) | Dois tipos: `SermonListItem` (com `duration` anulável e `cut_counts`) e `SermonCreated` (`_sermon` + `created`); lista mostra `duration` ou "A delimitar"; criação mostra `live_duration` | Corpos reais de `service/sermons.py` |
| Link inválido (L2) | Qualquer `invalid_argument` (`link`, `url` ou sem `details`) e `youtube_error` do `POST /api/sermons` aparecem junto ao campo | O serviço usa `details.argument: "link"` |
| `created: false` (L3) | Fecha o diálogo, recarrega a lista sem duplicar e avisa que a pregação já existia | Mesmo vídeo devolve a pregação existente |
| Live no ar (L4) | Cria e mostra o aviso "A live ainda não terminou" (não é erro) | API + spec; o 409 só sai no processamento |
| Papel (L5) | `GET /api/me` no cliente; identidade carregada antes das telas; `/settings` recusa o assistente; sem o "Ver como" do protótipo | Papel real, não simulado |
| 403 de papel × equipe (L6) | Tela de bloqueio só pelo resultado de `/api/me`; 403 em rota de administração vira mensagem local | ADR-0019 usa 403 para os dois |
| `/api/status` (L7) | Sem "quem"; "livre" segue `lock.held`; `suggest` sem trava aparece como informação à parte | Formato de `service/status.py` |
| SSE (L8) | FR-004 cumprido só com o polling de 3 s; os eventos SSE ficam para o item 22 (registrado na spec) | Item 22 é a tela que acompanha a tarefa |
| Polling (L9) | Para ao desmontar; continua após erro e mostra "indisponível" | Testável com fake timers |
| API fora do ar (L10) | Cliente normaliza `fetch` rejeitado (`network_error`) e corpo não-JSON (`unavailable`) | Mensagem clara, nunca exceção crua |
| Esqueleto (L11) | `src/api.ts` e `App.test.tsx` removidos; "API indisponível" coberto pelos testes novos | Sem código morto |
| "Salvo" (L12) | `ui/Saved.tsx` entra no passo 2, com teste (`role="status"`, `aria-live="polite"`, some em 1,5 s) | FR-005 |
| Miniatura (L13) | Sem miniatura | Requisito "sem prévia"; API sem rota |
| Confirmação do link (L14) | Envio por submit do formulário (Enter ou botão "Carregar"), sem envio no `paste` | Spec: "cola o link e confirma" |
| Depois de criar (L15) | Fecha e recarrega a lista; a ida ao nível 2 fica para o item 22 | Spec |
| Títulos no caminho (L16) | `GET /api/sermons/{id}`; `GET /api/cuts/{id}` → `sermon_id` → `GET /api/sermons/{sermon_id}`; páginas-esboço nas rotas; 404 mostra "não encontrada" | Níveis 2 e 3 fora de escopo |
| 390 px (L17) | Verificação em navegador sem interface (Playwright como biblioteca) registrada no `tdd.md`, mais revisão do CSS | jsdom não mede layout |
| Fontes (L18) | Geist e Geist Mono pelo npm (`@fontsource/geist`, `@fontsource/geist-mono`), empacotadas no build; sem CDN | Nenhuma chamada a terceiros |
| Rótulos de estado (L19) | "A delimitar" (`created`), "Delimitada" (`trimmed`), "Processando N%" (`processing`), "Pronta" (`processed`), "Falhou" (`failed`), tons `warn`/`accent`/`ok`/`danger` | Tom do protótipo |
| Documentação (L20) | ADR-0022 "Arquitetura do cliente web" (React Router, cliente HTTP próprio, CSS com tokens do protótipo), com entrada no índice e no README | CLAUDE.md: decisão de arquitetura vira ADR |

---

## Ordem de implementação

- [x] **Passo 1 — Cliente e tipos** — `client.ts`, `types.ts`, tratamento de erro e de 401/403,
  API fora do ar, `GET /api/me`.
- [x] **Passo 2 — Layout e rotas** — caminho no topo, rodapé, rotas, tokens visuais, 390 px,
  indicador "Salvo" (L12); `App` passa ao roteador e `src/api.ts` e `App.test.tsx` saem (L11).
- [x] **Passo 3 — Nível 1** — lista, estado vazio, diálogo "Nova pregação" com aviso de live no ar.
- [x] **Passo 4 — Barra de status e configurações vazias** — status atualizado; página de
  configurações só para admin.
- [x] **Passo 5 — Documentação** — arquitetura §4, CHANGELOG, ADR-0022 com índice e README.

---

## Verificação

- [x] Lista renderiza os dados da API; vazio mostra a ação.
- [x] Diálogo cria a pregação; aviso de live no ar; erro junto ao campo.
- [x] Caminho navega entre níveis; "Nova pregação" só no nível 1.
- [x] Barra de status mostra livre/ocupado e atualiza.
- [x] Configurações só para admin; 401/403 com tela própria.
- [x] typecheck, lint, testes e build limpos; suíte Python intacta.
