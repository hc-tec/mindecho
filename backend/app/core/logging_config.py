import logging
from logging.config import dictConfig

class LogConfig:
    """
    Logging configuration for the application.
    """
    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": "INFO",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "app": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "httpx": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
            "eai_rpc_client_async": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
            "aiohttp": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": "INFO",
        },
    }

    @classmethod
    def setup_logging(cls):
        """
        Applies the logging configuration.
        """
        dictConfig(cls.LOGGING_CONFIG)

def get_logger(name: str) -> logging.Logger:
    """
    Utility function to get a logger instance.
    """
    return logging.getLogger(name)
