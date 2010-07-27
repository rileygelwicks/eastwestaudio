import errno
import logging
from optparse import OptionParser
import os
from os import path
import re
import sys
import time

try:
    import grp
    import pwd
    have_unix = 1
except ImportError:
    have_unix = 0

try:
    from functools import partial
except ImportError:

    def partial(func, *args, **kw):

        def inner(*_args, **_kw):
            d = kw.copy()
            d.update(_kw)
            return func(*(args + _args), **d)
        return inner

try:
    from flup.server.scgi_fork import WSGIServer as SCGIServer
    from flup.server.fcgi_fork import WSGIServer as FCGIServer
    from flup.server.scgi import WSGIServer as SCGIThreadServer
    from flup.server.fcgi import WSGIServer as FCGIThreadServer
    haveflup = True
except ImportError:
    haveflup = False
try:
    from paste import httpserver
    havepaste = True
except ImportError:
    havepaste = False

import ewa.mp3
import ewa.audio
from ewa.config import Config, initConfig
from ewa.lighttpd_hack_middleware import LighttpdHackMiddleware
from ewa.logutil import (debug, error, exception, info, logger,
                         initLogging, warn)
from ewa.wsgiapp import EwaApp
from ewa.rules import FileRule
from ewa import __version__

VERSION_TEXT = """\
%%s %s

Copyright (C) 2007, 2010 WNYC New York Public Radio.
This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

Written by Jacob Smullyan and others, not necessarily in that order.
""" % __version__


SERVE_DESCRIPTION = """\
Starts a WSGI application that produces combined MP3 files
according to the specified rules.
"""

RULE_DESCRIPTION = """\
Produces a combined MP3 file according to the specified rules.
"""

SPLICE_DESCRIPTION = """\
Splices MP3 files together.
"""


def get_serve_parser():
    protocols = []
    if haveflup:
        protocols.extend(['fcgi', 'scgi'])
    if havepaste:
        protocols.append('http')
    if not protocols:
        print >> sys.stderr, ("no protocols available; "
                              "please install paste and/or flup")
        sys.exit(1)
    usage = "usage: %prog [options]"
    parser = OptionParser(usage, description=SERVE_DESCRIPTION)
    parser.add_option('-c',
                      '--config',
                      dest='configfile',
                      default=None,
                      help="path to ewa config file")
    parser.add_option('-D',
                      '--nodaemonize',
                      action='store_true',
                      default=False,
                      dest='nodaemonize',
                      help="don't daemonize, regardless of config settings")
    parser.add_option('--version',
                      action="store_true",
                      dest="version",
                      help="show version and exit")
    parser.add_option('--lighttpd-hack',
                      action='store_true',
                      default=False,
                      dest='lighttpd_hack',
                      help=("hack for some versions of lighttpd "
                            "to force SCRIPT_NAME to ''"))
    return parser


def get_splice_parser():
    usage = "%prog [options] files"
    parser = OptionParser(usage, description=SPLICE_DESCRIPTION)
    parser.add_option('-o',
                      '--output',
                      dest='output',
                      help="output file (default: stdout)",
                      default='-',
                      metavar='OUT')
    parser.add_option('-t',
                      '--tagfile',
                      dest="tagfile",
                      help="tag file",
                      default=None,
                      metavar="TAGFILE")
    parser.add_option('-d',
                      '--debug',
                      action='store_true',
                      default=False,
                      help="print debugging information",
                      dest='debugmode')
    parser.add_option('-s',
                      '--sanitycheck',
                      action='store_true',
                      default=False,
                      help="sanity check the input mp3 files",
                      dest='sanitycheck')
    parser.add_option('-e',
                      '--engine',
                      default='default',
                      dest='engine',
                      metavar='ENGINE',
                      choices=('default', 'mp3cat', 'sox'),
                      help=("which splicing engine to use (default ewa "
                            "splicer, mp3cat, or sox)"))
    parser.add_option('--version',
                      action="store_true",
                      dest="version",
                      help="show version and exit")
    return parser


