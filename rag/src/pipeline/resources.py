# Shared Dagster resources used across all pipeline definitions.

import threading

import dagster as dg
from pydantic import PrivateAttr
from sqlalchemy import Engine

from pipeline.config import build_database_url
from pipeline.lib.db import get_engine


class DatabaseResource(dg.ConfigurableResource):
    """PostgreSQL connection for the ingestion schema."""

    database_url: str = ""

    _engine: Engine | None = PrivateAttr(default=None)
    _lock: threading.Lock = PrivateAttr(default_factory=threading.Lock)

    def get_engine(self) -> Engine:
        if self._engine is None:
            with self._lock:
                if self._engine is None:
                    url = self.database_url or build_database_url()
                    self._engine = get_engine(url)
        return self._engine
