# Registros de decisão de arquitetura (ADRs)

Uma decisão por arquivo, no formato de Michael Nygard ([ADR-0001](0001-registrar-decisoes-em-adr.md)).

| ADR | Título | Status |
|---|---|---|
| [ADR-0001](0001-registrar-decisoes-em-adr.md) | Registrar decisões de arquitetura em ADRs | Aceita |
| [ADR-0002](0002-monorepo.md) | Monorepo com um projeto por aplicação | Aceita |
| [ADR-0003](0003-docker-compose.md) | Orquestração por Docker Compose | Aceita |
| [ADR-0004](0004-camada-de-servico-no-core.md) | Camada de serviço única no core | Aceita |
| [ADR-0005](0005-sqlite-com-migracoes.md) | SQLite com migrações por `user_version` | Aceita |
| [ADR-0006](0006-trava-global-flock.md) | Trava global com `flock` | Aceita |
| [ADR-0007](0007-tarefas-em-processo-destacado.md) | Tarefas em processo destacado | Aceita |
| [ADR-0008](0008-api-fastapi-e-web-separada.md) | API FastAPI e web em contêiner próprio | Aceita |
| [ADR-0009](0009-identidade-pelo-cloudflare-access.md) | Identidade pelo Cloudflare Access | Aceita |
| [ADR-0010](0010-llm-pelo-openrouter.md) | LLM pelo OpenRouter com critérios no código | Aceita |
| [ADR-0011](0011-transcricao-whisperx-local.md) | Transcrição com WhisperX na GPU local | Aceita |
| [ADR-0012](0012-contrato-da-cli.md) | Contrato de saída e erros da CLI | Aceita |
| [ADR-0013](0013-trava-herdada-pelo-processo-da-tarefa.md) | Trava herdada pelo processo da tarefa (complementa a ADR-0007) | Aceita |
| [ADR-0014](0014-processamento-por-portas-e-estado-na-leitura.md) | Processamento da pregação por portas, com o estado conferido na leitura | Aceita |
| [ADR-0015](0015-erro-de-uso-nao-repete-valor-digitado.md) | Erro de uso não repete valor digitado (complementa a ADR-0012) | Aceita |
| [ADR-0016](0016-sugestao-por-porta-com-falha-na-pregacao.md) | Sugestão de cortes por porta, com a falha gravada na pregação (complementa a ADR-0010 e a ADR-0014) | Aceita |
