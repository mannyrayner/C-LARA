# C-LARA Backup & Migration — Architecture & Export Plan (Pass 1)

> Purpose: capture enough architecture and operational detail to (a) export everything we care about from the UniSA host quickly and repeatably, and (b) restore to a new host with minimal surprises. This doc will be the basis for script implementation in Pass 2 and for the “C-LARA AI Assistant” knowledge base.

---

## 0) High-level overview

- **Stack**: Stack: Django application (“C‑LARA”), DB PostgreSQL on the UniSA server; SQLite (default Django DB) on Manny’s laptop for local dev. The codebase is DB‑agnostic and runs on both. Redis may be used for background tasks/queues (confirm usage); Nginx reverse proxy in front of the app.## 0) High-level overview

- **Stack**: Django application (“C-LARA”), DB **PostgreSQL** on the UniSA server; **SQLite** (default Django DB) on Manny’s laptop for local dev. The codebase is DB-agnostic and runs on both. **Asynchronous tasks**: handled by **DjangoQ** (confirm broker/config). In code, schedule background work with:

  ```python
  from django_q.tasks import async_task
  async_task(func_or_path, *args, **kwargs)```
- **Hot data pattern**: many small files created/edited in project trees; compiled artefacts per project; legacy LARA compiled trees.
- **Backup approach**: logical, app-level exports **plus** coarse filesystem snapshots.
- **Non-goals** (for now): S3/Swift for hot path; multi-writer across installs.

---

## 1) Data domains we must preserve

1. **Project source** (per project): the editable inputs (text, images, config).  
2. **Project compiled** outputs (per project): published artefacts.  
3. **Legacy LARA compiled** content (directory of historical builds).  
4. **Database**: accounts, project metadata, relations, job history, etc.  
5. **Configs & infra parity**: app version (git), `.env/settings`, Nginx site, cron/systemd units.
6. **Generated/cached media**: especially TTS-generated audio caches we want to retain to avoid expensive re-generation; confirm cache root path and retention policy.

---

## 2) Filesystem layout (current host)

> Concrete paths as configured on the UniSA server (rooted at `$CLARA`).

- **Projects source root**: `$CLARA/clara_content`

- **Compiled output roots**:
  - primary: `$CLARA/clara_compiled`
  - phonetic: `$CLARA/clara_compiled_phonetic`
  - questionnaire exports: `$CLARA/clara_compiled_for_questionnaire`

- **Legacy LARA root**: `$CLARA/lara_legacy`

- **Global media & repositories (keep in backups):**
  - **TTS audio cache (ORM)**: `$CLARA/audio/tts_repository_orm`
    - metadata DB: `$CLARA/audio/tts_metadata.db`
    - local DB: `$CLARA/audio/tts_metadata_local.db`
  - **TTS base dir (non-ORM, legacy)**: `$CLARA/audio/tts_repository`
  - **Image repository (ORM)**: `$CLARA/images/image_repository_orm`
    - metadata DB: `$CLARA/images/image_metadata.db`
  - **Phonetic lexicon repository**: `$CLARA/phonetic_lexicon`
    - metadata DB: `$CLARA/phonetic_lexicon/phonetic_lexicon_metadata.db`
  - **Prompt templates**: `$CLARA/prompt_templates`
  - **Phonetic orthography**: `$CLARA/phonetic_orthography`

- **Renderer templates**: `$CLARA/templates`

- **Backup root (to create)**: `/srv/clara_backups`

> Space estimate: fill approximate GB for each root.

---

## 3) Django application map

- **Project models (split)**:
  - `clara_app.models.CLARAProject` (DB model; holds metadata like `title`, `internal_id`, `l1`, `l2`, flags, etc.). It also exposes helpers such as `rendered_output_dir(text_type)` and `zip_filepath(text_type)` for locating build artefacts. :contentReference[oaicite:0]{index=0}
  - `clara_app.clara_main.CLARAProjectInternal` (filesystem-backed project; owns the on-disk tree, text-version files, metadata, import/export, rendering/internals). Instances are keyed by `internal_id` and manage the project directory under `$CLARA`. :contentReference[oaicite:1]{index=1}

- **Export helpers (top-level entry points)**:
  - **Source export (project source as a self-contained zip)**:
    - Web entrypoint: `export_zipfile_views.make_export_zipfile(request, project_id)` which schedules an async task via `django_q.tasks.async_task` to create the export zip by calling `clara_project_internal.create_export_zipfile(...)`. We will add a small refactor to also **return** (or make accessible) the resulting zipfile path/bytes directly for non-HTTP/management-command use. :contentReference[oaicite:2]{index=2}
  - **Compiled export (pack already-rendered HTML + rewrite multimedia to /multimedia + zip)**:
    - Function: `clara_make_content_zip.build_content_zip_for_text_type(request, project, text_type) → str` returning the final zip **filepath**. It copies the rendered tree, rewrites `<img>`/audio URLs, copies required media into `multimedia/`, and zips the bundle. :contentReference[oaicite:3]{index=3}

