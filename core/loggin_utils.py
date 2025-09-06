import logging
import logging.config
from . import logging_module
import threading
setup_logger_lock = threading.Lock()

CONST_ROTATING_FILE_HANDLER = 'RotatingFileHandler'
CONST_STREAM_HANDLER = 'StreamHandler'

def setup_logger(logger_name, log_file=None, level='DEBUG', use_stream_handler=0):
    config = logging_module.create_and_load_config_file()
    logging.config.dictConfig(config)

    if not use_stream_handler:
        my_logger = logging_module.create_logger(logger_name, [CONST_ROTATING_FILE_HANDLER], logging_level=level)
    else:
        my_logger = logging_module.create_logger(logger_name, [CONST_STREAM_HANDLER], logging_level=level)

    return my_logger
