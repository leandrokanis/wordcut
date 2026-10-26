# ADR-0019: Identidade e erros na API

**Status**: Aceita · **Data**: 2026-10-26

Complementa a [ADR-0009](0009-identidade-pelo-cloudflare-access.md) e a
[ADR-0012](0012-contrato-da-cli.md), que continuam valendo. Esta ADR diz como a API verifica
o token do Access, quando o modo de desenvolvimento vale e como um `WordcutError` vira
resposta HTTP (item 1.2.a.2).

## Contexto

A ADR-0009 decide que a API confia no e-mail verificado pelo Cloudflare Access e que uma
variável define o e-mail fixo em desenvolvimento, sem dizer o que se verifica no token, o
que acontece com uma configuração incompleta nem como os erros chegam ao navegador. A
ADR-0012 dá o objeto de erro e a saída de cada código para a CLI; a API precisa de um status
HTTP para cada um, sem perder o mesmo objeto.

## Decisão

- **Configuração** por ambiente: `WORDCUT_ACCESS_TEAM_DOMAIN` (o host do time do Access),
  `WORDCUT_ACCESS_AUD` (a tag AUD da aplicação) e `WORDCUT_DEV_EMAIL`. Valor vazio conta
  como ausente. Só uma das duas variáveis do Access faz a API recusar subir
  (`invalid_argument`), em vez de cair no modo de desenvolvimento ou aceitar token sem
  conferir o `aud`.
- **Token**: o e-mail sai só do JWT de `Cf-Access-Jwt-Assertion`, nunca do cabeçalho
  `Cf-Access-Authenticated-User-Email`. O JWT DEVE ser RS256, assinado pela chave do `kid`
  entre as chaves do time (`https://<time>/cdn-cgi/access/certs`), com `aud` igual à tag
  configurada, `iss` igual a `https://<time>`, `exp` presente e no futuro e o claim
  `email`. Qualquer falha dá `unauthenticated`, sem o token na mensagem, nos `details` ou
  no log.
- **Chaves**: ficam em cache por 10 minutos; um `kid` desconhecido busca de novo uma vez,
  para seguir a rotação. A busca real passa por `refuse_when_forbidden`
  ([ADR-0017](0017-testes-sem-rede-real.md)); falha ao buscar, ou resposta sem chave
  utilizável, dá `network_error`. As chaves entram por uma porta (`KeySource`), que os
  testes trocam por chaves geradas no próprio teste.
- **Papel**: `service.members.role_of(email)` a cada requisição, numa conexão aberta e
  fechada na própria requisição. E-mail fora da equipe dá `forbidden`, sem o e-mail. Uma rota
  declara o papel mínimo com `require(papel)`; o administrador passa em todas.
- **Modo de desenvolvimento**: `WORDCUT_DEV_EMAIL` vale só sem o Access configurado, gera um
  aviso no log ao subir e passa por `role_of` como qualquer e-mail. Sem Access e sem a
  variável, ninguém é identificado: toda rota protegida dá `unauthenticated`. O Compose
  nunca repassa a variável.
- **Erros**: o corpo é `{"error": <objeto da CLI>}`. O status segue a saída do código:
  saída 1 → 500, 2 → 400, 3 → 404, 4 → 409, 5 → 409, 6 → 502; `unauthenticated` → 401 e
  `forbidden` → 403, os dois com saída 1 na tabela única. Exceção que não é `WordcutError`
  dá 500 `internal_error`, sem o texto da exceção.
- `GET /api/health` não exige identificação nem abre o banco.

## Consequências

- Um código de erro novo ganha status pelo código de saída, sem tabela à parte na API; só
  um código que precise de status diferente do da sua saída entra na exceção da API.
- Uma configuração do Access pela metade aparece ao subir, não como 401 em toda rota.
- Um token forjado com outro algoritmo, outro emissor ou outro público não passa, mesmo
  assinado por uma chave válida de outro time.
- A CLI nunca produz `unauthenticated` nem `forbidden`; a saída 1 dos dois existe só porque
  a tabela de códigos é única.
