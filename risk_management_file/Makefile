HASH=$(shell git rev-parse --short HEAD)
DATE=$(shell date +%d-%m-%Y)
FILENAME_DATE=$(shell date +%d_%m_%Y)
BUILD=build/

# Run `make docx` to build the word document
.PHONY: docx
docx: $(BUILD)/bhf_hbr_notes.docx

# Run `make pdf` to build the PDF document
.PHONY: pdf
pdf: $(BUILD)/bhf_hbr_notes.pdf

$(BUILD)/bhf_hbr_notes.docx: $(BUILD)/word_doc_intermediate.html
	pandoc --toc \
	       --lua-filter=highlight_mark.lua \
	       --number-sections \
	       --number-offset=1 \
	       --metadata title="Bleeding/Ischaemia Risk Prediction Tool" \
	       --metadata subtitle="Notes (git checkout $(HASH))" \
	       --metadata author="John Scott and Maredudd Harris" \
	       --metadata date="$(DATE)"\
	       -o $@ $^

$(BUILD)/bhf_hbr_notes.pdf: main.adoc *.adoc
	asciidoctor-pdf --trace -r asciidoctor-bibtex $< -o $@

$(BUILD)/word_doc_intermediate.html: word_doc.adoc *.adoc
	asciidoctor -r asciidoctor-diagram $< -o $@

.PHONY: clean
clean:
	rm -rf $(BUILD)

$(BUILD):
	mkdir -p $(BUILD)
