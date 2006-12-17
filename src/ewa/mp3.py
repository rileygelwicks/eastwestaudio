import os
from struct import unpack
import subprocess

import eyeD3

from ewa.logutil import debug
from ewa.frameinfo import get_frame
from ewa.buffutil import buff_chunk_string, buff_chunk_file

            
def _sox_splicer(files,
                 buffsize,
                 sox_path='/usr/bin/sox'):
    pipe=subprocess.Popen([sox_path, ]+ files + ['-t', 'mp3', '-'],
                          stdout=subprocess.PIPE)
    while 1:
        stuff=pipe.stdout.read(buffsize)
        if stuff=='':
            break
        yield stuff
    # and we mean wait
    pipe.wait()


def _mp3cat_splicer(files,
                    buffsize,
                    mp3cat_path="/usr/bin/mp3cat"):

    """
    splicing engine that uses Tom Clegg's mp3cat.
    """
    
    p1=subprocess.Popen(["cat"]+ files,
                        stdout=subprocess.PIPE)
    p2=subprocess.Popen([mp3cat_path, "-", "-"],
                        stdin=p1.stdout,
                        stdout=subprocess.PIPE)
    while 1:
        stuff=p2.stdout.read(buffsize)
        if stuff=='':
            break
        yield stuff

    p1.wait()
    p2.wait()

def _default_splicer(files, buffsize):
    for filename in files:
        fp=open(filename, 'rb')
        # discard tag
        tag=get_id3v2_tags(fp)
        endoffset, endtag=get_id3v1_offset_and_tag(filename, True)
        for chunk in buff_chunk_file(fp, endoffset, buffsize):
            yield chunk
        fp.close()


def mp3_sanity_check(files):
    """
    if all files are mp3 files and
    are of the same bitrate, samplerate, and mode,
    do nothing; otherwise raise an exception
    """
    if not files:
        return
    res=[]
    for f in files:
        res.append(get_vbr_bitrate_samplerate_mode(f))
    template=res[0]
    fields=['vbr', 'bitrate', 'samplerate', 'mode']
    for r in res[1:]:
        diffs=[r[x]==template[x] for x in range(4)]
        if False in diffs:
            msg="%s does not match; expected %s, got %s"
            idx=diffs.index(False)
            raise ValueError, msg % (fields[idx],
                                     template[idx],
                                     r[idx])
    
                                     
def splice(files,
           tagfile=None,
           buffsize=2**20,
           splicer=_default_splicer,
           **splicerKwargs):
    """ Returns an iterator that supplies the spliced data from the files listed
    in chunks not larger than buffsize.  ID3 v2 and v1 tags are supplied from
    the tagfile if provided.
    """

    if tagfile:
        fp=open(tagfile, 'rb')
        try:
            data=get_id3v2_tags(fp)
        finally:
            fp.close()
        
        if data:
            for chunk in buff_chunk_string(data, buffsize):
                yield chunk

    for chunk in splicer(files, buffsize, **splicerKwargs):
        yield chunk
        
    if tagfile:
        endoffset, tag=get_id3v1_offset_and_tag(tagfile)
        if tag:
            yield tag
        
def get_vbr_bitrate_samplerate_mode(path):
    """
    returns a 4-tuple: whether the file is VBR,
    the bitrate, the samplerate, and the mode.
    """
    af = eyeD3.Mp3AudioFile(path)
    return af.getBitRate() + (af.getSampleFreq(), af.header.mode[0].lower())

def calculate_id3v2_size(header):
    """
    precondition: header is a valid ID3v2 header.

    """
    id3, vmaj, vrev, flags, size = unpack('>3sBBB4s', header)
    s = [ord(c) & 127 for c in header[6:10]]
    size = (s[0] << 21) | (s[1] << 14) | (s[2] << 7) | s[3]
    # we are expanding the size to 10 bytes
    # if there is a footer.
    if flags & 8:
        size += 10
    else:
        debug("no footer found, flags is %s", flags)

    return size

def get_id3v2_tags(fp):
    """
    returns the id3v2 tag as a string.  fp is an open file; if there
    is no id3v2 tag the file is left at the same position as when it
    was found, otherwise it is left at the end of the tag.
    """
    idx=fp.tell()
    header=fp.read(10)
    if not header[:3]=='ID3':
        fp.seek(idx)
        return ''
    else:
        size=calculate_id3v2_size(header)
        tags=header + fp.read(size)
        # WORKAROUND for when the footer is not correctly detected
        idx=fp.tell()
        buff=fp.read(8192)
        fp.seek(idx)
        fr=get_frame(buff)
        nxfr=get_frame(buff[10:])

        if fr[0]==0 and nxfr[0]!=0:
            # we'll conclude that there was a footer
            debug("inferring a footer")
            tags+=fp.read(10)
        return tags

def get_id3v1_offset_and_tag(filename, correct_offset=False):
    size=os.path.getsize(filename)
    tagidx=size-128
    fp=open(filename, 'rb')
    try:
        fp.seek(tagidx)
        tag=fp.read(128)
        if tag[:3]=='TAG':
            if correct_offset:
                return _check_last_sync(fp, tagidx), tag
            else:
                return tagidx, tag
        if correct_offset:
            return _check_last_sync(fp, size), ''
        else:
            return size, ''
    finally:
        fp.close()


BUFFMAX=8192

def _check_last_sync(fp, idx):
    """
    search back to no more than BUFFMAX
    to find a valid sync frame, and return the
    end index of the valid part of the file
    """
    where=fp.tell()
    newidx=max(0, idx-BUFFMAX)
    buffsize=(idx-newidx)
    fp.seek(newidx)
    stuff=fp.read(buffsize)
    fp.seek(where)
    prevend=end=len(stuff)
    while end >= 0:
        end=stuff.rfind('\xff', 0, end)
        frlen, frver, frlayer=get_frame(stuff[end:])
        if frlen==0:
            # invalid, not a sync at all
            continue
        else:
            # real sync
            # do we have a full frame?
            if frlen == prevend-end:
                # perfect
                newidx=idx-(buffsize-prevend)
                #debug("valid frame ends at %d", newidx)
                return newidx
            else:
                #debug("frlen: %d, prevend-end: %d", frlen, prevend-end)
                # fragmentary frame, delete it
                #debug("invalid frame at %d", idx-(buffsize-end))
                prevend=end
                continue
            
    # if we get here, no sync frame was found
    debug(
        ('no valid sync frame found in %d bytes '
         'at end of file before any id3v1 tag; '
         'no cleanup attempted'),
        BUFFMAX)
    
    return idx


         
