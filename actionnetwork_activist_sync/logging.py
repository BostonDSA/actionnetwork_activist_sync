"""
Helpers for configuring logging in the lambdas
"""

import logging
import os
import sys

from pythonjsonlogger import jsonlogger

def get_logger(name):
    """
    Get a preconfigured logger
    """

    logger = logging.getLogger()

    # Remove default lambda handler
    if len(logger.handlers) > 0:
        def_handler = logger.handlers[0]
        logger.removeHandler(def_handler)
        def_handler.close()

    logger.setLevel(os.environ.get('ROOT_LOG_LEVEL', logging.ERROR))

    formatter = jsonlogger.JsonFormatter(fmt='%(asctime)s %(levelname)s %(name)s %(message)s')

    json_handler = logging.StreamHandler()
    json_handler.setFormatter(formatter)
    logger.addHandler(json_handler)

    logger = logging.getLogger(name)
    logger.setLevel(os.environ.get('LOG_LEVEL', logging.DEBUG))

    def handle_exception(exc_type, exc_value, exc_traceback):
        logger.error("EXCEPTION", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception


    return logger
