.PHONY: help system_requirements gloss gen_csv_diffs gen_latex gen_latex compile_doc clean

STUBS = Supp Quality Approach
GLOSSARIES = $(addsuffix Glossary, $(STUBS))
CSV_GLOSSARIES = $(addsuffix .csv, $(GLOSSARIES))
TXT_GLOSSARIES = $(addsuffix .txt, $(GLOSSARIES))
DIFF_GLOSSARIES = $(addprefix Diff, $(TXT_GLOSSARIES))

GRAPHS = assets/graphs/*.tex assets/graphs/manual/*.tex
CUSTOM_STUBS = recovery scalability performance
ALL_CUSTOM_STUBS = $(CUSTOM_STUBS) $(addsuffix Proposed, $(CUSTOM_STUBS))
CUSTOM_GRAPHS = $(addprefix assets/graphs/, $(addsuffix Graph, $(ALL_CUSTOM_STUBS)))

DOC_NAME =
TEX_NAME ?= $(DOC_NAME)
TEX_FLAGS = -interaction=nonstopmode

help:
	@echo "Build:"
	@echo "  - build : Build a fresh copy of relevant artifacts."
	@echo "  - paper : Build a fresh copy of just the ICSE paper."
	@echo "  - thesis: Build a fresh copy of just the thesis."
	@echo "  - debug : Same as 'thesis', but pauses build on errors for easier debugging."
	@echo "  - poster: Build a fresh copy of the testing terminology poster."
	@echo "  - clean : Clean working TeX build artifacts."
	@echo ""
	@echo "Supplementary Information:"
	@echo "  - help               : View this help guide."
	@echo "  - system_requirements: List system requirements."
	@echo "  - gloss              : Open all relevant glossaries in Excel."
	@echo "  - csv_diff           : View changes to glossaries in an intuitive format."

system_requirements:
	@echo "System Requirements: LaTeX (latexmk + LuaLaTeX), Pygments, InkScape"
	@echo "  - working LaTeX installation (with latexmk and LuaLaTeX)"
	@echo "  - Pygments (for code snippet syntax highlighting, installed with Python/pip)"
	@echo "  - InkScape (for SVG-based figures)"

gloss:
	$(foreach gloss, $(CSV_GLOSSARIES),EXCEL.EXE $(gloss) &)

gen_csv_diffs:
	for gloss in $(GLOSSARIES) ; do \
		py scripts/diffCSV.py $$gloss; \
	done

csv_diff: gen_csv_diffs
	for gloss in $(DIFF_GLOSSARIES) ; do \
		git diff --word-diff=plain --color --no-index --word-diff-regex='[[:alnum:]]+|[^[:space:],\);\.]+|[,\);\.]+' scripts/$$gloss $$gloss; \
		if [ $$? -ne 1 ]; then echo "No diff in $$gloss"; rm $$gloss; fi; \
	done

# Update diff files for better diffs, ignore errors if no difference
update_diffs: gen_csv_diffs
	for gloss in $(DIFF_GLOSSARIES) ; do \
		if [ -f $$gloss ]; then mv $$gloss scripts/$$gloss; fi; \
	done

gen_latex:
	-mkdir build || true
	py scripts/csvToGraph.py
	py scripts/undefinedTermSources.py

compile_graphs:
	for filename in $(GRAPHS) ; do \
			filename=$${filename%.tex} ; \
			# -rm filename.pdf ; \
			latex -interaction=nonstopmode -shell-escape $${filename}.tex || true ; \
			latex -interaction=nonstopmode -shell-escape $${filename}.tex || true ; \
			basefilename=$$(basename $$filename) ; \
			cp $${basefilename}.pdf $${filename}.pdf ; \
	done
	rm *Graph*
	rm *Legend* || true

custom_graphs: GRAPHS="$(CUSTOM_GRAPHS)"
custom_graphs: gen_latex compile_graphs

graphs: gen_latex compile_graphs

compile_doc: # '-output-directory=build' is a special name and is referenced from '\usepackage{minted}' region in some .tex files
	-latexmk -output-directory=build -jobname=$(DOC_NAME) -pdflatex=lualatex -pdf $(TEX_FLAGS) -shell-escape $(TEX_NAME).tex
	cp build/$(DOC_NAME).pdf $(DOC_NAME).pdf
	-rm lualatex*.fls || true

paper thesis poster: gen_latex # standard build of documents
# Attempted to convert the following find and replace working in VS Code:
# ([^p])p.[\s~]+(\d+)([-,])(\d+) -> $1pp.~$2$3$4
# To a Makefile rule unsuccessfully (grep not finding tildes):
# grep -Irwl "([^p])p.[\s~]+(\d+)([-,])(\d+)" --include='*.tex' . | xargs sed -ri "s/([^p])p.[\s~]+(\d+)([-,])(\d+)/\1pp.~\2\3\4/g"
	make compile_doc DOC_NAME=$@

paper_blind: paper # double-blind build of ICSE paper for review submission
	make compile_doc DOC_NAME=$@ TEX_NAME=$<

build: csv_diff paper thesis graphs

debug: DOC_NAME=thesis
debug: TEX_FLAGS=
debug: gen_latex compile_doc # for finding hard issues, this is an interactive version of 'thesis'

clean:
	rm -rf build/
