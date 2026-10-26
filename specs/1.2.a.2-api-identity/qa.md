# QA — 1.2.a.2 — Identidade pelo Cloudflare Access e papéis na API

## Plano de QA — 2026-10-26

**baseline_commit**: afbe8e16606c94b897a70e46e4a7045f6e715687
**Componentes em escopo**: `apps/api` (`settings.py`, `identity.py`, `auth.py`, `errors.py`,
`app.py`, `pyproject.toml`, testes novos); `packages/core` (`errors.py`, só os dois códigos
novos); `compose.yaml`; documentação (`docs/architecture/README.md`, `docs/cli.md` §5.3,
`CHANGELOG.md`); `uv.lock` (efeito da dependência nova)
**Suítes que valem como prova**:

| Componente | Comando |
|---|---|
| API (passos 1–3) | `uv run pytest apps/api/tests -q` |
| Core (códigos novos) | `uv run pytest packages/core/tests/test_errors.py -q` |
| Monorepo inteiro (regressão) | `uv run pytest -q` |
| Checagem estática | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |
| Dependência travada | `uv lock --check` |
| Compose (passo 4) | `docker compose config` (só renderiza o arquivo; não sobe contêiner) |

**Fontes da barra**: `spec.md` e `plan.md` desta pasta; feature 1.2.a (tabela de
permissões); ADR-0004, ADR-0008, ADR-0009, ADR-0015, ADR-0017; constituição §VI;
`docs/cli.md` §5.2–5.3. Sem rastreador: os critérios saem do spec e da Verificação do plano.

**Regras da barra** (valem para todos os passos):

- Teste de comportamento pela interface pública: HTTP por `fastapi.testclient.TestClient`
  sobre `create_app(settings=…, keys=…)`, e `verify`/`AccessKeys` pela API pública do
  módulo. Teste que só inspeciona atributo interno não conta como prova.
- Tokens assinados nos testes com par RSA gerado no próprio teste (`cryptography`); nenhum
  JWT, chave ou e-mail real; e-mails fictícios do tipo `assistente@exemplo.org`.
- Nenhuma rede: a fixture `no_network` da raiz continua autouse; nenhum teste desliga
  `WORDCUT_FORBID_NETWORK`. Um teste que monte `AccessKeys` real sem dublê DEVE receber
  `network_error` da guarda, não uma resposta da Cloudflare.
- Banco: a API resolve o papel por `service.members.role_of` sobre o SQLite do
  `WORDCUT_HOME` (fixture `wordcut_home`); membros inseridos por `add_member`, não por SQL.
