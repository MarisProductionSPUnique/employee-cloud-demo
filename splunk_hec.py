"""Splunk HTTP Event Collector logging support.

The integration is disabled unless both SPLUNK_HEC_URL and SPLUNK_HEC_TOKEN
are configured. Secrets should be supplied through Render environment variables,
never committed to Git.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any


class SplunkHECHandler(logging.Handler):
    """Send Python log records to Splunk HEC as JSON events."""

    def __init__(
        self,
        hec_url: str,
        token: str,
        *,
        index: str = "",
        source: str = "employee-cloud-demo",
        sourcetype: str = "_json",
        verify_ssl: bool = True,
        timeout: float = 2.0,
    ) -> None:
        super().__init__()
        self.hec_url = self._normalise_url(hec_url)
        self.token = token
        self.index = index
        self.source = source
        self.sourcetype = sourcetype
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.host = os.getenv("RENDER_SERVICE_NAME") or socket.gethostname()

    @staticmethod
    def _normalise_url(url: str) -> str:
        url = url.strip().rstrip("/")
        if not url.endswith("/services/collector/event"):
            url += "/services/collector/event"
        return url

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
            try:
                parsed_message: Any = json.loads(message)
            except (json.JSONDecodeError, TypeError):
                parsed_message = message

            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "employee-operations-lab",
                "level": record.levelname,
                "logger": record.name,
                "message": parsed_message,
            }

            payload: dict[str, Any] = {
                "time": record.created,
                "host": self.host,
                "source": self.source,
                "sourcetype": self.sourcetype,
                "event": event,
            }
            if self.index:
                payload["index"] = self.index

            request = urllib.request.Request(
                self.hec_url,
                data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
                headers={
                    "Authorization": f"Splunk {self.token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )

            context = None
            if not self.verify_ssl:
                context = ssl._create_unverified_context()  # noqa: SLF001

            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
                context=context,
            ) as response:
                if response.status >= 300:
                    raise RuntimeError(f"Splunk HEC returned HTTP {response.status}")
        except Exception:
            self.handleError(record)


def configure_splunk_logging(logger: logging.Logger) -> bool:
    """Attach a Splunk HEC handler when the required env vars are present."""

    hec_url = os.getenv("SPLUNK_HEC_URL", "").strip()
    token = os.getenv("SPLUNK_HEC_TOKEN", "").strip()
    if not hec_url or not token:
        return False

    if any(isinstance(handler, SplunkHECHandler) for handler in logger.handlers):
        return True

    verify_ssl = os.getenv("SPLUNK_VERIFY_SSL", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }

    handler = SplunkHECHandler(
        hec_url=hec_url,
        token=token,
        index=os.getenv("SPLUNK_INDEX", "").strip(),
        source=os.getenv("SPLUNK_SOURCE", "employee-cloud-demo").strip(),
        sourcetype=os.getenv("SPLUNK_SOURCETYPE", "_json").strip(),
        verify_ssl=verify_ssl,
        timeout=float(os.getenv("SPLUNK_HEC_TIMEOUT", "2")),
    )
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.info("Splunk HEC logging enabled")
    return True
