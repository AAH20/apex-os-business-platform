"""Migration utilities for APEX-OS Business Platform.

Provides helper functions for running migrations programmatically,
checking migration status, and managing the migration lifecycle.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

logger = logging.getLogger(__name__)

# Default path to alembic.ini
DEFAULT_INI_PATH = Path(__file__).resolve().parent / "alembic.ini"


def get_alembic_config(
    url: Optional[str] = None,
    ini_path: Optional[Path] = None,
) -> Config:
    """Create an Alembic Config object.

    Args:
        url: Database URL. If None, uses environment or ini default.
        ini_path: Path to alembic.ini. Uses default if None.

    Returns:
        Configured Alembic Config object.
    """
    ini = ini_path or DEFAULT_INI_PATH
    cfg = Config(str(ini))

    if url:
        cfg.set_main_option("sqlalchemy.url", url)

    # Ensure script location is set correctly
    script_location = Path(__file__).resolve().parent
    cfg.set_main_option("script_location", str(script_location))

    return cfg


def run_migrations(
    url: str,
    revision: str = "head",
    ini_path: Optional[Path] = None,
) -> None:
    """Run migrations to the specified revision.

    Args:
        url: Database URL.
        revision: Target revision (default: 'head').
        ini_path: Path to alembic.ini.
    """
    cfg = get_alembic_config(url, ini_path)
    logger.info(f"Running migrations to revision: {revision}")
    command.upgrade(cfg, revision)
    logger.info("Migrations completed successfully")


def rollback_migrations(
    url: str,
    revision: str = "-1",
    ini_path: Optional[Path] = None,
) -> None:
    """Roll back migrations to the specified revision.

    Args:
        url: Database URL.
        revision: Target revision (default: '-1' for one step back).
        ini_path: Path to alembic.ini.
    """
    cfg = get_alembic_config(url, ini_path)
    logger.info(f"Rolling back migrations to revision: {revision}")
    command.downgrade(cfg, revision)
    logger.info("Rollback completed")


def get_current_revision(url: str) -> Optional[str]:
    """Get the current database revision.

    Args:
        url: Database URL.

    Returns:
        Current revision string, or None if no migrations applied.
    """
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            return context.get_current_revision()
    finally:
        engine.dispose()


def get_pending_migrations(url: str) -> list[str]:
    """Get list of pending migration revisions.

    Args:
        url: Database URL.

    Returns:
        List of pending revision IDs.
    """
    cfg = get_alembic_config(url)
    script = ScriptDirectory.from_config(cfg)

    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current = context.get_current_revision()

            pending = []
            for rev in script.walk_revisions():
                if current and rev.revision == current:
                    break
                pending.append(rev.revision)

            return list(reversed(pending))
    finally:
        engine.dispose()


def create_migration(
    message: str,
    url: Optional[str] = None,
    autogenerate: bool = True,
    ini_path: Optional[Path] = None,
) -> None:
    """Create a new migration script.

    Args:
        message: Migration message/description.
        url: Database URL for autogenerate comparison.
        autogenerate: Whether to autogenerate from model changes.
        ini_path: Path to alembic.ini.
    """
    cfg = get_alembic_config(url, ini_path)
    logger.info(f"Creating migration: {message}")
    command.revision(cfg, message=message, autogenerate=autogenerate)
    logger.info("Migration script created")


def check_migration_status(url: str) -> dict:
    """Get comprehensive migration status.

    Args:
        url: Database URL.

    Returns:
        Dict with 'current', 'pending', and 'is_up_to_date' keys.
    """
    current = get_current_revision(url)
    pending = get_pending_migrations(url)

    return {
        "current": current,
        "pending": pending,
        "is_up_to_date": len(pending) == 0,
    }


def init_database(url: str, ini_path: Optional[Path] = None) -> None:
    """Initialize a fresh database with all migrations.

    Args:
        url: Database URL.
        ini_path: Path to alembic.ini.
    """
    run_migrations(url, "head", ini_path)
