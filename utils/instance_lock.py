"""Prevent running multiple bot instances at the same time."""

import os
import sys

from config import BASE_DIR
from utils.logging import logger

LOCK_PATH = BASE_DIR / ".bot.lock"
_lock_file = None


def _is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _lock_exclusive(file_obj) -> None:
    """Non-blocking exclusive lock (Windows msvcrt / Unix fcntl)."""
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(file_obj.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(file_obj.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(file_obj) -> None:
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(file_obj.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)


def acquire_instance_lock() -> None:
    """Exit if another bot instance is already running."""
    global _lock_file

    if LOCK_PATH.exists():
        try:
            old_pid = int(LOCK_PATH.read_text(encoding="utf-8").strip())
        except ValueError:
            old_pid = None
        if old_pid and _is_pid_running(old_pid):
            logger.error(
                "Bot is already running in another process. "
                "Stop it (Ctrl+C / kill) before starting a new one."
            )
            sys.exit(1)
        LOCK_PATH.unlink(missing_ok=True)

    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    _lock_file = open(LOCK_PATH, "w", encoding="utf-8")

    try:
        _lock_exclusive(_lock_file)
    except OSError:
        logger.error(
            "Bot is already running in another process. "
            "Stop it (Ctrl+C / kill) before starting a new one."
        )
        sys.exit(1)

    _lock_file.write(str(os.getpid()))
    _lock_file.flush()


def release_instance_lock() -> None:
    """Release lock file on shutdown."""
    global _lock_file

    if _lock_file is not None:
        try:
            _unlock(_lock_file)
            _lock_file.close()
        except OSError:
            pass
        _lock_file = None

    try:
        LOCK_PATH.unlink(missing_ok=True)
    except OSError:
        pass
