# Requisitos — Temas, Épicos, Features e Histórias de Usuário

Fonte canônica de requisitos funcionais do Wordcut, gerada pela inception
([inception.md](inception.md)) e mantida por /dev-idea.

Formato: **BDD in Action** (Smart, 2014); Temas de Investimento conforme
**SAFe** (Leffingwell, 2011). Os cenários Dado/Quando/Então ficam nas specs (/dev-specify).

**MVP**: ondas 1–5.

**Protótipo navegável**: [docs/prototype/wordcut.html](../prototype/wordcut.html), com dados
fictícios; abrir no navegador.

**CLI**: [docs/cli.md](../cli.md), a especificação dos comandos `wordcut`.

## Requisitos gerais de interface

Valem para todas as features.

- Formulários salvam automaticamente, sem botão de salvar ou aplicar. Campos de texto
  salvam ao digitar, ou ao teclar Enter e sair do campo quando a mudança precisa de
  validação (chave da API, correção de palavra, e-mail da equipe). Valor inválido não é
  salvo e mostra o motivo junto ao campo.
- A tela confirma cada salvamento de forma discreta ("Salvo").
- Navegação em três níveis, percorrida pelo caminho no topo: **Pregações** (lista, sem prévia nem
  timeline) → **Pregação** (prévia 16:9, timeline e painel de cortes) → **Corte** (prévia 9:16,
  timeline do corte e painéis Texto e Legenda). Cada nível mostra só as opções que valem nele;
  "Nova pregação" existe só no primeiro.
- No corte, o painel abre na aba Texto. Clicar na camada de legenda da timeline abre a aba
  Legenda; fechá-la, ou clicar em outra área (vídeo, áudio, prévia), volta para Texto.
- Vocabulário: **corte** é a unidade editável (sugerido, escolhido ou descartado);
  **exportação** é o vídeo renderizado de um corte e fica registrada nele.
- Configurações ocupam a tela inteira, com navegação própria; o estado da máquina fica numa
  barra de status no rodapé, sempre visível.

---

## Índice