def get_ap_parser():
    usage = "%prog [options] [files]"
    parser = OptionParser(usage, description=RULE_DESCRIPTION)

    parser.add_option('-c',
                      '--config',
                      dest='configfile',
                      default=None,
                      help="path to ewa config file")
    parser.add_option('-r',
                      '--recursive',
                      dest='recursive',
                      help="recurse through directories",
                      action='store_true',
                      default=False)
    parser.add_option('--rulefile',
                      dest='rulefile',
                      help="specify a rulefile",
                      metavar='RULEFILE')
    parser.add_option('-d',
                      '--debug',
                      action='store_true',
                      default=False,
                      help="print debugging information",
                      dest='debugmode')
    parser.add_option('-n',
                      '--dry-run',
                      action='store_true',
                      default=False,
                      dest='dryrun',
                      help="don't do anything, just print what would be done")
    parser.add_option('-e',
                      '--engine',
                      default=None,
                      dest='engine',
                      metavar='ENGINE',
                      choices=('default', 'mp3cat', 'sox'),
                      help=("which splicing engine to use (default ewa "
                            "splicer, mp3cat, or sox)"))
    parser.add_option('-a',
                      '--absolute',
                      default=False,
                      dest='absolute',
                      action='store_true',
                      help=("interpret file paths relative to the filesystem "
                            "rather than the basedir (default: no)"))

    parser.add_option('-t',
                      '--configtest',
                      default=False,
                      dest='configtest',
                      action='store_true',
                      help="just test the config file for syntax errors")

    parser.add_option('-x',
                      '--max-age',
                      default=0,
                      dest='max_age',
                      type=int,
                      help=('max age before generated files expire and '
                            'are regenerated. Default is 0, which means no '
                            'expiration.  -1 will force regeneration.'))

    parser.add_option('-D',
                      '--delete',
                      default=False,
                      action='store_true',
                      help=('delete files in combined directory that are '
                            'not in the the main directory'))

    parser.add_option('--version',
                      action="store_true",
                      dest="version",
                      help="show version and exit")
    return parser


def resolve_engine(enginename):
    if enginename == 'default':
        return ewa.mp3._default_splicer
    elif enginename == 'mp3cat':
        return ewa.mp3._mp3cat_splicer
    elif enginename == 'sox':
        return ewa.mp3._sox_splicer


def do_splice(args):
    parser = get_splice_parser()
    opts, args = parser.parse_args(args)
    if opts.version:
        print VERSION_TEXT % path.basename(sys.argv[0])
        sys.exit(0)
    if opts.debugmode:
        Config.loglevel = logging.DEBUG
    initLogging(level=Config.loglevel,
                filename=Config.logfile)

    engine = resolve_engine(opts.engine)
    if opts.sanitycheck:
        try:
            ewa.mp3.mp3_sanity_check(args)
        except Exception, e:
            print >> sys.stderr, 'sanity check failed: %s' % str(e)
            sys.exit(1)

    use_stdout = opts.output == '-'
    if use_stdout:
        fp = sys.stdout
    else:
        fp = open(options.output, 'wb')
    for chunk in ewa.mp3.splice(args, opts.tagfile, splicer=engine):
        fp.write(chunk)
    if not use_stdout:
        fp.close()


def do_audioprovider(args):
    parser = gs = get_ap_parser()
    opts, args = parser.parse_args(args)
    if opts.version:
        print VERSION_TEXT % path.basename(sys.argv[0])
        sys.exit(0)
    configfile = _find_config(opts.configfile)
    if not configfile:
        parser.error('no config file specified or found in the usual places')
    if not path.exists(configfile):
        parser.error("config file does not exist: %s" % configfile)
    initConfig(configfile)

    # override config
    if opts.debugmode:
        Config.loglevel = 'debug'
    if opts.rulefile:
        Config.rulefile = opts.rulefile
    if opts.engine:
        Config.engine = engine
    engine = resolve_engine(Config.engine)
    initLogging(level=Config.loglevel)
    rule = FileRule(Config.rulefile)

    if opts.configtest:
        print "Config OK"
        sys.exit(0)

    provider = ewa.audio.FSAudioProvider(Config.basedir,
                                         Config.targetdir)
    mainpath = provider.get_main_path("")
    if not mainpath.endswith('/'):
        # currently this won't happen,
        # but better safe than sorry
        mainpath += '/'
    if opts.absolute:
        abs = [path.abspath(f) for f in args]
        stripped_main = mainpath[:-1]
        if not path.commonprefix([stripped_main] + abs) == stripped_main:
            debug("absolute paths of files: %s", abs)
            debug("mainpath: %s", mainpath)
            parser.error("files outside managed directory")
        idx = len(mainpath)
        args = [x[idx:] for x in abs]
    else:
        args = [re.sub('/*(.*)', r'\1', x) for x in args]

    if opts.delete:
        if not opts.recursive:
            parser.error("delete only works in recursive mode")
        delete_finder = DeleteFinder(args, mainpath)
        for file, isdir in delete_finder:
            info('deleting %s', file)
            if not opts.dryrun:
                try:
                    if isdir:
                        os.rmdir(file)
                    else:
                        os.unlink(file)
                except Exception, e:
                    error("couldn't unlink %s: %s", file, e)

    if opts.recursive:
        # replace args with an iterator that finds mp3 files
        if opts.max_age == -1:
            args = RecursiveMp3FileIterator(args, mainpath)
        else:
            args = RecursiveChangedMp3FileIterator(args,
                                                   mainpath,
                                                   opts.max_age)
    if not args:
        parser.error("no files specified")

    if opts.dryrun:
        for file in args:
            debug("mp3 file: %s", file)
            print "playlist for %s:" % file
            for part in provider.get_playlist(file, rule, False):
                print "\t%s" % part
        sys.exit(0)
    else:
        _change_user_group()
        for file in args:
            try:
                target = provider.create_combined(file, rule, splicer=engine)
            except:
                exception("error creating combined file for %s", file)
            else:
                debug('created %s', target)
    sys.exit(0)


