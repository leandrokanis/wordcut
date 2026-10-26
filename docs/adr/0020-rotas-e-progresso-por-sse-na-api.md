# ADR-0020: Rotas e progresso por SSE na API

**Status**: Aceita · **Data**: 2026-10-26

Complementa a [ADR-0019](0019-identidade-e-erros-na-api.md), que continua valendo, e a
[ADR-0015](0015-erro-de-uso-nao-repete-valor-digitado.md), que passa a valer também para a
API. Esta ADR diz como as rotas de negócio usam o banco, como a web acompanha uma tarefa,
como a API recusa uma requisição malformada e quando o esquema OpenAPI é servido (item 20a
do roadmap).

## Contexto

A web precisa das operações da CLI sobre pregações e tarefas e do progresso em tempo real
de uma tarefa que roda em outro processo, às vezes em outro contêiner
([ADR-0007](0007-tarefas-em-processo-destacado.md)). O progresso já fica no SQLite, que a
CLI lê por polling em `task wait`. O FastAPI responde por conta própria a uma requisição que
não valida, com 422 e um corpo que repete o valor enviado, e serve `/docs` e
`/openapi.json` sem identificação.

## Decisão

- **Conexão**: cada rota abre e fecha a conexão SQLite no próprio corpo. Nenhuma dependência
  do FastAPI entrega conexão, porque a dependência e a rota podem rodar em threads
  diferentes e a conexão fica presa à thread que a abriu.
- **Portas**: a rota pega o YouTube em `wordcut_api.deps.live_source()` na hora da
  requisição, como a CLI. Os testes da API trocam essa porta por um dublê que falha, numa
  fixture automática ([ADR-0017](0017-testes-sem-rede-real.md)).
- **Corpos**: as respostas são os `dict` da camada de serviço no formato do JSON da CLI. O
  `PATCH` da pregação não traz `needs_reprocess`, que a CLI transforma em aviso. Uma rota que
  lança tarefa responde 202 com `service.tasks.launched_task`.
- **Progresso**: `GET /api/tasks/{id}/events` é um fluxo SSE que lê a tarefa no banco a cada
  0,5 s (`show_task`, com a reconciliação de tarefa órfã), sem broker. O `data` de todo
  evento é a tarefa como `show_task` a dá. `progress` sai só quando muda o par
  `progress`/`progress_message`, como em `task wait`; `done` ou `failed` encerram o fluxo.
  Sem evento por 15 s, sai o comentário `: ping`. Tarefa inexistente dá 404 em JSON antes do
  fluxo. O gerador é assíncrono (`asyncio.sleep`, `show_task` no pool de threads), para que
  um cliente esperando o próximo polling não segure uma thread do pool das rotas síncronas.
  O cliente fecha o `EventSource` no evento final.
- **Requisição malformada**: um corpo, parâmetro de caminho ou filtro que não valida dá 400
  `invalid_argument`, com `details.argument` e, num filtro com escolhas (`Literal`),
  `details.choices`, nas mensagens da CLI. O valor enviado e o texto do pydantic nunca saem.
  Uma rota inexistente dá 404 `not_found`.
- **Filtros**: `status` e `kind` só aceitam as escolhas da CLI; o tipo interno `diagnostic`
  não é uma delas.
- **OpenAPI**: o esquema e a página dele ficam em `/api/openapi.json` e `/api/docs` só com a
  identificação de desenvolvimento (`WORDCUT_DEV_EMAIL`); com o Access, ou sem nenhuma
  identificação, não são servidos.

## Consequências

- A web e a CLI veem o mesmo JSON e os mesmos códigos de erro; a web decide pelo `code`.
- O progresso chega com até 0,5 s de atraso e custa uma leitura do banco por cliente a cada
  polling. Funciona entre contêineres sem processo extra.
- Uma tarefa nunca depende do cliente: fechar o fluxo só para de ler o banco.
- O proxy da web não pode guardar o fluxo em buffer (`proxy_buffering off` no
  `apps/web/nginx.conf`); o `: ping` fica abaixo do tempo limite de leitura do nginx.
- O esquema da API não aparece em produção; quem integra lê [docs/api.md](../api.md).
