"""Shared pytest fixtures."""
import shutil
import pytest
from pathlib import Path

from src.database import init_db
from src.tools.registry import create_default_registry


@pytest.fixture
def temp_env(tmp_path: Path):
    """Provide isolated paths for database and invoices."""
    db_file = tmp_path / "test_company.db"
    invoices_dir = tmp_path / "invoices"
    invoices_dir.mkdir(parents=True, exist_ok=True)

    # Copy real sample invoices from project data directory if present
    project_invoices = Path(__file__).resolve().parent.parent / "data" / "invoices"
    if project_invoices.exists():
        for f in project_invoices.glob("*"):
            if f.is_file():
                shutil.copy(f, invoices_dir / f.name)

    init_db(db_file)

    return {
        "db_path": db_file,
        "invoices_dir": invoices_dir
    }


@pytest.fixture
def clean_registry():
    """Provide a fresh default tool registry."""
    return create_default_registry()


@pytest.fixture(autouse=True)
def ensure_deterministic_tests(monkeypatch):
    """Ensure automated tests run against deterministic engine for speed, reproducibility, and offline safety."""
    from src.llm_client import LLMClient
    monkeypatch.setattr(LLMClient, "is_available", lambda self: False)
