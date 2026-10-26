# ADR-0022: Arquitetura do cliente web

**Status**: Aceita · **Data**: 2026-10-26

Complementa a [ADR-0008](0008-api-fastapi-e-web-separada.md) e a
[ADR-0019](0019-identidade-e-erros-na-api.md), que continuam valendo. Esta ADR diz como a
web navega, fala com a API, sabe quem a usa e se veste (item 21 do roadmap).

## Contexto

A web (`apps/web`, React + Vite + TypeScript) era um esqueleto que mostrava o estado da API.
O item 21 traz a navegação em três níveis (pregações, pregação, corte), a tela inteira das
configurações, a barra de status e a lista com o diálogo "Nova pregação". As URLs precisam
ser navegáveis, e o nginx já devolve `index.html` em qualquer caminho fora de `/api`.

A API responde erros como `{"error": {"code", "message", "details"?}}`, com o status da
ADR-0019. Na frente dela, o nginx devolve página HTML num 502, e o navegador rejeita o
`fetch` quando a API está fora do ar. O papel do usuário vem de `GET /api/me`. O protótipo
(`docs/prototype/wordcut.html`) define cores, tipografia (Geist e Geist Mono) e componentes,
e carrega as fontes do Google Fonts. Nenhuma tela deste item precisa de cache de dados entre
telas.

## Decisão

- **Roteamento pelo React Router**, em modo declarativo: `BrowserRouter` e `useRoutes` sobre
  uma tabela única (`app/routes.tsx`), que os testes montam num `MemoryRouter`. Rotas: `/`,
  `/sermons/:id`, `/cuts/:id` e `/settings`. Sem loaders nem data router.
- **Cliente HTTP próprio** sobre `fetch` (`api/client.ts`), sem biblioteca de cache. Toda
  falha vira `ApiError` com `status`, `code`, `message` e `details`: o objeto de erro da API;
  `unavailable` para corpo que não é o JSON da API (o 502 do nginx); `network_error` para
  `fetch` rejeitado. O `POST` manda só os campos declarados, como JSON. Os tipos dos corpos
  ficam em `api/types.ts`, com os nomes da API. As telas carregam pelo gancho
  `useResource`.
- **Identidade antes das telas**: `IdentityGate` chama `GET /api/me` e só então mostra a
  aplicação. 401 e 403 dão uma tela própria, sem pedir dado nenhum. O papel decide o que
  aparece, e a rota `/settings` também recusa o assistente.
- **Estado da máquina por consulta periódica**: `MachineStatusProvider` consulta
  `GET /api/status` a cada 3 s para a barra de status e para o progresso na lista. Os
  eventos SSE da tarefa ficam para a tela que acompanha a tarefa (item 22).
- **CSS com os tokens do protótipo**, sem framework de CSS: `ui/tokens.css` repete o `:root`
  do protótipo (um teste compara os valores), e `ui/app.css` traz os componentes. As fontes
  Geist e Geist Mono vêm do npm (`@fontsource/geist`, `@fontsource/geist-mono`) e saem no
  build. Nenhum recurso vem de outro host.

## Consequências

- Uma URL abre direto o nível certo, e o caminho no topo busca os títulos na API.
- Uma tela nova trata erro com um só tipo, e a API fora do ar dá mensagem, não tela branca.
- A web não pede nada a terceiros: fonte, script e estilo saem do próprio contêiner.
- Sem cache, duas telas que mostram o mesmo dado o pedem duas vezes. Se isso pesar, outra
  ADR traz uma biblioteca de cache.
- O progresso na barra de status atrasa até 3 s. O acompanhamento fino de uma tarefa usa o
  SSE do item 22.
