import atexit
import logging
import logging.handlers
import queue
import sys

from arxiv_rag.log._context import get_trace_id
from arxiv_rag.log._formatter import JSONFormatter
from arxiv_rag.log._handler import PostgresHandler

_listener: logging.handlers.QueueListener | None = None


class _TraceIdFilter(logging.Filter):
    """Stamps the current trace_id onto each record before it enters the queue.

    Must run on the calling thread (not the background listener thread)
    so the ContextVar is read from the correct context.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id() or None  # type: ignore[attr-defined]
        return True


def configure_logging(db_url: str, level: int = logging.INFO) -> None:
    global _listener

    log_queue: queue.Queue = queue.Queue()

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(JSONFormatter())

    postgres_handler = PostgresHandler(db_url)

    _listener = logging.handlers.QueueListener(
        log_queue,
        stdout_handler,
        postgres_handler,
        respect_handler_level=True,
    )
    _listener.start()

    queue_handler = logging.handlers.QueueHandler(log_queue)
    queue_handler.addFilter(_TraceIdFilter())

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(queue_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    atexit.register(_shutdown)


def _shutdown() -> None:
    if _listener:
        _listener.stop()
