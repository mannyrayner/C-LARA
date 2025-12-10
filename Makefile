.PHONY: backup-legacy backup-legacy-clean backup-legacy-list

# Config
CLARA           ?= $(shell echo $$CLARA)
LEGACY_ROOT     ?= $(CLARA)/LARA_legacy
BACKUP_DEST     ?= $(CLARA)/backups_lara_legacy
SPLIT_MB        ?= 2000     # split threshold per part (~2GB)

migrate:
	python3 manage.py makemigrations
	python3 manage.py migrate

runserver:
	python3 manage.py runserver

qcluster:
	python3 manage.py qcluster

check:
	python3 manage.py check

superuser:
	python3 manage.py createsuperuser

collectstatic:
	python3 manage.py collectstatic

test:
	python3 manage.py test

count_lines:
	python3 count_lines.py

heroku_log:
	heroku logs --tail --app c-lara

backup_db:
	cp db.sqlite3 db.sqlite3.bkp

restore_db:
	cp db.sqlite3.bkp db.sqlite3 

.PHONY: backup-legacy backup-legacy-clean backup-legacy-list

# Config
CLARA           ?= $(shell echo $$CLARA)
# If your dir is lowercase, change to $(CLARA)/lara_legacy
LEGACY_ROOT     ?= $(CLARA)/LARA_legacy
BACKUP_DEST     ?= $(CLARA)/backups_lara_legacy
SPLIT_MB        ?= 2000     # split threshold per part (~2GB)

