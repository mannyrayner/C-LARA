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
	[ -n "$(CLARA)" ] || { echo "CLARA is not set"; exit 1; }; \
	[ -d "$(LEGACY_ROOT)" ] || { echo "LEGACY_ROOT does not exist: $(LEGACY_ROOT)"; exit 1; }; \
	mkdir -p "$(BACKUP_DEST)"; \
	if command -v pigz >/dev/null 2>&1; then COMP="tar -I 'pigz -9' -cf"; else COMP="tar -czf"; fi; \
	echo "==> Archiving top-level folders from $(LEGACY_ROOT) to $(BACKUP_DEST)"; \
	for d in "$$(find "$(LEGACY_ROOT)" -mindepth 1 -maxdepth 1 -type d -print)"; do \
	  name="$$(basename "$$d")"; \
	  out="$(BACKUP_DEST)/$${name}.tgz"; \
	  echo "----> $$name"; \
	  ( cd "$(LEGACY_ROOT)" && eval $$COMP "\"$$out\"" "\"$$name\"" ); \
	  sha256sum "$$out" > "$$out.sha256"; \
	done; \
	echo "==> Splitting archives larger than $(SPLIT_MB) MB"; \
	for f in "$(BACKUP_DEST)"/*.tgz; do \
	  [ -f "$$f" ] || continue; \
	  sz_m=$$(du -m "$$f" | awk '{print $$1}'); \
	  if [ "$$sz_m" -ge "$(SPLIT_MB)" ]; then \
	    echo "----> splitting $${f}"; \
	    split -b "$(SPLIT_MB)m" -d -a 3 "$$f" "$$f.part."; \
	    sha256sum "$$f".part.* > "$$f.parts.sha256"; \
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
