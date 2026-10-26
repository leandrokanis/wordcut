# QA — monorepo — Monorepo com workspace e Docker Compose

## Plano de QA — 2026-10-26

**baseline_commit**: f95f5b132159ee8982675c20507490cee721ccf5
**Componentes em escopo**: `packages/core`, `apps/cli`, `apps/api`, `apps/web`, raiz
(workspace `uv`, `uv.lock`, `compose.yaml`, `docker/python/Dockerfile`, `apps/web/Dockerfile`,
`apps/web/nginx.conf`, `.dockerignore`, `.gitignore`, README, CONTRIBUTING,
`docs/architecture/`, CHANGELOG)
**Suítes que valem como prova**:
- Python (core, cli, api): `uv sync --all-packages` (com `--group dev` se o README
  registrar o fallback do risco 2) → `uv run pytest -q`; estática `uv run ruff check .`,
  `uv run ruff format --check .`, `uv run mypy` e também a forma do CONTRIBUTING §3.2
  `uv run mypy packages/core/src apps/cli/src apps/api/src`.
- Web: `npm --prefix apps/web ci` → `npm --prefix apps/web test`,
  `npm --prefix apps/web run typecheck`, `npm --prefix apps/web run lint`,
  `npm --prefix apps/web run build`.
- Docker (só o projeto Compose `wordcut`, sempre na raiz deste repositório):
  `docker compose config -q`, `docker compose build api web cli`,
  `docker compose up -d api web` → curls → `docker compose down`. Nunca `-p` de outro
  projeto, nunca `docker system prune`, `docker compose down -v` nem comandos sem escopo
  de projeto. Antes e depois, `docker compose ls` deve mostrar as outras stacks da máquina
  idênticas.

