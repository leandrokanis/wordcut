"""Command-line interface: ``wordcut [opções globais] <comando>`` (docs/cli.md)."""

from __future__ import annotations

import argparse
import sys

from wordcut_cli import criteria, legacy, preset, sermon, settings, status, task
from wordcut_cli.contract import create_parser, execute


def build_parser() -> argparse.ArgumentParser:
    parser, commands = create_parser()
    legacy.register(commands)
    criteria.register(commands)
    preset.register(commands)
    sermon.register(commands)
    settings.register(commands)
    status.register(commands)
    task.register(commands)
    return parser


def main(argv: list[str] | None = None) -> int:
    return execute(build_parser(), sys.argv[1:] if argv is None else argv)
