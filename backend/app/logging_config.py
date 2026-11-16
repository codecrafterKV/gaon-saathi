"""Privacy-preserving logging.

* HTTP access logs are disabled (they would contain IP addresses).
* Application logs never include request bodies, complaint text, evidence,
  tracking codes, IP addresses or user agents.
* Unexpected errors are logged as exception type + code location only, so
  that values embedded in exception messages cannot leak into log files.
"""

from __future__ import annotations

import logging
import traceback

LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
    },
    "loggers": {
        "gaon_saathi": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "uvicorn": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["console"], "level": "INFO", "propagate": False},
        # Access log disabled: it would record client IP addresses.
        "uvicorn.access": {"handlers": [], "level": "CRITICAL", "propagate": False},
    },
}


def safe_exception_summary(exc: BaseException) -> str:
    """Exception type and stack locations, without the exception message."""
    frames = traceback.extract_tb(exc.__traceback__)
    where = " <- ".join(f"{f.filename.rsplit('app', 1)[-1]}:{f.lineno}" for f in reversed(frames[-4:]))
    return f"{type(exc).__name__} at {where}"
