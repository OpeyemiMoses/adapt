import pytest
import tempfile
import shutil
from pathlib import Path

from adapt.storage.sqlite import SQLiteStorage


@pytest.fixture
def storage():
    """In-memory SQLite storage backend for fast isolated testing."""
    s = SQLiteStorage(db_path=":memory:")
    s.initialize()
    yield s
    s.close()


@pytest.fixture
def file_storage(tmp_path):
    """File-backed SQLite storage in a temporary directory."""
    db_file = tmp_path / "test_adapt.db"
    s = SQLiteStorage(db_path=str(db_file))
    s.initialize()
    yield s
    s.close()

