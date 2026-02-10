# Makefile for LWA Documentation
# Builds PDF documents from LaTeX sources

# Directories
SHL_ICD_DIR = SHL_ICD

# Output files
SHL_ICD_PDF = SHL_ICD.pdf

# Default target
all: shl-icd

# SHL ICD
shl-icd: $(SHL_ICD_PDF)

$(SHL_ICD_PDF): $(SHL_ICD_DIR)/lwa-icd.cls $(SHL_ICD_DIR)/SHL_ICD.tex $(wildcard $(SHL_ICD_DIR)/**/*.tex)
	cd $(SHL_ICD_DIR) && pdflatex -interaction=nonstopmode SHL_ICD.tex || true
	cd $(SHL_ICD_DIR) && pdflatex -interaction=nonstopmode SHL_ICD.tex || true
	mv $(SHL_ICD_DIR)/SHL_ICD.pdf .

# Clean intermediate files
clean:
	cd $(SHL_ICD_DIR) && rm -f *.aux *.log *.toc *.out *.lot *.lof

# Clean all generated files
distclean: clean
	rm -f $(SHL_ICD_PDF)

# Phony targets
.PHONY: all shl-icd clean distclean
