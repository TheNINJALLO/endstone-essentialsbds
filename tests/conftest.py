from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types


ROOT = Path(__file__).parents[1]
SRC_PACKAGE = ROOT / "src" / "endstone_primebds"


def load_source(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


# The production package entry point eagerly discovers every command. Tests of the
# pure hotspot helpers use a namespace package so importing one helper does not boot
# the plugin or require a running Bedrock server.
package = sys.modules.setdefault("endstone_primebds", types.ModuleType("endstone_primebds"))
package.__path__ = [str(SRC_PACKAGE)]
utils = sys.modules.setdefault(
    "endstone_primebds.utils", types.ModuleType("endstone_primebds.utils")
)
utils.__path__ = [str(SRC_PACKAGE / "utils")]

if "endstone_primebds.utils.entity_hotspots" not in sys.modules:
    load_source(
        "endstone_primebds.utils.entity_hotspots",
        SRC_PACKAGE / "utils" / "entity_hotspots.py",
    )

