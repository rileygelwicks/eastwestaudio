"""
A parser for the rule configuration format.

see doc/rule_grammar.rst for documentation.

"""
import datetime
import logging
import os
import re
import sys

# developer feature
PARSEDEBUG=os.environ.get('PARSEDEBUG', False)

from pkg_resources import resource_filename    
from ewa.ply import lex, yacc

from ewa.logutil import logger, critical, error, debug
import ewa.rules as rules


class ParseError(RuntimeError):
    pass

class RuleParser(object):

    def t_error(self, t):
        raise ParseError('lexical error, line %d: %s' \
                         % (t.lexer.lineno, t.value))

    # Define a rule so we can track line numbers
    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    def t_QREGEX(self, t):
        r'regex:(?:\'(?:[^\']|\\\')*\'|"(?:[^"]|\\")*")'  
        q=t.value[7]
        t.value=t.value[7:-1].replace('\\'+q,q)
        return t
        
    def t_BAREREGEX(self, t):
        r'regex:[^ ,:]+'
        t.value=t.value[6:].replace(
            '\ ', ' ').replace(
            '\,', ',').replace(
            '\:', ':')
        return t

    def t_DATE(self, t):
        r'(?P<month>0[1-9]|1[012])(?P<sep>-|/|\.)(?P<day>0[1-9]|[12]\d|3[01])(?P=sep)(?P<year>\d{4})'
        d=t.lexer.lexmatch.groupdict()
        kw=dict((k,int(d[k])) for k in ('month', 'day', 'year'))
        try:
            t.value=datetime.date(**kw)
        except ValueError:
            critical("invalid date: %s", t.value)
            raise
        return t

    def t_DATETIME(self, t):
        r'(?P<month>0[1-9]|1[012])(?P<sep>-|/|\.)(?P<day>0[1-9]|[12]\d|3[01])(?P=sep)(?P<year>\d{4})(?: |(?P=sep))(?P<hour>[01][0-9]|2[0-3])(?P<minute>[0-5]{2})'
        d=t.lexer.lexmatch.groupdict()
        kw=dict((k,int(d[k])) for k in ('month', 'day', 'year', 'hour', 'minute'))
        for k in ('hour', 'minute'):
            if kw[k]==None:
                kw[k]=0
        # normalize to 0
        kw['microsecond']=0
        try:
            t.value=datetime.datetime(**kw)
        except ValueError:
            critical("invalid datetime: %s", t.value)
            raise
        return t    
    
    def t_BAREWORD(self, t):
        r'[\w\d/\*\\\?_\.]+'
        if t.value in self.reserved:
            t.type=t.value.upper()
            return t
        return t

    def t_QWORD(self, t):
        r'\'(?:[^\']|\\\')*\'|"(?:[^"]|\\")*"'  
        q=t.value[0]
        t.value=t.value[1:-1].replace('\\'+q, q)
        return t


    reserved=('default',
              'pre',
              'post',
              'and',
              'or',
              'not')
              
    def t_COMMENT(self, t):
        '\#.*'
        pass

    tokens=('OP',
            'BAREWORD',
            'QWORD',
            'BAREREGEX',
            'QREGEX',
            'DATE',
            'DATETIME',
            'DEFAULT',
            'PRE',
            'POST',
            'AND',
            'OR',
            'NOT',
            'LPAREN',
            'RPAREN',
            'LBRACK',
            'RBRACK',
            'COLON',
            'COMMA',
            'DASH')

    t_LPAREN=r'\('

    t_RPAREN=r'\)'

    t_LBRACK=r'\['

    t_RBRACK=r'\]'

    t_COLON=':'

    t_COMMA=','

    t_DASH='-'

    t_OP='<=|>=|<|>|='

    t_ignore=' \t'

    def p_error(self, p):
        if not (p is None):
            raise ParseError("Syntax error at line %d: %s" % (p.lineno, p))
        else:
            raise ParseError("Syntax error: unexpected EOF")

    def p_grammar(self, p):
        'grammar : cond_rule_list'
        p[0]=rules.RuleList(p[1])

    def p_cond_rule_list(self, p):
        '''cond_rule_list : cond_rule
           | cond_rule COMMA cond_rule_list
           | cond_rule cond_rule_list'''
        plen=len(p)
        if plen==2:
            p[0]=[p[1]]
        elif plen==3:
            p[0]=[p[1]]+p[2]
        elif plen==4:
            p[0]=[p[1]]+p[3]
            
    def p_rulelist_1(self, p):
        'rulelist : LBRACK cond_rule_list RBRACK'
        p[0]=p[2]

    def p_rulelist_2(self, p):
        'rulelist : LBRACK RBRACK'
        p[0]=[]

    def p_cond_rule(self, p):
        '''cond_rule : cond COLON rule
           | rule'''
        if len(p)==2:
            p[0]=self._gen_rule(None, p[1])
        else:
            p[0]=self._gen_rule(p[1], p[3])

    def _gen_rule(self, cond, data):
        if isinstance(data, dict) and 'pre' in data:
            return rules.MatchRule(cond, data['pre'], data['post'])
        elif isinstance(data, list):
            # a rulelist
            return rules.RuleList(data, cond=cond)
        else:
            assert 0, 'not reached'

    def p_rule(self, p):
        '''rule : simplerule
        | rulelist'''
        p[0]=p[1]

    def p_simplerule_1(self, p):
        'simplerule : prelist COMMA postlist'
        p[0]=dict(pre=p[1], post=p[3])

    def p_simplerule_2(self, p):
        'simplerule : prelist postlist'
        p[0]=dict(pre=p[1], post=p[2])

    def p_simplerule_3(self, p):
        'simplerule : postlist COMMA prelist'
        p[0]=dict(pre=p[3], post=p[1])

    def p_simplerule_4(self, p):
        'simplerule : postlist prelist'
        p[0]=dict(pre=p[2], post=p[1])

    def p_simplerule_5(self, p):
        'simplerule : DEFAULT'
        p[0]=dict(pre=[], post=[])
    
    def p_prelist(self, p):
        'prelist : PRE COLON speclist'
        p[0]=p[3]
    
    def p_postlist(self, p):
        'postlist : POST COLON speclist'
        p[0]=p[3]
    
    def p_speclist_1(self, p):
        'speclist : LBRACK specifier_list RBRACK'
        p[0]=p[2]

    def p_speclist_2(self, p):
        'speclist : LBRACK RBRACK'
        p[0]=[]
    
    def p_specifier_list(self, p):
        '''specifier_list : specifier
           | specifier COMMA specifier_list'''
        if len(p)==2:
            p[0]=[p[1]]
        else:
            p[0]=[p[1]]+p[3]
    
    def p_specifier(self, p):
        'specifier : string'
        p[0]=p[1]

    def p_string(self, p):
        '''string : BAREWORD
         | QWORD'''
        p[0]=p[1]
    
    def p_cond(self, p):
        '''cond : cond_expr
        | simple_cond'''
        p[0]=p[1]

    def p_cond_expr_1(self, p):
        'cond_expr : cond_op LPAREN cond_list RPAREN'
        p[0]=p[1](*p[3])

    def p_cond_expr_2(self, p):
        'cond_expr : NOT LPAREN cond RPAREN'
        p[0]=rules.Not(p[3])
    
    def p_cond_list(self, p):
        '''cond_list : cond
        | cond COMMA cond_list'''
        if len(p)==2:
            p[0]=[p[1]]
        else:
            p[0]=[p[1]]+p[3]
    
    def p_cond_op(self, p):
        '''cond_op : AND
        | OR'''

        t=p[1]
        if t=='and':
            p[0]=rules.And
        elif t=='or':
            p[0]=rules.Or

        
    def p_simple_cond(self, p):
        '''simple_cond : regex
        | glob
        | datespec'''
        p[0]=p[1]
    
    def p_regex_1(self, p):
        '''regex : BAREREGEX
           | QREGEX'''
        p[0]=rules.RegexMatcher(p[1])

    def p_regex_2(self, p):
        '''regex : BAREREGEX condopts
           | QREGEX condopts'''
        # supported flags: I, L, U
        flags, nothing=p[2]
        if nothing:
            raise ParseError("illegal options for regex: %s" % p)
        validopts=dict(I=re.I, U=re.U, L=re.L)
        diff=set(flags).difference(validopts)
        if diff:
            raise ParseError("illegal options for regex: %s" % ','.join(list(diff)))
        flags=reduce(lambda x, y: x | y,
                     [validopts[k] for k in flags])
        p[0]=rules.RegexMatcher(p[1], flags)
    
    def p_glob_1(self, p):
        'glob : string'
        p[0]=rules.GlobMatcher(p[1])

    def p_glob_2(self, p):
        'glob : string condopts'
        # TO BE DONE
        p[0]=rules.GlobMatcher(p[1])

    def _expand_datefmt(self, fmt):
        d=dict(YYYY=('%Y', '\d{4}'),
               YY=('%y', '\d\d'),
               MM=('%m', '\d\d'),
               DD=('%d', '\d\d'),
               HH=('%H', '\d\d'),
               mm=('%M', '\d\d'),
               PM=('%p', '(?:AM|PM)'),
               hh=('%I', '\d\d'))
        buff=fmt
        regex=[]
        newfmt=[]
        keys=sorted(d, reverse=True)
        while buff:
            for k in keys:
                if buff.startswith(k):
                    buff=buff[len(k):]
                    v=d[k]
                    newfmt.append(v[0])
                    regex.append(v[1])
                    break
            else:
                newfmt.append(buff[0])
                regex.append(buff[0])
                buff=buff[1:]
                
            if not buff:
                break
            
        return (''.join(regex),
                ''.join(newfmt))

    def _gen_datematcher(self, start, end, opts, lineno):
        posopts, keyedopts=opts
        if posopts:
            supported_pos=['F', 'T']
            spos=set(posopts)
            diff=spos.difference(supported_pos)
            if diff:
                raise ParseError(
                    'unsupported condition options on line %d: %s' \
                    %s (lineno, ', '.join(list(diff))))
            lpos=len(posopts)
            if lpos>len(spos):
                raise ParseError(
                    'duplicate option on line %s: %s' \
                    % (lineno, ', '.join(posopts)))
            if lpos>=2:
                raise ParseError(
                    'incompatible options on line %d: %s' \
                    % (lineno, ', '.join(posopts)))
        if posopts and posopts[0]=='F':
            supported_keys=['fmt']
            diff=set(keyedopts).difference(supported_keys)
            if diff:
                raise ParseError(
                    'unsupported options on line %d: %s' \
                    % (lineno, ', '.join(list(diff))))
            if keyedopts:
                fmt=keyedopts['fmt']
                regex, newfmt=self._expand_datefmt(fmt)
                return rules.FileTimeMatch(start, end, regex, newfmt)
            
        else:
            return rules.CurrentTimeMatch(start, end)

    def p_datespec_1(self, p):
        '''datespec : datetime DASH datetime
           | date DASH date
           | datetime DASH date
           | date DASH datetime'''
        p[0]=rules.CurrentTimeMatch(_to_datetime(p[1]),
                                    _to_datetime(p[3]))
    def p_datespec_2(self, p):
        '''datespec : datetime DASH datetime condopts
           | date DASH date condopts
           | datetime DASH date condopts
           | date DASH datetime condopts'''
        p[0]=self._gen_datematcher(_to_datetime(p[1]),
                                   _to_datetime(p[3]),
                                   p[4],
                                   p.lineno)
                                                
    def p_datespec_3(self, p):
        '''datespec : datecompare datetime
           | datecompare date'''
        start, end=self._resolve_datecompare(p[1], p[2])
        p[0]=rules.CurrentTimeMatch(start, end)

    def p_datespec_4(self, p):
        '''datespec : datecompare datetime condopts
           | datecompare date condopts'''
        start, end=self._resolve_datecompare(p[1], p[2])
        p[0]=self._gen_datematcher(start, end, p[3], p.lineno)

    def p_condopts(self, p):
        '''condopts : LBRACK condopt_list RBRACK'''
        pos=[]
        keyed={}
        for opt in p[2]:
            if isinstance(opt, tuple):
                k,v=opt
                if k in keyed:
                    raise ParseError(
                        "duplicate option on line %d: %s" % (p.lineno, k))
                keyed[k]=v
            else:
                pos.append(opt)
        p[0]=(pos, keyed)

    def p_condopt_list(self, p):
        '''condopt_list : condopt
           | condopt COMMA condopt_list'''
        if len(p)==2:
            p[0]=[p[1]]
        else:
            p[0]=[p[1]]+p[3]

    def p_condopt_1(self, p):
        '''condopt : BAREWORD OP BAREWORD'''
        op=p[2]
        if op!='=':
            raise ParseError(
                "expected '=' in condition options on line %d, got %s" \
                % (p.lineno, op))
        p[0]=(p[1], p[3])
        

    def p_condopt_2(self, p):
        '''condopt : BAREWORD'''
        p[0]=p[1]
    
    def p_datecompare(self, p):
        'datecompare : OP'
        p[0]=p[1]
    
    def p_date(self, p):
        'date : DATE'
        p[0]=p[1]

    def p_datetime(self, p):
        'datetime : DATETIME'
        p[0]=p[1]

    def _resolve_datecompare(self, op, date):
        
        if op == '=':
            return (_to_datetime(date),
                    datetime.datetime(date.year,
                                      date.month,
                                      date.day,
                                      23,
                                      59,
                                      59))
            
        elif op == '<=':
            return (datetime.datetime.min,
                    _to_datetime(date))
            
        elif op == '>=':
            return (_to_datetime(date),
                    datetime.datetime.max)
        elif op == '<':
            return (datetime.datetime.min,
                    _to_datetime(date)-datetime.timedelta(microseconds=1))
        elif op == '>':
            return (_to_datetime(date)+datetime.timedelta(microseconds=1),
                    datetime.datetime.max)
        else:
            assert 0, "not reached"

