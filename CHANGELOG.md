# Changelog

Formato de [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/); versões em
[SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Adicionado

- Especificação da CLI `wordcut` (`docs/cli.md`).
- ADRs (`docs/adr/`), documentos de arquitetura (`docs/architecture/`), `CONTRIBUTING.md`.
- Esqueleto da API (`apps/api`, FastAPI) com `GET /api/health`.
- Esqueleto da web (`apps/web`, React + Vite + TypeScript) que mostra o estado da API.
- `compose.yaml` com os serviços `api`, `web` e `cli`, portas só em `127.0.0.1`, dados em
  `WORDCUT_HOME` e segredos montados só para leitura.
- Base da CLI nova: contrato de saída e erros (`--json`, `--quiet`, códigos de saída;
  ADR-0012), banco SQLite com migrações em `WORDCUT_HOME`, trava global de processamento e
  `wordcut status`.
- `wordcut sermon create <link>`, `sermon list [--status]` e `sermon show <id>`: a pregação
  passa a existir no banco (tabela `sermons`, migração 0002) a partir do link da live, com o
  mesmo vídeo devolvendo a pregação existente e aviso no stderr para live ainda no ar.
- `wordcut sermon trim <id> --start T --end T` e `--start/--end` no `sermon create`: grava as
  bordas da pregação em tempo da live (mínimo de 1 minuto, dentro da live), leva a pregação a
  `delimitada` e, numa pregação já processada, mantém o estado e avisa que reprocessar exige
  `sermon process --force`. `sermon list` e `sermon show` passam a trazer a duração da
  pregação.

### Alterado

- Tempos (`T`) aceitam só dígitos: minutos e segundos depois do primeiro componente ficam
  abaixo de 60, e valores como `inf`, `nan`, `1e3` ou negativos são recusados.
- O projeto passa a se chamar Wordcut; executável `wordcut`, pacote `wordcut`.
- Organização em monorepo orquestrado por Docker Compose (ADR-0002, ADR-0003): domínio em
  `packages/core`, CLI em `apps/cli`, workspace `uv` com lock único na raiz.
- Os cookies do YouTube vêm da pasta de segredos (`WORDCUT_CONFIG`, ou `~/.config/wordcut`),
  resolvida a cada uso; falhas do YouTube (inclusive cookies ausentes) viram `youtube_error`
  (saída 6), com mensagem sem o comando do `yt-dlp` nem o caminho dos cookies.
