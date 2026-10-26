# Plan: Equipe e papéis (`member`)

**Issue**: 1.2.a.1
**Feature**: specs/1.2.a.1-team-members
**Data**: 2026-10-26

---

## Resumo

Tabela `members` (e-mail e papel), serviço com a regra do último administrador e `role_of`
para a API, e grupo `member` na CLI.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md). D1–D9 e L1–L7 vêm do plano de QA (`qa.md`), aceitas pelo
orquestrador na rodada 1.

---

## Contexto de código

| Situação | Path |
|---|---|
| Criar | `packages/core/src/wordcut/db/migrations/0010_members.sql` — `members(email PRIMARY KEY, role CHECK IN ('assistant','admin'), created_at, updated_at)`, sem `BEGIN`/`COMMIT`, cabeçalho `-- 1.2.a.1: ...`; `user_version` passa a 10 |
| Criar | `packages/core/src/wordcut/db/members.py` — SQL da tabela, sem regra de negócio |
| Criar | `packages/core/src/wordcut/service/members.py` — `list_members`, `add_member`, `set_role`, `remove_member` (com `now` opcional), `role_of(conn, email) -> str \| None` |
| Só leitura | `packages/core/src/wordcut/errors.py` — `last_admin` (saída 5) já existe; não muda |
| Criar | `apps/cli/src/wordcut_cli/member.py` — grupo e ações no padrão de `preset.py` (ajuda "— administrador", `example=`) |
| Alterar | `apps/cli/src/wordcut_cli/__init__.py` — registra `member` |
| Alterar | `apps/cli/src/wordcut_cli/contract.py` — `add_group` aceita `example=` opcional, como `add_command` (exemplo no `--help` do grupo, D5) |
| Alterar | `apps/cli/tests/test_cli.py` — `member` na lista de comandos do `wordcut --help` |
| Criar | `packages/core/tests/test_members_service.py`, `apps/cli/tests/test_member_command.py` |
| Alterar | `CHANGELOG.md`, `docs/architecture/README.md` §4, `docs/cli.md` §12 (campos, ordem, saída de `remove`) e §17 |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python (core, cli) | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Identificador | e-mail em minúsculas, sem espaços | Cloudflare Access envia o e-mail; comparação estável |
| Validação de e-mail | `local@domínio.tld` simples (regex conservadora) | Sem dependência; o Access valida de verdade |
| Último administrador | remover ou rebaixar o único admin → `last_admin`; regra checada numa transação | FR-003 |
| Primeiro membro | qualquer papel; a CLI no servidor já age como admin, então não há bloqueio de "sem admin" antes do primeiro | Instalação nova |
| Dados guardados | só e-mail, papel, datas | LGPD (§VI) |
| Exemplos e testes | só e-mails `@exemplo.org` | §17 |
| Migração | `0010_members.sql` (D1) | A última no baseline é `0009_renders.sql` |
| Código de erro | `errors.py` intocado; `WordcutError("last_admin", ...)` (D2) | `last_admin` já existe com saída 5 |
| Concorrência do último admin | contagem e escrita sob `BEGIN IMMEDIATE` explícito; teste com uma segunda conexão concorrente (D3, L1) | CLI e API gravam no mesmo arquivo (ADR-0005); o `BEGIN` implícito só abre no primeiro DML |
| Saída | `list` → `{"items": [{email, role, created_at, updated_at}]}` ordenado por e-mail; `add`/`set-role` → o membro; `remove` → `{"email", "removed": true}`; datas ISO 8601 com fuso; `now` injetável; documentado em `docs/cli.md` §12 (D6, L2) | Padrão de `preset` |
| Privacidade em `docs/cli.md` §17 | "de dado pessoal, só o e-mail; além dele, papel e datas" (D4, L3) | A spec mostra a data de inclusão |
| `role_of` com e-mail malformado ou vazio | `None`, sem exceção (L4) | A API decide "sem acesso" |
| E-mails de exemplo | só `admin@exemplo.org`, `assistente@exemplo.org`, `editor2@exemplo.org`; spec corrigida (D8, L5) | CONTRIBUTING §6: sem nomes de pessoas |
| Eco do e-mail em erro | nenhuma mensagem nem `details` traz o e-mail; `details` só `{"argument": ...}` (+ `choices`) (D9, L6) | ADR-0015; o e-mail é dado pessoal |
| `set-role` para o mesmo papel | sucesso idempotente, sem gravar; `last_admin` só de `admin` para `assistant` (L7) | |
| `--role` | obrigatório, `choices=("assistant", "admin")`; `set-role` com papel posicional e as mesmas `choices`; o serviço valida de novo (D7) | A API chama o serviço direto |
| Ajuda | grupo e as quatro ações com "— administrador" e `example=` com `@exemplo.org` (D5) | `docs/cli.md` §3.5 |

---

## Ordem de implementação

- [x] **Passo 1 — Banco e serviço** — migração, repositório, serviço com validações e último admin, `role_of`.
- [x] **Passo 2 — CLI** — `member list/add/set-role/remove`.
- [x] **Passo 3 — Documentação** — CHANGELOG, arquitetura §4, `docs/cli.md` §12 e §17.

---

## Verificação

- [x] `member add` + `member list --json` → e-mail normalizado, papel, data.
- [x] `set-role` e `remove` funcionam; último admin → `last_admin`.
- [x] E-mail inválido, repetido ou papel inválido → `invalid_argument`; inexistente → `not_found`.
- [x] `role_of` devolve o papel ou `None`.
- [x] Quality gates limpos.
