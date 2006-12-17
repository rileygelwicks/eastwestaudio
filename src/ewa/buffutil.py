def buff_chunk_string(s, bsize):
    idx=0
    length=len(s)
    while idx < length:
        yield s[idx:bsize+idx]
        idx+=bsize

def buff_chunk_file(fp, end, bsize):
    idx=fp.tell()
    while 1:
        chunk=fp.read(min(bsize, end-idx))
        if chunk:
            idx+=len(chunk)
            yield chunk
        else:
            break

def buff_chunk_iterator(iterator, bsize):
    """
    this adapts an iterator that yields chunks of
    one size to one that yields chunks of another
    """
    buff=[]
    buffsize=0
    stopped=False
    while 1:
        while buffsize < bsize:
            try:
                chunkie=iterator.next()
            except StopIteration:
                stopped=True
                break
            else:
                buff.append(chunkie)
                buffsize+=len(chunkie)
        if stopped:
            if buffsize:
                yield ''.join(buff)
            raise StopIteration
        else:
            flattened=''.join(buff)
            while len(flattened) >=bsize:
                chunk=flattened[:bsize]
                flattened=flattened[bsize:]
                yield chunk
            buff=[flattened]
            buffsize=len(flattened)
