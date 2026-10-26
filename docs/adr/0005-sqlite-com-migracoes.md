# ADR-0005: SQLite com migrações por `user_version`

**Status**: Aceita · **Data**: 2026-10-26

## Contexto

Poucas pregações por semana e uma equipe pequena não justificam um banco servidor
(princípio V). A CLI e a API precisam ler e gravar o mesmo estado.

## Decisão

SQLite pela biblioteca padrão, sem ORM, num arquivo em `WORDCUT_HOME`. As migrações são
arquivos `NNNN_nome.sql` no `core`, aplicadas em ordem na abertura da conexão, uma
transação por arquivo, com `PRAGMA user_version` guardando a última aplicada. A conexão liga
`foreign_keys`, `journal_mode=WAL` e `busy_timeout`.

## Consequências

- Sem serviço de banco para operar nem `init` para lembrar.
- Leituras simultâneas da CLI e da API não bloqueiam; escritas são curtas.
