from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest


@pytest.fixture
def tmp_path() -> Path:
    # The desktop sandbox may not allow pytest's default user-temp directory.
    # Keep test databases in an ignored workspace-local folder instead.
    path = Path.cwd() / ".test_tmp" / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path
