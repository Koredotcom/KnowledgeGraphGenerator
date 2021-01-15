#!/usr/bin/env python
import logging
from logging.handlers import RotatingFileHandler

LOG_FILENAME = "log/auto_kg.log"


class Singleton(object):
    """
    Singleton interface:
    http://www.python.org/download/releases/2.2.3/descrintro/#__new__
    """

    def __new__(cls, *args, **kwds):
        it = cls.__dict__.get("__it__")
        if it is not None:
            return it
        cls.__it__ = it = object.__new__(cls)
        it.init(*args, **kwds)
        return it

    def init(self, *args, **kwds):
        pass


class LoggerManager(Singleton):
    """
    Logger Manager.
    Handles all logging files.
    """

    def init(self, loggername):
        self.logger = logging.getLogger(loggername)
        rhandler = None
        try:
            rhandler = RotatingFileHandler(
                LOG_FILENAME,
                mode='a',
                maxBytes=10 * 1024 * 1024,
                backupCount=5
            )
        except:
            raise IOError("Couldn't create/open file \"" + \
                          LOG_FILENAME + "\". Check permissions.")

        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            fmt='[%(asctime)s] %(message)s'
        )
        rhandler.setFormatter(formatter)
        self.logger.addHandler(rhandler)

    def debug(self, loggername, msg, args):
        self.logger = logging.getLogger(loggername)
        self.logger.debug(msg, *args)

    def error(self, loggername, msg, args):
        self.logger = logging.getLogger(loggername)
        self.logger.error(msg, *args)

    def info(self, loggername, msg, args):
        self.logger = logging.getLogger(loggername)
        self.logger.info(msg, *args)

    def warning(self, loggername, msg, args):
        self.logger = logging.getLogger(loggername)
        self.logger.warning(msg, *args)

    def critical(self, loggername, msg, args):
        self.logger = logging.getLogger(loggername)
        self.logger.warning(msg, *args)


class Logger(object):
    """
    Logger object.
    """

    def __init__(self, loggername="root"):
        self.lm = LoggerManager(loggername)  # LoggerManager instance
        self.loggername = loggername  # logger name

    def debug(self, msg, *args):
        self.lm.debug(self.loggername, msg, args)

    def error(self, msg, *args):
        self.lm.error(self.loggername, msg, args)

    def info(self, msg, *args):
        self.lm.info(self.loggername, msg, args)

    def warning(self, msg, *args):
        self.lm.warning(self.loggername, msg, args)

    def critical(self, msg, *args):
        self.lm.critical(self.loggername, msg, args)


if __name__ == '__main__':
    logger = Logger()
    a = 'sa'
    b = 'as'
    logger.debug('this %s and %s', a, b)
    logger.critical('this %s and %s', a, b)
