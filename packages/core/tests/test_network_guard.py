import json
import subprocess
import sys

import pytest

# Runs in a new interpreter, as a detached task does: it inherits the suite's environment but
# none of the doubles that replace the factories in the pytest process.
BUILD = """
import json, sys
from wordcut import processing, suggestion, timeline_media
from wordcut.errors import WordcutError
build = {
    "processing": lambda: processing.default_gateways("large-v3"),
    "suggestion": lambda: suggestion.default_model("provedor/modelo-de-teste", "chave-ficticia"),
    "timeline": timeline_media.default_gateways,
}[sys.argv[1]]
try:
    build()
except WordcutError as error:
    print(json.dumps([error.code, error.details]))
"""


@pytest.mark.parametrize("real_world", ["processing", "suggestion", "timeline"])
def test_the_real_outside_world_refuses_to_be_built_while_the_suite_forbids_the_network(
    real_world: str,
) -> None:
    built = subprocess.run(
        [sys.executable, "-c", BUILD, real_world], capture_output=True, text=True, check=True
    )

    assert json.loads(built.stdout or "null") == [
        "network_error",
        {"forbidden_by": "WORDCUT_FORBID_NETWORK"},
    ]
