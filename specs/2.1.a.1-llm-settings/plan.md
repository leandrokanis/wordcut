# Plan: Configurações do LLM, da transcrição e dos segredos (`settings`)

**Issue**: 2.1.a.1
**Feature**: specs/2.1.a.1-llm-settings
**Data**: 2026-10-26

---

## Resumo

Tabela de configurações chave-valor no SQLite (modelos), segredos em arquivos de
`WORDCUT_CONFIG` com permissão 600 (chave do LLM e cookies), serviço `settings` que nunca
devolve segredo em claro, e o grupo `settings` na CLI com leitura de segredo só pelo stdin.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Componentes em escopo

- `packages/core/src/wordcut/` — migração, `config.py` (segredos), `service/settings.py`.
- `apps/cli/src/wordcut_cli/settings.py`.

---

## Contexto de código

| Situação | Path |
|---|---|
| Criar | `packages/core/src/wordcut/db/migrations/<próximo número>_settings.sql` — tabela `settings(key PRIMARY KEY, value)` |
| Alterar | `packages/core/src/wordcut/config.py` — `llm_key_file()`, `write_secret(path, content)` atômico com 600, `read_llm_key()` (só para quem chama o LLM), `has_youtube_cookies()` |
| Criar | `packages/core/src/wordcut/service/settings.py` — `show_settings(conn)`, `update_settings(conn, llm_model=None, whisper_model=None)`, `store_llm_key(text)`, `store_youtube_cookies(text)`, `whisper_model(conn)`, `llm_model(conn)` |
| Criar | `apps/cli/src/wordcut_cli/settings.py` — `settings show`, `settings set`, `settings set-key`, `settings set-cookies` |
| Criar | `packages/core/tests/test_settings_service.py`, `packages/core/tests/test_secrets.py`, `apps/cli/tests/test_settings_command.py` |
| Alterar | `docs/architecture/README.md` §4, `CHANGELOG.md`, `SECURITY.md` (nomes dos arquivos de segredo) |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python (core, cli) | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

Testes usam `WORDCUT_CONFIG` e `WORDCUT_HOME` temporários; nunca a pasta real.

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Onde ficam os modelos | tabela `settings` chave-valor; chaves `llm_model`, `whisper_model` | Configuração comum no banco; segredo fora dele (§VI) |
| Padrões | `llm_model = null` (sem padrão no código); `whisper_model = "large-v3"` | Não escolher modelo pelo administrador |
| Arquivos de segredo | `WORDCUT_CONFIG/openrouter-key` e `WORDCUT_CONFIG/youtube-cookies.txt` | Nome dos cookies já usado pelo `yt-dlp` |
| Gravação | `os.open(tmp, O_WRONLY \| O_CREAT \| O_EXCL, 0o600)` + `os.replace`; pasta criada com 0700 | Nunca existe um instante com permissão aberta |
| Leitura do stdin | `sys.stdin.read()` sem terminal; `getpass.getpass()` com terminal; `strip()` na chave; cookies gravados como vieram | Sem argumento de linha de comando com segredo |
| Validação | chave vazia → `invalid_argument`; cookies vazios → `invalid_argument`; cookies sem linha no formato Netscape → `invalid_argument` | Evita gravar lixo |
| Máscara | `"••••" + key[-4:]`; chave com menos de 8 caracteres → `"••••"` | Não revela chave curta inteira |
| Pasta somente leitura | `PermissionError`/`OSError` → `WordcutError("config_not_writable", …)` saída 5, sem conteúdo | Contêiner monta `/config:ro` |
| Uso do modelo do WhisperX | o processamento lê `whisper_model(conn)` | FR-005 |
| Testes de vazamento | todo teste de `set-key` procura a chave no stdout, no stderr e no `show` | §VI |
| Código de erro da pasta somente leitura | `config_not_writable`, saída 5, em `errors.EXIT_CODES`, `docs/cli.md` §5.3 e `test_errors.py` | Lacuna 1 do QA; decisão do orquestrador |
| Argumento extra em `set-key`/`set-cookies` | `invalid_argument` com mensagem genérica e `details` sem o texto recebido; teste procura o valor em stdout e stderr | Lacuna 2 do QA; o erro de uso padrão ecoa o argumento |
| `set-cookies` com stdin de terminal | `invalid_argument` pedindo `wordcut settings set-cookies < arquivo` | Lacuna 3 do QA; `getpass` lê uma linha só |
| `settings set` sem opções ou com valor vazio | `invalid_argument` com `details.argument`, nada alterado | Lacuna 4 do QA |
| Modelo do WhisperX no processamento | `default_gateways(whisper_model)` → `LocalTranscriber(model=…)`; a tarefa `process` lê `whisper_model(conn)`; dublês existentes ajustados | Lacuna 5 do QA |
| Temporário do segredo | `tempfile.mkstemp` na mesma pasta, `chmod 600` antes de escrever, `os.replace`; temporário órfão não bloqueia | Lacuna 6 do QA; substitui o `O_EXCL` com nome fixo |
| `read_llm_key()` | fica para o item 9 (2.1.b.1); aqui só a máscara, que lê a chave e devolve os últimos 4 | Lacuna 7 do QA; sem código morto |
| Isolamento de `WORDCUT_CONFIG` | fixture autouse no `conftest.py` da raiz aponta para `tmp_path` | Lacuna 8 do QA |
| Formato Netscape aceito | ao menos uma linha não comentada com 7 campos separados por TAB; cabeçalho opcional | Lacuna 9 do QA |
| Ajuda e registro na CLI | `test_cli.py::COMMANDS` inclui `settings`; o `--help` diz "administrador" e traz exemplo | Lacuna 10 do QA; docs/cli.md §3.2, §3.5 |
| Erro de uso não repete valor digitado (regra global, ADR-0015, complementa a ADR-0012) | escolha inválida → `Valor inválido para <destino>; use um de: a, b, c.` com `details {"argument", "choices"}`; argumento não reconhecido (posicional, opção inexistente, valor colado ao hífen) → nunca repetido, nem como nome de opção: `Argumento não reconhecido; veja wordcut <comando> --help.` sem `details`, com `<comando>` vindo do parser; nome de opção só quando a opção existe no parser e pela definição dele (`--stat` abreviado aparece como `--status`); sem ramo próprio para comando de segredo (a regra geral recusa antes de ler o stdin); valor de tipo inválido → `Valor inválido para <destino>.`; testes procuram o valor em stdout e stderr, com e sem `--json`, em `settings set-key`, `settings <chave>`, `settings --key <chave> set-key` em comando comum (`sermon show`, `sermon list -sk-ficticia`) e com segredo em forma de opção (`--sk-or-v1-ficticia` em `sermon list`, `settings set`, `settings set-key` e na raiz, nada gravado); a recusa do argumento extra de `set-key`/`set-cookies` é testada com stdin cheio | Achados das Rodadas 1 e 2 do QA (passo 3 FAIL e PARCIAL); decisão final do orquestrador |
| Docstring de `config.py` | corrigida: o código lê a chave só para mascarar (e, no item 9, para chamar o LLM) | Contradição apontada pelo QA |

---

## Ordem de implementação

- [x] **Passo 1 — Segredos** — `write_secret` atômico com 600, máscara, presença dos cookies.
- [x] **Passo 2 — Tabela e serviço** — migração e `service/settings.py` (show, update, store).
- [x] **Passo 3 — CLI** — `settings show/set/set-key/set-cookies` com stdin e getpass.
- [x] **Passo 4 — Uso** — o processamento (se já existir) lê o modelo do WhisperX da configuração.
- [x] **Passo 5 — Documentação** — `docs/architecture/README.md` §4, CHANGELOG, SECURITY.md.

---

## Fora de escopo

- Presets e critérios (item 8). O `default_preset_id` aparece como `null` até lá.

---

## Verificação

- [x] Instalação nova → `settings show --json` com `llm_model: null`, `whisper_model: "large-v3"`,
  `llm_key: null`, `youtube_cookies: false`, `default_preset_id: null`.
- [x] `settings set --model x --whisper-model y` → refletido no `show`.
- [x] `set-key < arquivo` → arquivo 600 em `WORDCUT_CONFIG`; `show` com `••••` + 4 últimos; chave
  ausente de stdout e stderr.
- [x] `set-cookies < arquivo` → arquivo 600; `youtube_cookies: true`.
- [x] stdin vazio → `invalid_argument`, nada gravado.
- [x] Pasta somente leitura → `config_not_writable`, sem conteúdo.
- [x] Quality gates limpos.
