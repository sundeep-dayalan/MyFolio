"""
Logging configuration and setup.
"""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Dict, Any

from ..settings import settings


def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration."""
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": "default",
                "stream": sys.stdout,
            },
        },
        "loggers": {
            "": {  # root logger
                "level": settings.log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

    # Add file handler if log file is specified
    if settings.log_file:
        log_file_path = Path(settings.log_file)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": settings.log_level,
            "formatter": "detailed",
            "filename": str(log_file_path),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        }

        # Add file handler to all loggers
        for logger_config in config["loggers"].values():
            logger_config["handlers"].append("file")

    return config


def setup_logging() -> None:
    """Setup application logging."""
    logging_config = get_logging_config()
    logging.config.dictConfig(logging_config)

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Disable verbose Azure SDK logging
    azure_loggers = [
        "azure.core.pipeline.policies.http_logging_policy",
        "azure.cosmos",
        "azure.keyvault",
        "azure.identity",
        "azure.core",
        "azure",
    ]

    for logger_name in azure_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)
