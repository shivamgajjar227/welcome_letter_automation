import logging
import logging.config
from . import logging_module
import threading
import os
setup_logger_lock = threading.Lock()

CONST_ROTATING_FILE_HANDLER = 'RotatingFileHandler'
CONST_STREAM_HANDLER = 'StreamHandler'
#
def setup_logger(logger_name, log_file=None, level='DEBUG', use_stream_handler=0):
    config = logging_module.create_and_load_config_file()
    logging.config.dictConfig(config)

    if not use_stream_handler:
        my_logger = logging_module.create_logger(logger_name, [CONST_ROTATING_FILE_HANDLER], logging_level=level)
    else:
        my_logger = logging_module.create_logger(logger_name, [CONST_STREAM_HANDLER], logging_level=level)

    return my_logger
#
# def setup_logger(log_name, level='INFO'):
#     log_dir = "/app/app_logs"
#     os.makedirs(log_dir, exist_ok=True)  # <- important for Docker
#
#     config = {
#         "version": 1,
#         "formatters": {"default": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}},
#         "handlers": {
#             "hand_MondayPage_RotatingFileHandler": {
#                 "class": "logging.handlers.RotatingFileHandler",
#                 "filename": os.path.join(log_dir, f"{log_name}.log"),
#                 "maxBytes": 10*1024*1024,
#                 "backupCount": 5,
#                 "formatter": "default"
#             }
#         },
#         "root": {
#             "handlers": ["hand_MondayPage_RotatingFileHandler"],
#             "level": level
#         }
#     }
#     logging.config.dictConfig(config)
#     return logging.getLogger(log_name)
#
# def setup_simple_logger():
#     """Simple logger setup that works in Docker"""
#     logging.basicConfig(
#         level=logging.INFO,
#         format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#         handlers=[
#             logging.StreamHandler(),  # Log to console
#             logging.FileHandler('/app/app_logs/simple_test.log')  # Log to file
#         ]
#     )
#     return logging.getLogger(__name__)
