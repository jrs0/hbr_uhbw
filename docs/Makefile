HASH=$(shell git rev-parse --short HEAD)
DATE=$(shell date +%d-%m-%Y)
FILENAME_DATE=$(shell date +%d_%m_%Y)

.PHONY: word_doc
word_doc: word_doc.html
	pandoc --toc \
	       --lua-filter=highlight_mark.lua \
	       --number-sections \
	       --number-offset=1 \
	       --metadata title="Bleeding/Ischaemia Risk Prediction Tool" \
	       --metadata subtitle="Notes (git checkout $(HASH))" \
	       --metadata author="John Scott and Maredudd Harris" \
	       --metadata date="$(DATE)"\
	       -o bhf_hbr_notes_$(FILENAME_DATE).docx $^

.PHONY: pdf
pdf: main.adoc	
	asciidoctor-pdf -r asciidoctor-bibtex $< -o bhf_hbr_notes_$(FILENAME_DATE).pdf

word_doc.html: word_doc.adoc *.adoc
	asciidoctor -r asciidoctor-bibtex $<

.PHONY: clean
clean:
	rm -rf *.html *.docx *.pdf

