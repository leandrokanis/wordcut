<!--
Sync Impact Report
- Versão: 1.2.0 → 1.3.0 — emenda (2026-10-25): os critérios teológicos passam a ser do projeto.
  A tradição, o prompt base e um trecho de prompt por filtro e por valor, em três níveis de
  rigidez, ficam fixos no código. O preset guarda só os níveis, o formato, a colagem e as
  instruções adicionais do administrador.
  MINOR: orientação ampliada no princípio I; mudam o princípio VI (LGPD) e Restrições técnicas
  ("Critérios"). Documentos: docs/requirements/inception.md (visão, objetivo 2),
  docs/requirements/features.md (Tema 2), features/2.1.a-settings.md e
  2.1.b-llm-script-suggestion.md.
- Versão: 1.1.0 → 1.2.0 — emenda (2026-10-25): os critérios passam a ser organizados em presets
  com nome, editáveis no lugar; sai o versionamento dos critérios e o registro da versão em cada
  sugestão. A sugestão automática usa o preset padrão.
  MINOR: nenhum princípio removido ou redefinido; muda só a seção Restrições técnicas
  ("Critérios"). Documentos: docs/requirements/inception.md (F13),
  docs/requirements/features/2.1.a-settings.md e 2.1.b-llm-script-suggestion.md (2.1.b.3).
- Versão: 1.0.0 → 1.1.0 — emenda (2026-10-25): retirados os exemplos de calibração. A sugestão
  passa a depender só dos critérios, que ficam estruturados em campos.
  MINOR: nenhum princípio removido ou redefinido; a orientação muda dentro dos princípios I, III,
  VI e das Restrições técnicas.
- Princípios modificados: I (conteúdo decidido a partir dos critérios); III (sai o limite de
  exemplos no prompt); VI (LGPD vale para critérios e relatórios).
- Seções modificadas: Restrições técnicas ("Critérios"); Papéis e permissões (Configurações).
- Documentos atualizados: docs/requirements/inception.md (J2, F13),
  docs/requirements/features/2.1.a-settings.md e 2.1.b-llm-script-suggestion.md.
- Revisão das emendas 1.1.0, 1.2.0 e 1.3.0: pendente. Uma emenda MUST ser revisada por outra pessoa antes de valer (Governance).
- Pendências:
  - TODO(DOMINIO): confirmar o domínio na Cloudflare para o Tunnel + Access.
  - TODO(AJUSTE_BORDAS): decidir se a entrada/saída da pregação encosta na palavra depois da
    transcrição.
  - TODO(TRAVAS): reavaliar uma trava só versus GPU/CPU separadas depois do uso real.
-->

# cortes-pregacao Constitution

Aplicação web, na máquina com GPU do administrador, que transforma a live de um culto no
YouTube na pregação recortada e em cortes verticais editados palavra a palavra. É usada por
uma equipe de assistentes que edita vídeo, mas não decide teologia.

## Core Principles

### I. Teologia fora das mãos do editor (NÃO NEGOCIÁVEL)

- O conteúdo de um corte (quais trechos, em que ordem, com que limites) é decidido pelo LLM, a
  partir dos critérios teológicos do projeto, na rigidez escolhida no preset. Ou pelo
  administrador.
- Os critérios teológicos são parte do código: a tradição, o prompt base e o texto de cada
  filtro e de cada valor, em três níveis de rigidez. Mudá-los MUST passar por commit e revisão,
  como qualquer código. Pela configuração, o administrador escolhe só os níveis e escreve
  instruções adicionais.
- O editor MUST NOT alterar o conteúdo: não inclui, não remove, não reordena trechos, não muda
  limites e não cria roteiro do zero. Ele escolhe entre os roteiros sugeridos e mexe só na
  forma: enquadramento e grafia da legenda.
- A correção de grafia do editor MUST ficar restrita a palavras parecidas com a original
  (distância de edição pequena). Trocar uma palavra inteira ("não" → "sim") é bloqueado.