class DeleteFinder(object):
    def __init__(self, files, basedir):
        self.files = files
        self.basedir = basedir
        self.targetdir = Config.targetdir
        if self.targetdir is None:
            self.targetdir = path.join(Config.basedir, 'combined')

    def _yielder(self, root, apath, isdir):
        targetpath = os.path.join(root, apath)
        mainpath = path.join(self.basedir,
                             path.relpath(targetpath, self.targetdir))

        debug('mainpath for %s is %s', apath, mainpath)
        if not os.path.exists(mainpath):
            yield targetpath, isdir

    def __iter__(self):
        for f in (path.join(self.targetdir, x) for x in self.files):
            if path.isdir(f):
                debug('found directory: %s', f)
                for root, dirs, files in os.walk(f, topdown=False):
                    for thing in files:
                        if thing.endswith('~'):
                            # looks like an ewa temp file.  Let it be.
                            continue
                        for res in self._yielder(root, thing, 0):
                            yield res
                    for thing in dirs:
                        for res in self._yielder(root, thing, 1):
                            yield res
                            

class RecursiveMp3FileIterator(object):
    def __init__(self, files, basedir):
        self.files = files
        self.basedir = basedir

    def __iter__(self):
        length = len(self.basedir)
        for f in (path.join(self.basedir, x) for x in self.files):
            if path.isdir(f):
                debug('found directory: %s', f)
                for mp3 in self._walk(f):
                    debug('raw value: %s', mp3)
                    yield mp3[length:]
            else:
                debug('found non-directory: %s', f)
                yield f[length:]

    def _walk(self, f):
        for root, dirs, files in os.walk(f):
            for f in files:
                if f.endswith('.mp3') or f.endswith('MP3'):
                    yield path.join(root, f)


class RecursiveChangedMp3FileIterator(RecursiveMp3FileIterator):

    def __init__(self, files, basedir, max_age=0):
        super(RecursiveChangedMp3FileIterator, self).__init__(files, basedir)
        self.targetdir = Config.targetdir
        if self.targetdir is None:
            self.targetdir = path.join(Config.basedir, 'combined')
        self.max_age = max_age

    def _walk(self, f):
        for root, dirs, files in os.walk(f):
            for f in files:
                if f.endswith('.mp3') or f.endswith('MP3'):
                    fullpath = path.join(root, f)
                    debug('fullpath is %s', fullpath)
                    debug('basedir: %s; targetdir: %s',
                          self.basedir, self.targetdir)
                    targetpath = os.path.join(self.targetdir,
                                              path.relpath(fullpath,
                                                           self.basedir))
                    try:
                        stats = os.stat(targetpath)
                    except OSError, ozzie:
                        if ozzie.errno == errno.ENOENT:
                            # target doesn't exist
                            debug("target doesn't exist: %s", targetpath)
                            yield fullpath
                        else:
                            exception("error statting targetfile")
                            # should we return this, or continue? ????
                    else:
                        # we know the file exists
                        target_mtime = stats.st_mtime
                        try:
                            original_mtime = path.getmtime(fullpath)
                        except OSError:
                            exception('peculiar error getting mtime of %s',
                                      fullpath)
                            continue

                        if original_mtime > target_mtime:
                            # if original file has changed, we need to
                            # regenerate regardless
                            yield fullpath
                        elif self.max_age <= 0:
                            # max_age of zero or less means we never
                            # regenerate the files
                            continue
                        else:
                            # regenerate if the file is older than
                            # max_age minutes
                            mtime = stats.st_mtime
                            age = time.time() - mtime
                            if age > self.max_age * 60:
                                yield fullpath


def _find_config(givenpath):
    for pth in (p for p in (
        givenpath,
        path.expanduser('~/.ewa.conf'),
        path.expanduser('~/.ewa/ewa.conf'),
        '/etc/ewa.conf',
        '/etc/ewa/ewa.conf',
        ) if p):
        if path.exists(pth):
            return pth


