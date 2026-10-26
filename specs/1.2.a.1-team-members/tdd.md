## Plano de QA

baseline_commit: 18acfe5dcdf7d9d8ac1b268743abf1fdbcb1e6d2

12:25  ⚠️ LACUNA  plan.md: migração <próximo>_members.sql
       a última é 0009_renders.sql (item 15); criar 0010_members.sql,
       sem BEGIN/COMMIT; test_db.py lê a última e precisa seguir verde

12:25  ⚠️ LACUNA  last_admin já existe em errors.py (saída 5) e cli.md §5.3
       o plano não diz; acrescentar ou mudar código em errors.py é
       divergência. Só usar o que existe

12:25  📐 BARRA   members guarda só email, role, created_at, updated_at
       PRAGMA table_info(members) num teste; é a prova da LGPD (FR-002)
       no lugar onde o dado mora

12:25  🧬 EXIGE   coluna extra na migração (ex.: name)  ·  vermelha
       prova que a tabela não ganha dado pessoal sem ninguém ver

12:25  📐 BARRA   e-mail normalizado: strip + minúsculas, em todas as entradas
       teste de serviço e de CLI com e-mail em caixa mista no add, no
       set-role, no remove e no role_of

12:25  🧬 EXIGE   tirar .lower() do add  ·  vermelha
       prova a normalização do cenário "liberar e listar"

12:25  🧬 EXIGE   tirar a normalização da busca (set-role/remove/role_of)  ·  vermelha
       o Access pode mandar o e-mail em outra caixa; sobreviver = papel
       não encontrado na API

12:25  📐 BARRA   último admin: remover e rebaixar → last_admin, saída 5
       testes com 1 admin + 1 assistente, 1 admin sozinho e 2 admins;
       banco inalterado depois do erro

12:25  🧬 EXIGE   remover a checagem no remove  ·  vermelha
12:25  🧬 EXIGE   remover a checagem no set-role  ·  vermelha
       cada operação precisa do seu próprio teste

12:25  🧬 EXIGE   contar todos os membros em vez dos admins  ·  vermelha
       com 1 admin + 1 assistente a mutação deixaria remover o admin

12:25  ⚠️ LACUNA  "regra checada numa transação" com with connection:
       o BEGIN implícito só abre no primeiro DML; a contagem lida antes
       fica fora. CLI e API no mesmo arquivo podem zerar os admins.
       Sem BEGIN IMMEDIATE ou statement único, passo 1 PARCIAL

12:25  🧬 EXIGE   tirar o BEGIN IMMEDIATE (se for o caminho)  ·  vermelha
       teste com segunda conexão que rebaixa o outro admin entre a
       leitura e a escrita; sobreviver = FR-003 só vale sem concorrência

12:25  📐 BARRA   bordas: e-mail inválido, repetido, papel inválido → 2;
       inexistente → 3; validação antes do banco
       teste de serviço e de CLI; papel inválido com details.choices

12:25  🧬 EXIGE   tirar a checagem de repetido  ·  vermelha
       a PK vira IntegrityError → internal_error, não invalid_argument

12:25  🧬 EXIGE   tirar a validação de papel do serviço  ·  vermelha
       o CHECK vira internal_error; a API chama o serviço sem argparse

12:25  🧬 EXIGE   remove de inexistente em silêncio (rowcount 0)  ·  vermelha
       prova o not_found

12:25  🧬 EXIGE   regex aceitando qualquer texto  ·  vermelha

12:25  ⚠️ LACUNA  plano não diz se o erro repete o e-mail
       ADR-0015 e cli.md §17: nenhuma mensagem nem details com o e-mail;
       com eco, passo 1 (g) e passo 2 (f) FAIL

12:25  🧬 EXIGE   e-mail na mensagem do not_found/invalid_argument  ·  vermelha

12:25  📐 BARRA   role_of: papel ou None; malformado/vazio → None
       teste de serviço; a API decide "sem acesso" com None

12:25  🧬 EXIGE   role_of com padrão "assistant" em vez de None  ·  vermelha
       sobreviver = qualquer e-mail do Access ganharia acesso