Referência de comportamento da CLI: uma worktree descartável do baseline no scratchpad
(`git worktree add <scratchpad>/baseline f95f5b1`), onde se captura `uv run wordcut --help`,
o `--help` de cada subcomando e a saída de `uv run wordcut overview` sobre a mesma
transcrição de exemplo; a worktree é removida em seguida. Mutações manuais são desfeitas na
hora (`git diff` daquela linha limpo antes de seguir).

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Workspace e core | Domínio em `packages/core/src/wordcut/**` movido por rename (sem cópia nem reescrita), sem `cli.py`, com `assets/fonts`; testes do domínio em `packages/core/tests/`; raiz virtual (sem `[project]`) com `[tool.uv.workspace]` listando os três membros, `[tool.uv.sources]`, grupo `dev`, configs de ruff, mypy (`files` dos três `src`) e pytest (`testpaths` dos três `tests`, `--import-mode=importlib`); um único `uv.lock` na raiz; core não importa nem depende de app; `src/` e `tests/` antigos removidos | `git diff -M --name-status f95f5b1` + `git status --short` (entradas `R` para os 17 testes e os módulos do domínio); leitura de `pyproject.toml` e `packages/core/pyproject.toml` (`wordcut-core`, deps atuais, extra `asr`); `find . -name uv.lock -not -path ./.venv/*` = só a raiz; `uv lock --check`; `grep -rE 'wordcut_(cli\|api)' packages/core` vazio; `uv run pytest packages/core -q` verde com a mesma contagem de testes do baseline. Mutação exigida: apagar `assets/fonts/OpenSans-Bold.ttf` temporariamente → `tests/test_captions.py` vermelho (prova que a fonte é achada pelo novo caminho) |
| 2 — CLI | `apps/cli/src/wordcut_cli/__init__.py` com `main` e `build_parser` iguais aos de `src/wordcut/cli.py` do baseline (diff só de imports); `apps/cli/pyproject.toml` (`wordcut-cli`, depende de `wordcut-core`, script `wordcut = "wordcut_cli:main"`); `apps/cli/tests/test_cli.py` verifica que `--help` lista os sete comandos; `uv run wordcut overview` funciona igual | `git diff -M f95f5b1 -- src/wordcut/cli.py apps/cli/` (rename com diff mínimo); `uv run pytest apps/cli -q` verde; comparação textual de `uv run wordcut --help` e de cada `<subcomando> --help` com a worktree do baseline (idênticos, salvo o nome do programa se igual); `uv run wordcut overview <arquivo>` sobre a mesma transcrição de exemplo com saída idêntica à do baseline. Mutação exigida: remover um `add_parser` (ex.: `transcribe-live`) → `test_cli.py` vermelho |
| 3 — API | `create_app()` em `apps/api/src/wordcut_api/app.py`; `GET /api/health` → 200 com `{"status": "ok"}`; `apps/api/pyproject.toml` (`wordcut-api`, depende de `wordcut-core`, `fastapi`, `uvicorn[standard]`); teste via `TestClient` pela fábrica, sem estado global | `uv run pytest apps/api -q` verde; leitura do teste (assert de status e de corpo, não só de status); `uv run uvicorn wordcut_api.app:create_app --factory` sobe local e `curl` responde. Mutações exigidas: trocar `"ok"` por outro valor → vermelho; trocar o caminho da rota (ex.: `/health`) → vermelho |
| 4 — Web | `apps/web` (Vite + React + TS) com `package.json` e `package-lock.json`; `vite.config.ts` com proxy `/api` → `http://127.0.0.1:8781`; `src/api.ts` consulta `/api/health` com caminho relativo (mesma origem); `App.tsx` mostra o estado; `App.test.tsx` com `fetch` dublê cobre sucesso e falha; typecheck (`tsc -b`), lint (ESLint flat) e build verdes; `dist/` ignorado pelo git | `npm --prefix apps/web ci` e os quatro comandos da web; build gera `apps/web/dist/index.html` e assets; `git check-ignore apps/web/dist apps/web/node_modules`; leitura de `vite.config.ts` e `api.ts` (sem URL absoluta). Mutações exigidas: fazer o `App` ignorar a resposta e mostrar um texto fixo → vermelho; trocar a URL consultada → vermelho |
| 5 — Docker | `docker/python/Dockerfile` (base `python:3.12-slim-bookworm`, ffmpeg, `uv`, alvos `api` e `cli`, `ARG WITH_ASR=0`); `apps/web/Dockerfile` (`node:22-alpine` → `nginx:1.27-alpine`); `nginx.conf` com `try_files` e `location /api/` → `http://api:8000` com `proxy_buffering off`; `compose.yaml` com `name: wordcut`, `api`, `web`, `cli` (perfil `tools`, `entrypoint: ["wordcut"]`), bind de dados em `/data` com `WORDCUT_HOME=/data`, `${HOME}/.config/wordcut` → `/config:ro` com `WORDCUT_CONFIG=/config`, `user: "${UID:-1000}:${GID:-1000}"`, portas só em `127.0.0.1` (8780 web, 8781 api); `.dockerignore` cobre `.git`, `.venv`, `node_modules`, `dist`, caches, `*.mp4`, `*.wav`, `*cookies*` | `docker compose config -q`; `docker compose config` (ver `name: wordcut`, `host_ip: 127.0.0.1` em toda porta, `read_only: true` em `/config`, `WORDCUT_HOME`, `user`); `docker compose build api web cli`; `docker compose up -d api web` → `curl -fsS http://127.0.0.1:8780/api/health` = `{"status":"ok"}`, `curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:8780/` = 200, `curl -fsS http://127.0.0.1:8781/api/health`; `docker compose run --rm cli --help`; na imagem `cli`: `python -c` confirma `DEFAULT_FONT.exists()` e ausência de `whisperx`, `find / -name '*cookies*'` vazio fora de `/proc`; `docker compose down`; `docker compose ls` antes/depois com as outras stacks inalteradas |
| 6 — Documentação | README (estrutura, `uv sync --all-packages`, como rodar com `uv` e com Compose, fallback `--group dev` se usado), CONTRIBUTING §3.2 com os comandos que de fato passam, `docs/architecture/README.md` §4 com o estado novo, entrada no CHANGELOG; nenhum caminho `src/wordcut` ou `tests/` antigo restante em docs e `skills/` | `git diff f95f5b1 -- README.md CONTRIBUTING.md docs/architecture/ CHANGELOG.md`; `grep -rnE '(^\|[^/])src/wordcut\|(^\| )tests/' README.md CONTRIBUTING.md docs/ skills/` sem referência ao layout antigo; conferir que cada comando citado em CONTRIBUTING §3.2 roda verde (cruzado com as suítes acima). Sem teste automatizado: verificação documental |

