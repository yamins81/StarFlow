# Use pdflatex.
# Install 'pdftk' to split PDF files into two segments.
#
# Type "make" to produce todo.pdf 

TARGETS = todo

TEXFILES = $(wildcard *.tex)
PDFS = $(addsuffix .pdf,$(TARGETS))
BIBFILES = $(wildcard *.bib)

todo.pdf: *.tex
	pdflatex todo
	pdflatex todo

%.pdf: $(BIBFILES) $(TEXFILES)
	pdflatex $*.tex
	bibtex $*
	pdflatex $*.tex
	pdflatex $*.tex


spell:
	$(shell for i in $(TEXFILES); do ispell $(i); done)

missing:
	@echo "----------------------------------------------------------"
	@echo "Missing citations:"
	@echo "----------------------------------------------------------"
	@(grep Cit *.log | awk '{print $$4}' | sort | uniq; exit 0)
	@echo "----------------------------------------------------------"
	@echo "Missing references:"
	@echo "----------------------------------------------------------"
	@(grep Ref *.log ; exit 0)
	@echo "----------------------------------------------------------"
	@echo "Outstanding issues:"
	@echo "----------------------------------------------------------"
	@(grep XXXnote *.tex | grep -v newcommand | grep -v '^\%' ; exit 0)



FORCE:

