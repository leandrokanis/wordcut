## Plano de QA

baseline_commit: f95f5b132159ee8982675c20507490cee721ccf5

01:05  📐 BARRA   passo 1 — domínio movido por rename e testes verdes da raiz
       git diff -M --name-status + uv run pytest packages/core: prova
       histórico preservado e mesma contagem de testes do baseline

01:05  🧬 EXIGE   apagar assets/fonts/OpenSans-Bold.ttf  ·  vermelha
       test_captions.py tem de cair; prova que a fonte é achada no core

01:06  📐 BARRA   passo 2 — CLI com o mesmo comportamento
       diff com a worktree do baseline (--help, --help de cada subcomando e
       overview sobre a mesma transcrição); o teste só cobre --help

01:06  🧬 EXIGE   remover o add_parser de transcribe-live  ·  vermelha
       test_cli.py tem de cair; prova que o teste lista os sete comandos

01:07  📐 BARRA   passo 3 — GET /api/health devolve {"status": "ok"}
       TestClient sobre create_app(); assert de status e de corpo

01:07  🧬 EXIGE   trocar "ok" e trocar o caminho da rota  ·  vermelha
       sobreviver a qualquer uma prova teste que só olha o status

01:08  📐 BARRA   passo 4 — página consulta /api/health e mostra o estado
       Vitest + Testing Library com fetch dublê; build gera dist/index.html

01:08  🧬 EXIGE   App mostra texto fixo; URL consultada trocada  ·  vermelha
       prova que o teste observa a resposta, não só a renderização

01:09  📐 BARRA   passo 5 — Compose wordcut sobe api e web; cli roda
       docker compose config/build/up/run só no projeto wordcut, curl em
       8780 (/ e /api/health) e 8781; docker compose ls antes e depois

01:09  📐 BARRA   passo 6 — documentação reflete a estrutura nova
       verificação documental + grep de caminhos antigos; comandos de
       CONTRIBUTING §3.2 conferidos contra as suítes

01:10  ⚠️ LACUNA  asr/remote.py: nenhum teste cobre PACKAGE_DIR
       sem teste novo, o caso de borda do worker remoto fica PARCIAL

01:10  ⚠️ LACUNA  spec usa up -d --build; Verificação do plano usa up -d
       o QA roda a forma do spec, que inclui a do plano

01:10  ⚠️ LACUNA  mypy: plano usa files na config; CONTRIBUTING cita paths
       o QA roda as duas formas; divergência entre elas é FAIL do passo 1

01:11  ⚠️ LACUNA  instalação editável ou não na imagem não foi decidida
       se não for editável, a fonte tem de ir no wheel; prova por
       DEFAULT_FONT.exists() dentro da imagem cli

01:11  ⚠️ LACUNA  sem arquivo de exemplo para wordcut overview <arquivo>
       o QA usa a mesma transcrição sintética no baseline e na
       implementação

## Rodada 1 · implementador

01:06  ▶ INÍCIO   passos 1–6 do plan.md · baseline 93 testes (f95f5b1)

01:07  🔴 RED    packages/core/tests (suíte do domínio movida)
       o domínio movido por git mv para packages/core é importável como
       wordcut e os 93 testes do baseline rodam da raiz
       passo 1; FR-002, FR-003; barra do passo 1 no qa.md
       E   ModuleNotFoundError: No module named 'wordcut'

01:07  🟢 GREEN  packages/core/tests  ·  93 passed
       raiz virtual com workspace, sources, grupo dev e configs de ruff,
       mypy e pytest (importlib); packages/core/pyproject.toml wordcut-core

01:08  🔴 RED    test_submit_syncs_the_package_that_holds_the_worker
       submit() manda ao rsync o diretório wordcut que contém
       asr/worker.py, para <home>/src/ (subprocess.run é o dublê)
       borda do spec (worker remoto); lacuna 1 do qa.md
       caracterização: passou de primeira; RED por mutação
       PACKAGE_DIR = parents[2] → AssertionError: 'src' != 'wordcut'

01:08  🟢 GREEN  test_submit_syncs_the_package_that_holds_the_worker  ·  5 passed
       mutação desfeita; remote.py idêntico ao baseline

01:08  ⚠️ ACHADO  apagar OpenSans-Bold.ttf não derruba test_captions.py
       o Pillow cai na cópia do sistema em /usr/share/fonts por basename;
       a mutação exigida pela barra não pegava nada nesta máquina