| Critério de aceite | O que o cobre |
|---|---|
| Cenário: comandos atuais continuam funcionando (`uv run wordcut --help`, `uv run wordcut overview <arquivo>`) | `apps/cli/tests/test_cli.py` + comparação de saída com a worktree do baseline (passo 2) |
| Cenário: quality gates da raiz cobrem todos os projetos Python | `uv run pytest -q` coletando de `packages/core/tests`, `apps/cli/tests` e `apps/api/tests` (conferir com `--collect-only -q` que os três aparecem); ruff check/format e mypy verdes (passo 1) |
| Cenário: web verificável | instalação, typecheck, lint, testes e build da web; `apps/web/dist/index.html` gerado (passo 4) |
| Cenário: Compose sobe a aplicação (`up -d --build api web`; página em `http://127.0.0.1:<porta>/`; `/api/health` pela mesma origem = `{"status": "ok"}`) | `docker compose up -d --build api web` + curls na porta da `web` (8780) para `/` e `/api/health` (passo 5) |
| Cenário: CLI no contêiner (`docker compose run --rm cli --help`) | execução do comando e ajuda do `wordcut` com os sete comandos (passo 5) |
| Borda: portas publicadas só em `127.0.0.1` | `docker compose config` com `host_ip: 127.0.0.1` em toda porta; `ss -ltn` com 8780/8781 só em `127.0.0.1` durante o `up` |
| Borda: segredos fora de imagem e de contexto de build | `.dockerignore` com `*cookies*`, `.git`, `.venv`; Dockerfiles sem `COPY`/`ADD` de `~/.config`; `/config` montado `:ro`; `find` de `*cookies*` nas imagens vazio |
| Borda: fonte da legenda (`assets/fonts`) achada pelo domínio | `tests/test_captions.py` (usa `DEFAULT_FONT`) verde em `packages/core/tests` + mutação do passo 1; `DEFAULT_FONT.exists()` também dentro da imagem |
| Borda: worker remoto (`asr/remote.py`) sincroniza o pacote certo | Sem teste no baseline (`tests/test_remote.py` não toca em `PACKAGE_DIR`); prova por inspeção: `uv run python -c` confirmando que `PACKAGE_DIR.name == "wordcut"` e que contém `asr/worker.py`, e que o destino do `rsync` continua `<home>/src/`. Fica PARCIAL se o implementador não acrescentar teste |
| FR-001 — quatro projetos com manifesto, código e testes | `ls` de `pyproject.toml`/`package.json`, `src/` e `tests/` (ou `src/*.test.tsx`) em cada um |
| FR-002 — workspace com lock único; `wordcut` vem de `apps/cli` | `[tool.uv.workspace]` na raiz; um só `uv.lock`; `uv lock --check`; `apps/cli/pyproject.toml` declara o script; `uv run which wordcut` + `[project.scripts]` ausente no core |
| FR-003 — domínio em `packages/core`, importável como `wordcut`, sem depender de app | `uv run python -c "import wordcut"`; `grep` de `wordcut_cli`/`wordcut_api` vazio no core; deps do core sem apps |
| FR-004 — comandos da CLI com o mesmo comportamento | mesmo que o cenário 1 |
| FR-005 — `GET /api/health` → `{"status": "ok"}` | `apps/api/tests/test_health.py` + mutações do passo 3 |
| FR-006 — web compila página que consulta `/api/health` e mostra o resultado | `apps/web/src/App.test.tsx` + build + mutações do passo 4 |
| FR-007 — `compose.yaml` com `api`, `web`, `cli`, volume `WORDCUT_HOME`, segredos `:ro`, portas em `127.0.0.1`, `web` repassa `/api` | `docker compose config` + curl de `/api/health` pela porta da `web` (passo 5) |
| FR-008 — quality gates de CONTRIBUTING §3.2 passam da raiz | os quatro comandos de §3.2, exatamente como escritos no CONTRIBUTING final |
| FR-009 — README, CONTRIBUTING e `docs/architecture/` refletem a estrutura | verificação documental do passo 6 |
| Verificação: `uv sync --all-packages` instala os três projetos | `uv sync --all-packages` limpo + `uv pip list` com `wordcut-core`, `wordcut-cli`, `wordcut-api` |
| Verificação: `uv run pytest -q` roda core, cli e api e passa | suíte Python com `--collect-only` mostrando os três diretórios |
| Verificação: ruff check, ruff format --check e mypy limpos | checagem estática Python |
| Verificação: `uv run wordcut --help` lista `info`, `transcribe`, `transcribe-live`, `overview`, `cut`, `preview`, `short` | `test_cli.py` + execução direta |
| Verificação: `npm --prefix apps/web test`, `typecheck`, `lint` e `run build` passam | suíte web |
| Verificação: `docker compose config -q` sem erro; `build api web cli` constrói | comandos Docker do passo 5 |
| Verificação: `up -d api web` → health `{"status":"ok"}` e página 200; `down` em seguida | curls do passo 5 + `docker compose down` |
| Verificação: `docker compose run --rm cli --help` mostra a ajuda | comando do passo 5 |
| Verificação: portas só em `127.0.0.1` (`host_ip: 127.0.0.1`) | `docker compose config` |
| Verificação: nenhum segredo copiado para imagem | `.dockerignore` + Dockerfiles + `find` nas imagens |
| Verificação: README, CONTRIBUTING e `docs/architecture/` atualizados | passo 6 |

