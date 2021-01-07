import logging
import os

from pythonjsonlogger import jsonlogger

def get_logger(name):
    logger = logging.getLogger()

    # Remove default lambda handler
    if len(logger.handlers):
        logger.removeHandler(logger.handlers[0])

    logger.setLevel(os.environ.get('LOG_LEVEL', logging.DEBUG))

    formatter = jsonlogger.JsonFormatter(fmt='%(asctime)s %(levelname)s %(name)s %(message)s')

    json_handler = logging.StreamHandler()
    json_handler.setFormatter(formatter)
    logger.addHandler(json_handler)

    logger = logging.getLogger(name)
    return logger