def _to_datetime(dt):
    if isinstance(dt, datetime.date):
        return datetime.datetime(dt.year,
                                 dt.month,
                                 dt.day,
                                 0,
                                 0,
                                 0)
    return dt

def parse_string(s, debug=False):
    if debug:
        logger.setLevel(logging.DEBUG)
        logging.basicConfig(stream=sys.stderr)
    p=RuleParser()
    lexer=lex.lex(module=p)
    if PARSEDEBUG:
        yaccopts=dict(optimize=False,
                      debug=True,
                      tabmodule='_ruletab',
                      # directory of this module
                      outputdir=resource_filename('ewa.__init__', ''))
    else:
        yaccopts=dict(write_tables=False,
                      debug=False,
                      tabmodule='ewa._ruletab')
    parser=yacc.yacc(module=p,
                     **yaccopts)
    return parser.parse(s, lexer=lexer, debug=debug)

def parse_file(fp, debug=False):
    if not hasattr(fp, 'read'):
        fp=open(fp)
    return parse_string(fp.read(), debug=debug)

def lex_file(fp, debug=False):
    if not hasattr(fp, 'read'):
        fp=open(fp)
    return lex_string(fp.read(), debug)

def lex_string(s, debug=False):
    if debug:
        logger.setLevel(logging.DEBUG)
        logging.basicConfig(stream=sys.stderr)
    p=RuleParser()
    lexer=lex.lex(module=p)
    lexer.input(s)
    while 1:
        tok=lexer.token()
        if not tok:
            break
        print tok


if __name__=='__main__':
    args=sys.argv[1:]
    if len(args)==2:
        if args[0]=='-lex':
            lex_file(args[1], True)
            sys.exit(0)
        elif args[0]=='-parse':
            thing=parse_file(args[1], True)
            print rules.to_json(thing)
            sys.exit(0)

    prog=os.path.basename(sys.argv[0])
    print >> sys.stderr, 'usage: %s [-lex | -parse] file' % prog
    sys.exit(1)
            