12:25  ⚠️ LACUNA  formato da saída, ordem da lista e retorno do remove
       barra: items {email, role, created_at, updated_at} por e-mail;
       add/set-role = objeto; remove = {email, removed: true}. Sem
       cli.md §12 atualizado, passos 2 e 3 PARCIAL

12:25  ⚠️ LACUNA  cli.md §17 diz "mostra só o e-mail e o papel"
       a spec mostra a data de inclusão; a spec prevalece e o §17 é
       alinhado no passo 3, senão PARCIAL

12:25  📐 BARRA   --help do grupo e das 4 ações diz "administrador"
       cli.md §3.5 (MUST); teste no molde de test_settings_command:338

12:25  🧬 EXIGE   tirar "administrador" da ajuda de uma ação  ·  vermelha

12:25  ⚠️ LACUNA  spec usa ana@exemplo.org: prenome em dado de teste
       CONTRIBUTING §6 pede dados sem nomes de pessoas; usar
       admin@, assistente@, editor2@exemplo.org

## Rodada 1 · implementador

12:29  ▶️ PASSOS  1, 2, 3 (os três - [ ] do plan.md); decisões D1–D9 e
       L1–L7 do qa.md registradas no plan.md antes do código

12:29  --- Passo 1: Banco e serviço ---

12:29  🔴 RED    test_an_added_member_is_listed_with_the_email_in_lower_case_the_role_and_the_dates
       tracer: add com e-mail em caixa mista e espaços, list traz e-mail
       normalizado, papel e datas ISO com fuso (now injetado)
       Cenário "liberar e listar"; FR-002; D6/L2
       E   ModuleNotFoundError: No module named 'wordcut.service.members'

12:30  🟢 GREEN  test_an_added_member_is_listed_with_the_email_in_lower_case_the_role_and_the_dates  ·  11 passed
       (com test_db.py: user_version 10 com a migração 0010)

12:30  🛡️ GUARDA test_the_members_table_keeps_only_the_email_the_role_and_the_dates
       PRAGMA table_info(members) = email, role, created_at, updated_at
       FR-002 (LGPD); Passo 1 (a). Passa de saída: a migração veio no tracer
       🧬 coluna name TEXT na migração  ·  vermelha (1 failed)

12:30  🛡️ GUARDA test_members_are_listed_by_email_whatever_the_order_they_were_added
       inclusão fora de ordem; a lista sai por e-mail
       D6/L2; Passo 1 (c). Passa de saída: ORDER BY veio no tracer
       🧬 tirar ORDER BY email  ·  vermelha (1 failed)

12:30  🟢 GREEN  guardas restauradas  ·  3 passed

12:30  🔴 RED    test_an_invalid_email_is_an_invalid_argument_and_nothing_is_added
       vazio, só espaços, sem @, sem local, sem domínio com ponto, espaço
       interno e dois @ → invalid_argument {argument: email}, lista vazia
       Borda "e-mail inválido"; Passo 1 (f); D9
       E       Failed: DID NOT RAISE WordcutError  (9 failed)

12:30  🟢 GREEN  test_an_invalid_email_is_an_invalid_argument_and_nothing_is_added  ·  12 passed

12:31  🔴 RED    test_an_email_already_in_the_team_in_another_case_is_an_invalid_argument_not_a_duplicate
       o mesmo e-mail em outra caixa → invalid_argument {argument: email};
       a lista segue com um membro
       Borda "e-mail já liberado"; Passo 1 (f)
       E       sqlite3.IntegrityError: UNIQUE constraint failed: members.email

12:31  🟢 GREEN  test_an_email_already_in_the_team_in_another_case_is_an_invalid_argument_not_a_duplicate  ·  13 passed

12:31  🔴 RED    test_adding_with_a_role_other_than_assistant_or_admin_is_an_invalid_argument
       owner, Admin e vazio → invalid_argument com choices, antes do banco
       Borda "papel fora de assistant|admin"; Passo 1 (f); D7
       E       sqlite3.IntegrityError: CHECK constraint failed (3 failed)

