import logging
import os

from pythonjsonlogger import jsonlogger

def get_logger(name):
    logger = logging.getLogger()

    # Remove default lambda handler
    if len(logger.handlers):
        def_handler = logger.handlers[0]
        logger.removeHandler(def_handler)
        def_handler.close()

    logger.setLevel(os.environ.get('LOG_LEVEL', logging.DEBUG))

    formatter = jsonlogger.JsonFormatter(fmt='%(asctime)s %(levelname)s %(name)s %(message)s')

    json_handler = logging.StreamHandler()
    json_handler.setFormatter(formatter)
    logger.addHandler(json_handler)

    logger = logging.getLogger(name)
    return logger
