#!/bin/bash
# Compile paper draft
pdflatex -interaction=nonstopmode draft.tex
bibtex draft
pdflatex -interaction=nonstopmode draft.tex
pdflatex -interaction=nonstopmode draft.tex
echo "Draft PDF: draft.pdf"
