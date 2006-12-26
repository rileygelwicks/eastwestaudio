import logging as _logging
import logging.handlers as _loghandlers
import sys as _sys

logger=_logging.getLogger('ewa')
debug=logger.debug
warn=logger.warn
error=logger.error
critical=logger.critical
info=logger.info
exception=logger.exception

def initLogging(level=_logging.CRITICAL,
                format='%(asctime)s %(filename)s %(levelname)s %(message)s',
                stream=None,
                filename=None,
                datefmt=None,
                rotate=None):
    
    if isinstance(level, str):
        levels=dict((v,k) for k, v in _logging._levelNames.iteritems())
        level=levels.get(level, levels[level.upper()])
    if filename:
        if not rotate:
            handler=_logging.FileHandler(filename, 'a')
        elif rotate == True:
            handler=_loghandlers.RotatingFileHandler(filename,
                                                     mode='a',
                                                     maxBytes=1e7,
                                                     backupCount=10)
        elif isinstance(rotate, int):
            handler=_loghandlers.RotatingFileHandler(filename,
                                                     mode='a',
                                                     maxBytes=rotate,
                                                     backupCount=10)
        elif isinstance(rotate, tuple) and len(rotate==2):
            handler=_loghandlers.RotatingFileHandler(filename,
                                                     mode='a',
                                                     maxBytes=rotate[0],
                                                     backupCount=rotate[1])
        elif not isinstance(rotate, str):
            raise ValueError, "illegal value for logrotate: %s" % rotate
        else:
            #rotate can be two values, corresponding to "when" and
            #"interval" in logging.TimedRotatingHandler
            if ':' in rotate:
                when, interval=rotate.split(':', 1)
                interval=int(interval)
            else:
                when=rotate
                interval=1
            # special values
            if when=='weekly':
                when='w0'
            if when=='daily':
                when='d'
            handler=_loghandlers.TimedRotatingFileHandler(filename,
                                                          when=when,
                                                          interval=interval)
    else:
        stream=stream or _sys.stderr
        handler=_logging.StreamHandler(stream)
    formatter=_logging.Formatter(format, datefmt)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)
    