- A sugestão do LLM roda automaticamente uma única vez por pregação. Só o administrador pode
  pedir outra.
- A revisão final por um adulto acontece fora da aplicação. A aplicação MUST NOT apresentar um
  corte como "aprovado para publicar".

Razão: os editores são menores de idade e publicam em nome da igreja. A responsabilidade
doutrinária fica com o sistema configurado por um adulto e com a revisão humana final.

### II. CLI completa e operável por agentes (NÃO NEGOCIÁVEL)

- Todo o fluxo MUST ser executável pela CLI, de ponta a ponta: criar a pregação, marcar a
  faixa, processar, sugerir, editar, renderizar, baixar, configurar.
- A CLI chama a camada de serviço direto, sem depender do servidor web estar no ar.
- A web e a CLI MUST usar a mesma camada de serviço. Nenhuma regra de negócio vive só na API
  HTTP ou só na interface.
- Todo comando MUST ser não interativo quando chamado com argumentos e oferecer `--json`.
  Também MUST ter códigos de saída consistentes, IDs estáveis e uma forma de esperar o fim de
  uma tarefa (`--wait`), com o progresso no stderr.
- A CLI na máquina do servidor age como administrador.

Razão: o administrador quer operar pelo terminal e delegar a agentes. Um contrato único
evita que a web e a CLI divirjam.

### III. Economia de tokens

- O LLM MUST ser chamado só para sugerir os cortes de uma pregação: uma chamada por
  pregação, mais as regenerações pedidas pelo administrador.
- Localizar a pregação, editar, validar edições e renderizar MUST NOT usar o LLM.
- A transcrição vai ao LLM como frases numeradas, sem tempo. O LLM responde com intervalos de
  frases, e o servidor converte para os tempos das palavras.
- A resposta MUST seguir um esquema JSON e ser validada. Em caso de falha: uma nova tentativa,
  depois o erro aparece para o usuário. Não há "conserto" heurístico.
- Só a faixa da pregação vai ao LLM, nunca a live inteira.

Razão: o custo fica previsível (uma chamada por pregação) e não cresce com a edição.

### IV. Desempenho com um processamento por vez

- Só um processamento pesado roda por vez na máquina inteira: download, transcrição, corte ou
  renderização. A web e a CLI compartilham a mesma trava de sistema operacional (`flock`), que
  se libera sozinha quando o processo morre.
- Um segundo pedido MUST ser recusado com "ocupado", informando o que está rodando, quem
  iniciou e há quanto tempo. Ele não entra em fila.
- O estado dos processamentos fica no SQLite e aparece na tela e no `cortes status`. Tarefa
  interrompida por reinício MUST aparecer como falha, com a opção de refazer.
- Edição, prévia e navegação nunca são bloqueadas pela trava.
- A prévia de um corte MUST tocar no navegador a partir do vídeo horizontal, pulando de trecho
  em trecho com a legenda por cima, sem renderizar. A renderização 9:16 só roda ao pedir para
  gerar.
- Otimizações de desempenho MUST ser medidas antes de adotadas. Exemplo: o reenquadramento e a
  legenda no ffmpeg, com NVENC.

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

- O acesso externo MUST passar só pelo Cloudflare Tunnel com o Cloudflare Access (código por
  e-mail, lista de e-mails liberados). Nenhuma porta aberta e nenhuma autenticação própria.
- O papel de cada pessoa vem do e-mail verificado pelo Access, conforme a lista da
  configuração.
- A chave da API do LLM só pode ser gravada pela interface e pela CLI, nunca lida de volta:
  aparecem só os últimos 4 caracteres. Ela MUST NOT aparecer em resposta da API, em log ou em
  mensagem de erro. Fica num arquivo com permissão `600` ou no banco, cifrada.
- Os cookies do YouTube seguem a mesma regra.
- LGPD: dos editores se guarda só o e-mail. As instruções adicionais dos presets e os
  relatórios MUST NOT conter nomes de pessoas.

## Restrições técnicas

