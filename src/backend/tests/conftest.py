import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture(autouse=True)
def reset_fastapi_dependency_overrides():
    from backend import main

    main.app.dependency_overrides.clear()
    yield
    main.app.dependency_overrides.clear()
