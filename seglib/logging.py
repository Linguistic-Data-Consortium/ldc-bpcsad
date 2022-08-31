"""Logging utilities."""
import logging
import sys

from tqdm import tqdm

__all__ = ['getLogger', 'setup_logger', 'CustomFormatter',
           'CustomStreamHandler']


ERROR = logging.ERROR
WARN = logging.WARN
WARNING = logging.WARNING
INFO = logging.INFO
DEBUG = logging.DEBUG
LEVELS = [ERROR, WARN, INFO, DEBUG]


class CustomStreamHandler(logging.Handler):
    """Mimics ``logging.StreamHandler``, but outputs WARN/ERROR to STDERR and
    all other levels to STDOUT.
    """
    def __init__(self, stdout=None, stderr=None, formatter=None):
        logging.Handler.__init__(self)
        self.stdout = sys.stdout if stdout is None else stdout
        self.stderr = sys.stderr if stderr is None else stderr
        self.formatter = formatter

    def flush(self):
        """Flushes the stream."""
        for stream in (self.stdout, self.stderr):
            stream.flush()

    def emit(self, record):
        try:
            msg = self.format(record)
            if record.levelno > INFO:
                stream = self.stderr
            else:
                stream = self.stdout
            msg = f'{msg}'
            tqdm.write(msg, file=stream)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class CustomFormatter(logging.Formatter):
    """Formatter with different formats for each logging level.

    Parameters
    ----------
    include_date : bool, optional
        If True, include date in logged messages.
        (Default: False)

    include_name : bool, optional
        If True, include logger name named in logged messages,
        (Default: False)

    Attributes
    ----------
    _levelno_to_fmt : dict
        Mapping from level numbers to format strings.
    """
    def __init__(self, include_date=False, include_name=False):
        logging.Formatter.__init__(self, datefmt='%Y-%m-%d %H:%M:%S')
        self.include_date = include_date
        self.include_name = include_name
        def expand_fmt(fmt):
            if include_name:
                fmt = '%(name)s ' + fmt
            if include_date:
                fmt = '%(asctime)s ' + fmt
            return fmt
        self._levelno_to_fmt = {
            ERROR : expand_fmt('ERROR: %(message)s'),
            WARN : expand_fmt('WARNING: %(message)s'),
            WARNING : expand_fmt('WARNING: %(message)s'),
            INFO : expand_fmt('%(message)s'),
	    DEBUG : expand_fmt('DEBUG: %(message)s'),
            }

    def format(self, record):
        orig_fmt = self._style._fmt
        self._style._fmt = self._levelno_to_fmt.get(record.levelno, orig_fmt)
        result = logging.Formatter.format(self, record)
        self._style._fmt = orig_fmt
        return result


def getLogger(name=None):
    """Return a logger with the specified name, creating it if necessary.
    If no name is specified, return the root logger.
    """
    return logging.getLogger(name)


def setup_logger(logger, include_date=False, include_name=False, level=INFO,
                 output_to_stdout=False):
    """Setup logger with appropriate handlers.

    Should only ever be called on root logger.

    Parameters
    ----------
    include_date : bool, optional
        If True, include date in logged messages.
        (Default: False)

    include_name : bool, optional
        If True, include logger name in logged messages,
        (Default: False)

    level : int, optional
        Logging level.
        (Default: INFO)

    output_to_stdout : bool, optional
        If True, output all messages to STDOUT. Otherwise, only INFO will be
        output to STDOUT and all other levels to STDERR.
    """
    logger.setLevel(level)
    formatter = CustomFormatter(include_date, include_name)
    stdout = sys.stdout
    stderr = sys.stdout if output_to_stdout else sys.stderr
    handler = CustomStreamHandler(
        formatter=formatter, stdout=stdout, stderr=stderr)
    logger.handlers = []
    logger.addHandler(handler)