**Lacunas registradas no plano de QA** (detalhe no diário `tdd.md`):
1. Nenhum teste cobre o `PACKAGE_DIR` de `asr/remote.py`; sem teste novo, o caso de borda
   fica PARCIAL.
2. O spec pede `docker compose up -d --build api web`; a Verificação do plano usa
   `up -d api web` depois de `build`. O QA roda a forma do spec (inclui a do plano).
3. CONTRIBUTING §3.2 já cita `uv run mypy packages/core/src apps/cli/src apps/api/src`; o
   plano usa `uv run mypy` com `files`. O QA roda as duas formas.
4. O plano não diz se a imagem instala os pacotes em modo editável; se não for editável, a
   fonte precisa entrar no wheel do `wordcut-core`. Verificado por `DEFAULT_FONT.exists()`
   dentro da imagem.
5. O plano não fixa um arquivo de exemplo para `wordcut overview <arquivo>`; o QA usa a
   mesma transcrição sintética nas duas árvores (baseline e implementação).

## Rodada 1 — 2026-10-26 — working tree sobre f95f5b1

**baseline_commit**: f95f5b132159ee8982675c20507490cee721ccf5
**Componentes avaliados**: `packages/core`, `apps/cli`, `apps/api`, `apps/web`, raiz
(workspace, `uv.lock`, Compose, Dockerfiles, `.dockerignore`, `.gitignore`, documentação)
**Suítes**: Python ✅ (97 / 0 falhas: core 95, cli 1, api 1; baseline 93) · web ✅ (2 / 0
falhas) · ruff check ✅ · ruff format --check ✅ · mypy ✅ (as duas formas, 30 arquivos) ·
`uv lock --check` ✅ · typecheck ✅ · lint ✅ · build ✅ · `docker compose config -q` ✅ ·
`docker compose build api web cli` ✅ · `up -d --build api web` + curls ✅