01:08  🔴 RED    test_default_font_ships_with_the_package
       a fonte da legenda vem dentro do pacote wordcut (vale na imagem
       slim, sem fontes do sistema)
       borda do spec (assets/fonts); mutação do passo 1 no qa.md
       E       AssertionError: assert False (fonte movida para fora)

01:08  🟢 GREEN  test_default_font_ships_with_the_package  ·  10 passed

01:09  ⚠️ NOTA    mutação de mesmo tamanho no mesmo segundo deixa .pyc velho
       PACKAGE_DIR parents[1]/[2] restaurado no mesmo segundo manteve o
       bytecode mutado; limpar __pycache__ após mutar evita falso vermelho

01:09  ✅ PASSO 1/6 — Workspace e core  ·  +2 testes  ·  suíte 95
       uv lock --check ok; ruff, format e mypy (27 arquivos) limpos;
       core sem wordcut_cli/wordcut_api

01:09  🔴 RED    test_help_lists_every_command
       wordcut --help, vindo de apps/cli, lista os sete comandos atuais
       passo 2; FR-002, FR-004; cenário "comandos atuais continuam"
       E   ModuleNotFoundError: No module named 'wordcut_cli'

01:10  🟢 GREEN  test_help_lists_every_command  ·  1 passed
       apps/cli/pyproject.toml wordcut-cli com script wordcut; módulo
       movido por git mv (R100, sem mudar uma linha)

01:10  ✅ PASSO 2/6 — CLI  ·  +1 teste  ·  suíte 96
       --help, --help dos sete subcomandos e overview (frases e --words)
       idênticos à worktree do baseline sobre a mesma transcrição sintética

01:11  🔴 RED    test_health_reports_ok
       GET /api/health na app criada por create_app() devolve 200 e
       {"status": "ok"} (status e corpo na mesma asserção)
       passo 3; FR-005
       E   ModuleNotFoundError: No module named 'wordcut_api.app'

01:11  🟢 GREEN  test_health_reports_ok  ·  1 passed
       aviso de depreciação do Starlette sobre httpx (terceiro); trocar
       por httpx2 foi negado pelo classificador, fica httpx

01:11  ✅ PASSO 3/6 — API  ·  +1 teste  ·  suíte 97
       uvicorn wordcut_api.app:create_app --factory subiu em 127.0.0.1;
       curl /api/health → {"status":"ok"}; mypy nas duas formas limpo

01:13  🔴 RED    shows the status the API reports
       a página consulta /api/health (caminho relativo) e mostra o status
       que a API devolve; fetch dublê só responde nessa URL
       passo 4; FR-006
       Error: Failed to resolve import "./App" from "src/App.test.tsx"

01:13  🟢 GREEN  shows the status the API reports  ·  1 passed

01:13  🔴 RED    shows the API as unavailable when the health check fails
       resposta de erro (503) vira "API: indisponível", não o corpo cru;
       com o caso de sucesso, derruba texto fixo na página
       passo 4; FR-006; mutação "texto fixo" do qa.md
       → Unable to find an element with the text: API: indisponível

01:14  🟢 GREEN  shows the API as unavailable when the health check fails
       ·  2 passed
       mutações conferidas e desfeitas: URL /api/healthz → 1 failed;
       texto fixo "API: ok" → 1 failed

01:14  ✅ PASSO 4/6 — Web  ·  +2 testes  ·  suíte web 2
       npm ci, test, typecheck (tsc -b), lint e build verdes; dist/ e
       node_modules/ ignorados; proxy do Vite → 127.0.0.1:8781 conferido
       com uvicorn local (curl via vite → {"status":"ok"})

01:17  ✅ PASSO 5/6 — Docker  ·  verificado por comando (sem teste unitário)
       compose config -q ok (name wordcut, host_ip 127.0.0.1, /config
       read_only, WORDCUT_HOME/CONFIG, user 1000:1000); build api web cli
       ok; up -d --build api web → 8780 / = 200, 8780 e 8781 /api/health
       = {"status":"ok"}; ss: só 127.0.0.1; run --rm cli --help mostra os
       sete comandos; na imagem cli DEFAULT_FONT.exists() True (instalação
       não editável, fonte no wheel) e whisperx ausente; down; compose ls
       das outras stacks idêntico antes e depois

01:17  ⚠️ ACHADO  find / -name '*cookies*' nas imagens python não fica vazio
       acha só módulos de terceiros/stdlib: http/cookies.py e
       pip/_vendor/requests/cookies.py; nenhum arquivo de cookies do
       usuário; imagem web vazia