12:31  🟢 GREEN  test_adding_with_a_role_other_than_assistant_or_admin_is_an_invalid_argument  ·  16 passed

12:31  🔴 RED    test_set_role_finds_the_member_in_another_case_and_changes_the_role_and_updated_at_only
       set_role com e-mail em outra caixa muda role e updated_at, mantém
       created_at; o retorno é o membro como a lista o dá
       Cenário "mudar papel e remover"; Passo 1 (d)
       E   ImportError: cannot import name 'set_role'

12:31  🟢 GREEN  test_set_role_finds_the_member_in_another_case_and_changes_the_role_and_updated_at_only  ·  17 passed

12:31  🔴 RED    test_set_role_of_an_email_not_in_the_team_is_not_found
       set_role de e-mail fora da equipe → not_found {argument: email}
       Borda "membro inexistente"; Passo 1 (f)
       E       AssertionError  (o assert de set_role, sem not_found)

12:31  🟢 GREEN  test_set_role_of_an_email_not_in_the_team_is_not_found  ·  18 passed

12:32  🔴 RED    test_set_role_to_a_role_other_than_assistant_or_admin_is_an_invalid_argument
       set_role owner → invalid_argument com choices; o papel não muda
       Borda "papel inválido"; Passo 1 (f); D7 (a API chama o serviço direto)
       E       sqlite3.IntegrityError: CHECK constraint failed

12:32  🟢 GREEN  test_set_role_to_a_role_other_than_assistant_or_admin_is_an_invalid_argument  ·  19 passed

12:32  🔴 RED    test_removing_a_member_in_another_case_takes_it_off_the_list_even_with_no_admin
       remove_member com e-mail em outra caixa → {email, removed: true} e o
       membro some; sem admin na equipe, remover assistente funciona
       Cenário "mudar papel e remover"; Passo 1 (d, e); D6
       E   ImportError: cannot import name 'remove_member'

12:32  🟢 GREEN  test_removing_a_member_in_another_case_takes_it_off_the_list_even_with_no_admin  ·  20 passed

12:32  🛡️ GUARDA test_removing_an_email_not_in_the_team_is_not_found
       remove de e-mail fora da equipe → not_found {argument: email}
       Borda "membro inexistente"; Passo 1 (f). Passa de saída: _existing
       veio do set_role
       🧬 remove em silêncio (sem _existing, rowcount 0)  ·  vermelha (1 failed)

12:32  🔴 RED    test_removing_the_only_admin_is_last_admin_and_changes_nothing
       único admin, sozinho e com um assistente: remove → last_admin
       (saída 5) e a lista não muda
       Cenário "último administrador"; FR-003; Passo 1 (e)
       E       Failed: DID NOT RAISE WordcutError  (2 failed)

12:33  🟢 GREEN  test_removing_the_only_admin_is_last_admin_and_changes_nothing  ·  23 passed

12:33  🔴 RED    test_demoting_the_only_admin_is_last_admin_and_changes_nothing
       único admin, sozinho e com um assistente: set_role assistant →
       last_admin (saída 5) e a lista não muda
       Cenário "último administrador"; FR-003; Passo 1 (e)
       E       Failed: DID NOT RAISE WordcutError  (2 failed)

12:33  🟢 GREEN  test_demoting_the_only_admin_is_last_admin_and_changes_nothing  ·  25 passed

12:33  🛡️ GUARDA test_with_two_admins_either_one_can_be_demoted_or_removed
       dois admins: rebaixar ou remover um deles funciona; fica o outro
       FR-003 (o lado permitido); Passo 1 (e). Passa de saída
       🧬 last_admin com qualquer admin (>= 1)  ·  vermelha (2 failed)

12:33  🧬 MUTAÇÃO contar todos os membros em vez dos admins  ·  vermelha (2 failed)
       os casos with_assistant de remove e de set_role

12:33  🧬 MUTAÇÃO tirar a checagem do remove  ·  vermelha (2 failed)

12:33  🧬 MUTAÇÃO tirar a checagem do set_role  ·  vermelha (2 failed)
       restaurado  ·  27 passed

