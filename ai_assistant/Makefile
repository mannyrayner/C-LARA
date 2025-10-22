# Makefile for $CLARA/ai_assistant

# ---- Config (paths) ----
PY     ?= python3
REPO   ?= $(strip $(abspath ..))
PUBS   ?= $(strip $(abspath ../publications_pdf))
OUT    ?= $(strip $(abspath ./knowledge))

SCRIPT ?= clara_feature_extractor.py
ENRICH ?= ai_enrich_features.py

REPO_WIN := $(shell cygpath -w '$(REPO)' 2>/dev/null)
PYMODPATH := $(if $(REPO_WIN),$(REPO_WIN),$(REPO))

# ---- Private config via TOML ----
CONFIG_TOML ?= $(abspath ./config.toml)

# Helper: load MODEL/API_KEY from TOML at recipe time

define LOAD_FROM_TOML
eval "$$(PYTHONPATH="$(PYMODPATH)" $(PY) read_config.py --toml "$(CONFIG_TOML)" --format sh)"; \
if [ -z "$$MODEL" ]; then echo "ERROR: MODEL missing in $(CONFIG_TOML)"; exit 2; fi; \
if [ -z "$$API_KEY" ]; then echo "ERROR: API_KEY missing in $(CONFIG_TOML)"; exit 2; fi;
endef

# ---- Phonies ----
.PHONY: all deps extract extract-nopubs map enrich enrich-some clean clean-cfg show help check-config

all: extract

deps:
	@echo "Installing minimal dependencies (pyyaml; tomli for Python<3.11)…"
	$(PY) -m pip install --upgrade pip >/dev/null
	$(PY) -m pip install pyyaml tomli >/dev/null 2>&1 || true

extract: $(SCRIPT)
	@echo "Running extractor:"
	@echo "  REPO = $(REPO)"
	@echo "  PUBS = $(PUBS)"
	@echo "  OUT  = $(OUT)"
	@mkdir -p "$(OUT)"
	PYTHONPATH="$(PYMODPATH)" \
	$(PY) -m ai_assistant.clara_feature_extractor --repo "$(REPO)" --pubs "$(PUBS)" --out "$(OUT)"

extract-nopubs: $(SCRIPT)
	@echo "Running extractor (no publications):"
	@echo "  REPO = $(REPO)"
	@echo "  OUT  = $(OUT)"
	@mkdir -p "$(OUT)"
	PYTHONPATH="$(PYMODPATH)" \
	$(PY) -m ai_assistant.clara_feature_extractor --repo "$(REPO)" --out "$(OUT)"

# Full pipeline: extract -> enrich
map: extract enrich

# Enrich all cards — TOML required (loads MODEL/API_KEY at recipe time)
enrich: $(ENRICH)
	@mkdir -p "$(OUT)"
	@{ $(LOAD_FROM_TOML) \
	  echo "Enriching cards with AI (MODEL=$$MODEL)"; \
	  OPENAI_API_KEY="$$API_KEY" PYTHONPATH="$(PYMODPATH)" \
	  $(PY) -m ai_assistant.ai_enrich_features \
	    --repo "$(REPO)" --out "$(OUT)" \
	    --gpt-model "$$MODEL"; }

# Enrich only a subset: make enrich-some ONLY="export_zipfile,edit_images_v2" LIMIT=2
ONLY  ?=
LIMIT ?= 0
enrich-some: $(ENRICH)
	@mkdir -p "$(OUT)"
	@{ $(LOAD_FROM_TOML) \
	  echo "Enriching subset (MODEL=$$MODEL)"; \
	  PYTHONPATH="$(PYMODPATH)" \
	  OPENAI_API_KEY="$$API_KEY" PYTHONPATH="$(PYMODPATH)" \
	  $(PY) -m ai_assistant.ai_enrich_features \
	    --repo "$(REPO)" --out "$(OUT)" \
	    $(if $(ONLY),--only $(ONLY),) \
	    $(if $(LIMIT),--limit $(LIMIT),) \
	    --gpt-model "$$MODEL"; }

clean:
	@echo "Removing knowledge output at $(OUT)"
	@rm -rf "$(OUT)"

clean-cfg:
	@echo "Removing generated $(CONFIG_MK)"
	@rm -f "$(CONFIG_MK)"

rebuild: clean extract

show:
	@echo "PY   = $(PY)"
	@echo "REPO = $(REPO)"
	@echo "PUBS = $(PUBS)"
	@echo "OUT  = $(OUT)"
	@echo "MODEL = $(MODEL)"
	@echo "CONFIG_TOML = $(CONFIG_TOML)"
	@echo "CONFIG_MK   = $(CONFIG_MK)"
	@echo "SCRIPT = $(SCRIPT)"
	@echo "ENRICH = $(ENRICH)"

help:
	@echo "Targets: deps | extract | extract-nopubs | map | enrich | enrich-some | clean | clean-cfg | rebuild | show"
	@echo "Private config: put model/key in ai_assistant/config.toml; .config.mk is auto-generated and gitignored."
	@echo "Override examples:"
	@echo "  make enrich MODEL=gpt-5"
	@echo "  make enrich-some ONLY=\"export_zipfile,render_text_start_normal\" LIMIT=2"
