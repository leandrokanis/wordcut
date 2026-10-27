"""The ``suggest`` task: a new suggestion of cuts for a processed sermon (docs/cli.md §7.6).

Parameters: ``preset_id``, the preset the launch resolved (the default one when none was
given). The task does not take the processing lock: it only calls the LLM. A success replaces
the sermon's unedited ``suggested`` cuts with the new ones (2.1.b.2) and removes the export
files of the cuts it replaced (1.2.b.1).
"""

from __future__ import annotations

from contextlib import closing

from wordcut import suggestion
from wordcut.db import connect, cuts
from wordcut.service.media_files import exports_by_cut, remove_exports_of_gone_cuts
from wordcut.service.presets import show_preset
from wordcut.service.sermons import shown_cut
from wordcut.tasks import Result, TaskContext, TaskKind, register

# The only stage: the LLM call; the same name as the process task's last stage.
SUGGESTING = (0.0, "sugerindo")


def _run(ctx: TaskContext) -> Result:
    sermon_id = ctx.resource.id
    ctx.progress(*SUGGESTING)
    with closing(connect(ctx.home)) as connection:
        preset = show_preset(connection, ctx.params["preset_id"])
        exports = exports_by_cut(ctx.home, connection, sermon_id)
        made = suggestion.suggest(connection, sermon_id, preset, replace_suggested=True)
        remove_exports_of_gone_cuts(ctx.home, connection, sermon_id, exports)
        saved = set(made.cut_ids)
        suggested = [cut for cut in cuts.of_sermon(connection, sermon_id) if cut.id in saved]
    return {
        "sermon_id": sermon_id,
        "preset_id": preset["id"],
        "suggested_cuts": [shown_cut(cut) for cut in suggested],
        "suggestion_warnings": list(made.warnings),
    }


SUGGEST = register(TaskKind(name="suggest", run=_run, needs_lock=False))
