import os
import subprocess

from ewa.logutil import debug, warn, exception
from ewa.mp3 import get_vbr_bitrate_samplerate_mode
from ewa.config import Config

class TranscodeError(RuntimeError): pass

def lameTranscode(newBitRate, 
                  newSampleRate, 
                  newMode, 
                  masterPath,
                  newPath,
                  quiet=True):
    """ Executes LAME to transcode a file to a new    
    bit rate, sample rate, and mode. """

##     # why is this here?
##     if newMode=='m':
##         newMode='f'

    args = [Config.lame_path,
            '--cbr',
            '-b',
            str(newBitRate),
            '-t',
            '--resample',
            '%0.2f' % (newSampleRate / 1000.0),
            '-m',
            newMode,
            masterPath,
            newPath]
    
    if quiet:
        args.insert(1, "--quiet")

    debug("lame transcode called with args: %s", args)

    res = subprocess.call(args)
    if res != 0:
        raise TranscodeError("LAME transcoder exploded, return code %d" % res)

def transcode(masterPath, 
              newPath, 
              newBitRate,
              newSampleRate, 
              newMode, 
              allow_master=False,
              transcodeFunc=lameTranscode,
              **transcodeKwargs):
    """
    transcodes master file at masterPath to specified bitrate,
    samplerate, and mode using transcodeFunc, by default one using
    LAME, to perform the transcoding.  Returns either masterPath or
    newPath, depending on if the master path or new path should be
    used after possible transcoding.
    """
    # is this an mp3?
    if masterPath.endswith('.mp3') or masterPath.endswith('.MP3'):
        vbr, bitrate, samplerate, mode = get_vbr_bitrate_samplerate_mode(masterPath)
        if vbr:
            warn("master mp3 %s is VBR", masterPath)

        if (allow_master and bitrate==newBitRate and samplerate==newSampleRate and mode==newMode):
            # no need to transcode
            return masterPath
        
    dirNewPath = os.path.dirname(newPath)
    if not os.path.exists(dirNewPath):
        os.makedirs(dirNewPath)

    debug('transcoding %s to %s', masterPath, newPath)
    
    transcodeFunc(newBitRate,
                  newSampleRate,
                  newMode,
                  masterPath,
                  newPath,
                  **transcodeKwargs)
    return newPath


__all__ = ['transcode',  'lameTranscode']
