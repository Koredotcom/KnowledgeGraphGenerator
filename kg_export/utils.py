from kg_export.log.Logger import Logger

logger = Logger()

color_reset = "\033[0;0m"
color_red = "\033[1;31m"
color_green = "\033[0;32m"

logger_dict = {
    'error': logger.error,
    'info': logger.info,
    'warning': logger.warning,
    'critical': logger.critical,
    'debug': logger.debug
}


def log_message(msg, log_level='info'):
    if log_level == 'error':
        color = color_red
    else:
        color = color_green

    print(color + msg + color_reset)
    logger = logger_dict.get(log_level)
    logger(msg)

def get_index(key, iterable):
    try:
        return iterable.index(key) + 1
    except ValueError:
        return ''