- `apps/api/tests/test_health.py` continua passando sem alteração.
- Mutação manual, desfeita na hora, nas linhas marcadas com 🧬 em `tdd.md`; mutação que
  sobrevive é achado (PARCIAL do passo).

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Erros HTTP | (a) `unauthenticated` e `forbidden` existem em `EXIT_CODES` com saída 1, e nenhum código existente mudou de saída. (b) Um `WordcutError` levantado numa rota vira a resposta com o status da tabela de Decisões técnicas — `invalid_argument` 400, `unauthenticated` 401, `forbidden` 403, `not_found` 404, `busy` 409, todo código de saída 5 → 409, todo código de saída 6 → 502, `internal_error` 500 — e corpo `{"error": <WordcutError.to_dict()>}`, idêntico ao da CLI (com `details` quando houver, sem `details` quando não houver). (c) Todo código de `EXIT_CODES` tem status definido (inclusive `interrupted` e `processing_error`); um código novo não cai num padrão silencioso. | `test_errors.py` do core ganha os dois códigos na tabela parametrizada. `apps/api/tests/test_errors_http.py`: app de `create_app` com rota de teste que levanta o erro, parametrizado sobre **todos** os itens de `EXIT_CODES` (status + corpo). 🧬 `unauthenticated`→403; saída 5→400; descartar `details` do corpo → todas vermelhas. |
| 2 — Verificação do token | (a) `verify(token)` devolve o e-mail de um JWT RS256 válido, assinado pela chave do `kid`, com o `aud` configurado e não expirado. (b) Recusa com `unauthenticated` (401): assinatura de outra chave, `exp` no passado, `aud` diferente, `kid` desconhecido mesmo após nova busca, token malformado, `alg` diferente de RS256 (`none` e HS256 com a chave pública como segredo), token sem claim `email`. (c) `AccessKeys` guarda as chaves em cache por 10 min (segunda verificação dentro da janela não busca de novo; depois da janela busca) e busca de novo quando aparece `kid` desconhecido (rotação). (d) `AccessKeys` real chama `refuse_when_forbidden` antes de qualquer rede: sob a suíte, dá `network_error` com `details.forbidden_by`. (e) Nenhuma mensagem de erro, `details` ou log contém o token. | `apps/api/tests/test_identity.py` contra `verify` e `AccessKeys`, com `KeySource` dublê e busca dublê que conta chamadas e relógio injetado (sem `sleep`). Log por `caplog`. 🧬 aceitar `algorithms=["RS256","HS256"]`/`none`; tirar `audience=`; `options={"verify_exp": False}`; cache que nunca expira; não buscar de novo em `kid` desconhecido; remover a chamada a `refuse_when_forbidden` → todas vermelhas. |
| 3 — Membro e papel | (a) `GET /api/me` com token válido de membro → 200 `{"email", "role"}` (assistant e admin). (b) Sem `Cf-Access-Jwt-Assertion`, ou com qualquer token recusado no passo 2 → 401 `unauthenticated`. (c) Token válido de e-mail fora da equipe → 403 `forbidden`, sem o e-mail no corpo nem no log (ADR-0015, LGPD). (d) `require("admin")`: assistente → 403 `forbidden`, admin → resposta normal da rota. (e) O e-mail vem só do JWT: o cabeçalho `Cf-Access-Authenticated-User-Email` sozinho → 401. (f) Modo dev: sem `WORDCUT_ACCESS_TEAM_DOMAIN` e com `WORDCUT_DEV_EMAIL` de um membro → `/api/me` 200 sem token, com aviso no log ao subir; com o Access configurado, `WORDCUT_DEV_EMAIL` é ignorado (sem token → 401); sem Access e sem `WORDCUT_DEV_EMAIL` → 401; o e-mail dev também passa por `role_of` (fora da equipe → 403). (g) `/api/health` responde 200 sem token com o Access configurado. (h) `ApiSettings` lê as três variáveis do ambiente. | `apps/api/tests/test_auth.py` por HTTP (`TestClient`), `create_app(settings=ApiSettings(...), keys=<dublê>)`, membros por `add_member` sobre `wordcut_home`. A rota de admin é montada **no teste** com `Depends(require("admin"))` (o passo não cria rota de negócio). Leitura do ambiente por `monkeypatch.setenv` + `create_app()` sem argumento. 🧬 `require` que não compara papel; modo dev ligado com Access configurado; `current_member` que confia no cabeçalho de e-mail; 403 trocado por 401 para e-mail fora da equipe → todas vermelhas. |
| 4 — Compose e documentação | (a) `compose.yaml` repassa à `api` `WORDCUT_ACCESS_TEAM_DOMAIN` e `WORDCUT_ACCESS_AUD`; não liga `WORDCUT_DEV_EMAIL` por padrão (ADR-0009: nunca em produção). (b) `docs/cli.md` §5.3 lista `unauthenticated` e `forbidden` com saída 1 e o "quando". (c) `docs/architecture/README.md` deixa de dizer "esqueleto com `GET /api/health`" e descreve identidade, papéis e `/api/me`. (d) `CHANGELOG.md` tem a entrada em `[Não lançado]`. (e) `apps/api/pyproject.toml` declara `pyjwt[crypto]` e o `uv.lock` está coerente. | `docker compose config` (renderização, sem subir) e leitura do diff de `compose.yaml`; leitura de `git diff afbe8e1 -- docs CHANGELOG.md`; `uv lock --check`. Passo sem teste automatizado: o veredito sai da leitura do diff contra (a)–(e). |

