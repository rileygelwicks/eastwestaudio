import logging as _logging
import sys as _sys

logger=_logging.getLogger('ewa')
debug=logger.debug
warn=logger.warn
error=logger.error
critical=logger.critical
info=logger.info
exception=logger.exception

def initLogging(level=_logging.CRITICAL,
                **kwargs):
    if isinstance(level, str):
        levels=dict((v,k) for k, v in _logging._levelNames.iteritems())
        level=levels.get(level, levels[level.upper()])
    defaults=dict(stream=_sys.stderr,
                  format='%(asctime)s %(filename)s %(levelname)s %(message)s',
                  level=level)
    defaults.update(kwargs)
    _logging.basicConfig(**defaults)


