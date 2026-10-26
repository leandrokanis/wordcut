# Roadmap de desenvolvimento do MVP

Plano de execução do MVP do Wordcut (ondas 1–5 de
[docs/requirements/features.md](../docs/requirements/features.md)), na branch `mvp`.

## Regras da execução automatizada

Definidas pelo administrador em 2026-10-26:

- Cada item passa por `/dev-specify` → `/dev-plan` → `/dev-implement-qa`, nesta ordem.
- Toda decisão que as skills levariam ao desenvolvedor é tomada pela recomendação do
  agente, registrada no `plan.md` do item, sem parar para perguntar.
- Tudo na branch `mvp`, um commit por item. Sem push e sem PR.
- O ID de cada item é o código da história principal; a pasta é `specs/<código>-<nome>/`.
- Item que não chegar a PASS no limite de rodadas é commitado como `WIP` com as pendências
  anotadas aqui, e a execução segue para o próximo, para a branch não acumular mudança
  solta.
- Quality gates antes de cada commit: `uv run pytest`, `uv run ruff check .`,
  `uv run ruff format --check .`, `uv run mypy src`; na interface, typecheck e lint.
- Testes nunca chamam serviço externo de verdade: YouTube, WhisperX, OpenRouter e
  renderização longa são dublês. Nenhum vídeo real é renderizado sem pedido explícito.
- Segredos (chave do LLM, cookies) nunca são lidos, exibidos ou registrados.
- Convenções de [CONTRIBUTING.md](../CONTRIBUTING.md): monorepo, clean code, XP, política de
  comentários. Decisão de arquitetura nova vira ADR e atualiza `docs/architecture/` e o README
  no mesmo commit.

## Pendências do administrador

- Instalar o NVIDIA Container Toolkit no host, para a GPU aparecer nos contêineres
  (ADR-0003, ADR-0011). Sem ele, a transcrição só roda pela CLI no host.

- Revisar, por pessoa qualificada, o texto dos critérios em
  `packages/core/src/wordcut/criteria/texts/` (item 8) antes de usar as sugestões em produção
  (constituição §I).

## Ordem

CLI primeiro (constituição §II): ela cobre o fluxo inteiro e é a base que a web reaproveita.
Depois o servidor e, por fim, a interface, seguindo o protótipo
([docs/prototype/wordcut.html](../docs/prototype/wordcut.html)) e a especificação da CLI
([docs/cli.md](../docs/cli.md)).

### Fase 0 — Estrutura

| # | ID | Item | Cobre | Estado |
|:-:|---|---|---|---|
| 0 | monorepo | Monorepo (`packages/core`, `apps/cli`, `apps/api`, `apps/web`), workspace `uv`, Docker Compose | ADR-0002, ADR-0003 | ☑ |

### Fase 1 — Camada de serviço e CLI

| # | ID | Item | Cobre | Estado |
|:-:|---|---|---|---|
| 1 | 3.1.a.3 | Base: SQLite, contrato da CLI (`--json`, erros, saídas), trava e `status` | 3.1.a.1, 3.1.a.3 | ☑ |
| 2 | 1.1.a.1 | `sermon create`, `list`, `show` | 1.1.a.2 | ☑ |
| 3 | 1.1.b.2 | `sermon trim` | — | ☑ |
| 4 | 3.1.a.2 | Tarefas: processo destacado, `--wait`, `task list/show/wait` | — | ☑ |
| 5 | 1.1.c.1 | `sermon process`: baixar a faixa, transcrever, cortar em 16:9, palavras no SQLite | 1.1.c.2, 1.1.c.3, 1.1.b.3 | ☑ |
| 6 | 1.1.d.1 | `sermon download` | — | ☑ |
| 7 | 2.1.a.1 | `settings`: modelo, chave e cookies pelo stdin, modelo do WhisperX | — | ☑ |
| 8 | 2.1.a.2 | Critérios no pacote, `criteria list` e `preset` | 2.1.a.3 | ☑ |
| 9 | 2.1.b.1 | Sugestão de cortes pelo LLM ao fim do processamento | 2.1.b.3 | ☑ |
| 10 | 2.1.b.2 | `sermon suggest` | — | ☐ |
| 11 | 1.1.e.1 | `cut list/show/choose/discard/restore` | 1.1.e.2 | ☐ |
| 12 | 1.1.g.1 | `cut preview` (sequência da prévia) | — | ☐ |
| 13 | 1.1.f.2 | `cut fix-word` com a trava de grafia | 1.1.f.3 | ☐ |
| 14 | 1.1.f.4 | `cut caption` | 1.1.f.5 | ☐ |
| 15 | 1.1.h.1 | `cut render` com opções e `--estimate` | 1.1.h.2, 1.1.h.3 | ☐ |
| 16 | 1.1.i.1 | `render list/show/download` | — | ☐ |
| 17 | 1.2.a.1 | `member` | — | ☐ |
| 18 | cli-migration | Remover a CLI antiga e reescrever README e skills sobre a nova | — | ☐ |