| Critério de aceite | O que o cobre |
|---|---|
| Spec · Cenário "membro identificado": assistente com token válido → `GET /api/me` 200 `{"email", "role": "assistant"}` | `test_auth.py`, passo 3 (a) |
| Spec · Cenário "sem token ou token inválido" (sem cabeçalho, assinatura errada, expirado, `aud` errado) → 401 `unauthenticated` em qualquer rota menos `/api/health` | `test_identity.py` passo 2 (b) para cada forma de token; `test_auth.py` passo 3 (b) por HTTP em `/api/me` **e** na rota de admin de teste; passo 3 (g) para `/api/health` |
| Spec · Cenário "e-mail não liberado" → 403 `forbidden` | `test_auth.py`, passo 3 (c) |
| Spec · Cenário "permissão por papel": assistente em rota de admin → 403; admin → normal | `test_auth.py`, passo 3 (d) |
| Spec · Borda: chaves buscadas e em cache; nos testes nunca há rede, chaves de dublê | `test_identity.py`, passo 2 (c) e (d); suíte inteira verde com `no_network` autouse |
| Spec · Borda: modo dev só sem `WORDCUT_ACCESS_TEAM_DOMAIN`; com Access, ignorado | `test_auth.py`, passo 3 (f) |
| Spec · Borda: sem Access e sem `WORDCUT_DEV_EMAIL`, toda rota protegida → 401 | `test_auth.py`, passo 3 (f), terceiro caso |
| Spec · Borda: nenhum token em log ou erro | `test_identity.py` passo 2 (e) e `test_auth.py` (corpo das respostas 401 e `caplog`), com o token literal procurado no texto |
| FR-001: JWT de `Cf-Access-Jwt-Assertion`, RS256, chaves do time e `aud` configurado | `test_identity.py` passo 2 (a)(b), incluindo a recusa de `alg` diferente de RS256 |
| FR-002: papel por `members.role_of(email)` | `test_auth.py` passo 3 (a)(c): papel trocado com `set_role` muda a resposta de `/api/me` sem mexer no token |
| FR-003: cada rota declara o papel mínimo; tabela da 1.2.a respeitada | Nesta issue: `require("admin")` provado na rota de teste (passo 3 d). A aplicação da tabela linha a linha fica com as rotas de negócio (20a/20b, fora de escopo) — ver lacuna L2 |
| FR-004: `GET /api/me` devolve e-mail e papel | `test_auth.py`, passo 3 (a) |
| FR-005: mesmo objeto de erro da CLI, status coerente | `test_errors_http.py`, passo 1 (b)(c) |
| Verificação · Token válido de membro → `/api/me` 200 com e-mail e papel | igual a FR-004 |
| Verificação · Sem token, assinatura errada, expirado, `aud` errado → 401 | igual ao cenário "sem token ou token inválido" |
| Verificação · Fora da equipe → 403; assistente em rota de admin → 403 | passo 3 (c)(d) |
| Verificação · Modo dev só sem Access configurado | passo 3 (f) |
| Verificação · Nenhuma chamada de rede nos testes; token não aparece em erro | passo 2 (d)(e); suíte inteira com `no_network`; nenhum teste remove `WORDCUT_FORBID_NETWORK` (conferido por `git diff afbe8e1 -- '*test*' conftest.py`) |
| Verificação · Quality gates limpos | `uv run ruff check . && uv run ruff format --check . && uv run mypy` e `uv run pytest -q` verdes; `uv lock --check` |

**Lacunas do plano** (decididas pela opção mais conservadora, sem consulta, conforme a
execução automatizada aprovada; detalhe em `tdd.md`):

- **L1 — Conexão com o banco.** O plano não diz de onde a API tira a conexão para `role_of`.
  Barra: conexão por requisição com `db.connect(Home.from_environment())`, fechada ao fim;
  `/api/health` não abre o banco. Sem isso, passo 3 fica PARCIAL se `test_health.py`
  precisar de `WORDCUT_HOME` ou se a conexão for compartilhada entre threads.
- **L2 — Rota de admin.** Não existe rota de admin nesta issue. Barra: a rota é montada no
  teste com `Depends(require("admin"))`; nenhuma rota de negócio em produção. A tabela da
  1.2.a, linha a linha, é critério das issues 20a/20b.
