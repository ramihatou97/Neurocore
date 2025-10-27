"""
Logging configuration for the Neurosurgery Knowledge Base
Provides consistent logging across all modules
"""

import logging
import sys
from typing import Optional
from datetime import datetime
from backend.config import settings


# Color codes for terminal output
class ColorCodes:
    """ANSI color codes for terminal output"""
    RESET = "\033[0m"
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BOLD = "\033[1m"


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds colors to log levels
    """

    COLORS = {
        'DEBUG': ColorCodes.CYAN,
        'INFO': ColorCodes.GREEN,
        'WARNING': ColorCodes.YELLOW,
        'ERROR': ColorCodes.RED,
        'CRITICAL': ColorCodes.RED + ColorCodes.BOLD
    }

    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{ColorCodes.RESET}"

        return super().format(record)


def get_logger(
    name: str,
    level: Optional[str] = None,
    use_colors: bool = True
) -> logging.Logger:
    """
    Get or create a logger with consistent formatting

    Args:
        name: Logger name (usually __name__ of the module)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               If None, uses LOG_LEVEL from settings
        use_colors: Whether to use colored output (default: True)

    Returns:
        logging.Logger: Configured logger instance

    Usage:
        from backend.utils.logger import get_logger

        logger = get_logger(__name__)
        logger.info("Starting authentication process")
        logger.error("Authentication failed", exc_info=True)
    """
    logger = logging.getLogger(name)

    # Only configure if logger doesn't have handlers
    if not logger.handlers:
        # Determine log level
        log_level = level or settings.LOG_LEVEL
        logger.setLevel(getattr(logging, log_level.upper()))

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))

        # Create formatter
        if use_colors and sys.stdout.isatty():
            formatter = ColoredFormatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            formatter = logging.Formatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def configure_root_logger(level: Optional[str] = None) -> None:
    """
    Configure the root logger for the entire application

    This should be called once at application startup.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               If None, uses LOG_LEVEL from settings

    Usage:
        from backend.utils.logger import configure_root_logger

        # In main.py
        configure_root_logger()
    """
    log_level = level or settings.LOG_LEVEL
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


class LoggerContextFilter(logging.Filter):
    """
    Filter that adds custom context to log records

    Usage:
        logger = get_logger(__name__)
        filter = LoggerContextFilter(user_id="123", request_id="abc")
        logger.addFilter(filter)
    """

    def __init__(self, **kwargs):
        super().__init__()
        self.context = kwargs

    def filter(self, record):
        for key, value in self.context.items():
            setattr(record, key, value)
        return True
