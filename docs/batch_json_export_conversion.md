# Batch-convert legacy C-LARA export bundles to JSON-format bundles

Use the Django management command `convert_exported_project_bundles_to_json` when you already have a folder downloaded from a C-LARA server where each immediate subfolder is one project and contains exactly:

1. one legacy C-LARA export zip, and
2. one JSON metadata file.

The command imports each legacy zip into the local C-LARA instance, immediately exports it again using the JSON-based export format (`annotated_text.json`), and writes a matching output folder. The metadata JSON file is copied unchanged. By default, it does not generate missing TTS audio and it skips projects that contain a phonetic text version.

## Basic invocation

From the repository root, with your normal C-LARA environment activated:

```bash
python manage.py convert_exported_project_bundles_to_json /path/to/legacy_exports /path/to/json_exports --username YOUR_DJANGO_USERNAME
```

For example:

```bash
python manage.py convert_exported_project_bundles_to_json \
  /mnt/adelaide_download/all_legacy_project_exports \
  /mnt/adelaide_download/all_json_project_exports \
  --username admin
```

After a successful run, each output subfolder will have the same name as the input subfolder and will contain:

- a JSON-format zip with the same filename as the input zip; and
- a copy of the input metadata JSON file.

The command also writes `conversion_index.json` in the destination root summarising converted, skipped, and failed project folders.

## Useful options

```bash
python manage.py convert_exported_project_bundles_to_json SOURCE_ROOT DEST_ROOT --dry-run
```

Lists the project folders that would be converted without importing or writing bundles.

```bash
python manage.py convert_exported_project_bundles_to_json SOURCE_ROOT DEST_ROOT --existing overwrite --username admin
```

Replaces an existing output subfolder. The default is `--existing skip`; `--existing error` stops on pre-existing output.

```bash
python manage.py convert_exported_project_bundles_to_json SOURCE_ROOT DEST_ROOT --keep-imported-projects --username admin
```

Keeps the temporary imported `CLARAProject` database rows after conversion. By default, the command deletes those rows after each JSON-format export has been written, so the conversion database does not fill up with temporary projects.

```bash
python manage.py convert_exported_project_bundles_to_json SOURCE_ROOT DEST_ROOT --generate-audio --username admin
```

Allows the JSON export step to generate missing TTS audio. The default is not to generate audio, which is usually the right behaviour for preprocessing downloaded Adelaide export bundles before transferring them to C-LARA-2.

```bash
python manage.py convert_exported_project_bundles_to_json SOURCE_ROOT DEST_ROOT --no-skip-phonetic-projects --username admin
```

Includes projects that contain a phonetic text version. The default is `--skip-phonetic-projects`, because C-LARA-2 does not yet support importing these projects.

## Notes

- Run the command in a local C-LARA environment that can already import and export individual project bundles.
- `SOURCE_ROOT` and `DEST_ROOT` must be different directories.
- Each input project subfolder must contain exactly one `.zip` and exactly one `.json` file.
- Missing audio is not generated unless you explicitly pass `--generate-audio`.
- Phonetic projects are skipped unless you explicitly pass `--no-skip-phonetic-projects`.
- If `--username` is omitted, the command uses the first superuser, then the first staff user, then the first user in the database.
