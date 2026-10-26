# Inception — Wordcut

**Iniciada**: 2026-10-25 · **Concluída**: 2026-10-25

## Estado

- [x] 1. Visão
- [x] 2. É / Não é / Faz / Não faz
- [x] 3. Objetivos
- [x] 4. Personas
- [x] 5. Jornadas
- [x] 6. Funcionalidades
- [x] 7. Revisão
- [x] 8. Sequenciador
- [x] 9. Canvas do MVP
- [x] Histórias
- [x] Documento de requisitos

## 1. Visão

```
Para a equipe de mídia da igreja,
cujos cortes da pregação exigem edição demorada e julgamento teológico,
o Wordcut é uma aplicação web com CLI
que transforma o link da live em cortes verticais prontos.
Diferentemente de ferramentas automáticas de cortes,
ele escolhe os trechos por critérios teológicos do projeto, na rigidez do administrador.
```

Nome: "Wordcut" — a Palavra e a edição palavra a palavra.

## 2. É / Não é / Faz / Não faz

| É | Não é |
|---|---|
| Aplicação web com CLI, na máquina do admin | Editor de vídeo genérico |
| Ferramenta de equipe, com admin e assistente | Serviço na nuvem para outras igrejas |
| Editor de cortes de fala, guiado pelo texto | Plataforma de publicação |
| Curadoria teológica configurável | Quem aprova o que vai ao ar |

| Faz | Não faz |
|---|---|
| Recorta a pregação a partir do link da live | Publicar nas redes |
| Sugere cortes com critérios teológicos | Assistente decidir conteúdo |
| Edita a forma e, para o admin, o conteúdo | Fila: um processamento por vez |
| Prévia no navegador e render 9:16 | Música, efeitos e trilha sonora |
| Fluxo inteiro pela CLI, operável por agentes | Login próprio fora do Cloudflare Access |

## 3. Objetivos

1. **Autonomia da equipe** — investir em autonomia da equipe para que os assistentes produzam
   cortes sem depender do admin.
2. **Curadoria confiável** — investir em curadoria teológica automática para que nenhum trecho
   chegue à edição sem passar pelos critérios do projeto, na rigidez escolhida pelo
   administrador.
3. **Rapidez e custo previsível** — investir em desempenho e economia para que um corte fique
   pronto em minutos, com uma chamada de LLM por pregação.

## 4. Personas

1. **Administrador** — responde pela mídia e pela doutrina dos cortes, técnico; precisa controlar
   os critérios e operar tudo sem depender da tela; configura, edita o conteúdo e revisa antes
   de publicar.
2. **Assistente de edição** — sabe editar vídeo, sem papel teológico; precisa produzir cortes
   rápido sem decidir conteúdo; usa o navegador de vez em quando, inclusive pelo celular.
3. **Agente operador** — agente de IA que controla a CLI; precisa de um contrato previsível
   (`--json`, códigos de saída, `--wait`); executa o fluxo inteiro sem interação.

## 5. Jornadas

**J1. Produzir a pregação e os cortes** · Assistente de edição · Tema 1
cola o link da live → delimita a pregação na timeline → processa → baixa a pregação recortada
(16:9) → recebe e escolhe os cortes sugeridos → ajusta a forma, com prévia → exporta →
baixa os cortes (9:16)
*Resultado: a pregação e os cortes prontos para a revisão do supervisor.*

**J2. Curar o conteúdo** · Administrador · Tema 2
configura o modelo e a chave → ajusta os critérios → lê as sugestões de uma pregação → edita
o conteúdo de um corte ou cria um do zero → pede novas sugestões, se precisar
*Resultado: sugestões cada vez mais alinhadas ao critério.*

**J3. Operar pela CLI** · Agente operador · Tema 3
cria a pregação pelo link → marca a faixa → processa com `--wait` → lê as sugestões em JSON →
renderiza → devolve os caminhos da pregação e dos cortes
*Resultado: a pregação e os cortes gerados sem intervenção na tela.*

**J4. Administrar a equipe e a máquina** · Administrador · Tema 1
libera um e-mail e define o papel → acompanha o processamento em andamento → apaga pregações e
cortes antigos
*Resultado: a equipe acessa com segurança e a máquina não lota.*

## 6. Funcionalidades

Toda funcionalidade tem o comando de CLI correspondente (constituição §II). "Motor já existe" =
lógica pronta no pacote atual, falta o produto em volta.

| # | Funcionalidade | Atende | Estado |
|---|---|---|---|
| F1 | Criar a pregação a partir do link | J1.1, J3.1 | parcial (`info`) |
| F2 | Delimitar a pregação pelas bordas do vídeo na timeline | J1.2, J3.2 | nova |
| F3 | Processar: baixar a faixa, transcrever, cortar em 16:9 | J1.3, J3.3 | motor já existe (`transcribe-live`, `cut`) |
| F4 | Trava de um processamento por vez, com status | J1.3, J4.2 | nova |
| F5 | Baixar a pregação recortada (16:9) | J1.4, J3.6 | nova |
| F6 | Sugestão automática de cortes pelo LLM; nova sugestão só pelo admin | J1.5, J2.3, J2.5, J3.4 | nova |
| F7 | Escolher ou descartar cortes sugeridos | J1.5 | nova |
| F8 | Editar a forma: grafia (com trava) e estilo da legenda | J1.6 | parcial (`corrections`) |
| F9 | Prévia no navegador, sem renderizar | J1.6 | nova |
| F10 | Exportar o corte em 9:16 | J1.7, J3.5 | motor já existe (`short`) |
| F11 | Baixar as exportações (9:16) | J1.8, J3.6 | nova |
| F12 | Editar o conteúdo pelo texto e pela trilha (admin) | J2.4 | nova |
| F13 | Configurações: modelo e chave do OpenRouter, critérios em campos, organizados em presets | J2.1, J2.2 | nova |
| F14 | Equipe e papéis por e-mail (Cloudflare Access) | J4.1 | nova |
| F15 | Apagar pregações e cortes | J4.3 | nova |

