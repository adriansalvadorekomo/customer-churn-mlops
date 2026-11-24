"""Structured events for the ELK monitoring layer.

Every event is one JSON line on stdout. Docker keeps container stdout as its log;
in the ``monitoring`` compose profile Filebeat ships those lines to Logstash,
which parses them into Elasticsearch, and Kibana charts them. Without that
profile the lines are simply readable logs: nothing here needs Elastic to run.

Events (the ``event`` field):

- ``http_request``: method, path, status, duration_ms (every API call)
- ``prediction``: exited (0 stays, 1 leaves) for each ``POST /predict``
- ``training_run`` / ``evaluation_run``: flow, accuracy, churner recall
  (class 1), duration_s

Stdlib only, so the gates and tests run without extra dependencies.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import UTC, datetime
from typing import Self

SERVICE_DEFAULT = "churn-mlops"


class JsonFormatter(logging.Formatter):
    """Render a record as one JSON object; extra fields go under their own keys."""

    def format(self, record: logging.LogRecord) -> str:
        doc = {
            "@timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname.lower(),
            "service": getattr(record, "service", SERVICE_DEFAULT),
            "event": record.getMessage(),
        }
        doc.update(getattr(record, "fields", {}))
        return json.dumps(doc, default=str)


class _StdoutHandler(logging.StreamHandler):
    """Writes to whatever ``sys.stdout`` is now (test capture, Docker, a terminal)."""

    def emit(self, record: logging.LogRecord) -> None:
        self.stream = sys.stdout
        super().emit(record)


def get_logger(service: str) -> logging.LoggerAdapter:
    """A logger that writes JSON events to stdout, tagged with ``service``."""
    logger = logging.getLogger(f"churn.events.{service}")
    if not logger.handlers:
        handler = _StdoutHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        # Prefect and uvicorn configure the root logger; keep events out of their formats.
        logger.propagate = False
    return logging.LoggerAdapter(logger, {"service": service})


def emit(log: logging.LoggerAdapter, event: str, **fields) -> None:
    """Log one structured event: ``emit(log, "prediction", exited=0)``."""
    # LoggerAdapter.info would replace ``extra``; log through the wrapped logger instead.
    log.logger.info(event, extra={"service": log.extra["service"], "fields": fields})


def churner_recall(confusion: list[list[int]]) -> float | None:
    """Recall on class 1 from a 2x2 confusion matrix [[tn, fp], [fn, tp]]."""
    (_, _), (fn, tp) = confusion
    return round(tp / (tp + fn), 4) if (tp + fn) else None


class Timer:
    """``with Timer() as t: ...`` then ``t.seconds``."""

    def __enter__(self) -> Self:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc) -> None:
        self.seconds = round(time.perf_counter() - self._start, 3)
