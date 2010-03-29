"""

a rule system for ewa, used to determine what files should appear
before or after a main mp3 file in a composite mp3.

Rules are callables that take a single "filename" parameter and return
None or a generator that yields mp3 filenames (or equivalent
designations) in sequence.

A RuleList is a rule with a list of subrules, optionally with a
condition (matched against the filename).  When the RuleList is
called, if the condition does not exist, or if it matches, each
subrule is called on the filename until one returns something, which
is the return value.

Rules can be marshalled to and from JSON, and from (but currently not
to) the ewa rule configuration format implemented in ewa.ruleparser.

"""


import datetime
import fnmatch
import os
import re
from string import Template
import time

try:
    import simplejson as json
except ImportError:
    import json

from ewa.logutil import warn

class _template(Template):
    idpattern='[_a-z0-9]+'

class OriginalName(str):
    is_original=True

def to_jsondata(obj):
    if isinstance(obj, datetime.date):
        return dict(year=obj.year, month=obj.month, day=obj.day)
    elif isinstance(obj, datetime.datetime):
        # tzinfo not supported
        return dict(year=obj.year,
                    month=obj.month,
                    day=obj.day,
                    hour=obj.hour,
                    minute=obj.minute,
                    second=obj.second,
                    microsecond=obj.microsecond)
    
    elif isinstance(obj, list):
        return [to_jsondata(x) for x in obj]
    elif isinstance(obj, tuple):
        return tuple(to_jsondata(x) for x in obj)
    try:
        return obj.to_jsondata()
    except AttributeError:
        return obj

class _jsonable(object):
    def to_jsondata(self):
        return dict((k, to_jsondata(v)) for k,v in self.__dict__.iteritems())

class RuleList(_jsonable):

    def __init__(self, rules, cond=None):
        self.rules=rules
        self.cond=cond

    def __call__(self, filename):
        if self.cond:
            m=self.cond.match(filename)
            if not m:
                return
        for r in self.rules:
            res=r(filename)
            if res:
                return res


class DefaultRule(_jsonable):
    """
    this may be useful as the last rule in a rule-list;
    it yields the filename passed and nothing else
    """
    def __call__(self, filename):
        yield OriginalName(filename)

class MatchRule(_jsonable):
    def __init__(self, matcher, pre=None, post=None):
        """
        the matcher is a callable with a "match" method.  pre and post
        and lists of things that go before and after the filename
        passed in.
        """
        self.matcher=matcher
        self.pre=pre or []
        self.post=post or []

    def _gen_list(self, filename, match):
        if hasattr(match, 'groupdict'):
            # is a regex match
            d=dict((str(i+1), v) for i, v in enumerate(match.groups()))
            d.update(match.groupdict())
            expand=lambda s: match.expand(_template(f).safe_substitute(d))
        else:
            expand=lambda s: s
            
        for f in self.pre:
            yield expand(f)

        yield OriginalName(filename)
        
        for f in self.post:
            yield expand(f)


    def _match(self, filename):
        if self.matcher is None:
            return True
        return self.matcher.match(filename)

    def __call__(self, filename):
        m=self._match(filename)
        if m:
            return self._gen_list(filename, m)

class And(_jsonable):
    def __init__(self, *submatchers):
      self.submatchers=submatchers

    def match(self, target):
        res=False
        for m in self.submatchers:
            res=m.match(target)
            if not res:
                return False
        return res

class Or(_jsonable):
    def __init__(self, *submatchers):
        self.submatchers=submatchers

    def match(self, target):
        for m in self.submatchers:
            res=m.match(target)
            if res:
                return res
        return False

class Not(_jsonable):
    def __init__(self, matcher):
        self.matcher=matcher
        
    def match(self, target):
        return not self.matcher.match(target)
            
class RegexMatcher(_jsonable):
    def __init__(self, regex, flags=0):
        self.regex=regex
        self.flags=flags
        
    def match(self, target):
        return re.match(self.regex, target, self.flags)
    
class GlobMatcher(_jsonable):
    def __init__(self, pattern, casesensitive=True):
        self.pattern=pattern
        self.casesensitive=casesensitive

    def match(self, target):
        if self.casesensitive:
            return fnmatch.fnmatchcase(target, self.pattern)
        else:
            return fnmatch.fnmatch(target, self.pattern)

def extract_datetime(target, regex=r'\d{6}', format='%m%d%y'):
    m=re.search(regex, target)
    if m:
        try:
            ttuple=time.strptime(m.group(), format)
        except ValueError:
            warn("error in time format: %s from %s", m.group(), target)
        else:
            return datetime.datetime(*ttuple[:6])
    return None