def do_serve(args):
    parser = get_serve_parser()
    opts, args = parser.parse_args(args)
    if opts.version:
        print VERSION_TEXT % path.basename(sys.argv[0])
        sys.exit(0)
    configfile = _find_config(opts.configfile)
    if not configfile:
        parser.error('no config file specified or found in the usual places')
    if not path.exists(configfile):
        parser.error("config file does not exist: %s" % configfile)
    initConfig(configfile)
    if opts.nodaemonize:
        Config.daemonize = False

    if not Config.rulefile:
        parser.error("a rulefile needs to be specified")
    rule = FileRule(Config.rulefile)
    if Config.logfile:
        initLogging(level=Config.loglevel,
                    filename=Config.logfile,
                    rotate=Config.logrotate)
    # check for incompatible options
    if Config.protocol == 'http' and Config.unixsocket:
        parser.error('unix sockets not supported for http server')
    if Config.umask and not Config.unixsocket:
        parser.error('umask only applicable for unix sockets')
    if Config.unixsocket and (Config.interface or Config.port):
        parser.error('incompatible mixture of unix socket and tcp options')
    engine = resolve_engine(Config.engine)

    app = EwaApp(rule=rule,
                 basedir=Config.basedir,
                 targetdir=Config.targetdir,
                 stream=Config.stream,
                 refresh_rate=Config.refresh_rate,
                 use_xsendfile=Config.use_xsendfile,
                 sendfile_header=Config.sendfile_header,
                 content_disposition=Config.content_disposition,
                 splicer=engine)

    if opts.lighttpd_hack:
        app = LighttpdHackMiddleware(app)

    if Config.protocol == 'http':
        runner = partial(httpserver.serve,
                         app,
                         Config.interface,
                         Config.port)
    else:
        if Config.interface:
            bindAddress = (Config.interface, Config.port)
            debug('bindAddress: %s', bindAddress)
        elif Config.unixsocket:
            bindAddress = Config.unixsocket
        if Config.protocol == 'scgi':
            if Config.use_threads:
                serverclass = SCGIThreadServer
            else:
                serverclass = SCGIServer
        elif Config.protocol == 'fcgi':
            if Config.use_threads:
                serverclass = FCGIThreadServer
            else:
                serverclass = FCGIServer
        if Config.protocol in ('fcgi', 'scgi'):
            if Config.use_threads:
                kw = dict(maxSpare=Config.max_spare,
                          minSpare=Config.min_spare,
                          maxThreads=Config.max_threads)
            else:
                kw = dict(maxSpare=Config.max_spare,
                          minSpare=Config.min_spare,
                          maxChildren=Config.max_children,
                          maxRequests=Config.max_requests)
            # clean out Nones
            kw = dict(i for i in kw.items() if not i[1] is None)
        else:
            kw = {}

        runner = serverclass(app,
                             bindAddress=bindAddress,
                             umask=Config.umask,
                             **kw).run

    try:
        run_server(runner,
                   Config.pidfile,
                   Config.daemonize)
    except SystemExit:
        raise
    except:
        exception('exception caught')
        sys.exit(1)
    else:
        sys.exit(0)


def _change_user_group():
    if not have_unix:
        # maybe do something else on Windows someday...
        return

    user = Config.user
    group = Config.group
    if user or group:
        # in case we are seteuid something else, which would
        # cause setuid or getuid to fail, undo any existing
        # seteuid. (The only reason to do this is for the case
        # os.getuid()==0, AFAIK).
        try:
            seteuid = os.seteuid
        except AttributeError:
            # the OS may not support seteuid, in which
            # case everything is hotsy-totsy.
            pass
        else:
            seteuid(os.getuid())
        if group:
            gid = grp.getgrnam(group)[2]
            os.setgid(gid)
        if user:
            uid = pwd.getpwnam(user)[2]
            os.setuid(uid)


def run_server(func, pidfile=None, daemonize=True):
    debug("daemonize: %s, pidfile: %s", daemonize, pidfile)
    if daemonize:
        try:
            os.fork
        except NameError:
            info("not daemonizing, as the fork() call is not available")
            daemonize = False
    if daemonize:
        if os.fork():
            os._exit(0)
        if os.fork():
            os._exit(0)
        os.setsid()
        os.chdir('/')
        os.umask(0)
        os.open(os.devnull, os.O_RDWR)
        os.dup2(0, 1)
        os.dup2(0, 2)
        if pidfile:
            pidfp = open(pidfile, 'w')
            pidfp.write('%s' % os.getpid())
            pidfp.close()

    try:
        _change_user_group()
        try:
            func()
        except KeyboardInterrupt:
            pass
    finally:
        if daemonize and pidfile:
            try:
                os.unlink(pidfile)
            except OSError, e:
                # if it doesn't exist, that's OK
                if e.errno != errno.ENOENT:
                    warn("problem unlinking pid file %s", pidfile)
