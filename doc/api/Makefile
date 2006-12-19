EPYDOC=/usr/bin/epydoc

html:
	PYTHONPATH=../../src ${EPYDOC} -o html -n ewa -u http://code.wnyc.org/ewa/  ../../src/ewa/
clean:
	-rm -fR html

.PHONY: html clean