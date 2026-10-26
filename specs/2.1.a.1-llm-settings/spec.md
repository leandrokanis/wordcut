# Spec: Configurações do LLM, da transcrição e dos segredos (`settings`)

**Issue**: 2.1.a.1 (sem rastreador; o ID é o código do requisito)
**Requisito**: docs/requirements/features/2.1.a-settings.md §2.1.a.1; docs/cli.md §11.1, §16;
constituição §VI
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

O administrador escolhe o modelo do LLM e o modelo do WhisperX e grava a chave do LLM e os
cookies do YouTube sem que eles apareçam de volta. A chave aparece só pelos últimos 4
caracteres; os cookies, só como presentes ou ausentes.

---

## Cenários de aceite

**Cenário: ver as configurações**
- **Dado** uma instalação nova
- **Quando** o administrador roda `wordcut settings show --json`
- **Então** recebe `llm_model: null`, `whisper_model: "large-v3"`, `llm_key: null`,
  `youtube_cookies: false` e `default_preset_id: null`

**Cenário: trocar modelos**
- **Dado** as configurações padrão
- **Quando** o administrador roda `settings set --model <id> --whisper-model <nome>`
- **Então** os novos valores aparecem no `show`

**Cenário: gravar a chave pelo stdin**
- **Dado** uma chave num arquivo
- **Quando** o administrador roda `wordcut settings set-key < chave.txt`
- **Então** a chave é gravada em `WORDCUT_CONFIG` com permissão 600 e o `show` mostra só
  `"llm_key": "••••abcd"` (últimos 4)

**Cenário: gravar os cookies pelo stdin**
- **Dado** um arquivo de cookies
- **Quando** o administrador roda `settings set-cookies < cookies.txt`
- **Então** o arquivo é gravado em `WORDCUT_CONFIG` com permissão 600 e o `show` mostra
  `youtube_cookies: true`

### Casos de borda

- `set-key` sem nada no stdin → `invalid_argument`; nada gravado.
- `set-key` com stdin de terminal → lê sem eco (getpass).
- Chave nunca aparece em saída, erro, log ou progresso; teste procura a chave em stdout e
  stderr.
- Não existe opção de linha de comando que receba segredo.
- Pasta de configuração somente leitura (contêiner) → erro claro, sem o conteúdo.

---

## Requisitos funcionais

- **FR-001**: `settings show` DEVE mostrar modelo do LLM, modelo do WhisperX, chave mascarada
  (últimos 4 ou `null`), presença dos cookies e preset padrão.
- **FR-002**: `settings set [--model] [--whisper-model]` DEVE gravar os valores no SQLite.
- **FR-003**: `settings set-key` e `settings set-cookies` DEVEM ler só do stdin e gravar em
  arquivos de `WORDCUT_CONFIG` com permissão 600, de forma atômica.
- **FR-004**: Segredos NÃO DEVEM aparecer em nenhuma saída; a chave aparece só mascarada.
- **FR-005**: O processamento DEVE usar o modelo do WhisperX configurado.

---

## Escopo

### Componentes em escopo
- `packages/core/src/wordcut/` — tabela de configurações (migração), serviço `settings`,
  gravação de segredos em `config.py`.
- `apps/cli/src/wordcut_cli/settings.py`.
- Testes com `WORDCUT_CONFIG` temporário.

### Fora de escopo
- Presets e critérios (item 8).
- Tela de configurações (fase 3).

---

## Pressupostos

- O modelo do LLM não tem padrão no código: começa `null` e precisa ser escolhido pelo
  administrador antes da primeira sugestão (item 9 falha com erro claro sem ele). O do
  WhisperX é `large-v3`.