### Fase 2 — Servidor

| # | ID | Item | Cobre | Estado |
|:-:|---|---|---|---|
| 19 | 1.2.a.2 | App `api`: FastAPI no Compose, identidade pelo Cloudflare Access e papéis | — | ☐ |
| 20 | web-api | Rotas da API sobre a camada de serviço e progresso das tarefas por SSE | — | ☐ |

### Fase 3 — Interface web (React + Vite + TypeScript)

| # | ID | Item | Cobre | Estado |
|:-:|---|---|---|---|
| 21 | web-shell | Navegação em três níveis, barra de status, lista de pregações e Nova pregação | 1.1.a.1 (web) | ☐ |
| 22 | 1.1.b.1 | Nível 2: prévia 16:9, timeline, delimitar pelas bordas, processar | 1.1.b.3, 1.1.c.2 (web) | ☐ |
| 23 | 1.1.e-web | Nível 2: painel de cortes | 1.1.e.1, 1.1.e.2 (web) | ☐ |
| 24 | 1.1.g-web | Nível 3: prévia 9:16 sem renderizar, abas Texto e Legenda, grafia na prévia | 1.1.g.1, 1.1.f (web) | ☐ |
| 25 | 1.1.h-web | Caixa de exportação e downloads | 1.1.h.1, 1.1.h.3, 1.1.i.1 (web) | ☐ |
| 26 | 2.1.a-web | Configurações e equipe | 2.1.a, 1.2.a.1 (web) | ☐ |

## Registro

| Item | Resultado | Commit | Observações |
|---|---|---|---|
| 0 monorepo | PASS na rodada 1 | aafe521 | Mutações fora da barra que sobreviveram (ver qa.md): barra final no `rsync` do worker remoto; `setStatus("ok")` fixo na web. Cobrir quando a web real chegar (fase 3). |
| 1 3.1.a.3 | PASS na rodada 2 | (ver git log) | Rodada 1 PARCIAL: erro de uso dos comandos antigos passou a seguir o contrato; decisão mantida e documentada na ADR-0012. |
| 2 1.1.a.1 | PASS na rodada 1 | (ver git log) | Erro de cookies ausentes passou a `youtube_error` sem caminho (decisão 2). |
| 3 1.1.b.2 | PASS na rodada 1 | (ver git log) | `parse_timestamp` ficou estrito (vale também para os comandos antigos). Criação com bordas valida antes do insert; falha entre os dois commits deixaria pregação `created` sem bordas (aceito). |
| 4 3.1.a.2 | PASS na rodada 1 | (ver git log) | ADR-0013 (trava herdada). Ordem "solta a trava antes do estado final" está no código, mas sem teste que pegue a inversão (janela de microssegundos). |
| 5 1.1.c.1 | PASS na rodada 3 | (ver git log) | ADR-0014. Rodadas 1–2 PARCIAL: revalidação no `admit` e `failed` gravado no erro (inclusive exceção inesperada). Processamento real (YouTube + WhisperX) ainda não exercitado fora dos dublês. |
| 6 1.1.d.1 | PASS na rodada 2 | (ver git log) | Cópia sem sobrescrever por hard link, com queda para `open("x")` em sistemas sem link (nome final existe pela metade durante a cópia nesse caso). |
| 7 2.1.a.1 | PASS na rodada 3 | (ver git log) | ADR-0015: erro de uso nunca repete valor digitado (rodadas 1–2 acharam eco da chave). Mutações fora da barra: fallback "Uso inválido" e legado ignorando sobra (sem eco hoje). |
| 8 2.1.a.2 | PASS na rodada 2 | (ver git log) | Texto dos critérios tirado de `sugerir-cortes.md` e do protótipo; duas linhas de opção não literais (reordenar). Revisão humana pendente. |
| 9 2.1.b.1 | PASS na rodada 2 | (ver git log) | ADR-0016. Falha da sugestão fica em `suggestion_error`, sem desfazer o processamento. Nenhuma chamada real ao OpenRouter feita. |
