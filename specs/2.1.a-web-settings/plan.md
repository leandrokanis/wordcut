# Plan: Configurações e equipe na web

**Issue**: 2.1.a (web) · **Feature**: specs/2.1.a-web-settings · **Data**: 2026-10-26

## Resumo
Página de configurações com as seções do protótipo (Modelo, Presets, Filtros, Valor, Formato,
Pessoas) em rolagem contínua, menu com scroll-spy, formulários em linhas (rótulo à esquerda,
controle à direita) com autosave, e controles de rigidez em três níveis.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

## Contexto de código
| Situação | Path |
|---|---|
| Alterar | `apps/web/src/features/settings/SettingsPage.tsx` (e o teste do item 21, L1) |
| Alterar | `apps/web/src/api/client.ts`, `apps/web/src/api/types.ts` (rotas de admin, L2) |
| Alterar | `apps/web/src/app/Identity.tsx` (recarregar `/api/me`, L9); `features/cut/ExportDialog.tsx` (usa `FormRow`, L2) |
| Criar | `features/settings/`: `ModelSection.tsx`, `PresetSections.tsx`, `LevelControl.tsx`, `TeamSection.tsx`, `useScrollSpy.ts`, `usePresetDrafts.ts`, `CommitInput.tsx`, `Section.tsx`; `ui/FormRow.tsx` (extraído do `SettingRow`) |
| Criar | `src/test/fakeIntersectionObserver.ts`, fixtures de settings/presets/critérios/membros; testes Vitest |
| Alterar | `CHANGELOG.md`, `docs/architecture/README.md`, `specs/roadmap.md` (Registro) |

## Comandos de verificação
| Componente | Um arquivo | Suíte | Estática |
|---|---|---|---|
| `apps/web` | `npm --prefix apps/web test -- <arquivo>` | `npm --prefix apps/web test` | `npm --prefix apps/web run typecheck && npm --prefix apps/web run lint && npm --prefix apps/web run build` |

## Decisões técnicas
| Decisão | Escolha | Justificativa |
|---|---|---|
| Segredos | campo de senha; envio ao Enter/blur; limpa o campo depois; mostra só a máscara | §VI |
| Níveis | controle segmentado de 3 opções por critério, nomes do catálogo | Protótipo |
| Autosave | debounce por campo; Enter/blur nos campos validados (chave, e-mail) | Requisito geral |
| Scroll-spy | `IntersectionObserver` com dublê nos testes | Padrão |
| L1 — Seções | as do protótipo: Modelo, Presets, Filtros, Valor, Formato, Pessoas; chave, WhisperX e cookies em Modelo; seletor de preset no topo do grupo Presets–Formato. "Processamentos" sai do menu (teste do item 21 ajustado) e vai ao Registro; "Em construção" sai | QA L1; protótipo `SPAGES` |
| L2 — Contexto | `SettingRow` do `ExportDialog` extraído para `ui/FormRow.tsx` e usado nas duas telas; rotas de admin em `client.ts`/`types.ts` | QA L2 |
| L3 — Campos | só campos com rota na API (`settings`, segredos, preset: `name`, `levels`, durações, `reorder`, `protected_words`, `instructions`; membros). Fora: gancho, autônomo, fechamento, limpo, ideias por pregação, descrição por critério, busca do menu (Registro) | QA L3 |
| L4 — Níveis | Brando/Moderado/Rigoroso ↔ `lenient`/`moderate`/`strict`, agrupados por `type` (`filter` → Filtros, `value` → Valor), `Choice` dentro de `LevelControl`; dicas `LEVELS_F`/`LEVELS_V` no `title` dos botões | QA L4 |
| L5 — Cookies e 409 | cookies por `<input type="file">` lido no cliente e enviado em `{"value"}`, conteúdo nunca renderizado; 409 `config_not_writable` → mensagem da API + orientação da CLI no host (`wordcut settings set-key < chave.txt` / `set-cookies < cookies.txt`), campo limpo, máscara/presença inalterada | QA L5; docs/api.md §2 |
| L6 — Texto validado | modelo do LLM, modelo do WhisperX e nome do preset são texto salvo ao Enter ou ao sair do campo (sem debounce), só quando mudou | QA L6 |
| L7 — Debounce | 400 ms (como `useCaptionStyle`) para instruções, durações e palavras protegidas; a gravação pendente é concluída (flush) no preset em que foi digitada antes de trocar de preset ou sair da tela; `PATCH` só com o campo mudado | QA L7 |
| L8 — Criar | "Duplicar" → `POST /api/presets {"name": "Cópia de <nome>", "from_id"}`; o novo fica selecionado; 400 mostra o motivo | QA L8; protótipo `pdup` |
| L9 — Último admin | nada escondido por e-mail; 409 `last_admin` mostra a mensagem e reverte o papel/mantém a linha. Quem rebaixa a si mesmo recarrega `GET /api/me` e cai na tela de recusa | QA L9 |
| L10 — Dublê | `src/test/fakeIntersectionObserver.ts` reutilizável (`observe`, `disconnect`, `trigger`); no fim da rolagem, a última seção | QA L10 |
| L11 — "Salvo" | um `Saved` único no topo da página, disparado por toda gravação bem-sucedida, nunca depois de erro | QA L11; protótipo `.s-saved` |
| L12 — Docs | `CHANGELOG.md`, linha da web em `docs/architecture/README.md` e Registro do roadmap (L1, L3, L9) | QA L12 |

## Ordem de implementação
- [x] **Passo 1 — Estrutura** — página contínua, menu (L1), scroll-spy (L10), `FormRow` (L2), "Salvo" único (L11).
- [x] **Passo 2 — Modelo e segredos** — modelos por Enter/blur (L6), chave, cookies por arquivo e 409 (L5).
- [x] **Passo 3 — Presets** — seletor, níveis (L4), formato, edição, instruções com debounce e flush (L7), duplicar (L8), apagar e padrão.
- [x] **Passo 4 — Equipe** — liberar, mudar papel, remover, último admin e autorrebaixamento (L9).
- [x] **Passo 5 — Documentação** — CHANGELOG, arquitetura e Registro do roadmap (L12).

## Verificação
- [x] Modelos salvam sozinhos; segredos mostram só máscara/presença.
- [x] Presets editáveis com autosave; padrão protegido.
- [x] Equipe com último admin protegido; e-mail inválido com motivo.
- [x] Assistente sem acesso; typecheck, lint, testes, build limpos.
