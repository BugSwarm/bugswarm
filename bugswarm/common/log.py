import logging
import sys

from typing import Optional


def debug(*args):
    logging.getLogger().debug(_log_string(*args))


def info(*args):
    logging.getLogger().info(_log_string(*args))


def warning(*args):
    logging.getLogger().warning(_log_string(*args))


def error(*args):
    logging.getLogger().error(_log_string(*args))


def critical(*args):
    logging.getLogger().critical(_log_string(*args))


def _log_string(*args):
    str_args = [str(arg) for arg in args]
    return ' '.join(str_args)


def config_logging(log_level: int, log_file_path: Optional[str] = None):
    logger = logging.getLogger()
    logger.handlers = []  # Remove previously added handlers before adding new ones.

    formatter = logging.Formatter('[%(levelname)8s] --- %(message)s')

    if log_file_path:
        file_handler = logging.FileHandler(log_file_path, mode='w')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(log_level)
    logger.addHandler(stream_handler)

    logger.setLevel(log_level)
