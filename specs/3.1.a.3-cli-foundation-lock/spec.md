# Spec: Base da CLI, trava de processamento e `wordcut status`

**Issue**: 3.1.a.3 (sem rastreador; o ID é o código do requisito)
**Requisito**: docs/requirements/features/3.1.a-processing-lock-and-status.md §3.1.a.3, §3.1.a.1;
docs/cli.md §3, §4, §5, §6.4, §10, §14
**Branch**: `mvp` (branch única da execução automatizada; ver specs/roadmap.md)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

O administrador e os agentes precisam de uma CLI `wordcut` com contrato previsível (saída
JSON, erros com código estável, códigos de saída fixos) e de um jeito de saber se a máquina
está ocupada. Este item cria a fundação que todos os outros comandos usam: onde os dados
ficam, o banco criado sozinho, o contrato de saída e erro, a trava global de um processamento
por vez e o comando `wordcut status`.

---

## Cenários de aceite

**Cenário: status com a máquina livre**
- **Dado** que nenhuma operação pesada está rodando
- **Quando** o administrador roda `wordcut status --json`
- **Então** o stdout traz um único objeto JSON com `"lock": {"held": false}` e a saída é 0

**Cenário: status com a máquina ocupada**
- **Dado** que outro processo segura a trava para uma operação descrita
- **Quando** o administrador roda `wordcut status --json`
- **Então** o JSON traz `held: true`, o tipo da operação, o recurso, o PID e o início, e a
  saída é 0

**Cenário: segunda operação pesada recusada (3.1.a.1)**
- **Dado** que outro processo segura a trava
- **Quando** uma operação que exige a trava é iniciada
- **Então** ela falha na hora com o código `busy` e a saída 4, e `details` diz o que roda e
  desde quando, sem fila

**Cenário: trava liberada quando o processo morre**
- **Dado** que um processo segurava a trava e morreu sem liberá-la
- **Quando** `wordcut status` é chamado
- **Então** a trava aparece livre

**Cenário: erro em JSON**
- **Dado** uma chamada com argumento inválido e `--json`
- **Quando** o comando roda
- **Então** o stdout traz só `{"error": {"code": "invalid_argument", "message": …}}`, em
  português no `message`, e a saída é 2

**Cenário: primeira execução cria o banco**
- **Dado** um `WORDCUT_HOME` vazio
- **Quando** qualquer comando roda
- **Então** a pasta e o banco são criados com o esquema atual, sem `wordcut init`

### Casos de borda

- `--json` antes ou depois do subcomando dá o mesmo resultado.
- Sem `--json`, o erro vai para o stderr como texto e o stdout fica vazio.
- Erro não previsto vira `internal_error` com saída 1, sem traceback no stdout.
- Ctrl+C sai com 130.
- Banco de uma versão de esquema anterior é migrado na abertura, sem perder dados.
- `--version` imprime a versão e sai com 0.

---

## Requisitos funcionais

- **FR-001**: O executável `wordcut` DEVE aceitar as opções globais `--json`, `--quiet`,
  `--version` e `--help`, com `--json` e `--quiet` válidos antes ou depois do subcomando.
- **FR-002**: Com `--json`, o stdout DEVE conter exatamente um documento JSON: objeto,
  `{"items": [...]}` ou `{"error": {...}}`.
- **FR-003**: O stdout DEVE conter só o resultado; progresso, avisos e logs DEVEM ir para o
  stderr, e `--quiet` DEVE suprimir o progresso.
- **FR-004**: Os erros DEVEM seguir o objeto `{"error": {"code", "message", "details"?}}`
  e os códigos de saída de docs/cli.md §5.1 (0, 1, 2, 3, 4, 5, 6, 130).
- **FR-005**: O mapeamento código de erro → saída DEVE ser central, para que todo comando
  futuro herde o contrato.
- **FR-006**: Os dados DEVEM ficar em `~/.local/share/wordcut/`, ou em `WORDCUT_HOME` quando
  definido; o banco SQLite DEVE ser criado e migrado automaticamente.
- **FR-007**: DEVE existir uma trava global do sistema operacional, compartilhada por todo
  processo `wordcut` (CLI e futuro servidor), liberada sozinha se o processo morrer.
- **FR-008**: Tentar adquirir a trava ocupada DEVE falhar imediatamente com `busy`
  (saída 4), com `details` contendo tipo da operação, recurso, PID e início.
- **FR-009**: `wordcut status` DEVE mostrar se a trava está livre ou, se ocupada, quem a
  segura (tipo, recurso, PID, início e tempo decorrido), em texto ou JSON.
- **FR-010**: `wordcut status` NÃO DEVE ser bloqueado pela trava.

---

## Entidades e dados

- **Banco**: arquivo SQLite em `WORDCUT_HOME`, com versão de esquema registrada para
  migrações.
- **Trava**: arquivo de trava em `WORDCUT_HOME`, com a descrição de quem a segura (tipo da
  operação, recurso, PID, início).

---

## Escopo

### Componentes em escopo
- `src/wordcut/cli.py` — novo ponto de entrada com o contrato global (opções, saída, erros).
- `src/wordcut/` — novas áreas: configuração de caminhos (`WORDCUT_HOME`), banco e
  migrações, trava global, erros de domínio com código e saída.
- `tests/` — testes de comportamento do contrato, do banco, da trava e do `status`.

### Fora de escopo
- Tarefas em segundo plano, `--wait` e `task` (item 4 do roadmap).
- Recursos (`sermon`, `cut`…) e qualquer tabela de domínio além do controle de esquema.
- Remoção dos comandos antigos (`info`, `live`, `cut`, `short`…): continuam funcionando até o
  item `cli-migration`.
- Servidor web.

---

## Pressupostos

- Os comandos antigos convivem com os novos no mesmo executável até o item `cli-migration`;
  eles não precisam seguir o contrato novo.
- Enquanto não há tarefas, a descrição de quem segura a trava é a operação em curso (tipo e
  recurso); o ID de tarefa entra no item 4.
- A trava vale para a máquina inteira por meio de um arquivo dentro de `WORDCUT_HOME`;
  processos com `WORDCUT_HOME` diferentes não se enxergam, o que permite testes isolados.
