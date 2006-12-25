"""
A barebones config object loaded from a Python config file.
"""

import os

try:
    os.fork
except NameError:
    have_fork=False
else:
    have_fork=True

class _config(object):
    def __init__(self):
        pass

    def load(self, filename):
        filename=os.path.abspath(filename)
        s=open(filename).read()
        codeobj=compile(s, filename, 'exec')
        env={}
        exec codeobj in {}, env
        # load env selectively into self.__dict__
        for key in (k for k in env if not k.startswith('_')):
            self.__dict__[key]=env[key]

    def merge_defaults(self, **kw):
        for k in kw:
            self.__dict__.setdefault(k, kw[k])

    def keys(self):
        return self.__dict__.keys()

    def __iter__(self):
        return self.__dict__.__iter__()

    def iteritems(self):
        return self.__dict__.iteritems()

    def clear(self):
        self.__dict__
    
Config=_config()

DEFAULTS=dict(loglevel='critical',
              logfile=None,
              logrotate=None,
              daemonize=True,
              use_xsendfile=True,
              sendfile_header='X-Sendfile',
              refresh_rate=0,
              protocol='fcgi',
              interface='127.0.0.1',
              port=5000,
              unixsocket=None,
              umask=None,
              stream=False,
              basedir=None,
              rulefile=None,
              targetdir=None,
              pidfile=None,
              use_threads=not have_fork,
              engine='default',
              user=None,
              group=None,
              content_disposition='attachment',
              lame_path='/usr/bin/lame',
              min_spare=None,
              max_spare=None,
              max_threads=None,
              max_children=None,
              max_requests=None
              )

def initConfig(configfile):
    Config.load(configfile)
    Config.merge_defaults(**DEFAULTS)

__all__=['Config', 'initConfig']