- **Related async pattern**:
  - `make_export_zipfile` → creates `CLARAProjectInternal(...)` from DB row, infers audio settings, enqueues `clara_project_internal_make_export_zipfile(...)`, then monitors status via `make_export_zipfile_status` / `make_export_zipfile_monitor`. S3 presigned URL support is present if `_s3_storage` is enabled. :contentReference[oaicite:4]{index=4}

- **Management command location**:
  - Use the standard Django layout under the main app: `clara_app/management/commands/`. Our Pass-2 commands (`backup_all_source_zips`, `backup_all_compiled_zips`) will live here and call the same helpers used by the views above (or thin refactors thereof). (App label inferred from imports like `from .models import CLARAProject`.) :contentReference[oaicite:5]{index=5} :contentReference[oaicite:6]{index=6}

> Note: For performance and fewer moving parts, the management commands will prefer **in-process** helper calls (e.g., a refactored function that returns a zip path) over HTTP round-trips. We’ll keep the async web flow intact for users, but expose a direct function for batch exports.


---

## 4) Backup targets (artifacts we’ll produce)

**Root directory:** `/srv/clara_backups/`

> For easier restore and auditing, we bundle **metadata + zip together per unit** (one folder per project or legacy item), and also generate lightweight indexes at the top level.

- `source_exports/`
  - `<project_id>/`
    - `metadata.json`  *(id, name, language(s), owner, timestamps, sizes, checksums)*
    - `source.zip`     *(project editable inputs)*
  - `index.json` *(array of `{project_id, path, size_bytes, sha256, updated_at}`)*

- `compiled_exports/`
  - `<project_id>/`
    - `metadata.json`  *(includes text types present, sizes, checksums)*
    - `compiled.zip`   *(published artefacts for the project; if multiple text types exist we either: (a) include all in one zip under subdirs, or (b) create `compiled_<text_type>.zip` and reference them in `metadata.json`)*
  - `index.json`

- `legacy_zips/`
  - `<legacy_name>/`
    - `metadata.json`
    - `legacy.zip`
  - `index.json`

- `audio_cache/`  *(TTS-generated audio — details to be scripted later)*
  - `orm_db/`
    - `tts_metadata.db`
    - `tts_metadata_local.db`   *(if present)*
    - `db_metadata.json`        *(sizes, schema/version info if available)*
  - `archives/`
    - `tts_audio_part_0001.tgz` *(sharded archives of `$CLARA/audio/tts_repository_orm` or selected subsets)*
    - `tts_audio_part_0002.tgz`
    - `…`
  - `index.json` *(lists shards with sizes + checksums)*

- `db/`
  - `clara_db_YYYYMMDD_HHMMSS.dump` *(PostgreSQL custom format)*  
    **or** `clara_db_YYYYMMDD_HHMMSS.sql` *(if using Maria/MySQL)*
  - `index.json`

- `snapshots/`  *(coarse safety nets)*
  - `full_projects_tree.tgz`
  - `full_media_tree.tgz` *(if applicable)*
  - `index.json`

- `infra/`
  - `git_info.txt`           *(repo URL + commit hash)*
  - `settings_snapshot.txt`  *(sanitised; no secrets)* / `.env.sample`
  - `nginx_site.conf`
  - `systemd_units/`         *(service files)*
  - `index.json`

**Notes**
- Each `metadata.json` includes `size_bytes`, `sha256`, `created_at`, and any project identifiers needed to restore.
- Top-level `index.json` files are optional but make verification and scripted restores easier.


---

## 5) Management commands (design)

We will add **two Django management commands** that call the **same helpers** as the existing per-project web exports (see §3), but run **in-process** and write into the **per-unit layout** defined in §4.

### `backup_all_source_exports`
- Enumerate all `CLARAProject` rows (join to `CLARAProjectInternal` via `internal_id` as needed).
- For each project:
  - Create folder: `source_exports/<project_id>/`
  - Produce `source.zip` by calling the refactored helper behind `export_zipfile_views.make_export_zipfile(...)` (direct function that returns a local zip path).
  - Write `metadata.json` (id, name, languages, owner, size_bytes, sha256, created_at, commit hash if available).
- Update/append `source_exports/index.json` (one entry per project).
- **Skip gracefully** if a project cannot be exported; record in `failures.json`.

