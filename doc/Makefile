RST2HTML=/usr/bin/rst2html.py
RST2LATEX=/usr/bin/rst2latex.py
PDFLATEX=/usr/bin/pdflatex
HTMLSTYLESHEET=style.css
HTMLOPTS=-s --footnote-references=brackets


ewamanual.html: ewamanual.rst
	${RST2HTML} ${HTMLOPTS} --stylesheet=${HTMLSTYLESHEET} ewamanual.rst ewamanual.html

ewamanual.tex: ewamanual.rst
	${RST2LATEX} ewamanual.rst ewamanual.tex

ewamanual.pdf: ewamanual.tex
	${PDFLATEX} ewamanual.tex

clean: 
	-rm ewamanual.html ewamanual.tex ewamanual.pdf

.PHONY: clean

