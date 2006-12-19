import tempfile

import ewa.rules


def test_filerule1():
    tmp=tempfile.NamedTemporaryFile(suffix='.py')
    filename=tmp.name
    s='\n'.join(['import ewa.rules as R',
               'rules=R.DefaultRule()',
               ''])
    tmp.write(s)
    tmp.flush()
    fr=ewa.rules.FileRule(filename)
    orig='blather.mp3'
    assert list(fr(orig))==[orig]
    
