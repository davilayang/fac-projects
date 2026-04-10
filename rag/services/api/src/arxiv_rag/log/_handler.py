import json
import logging
import traceback

import psycopg


class PostgresHandler(logging.Handler):
    def __init__(self, db_url: str) -> None:
        super().__init__()
        # Strip the SQLAlchemy driver prefix to get a plain libpq URI
        self._db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
        self._conn: psycopg.Connection | None = None

    def _get_conn(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(self._db_url, autocommit=True)
        return self._conn

    def emit(self, record: logging.LogRecord) -> None:
        try:
            conn = self._get_conn()
            chunks = getattr(record, "chunks", None)
            cited = getattr(record, "cited", None)
            error = getattr(record, "error", None) or (
                "".join(traceback.format_exception(*record.exc_info))
                if record.exc_info
                else None
            )
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO logs (
                        trace_id, level, event, latency_ms, query, model,
                        tokens_input, tokens_output, chunks, cited, error
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s::jsonb, %s::jsonb, %s
                    )
                    """,
                    (
                        getattr(record, "trace_id", None),
                        record.levelname,
                        getattr(record, "event", record.getMessage()),
                        getattr(record, "latency_ms", None),
                        getattr(record, "query", None),
                        getattr(record, "model", None),
                        getattr(record, "tokens_input", None),
                        getattr(record, "tokens_output", None),
                        json.dumps(chunks) if chunks is not None else None,
                        json.dumps(cited) if cited is not None else None,
                        error,
                    ),
                )
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        if self._conn and not self._conn.closed:
            self._conn.close()
        super().close()
