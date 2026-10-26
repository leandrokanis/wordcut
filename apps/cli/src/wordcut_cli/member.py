"""``wordcut member <action>``: the team, e-mails allowed in and their roles (docs/cli.md §12)."""

from __future__ import annotations

import argparse
from contextlib import closing
from typing import TYPE_CHECKING, Any

from wordcut.db import connect
from wordcut.home import Home
from wordcut.service.members import ROLES, add_member, list_members, remove_member, set_role
from wordcut_cli.contract import Context, add_command, add_group

if TYPE_CHECKING:
    from wordcut_cli.contract import Commands

# Readable output is in Portuguese (docs/cli.md §4.2); JSON keeps the English values.
ROLE_NAMES = {"assistant": "assistente", "admin": "administrador"}


def register(commands: Commands) -> None:
    actions = add_group(
        commands,
        "member",
        help="equipe e papéis — administrador",
        example="wordcut member add assistente@exemplo.org --role assistant",
    )
    add_command(
        actions,
        "list",
        help="lista os e-mails liberados, com o papel e a data de inclusão — administrador",
        run=_list,
        render=_render_list,
        example="wordcut member list --json",
    )
    add = add_command(
        actions,
        "add",
        help="libera um e-mail com um papel — administrador",
        run=_add,
        render=_render_member,
        example="wordcut member add assistente@exemplo.org --role assistant",
    )
    add.add_argument("email", help="e-mail da pessoa")
    add.add_argument("--role", required=True, choices=ROLES, help="papel: assistant ou admin")
    change = add_command(
        actions,
        "set-role",
        help="troca o papel de um membro; o último administrador não pode ser rebaixado"
        " — administrador",
        run=_set_role,
        render=_render_member,
        example="wordcut member set-role assistente@exemplo.org admin",
    )
    change.add_argument("email", help="e-mail do membro")
    change.add_argument("role", choices=ROLES, help="papel novo: assistant ou admin")
    remove = add_command(
        actions,
        "remove",
        help="tira um e-mail da equipe; o último administrador não pode ser removido"
        " — administrador",
        run=_remove,
        render=_render_removed,
        example="wordcut member remove editor2@exemplo.org",
    )
    remove.add_argument("email", help="e-mail do membro")


def _list(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(connect(Home.from_environment())) as connection:
        return {"items": list_members(connection)}


def _add(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(connect(Home.from_environment())) as connection:
        return add_member(connection, args.email, args.role)


def _set_role(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(connect(Home.from_environment())) as connection:
        return set_role(connection, args.email, args.role)


def _remove(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(connect(Home.from_environment())) as connection:
        return remove_member(connection, args.email)


def _render_removed(result: dict[str, Any]) -> str:
    return f"{result['email']} removido da equipe."


def _render_list(result: dict[str, Any]) -> str:
    if not result["items"]:
        return "Nenhum e-mail liberado na equipe."
    return "\n".join(
        f"{item['email']}  {ROLE_NAMES[item['role']]}  (incluído em {item['created_at'][:10]})"
        for item in result["items"]
    )


def _render_member(member: dict[str, Any]) -> str:
    return f"{member['email']}: {ROLE_NAMES[member['role']]}"
