# ADR-0021: Rotas de cortes e de administração na API

**Status**: Aceita · **Data**: 2026-10-26

Complementa a [ADR-0020](0020-rotas-e-progresso-por-sse-na-api.md) e a
[ADR-0019](0019-identidade-e-erros-na-api.md), que continuam valendo. Esta ADR diz onde a API
exige a identidade, o que as respostas de exportação deixam de fora, por onde chegam o
e-mail de um membro e os segredos, e como a API recusa um campo que a rota não declara (item
20b do roadmap).

## Contexto

O item 20b leva à web as operações de cortes, exportações, configurações, critérios, presets
e equipe. No item 20a, cada router declarava a identidade no próprio `APIRouter`, e a
varredura que prova o 401 lia o esquema OpenAPI. Assim, uma rota com
`include_in_schema=False` ou um router incluído sem a identidade escapava da prova.

A camada de serviço devolve cada exportação com `path`, o caminho absoluto do arquivo na
pasta de dados. A CLI roda no servidor e usa esse caminho. Na web, ele é estrutura interna.
Os proxies (uvicorn, nginx e Cloudflare) registram o caminho de toda requisição, e o e-mail
de um membro é dado pessoal (LGPD). A pasta de segredos é montada só para leitura na `api`
([ADR-0003](0003-docker-compose.md)). Por fim, um corpo com campo desconhecido, quando
recusado pelo pydantic, põe o nome digitado em `details.argument`, e a
[ADR-0015](0015-erro-de-uso-nao-repete-valor-digitado.md) proíbe repetir texto digitado.

## Decisão

- **Identidade num lugar só**: `wordcut_api.routes.ROUTERS` lista todos os routers de
  negócio. O `create_app` inclui cada um num laço com `dependencies=[Depends(current_member)]`,
  e nenhum router declara a identidade por conta própria. Os routers de configurações,
  critérios, presets e equipe declaram `require("admin")` no próprio `APIRouter`, leitura
  incluída. A prova das permissões lê as rotas de `ROUTERS`, não o OpenAPI. Um teste exige
  que o app não inclua router fora dessa lista.
- **Sem caminho local**: toda exportação que a API devolve sai sem `path`: no corte, nas
  transições, na lista e no detalhe. A web baixa o arquivo por
  `GET /api/renders/{id}/file`, com o nome legível.
- **E-mail só no corpo**: incluir, trocar o papel e remover um membro são `POST /api/members`,
  `POST /api/members/set-role` e `POST /api/members/remove`, com o e-mail no corpo. Nenhuma
  rota tem o e-mail no caminho.
- **Segredos pelo corpo**: `PUT /api/settings/llm-key` e `PUT /api/settings/youtube-cookies`
  recebem `{"value"}` e respondem as configurações, com a chave mascarada e os cookies só
  como presentes. O valor nunca volta em resposta, erro ou log. Um erro do valor nomeia
  `value` em `details.argument`. A montagem `/config:ro` do Compose não muda: lá, as duas
  rotas respondem 409 `config_not_writable`, sem caminho na mensagem nem em `details` (a CLI,
  no host, pode mostrá-lo), e o segredo se grava pela CLI no host.
- **Corpos estritos**: todo corpo recusa campo que não declara, número e chave como texto
  (`StrictInt`, `StrictBool`) e `null` num campo opcional. Só os campos enviados chegam ao
  serviço. Um campo de escolha é texto, para o erro vir do serviço com `details.choices`.
  A entrada tem o formato e os nomes da saída. Um `PATCH` de legenda sem nenhum campo dá
  400 e não grava nada.
- **Campo desconhecido**: um campo do corpo ou um parâmetro da query que a rota não declara
  dá 400 `invalid_argument` com a mensagem "Argumento não reconhecido; veja docs/api.md.",
  sem `details` e sem o nome enviado.

## Consequências

- Uma rota nova fica coberta pela identidade ao entrar num router de `ROUTERS`, e a prova
  das permissões quebra se ela ficar sem linha na tabela de papéis.
- A web nunca vê a estrutura de pastas do servidor. O agente que precisa do arquivo local
  usa a CLI.
- Os logs de acesso não guardam e-mail. As rotas de equipe fogem do CRUD por caminho.
- Pelo Compose, a administração dos segredos pela web só funciona se a montagem mudar, o que
  pede outra ADR. Até lá, a tela de configurações mostra o 409.
- Um cliente que manda um campo a mais recebe 400 em vez de vê-lo ignorado.
