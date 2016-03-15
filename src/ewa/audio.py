"""

This module is responsible for managing audio files:

  * managing the main (content) audio files, located in
    <audioroot>/main/path/to/audiofile
  * managing extra audio files, located in
    <audioroot/extra, in two subdirectories,
    <audioroot/extra/masters and <audioroot/extra/transcoded.
  * resolving audiofile symbolic names to files within
    the managed hierarchy.
  * creating combined (spliced) files according to rules passed
    in.

"""
import os
import thread

from eyed3.mp3 import Mp3Exception
from eyed3.id3.tag import TagException

from ewa.mp3 import get_vbr_bitrate_samplerate_mode, splice
from ewa.transcode import transcode
from ewa.logutil import warn
from ewa.rules import DefaultRule

path_join = os.path.join
path_exists = os.path.exists
getmtime = os.path.getmtime


def is_original(s):
    return getattr(s, 'is_original', False)


class AudioProviderException(RuntimeError):
    pass


class FileNotFound(AudioProviderException):
    pass


class BaseAudioProvider(object):
    def __init__(self,
                 basedir,
                 tolerate_vbr=True,
                 tolerate_broken=True):
        self.basedir = os.path.normpath(os.path.abspath(basedir))
        self.tolerate_vbr = tolerate_vbr
        self.tolerate_broken = tolerate_broken

    def get_main_path(self, audioname):
        return path_join(self.basedir,
                         'main',
                         audioname)

    def get_extra_master_path(self,
                              audioname):
        p = path_join(self.basedir,
                      'extra',
                      'master',
                      audioname)
        if path_exists(p):
            return p
        raise FileNotFound(p)

    def get_extra_transcoded_path(self,
                                  audioname,
                                  mode,
                                  bitrate,
                                  samplerate,
                                  create=False):
        path = path_join(self.basedir,
                         'extra',
                         'transcoded',
                         str(bitrate),
                         str(samplerate),
                         mode,
                         audioname)
        if not path.endswith('.mp3') or path.endswith('.MP3'):
            path += '.mp3'
        if create:
            orig_path = self.get_extra_master_path(audioname)
            if path_exists(path):
                trans_mtime = getmtime(path)
                orig_mtime = getmtime(orig_path)
                if orig_mtime <= trans_mtime:
                    # no transcoding necessary, return
                    return path
            # either transcoded file is out of date
            # or it doesn't exist, transcode
            transcode(orig_path, path, bitrate, samplerate, mode)
        return path

    def get_playlist(self, audioname, rule, create=True):
        symbols = list(rule(audioname))
        if not symbols:
            return symbols
        audiopath = self.get_main_path(audioname)
        try:
            (isvbr, bitrate,
             samplerate, mode) = get_vbr_bitrate_samplerate_mode(audiopath)
        except (Mp3Exception, TagException), exc:
            if self.tolerate_broken:
                warn('got %s for %s', exc, audiopath)
                # no splicing, return default rule
                symbols = list(DefaultRule()(audioname))
                isvbr = bitrate = samplerate = mode = None
            else:
                raise exc
        else:
            if isvbr:
                warn("file is vbr: %s", audiopath)
                if not self.tolerate_vbr:
                    raise AudioProviderException("vbr not supported: %s" \
                                                 % audiopath)
                else:
                    # just return the default rule for vbr
                    symbols = list(DefaultRule()(audioname))

        def resolve(x):
            if is_original(x):
                path = self.get_main_path(x)
                if create and not path_exists(path):
                    raise FileNotFound(path)
                return path
            else:
                try:
                    return self.get_extra_transcoded_path(x,
                                                          mode,
                                                          bitrate,
                                                          samplerate,
                                                          create)
                except FileNotFound:
                    warn("extra audio not found: %s", x)
                    return None

        return [y for y in (resolve(x) for x in symbols) if y]


class FSAudioProvider(BaseAudioProvider):

    def __init__(self, basedir, tolerate_vbr=True,
                 tolerate_broken=True, targetdir=None):
        super(FSAudioProvider, self).__init__(basedir,
                                              tolerate_vbr,
                                              tolerate_broken)
        if targetdir is None:
            targetdir = path_join(basedir, 'combined')
        self.targetdir = os.path.abspath(targetdir)

    def get_combined_path(self, audioname):
        return path_join(self.targetdir, audioname)

    def create_combined(self, audioname, rule, **spliceKwargs):
        if audioname.startswith('/'):
            audioname = audioname[1:]
        mainpath = self.get_main_path(audioname)
        playlist = self.get_playlist(audioname, rule)
        target = self.get_combined_path(audioname)
        parent = os.path.dirname(target)
        if not path_exists(parent):
            os.makedirs(parent)
        renamed = '%s%d~%d~' % (target,
                                os.getpid(),
                                thread.get_ident())
        fp = open(renamed, 'wb')
        for chunk in splice(playlist, mainpath, **spliceKwargs):
            fp.write(chunk)
        fp.close()
        os.rename(renamed, target)
        return target


class StreamAudioProvider(BaseAudioProvider):

    def create_combined(self, audioname, rule, **spliceKwargs):
        if audioname.startswith('/'):
            audioname = audioname[1:]
        mainpath = self.get_main_path(audioname)
        playlist = self.get_playlist(audioname, rule)
        return splice(playlist, mainpath, **spliceKwargs)


__all__ = ['AudioProviderException',
           'FileNotFound',
           'FSAudioProvider',
           'StreamAudioProvider']