- **L3 — Configuração parcial do Access.** O plano não decide `TEAM_DOMAIN` sem `AUD` (ou o
  inverso). Barra: nunca cai no modo dev; `create_app` falha ao subir ou toda rota protegida
  dá 401. Qualquer caminho que aceite token sem checar `aud` é FAIL do passo 2/3.
- **L4 — Falha ao buscar as chaves.** O plano não diz o status quando a busca das chaves
  falha. Barra: `network_error` → 502 pelo mapeamento do passo 1, nunca 200 nem acesso
  liberado; corpo sem o token.
- **L5 — Códigos de saída 1 além de `internal_error`.** `interrupted` e `processing_error`
  não têm status no plano. Barra: 500, e o teste do passo 1 percorre todo `EXIT_CODES`.
- **L6 — Erro inesperado.** O plano não cobre exceção que não é `WordcutError`. Barra
  recomendada (não bloqueia o PASS): 500 `internal_error` com o objeto de erro e sem
  rastro, token ou e-mail no corpo.
- **L7 — `iss`.** FR-001 não pede checar o emissor (`https://<team>`). Recomendado
  checar; não bloqueia o PASS.
- **L8 — Modo dev e equipe.** O plano não diz se `WORDCUT_DEV_EMAIL` passa por `role_of`.
  Barra: passa (e-mail dev fora da equipe → 403); o modo dev não é atalho de admin.

## Rodada 1 — 2026-10-26 — working tree sobre afbe8e1

**baseline_commit**: afbe8e16606c94b897a70e46e4a7045f6e715687
**Componentes avaliados**: `apps/api` (settings, identity, auth, errors, app, testes novos);
`packages/core` (`errors.py`); `compose.yaml`; documentação; `uv.lock`
**Suítes**: API ✅ (63 / 0 falhas) · core `test_errors.py` ✅ (23 / 0) · monorepo ✅ (1335 /
0, com `UV_OFFLINE=1`) · ruff check ✅ · ruff format --check ✅ · mypy ✅ · `uv lock --check`
✅ (offline) · `docker compose config -q` ✅

Mutações manuais numa cópia no scratchpad (a working tree não foi tocada): passo 1, 5 de 5
mortas; passo 2, 15 de 19; passo 3, 14 de 17. Todas as mutações que a barra exige (🧬 do
Plano de QA) morrem, menos `algorithms` com `"none"`, que é equivalente (ver abaixo).

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Erros HTTP | PASS | `test_errors_http.py` parametrizado sobre todo `EXIT_CODES` (status + `{"error": to_dict()}`), sem `details` quando não há, exceção inesperada → 500 sem o texto (L5, L6); `test_errors.py` do core com os dois códigos (saída 1). 🧬 `unauthenticated`→403, saída 5→400 e corpo sem `details` mortas |
| 2 — Verificação do token | PASS | `test_identity.py`: e-mail de token válido; 9 tokens ruins → `unauthenticated` sem o token no erro nem no log (inclui `iss`, L7); cache de 10 min dos dois lados com relógio injetado; nova busca em `kid` novo; `AccessKeys` real → `network_error` com `forbidden_by`. 🧬 +HS256, sem `audience`, `verify_exp` False, cache sem validade, sem nova busca, sem `refuse_when_forbidden` mortas |
| 3 — Membro e papel | PASS | `test_auth.py` por `TestClient`: `/api/me` 200 (assistant e admin), papel vindo de `role_of`, 401 sem token / token recusado / só cabeçalho de e-mail, 403 fora da equipe sem e-mail no corpo e no log, `require("admin")` em rota do teste, modo dev (aviso, ignorado com Access, 401 sem nada, 403 fora da equipe — L8), meia config recusa subir (L3), 502 sem chaves (L4), health sem token nem banco (L1), leitura do ambiente. 🧬 `require` sem papel, dev com Access, confiar no cabeçalho, 403→401 mortas |
| 4 — Compose e documentação | PASS | `compose.yaml` repassa `WORDCUT_ACCESS_TEAM_DOMAIN`/`AUD` com padrão vazio e nunca `WORDCUT_DEV_EMAIL` (conferido com a variável no shell); `docs/cli.md` §5.1 e §5.3; arquitetura (estado da API e fluxo 5.4); entrada em `[Não lançado]`; `pyjwt[crypto]>=2.8` e `uv lock --check` ok |