### `backup_all_compiled_exports`
- Enumerate all `CLARAProject` rows.
- For each project:
  - Create folder: `compiled_exports/<project_id>/`
  - Determine available `text_type`(s) (e.g., default, phonetic, questionnaire). Two supported modes:
    1) **Single bundle**: call `clara_make_content_zip.build_content_zip_for_text_type(...)` for each text type and merge into one `compiled.zip` with subfolders.
    2) **Per-text-type**: produce `compiled_<text_type>.zip` files.
  - Write `metadata.json` summarising text types exported, sizes, sha256 per zip, created_at.
- Update `compiled_exports/index.json`.
- **Skip gracefully** if a project has no compiled artefacts; record in `failures.json`.

### Common features / flags
- `--dest PATH` : override backup root (default `/srv/clara_backups`).
- `--only IDS`  : comma-separated project ids/slugs to include.
- `--skip IDS`  : comma-separated project ids/slugs to exclude.
- `--text-types TYPES` : restrict compiled export to a subset (e.g., `default,phonetic`).
- `--existing {skip,overwrite}` : behaviour when a destination already exists (default `skip`).
- `--workers N` : limited parallelism for CPU-bound zip steps (be conservative; IO is the bottleneck).
- `--checksums` : compute SHA256 for each produced artifact.
- `--dry-run`   : list what would be exported without writing files.
- Logging: progress per project, summary counts, and `failures.json` per command.

> Notes
> - Both commands write into the **unit folders** defined in §4 and keep the **top-level `index.json`** updated for easy verification and restore scripting.
> - We **avoid HTTP** paths; instead we refactor/introduce thin helpers that **return local zip paths** (wrapping the logic used by `make_export_zipfile` and `build_content_zip_for_text_type`).
> - When available, record the **git commit hash** and **app version** in `metadata.json` to aid reproducibility.

---

## 6) Shell scripts (design)

> These scripts **orchestrate and complement** the Django management commands in §5.  
> In particular, `backup_all.sh` **calls** `backup_all_source_exports` and `backup_all_compiled_exports` to produce per-project units under `source_exports/` and `compiled_exports/` (see §4), then archives legacy content, DB, TTS audio cache, infra, and optional coarse snapshots.

### `backup_all.sh` (orchestrator)
- **Purpose**: single entrypoint to produce a complete backup in one run.
- **Behaviour (order)**:
  1) Create directory layout under `${BACKUP_ROOT:-/srv/clara_backups}` (per §4).
  2) **Projects (via §5 commands):**
     - `python manage.py backup_all_source_exports   --dest "$BACKUP_ROOT"`
     - `python manage.py backup_all_compiled_exports --dest "$BACKUP_ROOT"`
  3) **Other domains (shell helpers below):**
     - `backup_legacy.sh`
     - `backup_db.sh`
     - `backup_audio_cache.sh`
     - `backup_infra.sh`
     - `backup_snapshots.sh` *(optional)*
  4) Generate top-level `manifest.json` (counts, bytes, start/end timestamps) and merge per-step `failures.json`.
- **Flags (propagated as appropriate)**:
  - `--dry-run`, `--checksums`, `--only`, `--skip`, `--text-types`, `--existing {skip,overwrite}`.
- **Safety**: lock file `/var/lock/clara_backup.lock`; atomic writes (`*.tmp` → `mv`).

### `backup_legacy.sh`
- **Inputs**:
  - `LEGACY_ROOT=${LEGACY_ROOT:-$CLARA/lara_legacy}`
  - `DEST=$BACKUP_ROOT/legacy_zips`
- **Behaviour**:
  - For each top-level subdirectory in `$LEGACY_ROOT`:
    - Create unit folder: `"$DEST/<legacy_name>/"`
    - Archive as `legacy.zip` (`zip -r` or `tar czf` for very large trees)
    - Write `metadata.json` (name, size_bytes, sha256, mtime)
  - Maintain `"$DEST/index.json"`.

### `backup_db.sh`
- **Inputs**: `DB_ENGINE` (e.g., `postgresql`), creds from env / `.pgpass` / `.my.cnf`.
- **Destination**: `$BACKUP_ROOT/db`
- **Behaviour**:
  - **PostgreSQL**: `pg_dump -Fc <db> > "$DEST/clara_db_YYYYMMDD_HHMMSS.dump"`
  - **Maria/MySQL**: `mysqldump --single-transaction <db> > "$DEST/clara_db_YYYYMMDD_HHMMSS.sql"`
  - Compute size + sha256; update `db/index.json`.

### `backup_audio_cache.sh`
- **Purpose**: archive TTS-generated audio caches + metadata (see §2, §4).
- **Inputs**:
  - Repo: `$CLARA/audio/tts_repository_orm`
  - DBs: `$CLARA/audio/tts_metadata.db`, `$CLARA/audio/tts_metadata_local.db` (if present)
  - `DEST=$BACKUP_ROOT/audio_cache`, `SHARD_SIZE_MB=2048` (configurable)
