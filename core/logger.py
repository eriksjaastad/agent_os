# core/logger.py
import logging
import os

# CONFIGURABLE: Log file path can be set via environment variable.
# This allows different environments (dev, prod, testing) to use different log locations.
# Default: "agent.log" in current working directory
LOG_FILE = os.getenv("AGENT_OS_LOG_FILE", "agent.log")


def setup_logger(name: str = "agent_os"):
    """
    Configure and return a logger with file and console handlers.

    This function is idempotent - calling it multiple times with the same name
    will return the same logger instance without adding duplicate handlers.

    Args:
        name: Logger name (default: "agent_os")

    Returns:
        Configured logging.Logger instance
    """
    logger = logging.getLogger(name)

    # BUGFIX: Prevent duplicate handlers when setup_logger() is called multiple times.
    # This can happen during testing, module reimports, or if multiple parts of the
    # application call setup_logger(). Without this check, each call would add new
    # handlers, causing duplicate log entries.
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # File handler - writes to persistent log file
    fh = logging.FileHandler(LOG_FILE)
    fh.setLevel(logging.INFO)

    # Console handler - writes to stdout for immediate feedback
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # Formatter with timestamp, logger name, level, and message
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger
