# Plan: Criar pregação pelo link e consultá-la (`sermon create`, `list`, `show`)

**Issue**: 1.1.a.1
**Feature**: specs/1.1.a.1-sermon-create
**Data**: 2026-10-26

---

## Resumo

Primeira entidade do domínio: a pregação. O core ganha a tabela `sermons` (migração 0002),
um repositório SQL, o serviço `sermons` (criar idempotente pelo ID do vídeo, listar,
detalhar) e a extração do ID do vídeo; o YouTube entra por uma interface (`LiveSource`)
para ser dublê nos testes. A CLI ganha grupos de subcomandos (`sermon <ação>`) no contrato e
os três comandos.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Componentes em escopo

- `packages/core/src/wordcut/` — migração, repositório, serviço, ID do vídeo, erro do YouTube,
  configuração dos segredos.
- `apps/cli/src/wordcut_cli/` — grupos de subcomandos no contrato, aviso no stderr, comandos
  `sermon`.
- `packages/core/tests/`, `apps/cli/tests/`.

---

## Contexto de código

| Situação | Path |
|---|---|
| Criar | `packages/core/src/wordcut/db/migrations/0002_sermons.sql` — tabela `sermons` (`youtube_id` único, `status` com `CHECK`) |
| Criar | `packages/core/src/wordcut/db/sermons.py` — repositório: `insert`, `by_id`, `by_youtube_id`, `list(status)` devolvendo `SermonRow` |
| Criar | `packages/core/src/wordcut/service/sermons.py` — `create_sermon(conn, live, url)`, `list_sermons(conn, status)`, `show_sermon(conn, id)`; devolvem `dict` no formato de docs/cli.md |
| Alterar | `packages/core/src/wordcut/youtube.py` — `video_id(url) -> str`; `YouTubeError`; `info()` traduz falha do `yt-dlp`, JSON inválido e vídeo sem horário em `YouTubeError`; protocolo `LiveSource` |
| Criar | `packages/core/src/wordcut/config.py` — `config_dir()`: `WORDCUT_CONFIG` ou `~/.config/wordcut`; `youtube_cookies()` |
| Alterar | `packages/core/src/wordcut/youtube.py` — `DEFAULT_COOKIES` passa a vir de `config.youtube_cookies()` |
| Alterar | `apps/cli/src/wordcut_cli/contract.py` — `add_group(commands, name, help) -> Commands` para subcomandos aninhados; `Context.warn(message)` no stderr (não suprimido por `--quiet`) |
| Criar | `apps/cli/src/wordcut_cli/deps.py` — fábricas `live_source()` e `connection()` (ponto único que os testes substituem) |
| Criar | `apps/cli/src/wordcut_cli/sermon.py` — `sermon create/list/show`, texto legível, exemplos no `--help` |
| Alterar | `apps/cli/src/wordcut_cli/__init__.py` — registra o grupo `sermon` |
| Criar | `packages/core/tests/test_video_id.py`, `packages/core/tests/test_sermons_service.py`, `apps/cli/tests/test_sermon_command.py` |
| Alterar | `apps/cli/tests/test_cli.py` — inclui `sermon` |
| Alterar | `docs/architecture/README.md` §4, `CHANGELOG.md` |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python (core, cli) | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