01:19  ✅ PASSO 6/6 — Documentação  ·  verificação documental
       README (estrutura, uv sync --all-packages, dev, Compose),
       CONTRIBUTING §3.2 (comandos rodados verdes como escritos),
       docs/architecture §4 e CHANGELOG; grep sem src/wordcut, tests/
       nem "mypy src" em README, CONTRIBUTING, docs/ e skills/

01:19  🏁 FIM     suíte Python 97 (core 95, cli 1, api 1) · web 2
       ruff, format, mypy (as duas formas), uv lock --check, npm test,
       typecheck, lint, build e compose config verdes; um só uv.lock

## Rodada 1 · QA

01:20  📊 SUÍTE  python 97 passed (core 95, cli 1, api 1)  ·  0 failed
       baseline f95f5b1: 93 passed; core 95 = 93 + 2 testes novos

01:20  📊 SUÍTE  web 2 passed  ·  0 failed
       npm ci, typecheck (tsc -b), lint e build verdes; dist/index.html

01:21  🧬 MUTAÇÕES · python (barra + lacuna 1)  ·  6 de 7 mortas
       ☠️  remote.py PACKAGE_DIR parents[2]                    1 teste
       ☠️  remote.py PACKAGE_DIR / "asr"                       1 teste
       ☠️  cli: add_parser transcribe-live renomeado            1 teste
       ☠️  api: "ok" → "up"                                     1 teste
       ☠️  api: rota /api/health → /health                      1 teste
       ☠️  OpenSans-Bold.ttf apagada (test_captions.py)         1 teste
       🚨  rsync com PACKAGE_DIR + "/"   SOBREVIVEU — fora da barra;
           Path() apaga a barra final, o teste não distingue copiar
           o diretório de copiar o conteúdo dele para <home>/src/

01:21  ⚠️ NOTA    fonte apagada: só test_default_font_ships_with_the_package
       cai; os 9 restantes passam porque o host tem
       /usr/share/fonts/truetype/open-sans/OpenSans-Bold.ttf e o Pillow
       busca por basename. Fato 1 do implementador confirmado; a barra
       pede test_captions.py vermelho e ele fica vermelho

01:21  ⚠️ NOTA    .pyc velho: fato 3 confirmado como risco; as mutações
       desta rodada rodaram com PYTHONPYCACHEPREFIX novo por execução

01:22  🧬 MUTAÇÕES · web  ·  3 de 4 mortas
       ☠️  App mostra "API: ok" fixo                            1 teste
       ☠️  URL /api/health → /api/healthz                       1 teste
       ☠️  URL absoluta http://127.0.0.1:8781/api/health        1 teste
       🚨  setStatus("ok") ignorando o corpo  SOBREVIVEU — fora da
           barra; o dublê responde "ok", igual ao valor fixo

01:23  🔎 QA     passo 1/6 — Workspace e core  ·  ✅ PASS
       R100 nos módulos, 17 testes por rename; raiz virtual; um uv.lock;
       uv lock --check; core sem wordcut_cli/api; mutação da fonte morta

01:23  🔎 QA     passo 2/6 — CLI  ·  ✅ PASS
       R100 de cli.py; --help, 7 subcomandos e overview (3 formas)
       idênticos à worktree do baseline sobre transcrição sintética

01:23  🔎 QA     passo 3/6 — API  ·  ✅ PASS
       status e corpo na mesma asserção; uvicorn --factory local ok

01:23  🔎 QA     passo 4/6 — Web  ·  ✅ PASS
       as duas mutações da barra morrem; achado acima fica de nota

01:24  🔎 QA     passo 5/6 — Docker  ·  ✅ PASS
       config, build, up --build, curls 8780 (/, SPA, /api/health) e
       8781, ss só 127.0.0.1, run cli --help, uid 1000, fonte no wheel,
       sem whisperx; down; compose ls e docker ps idênticos

01:24  ⚠️ LACUNA  find '*cookies*' vazio: a linha da matriz não julga
       acha http/cookies.py e pip/_vendor/requests/cookies.py, os mesmos
       na imagem python:3.12-slim-bookworm pura; nenhum vem do contexto

01:24  🔎 QA     passo 6/6 — Documentação  ·  ✅ PASS
       README, CONTRIBUTING §3.2 (comandos rodados verdes), docs §4,
       CHANGELOG; grep sem caminhos antigos
