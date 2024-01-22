HASH=$(shell git rev-parse --short HEAD)
DATE=$(shell date +%d-%m-%Y)
FILENAME_DATE=$(shell date +%d_%m_%Y)

bhf_hbr_notes_$(FILENAME_DATE).docx: all.html
	pandoc --toc \
		   --lua-filter=highlight_mark.lua \
	       --number-sections \
		   --number-offset=1 \
	       --metadata title="Bleeding/Ischaemia Risk Prediction Tool" \
	       --metadata subtitle="Notes (git checkout $(HASH))" \
	       --metadata author="John Scott and Maredudd Harris" \
	       --metadata date="$(DATE)"\
	       -o $@ $^

all.html: all.adoc *.adoc
	asciidoctor $<