Fora do escopo desta feature e não julgados: alterações não preparadas em
`specs/3.1.a.3-cli-foundation-lock/` e `specs/active.md`.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Workspace e core | PASS | Módulos do domínio R100 (`git diff -M --stat`), 17 testes por rename (`test_captions.py` +5, `test_remote.py` +26, os demais R100); `src/` e `tests/` antigos ausentes; raiz virtual com `[tool.uv.workspace]` (3 membros), `[tool.uv.sources]`, grupo `dev`, ruff/mypy `files`/pytest `testpaths` + `--import-mode=importlib`; um só `uv.lock`; `uv lock --check` ok; `grep wordcut_(cli\|api)` vazio no core; core 95 = 93 do baseline + 2 novos. Mutação exigida (fonte apagada) → `test_captions.py` vermelho via `test_default_font_ships_with_the_package` |
| 2 — CLI | PASS | `cli.py` → `apps/cli/src/wordcut_cli/__init__.py` R100; `wordcut-cli` com `wordcut = "wordcut_cli:main"`; `test_help_lists_every_command` verde e morre com `transcribe-live` renomeado; `--help`, `--help` dos 7 subcomandos e `overview` (frases, `--words`, `--start/--end`) idênticos byte a byte à worktree do baseline |
| 3 — API | PASS | `create_app()` + `GET /api/health`; `test_health_reports_ok` compara `(status, json)` = `(200, {"status": "ok"})`; mutações `"ok"→"up"` e rota `/health` mortas; `uvicorn wordcut_api.app:create_app --factory` local respondeu `{"status":"ok"}` |
| 4 — Web | PASS | 2 testes com `fetch` dublê (sucesso e 503); mutações da barra mortas (texto fixo `API: ok`, URL `/api/healthz`; também URL absoluta); `api.ts` usa caminho relativo; proxy do Vite → `127.0.0.1:8781`; `dist/index.html` gerado; `dist` e `node_modules` ignorados. Nota fora da barra: `setStatus("ok")` ignorando o corpo sobrevive, porque o dublê de sucesso devolve o mesmo `"ok"` |
| 5 — Docker | PASS | Arquivos conforme as Decisões técnicas; `config`: `name: wordcut`, `host_ip: 127.0.0.1` nas duas portas, `/config` `read_only: true`, `WORDCUT_HOME=/data`, `WORDCUT_CONFIG=/config`, `user: 1000:1000`; build ok; `up -d --build api web` → 8780 `/` 200, rota SPA 200, `/api/health` `{"status":"ok"}`, 8781 `{"status":"ok"}`; `ss` só em `127.0.0.1`; `run --rm cli --help` com os 7 comandos; na imagem `cli`: fonte em `site-packages/wordcut/assets/fonts` (`exists()` True, não editável), `whisperx` ausente, sem `/src`; `docker compose down`; `docker compose ls -a` e `docker ps` idênticos antes e depois. A linha "`find '*cookies*'` vazio" não julga: ver nota abaixo |
| 6 — Documentação | PASS | README (estrutura, `uv sync --all-packages`, dev, web, Compose), CONTRIBUTING §3.2 (cada comando rodado verde como escrito), `docs/architecture/README.md` §4, CHANGELOG; grep sem `src/wordcut`, `tests/` nem `mypy src` em README, CONTRIBUTING, CHANGELOG, `docs/` e `skills/` |

**Linha da matriz que não julga (passo 5 e borda de segredos).** `find / -name '*cookies*'`
nas imagens `api` e `cli` acha `/usr/local/lib/python3.12/http/cookies.py` e
`.../pip/_vendor/requests/cookies.py`; a imagem `python:3.12-slim-bookworm` pura, base fixada
pelo plano, acha os mesmos dois. Nenhum vem do contexto de build; a imagem `web` fica vazia.
O critério literal falharia em qualquer imagem sobre essa base, então não discrimina a
implementação. O QA não o trocou: o veredito do passo se apoia nas outras provas da mesma
linha (`.dockerignore` com `**/*cookies*`, Dockerfiles sem `COPY`/`ADD` de config, só
`/opt/venv` no estágio final, `/config` `:ro`).

**Fatos do implementador, julgados.**
1. Fonte: confirmado. O host tem `/usr/share/fonts/truetype/open-sans/OpenSans-Bold.ttf` e o
   Pillow acha por basename; com a fonte do pacote apagada, 9 testes de `test_captions.py`
   passam e só o novo cai. A barra pedia o arquivo vermelho, e ele fica vermelho.
2. Cookies: confirmado, e os dois arquivos vêm da imagem base (nota acima).
3. `.pyc` velho: risco real; as mutações desta rodada rodaram com `PYTHONPYCACHEPREFIX` novo a
   cada execução. Não muda a barra.

