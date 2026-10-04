"""Connection pooling for database sessions.

Provides a thread-safe pool of SQLAlchemy engines with configurable
pool sizes, timeouts, and health checks.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Dict, Generator, Optional

from sqlalchemy import create_engine, text, Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool


class DatabasePool:
    """Manages a pool of database connections.

    Supports multiple named pools with different configurations.
    Thread-safe singleton pattern.
    """

    _instance: Optional["DatabasePool"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "DatabasePool":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._pools: Dict[str, Engine] = {}
        self._sessionmakers: Dict[str, sessionmaker] = {}
        self._pool_lock = threading.Lock()
        self._initialized = True

    def create_pool(
        self,
        name: str,
        url: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        echo: bool = False,
    ) -> Engine:
        """Create a new connection pool.

        Args:
            name: Unique pool identifier.
            url: Database URL (e.g., 'sqlite:///app.db').
            pool_size: Number of persistent connections.
            max_overflow: Additional connections beyond pool_size.
            pool_timeout: Seconds to wait for a connection.
            pool_recycle: Seconds before recycling connections.
            echo: Log all SQL statements.

        Returns:
            The created SQLAlchemy Engine.
        """
        with self._pool_lock:
            if name in self._pools:
                raise ValueError(f"Pool '{name}' already exists")

            # SQLite doesn't support QueuePool well; use StaticPool for :memory:
            # so all connections share the same in-memory database.
            if url.startswith("sqlite") and ":memory:" in url:
                from sqlalchemy.pool import StaticPool
                engine = create_engine(
                    url,
                    echo=echo,
                    poolclass=StaticPool,
                    connect_args={"check_same_thread": False},
                )
            else:
                engine = create_engine(
                    url,
                    echo=echo,
                    poolclass=QueuePool,
                    pool_size=pool_size,
                    max_overflow=max_overflow,
                    pool_timeout=pool_timeout,
                    pool_recycle=pool_recycle,
                )

            self._pools[name] = engine
            self._sessionmakers[name] = sessionmaker(bind=engine, expire_on_commit=False)
            return engine

    def get_engine(self, name: str = "default") -> Engine:
        """Get an engine by pool name."""
        with self._pool_lock:
            if name not in self._pools:
                raise KeyError(f"Pool '{name}' not found. Create it first with create_pool().")
            return self._pools[name]

    def get_session(self, name: str = "default") -> Session:
        """Get a new session from the named pool."""
        with self._pool_lock:
            if name not in self._sessionmakers:
                raise KeyError(f"Pool '{name}' not found. Create it first with create_pool().")
            return self._sessionmakers[name]()

    @contextmanager
    def session_scope(self, name: str = "default") -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations.

        Automatically commits on success, rolls back on exception.
        """
        session = self.get_session(name)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_pool_status(self, name: str = "default") -> Dict[str, int | str]:
        """Get status information for a pool."""
        engine = self.get_engine(name)
        pool = engine.pool
        # Some pool implementations (e.g., NullPool) lack certain methods
        return {
            "size": pool.size() if hasattr(pool, "size") else 0,
            "checked_in": pool.checkedin() if hasattr(pool, "checkedin") else 0,
            "checked_out": pool.checkedout() if hasattr(pool, "checkedout") else 0,
            "overflow": pool.overflow() if hasattr(pool, "overflow") else 0,
        }

    def health_check(self, name: str = "default") -> bool:
        """Check if the database is reachable."""
        try:
            engine = self.get_engine(name)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def dispose_pool(self, name: str = "default") -> None:
        """Dispose of a pool and all its connections."""
        with self._pool_lock:
            if name in self._pools:
                self._pools[name].dispose()
                del self._pools[name]
                del self._sessionmakers[name]

    def dispose_all(self) -> None:
        """Dispose of all pools."""
        with self._pool_lock:
            for engine in self._pools.values():
                engine.dispose()
            self._pools.clear()
            self._sessionmakers.clear()


def get_pool() -> DatabasePool:
    """Get the singleton DatabasePool instance."""
    return DatabasePool()