### Fatos relatados pelo implementador

- **Rede no `uv add`**: a barra proíbe rede nos testes, não na resolução da dependência. Os
  testes não usam rede: `no_network` da raiz continua autouse, nenhum teste remove
  `WORDCUT_FORBID_NETWORK`, a mutação que tira `refuse_when_forbidden` morre, e suíte, lock
  e checagens passaram com `UV_OFFLINE=1`. O `uv.lock` ganhou só `pyjwt`, `cryptography`,
  `cffi` e `pycparser`, do registro PyPI.
- **`"none"` em `algorithms`**: equivalente, confirmado. No PyJWT 2.15.1,
  `NoneAlgorithm.prepare_key` levanta `InvalidKeyError` (um `PyJWTError` → 401) para chave
  não nula, e `verify` nunca decodifica com chave nula: a guarda `if key is None` está presa
  pelo caso "kid desconhecido" (removê-la, com ou sem `"none"`, deixa o teste vermelho).

### Achados que não bloqueiam (fora da barra)

- Mutação sobrevivente: tirar `"exp"` de `REQUIRED_CLAIMS` — um token **sem** `exp`
  assinado pelo Access passaria sem validade. Nenhum caso "sem `exp`" entre os tokens ruins;
  a barra só exige `exp` no passado. Recomendado acrescentar o caso.
- Mutação sobrevivente: ler `WORDCUT_ACCESS_AUD` de `WORDCUT_ACCESS_TEAM_DOMAIN` (ou o
  inverso). O teste do ambiente prova que as variáveis são lidas, não que o valor chega à
  verificação; a falha seria fechada (401). Recomendado: `monkeypatch.setenv` das duas +
  `create_app(keys=<dublê>)` e `/api/me` 200 com token válido.
- Mutação sobrevivente: `require` sem o atalho de admin (`member.role != role`). Nenhuma rota
  com `require("assistant")` no teste; a ADR-0019 diz que o admin passa em todas.
- Equivalentes: `_key_id` sem checar o tipo e chave não-RSA mantida no cache → os dois
  acabam em 401.
- Log: o Starlette relança a exceção inesperada depois do handler, e o servidor registra o
  rastro com o texto dela. A L6 fala do corpo (cumprida); nenhum caminho atual leva token ou
  e-mail ao texto de uma exceção inesperada, mas a garantia "nunca no log" não vale para
  esse caso.
- Cada token com `kid` desconhecido dispara uma busca das chaves (sem limite). É a decisão
  do plano; com a API só em `127.0.0.1` e atrás do Access, o risco é baixo.
- Comentários: todos de um tipo da política (intenção, alerta, restrição externa com
  fonte, referência). ADR-0019 coerente com o código e com o índice.