**Mutações sobreviventes fora da barra** (achados, sem efeito no veredito):
- `str(PACKAGE_DIR) + "/"` no `rsync` de `asr/remote.py` passa no teste novo, porque
  `Path()` apaga a barra final; o teste não distingue copiar o diretório `wordcut` de copiar o
  conteúdo dele para `<home>/src/`.
- `setStatus("ok")` ignorando o corpo em `App.tsx` passa nos testes da web.

Efeito colateral: o QA baixou a tag `python:3.12-slim-bookworm` (camadas já existiam, base
das imagens `wordcut`) para a comparação; nenhum contêiner, imagem, volume ou stack de outro
projeto foi tocado.

### Critérios de aceite
- ✅ Cenário: comandos atuais continuam funcionando — `test_cli.py` + comparação byte a byte
  com o baseline (`--help`, 7 subcomandos, `overview`)
- ✅ Cenário: quality gates da raiz cobrem os três projetos Python — `--collect-only`: core 95,
  cli 1, api 1; ruff, format e mypy verdes
- ✅ Cenário: web verificável — `npm ci`, test, typecheck, lint, build; `dist/index.html`
- ✅ Cenário: Compose sobe a aplicação — `up -d --build api web`; 8780 `/` 200 e
  `/api/health` `{"status":"ok"}` pela mesma origem
- ✅ Cenário: CLI no contêiner — `docker compose run --rm cli --help` com os 7 comandos
- ✅ Borda: portas só em `127.0.0.1` — `config` (`host_ip: 127.0.0.1`) e `ss` no `up`
- ✅ Borda: segredos fora de imagem e de contexto — `.dockerignore`, Dockerfiles, `/config`
  `:ro`; `find` com só arquivos da imagem base (linha literal não julga, nota acima)
- ✅ Borda: fonte achada pelo domínio — `test_default_font_ships_with_the_package` + mutação;
  `DEFAULT_FONT.exists()` True na imagem `cli`
- ✅ Borda: worker remoto sincroniza o pacote certo —
  `test_submit_syncs_the_package_that_holds_the_worker` (nome `wordcut`, contém
  `asr/worker.py`, destino `leitao:/opt/cp/src/`); mutações `parents[2]` e `/ "asr"` mortas.
  Lacuna 1 fechada
- ✅ FR-001 — quatro projetos com manifesto, código e testes
- ✅ FR-002 — `[tool.uv.workspace]`, um `uv.lock`, `uv lock --check`, `wordcut` de
  `apps/cli` (`uv run which wordcut` → `.venv/bin/wordcut`), core sem `[project.scripts]`
- ✅ FR-003 — `import wordcut` resolve em `packages/core/src`; core sem dependência de app
- ✅ FR-004 — mesmo que o cenário 1
- ✅ FR-005 — `test_health.py` + mutações
- ✅ FR-006 — `App.test.tsx` + build + mutações da barra
- ✅ FR-007 — `docker compose config` + curl de `/api/health` pela porta da `web`
- ✅ FR-008 — os comandos de CONTRIBUTING §3.2, como escritos, verdes
- ✅ FR-009 — verificação documental do passo 6
- ✅ Verificação: `uv sync --all-packages` instala `wordcut-core`, `wordcut-cli`, `wordcut-api`
- ✅ Verificação: `uv run pytest -q` roda core, cli e api e passa (97)
- ✅ Verificação: ruff check, format --check e mypy limpos
- ✅ Verificação: `uv run wordcut --help` lista os 7 comandos
- ✅ Verificação: web test, typecheck, lint e build
- ✅ Verificação: `config -q` e `build api web cli`
- ✅ Verificação: `up` → health `{"status":"ok"}` e página 200; `down` em seguida
- ✅ Verificação: `run --rm cli --help`
- ✅ Verificação: portas só em `127.0.0.1`
- ✅ Verificação: nenhum segredo copiado para imagem (nota do `find` acima)
- ✅ Verificação: README, CONTRIBUTING e `docs/architecture/` atualizados

### Veredito geral: PASS
Seis passos PASS contra a barra, lacuna 1 fechada por teste com mutação morta. A linha
"`find '*cookies*'` vazio" da matriz não julga; duas mutações fora da barra sobreviveram e
ficam como achado para o review.
