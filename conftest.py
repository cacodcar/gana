"""Enable automatic function profiles for all repository pytest commands."""

import sys
from pathlib import Path

# The existing quality tools use flat imports from this directory. Loading the
# plugin by name keeps pytest and mypy consistent without an installed package.
_TOOLS = str(Path(__file__).resolve().parent / "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)
pytest_plugins = ["pytest_profile"]