**[Tema 1 — Autonomia da equipe](#tema-1--autonomia-da-equipe)**

- [Épico 1.1 — Produzir a pregação e os cortes](#épico-11--produzir-a-pregação-e-os-cortes)
  - [Feature 1.1.a — Criar pregação pelo link](features/1.1.a-create-sermon-from-link.md) · onda 1 (MVP)
  - [Feature 1.1.b — Delimitar a pregação](features/1.1.b-mark-sermon-range.md) · onda 2 (MVP)
  - [Feature 1.1.c — Processar a pregação](features/1.1.c-process-sermon.md) · onda 2 (MVP)
  - [Feature 1.1.d — Baixar a pregação](features/1.1.d-download-sermon.md) · onda 3 (MVP)
  - [Feature 1.1.e — Escolher cortes sugeridos](features/1.1.e-choose-suggested-scripts.md) · onda 4 (MVP)
  - [Feature 1.1.f — Ajustar a forma](features/1.1.f-adjust-form.md) · onda 5 (MVP)
  - [Feature 1.1.g — Prévia sem renderizar](features/1.1.g-preview-without-render.md) · onda 4 (MVP)
  - [Feature 1.1.h — Exportar o corte 9:16](features/1.1.h-render-vertical-cut.md) · onda 4 (MVP)
  - [Feature 1.1.i — Baixar as exportações](features/1.1.i-download-cuts.md) · onda 5 (MVP)
- [Épico 1.2 — Administrar a equipe e a máquina](#épico-12--administrar-a-equipe-e-a-máquina)
  - [Feature 1.2.a — Equipe e papéis](features/1.2.a-team-and-roles.md) · onda 5 (MVP)
  - [Feature 1.2.b — Apagar pregações e cortes](features/1.2.b-delete-sermons-and-cuts.md) · onda 6

**[Tema 2 — Curadoria confiável](#tema-2--curadoria-confiável)**

- [Épico 2.1 — Curar o conteúdo](#épico-21--curar-o-conteúdo)
  - [Feature 2.1.a — Configurações](features/2.1.a-settings.md) · onda 1 (MVP)
  - [Feature 2.1.b — Sugestão de cortes pelo LLM](features/2.1.b-llm-script-suggestion.md) · onda 3 (MVP)
  - [Feature 2.1.c — Editar o conteúdo](features/2.1.c-edit-content.md) · onda 6 (2.1.c.1 antecipada)

**[Tema 3 — Rapidez e custo previsível](#tema-3--rapidez-e-custo-previsível)**

- [Épico 3.1 — Operar pela CLI](#épico-31--operar-pela-cli)
  - [Feature 3.1.a — Trava e status](features/3.1.a-processing-lock-and-status.md) · onda 1 (MVP)

---

# Tema 1 — Autonomia da equipe

Investir em autonomia da equipe para que os assistentes produzam cortes sem depender do admin.

## Épico 1.1 — Produzir a pregação e os cortes

A fim de entregar a pregação e os cortes para a revisão do supervisor, o assistente de edição precisa ser capaz de ir do link da live aos vídeos baixados sem decidir conteúdo.

**Features**

- [Feature 1.1.a — Criar pregação pelo link](features/1.1.a-create-sermon-from-link.md)
- [Feature 1.1.b — Delimitar a pregação](features/1.1.b-mark-sermon-range.md)
- [Feature 1.1.c — Processar a pregação](features/1.1.c-process-sermon.md)
- [Feature 1.1.d — Baixar a pregação](features/1.1.d-download-sermon.md)
- [Feature 1.1.e — Escolher cortes sugeridos](features/1.1.e-choose-suggested-scripts.md)
- [Feature 1.1.f — Ajustar a forma](features/1.1.f-adjust-form.md)
- [Feature 1.1.g — Prévia sem renderizar](features/1.1.g-preview-without-render.md)
- [Feature 1.1.h — Exportar o corte 9:16](features/1.1.h-render-vertical-cut.md)
- [Feature 1.1.i — Baixar as exportações](features/1.1.i-download-cuts.md)

---

## Épico 1.2 — Administrar a equipe e a máquina

A fim de que a equipe acesse com segurança e a máquina não lote, o administrador precisa ser capaz de gerenciar acessos e apagar o que não serve mais.

**Features**

- [Feature 1.2.a — Equipe e papéis](features/1.2.a-team-and-roles.md)
- [Feature 1.2.b — Apagar pregações e cortes](features/1.2.b-delete-sermons-and-cuts.md)

---

# Tema 2 — Curadoria confiável

Investir em curadoria teológica automática para que nenhum trecho chegue à edição sem passar pelos critérios do projeto, na rigidez escolhida pelo administrador.

## Épico 2.1 — Curar o conteúdo

A fim de que as sugestões sigam o critério teológico, o administrador precisa ser capaz de configurar o modelo e os critérios e de editar o conteúdo dos cortes.

**Features**

- [Feature 2.1.a — Configurações](features/2.1.a-settings.md)
- [Feature 2.1.b — Sugestão de cortes pelo LLM](features/2.1.b-llm-script-suggestion.md)
- [Feature 2.1.c — Editar o conteúdo](features/2.1.c-edit-content.md)

---

# Tema 3 — Rapidez e custo previsível

Investir em desempenho e economia para que um corte fique pronto em minutos, com uma chamada de LLM por pregação.

## Épico 3.1 — Operar pela CLI

A fim de gerar a pregação e os cortes sem intervenção na tela, o agente operador precisa ser capaz de executar o fluxo inteiro pela CLI, com um contrato previsível.

**Features**

- [Feature 3.1.a — Trava e status](features/3.1.a-processing-lock-and-status.md)