12:34  🔴 RED    test_set_role_to_the_role_the_member_has_succeeds_and_changes_nothing
       set_role para o papel que o membro já tem (inclusive o único admin
       para admin) dá certo, devolve o membro e não grava updated_at
       L7 (idempotente); Passo 1 (e)
       E       AssertionError: assert (False, [...]) == (True, [...])  (2 failed)

12:34  🟢 GREEN  test_set_role_to_the_role_the_member_has_succeeds_and_changes_nothing  ·  29 passed

12:34  🛡️ GUARDA test_no_error_repeats_the_email
       repetido, inválido, inexistente (set_role e remove) e last_admin
       (remove e set_role): nem message nem details trazem o e-mail
       D9/L6; Passo 1 (g). Passa de saída: as mensagens nasceram sem eco
       🧬 e-mail na mensagem do not_found  ·  vermelha (2 failed)
       🧬 e-mail em details do inválido  ·  vermelha (10 failed)

12:34  🔴 RED    test_role_of_gives_the_role_of_the_email_in_any_case
       role_of com e-mail em outra caixa e espaços devolve o papel
       FR-004; Passo 1 (h)
       E   ImportError: cannot import name 'role_of'

12:34  🟢 GREEN  test_role_of_gives_the_role_of_the_email_in_any_case  ·  36 passed

12:35  🔴 RED    test_role_of_an_email_not_in_the_team_or_malformed_is_none
       e-mail fora da equipe, vazio, só espaços, sem @ e com dois @ →
       None, sem exceção (a API decide "sem acesso")
       FR-004; L4; Passo 1 (h)
       E       AttributeError: 'NoneType' object has no attribute 'role'  (5 failed)

12:35  🟢 GREEN  test_role_of_an_email_not_in_the_team_or_malformed_is_none  ·  41 passed

12:35  🧬 MUTAÇÃO role_of com padrão "assistant" em vez de None  ·  vermelha (5 failed)

12:35  🧬 MUTAÇÃO role_of sem normalizar a busca  ·  vermelha (1 failed)

12:35  🧬 MUTAÇÃO tirar .lower() da normalização (add e buscas)  ·  vermelha (6 failed)

12:35  🧬 MUTAÇÃO regex de e-mail aceitando qualquer texto  ·  vermelha (10 failed)
       restaurado  ·  41 passed

12:36  🔴 RED    test_two_admins_demoted_at_the_same_time_from_two_connections_leave_one_admin
       dois admins; outra conexão (a API) segura o rebaixamento de um deles
       sem commit; a CLI rebaixa o outro numa thread; a API comita. Tem de
       dar last_admin e sobrar um admin
       FR-003; D3/L1; Passo 1 (i)
       E       AssertionError: assert ([None], []) == (['last_admin'], [...])
       (com with connection: a contagem lida antes do DML zerou os admins)

12:36  🟢 GREEN  test_two_admins_demoted_at_the_same_time_from_two_connections_leave_one_admin  ·  42 passed
       add, set_role e remove gravam sob BEGIN IMMEDIATE (_writing)

12:36  🔵 REFACTOR set_role sem o if redundante (com dois papéis, mudar o papel
       de um admin é rebaixar); comentários e docstring de role_of  ·  verde

12:37  🧬 MUTAÇÃO tirar o BEGIN IMMEDIATE de _writing  ·  vermelha (1 failed)
       o teste das duas conexões; restaurado

12:37  ✅ PASSO 1/3 — Banco e serviço  ·  +19 testes (42 casos)  ·  suíte core 844

12:37  --- Passo 2: CLI ---

12:38  🔴 RED    test_an_added_member_is_listed_with_the_email_in_lower_case_the_role_and_the_date
       tracer: member add em caixa mista --role assistant --json e member
       list --json → {items: [o membro]}, e-mail minúsculo, quatro chaves
       Cenário "liberar e listar"; FR-001; Passo 2 (a, b)
       E       AssertionError: assert (2, 2, {'error'...}) == (0, 0, {...})
       (invalid_argument: o grupo member não existe)

12:38  🟢 GREEN  test_an_added_member_is_listed_with_the_email_in_lower_case_the_role_and_the_date  ·  1 passed

