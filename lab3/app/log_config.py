import os

# e.g. export LOG_LEVEL=DEBUG
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_DIR = "/logs"
os.makedirs(LOG_DIR, exist_ok=True)

MAX_BYTES = 1 * 1024 * 1024  # 1MB
BACKUP_COUNT = 5

log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(request_id)s | %(message)s",
            "defaults": {"request_id": "-"},
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
        "access_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filename": os.path.join(LOG_DIR, "access.log"),
            "maxBytes": MAX_BYTES,
            "backupCount": BACKUP_COUNT,
            "mode": "a",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filename": os.path.join(LOG_DIR, "error.log"),
            "maxBytes": MAX_BYTES,
            "backupCount": BACKUP_COUNT,
            "mode": "a",
        },
    },
    "loggers": {
        "myapp": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "access": {
            "handlers": ["console", "access_file"],
            "level": "INFO",
            "propagate": False,
        },
        "error": {
            "handlers": ["console", "error_file"],
            "level": "WARNING",
            "propagate": False,
        },

        "uvicorn": {"handlers": [], "level": "WARNING", "propagate": False},
        "uvicorn.error": {"handlers": [], "level": "WARNING", "propagate": False},
        "uvicorn.access": {"handlers": [], "level": "WARNING", "propagate": False},
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}