Infraestrutura (systemd, Cloudflare Tunnel) não é funcionalidade: entra como restrição não
funcional nas features que dependem dela.

## 7. Revisão

🟢 sabemos fazer · 🟡 dúvida pontual · 🔴 incerteza alta. Esforço e valor relativos.

| # | Funcionalidade | Conf. | Esf. | Valor | Observação |
|---|---|:-:|:-:|:-:|---|
| F1 | Criar pregação pelo link | 🟢 | E | $$ | |
| F2 | Delimitar a pregação | 🟢 | EE | $$ | |
| F3 | Processar (baixar, transcrever, cortar) | 🟢 | EE | $$$ | motor existe; migrar para SQLite |
| F4 | Trava de um por vez + status | 🟢 | E | $$ | |
| F5 | Baixar a pregação 16:9 | 🟢 | E | $$ | |
| F6 | Sugestão pelo LLM | 🟡 | EE | $$$ | qualidade e JSON variam com o modelo do OpenRouter |
| F7 | Escolher ou descartar cortes | 🟢 | E | $$ | |
| F8 | Forma: grafia e estilo da legenda | 🟡 | EE | $ | trava da grafia |
| F9 | Prévia sem renderizar | 🔴 | EE | $$ | saltos precisos no `<video>` e legenda sincronizada |
| F10 | Renderizar 9:16 | 🟢 | E | $$$ | motor existe |
| F11 | Baixar as exportações | 🟢 | E | $$ | |
| F12 | Editar o conteúdo pelo texto e pela trilha | 🔴 | EEE | $$ | a interface mais complexa |
| F13 | Configurações | 🟢 | EE | $$ | |
| F14 | Equipe e papéis (Access) | 🟡 | EE | $$ | token do Access; domínio pendente |
| F15 | Apagar pregações e cortes | 🟢 | E | $ | |

## 8. Sequenciador

Regras por onda: ≤ 3 itens · ≤ 1 🔴 · ≥ 1 🟢 · esforço ≤ 5 E · valor ≥ 4 $ · dependência em
onda anterior.

Dependências: F2, F3 → F1 · F5, F12, F15 → F3 · F6 → F3, F13 · F7, F8, F9, F10 → F6 ·
F11 → F10. F2 não bloqueia F3 (a faixa também é marcada pela CLI).

| Onda | Funcionalidades | Conta |
|---|---|---|
| 1 | F1 criar pregação · F4 trava · F13 configurações | 3 · 0 🔴 · 3 🟢 · 4 E · 6 $ |
| 2 | F2 delimitar pregação · F3 processar | 2 · 0 🔴 · 2 🟢 · 4 E · 5 $ |
| 3 | F5 baixar a pregação · F6 sugestão LLM | 2 · 0 🔴 · 1 🟢 · 3 E · 5 $ |
| 4 | F7 escolher cortes · F9 prévia · F10 exportar | 3 · 1 🔴 · 2 🟢 · 4 E · 7 $ |
| 5 | F8 forma · F11 baixar cortes · F14 equipe | 3 · 0 🔴 · 1 🟢 · 5 E · 5 $ |
| 6 | F12 editar conteúdo · F15 apagar | 2 · 1 🔴 · 1 🟢 · 4 E · 3 $ ⚠ |

**MVP = ondas 1–5** (13 funcionalidades): fecha J1 (assistente, do link aos cortes baixados) e
J3 (agente pela CLI).

### Quebras de regra

- **Onda 6 — regra 5 (valor 3 $ < 4 $).** F12 (🔴, EEE) é a última peça, pesada e de valor
  médio; as verdes que poderiam acompanhá-la são necessárias antes para fechar a J1. Até lá, o
  admin só muda o conteúdo pedindo nova sugestão (F6).

## 9. Canvas do MVP

| Bloco | Conteúdo |
|---|---|
| **Proposta** | O assistente leva o link da live à pregação 16:9 e aos cortes 9:16, sem decidir o conteúdo |
| **Personas segmentadas** | Assistente de edição (principal), administrador, agente operador |
| **Jornadas** | J1 e J3 completas; J2 e J4 parciais (sem edição de conteúdo e sem apagar) |
| **Funcionalidades** | F1–F11, F13, F14 (ondas 1–5) |
| **Resultado esperado** | A equipe entrega os cortes da pregação da semana sem o administrador operar a máquina |
| **Métricas** | tempo do link aos cortes baixados · fração dos cortes sugeridos escolhidos pelos assistentes · fração dos cortes aprovados na revisão do supervisor (contada à mão; revisão fora da aplicação) · custo de LLM por pregação. Metas: a definir |
| **Custo e cronograma** | a definir. O LLM faz uma chamada por pregação; o custo depende do modelo escolhido |

## Estacionamento

*(vazio)*
