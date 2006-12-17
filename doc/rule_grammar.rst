===================================
 The EWA Rule Configuration Format
===================================

:Author: Jacob Smullyan <jsmullyan@wnyc.org>

.. contents::
..
    1  Introduction
    2  Format Description
    3  Formal Grammar Specification
      3.1  Normative EBNF
      3.2  Implemented BNF
      3.3  Lexical Details
        3.3.1  Significant Tokens
        3.3.2  Ignored Tokens
    4  Complete Example

Introduction
============

Ewa's rule configuration format is designed to make it easy to define
a list of rules that say, for a given mp3 file, what files ewa should
combine to make an aggregate file, and in what order.  The rules are
consulted in order, and checked to see if they match the input mp3
file; the first one that matches returns a list of files to combine,
and those are then combined.

This format is not the only way of setting file combination rules for
ewa.  Rules can also be defined in Python, which permits the rule
system to be extended or even replaced.  This format supports the core
rule feature set only.


Format Description
==================

A rule is normally written in the form::

  condition [options]: 
     pre:  [file1,file2...] 
     post: [file1,file2...]

where a condition is a glob pattern, a regex pattern, or a date
specification, or combinations of the above with with the logical
operators ``and``, ``or``, and ``not``.  The ``pre`` and ``post``
lists indicate what files should go before or after the main content
file in the aggregate file ewa produces.  Condition options are put in
brackets after the condition and separated by commas; they can either
be a single symbol, such as ``F`` or ``I``, or a name-value pair,
separated by ``=``.  For example::

  bigband*.mp3 [I]: 
    pre: [bigbandintro]
    post: [bigbandoutro]
  regex:schwartz.*:
    pre: []
    post: []
  and(09/01/2006 - 11/01/2006 [F,fmt=YYYYMMDD], 
      or(lopate/*, bl/*):
    pre: []
    post: [specialoutro]

The regular expression follows Python regular expression rules.   If you want a
regex to ignore case, you can pass the ``I`` option.  Two other regex
options are supported: ``U`` (unicode) and ``L`` (locale).  These
correspond to the same options in the Python ``re`` module.  For more
information, see the `official Python documentation 
<http://www.python.org/doc/current/lib/module-re.html>`_.

Globs support only one option: ``I``.  By default, globs are
case-sensitive, but if this option is passed they will ignore case.

Both globs and regexes can contain arbitary characters if they are
delimited with either single or double quotation marks.  They can also
be written without quotation marks, with some restrictions.  Spaces
are not permitted for either; for regexes, colons and commas must be
escaped with a preceding backslash. Unquoted globs are furthermore
restricted to alphanumeric characters, forward slashes, asterisks,
question marks, underscores, and periods.  When in doubt, quote.

The date options are ``F``, ``T``, and the name-value option ``fmt``.
``F`` and ``T`` are incompatible.  ``T`` is the default (so its use is
actually not necessary except perhaps for readability); it means that
the condition will return true only if the current time matches
against the date range specified.

``F`` means that the date is matched against the filename using a
regular expression derived from a format (the ``fmt`` option); the
default format is ``MMDDYYYY``.  Formats may be specified with the
following symbols:

* MM (months)
* DD (days)
* YY (2-digit year)
* YYYY (4-digit year)
* HH (hours, 24 hour clock)
* mm (minutes)
* PM (AM or PM)
* hh (hours, 12 hour clock)

Any additional characters in the format become a literal part of the
regular expression.  The ``fmt`` option has no meaning and may not be
used when matching against the current time.

If the pre and post lists are both empty, the special form ``default``
may be used.   Also, if a rule applies unconditionally, the condition
may be omitted.  Therefore, the following four forms are equivalent::

   *: pre: [], post: []
   *: default
   pre: [], post: []
   default

For regex rules, it is possible for the filenames in the pre and post
lists to backreference named groups in the matching regex::

   regex:^/shows/(?P<showname>[^/]+)/.*\.mp3: 
      pre:  [intro/$showname]
      post: [outro/generic]

(Because of implementation details in the underlying parsing library
(`PLY <http://www.dabeaz.com/ply/>`_), only named groups can be used.)

It is convenient under some circumstances to nest lists of rules, with
a conditional qualifier shared by all of them.  To do this, enclose
the nested list of rules in matching brackets::

   regex:shows/(?P<showname>[^/]+)/.*: [
       <=09-01-2005 [F]: default
       09-02-2005 - 10-14-2006 [F]: 
          pre: [intro/$showname]
          post: []
       >10-15-2006 [F]: 
          pre: [current]
          post: [current]
       ]


Formal Grammar Specification
============================

Normative EBNF
--------------

The below is an EBNF grammar for the rule configuration format::

 grammar 	:= cond_rule [','? cond_rule]*
 rulelist 	:= '[' cond_rule [','? cond_rule]* ']'
 cond_rule 	:= [cond ':']? rule
 rule 		:= simplerule | rulelist
 simplerule 	:= prelist ','? postlist | postlist ','? prelist | 'default'
 prelist	:= 'pre' ':' speclist 
 postlist	:= 'post' ':' speclist
 speclist	:= '[' [specifier [',' specifier]*]? ']'
 specifier	:= string
 string         := BAREWORD | QWORD
 cond		:= cond_expr | simple_cond 
 cond_expr	:= cond_op '(' cond [',' cond]+ ')'
 cond_expr	:= NOT '(' cond ')'
 cond_op	:= 'and' | 'or'
 simple_cond	:= regex | glob | datespec
 regex		:= BAREREGEX condopts? | QREGEX condopts?
 glob		:= string condopts?
 datespec       := daterange condopts?
 daterange	:= [date '-' date] | [ datecompare date ] | date
 datecompare	:= '<' | '<=' | '>' | '>=' | '='
 date           := DATE | DATETIME
 condopts       := '[' condopt [',' condopt]* ']'
 condopt        := BAREWORD | BAREWORD '=' BAREWORD
  

Implemented BNF
---------------

The above is actually implemented by the following less readable but
equivalent grammar in a BNF notation without quantifiers::

 grammar -> cond_rule_list
 cond_rule_list -> cond_rule
 cond_rule_list -> cond_rule COMMA cond_rule_list
 cond_rule_list -> cond_rule cond_rule_list
 rulelist -> LBRACK cond_rule_list RBRACK
 rulelist -> LBRACK RBRACK
 cond_rule -> cond COLON rule
 cond_rule -> rule
 rule -> simplerule
 rule -> rulelist
 simplerule -> prelist COMMA postlist
 simplerule -> prelist postlist
 simplerule -> postlist COMMA prelist
 simplerule -> postlist prelist
 simplerule -> DEFAULT
 prelist -> PRE COLON speclist
 postlist -> POST COLON speclist
 speclist -> LBRACK specifier_list RBRACK
 speclist -> LBRACK RBRACK
 specifier_list -> specifier
 specifier_list -> specifier COMMA specifier_list
 specifier -> string
 string -> BAREWORD
 string -> QWORD
 cond -> cond_expr
 cond -> simple_cond
 cond_expr -> cond_op LPAREN cond_list RPAREN
 cond_expr -> NOT LPAREN cond RPAREN
 cond_list -> cond
 cond_list -> cond COMMA cond_list
 cond_op -> AND
 cond_op -> OR
 simple_cond -> regex
 simple_cond -> glob
 simple_cond -> datespec
 regex -> BAREREGEX
 regex -> QREGEX
 regex -> BAREREGEX condopts
 regex -> QREGEX condopts
 glob -> string
 glob -> string condopts
 datespec -> datetime DASH datetime
 datespec -> date DASH date
 datespec -> datetime DASH date
 datespec -> date DASH datetime
 datespec -> datetime DASH datetime condopts
 datespec -> date DASH date condopts
 datespec -> datetime DASH date condopts
 datespec -> date DASH datetime condopts
 datespec -> datecompare datetime
 datespec -> datecompare date
 datespec -> datecompare datetime condopts
 datespec -> datecompare date condopts
 condopts -> LBRACK condopt_list RBRACK
 condopt_list -> condopt
 condopt_list -> condopt COMMA condopt_list
 condopt -> BAREWORD OP BAREWORD
 condopt -> BAREWORD
 datecompare -> OP
 date -> DATE
 datetime -> DATETIME

Lexical Details
---------------

Significant Tokens
~~~~~~~~~~~~~~~~~~

The tokens that the lexer must produce will be:

 BAREWORD
     an unquoted string with alphanumeric characters, asterisks,
     backslashes, question marks, underscores, or periods.
 QWORD
     a string delimited by single or double quotation marks.  Internal
     quotation marks of the same type used as the delimiter must be
     escaped.
 BAREREGEX
     a string that matches a regex; should start with ``regex:``,
     followed by an unquoted string with the same restrictions as
     BAREWORD above.
 QREGEX
     like a BAREREGEX, but the regex, after the ``regex:`` prefix, 
     is delimited by single or double quotation marks, and escaping
     (except of quotation marks) is not necessary.
 DATE
     MM-DD-YYYY format.  The separator can also be a slash (/) or a
     period (.), but the same separator must be used in both
     positions. 
 DATETIME
     MM-DD-YYYY HHMM format.  The separator can also be a slash or
     period, as with DATE, and the space before the hour can be either
     a space or the previously used separator.
 DEFAULT
    'default'
 PRE
    'pre'
 POST
    'post'
 AND
    'and'
 OR
    'or'
 OP
    '<', '<=', '>', '>=', '='
 DASH
    '-'
 COMMA
    ','
 COLON
    ':'
 LBRACK
    '['
 RBRACK
    ']'
 LPAREN
    '('
 RPAREN
    ')'

Ignored Tokens
~~~~~~~~~~~~~~

Any text on a line after a pound sign (#) is a comment and is ignored.
Whitespace, including line returns, is ignored between tokens.
Indentation may be freely used to clarify patterns.

Complete Example
================

.. include :: ../conf/rules.conf.sample
  :literal:

