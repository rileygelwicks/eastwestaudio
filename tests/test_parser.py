import re

import ewa.ruleparser as R

def test_regex1():
    s="""
    regex:.*bingbong: pre:[ingopotty], post: []
    default
    """
    rules=R.parse_string(s)
    orig='/kimp/bingbong/foo'
    res=list(rules(orig))
    assert res==['ingopotty', orig]


def test_regex2():    
    s="""
    regex:.*bingbong [I]: pre:[ingopotty], post: []
    default
    """
    
    rules=R.parse_string(s)
    orig='/kimp/bINGbong/foo'
    res=list(rules(orig))
    assert res==['ingopotty', orig]

def test_qregex1():    
    s="""
    regex:".*bingbong" [I]: pre:[ingopotty], post: []
    default
    """
    rules=R.parse_string(s)
    orig='/kimp/bINGbong/foo'
    res=list(rules(orig))
    assert res==['ingopotty', orig]



def test_glob1():
    s="""
    *bingbong*: pre:[ingopotty], post: []
    default
    """
    rules=R.parse_string(s)
    orig='/kimp/bingbong/foo'
    res=list(rules(orig))
    assert res==['ingopotty', orig]


def test_glob2():
    s=r"""
    '*bing bong*' : pre:[ingopotty], post: []
    default
    """
    rules=R.parse_string(s)
    orig='/kimp/bing bong/foo'
    res=list(rules(orig))

    assert res==['ingopotty', orig]


def test_and1():
    s="""
    and(*bing*, *bong*): pre: [ingopotty], post: []
    default
    """
    rules=R.parse_string(s)
    orig='/kimp/bingbong/foo'
    res=list(rules(orig))
    assert res==['ingopotty', orig]
    
def test_or1():
    s="""
    or(*zing*, *bong*): pre: [ingopotty], post: []
    default
    """
    rules=R.parse_string(s)
    orig='/kimp/bingbong/foo'
    res=list(rules(orig))
    assert res==['ingopotty', orig]


def test_not1():
    s="""
    not(*zing*): pre: [ingopotty], post: []
    default
    """
    rules=R.parse_string(s)
    orig='/kimp/bingbong/foo'
    res=list(rules(orig))
    assert res==['ingopotty', orig]
    
def test_date1():
    s="""
    =12.01.2005 [F,fmt=YYMMDD]:
        pre: [pingpong]
        post: [blah]
    default
    """
    rules=R.parse_string(s)
    orig='/zinger051201pod.mp3'
    res=list(rules(orig))
    assert res==['pingpong', orig, 'blah']

def test_date2():
    s="""
    =12.01.2005 [F]:
        pre: [pingpong]
        post: [blah]
    default
    """
    rules=R.parse_string(s)
    orig='/zinger12012005pod.mp3'
    res=list(rules(orig))
    assert res==['pingpong', orig, 'blah']

    
def test_date3():
    s="""
    <=12.01.2005 [F]:
        pre: [pingpong]
        post: [blah]
    default
    """
    rules=R.parse_string(s)
    orig='/zinger12012005pod.mp3'
    res=list(rules(orig))
    assert res==['pingpong', orig, 'blah']

def test_date4():
    s="""
    >=12.01.2005:
        pre: [pingpong]
        post: [blah]
    default
    """
    rules=R.parse_string(s)
    orig='whatever.mp3'
    res=list(rules(orig))
    assert res==['pingpong', orig, 'blah']

def test_date5():
    s="""
    <12.01.2005:
        pre: [pingpong]
        post: [blah]
    default
    """
    rules=R.parse_string(s)
    orig='whatever.mp3'
    res=list(rules(orig))
    assert res==[orig]


def test_backreference1():
    s="""
    regex:(pingpong|nougat|follicle)\d{6}[a-z]?\.mp3:
        pre: ["\\1_intro.mp3"]
        post: []
    default
    """
    rules=R.parse_string(s)
    orig='nougat060605a.mp3'
    res=list(rules(orig))
    assert res==['nougat_intro.mp3', orig]

def test_backreference2():
    s="""
    regex:(?P<show>pingpong|nougat|follicle)\d{6}[a-z]?\.mp3:
        pre: ["\\g<show>_intro.mp3"]
        post: []
    default
    """
    rules=R.parse_string(s)
    orig='pingpong060605a.mp3'
    res=list(rules(orig))
    assert res==['pingpong_intro.mp3', orig]

def test_backreference3():
    s="""
    regex:(?P<show>pingpong|nougat|follicle)\d{6}[a-z]?\.mp3:
        pre: ["${show}_intro.mp3"]
        post: []
    default
    """
    rules=R.parse_string(s)
    orig='pingpong060605a.mp3'
    res=list(rules(orig))
    assert res==['pingpong_intro.mp3', orig]
    
def test_backreference4():
    s="""
    regex:(pingpong|nougat|follicle)\d{6}[a-z]?\.mp3:
        pre: ["${1}_intro.mp3"]
        post: []
    default
    """
    rules=R.parse_string(s)
    orig='nougat060605a.mp3'
    res=list(rules(orig))
    assert res==['nougat_intro.mp3', orig]

def test_backreference5():
    s="""
    and(>12-01-2001,
        regex:"(pingpong|nougat|follicle)\d{6}[a-z]?\.mp3"):
        pre: ["${1}_intro.mp3"]
        post: []
    default
    """
    rules=R.parse_string(s)
    orig='nougat060605a.mp3'
    res=list(rules(orig))
    assert res==['nougat_intro.mp3', orig]

# this one is subtle.  The match returned by "and" is the last
# thing matched; you can't use backreferences with "and" except
# on the last sub-condition.
def test_backreference6():
    s="""
    and(regex:"(pingpong|nougat|follicle)\d{6}[a-z]?\.mp3",
        >12-01-2001):
        pre: ["${1}_intro.mp3"]
        post: []
    default
    """
    rules=R.parse_string(s)
    orig='nougat060605a.mp3'
    res=list(rules(orig))
    assert res==['${1}_intro.mp3', orig]
        