- **Servidor:** Python ≥ 3.10 com FastAPI, reaproveitando os módulos de domínio existentes
  (limpeza, câmera, legenda, renderização).
- **Interface:** React com TypeScript, compilada com Vite e servida como arquivos estáticos
  pelo FastAPI. O progresso das tarefas chega por SSE.
- **Dados:** SQLite para tudo o que não é mídia, inclusive as palavras transcritas (uma linha
  por palavra). As mídias ficam no disco.
- **Tarefas:** em segundo plano no próprio processo que as dispara (servidor ou CLI), sob a
  trava global do princípio IV.
- **Transcrição:** WhisperX na GPU local, só na faixa marcada da pregação.
- **Marcar a pregação:** pelo player do YouTube embutido, com botões de entrada e saída. Sem
  forma de onda e sem baixar nada antes de marcar.
- **Editar um corte:** pelo texto (selecionar, reordenar, ajustar na palavra), com uma trilha
  sincronizada que mostra os trechos e a duração (meta de 40 a 75 s). A borda arrastada na
  trilha encosta na palavra.
- **LLM:** pelo OpenRouter. O modelo e a chave se escolhem na página de configurações.
- **Critérios (fixos no código):** o prompt base, com a tradição teológica, e um trecho de
  prompt para cada filtro e cada valor, nos níveis brando, moderado e rigoroso. Ficam em
  arquivos no pacote, um por critério, validados ao carregar: todo critério MUST ter os três
  níveis. O conteúdo inicial vem de `skills/video-corte-vertical/sugerir-cortes.md`. Não há
  exemplos de calibração no prompt.
- **Presets (no banco):** têm nome e guardam só o nível de cada critério, pelo ID do critério,
  os números do formato, as opções de colagem e as instruções adicionais (texto livre do
  administrador, acrescentado ao prompt). São editáveis na configuração e pela CLI. A sugestão
  automática usa o preset padrão. Critério novo no código entra nos presets com o nível padrão
  dele; critério removido do código é ignorado.

## Papéis e permissões

| Ação | Editor | Admin |
|---|:-:|:-:|
| Criar pregação a partir do link | ✅ | ✅ |
| Marcar início e fim no player | ✅ | ✅ |
| Processar (baixar, transcrever, cortar) | ✅ | ✅ |
| Sugestão do LLM: automática, uma vez por pregação | — | — |
| Pedir novas sugestões | ❌ | ✅ |
| Escolher ou descartar roteiros sugeridos | ✅ | ✅ |
| Forma: enquadramento e grafia com trava | ✅ | ✅ |
| Conteúdo: trechos, limites, ordem, texto livre | ❌ | ✅ |
| Criar roteiro do zero | ❌ | ✅ |
| Renderizar e baixar | ✅ | ✅ |
| Apagar pregação ou corte | ❌ | ✅ |
| Configurações (modelo, chave, critérios, equipe) | ❌ | ✅ |

## Fluxo de desenvolvimento

- Testes de comportamento pela interface pública da camada de serviço. Toda funcionalidade
  nova chega com o comando de CLI e o teste correspondente.
- Quality gates antes de integrar: `uv run pytest`, `uv run ruff check .`,
  `uv run ruff format --check .` e `uv run mypy src` (strict), todos limpos. A interface tem o
  equivalente em TypeScript (typecheck e lint).
- Mensagens de commit em inglês, no imperativo. Texto voltado ao usuário em português.

## Governance

- Esta constituição prevalece sobre outras práticas do projeto. Specs, planos e revisões MUST
  verificar a conformidade com ela, e um desvio MUST ser justificado no plano ou virar emenda.
- Emendas são feitas editando este arquivo, com o número de versão incrementado:
  - MAJOR: remoção ou redefinição de um princípio;
  - MINOR: princípio ou seção nova, ou orientação ampliada;
  - PATCH: redação e esclarecimentos.
- Uma emenda MUST ser revisada por uma pessoa diferente de quem a redigiu antes de valer.

**Version**: 1.3.0 | **Ratified**: 2026-10-24 | **Last Amended**: 2026-10-25
