HASH=$(shell git rev-parse --short HEAD)
DATE=$(shell date +%d-%m-%Y)

bhf_hbr_notes.docx: all.html
	pandoc --toc \
		   --lua-filter=highlight_mark.lua \
	       --number-sections \
		   --number-offset=1 \
	       --metadata title="Bleeding/Ischaemia Risk Prediction Tool" \
	       --metadata subtitle="Notes (git checkout $(HASH))" \
	       --metadata author="John Scott and Maredudd Harris" \
	       --metadata date="$(DATE)"\
	       -o $@ $^

all.html: all.adoc
	asciidoctor all.adoc
