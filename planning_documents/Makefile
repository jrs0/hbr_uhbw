HASH=$(shell git rev-parse --short HEAD)
DATE=$(shell date +%d-%m-%Y)

planning_documents.pdf: $(wildcard [0-9][0-9]*.md)
	pandoc --toc \
	       --number-sections \
	       --metadata title="Bleeding/Ischaemia Risk Prediction Tool" \
	       --metadata subtitle="Planning Document (git checkout $(HASH))" \
	       --metadata author="John Scott and Maredudd Harris" \
	       --metadata date="$(DATE)"\
	       $^ -o $@
