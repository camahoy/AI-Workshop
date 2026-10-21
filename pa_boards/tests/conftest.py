import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def store(tmp_path, monkeypatch):
    """A fresh store pointed at a temp data dir for every test."""
    monkeypatch.setenv("PA_BOARDS_DATA_DIR", str(tmp_path))
    from palib import store as store_mod
    importlib.reload(store_mod)
    for name in ("summary", "export", "ai_summary"):
        mod = sys.modules.get(f"palib.{name}")
        if mod:
            importlib.reload(mod)
    return store_mod
