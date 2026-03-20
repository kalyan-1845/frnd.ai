"""
Decision Logger — Structured logging for every AI brain decision.
Logs: input, classified intent, tool used, result, timestamp.
"""
import os
import logging
from datetime import datetime

# Ensure logs directory exists
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "brain_decisions.log")

# Configure file logger
_file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_file_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
))

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(logging.Formatter(
    "[Brain] %(message)s"
))

logger = logging.getLogger("brain")
logger.setLevel(logging.DEBUG)
logger.addHandler(_file_handler)
logger.addHandler(_console_handler)
# Prevent duplicate logs if module is re-imported
logger.propagate = False


def log_decision(user_input: str, intent_type: str, action: str, target: str,
                 result: str, details: str = ""):
    """
    Log a complete decision cycle.

    Args:
        user_input: Raw user input text
        intent_type: Classified type (chat/task/automation/system/media)
        action: The action name selected
        target: The target/argument for the action
        result: Outcome (success/failure/fallback/skipped)
        details: Optional extra details
    """
    msg = (
        f"INPUT=\"{user_input[:80]}\" | "
        f"TYPE={intent_type} | "
        f"ACTION={action} | "
        f"TARGET=\"{str(target)[:60]}\" | "
        f"RESULT={result}"
    )
    if details:
        msg += f" | DETAILS={details}"

    if result == "failure":
        logger.warning(msg)
    elif result == "blocked":
        logger.error(msg)
    else:
        logger.info(msg)


def log_error(component: str, error: Exception, context: str = ""):
    """Log a module error with context."""
    logger.error(f"COMPONENT={component} | ERROR={type(error).__name__}: {error} | CTX={context}")


def log_event(event: str, details: str = ""):
    """Log a general system event."""
    logger.info(f"EVENT={event} | {details}")
