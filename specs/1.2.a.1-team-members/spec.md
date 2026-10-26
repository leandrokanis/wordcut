# Spec: Equipe e papéis (`member`)

**Issue**: 1.2.a.1 (sem rastreador; o ID é o código do requisito)
**Requisito**: docs/requirements/features/1.2.a-team-and-roles.md §1.2.a.1; docs/cli.md §12, §17;
constituição §VI; ADR-0009
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

O administrador libera e-mails e define o papel de cada pessoa (assistente ou administrador).
Da equipe se guarda só o e-mail e o papel (LGPD). A API usará essa lista para decidir o que
cada pessoa pode fazer, a partir do e-mail verificado pelo Cloudflare Access.

---

## Cenários de aceite

**Cenário: liberar e listar**
- **Dado** uma instalação nova
- **Quando** o administrador roda `member add assistente@exemplo.org --role assistant` e `member list --json`
- **Então** a lista traz o e-mail (normalizado em minúsculas), o papel e a data de inclusão

**Cenário: mudar papel e remover**
- **Dado** um membro assistente
- **Quando** o administrador roda `member set-role <email> admin` e depois `member remove <email>`
- **Então** o papel muda e depois o membro some da lista

**Cenário: último administrador**
- **Dado** um único administrador
- **Quando** alguém tenta removê-lo ou rebaixá-lo
- **Então** falha com `last_admin` (saída 5)

### Casos de borda

- E-mail inválido → `invalid_argument`.
- E-mail já liberado → `invalid_argument` (sem duplicar).
- Membro inexistente → `not_found`.
- Papel fora de `assistant|admin` → `invalid_argument`.

---

## Requisitos funcionais

- **FR-001**: `member list/add/set-role/remove` DEVEM existir conforme docs/cli.md §12.
- **FR-002**: Só e-mail, papel e datas DEVEM ser guardados.
- **FR-003**: Nunca DEVE ficar sem administrador depois de existir o primeiro.
- **FR-004**: O serviço DEVE oferecer `role_of(email)` para a API (item 19).

---

## Entidades e dados

- **Membro (`member`)**: email (único, minúsculas), role, created_at, updated_at.

---

## Escopo

### Componentes em escopo
- `packages/core/src/wordcut/` — migração, repositório, serviço `members`.
- `apps/cli/src/wordcut_cli/member.py`.

### Fora de escopo
- Login por código e Cloudflare Access (item 19).
