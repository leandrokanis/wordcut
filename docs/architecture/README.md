# Arquitetura do Wordcut

Modelo C4 e fluxos principais. As decisões que levam a esta forma estão nas
[ADRs](../adr/README.md). Este documento descreve a arquitetura **alvo do MVP**; a coluna
"Estado" da seção 4 diz o que já existe.

## 1. Contexto (C4 nível 1)

```mermaid
C4Context
  title Contexto do Wordcut
  Person(assistant, "Assistente de edição", "Escolhe cortes sugeridos e ajusta a forma")
  Person(admin, "Administrador", "Configura critérios, edita conteúdo, opera pela CLI")
  System_Ext(agent, "Agente operador", "Executa o fluxo pela CLI")
  System(wordcut, "Wordcut", "Da live do culto à pregação recortada e aos cortes 9:16")
  System_Ext(youtube, "YouTube", "Live do culto")
  System_Ext(openrouter, "OpenRouter", "LLM que sugere os cortes")
  System_Ext(cloudflare, "Cloudflare Tunnel + Access", "Acesso externo e identidade por e-mail")

  Rel(assistant, cloudflare, "Usa no navegador", "HTTPS")
  Rel(admin, cloudflare, "Usa no navegador", "HTTPS")
  Rel(cloudflare, wordcut, "Repassa com o e-mail verificado")
  Rel(admin, wordcut, "Opera pela CLI na máquina")
  Rel(agent, wordcut, "Opera pela CLI", "--json")
  Rel(wordcut, youtube, "Lê dados e baixa a faixa")
  Rel(wordcut, openrouter, "Uma chamada por pregação", "HTTPS")
```

## 2. Contêineres (C4 nível 2)

```mermaid
C4Container
  title Contêineres do Wordcut (Docker Compose)
  Person(user, "Equipe", "Assistentes e administrador")
  System_Ext(cloudflare, "Cloudflare Tunnel + Access")
  System_Ext(youtube, "YouTube")
  System_Ext(openrouter, "OpenRouter")

  System_Boundary(machine, "Máquina com GPU") {
    Container(web, "web", "React + Vite, servidor estático", "Interface; repassa /api para a api")
    Container(api, "api", "Python, FastAPI", "HTTP + SSE sobre a camada de serviço")
    Container(cli, "cli", "Python", "Executável wordcut; chama a camada de serviço direto")
    ContainerDb(data, "WORDCUT_HOME", "Volume: SQLite, mídias, processing.lock", "Estado compartilhado")
  }

  Rel(user, cloudflare, "HTTPS")
  Rel(cloudflare, web, "HTTP local")
  Rel(web, api, "/api", "HTTP, SSE")
  Rel(api, data, "Lê e grava; trava flock")
  Rel(cli, data, "Lê e grava; trava flock")
  Rel(api, youtube, "yt-dlp")
  Rel(cli, youtube, "yt-dlp")
  Rel(api, openrouter, "HTTPS")
  Rel(cli, openrouter, "HTTPS")
```

`api` e `cli` usam o mesmo pacote `core` (camada de serviço e domínio), em processos
separados. O que os coordena é o volume de dados: o banco SQLite e a trava `flock`.

## 3. Componentes do core (C4 nível 3)

```mermaid
flowchart LR
  subgraph apps
    CLI["apps/cli<br/>wordcut_cli"]
    API["apps/api<br/>wordcut_api"]
  end
  subgraph core["packages/core — pacote wordcut"]
    SVC["service<br/>operações do sistema"]
    ERR["errors<br/>WordcutError + códigos"]
    DB["db<br/>SQLite + migrações"]
    LOCK["lock<br/>trava global"]
    TASK["tasks<br/>processo destacado"]
    DOM["domínio<br/>youtube, asr, edit, vertical"]
  end
  CLI --> SVC
  API --> SVC
  SVC --> DB
  SVC --> LOCK
  SVC --> TASK
  SVC --> DOM
  SVC --> ERR
```

## 4. Estado da implementação

| Peça | Estado |
|---|---|
| Monorepo (workspace `uv` com lock único; `apps/web` com npm) | existe |
| Docker Compose (`api`, `web`, `cli` no perfil `tools`; portas só em `127.0.0.1`) | existe; sem GPU e sem WhisperX na imagem (roadmap, item 5) |
| Domínio (`youtube`, `asr`, `edit`, `vertical`) | existe em `packages/core`, herdado da CLI anterior |
| Camada de serviço, banco, trava, tarefas | em construção (roadmap, fase 1) |
| CLI | a anterior, movida para `apps/cli`; a nova (`docs/cli.md`) em construção (roadmap, fase 1) |
| API | esqueleto em `apps/api` com `GET /api/health`; rotas planejadas (roadmap, fase 2) |
| Web | esqueleto em `apps/web` que mostra o estado da API; protótipo em `docs/prototype/wordcut.html`; interface planejada (roadmap, fase 3) |

## 5. Fluxos

### 5.1. Criar e processar uma pregação pela CLI

```mermaid
sequenceDiagram
  autonumber
  actor Op as Operador
  participant CLI as wordcut (cli)
  participant SVC as core.service
  participant DB as SQLite
  participant Child as processo destacado
  participant Lock as processing.lock
  participant YT as YouTube

  Op->>CLI: sermon create <link> --start T --end T
  CLI->>SVC: create_sermon(link, start, end)
  SVC->>YT: dados da live
  SVC->>DB: grava a pregação
  SVC-->>CLI: pregação (id, título, duração)
  Op->>CLI: sermon process <id>
  CLI->>SVC: start_process(id)
  SVC->>Lock: flock exclusivo (não bloqueante)
  alt trava ocupada
    SVC-->>CLI: WordcutError busy
    CLI-->>Op: saída 4
  else livre
    SVC->>DB: tarefa running
    SVC->>Child: lança em sessão própria (herda a trava)
    SVC-->>CLI: task_id
    CLI-->>Op: {"task_id": …}
    Child->>YT: baixa só a faixa
    Child->>Child: transcreve, corta 16:9, pede sugestões
    Child->>DB: palavras, cortes, tarefa succeeded
    Child->>Lock: libera ao terminar
  end
```

### 5.2. Exportar um corte pela web

```mermaid
sequenceDiagram
  autonumber
  actor A as Assistente
  participant Web as web
  participant API as api
  participant SVC as core.service
  participant Lock as processing.lock
  participant DB as SQLite

  A->>Web: Exportar (opções)
  Web->>API: POST /api/cuts/{id}/renders
  API->>SVC: start_render(cut_id, options)
  SVC->>Lock: flock exclusivo
  alt ocupada
    API-->>Web: 409 {"error": {"code": "busy"}}
  else livre
    SVC->>DB: opções salvas no corte; tarefa running
    API-->>Web: 202 {"task_id": …}
    Web->>API: GET /api/tasks/{id}/events (SSE)
    loop progresso
      API-->>Web: event: progress
    end
    SVC->>DB: exportação registrada; tarefa succeeded
    API-->>Web: event: done (render_id)
  end
```
