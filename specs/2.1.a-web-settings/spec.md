# Spec: Configurações e equipe na web

**Issue**: 2.1.a (web; item 26) · **Requisito**: features 2.1.a, 1.2.a.1 (web); protótipo (configurações em rolagem contínua)
**Branch**: `mvp` · **Status**: Draft · **Criado**: 2026-10-26

## Descrição
O administrador ajusta, numa tela inteira com rolagem contínua e menu que pula para cada
seção: o modelo e a chave do LLM, o modelo do WhisperX, os cookies do YouTube, os presets
(níveis de rigidez de cada filtro e valor, formato, edição, instruções adicionais, padrão) e a
equipe (e-mails e papéis). Tudo salva sozinho; segredos nunca aparecem de volta.

## Cenários de aceite
- **Modelos e segredos**: mudar o modelo salva sozinho; colar a chave e confirmar mostra só
  `••••` + 4 últimos; cookies mostram "presentes".
- **Presets**: escolher preset, mudar níveis (brando/moderado/rigoroso) por critério, formato,
  reordenar, palavras protegidas e instruções adicionais, tudo com autosave; criar, renomear,
  apagar (menos o padrão) e definir padrão.
- **Equipe**: liberar e-mail com papel, mudar papel, remover; último administrador protegido.
- **Navegação**: rolagem contínua; o menu pula para a seção e acompanha a rolagem. Seções do
  protótipo: Modelo, Presets, Filtros, Valor, Formato, Pessoas.
- **Autorrebaixamento**: o administrador que muda o próprio papel para Assistente (não sendo o
  último) perde a tela e vê a recusa.

## Casos de borda
- Assistente não acessa a tela.
- Valor inválido não é salvo e mostra o motivo junto ao campo.
- O texto dos critérios nunca aparece.
- Segredo recusado com 409 `config_not_writable` (pasta só para leitura no Compose): a
  mensagem da API e a orientação de gravar pela CLI no host; nada é exibido de volta.
- Duplicar cria `Cópia de <nome>`; nome repetido mostra o motivo.

## Fora deste item
- "Processamentos" no menu (não está no spec; fica para item próprio).
- Campos do protótipo sem rota na API: gancho, autônomo, fechamento, limpo, ideias por
  pregação, descrição por critério e a busca do menu.

## Requisitos funcionais
- **FR-001**: Seções sobre as rotas de admin do item 20b.
- **FR-002**: Autosave com indicador "Salvo"; segredos só por envio, nunca exibidos.
- **FR-003**: Texto validado (modelos, nome do preset) grava ao Enter ou ao sair do campo; os
  demais campos livres gravam 400 ms depois da última mudança, e a gravação pendente vai para
  o preset em que foi feita antes de trocar de preset.
- **FR-004**: Cookies do YouTube enviados por arquivo; o conteúdo nunca é exibido.

## Escopo
- `apps/web/src/features/settings/`.