12:38  🔴 RED    test_set_role_changes_the_role_and_remove_takes_the_member_off_the_list
       set-role <email em outra caixa> admin e remove → papel muda, remove
       devolve {email, removed: true} e o membro some da lista
       Cenário "mudar papel e remover"; FR-001; Passo 2 (c)
       E       KeyError: 'role'  (set-role ainda não existe: saída de erro)

12:38  🟢 GREEN  test_set_role_changes_the_role_and_remove_takes_the_member_off_the_list  ·  2 passed

12:39  🔴 RED    test_the_help_of_the_group_and_of_each_action_says_administrator_with_an_example
       --help do grupo e de list/add/set-role/remove traz "— administrador"
       e, depois de "Exemplo:", o comando pronto, com @exemplo.org
       docs/cli.md §3.5 (MUST); D5; Passo 2 (g)
       E       assert (0, True, False, False) == (0, True, True, True)  [action0]
       (add_group não tem example=: o grupo fica sem exemplo)

12:39  🟢 GREEN  test_the_help_of_the_group_and_of_each_action_says_administrator_with_an_example  ·  7 passed
       contract.add_group ganha example= opcional, como add_command

12:39  🧬 MUTAÇÃO tirar "— administrador" da ajuda do set-role  ·  vermelha (1 failed)
       o teste busca o marcador "— administrador", não a palavra solta, que
       a ajuda do set-role e do remove já traz em "último administrador"

12:39  🛡️ GUARDA test_removing_or_demoting_the_only_admin_is_last_admin_with_exit_code_5
       remove e set-role do único admin pela CLI → error.code last_admin,
       saída 5. Passa de saída: o serviço e o contrato já cuidam
       Cenário "último administrador"; Passo 2 (d)

12:40  🛡️ GUARDA test_wrong_member_arguments_are_invalid_or_not_found
       e-mail inválido e repetido, --role inválido e ausente, papel inválido
       no set-role → 2 invalid_argument (papel com choices assistant/admin);
       inexistente no set-role e no remove → 3 not_found
       Bordas; D7; Passo 2 (e). Passa de saída: serviço + argparse
       🧬 --role sem required=True  ·  vermelha (1 failed)

12:40  🛡️ GUARDA test_no_error_output_repeats_the_email_typed
       inválido, papel inválido, inexistente (set-role, remove) e last_admin,
       com e sem --json: stdout + stderr sem o e-mail digitado
       D9/L6; Passo 2 (f). 1ª versão buscava só a parte local e achou
       "admin" em "administrador" (2 failed, erro do teste): agulha = e-mail
       🧬 e-mail na mensagem do not_found  ·  vermelha (4 failed)

12:40  🔴 RED    test_an_empty_team_lists_no_items_and_says_so_in_text
       equipe vazia: --json → {items: []}; texto → uma frase no stdout, nada
       no stderr, saída 0
       Passo 2 (b)
       E       AssertionError: ... At index 3 diff: False != True  (texto vazio)

12:40  🟢 GREEN  test_an_empty_team_lists_no_items_and_says_so_in_text  ·  27 passed

12:41  🛡️ GUARDA test_json_works_before_the_group_too  ·  test_without_json_the_result_is_text_on_stdout_and_an_error_only_on_stderr
       --json antes do grupo; sem --json, resultado em texto no stdout e o
       erro só no stderr (saída 5). Passo 2 (h). Passam de saída: contrato

12:41  🎨 VISUAL  texto legível em português: papel por extenso e a data de
       inclusão na lista (§4.2; sem TDD, conferido na tela)  ·  29 passed

12:44  ⚠️ CHECKPOINT test_cli.py::test_help_lists_every_command vermelho: a lista
       fixa dos comandos do wordcut --help não tinha member. Relacionado ao
       passo (FR-001): member entra na constante  ·  suíte cli 430 passed

12:44  ✅ PASSO 2/3 — CLI  ·  +9 testes (29 casos)  ·  suíte cli 430

12:44  --- Passo 3: Documentação ---

