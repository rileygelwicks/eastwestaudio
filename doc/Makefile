
rule_grammar.html: rule_grammar.rst
	rst2html.py rule_grammar.rst rule_grammar.html

ewa.man: ewa.pod
	pod2man --center="EWA (EastWestAudio)" --section=1 ewa.pod ewa.man

clean: 
	-rm ewa.man rule_grammar.html

.PHONY: clean

