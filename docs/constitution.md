<!--
Sync Impact Report
- Versão: 2.0.1 → 2.0.2 — PATCH (2026-10-26): o projeto passa a se chamar Wordcut (título).
  Aprovada pelo administrador do projeto em 2026-10-26.
- Versão: 2.0.0 → 2.0.1 — PATCH (2026-10-25): "roteiros sugeridos" passa a "cortes sugeridos" no
  princípio I, acompanhando o vocabulário dos requisitos.
- Versão: 1.3.0 → 2.0.0 — emenda (2026-10-25): a constituição passa a tratar só de princípios e
  arquitetura. Os detalhes de funcionalidade saem daqui e ficam nos requisitos
  (docs/requirements/), que prevalecem em questões de funcionalidade.
  MAJOR: redefine o escopo do documento e a Governança.
- Princípios redefinidos: I (sem a trava de grafia por distância de edição e sem a regra de
  "uma sugestão por pregação", que já estão nas features 1.1.f e 2.1.b); III (sem o formato
  de frases numeradas, já na 2.1.b); IV (sem o status no SQLite e a prévia, já nas 1.1.c,
  1.1.g e 3.1.a); VI (sem os "últimos 4 caracteres", já na 2.1.a).
- Seções removidas: "Papéis e permissões" (a tabela foi para a feature 1.2.a); em Restrições
  técnicas, "Marcar a pregação", "Editar um corte", "Critérios" e "Presets" (foram para as
  features 1.1.b, 2.1.c e 2.1.a).
- Pendência movida: TODO(AJUSTE_BORDAS) agora é questão aberta da feature 1.1.b.
- Emendas anteriores (2026-10-25): 1.1.0 retirou os exemplos de calibração; 1.2.0 trocou as
  versões dos critérios por presets; 1.3.0 fixou os critérios no código.
- Revisão das emendas 1.1.0 a 2.0.1: aprovadas pelo administrador do projeto em 2026-10-25.
- Pendências:
  - TODO(DOMINIO): confirmar o domínio na Cloudflare para o Tunnel + Access.
  - TODO(TRAVAS): reavaliar uma trava só versus GPU/CPU separadas depois do uso real.
-->

# Wordcut Constitution

Aplicação web, na máquina com GPU do administrador, que transforma a live de um culto no
YouTube na pregação recortada e em cortes verticais editados palavra a palavra. É usada por
uma equipe de assistentes que edita vídeo, mas não decide teologia.

Este documento guarda os princípios e a arquitetura. O que a aplicação faz, e como, está nos
requisitos em `docs/requirements/`.

## Core Principles

### I. Teologia fora das mãos do assistente (NÃO NEGOCIÁVEL)

- O conteúdo de um corte (quais trechos, em que ordem, com que limites) é decidido pelo LLM, a
  partir dos critérios teológicos do projeto, ou pelo administrador.
- O assistente MUST NOT alterar o conteúdo. Ele escolhe entre os cortes sugeridos e mexe só
  na forma.
- Os critérios teológicos fazem parte do código e só mudam por commit revisado. A
  configuração ajusta como eles se aplicam, mas não os reescreve.
- A aplicação MUST NOT apresentar um corte como "aprovado para publicar". A revisão final é do
  supervisor, fora da aplicação.

Razão: os assistentes não têm papel teológico e publicam em nome da igreja. A
responsabilidade doutrinária fica com os critérios do projeto, com o administrador e com a
revisão do supervisor.

### II. CLI completa e operável por agentes (NÃO NEGOCIÁVEL)

- Todo o fluxo MUST ser executável pela CLI, de ponta a ponta.
- A web e a CLI MUST usar a mesma camada de serviço. Nenhuma regra de negócio vive só na API
  HTTP ou só na interface. A CLI chama essa camada direto, sem depender do servidor no ar.
- Todo comando MUST ser não interativo quando chamado com argumentos e oferecer `--json`.
  Também MUST ter códigos de saída consistentes, IDs estáveis e uma forma de esperar o fim de
  uma tarefa (`--wait`), com o progresso no stderr.
- A CLI na máquina do servidor age como administrador.

Razão: o administrador quer operar pelo terminal e delegar a agentes. Um contrato único
evita que a web e a CLI divirjam.

### III. Economia de tokens