backup-legacy:
	@set -euo pipefail; \
	set -x; \
	echo "CLARA=$(CLARA)"; \
	echo "LEGACY_ROOT=$(LEGACY_ROOT)"; \
	echo "BACKUP_DEST=$(BACKUP_DEST)"; \
	[ -n "$(CLARA)" ] || { echo "CLARA is not set"; exit 1; }; \
	[ -d "$(LEGACY_ROOT)" ] || { echo "LEGACY_ROOT does not exist: $(LEGACY_ROOT)"; exit 1; }; \
	mkdir -p "$(BACKUP_DEST)"; \
	if command -v pigz >/dev/null 2>&1; then COMP="tar -I 'pigz -9' -cf"; else COMP="tar -czf"; fi; \
	echo "==> Archiving top-level folders from $(LEGACY_ROOT) to $(BACKUP_DEST)"; \
	find "$(LEGACY_ROOT)" -mindepth 1 -maxdepth 1 -type d -print0 | \
	while IFS= read -r -d '' d; do \
	  name=$$(basename "$$d"); \
	  out="$(BACKUP_DEST)/$${name}.tgz"; \
	  echo "----> $$name  ->  $$out"; \
	  ( cd "$(LEGACY_ROOT)" && eval $$COMP "\"$$out\"" "\"$$name\"" ) \
	    || { echo "WARN: archiving $$name failed; continuing"; continue; }; \
	  sha256sum "$$out" > "$$out.sha256" || { echo "WARN: checksum for $$out failed"; }; \
	done; \
	echo "==> Splitting archives larger than $(SPLIT_MB) MB"; \
	for f in "$(BACKUP_DEST)"/*.tgz; do \
	  [ -e "$$f" ] || break; \
	  sz_m=$$(du -m "$$f" | awk '{print $$1}'); \
	  if [ "$$sz_m" -ge "$(SPLIT_MB)" ]; then \
	    echo "----> splitting $${f}"; \
	    split -b "$(SPLIT_MB)m" -d -a 3 "$$f" "$$f.part." || { echo "WARN: split failed for $$f"; continue; }; \
	    sha256sum "$$f".part.* > "$$f.parts.sha256" || echo "WARN: sha256 for parts failed"; \
	    rm -f "$$f"; \
	  fi; \
	done; \
	echo "==> Done. Listing:"; \
	ls -lh "$(BACKUP_DEST)"

backup-legacy-list:
	@ls -lh "$(BACKUP_DEST)"

backup-legacy-clean:
	@echo "Removing $(BACKUP_DEST)"; \
	rm -rf "$(BACKUP_DEST)"

# === Cygwin-side Make targets (run these on your laptop) ===

# Remote (server) details
REMOTE_USER    ?= stm-admmxr
REMOTE_HOST    ?= stmpl-lara2.ml.unisa.edu.au
REMOTE_DIR     ?= /home/stm-admmxr/C-LARA/backups_lara_legacy/

# Local (laptop) destination in Cygwin path form
LOCAL_DIR      ?= /home/LARALegacyFromServer

# rsync options:
#  -a               archive (preserves times/perm as best as Windows allows)
#  --info=progress2 nice progress
#  --partial        keep partial files if interrupted
#  --inplace        write in place (helps resume big files)
#  -e ssh           use SSH transport
RSYNC_OPTS      ?= -a --info=progress2 --partial --inplace -e ssh

.PHONY: pull-legacy-backup pull-legacy-verify ensure-local-dir

ensure-local-dir:
	mkdir -p "$(LOCAL_DIR)"

pull-legacy-backup: ensure-local-dir
	@echo "Pulling from $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR) -> $(LOCAL_DIR)/"
	rsync $(RSYNC_OPTS) "$(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)" "$(LOCAL_DIR)/"

# Optional: verify any .sha256 files that came down (single-file archives)
pull-legacy-verify:
	@echo "Verifying .sha256 checksums (single-file .tgz):"
	@find "$(LOCAL_DIR)" -type f -name '*.sha256' -print0 | \
	  xargs -0 -I{} sh -c 'cd "$$(dirname "{}")" && sha256sum -c "$$(basename "{}")" || true'
	@echo "If you have split archives (.tgz.part.*), compare parts with the corresponding *.parts.sha256:"
	@echo "    cd $(LOCAL_DIR) && sha256sum -c <archive>.tgz.parts.sha256"

.PHONY: list-archives verify-legacy extract-legacy clean-extracted

list-archives:
	@ls -lh "$(LOCAL_DIR)"/*.tgz

# Verify any *.sha256 files (single-file archives)
verify-legacy:
	@set -euo pipefail; set -x; \
	find "$(LOCAL_DIR)" -maxdepth 1 -type f -name '*.sha256' -print0 | \
	xargs -0 -I{} sh -c 'cd "$$(dirname "{}")" && sha256sum -c "$$(basename "{}")"'

# Extract each .tgz into a directory with the same basename
# e.g., foo.tgz -> ./foo/
extract-legacy:
	@set -euo pipefail; set -x; \
	find "$(LOCAL_DIR)" -maxdepth 1 -type f -name '*.tgz' -print0 | \
	while IFS= read -r -d '' f; do \
	  base="$$(basename "$$f" .tgz)"; \
	  dest="$(LOCAL_DIR)/$$base"; \
	  mkdir -p "$$dest"; \
	  echo "==> Extracting $$f -> $$dest/"; \
	  tar -xzf "$$f" -C "$$dest"; \
	done

# Remove all extracted directories (does not delete the .tgz archives)
clean-extracted:
	@set -euo pipefail; set -x; \
	find "$(LOCAL_DIR)" -maxdepth 1 -type d ! -path "$(LOCAL_DIR)" -print0 | \
	while IFS= read -r -d '' d; do \
	  case "$$d" in \
	    "$(LOCAL_DIR)") ;; \
	    *) echo "Removing $$d"; rm -rf "$$d" ;; \
	  esac; \
	done
	
# === pull all exported project zips to Cygwin laptop ===
REMOTE_EXPORTS_DIR  ?= /home/stm-admmxr/C-LARA/tmp/all_exports/
LOCAL_EXPORTS_DIR   ?= /home/CLARA_all_exports

RSYNC_OPTS_EXPORTS  ?= -a --info=progress2 --partial --inplace -e ssh

.PHONY: make-all-clara-exports pull-all-clara-exports --existing overwrite --checksums

make-all-clara-exports:
	python3 manage.py export_all_project_zips --checksums
	
pull-all-clara-exports:
	mkdir -p "$(LOCAL_EXPORTS_DIR)"; \
	rsync $(RSYNC_OPTS_EXPORTS) "$(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_EXPORTS_DIR)" "$(LOCAL_EXPORTS_DIR)/"