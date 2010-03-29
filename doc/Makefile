RST2HTML=/usr/bin/rst2html
RST2LATEX=/usr/bin/rst2latex
PDFLATEX=/usr/bin/pdflatex
HTMLSTYLESHEET=style.css
HTMLOPTS=-s --footnote-references=brackets
HELP2MAN=/usr/bin/help2man


ewamanual.html: ewamanual.rst
	${RST2HTML} ${HTMLOPTS} --stylesheet=${HTMLSTYLESHEET} ewamanual.rst ewamanual.html

ewamanual.tex: ewamanual.rst
	${RST2LATEX} ewamanual.rst ewamanual.tex

ewamanual.pdf: ewamanual.tex
	${PDFLATEX} ewamanual.tex

ewa.1: 
	PYTHONPATH=../src ${HELP2MAN} -N -s 1 ../bin/ewa -o ewa.1

ewabatch.1: 
	PYTHONPATH=../src ${HELP2MAN} -N -s 1 ../bin/ewabatch -o ewabatch.1

ewasplice.1: 
	PYTHONPATH=../src ${HELP2MAN} -N -s 1 ../bin/ewasplice -o ewasplice.1

man: ewa.1 ewabatch.1 ewasplice.1

all: ewamanual.html ewamanual.pdf man

cleanjunk:
	-rm ewamanual.{aux,log,out}

clean: cleanjunk
	-rm ewamanual.{html,tex,pdf} *.1

.PHONY: clean cleanjunk all man

