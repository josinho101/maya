import os
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from configs.settings import LOGGING, PATHS

LOG_DIR = PATHS["logs"]
os.makedirs(LOG_DIR, exist_ok=True)

_FORMATTER = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class SizeTimedRotatingFileHandler(TimedRotatingFileHandler):
    """Rotates on the time interval (e.g. midnight) OR on max_bytes, whichever comes first."""

    def __init__(self, filename, when="midnight", interval=1, backupCount=0,
                 max_bytes=0, encoding=None):
        # backupCount=0 disables the stdlib's own pruning in doRollover: its
        # getFilesToDelete() matches filenames with an exact dated suffix and
        # won't recognize our counter-suffixed names below, so it would never
        # delete anything. We prune ourselves in doRollover instead.
        super().__init__(filename, when=when, interval=interval,
                          backupCount=0, encoding=encoding)
        self.max_bytes = max_bytes
        self.rotation_backup_count = backupCount

    def shouldRollover(self, record):
        if self.max_bytes > 0 and self.stream:
            msg = "%s\n" % self.format(record)
            if self.stream.tell() + len(msg.encode(self.encoding or "utf-8")) >= self.max_bytes:
                return 1
        return super().shouldRollover(record)

    def rotation_filename(self, default_name):
        # If a size-triggered rollover already happened earlier in the same time
        # bucket, the default dated suffix would collide. doRollover() silently
        # skips rotating when the target name already exists, so without this
        # the active file would just keep growing past max_bytes for the rest
        # of the bucket. Append an incrementing counter to keep each rollover.
        name = super().rotation_filename(default_name)
        if os.path.exists(name):
            counter = 1
            candidate = f"{name}.{counter}"
            while os.path.exists(candidate):
                counter += 1
                candidate = f"{name}.{counter}"
            name = candidate
        return name

    def doRollover(self):
        super().doRollover()
        self._prune_backups()

    def _prune_backups(self):
        if self.rotation_backup_count <= 0:
            return
        dir_name, base_name = os.path.split(self.baseFilename)
        prefix = base_name + "."
        backups = sorted(
            f for f in os.listdir(dir_name or ".")
            if f.startswith(prefix)
        )
        excess = len(backups) - self.rotation_backup_count
        if excess > 0:
            for f in backups[:excess]:
                os.remove(os.path.join(dir_name, f))


def _build_file_handler(filename):
    path = os.path.join(LOG_DIR, filename)
    rotation = LOGGING.get("rotation")

    if rotation == "time":
        handler = TimedRotatingFileHandler(
            path,
            when=LOGGING.get("when", "midnight"),
            interval=LOGGING.get("interval", 1),
            backupCount=LOGGING.get("backup_count", 5),
            encoding="utf-8",
        )
    elif rotation == "both":
        handler = SizeTimedRotatingFileHandler(
            path,
            when=LOGGING.get("when", "midnight"),
            interval=LOGGING.get("interval", 1),
            backupCount=LOGGING.get("backup_count", 5),
            max_bytes=LOGGING.get("max_bytes", 1 * 1024 * 1024),
            encoding="utf-8",
        )
    else:
        handler = RotatingFileHandler(
            path,
            maxBytes=LOGGING.get("max_bytes", 1 * 1024 * 1024),
            backupCount=LOGGING.get("backup_count", 5),
            encoding="utf-8",
        )

    handler.setFormatter(_FORMATTER)
    return handler


def _build_logger(name, filename):
    log = logging.getLogger(name)
    log.setLevel(LOGGING.get("level", "INFO"))
    log.propagate = False

    if not log.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(_FORMATTER)
        log.addHandler(console_handler)
        log.addHandler(_build_file_handler(filename))

    return log


# General application / business-logic logger (generation & execution lifecycle, auth, errors)
logger = _build_logger("app", "app.log")

# Backend REST API request/response logger
api_logger = _build_logger("api", "api.log")

# Full LLM prompt/response logger
llm_logger = _build_logger("llm", "llm.log")