- **Behaviour**:
  - Copy DB files to `"$DEST/orm_db/"`; write `db_metadata.json`.
  - Tar into shards under `"$DEST/archives/"`: `tts_audio_part_0001.tgz`, `...`
  - Compute sha256; update `"$DEST/index.json"`.

### `backup_infra.sh`
- **Inputs**: app repo path, `.env`/settings, nginx site, systemd unit paths.
- **Destination**: `$BACKUP_ROOT/infra`
- **Behaviour**:
  - `git_info.txt` (remote URLs + commit hash)
  - `settings_snapshot.txt` (sanitised) or `.env.sample`
  - `nginx_site.conf`, `systemd_units/` (service files)
  - Update `infra/index.json`.

### `backup_snapshots.sh` *(optional, coarse safety nets)*
- **Inputs**:
  - Projects tree (e.g., `$CLARA/clara_content`)
  - Global media subtrees as needed (e.g., `$CLARA/images`, `$CLARA/phonetic_lexicon`)
  - `DEST=$BACKUP_ROOT/snapshots`
- **Behaviour**:
  - Create `full_projects_tree.tgz` and, if relevant, `full_media_tree.tgz`
  - Compute checksums; update `"$DEST/index.json"`.

> **Important**: The **project source and compiled backups are produced by the Django commands in §5** and written to `source_exports/` and `compiled_exports/`. The shell scripts handle **everything else** and assemble a top-level manifest for verification and restore.


---

## 7) Restore notes (outline)

1) Provision a new Unix host with a **large local/block disk** (fast POSIX FS).  
2) Install system packages, Python, DB, Nginx; clone the C-LARA repo.  
3) Create the database; restore:
   - **PostgreSQL**: `pg_restore -d <db_name> <dump_file>`  
   - **Maria/MySQL**: `mysql < <sql_file>`
4) Restore projects (default = **compiled** for conservative rollout):
   - **Default (compiled-first)**: unpack each project’s `compiled.zip` (or `compiled_<text_type>.zip`) into the runtime location expected by the app so users immediately see the last known good outputs.
   - **Optional (rebuild from source)**: when you *choose* to recompile, import that project’s `source.zip` and run the usual compile pipeline.
5) Restore **legacy** zips under the legacy root (matching the original URL paths if required).  
6) Restore configs (nginx site, `.env` / settings), TLS, and start services.  
7) Smoke test: open a few projects, verify pages render, audio/images resolve, and DB lookups succeed.


---

## 8) Verification checklist

- **Project counts**: number of exported units in `source_exports/` and `compiled_exports/` == number of rows in `CLARAProject` (minus any intentionally skipped/failed items recorded in `failures.json`).
- **Indexes present**: `index.json` exists and lists every unit for `source_exports/`, `compiled_exports/`, `legacy_zips/`, `audio_cache/archives/`, `db/`, `snapshots/`, and `infra/`.
- **Checksums & sizes**: each unit’s `metadata.json` (and shard `index.json` where applicable) includes `size_bytes` and `sha256`; spot-verify a few with `sha256sum`.
- **Random spot-checks**:
  - Unzip a few **compiled** bundles and open pages locally (images/audio resolve, links okay).
  - Unzip a few **source** bundles and run a compile in a dev instance (CI-like smoke test).
- **DB restore dry-run**: create a scratch DB and `pg_restore` (or `mysql` import); confirm schema + migrations align with current code.
- **Legacy content**: unzip a couple of large legacy zips (e.g., Proust vols) and verify expected structure/media files exist.
- **Audio cache**: confirm `audio_cache/orm_db/*.db` files are present and non-empty; restore one or two `tts_audio_part_*.tgz` shards and verify file integrity.
- **Manifest**: top-level `manifest.json` shows consistent totals (counts, bytes) and the run timestamps match logs.

---

## 9) Security & access

- **Permissions**: restrict `/srv/clara_backups` to a dedicated backup group/user (e.g., `clara-backup:clara-backup`, `750` on dirs, `640` on files).
- **Transfer**: use SSH with keys to `rsync` backups to Manny’s laptop (and optionally a second off-site location).
- **Secrets hygiene**: ensure `infra/settings_snapshot.txt` and `.env.sample` contain **no live secrets** (redact/placeholder as needed).
- **Encryption (optional)**: encrypt large tarballs or DB dumps with `age` or `gpg` before off-site transfer/storage.
- **Provenance**: include `git_info.txt` (remote URLs + commit hash) so backups are tied to a specific code revision.
- **Rotation**: keep at least two recent backup runs; prune older runs with a simple retention policy (e.g., 7 daily, 4 weekly).

---

*End of Pass 1 doc. Pass 2 will implement the commands/scripts exactly as specified here, once placeholders are filled.*
