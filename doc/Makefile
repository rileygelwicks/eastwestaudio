RST2HTML=/usr/bin/rst2html.py
RST2LATEX=/usr/bin/rst2latex.py
PDFLATEX=/usr/bin/pdflatex
HTMLSTYLESHEET=style.css
HTMLOPTS=-s --footnote-references=brackets
FILENAME=manual



index.html: index.rst
	${RST2HTML} ${HTMLOPTS} --stylesheet=${HTMLSTYLESHEET} index.rst index.html

rule_grammar.html: rule_grammar.rst
	rst2html.py rule_grammar.rst rule_grammar.html

ewamanual.tex: index.rst
	${RST2LATEX} index.rst ewamanual.tex

ewamanual.pdf: ewamanual.tex
	${PDFLATEX} ewamanual.tex

ewa.man: ewa.pod
	pod2man --center="EWA (EastWestAudio)" --section=1 ewa.pod ewa.man

clean: 
	-rm ewa.man rule_grammar.html index.html

.PHONY: clean

