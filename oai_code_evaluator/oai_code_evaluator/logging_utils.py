import logging
from pathlib import Path

LOG_NAME = "oai_code_eval"


def setup_logger(log_file: Path | None = None, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(LOG_NAME)
    logger.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.handlers.clear()
    logger.addHandler(sh)
    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger
