# Plan: Identidade pelo Cloudflare Access e papéis na API

**Issue**: 1.2.a.2
**Feature**: specs/1.2.a.2-api-identity
**Data**: 2026-10-26

---

## Resumo

`apps/api` ganha configuração por ambiente, verificação do JWT do Access com chaves em cache
(porta para dublê), dependência FastAPI `current_member` com `require(role)`, mapeamento de
`WordcutError` para HTTP e `GET /api/me`.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Contexto de código

| Situação | Path |
|---|---|
| Criar | `apps/api/src/wordcut_api/settings.py` — `ApiSettings` lido do ambiente (`WORDCUT_ACCESS_TEAM_DOMAIN`, `WORDCUT_ACCESS_AUD`, `WORDCUT_DEV_EMAIL`) |
| Criar | `apps/api/src/wordcut_api/identity.py` — `KeySource` (porta: chaves por `kid`), `AccessKeys` (busca `https://<team>/cdn-cgi/access/certs` com cache e a guarda de rede), `verify(token) -> email` |
| Criar | `apps/api/src/wordcut_api/auth.py` — dependências `current_member`, `require("admin")`; papel por `service.members.role_of` |
| Criar | `apps/api/src/wordcut_api/errors.py` — handler de `WordcutError` → status HTTP + `{"error": …}`; usa os códigos novos do core |
| Alterar | `apps/api/src/wordcut_api/app.py` — `create_app(settings=None, keys=None)`; `/api/me` |
| Alterar | `apps/api/pyproject.toml` — `pyjwt[crypto]` |
| Alterar | `packages/core/src/wordcut/errors.py` — `unauthenticated` e `forbidden`, com saída 1 (a CLI nunca os produz; a saída só existe porque a tabela é única) |
| Criar | `apps/api/tests/test_identity.py`, `apps/api/tests/test_auth.py`, `apps/api/tests/test_errors_http.py` |
| Alterar | `compose.yaml`, `docs/architecture/README.md`, `docs/cli.md` §5.3 (novos códigos), CHANGELOG |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Biblioteca JWT | PyJWT com `cryptography` | Padrão, mantida |
| Chaves | `KeySource` injetável; real com cache de 10 min e nova busca em `kid` desconhecido | Rotação de chaves do Access |
| Testes | par RSA gerado no teste; `KeySource` dublê; guarda de rede ligada | ADR-0017 |
| Status HTTP | `invalid_argument` 400; `unauthenticated` 401; `forbidden` 403; `not_found` 404; `busy` 409; regras (saída 5) 409; falha externa (saída 6) 502; `internal_error` 500 | Semântica HTTP; corpo igual ao da CLI |
| Modo dev | `WORDCUT_DEV_EMAIL` só sem Access configurado; aviso no log ao subir | ADR-0009 |
| Health | `/api/health` sem autenticação | Monitoramento e Compose |
| L1 — Conexão para `role_of` | Conexão por requisição com `db.connect(Home.from_environment())`, fechada ao fim; `/api/health` não abre o banco | SQLite não compartilha conexão entre threads; health não depende de `WORDCUT_HOME` (orquestrador, rodada 1) |
| L2 — Rota de admin | `require("admin")` provado numa rota montada no próprio teste; nenhuma rota de negócio nesta issue | Rotas de negócio são 20a/20b (orquestrador, rodada 1) |
| L3 — Access pela metade | Só `WORDCUT_ACCESS_TEAM_DOMAIN` ou só `WORDCUT_ACCESS_AUD` → `create_app` falha ao subir com mensagem clara; nunca cai no modo dev | Configuração incompleta não pode aceitar token sem `aud` nem abrir o modo dev (orquestrador, rodada 1) |
| L4 — Falha ao buscar chaves | `network_error` → 502 pelo mapeamento do passo 1; corpo sem o token | Falha externa, saída 6 (orquestrador, rodada 1) |
| L5 — Outras saídas 1 | `interrupted` e `processing_error` → 500; o teste percorre todo `EXIT_CODES` | Código novo não cai em padrão silencioso (orquestrador, rodada 1) |
| L6 — Exceção inesperada | Exceção que não é `WordcutError` → 500 `internal_error`, sem rastro, token ou e-mail no corpo | Constituição §VI, ADR-0015 (orquestrador, rodada 1) |
| L7 — Emissor | Verificar `iss == https://<team domain>` | Defesa em profundidade além do `aud` (orquestrador, rodada 1) |
| L8 — Modo dev e equipe | O e-mail de `WORDCUT_DEV_EMAIL` passa por `role_of`; fora da equipe → 403 | Modo dev não é atalho de admin (orquestrador, rodada 1) |
| L9 — Claims obrigatórios | `exp`, `aud` e `iss` em `options={"require": …}` do PyJWT; token sem `exp` → 401 `unauthenticated`. `email` fica fora do `require`: `_email` já recusa ausente, não texto ou vazio (equivalente, sem checagem duplicada) | Sem `exp`, um token assinado pelo Access valeria para sempre (orquestrador, rodada 2) |
| L10 — Admin em toda rota | `require(papel)` deixa passar o admin em rota de papel menor; provado com `require("assistant")` numa rota montada no teste | ADR-0019: o administrador passa em todas; a mutação que tira o atalho muda comportamento público (orquestrador, rodada 2) |

---

## Ordem de implementação

- [x] **Passo 1 — Erros HTTP** — códigos novos e handler.
- [x] **Passo 2 — Verificação do token** — `KeySource`, `verify`, cache, guarda de rede.
- [x] **Passo 3 — Membro e papel** — `current_member`, `require`, modo dev, `/api/me`.
- [x] **Passo 4 — Compose e documentação** — variáveis, arquitetura, cli.md, CHANGELOG.

---

## Verificação

- [x] Token válido de membro → `/api/me` 200 com e-mail e papel.
- [x] Sem token, assinatura errada, expirado, `aud` errado → 401 `unauthenticated`.
- [x] E-mail fora da equipe → 403 `forbidden`; assistente em rota de admin → 403.
- [x] Modo dev funciona só sem Access configurado.
- [x] Nenhuma chamada de rede nos testes; token não aparece em erro.
- [x] Quality gates limpos.