### Critérios de aceite
- ✅ Membro identificado → `/api/me` 200 — `test_a_member_with_a_valid_token_sees_the_email_and_role`
- ✅ Sem token ou token inválido → 401 — `test_a_token_access_did_not_sign_…`, `test_a_request_without_the_access_token_is_unauthenticated` (`/api/me` e rota de admin), `test_a_rejected_token_is_unauthenticated_and_never_repeated`; health em `test_health_answers_without_a_token_nor_the_database`
- ✅ E-mail não liberado → 403 — `test_an_email_outside_the_team_is_forbidden_without_repeating_it`
- ✅ Permissão por papel — `test_an_assistant_is_forbidden_…`, `test_an_admin_gets_the_answer_…`
- ✅ Borda: chaves em cache, sem rede — `test_the_keys_are_fetched_*`, `test_the_real_keys_refuse_…`; suíte com `no_network`
- ✅ Borda: modo dev só sem Access — `test_the_dev_email_identifies_…`, `test_the_dev_email_is_ignored_when_access_is_configured`
- ✅ Borda: sem Access e sem dev → 401 — `test_without_access_nor_dev_email_nobody_is_identified`
- ✅ Borda: nenhum token em log ou erro — tokens ruins em `test_identity.py` e `test_auth.py` (corpo + `caplog`), `test_keys_out_of_reach_are_a_bad_gateway_without_the_token`
- ✅ FR-001 — `test_identity.py` (RS256, `aud`, `iss`, recusa de `none` e HS256)
- ✅ FR-002 — `test_the_role_comes_from_the_team_not_from_the_token`
- ✅ FR-003 (escopo desta issue, L2) — `require("admin")` na rota do teste
- ✅ FR-004 — `test_a_member_with_a_valid_token_sees_the_email_and_role`
- ✅ FR-005 — `test_every_error_code_answers_with_its_status_and_the_error_object_of_the_cli`
- ✅ Verificação · token válido → 200 — idem FR-004
- ✅ Verificação · sem token, assinatura, expirado, `aud` → 401 — idem cenário
- ✅ Verificação · fora da equipe / assistente em admin → 403 — passo 3 (c)(d)
- ✅ Verificação · modo dev só sem Access — passo 3 (f)
- ✅ Verificação · sem rede, token fora do erro — passo 2 (d)(e); nenhum teste remove `WORDCUT_FORBID_NETWORK`
- ✅ Verificação · quality gates — ruff, mypy, pytest, `uv lock --check` verdes

### Veredito geral: PASS
Os 4 passos e os 19 critérios passam contra a barra. Os sobreviventes acima ficam fora da
barra; recomendado fechá-los (`exp` ausente e valores do ambiente) antes das rotas de negócio.

## Rodada 2 — 2026-10-26 — working tree sobre afbe8e1

**baseline_commit**: afbe8e16606c94b897a70e46e4a7045f6e715687
**Componentes avaliados**: `apps/api` (`identity.py`, `auth.py`, testes); `packages/core`
(`errors.py`); `compose.yaml`; documentação; `uv.lock`; `plan.md` (L9, L10)
**Barra desta rodada**: a matriz do Plano de QA, mais a decisão do orquestrador que reabriu
o passo 2: token sem `exp` → 401 e mutação "`exp` ausente aceito" vermelha; atalho de admin
do `require` coberto ou registrado como equivalente; L9 e L10 no `plan.md`.
**Suítes**: API ✅ (66 / 0 falhas) · core `test_errors.py` ✅ (23 / 0) · monorepo ✅ (1338 /
0, com `UV_OFFLINE=1`) · ruff check ✅ · ruff format --check ✅ · mypy ✅ · `uv lock --check`
✅ (offline) · `docker compose config -q` ✅

Mutações manuais numa cópia no scratchpad (a working tree não foi tocada): barra da rodada 2,
4 de 4 mortas; regressão das 🧬 da rodada 1, 13 de 13 mortas; fora da barra, 0 de 2.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Erros HTTP | PASS | Sem mudança desde a rodada 1; 🧬 `unauthenticated`→403, saída 5→400 e corpo sem `details` continuam mortas |
| 2 — Verificação do token | PASS | Caso `without an expiry` em `BAD_TOKENS` (`test_identity.py`) e em `REJECTED_TOKENS` (`test_auth.py`, e-mail assinado cadastrado como admin, para o 401 não ser mascarado por 403). 🧬 `REQUIRED_CLAIMS` sem `"exp"` → os 2 testes vermelhos; `REQUIRED_CLAIMS` vazio e `options` sem `require` também mortas. `identity.py:24` e `:108` seguem a L9 (`aud`, `exp`, `iss` no `require`; `email` por `_email`, equivalente, com o caso `without an e-mail` vermelho). As 🧬 da rodada 1 continuam mortas |
| 3 — Membro e papel | PASS | `test_an_admin_gets_the_answer_of_a_route_for_assistants`: rota de teste com `require("assistant")`, admin → 200. 🧬 `member.role != role` → vermelha (L10). As 🧬 da rodada 1 continuam mortas |
| 4 — Compose e documentação | PASS | Sem mudança desde a rodada 1; ADR-0019 diz "`exp` presente e no futuro" (linha 28) e "o administrador passa em todas" (linha 38) |

