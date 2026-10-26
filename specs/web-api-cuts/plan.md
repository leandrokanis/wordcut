# Plan: Rotas da API para cortes, exportações, configurações, presets e equipe

**Issue**: web-api-cuts
**Feature**: specs/web-api-cuts
**Data**: 2026-10-26

---

## Resumo

Routers finos sobre os serviços existentes, com as dependências do item 20a e as permissões
do item 19. Segredos pelo corpo, nunca devolvidos.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Contexto de código

| Situação | Path |
|---|---|
| Criar | `apps/api/src/wordcut_api/routes/cuts.py`, `routes/renders.py`, `routes/settings.py`, `routes/presets.py`, `routes/members.py` |
| Alterar | `apps/api/src/wordcut_api/app.py` — registra os routers |
| Criar | `apps/api/tests/test_cuts_routes.py`, `test_renders_routes.py`, `test_settings_routes.py`, `test_presets_routes.py`, `test_members_routes.py`, `test_permissions.py` (tabela da 1.2.a por rota) |
| Alterar | `docs/api.md`, `CHANGELOG.md`, `docs/architecture/README.md` §4 e fluxo 5.3, `README.md` |
| Criar | `apps/api/src/wordcut_api/bodies.py` — base dos corpos estritos (L6) |
| Alterar | `apps/api/src/wordcut_api/routes/__init__.py` — `ROUTERS` (L1) |
| Alterar | `apps/api/src/wordcut_api/routes/{sermons,tasks,status}.py` — a identidade sai do `APIRouter` e vai para a inclusão (L1) |
| Alterar | `apps/api/src/wordcut_api/errors.py` — `extra_forbidden` vira argumento não reconhecido (L7) |
| Alterar | `apps/api/tests/conftest.py` — `home`, pregação processada, corte e exportação pelos repositórios (L9) |
| Alterar | `apps/api/tests/test_auth.py` — a varredura lê `routes.ROUTERS` (L1) |
| Criar | `docs/adr/0021-rotas-de-cortes-e-administracao-na-api.md`, com entrada em `docs/adr/README.md` (L10) |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Verbos | `POST` para transições e tarefas; `PUT` para correção de palavra e segredos; `PATCH` para alteração parcial; `DELETE` para restaurar estilo e apagar | REST previsível |
| Permissões | tabela única `route → papel mínimo` testada inteira em `test_permissions.py` | FR-005 sem esquecer rota |
| Identidade estrutural | todo router de `/api` (menos health) é incluído com `dependencies=[Depends(current_member)]`; a varredura percorre também rotas fora do OpenAPI | Risco registrado no QA do 20a |
| Segredos | corpo `{"value": "…"}`; resposta só máscara/presença; corpo nunca logado | §VI |
| Estimativa | `GET` com opções em query string | Sem efeito colateral |
| Arquivos | `FileResponse` com nome legível | Igual ao `render download` |
| L1 — Identidade num lugar só | `routes.ROUTERS` (os oito routers); `app.py` inclui cada um num laço com `dependencies=[Depends(current_member)]`; a identidade sai dos construtores do 20a; os routers de administrador declaram `require("admin")` no próprio `APIRouter`; a varredura de `test_auth.py` e `test_permissions.py` lê as `APIRoute` de `ROUTERS`; um teste exige que as entradas de `app.routes` que não são `APIRoute` somem `len(ROUTERS)` | Uma rota fora do OpenAPI não escapa da varredura (QA, L1) |
| L2 — Papel da administração | `/api/settings`, `/api/criteria`, `/api/presets` e `/api/members` são só de administrador, leitura incluída | 1.2.a "Configurações e equipe"; docs/cli.md §11 (QA, L2) |
| L3 — Sem caminho local | a API tira `path` de toda exportação (`GET` do corte, transições, `GET /api/cuts/{id}/renders`, `GET /api/renders/{id}`); a web baixa por `GET /api/renders/{id}/file` | Caminho interno não vai à web (QA, L3) |
| L4 — E-mail só no corpo | `POST /api/members {"email", "role"}` (201), `POST /api/members/set-role {"email", "role"}` (200), `POST /api/members/remove {"email"}` (200) | E-mail na URL iria para os logs de acesso (LGPD; QA, L4) |
| L5 — Segredo com `/config:ro` | a montagem fica como está; a rota devolve 409 `config_not_writable` sem o segredo, testado com a pasta sem escrita; `details.argument` `key`/`cookies` vira `value`; `docs/api.md` diz que, no Compose, o segredo se grava pela CLI no host | Mudar a montagem é decisão de segurança à parte (QA, L5) |
| L5b — `config_not_writable` sem caminho | na rota de segredo, o 409 sai com a mensagem "A pasta de configuração não aceita gravação; grave o segredo pela CLI no host.", sem `details` e sem caminho; a CLI continua mostrando o caminho, porque roda no host | A API nunca mostra caminho do servidor (ADR-0021; decisão do orquestrador, Rodada 2) |
| L6 — Corpos estritos | modelos com `extra="forbid"`, `StrictInt`/`StrictBool`, `null` recusado e `model_dump(exclude_unset=True)`; campos de escolha tipados `str`, para o serviço dar `details.choices`; entrada no formato da saída e com os nomes do serviço; `PATCH` de legenda `{}` dá 400; no preset, `details.argument` `level` vira `levels` | Tipo errado nunca vira 500 (QA, L6) |
| L7 — Campo desconhecido | `extra_forbidden` (corpo ou query) dá 400 `invalid_argument` "Argumento não reconhecido; veja docs/api.md.", sem `details`; a estimativa lê a query por um modelo com `extra="forbid"` | ADR-0015: nem o nome digitado volta (QA, L7) |
| L8 — Status de sucesso | 201 em `POST /api/presets` e `POST /api/members`; 200 com corpo em `DELETE /api/cuts/{id}/caption` e `DELETE /api/presets/{id}`; 200 com `show_cut` nas transições; 202 só na exportação | (QA, L8) |
| L9 — Fixtures sem renderizar | toda exportação 202 nos testes usa `harmless_tasks`; nenhum `detached_tasks` de `render`; pregação, transcrição, corte e exportação de teste pelos repositórios, no `tests/conftest.py` da API | ADR-0017, ADR-0018 (QA, L9) |
| L10 — ADR | ADR-0021 para L1, L3, L4, L5 e L7, com entrada no índice, na arquitetura e no README | CONTRIBUTING §3.1 (QA, L10) |
| L11 — Contexto de código | tabela acima completada | (QA, L11) |

---

## Ordem de implementação

- [x] **Passo 1 — Cortes** — leitura, prévia, transições, correção, legenda.
- [x] **Passo 2 — Exportações** — exportar (202), estimativa, listar, detalhar, arquivo.
- [x] **Passo 3 — Administração** — configurações (com segredos), critérios, presets, membros.
- [x] **Passo 4 — Permissões** — tabela por rota testada inteira.
- [x] **Passo 5 — Documentação** — `docs/api.md`, CHANGELOG, arquitetura.

---

## Verificação

- [x] Cada rota devolve o JSON da CLI; erros com status do item 19.
- [x] Exportar → 202; estimativa sem tarefa; arquivo com nome legível.
- [x] Segredos nunca devolvidos (procura do valor fictício nas respostas).
- [x] Assistente recebe 403 em toda rota de admin; admin passa.
- [x] Sem rede, sem renderização real; quality gates limpos.