class CurrentTimeMatch(_jsonable):
    """
    returns true if the current time falls within a
    datetime range
    """

    def __init__(self,
                 start=datetime.datetime.min,
                 end=datetime.datetime.max):
        self.start=start
        self.end=end
        
    def match(self, target):
        return self.start <= datetime.datetime.now() <= self.end

    
    
class FileTimeMatch(_jsonable):
    """
    returns true if a date encoded in a string falls within
    a date range
    """
    def __init__(self,
                 start=datetime.datetime.min,
                 end=datetime.datetime.max,
                 dateregex=r'\d{6}',
                 dateformat='%m%d%y'):
        self.start=start
        self.end=end
        self.dateregex=dateregex
        self.dateformat=dateformat

    def match(self, target):
        date=extract_datetime(target, self.dateregex, self.dateformat)
        if not date:
            return False
        return self.start <= date <= self.end

def RegexRule(pattern, pre=None, post=None, flags=0):
    matcher=RegexMatcher(pattern, flags)
    return MatchRule(matcher, pre, post)

def GlobMatchRule(pattern, pre=None, post=None, casesensitive=True):
    matcher=GlobMatcher(pattern, casesensitive)
    return MatchRule(matcher, pre, post)

_json_registry=dict((x.__name__, x) for x in (datetime.date,
                                              datetime.datetime,
                                              RuleList,
                                              DefaultRule,
                                              MatchRule,
                                              And,
                                              Or,
                                              Not,
                                              RegexMatcher,
                                              GlobMatcher,
                                              CurrentTimeMatch,
                                              FileTimeMatch))

def from_jsondata(data):
    if isinstance(data, dict) and len(data)==1:
        key=data.keys()[0]
        if key in _json_registry:
            obj=_json_registry[key]
            kwargs=dict((str(k),from_jsondata(v)) for k,v in data[key].iteritems())
            return obj(**kwargs)

    if isinstance(data, list):
        return [from_jsondata(x) for x in data]
    return data
        

def from_json(json):
    data=json.loads(json)
    return from_jsondata(data)

def to_json(data):
    jd=to_jsondata(data)
    return json.dumps(jd)

# to avoid a circular dependency, this is a stand-in for
# ewa.ruleparser.parse_file for the first run, and is the real thing
# thereafter
def _parse_ewaconf(filename):
    global _parse_ewaconf
    from ewa.ruleparser import parse_file
    # replace ourself after the first run
    parse_ewaconf=parse_file
    return parse_file(filename)

class FileRule(object):
        
    def __init__(self, rulefile, refresh=15, format=None):
        self.rulefile=rulefile
        self._refresh=refresh
        if format is None:
            if rulefile.endswith('.json') or rulefile.endswith('.js'):
                format='json'
            elif rulefile.endswith('.py'):
                format='python'
            else:
                format='ewaconf'
        self.format=format
        self._load_rule()

    @staticmethod
    def _rules_from_python(pyfile):
        filename=os.path.abspath(pyfile)
        s=open(filename).read()
        codeobj=compile(s, filename, 'exec')
        env={}
        exec codeobj in {}, env
        # let a KeyError propagate
        return env['rules']

    def _load_rule(self, mtime=None, lastchecked=None):
        if mtime is None:
            mtime=os.path.getmtime(self.rulefile)
        if lastchecked is None:
            lastchecked=time.time()
        self._modified=mtime
        if self.format=='json':
            self._rule=from_json(open(self.rulefile).read())
        elif self.format=='python':
            self._rule=self._rules_from_python(self.rulefile)
        elif self.format=='ewaconf':
            self._rule=_parse_ewaconf(self.rulefile)
        else:
            raise ValueError, "unrecognized format: %s" % self.format
        self._lastchecked=lastchecked

    def _check(self):
        t=time.time()
        if (t-self._lastchecked) > self._refresh:
            m=os.path.getmtime(self.rulefile)
            if m > self._modified:
                self._load_rule(m,t)

    def __call__(self, filename):
        self._check()
        return self._rule(filename)

__all__=[
    'RuleList',
    'DefaultRule',
    'MatchRule',
    'And',
    'Or',
    'Not',
    'RegexMatcher',
    'GlobMatcher',
    'extract_datetime',
    'CurrentTimeMatch',
    'FileTimeMatch',
    'RegexRule',
    'GlobMatchRule',
    'from_json',
    'to_json',
    'FileRule'
    ]
