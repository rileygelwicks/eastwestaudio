"""

A WSGI application that generates mp3s dynamically
according to a ruleset.


"""
import mimetypes
import os
import time

import eyeD3

import ewa.audio
from ewa.logutil import debug, info, error, exception

_codes={200:'200 OK',
        404:'404 Not Found',
        500:'500 Internal Server Error'}

GENERIC_SENDFILE_HEADER='X-Sendfile'

LIGHTTPD_SENDFILE_HEADER='X-LIGHTTPD-send-file'

MP3_MIMETYPE='audio/mpeg'

mimetypes.init()

def guess_mime(filename):
    mtype, extension=mimetypes.guess_type(filename)
    if mtype is None:
        return 'application/octet-stream'
    return mtype

class EwaApp(object):

    def __init__(self,
                 rule,
                 basedir,
                 targetdir=None,
                 stream=False,
                 refresh_rate=0,
                 use_xsendfile=True,
                 sendfile_header=GENERIC_SENDFILE_HEADER,
#                 index_directories=False,
                 content_disposition='',
                 **spliceKwargs):
        self.rule=rule
        self.stream=stream
        if stream and targetdir:
            raise ValueError, "in streaming mode but targetdir supplied"
        self.spliceKwargs=spliceKwargs
        self.refresh_rate=refresh_rate
        self.use_xsendfile=use_xsendfile
        self.sendfile_header=sendfile_header
#        self.index_directories=index_directories
        self.content_disposition=content_disposition
        if self.stream:
            self.provider=ewa.audio.StreamAudioProvider(basedir)
        else:
            self.provider=ewa.audio.FSAudioProvider(basedir,
                                                    targetdir)

    basedir=property(lambda x: x.provider.basedir)
    
    targetdir=property(lambda x: getattr(x.provider, 'basedir', None))

    def send(self, start_response, status, headers=None, iterable=None):
        codeline=_codes[status]
        if headers is None:
            headers=[('Content-Type', 'text/plain')]
        start_response(codeline, headers)
        if iterable is None:
            return [codeline[4:]]
        else:
            return iterable


    def _create_combined(self, mp3file):
        # strip leading '/'
        if mp3file.startswith('/'):
            mp3file=mp3file[1:]
        mainpath=self.provider.get_main_path(mp3file)
        # if this blows up, propagate
        maintime=os.path.getmtime(mainpath)
        if os.path.isdir(mainpath):
##             if self.index_directories:
##                 # implement this eventually.
##                 # probably the file-existence/directory
##                 # check should be moved to __call__
##                 pass
            raise OSError
        if self.stream:
            try:
                return self.provider.create_combined(mp3file,
                                                     self.rule,
                                                     **self.spliceKwargs), MP3_MIMETYPE
            except (ewa.audio.AudioProviderException, eyeD3.InvalidAudioFormatException):
                info("%s cannot be processed.  Serving statically", mainpath)
                return open(mainpath), guess_mime(mainpath)
        else:
            path=self.provider.get_combined_path(mp3file)
            try:
                mtime=os.path.getmtime(path)
            except OSError:
                exception("OSError in getting mod time")
                pass
            else:
                # if the main file modified?
                regen= maintime > mtime
                if not regen:
                    if self.refresh_rate==0:
                        debug("no refresh, returning target path")
                        return path, MP3_MIMETYPE
                    else:
                        t=time.time()
                        if t-mtime < self.refresh_rate:
                            debug("not necessary to refresh, returning target path")
                            return path, MP3_MIMETYPE

            # if we get here we regenerate
            debug("need to regenerate combined file")
            try:
                path2=self.provider.create_combined(mp3file,
                                                    self.rule,
                                                    **self.spliceKwargs)
            except (ewa.audio.AudioProviderException, eyeD3.InvalidAudioFormatException):
                info("%s cannot be processed.  Serving statically", mainpath)
                return mainpath, guess_mime(mainpath)
            # should be the same
            debug("path returned from provider: %s", path2)
            debug("our calculated path: %s", path)
            return path2, MP3_MIMETYPE
                    

    def __call__(self, environ, start_response):
        mp3file=environ['SCRIPT_NAME']+environ['PATH_INFO']
        info("mp3file: %s", mp3file)
        if not mp3file:
            return self.send(start_response, 404)
        try:
            result, mtype=self._create_combined(mp3file)
        except (OSError, IOError):
            exception("Error in looking for file %s", mp3file)
            return self.send(start_response, 404)
        except:
            error("error creating combined file")
            exception("internal server error")
            return self.send(start_response, 500)        
        else:
            return self.sendfile(result, start_response, mtype)

    def sendfile(self, result, start_response, mtype):
        headers=[('Content-Type', mtype)]
        if mtype==MP3_MIMETYPE and self.content_disposition:
            headers.append(('Content-Disposition', self.content_disposition))
        if self.use_xsendfile:
            length=os.path.getsize(result)
            headers.extend([(self.sendfile_header, result),
                            ('Content-Length', "%d" % length)])
            debug('headers are: %s', headers)
            return self.send(start_response,
                             200,
                             headers,
                             "OK")
        else:
            if not self.stream:
                result=open(result, 'rb')
            return self.send(start_response,
                             200,
                             headers,
                             result)
        

    
