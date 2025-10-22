# Makefile for $CLARA/ai_assistant
# Default: run the static extractor and write to ai_assistant/knowledge/

# --- Config (override at invoke time if needed) ---
PY        ?= python3
REPO      ?= $(abspath ..)                 # path to C-LARA repo root
PUBS      ?= $(abspath ../publications_pdf) # path to local publications folder (optional)
OUT       ?= $(abspath ./knowledge)        # output folder for generated knowledge
SCRIPT    ?= clara_feature_extractor.py

# Optional: use a venv (uncomment if you want)
# VENV_DIR  ?= .venv
# PY        := $(VENV_DIR)/bin/python
# PIP       := $(VENV_DIR)/bin/pip

# --- Phony targets ---
.PHONY: all extract extract-nopubs clean rebuild show help deps

# Default target
all: extract

# Install minimal deps (pyyaml). Uncomment venv lines above if you want isolation.
deps:
	@echo "Installing minimal dependencies (pyyaml)…"
	$(PY) -m pip install --upgrade pip >/dev/null
	$(PY) -m pip install pyyaml

# Run extractor with publications
extract: $(SCRIPT)
	@echo "Running extractor:"
	@echo "  REPO = $(REPO)"
	@echo "  PUBS = $(PUBS)"
	@echo "  OUT  = $(OUT)"
	@mkdir -p "$(OUT)"
	$(PY) $(SCRIPT) --repo "$(REPO)" --pubs "$(PUBS)" --out "$(OUT)"

# Run extractor without publications
extract-nopubs: $(SCRIPT)
	@echo "Running extractor (no publications):"
	@echo "  REPO = $(REPO)"
	@echo "  OUT  = $(OUT)"
	@mkdir -p "$(OUT)"
	$(PY) $(SCRIPT) --repo "$(REPO)" --out "$(OUT)"

# Clean generated knowledge
clean:
	@echo "Removing knowledge output at $(OUT)"
	@rm -rf "$(OUT)"

# Clean + extract
rebuild: clean extract

# Show current config
show:
	@echo "PY   = $(PY)"
	@echo "REPO = $(REPO)"
	@echo "PUBS = $(PUBS)"
	@echo "OUT  = $(OUT)"
	@echo "SCRIPT = $(SCRIPT)"

# Help
help:
	@echo "Targets:"
	@echo "  deps             Install minimal deps (pyyaml)"
	@echo "  extract          Run extractor with publications (default)"
	@echo "  extract-nopubs   Run extractor without publications"
	@echo "  clean            Remove knowledge output"
	@echo "  rebuild          Clean then extract"
	@echo "  show             Show current variable values"
	@echo "Variables (override like VAR=value):"
	@echo "  PY   (default: python3)"
	@echo "  REPO (default: ../)"
	@echo "  PUBS (default: ../publications_pdf)"
	@echo "  OUT  (default: ./knowledge)"