Sem rede: o YouTube é sempre dublê nos testes.

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Camadas no core | repositório SQL (`db/sermons.py`) + serviço (`service/sermons.py`) | SQL num lugar só; serviço com a regra (ADR-0004) |
| Dependências do serviço | funções recebem `sqlite3.Connection` e um `LiveSource` (protocolo com `info(url)`) | Injeção explícita, sem estado global; dublê trivial |
| Formato do retorno | `dict` serializável no formato de docs/cli.md §4.3 (snake_case, segundos, ISO 8601) | O mesmo dicionário serve à CLI e à futura API |
| ID do vídeo | `video_id(url)` aceita `watch?v=`, `youtu.be/`, `/live/`, `/shorts/`, com ou sem `www.`/`m.`; outro link → `invalid_argument` com `details.argument = "link"` | FR-002; valida antes de chamar o YouTube |
| Idempotência | busca por `youtube_id` antes de consultar o YouTube; existente → `created: false` | Repetir não custa rede nem cria duplicata |
| Corrida de dois `create` iguais | `UNIQUE(youtube_id)`; `IntegrityError` → relê e devolve `created: false` | Correto sem trava |
| Erros do YouTube | `YouTube.info` lança `YouTubeError`; o serviço traduz para `youtube_error` (saída 6) com mensagem em português, sem o comando nem caminhos de cookies | §VI; contrato de erros |
| Cortes no `show`/`list` | `cuts: []` e contagens zeradas por estado até existir a tabela de cortes (item 9) | Formato estável desde já |
| Aviso de live no ar | serviço devolve `live_finished: false`; CLI chama `ctx.warn(...)` | Regra no core, apresentação na CLI |
| Grupos de subcomandos | `add_group` cria `sermon` com subparsers `required`; cada ação via `add_command` no grupo | Reaproveita o contrato, opções globais em qualquer posição |
| Fábricas da CLI | `wordcut_cli.deps` com `live_source()` e `connection()`; testes trocam por `monkeypatch` | Um ponto de injeção na borda |
| Segredos | `config.py` resolve `WORDCUT_CONFIG` (contêiner: `/config`) | ADR-0003; nunca lidos pelo código além de repassar o caminho ao `yt-dlp` |
| Ordenação do `list` | `service_date DESC, id DESC` | Mais recente primeiro |
| Live no ar sem `duration` (lacuna QA 1) | aceita, com `live_duration: null`; teste com `is_live` sem `duration` | O `yt-dlp` pode não trazer a duração de live em andamento |
| Cookies ausentes (lacuna QA 2) | `YouTubeError` → `youtube_error` (saída 6), mensagem sem caminho | §VI: caminho de segredo não aparece em saída |
| Resolução do caminho dos cookies (lacuna QA 3) | no construtor do `YouTube`, não na importação; teste com `monkeypatch.setenv("WORDCUT_CONFIG")` depois do import | `WORDCUT_CONFIG` definido depois da importação vale |
| Contagens de cortes (lacuna QA 4) | `cut_counts: {"suggested": 0, "chosen": 0, "discarded": 0}` em `list` e `show` | Estados de docs/cli.md §8 |
| Campos de docs/cli.md §7.2 (lacuna QA 5) | `duration: null` (duração da pregação, até haver bordas) em `list`/`show`; `last_task: null` no `show` | Formato estável desde já |
| Hosts e ID (lacuna QA 6) | hosts exatos `youtube.com`, `www.youtube.com`, `m.youtube.com`, `youtu.be`; ID `[A-Za-z0-9_-]{11}` | Rejeita host parecido e ID vazio |
| Prova da corrida (lacuna QA 7) | dublê cujo `info()` insere o mesmo `youtube_id` antes de responder | Reproduz a corrida sem threads |
| `--status` (lacuna QA 8) | `choices` com os cinco estados | Valor fora → `invalid_argument` pelo contrato |
| Guarda contra rede (lacuna QA 9) | fixture `autouse` na suíte da CLI troca `deps.live_source` por dublê que falha se usado; todo teste de `info()` troca `subprocess.run` | Nenhum teste alcança o `yt-dlp` real |
| Relógio (lacuna QA 10) | `create_sermon(..., now=None)`, como `machine_status` | `created_at` determinístico nos testes |
| Comando antigo `info` (lacuna QA 11) | só `test_legacy_commands.py` segue verde | Será removido na migração da CLI |

---

## Ordem de implementação

- [x] **Passo 1 — ID do vídeo e erros do YouTube** — `video_id(url)` com os formatos e a
  rejeição; `YouTubeError` em `info()`; `config.py` e `DEFAULT_COOKIES` vindo dele.
- [x] **Passo 2 — Tabela e repositório** — migração `0002_sermons.sql` e `db/sermons.py`.
- [x] **Passo 3 — Serviço de pregações** — `create_sermon` (novo, idempotente, live no ar,
  erros), `list_sermons` (ordem e filtro), `show_sermon` (`not_found`).
- [x] **Passo 4 — CLI `sermon`** — `add_group`, `Context.warn`, `deps.py`, comandos `create`,
  `list`, `show` com texto legível e JSON; `test_cli.py` com `sermon`.
- [x] **Passo 5 — Documentação** — `docs/architecture/README.md` §4, CHANGELOG.

---

## Riscos

- **`yt-dlp` mudar o formato de erro**: o serviço não interpreta a mensagem do `yt-dlp`; só
  traduz a falha em `youtube_error` genérico.
- **Formatos de link novos do YouTube**: `video_id` testado por tabela; acrescentar formato é
  uma linha.

---

## Fora de escopo

- `--start`, `--end` e `--process` no `create` (itens 3 e 5).
- `sermon show --transcript` (item 5).
- Tabela de cortes (item 9).

---

## Verificação

- [x] `sermon create <link> --json` com dublê de live terminada → `created: true`, campos de
  FR-001, `status: "created"`, saída 0.
- [x] Mesmo vídeo por outro formato de link → `created: false`, mesmo `id`, dublê não é chamado.
- [x] Live no ar → `live_finished: false` e aviso no stderr.
- [x] Link inválido → `invalid_argument` (saída 2), dublê não é chamado.
- [x] Falha do YouTube → `youtube_error` (saída 6), nada gravado.
- [x] `sermon list --json` → `{"items": [...]}` mais recente primeiro; `--status` filtra.
- [x] `sermon show <id> --json` → pregação com bordas nulas e `cuts: []`; ID inexistente →
  `not_found` (saída 3).
- [x] Sem `--json`, saídas legíveis em português.
- [x] Quality gates limpos.
