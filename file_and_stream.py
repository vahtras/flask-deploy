import logging
formatter = logging.Formatter("%(levelname)s:%(funcName)s:%(message)s")

def stream_handler():
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    return ch

def file_handler(logfile):
    fh = logging.FileHandler(logfile)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    return fh

def file_and_stream(logger, logfile):
    logger.addHandler(stream_handler())
    logger.addHandler(file_handler(logfile))


def f():
    logger.debug('foo')
    logger.info('bar')


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    file_and_stream(logger, 'my.log')
    f()