- O LLM MUST ser usado só para sugerir os cortes de uma pregação: uma chamada por pregação,
  mais as que o administrador pedir.
- Editar, validar edições e renderizar MUST NOT usar o LLM.
- Só a pregação vai ao LLM, nunca a live inteira, e no formato mais enxuto que permita
  responder.
- A resposta MUST seguir um esquema e ser validada. Sem "conserto" heurístico: uma nova
  tentativa e, depois, o erro para o usuário.

Razão: o custo fica previsível e não cresce com a edição.

### IV. Desempenho com um processamento por vez

- Só um processamento pesado roda por vez na máquina inteira. A web e a CLI compartilham a
  mesma trava do sistema operacional, que se libera sozinha quando o processo morre.
- Um segundo pedido MUST ser recusado como "ocupado", sem fila.
- Edição, prévia e navegação nunca são bloqueadas pela trava.
- Trabalho pesado só roda quando pedido: enquanto a pessoa edita, ela vê o resultado sem
  renderizar.
- Otimizações de desempenho MUST ser medidas antes de adotadas.

Razão: uma GPU, uma máquina pessoal, e resposta imediata onde a pessoa está esperando.

### V. Simplicidade

- Sem infraestrutura além do que a máquina já roda: nada de Redis, broker de filas ou banco
  servidor enquanto o uso real não exigir. Se surgir a necessidade, ela é registrada como
  emenda.
- Um único processo servidor serve a API e a interface compilada.
- O projeto não tem compromisso de retrocompatibilidade com o formato antigo (pastas, `.json`
  e skills do Claude Code).

Razão: poucas pregações por semana e uma equipe pequena não justificam operar
infraestrutura.

### VI. Segurança e privacidade

- O acesso externo MUST passar só pelo Cloudflare Tunnel com o Cloudflare Access. Nenhuma porta
  aberta e nenhuma autenticação própria. O papel de cada pessoa vem do e-mail verificado.
- Segredos (chave do LLM, cookies do YouTube) MUST NOT ser lidos de volta pela interface nem
  aparecer em resposta da API, em log ou em mensagem de erro. Ficam com permissão restrita ou
  cifrados.
- LGPD: dos assistentes se guarda só o e-mail. Textos livres da configuração e relatórios MUST
  NOT conter nomes de pessoas.

## Restrições técnicas

- **Servidor:** Python ≥ 3.10 com FastAPI, reaproveitando os módulos de domínio existentes
  (limpeza, câmera, legenda, renderização).
- **Interface:** React com TypeScript, compilada com Vite e servida como arquivos estáticos
  pelo FastAPI. O progresso das tarefas chega por SSE.
- **Dados:** SQLite para tudo o que não é mídia, inclusive as palavras transcritas. As mídias
  ficam no disco.
- **Tarefas:** em segundo plano no próprio processo que as dispara (servidor ou CLI), sob a
  trava global do princípio IV.
- **Transcrição:** WhisperX na GPU local.
- **LLM:** pelo OpenRouter, com modelo e chave configuráveis.

## Fluxo de desenvolvimento

- Testes de comportamento pela interface pública da camada de serviço. Toda funcionalidade
  nova chega com o comando de CLI e o teste correspondente.
- Quality gates antes de integrar: `uv run pytest`, `uv run ruff check .`,
  `uv run ruff format --check .` e `uv run mypy src` (strict), todos limpos. A interface tem o
  equivalente em TypeScript (typecheck e lint).
- Mensagens de commit em inglês, no imperativo. Texto voltado ao usuário em português.

## Governance

- Esta constituição prevalece em princípios e arquitetura. Em funcionalidade, prevalecem os
  requisitos (`docs/requirements/`). Specs, planos e revisões MUST verificar a conformidade com
  os dois, e um desvio de princípio MUST ser justificado no plano ou virar emenda.
- Emendas são feitas editando este arquivo, com o número de versão incrementado:
  - MAJOR: remoção ou redefinição de um princípio;
  - MINOR: princípio ou seção nova, ou orientação ampliada;
  - PATCH: redação e esclarecimentos.
- Uma emenda MUST ser revisada por uma pessoa diferente de quem a redigiu antes de valer.

**Version**: 2.0.2 | **Ratified**: 2026-10-24 | **Last Amended**: 2026-10-26