12:45  📝 DOC    docs/cli.md §12 (identidade pelo e-mail normalizado, saída de
       list/add/set-role/remove, objeto do membro, ordem, idempotência, erros
       sem eco) e §17 (de dado pessoal, só o e-mail); CHANGELOG [Não lançado]
       / Adicionado; arquitetura §4 (linha Equipe, service.members, CLI)
       Passo 3; D4, L2, L3. Sem TDD: documentação

12:45  📝 DOC    exemplos só com @exemplo.org; a mensagem de e-mail inválido e o
       comentário da regex sem endereço-modelo; caso de dois @ do teste sem
       domínio real (L5)

12:46  ✅ PASSO 3/3 — Documentação  ·  +0 testes  ·  suíte 1275

12:46  🏁 FINAL  uv run pytest -q: 1275 passed (baseline 1204, +71 casos);
       ruff check, ruff format --check e mypy limpos; errors.py intocado;
       sem commit (override do orquestrador)

## Rodada 1 · QA

12:47  📊 SUÍTE  1275 passed  ·  0 failed
       uv run pytest -q; ruff check, ruff format --check e mypy limpos

12:48  🔎 QA     passo 1/3 — Banco e serviço  ·  ✅ PASS
       (a)–(i) da matriz com teste de comportamento; BEGIN IMMEDIATE em
       _writing, provado pelo teste das duas conexões

12:50  🧬 MUTAÇÕES · serviço, repositório e migração  ·  22 de 22 mortas
       ☠️  coluna name na migração                        1 teste
       ☠️  sem .lower() / sem strip() na normalização     4+ testes
       ☠️  busca sem normalizar (role_of, set_role, remove)  1–4 testes
       ☠️  sem checagem no remove / no set_role            4 testes cada
       ☠️  contar todos os membros em vez dos admins       4 testes
       ☠️  last_admin com >= 1                             3 testes
       ☠️  sem BEGIN IMMEDIATE (6 execuções)               1 teste, 6/6
       ☠️  sem checagem de repetido / de papel             3–4 testes
       ☠️  remove inexistente em silêncio                  4 testes
       ☠️  regex aceita tudo / sem exigir ponto            4+ testes
       ☠️  e-mail na mensagem ou em details do erro        2–4 testes
       ☠️  role_of com padrão "assistant"                  4 testes
       ☠️  set_role sem idempotência / sem updated_at      1–2 testes
       ☠️  lista sem ORDER BY / remove sem "removed"       1–3 testes

12:51  🔎 QA     passo 2/3 — CLI  ·  ✅ PASS
       (a)–(h) cobertos em test_member_command.py; smoke real com
       WORDCUT_HOME no scratchpad confere texto, JSON e saídas 0/2/5

12:52  🧬 MUTAÇÕES · CLI e contrato  ·  7 de 8 mortas
       ☠️  --role sem required                             1 teste
       ☠️  sem "— administrador" no set-role               1 teste
       ☠️  grupo sem example / add_group ignora example    1 teste
       ☠️  lista vazia sem texto                           1 teste
       ☠️  member não registrado                           4+ testes
       🚨  set-role sem choices=ROLES     SOBREVIVEU — equivalente na
           barra: o serviço revalida e dá o mesmo invalid_argument com
           details.choices; só o usage do --help muda

12:53  🔎 QA     escopo — contract.py e test_cli.py  ·  ✅ justificados
       ambos listados no plan.md (D5 e lista do --help); efeito colateral:
       formatter_class fixo em add_group tira a quebra de linha da
       descrição de todos os grupos (cut --help imprime linha de 102
       colunas em terminal de 80); nenhum teste cobre; fora da matriz

12:54  🔎 QA     passo 3/3 — Documentação  ·  ✅ PASS
       CHANGELOG, arquitetura §4 (Equipe, serviço, CLI), cli.md §12 e §17
       conferem com o que os testes provam; grep de e-mail da matriz vazio

12:55  🔎 QA     LGPD e comentários  ·  ✅
       só admin@, assistente@, editor2@exemplo.org (e variantes de caixa
       ou inválidas do mesmo domínio); nenhum prenome; comentários novos
       são intenção, referência ou formato, em inglês