### Barra da rodada 2
- ✅ Token sem `exp` → 401 `unauthenticated` (em `verify` e por HTTP); mutação "`exp` ausente
  aceito" vermelha.
- ✅ Atalho de admin do `require` coberto por teste de comportamento (não equivalente).
- ✅ L9 e L10 nas Decisões técnicas do `plan.md`.

### Achados que não bloqueiam (fora da barra)

- Mutação sobrevivente nova: `require` que só deixa passar o admin (`member.role != ADMIN`).
  Nenhum teste põe um **assistente** numa rota `require("assistant")`; o mutante trancaria o
  assistente em toda rota de assistente. Recomendado: o mesmo teste da L10 com o assistente,
  antes das rotas de negócio (20a/20b).
- Continua sobrevivendo: `WORDCUT_ACCESS_AUD` lido de `WORDCUT_ACCESS_TEAM_DOMAIN` (achado da
  rodada 1, falha fechada em 401). A recomendação não foi aplicada.
- Os demais achados da rodada 1 (rastro no log do servidor para exceção inesperada; busca sem
  limite por `kid` desconhecido) seguem como estavam.

### Critérios de aceite
- ✅ Membro identificado → `/api/me` 200 — `test_a_member_with_a_valid_token_sees_the_email_and_role`
- ✅ Sem token ou token inválido → 401 — `test_a_request_without_the_access_token_is_unauthenticated`, `test_a_rejected_token_is_unauthenticated_and_never_repeated` (agora com `without an expiry`), `test_a_token_access_did_not_sign_…`; health em `test_health_answers_without_a_token_nor_the_database`
- ✅ E-mail não liberado → 403 — `test_an_email_outside_the_team_is_forbidden_without_repeating_it`
- ✅ Permissão por papel — `test_an_assistant_is_forbidden_…`, `test_an_admin_gets_the_answer_…` e `test_an_admin_gets_the_answer_of_a_route_for_assistants`
- ✅ Borda: chaves em cache, sem rede — `test_the_keys_are_fetched_*`, `test_the_real_keys_refuse_…`; suíte com `no_network`
- ✅ Borda: modo dev só sem Access — `test_the_dev_email_identifies_…`, `test_the_dev_email_is_ignored_when_access_is_configured`
- ✅ Borda: sem Access e sem dev → 401 — `test_without_access_nor_dev_email_nobody_is_identified`
- ✅ Borda: nenhum token em log ou erro — tokens ruins em `test_identity.py` e `test_auth.py` (corpo + `caplog`)
- ✅ FR-001 — `test_identity.py` (RS256, `aud`, `iss`, `exp` obrigatório, recusa de `none` e HS256)
- ✅ FR-002 — `test_the_role_comes_from_the_team_not_from_the_token`
- ✅ FR-003 (escopo desta issue, L2 e L10) — `require("admin")` e `require("assistant")` em rotas do teste
- ✅ FR-004 — `test_a_member_with_a_valid_token_sees_the_email_and_role`
- ✅ FR-005 — `test_every_error_code_answers_with_its_status_and_the_error_object_of_the_cli`
- ✅ Verificação · token válido → 200 — idem FR-004
- ✅ Verificação · sem token, assinatura, expirado, `aud` → 401 — idem cenário
- ✅ Verificação · fora da equipe / assistente em admin → 403 — passo 3 (c)(d)
- ✅ Verificação · modo dev só sem Access — passo 3 (f)
- ✅ Verificação · sem rede, token fora do erro — passo 2 (d)(e); nenhum teste remove `WORDCUT_FORBID_NETWORK`
- ✅ Verificação · quality gates — ruff, mypy, pytest, `uv lock --check` verdes

### Veredito geral: PASS
Os 4 passos e os 19 critérios passam; os três pontos da barra da rodada 2 estão cumpridos.
Dois mutantes sobrevivem fora da barra (assistente em rota de assistente; AUD trocado).
