# Spec: Identidade pelo Cloudflare Access e papéis na API

**Issue**: 1.2.a.2 (sem rastreador; o ID é o código do requisito)
**Requisito**: docs/requirements/features/1.2.a-team-and-roles.md §1.2.a.2 e tabela de
permissões; ADR-0008, ADR-0009; constituição §VI
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

A equipe entra pelo navegador com um código enviado ao e-mail, pelo Cloudflare Access; a
aplicação não tem login próprio. A API confia só no token assinado que o Access envia,
descobre o e-mail verificado, procura o papel na lista de membros e aplica a tabela de
permissões da 1.2.a a cada rota.

---

## Cenários de aceite

**Cenário: membro identificado**
- **Dado** um membro `assistant` liberado e um token válido do Access com o e-mail dele
- **Quando** o navegador chama `GET /api/me`
- **Então** a resposta é `200 {"email": …, "role": "assistant"}`

**Cenário: sem token ou token inválido**
- **Dado** uma requisição sem o cabeçalho do Access, com assinatura errada, expirado ou de
  outro público (`aud`)
- **Quando** ela chega a qualquer rota (menos `/api/health`)
- **Então** a resposta é `401` com o objeto de erro e código `unauthenticated`

**Cenário: e-mail não liberado**
- **Dado** um token válido de um e-mail que não está na equipe
- **Quando** ele chama a API
- **Então** a resposta é `403` com código `forbidden`

**Cenário: permissão por papel**
- **Dado** um assistente identificado
- **Quando** ele chama uma rota marcada como de administrador
- **Então** a resposta é `403` com código `forbidden`; um administrador recebe a resposta
  normal

### Casos de borda

- As chaves públicas do Access são buscadas e guardadas em cache; nos testes, nunca há rede
  (ADR-0017) e as chaves vêm de um dublê.
- Modo de desenvolvimento: `WORDCUT_DEV_EMAIL` define o e-mail fixo, só quando
  `WORDCUT_ACCESS_TEAM_DOMAIN` não está configurado; com o Access configurado, a variável é
  ignorada (ADR-0009).
- Sem configuração do Access e sem `WORDCUT_DEV_EMAIL`, toda rota protegida dá `401`.
- Nenhum token aparece em log ou erro.

---

## Requisitos funcionais

- **FR-001**: A API DEVE validar o JWT de `Cf-Access-Jwt-Assertion` (RS256) contra as chaves
  públicas do time configurado e o `aud` configurado.
- **FR-002**: O papel DEVE vir de `members.role_of(email)` (item 17).
- **FR-003**: Cada rota DEVE declarar o papel mínimo; a tabela da 1.2.a DEVE ser respeitada.
- **FR-004**: `GET /api/me` DEVE devolver e-mail e papel.
- **FR-005**: Os erros DEVEM usar o mesmo objeto de erro da CLI (ADR-0004) com status HTTP
  coerente.

---

## Escopo

### Componentes em escopo
- `apps/api/src/wordcut_api/` — configuração, identidade, permissões, mapeamento de erros,
  `/api/me`.
- `compose.yaml` — variáveis do Access para a `api`.

### Fora de escopo
- As rotas de negócio (itens 20a e 20b).
- Configurar o Cloudflare Tunnel e o Access (administrador; pendência do domínio).

### Integrações externas
- Cloudflare Access (chaves públicas; dublê nos testes).
