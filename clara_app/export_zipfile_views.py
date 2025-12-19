"""
Export packaging views: create portable C-LARA export bundles (projects and audio).

This module provides UI endpoints for exporting data out of a running C-LARA instance
into a filesystem bundle (zip files / directory trees) that can be copied elsewhere and
imported later. There are three workflows:

A) Single-project export zip (role-guarded)
   Views:
     - make_export_zipfile(request, project_id)
         Creates a report_id via make_asynch_callback_and_report_id, then enqueues an async Django-Q task
         (make_export_zipfile_with_messages). Redirects to the monitor view. 
     - make_export_zipfile_status(request, project_id, report_id)
         JSON polling endpoint; returns unread TaskUpdate rows for report_id and derives status:
           status='error' if 'error' message seen
           status='finished' if 'finished' message seen
           else 'unknown'. :contentReference[oaicite:2]{index=2}
     - make_export_zipfile_monitor(request, project_id, report_id)
         Rendered monitor page which polls the status endpoint. :contentReference[oaicite:3]{index=3}
     - make_export_zipfile_complete(request, project_id, status)
         Completion page; if S3 storage is enabled, returns a presigned URL for the zipfile path
         computed by CLARAProjectInternal.export_zipfile_pathname(). 

   Work performed:
     - make_export_zipfile_with_messages(project, callback) calls clara_export_import.make_export_zipfile_internal(project),
       posts progress messages via post_task_update(callback, ...), and posts a terminal 'finished' or 'error' marker. 

   Export zip structure (built by clara_export_import.make_export_zipfile_internal):
     - Output zip path: $CLARA/tmp/<project_id>_zipfile.zip  (export_zipfile_pathname) 
     - Contents assembled in a temp dir then zipped:
         metadata.json
         project_dir/                 (project directory copied verbatim)
         audio/metadata.json + audio files (filenames rewritten to basenames)
         phonetic_audio/metadata.json + audio files (if phonetic text exists + human phonetic voice configured)
         images/metadata.json + image & thumbnail files (filenames rewritten to basenames)
         image_descriptions/metadata.json (records only)
       The global metadata includes project simple_clara_type, coherent-image flags, translation-for-images flag,
       and the project’s audio configuration (human voice ids and audio type settings). 

B) Bulk export of project source zips (admin-only)
   Views:
     - start_bulk_source_exports / bulk_source_exports_monitor / bulk_source_exports_status / bulk_source_exports_complete 

   Work performed:
     - export_all_project_zips_task(params, callback) iterates over CLARAProject objects (with optional only_ids/skip_ids filters),
       writes one directory per project under an output root, and records index/failures JSON files. 

   Output format:
     - Output root:
         Path(params["dest_root"]) if provided, else $CLARA/tmp/bulk_source_exports 
     - Per project:
         <out_root>/<project_id>/source.zip
         <out_root>/<project_id>/metadata.json   (id/title/l1/l2/owner_username/size_bytes/sha256)
     - Batch summary:
         <out_root>/index.json
         <out_root>/failures.json
     - Terminal status markers posted:
         'error' if failures exist, else 'finished'. :contentReference[oaicite:12]{index=12}

C) Bulk export of audio repository content (admin-only)
   Views:
     - start_bulk_audio_export / bulk_audio_export_monitor / bulk_audio_export_status / bulk_audio_export_complete 

   Work performed:
     - export_all_audio_task(params, callback) copies audio files referenced by AudioMetadata rows into a directory tree
       grouped by (engine_id, language_id, voice_id), and writes a manifest.json per triple plus index/failures. 

   Output format:
     - Output root: $CLARA/tmp/bulk_audio_exports 
     - Per triple:
         <out_root>/<engine_id>/<language_id>/<voice_id>/manifest.json
         (audio files stored alongside manifest, preserving filename)
     - Batch summary:
         <out_root>/index.json
         <out_root>/failures.json (only written if failures exist)

Task update mechanism
---------------------
All async jobs emit progress via post_task_update(callback, "..."). The callback is the object returned by
make_asynch_callback_and_report_id(...) and is polled via get_task_updates(report_id) in the *_status endpoints. 

Security model
--------------
- Single-project export endpoints require login and project role membership.
- Bulk export endpoints are restricted to admins (userprofile.is_admin).

Implementation caveats (current code)
-------------------------------------
- bulk_source_exports_complete reads from $CLARA/tmp/bulk_source_exports unconditionally (via os.environ["CLARA"]/tmp/...),
  which may diverge from a custom dest_root used in the batch task. :contentReference[oaicite:19]{index=19} 
- bulk_audio_export_status flags an error if any message contains substring "error". The audio task posts
  "finished with N errors" on failure, so status becomes "error" (probably intended), but note this is substring-based. 
"""

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages

from django.db.models import Prefetch

from django_q.tasks import async_task

from .models import CLARAProject, ProjectPermissions, AudioMetadata
from .forms import MakeExportZipForm, BulkSourceExportForm, BulkAudioExportForm

from .clara_export_import import make_export_zipfile_internal

from .clara_audio_repository_orm import AudioRepositoryORM

from .utils import get_user_config, make_asynch_callback_and_report_id
from .utils import user_has_a_project_role
from .utils import get_task_updates
from .utils import audio_info_for_project

from .clara_main import CLARAProjectInternal

from .clara_utils import _s3_storage, get_config, absolute_file_name, make_directory
from .clara_utils import generate_s3_presigned_url
from .clara_utils import post_task_update

import logging
import traceback
import os
import json
import hashlib
import shutil

from pathlib import Path

config = get_config()
logger = logging.getLogger(__name__)

# Start the async process that will do the rendering
@login_required
@user_has_a_project_role
def make_export_zipfile(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    audio_info = audio_info_for_project(project)

    if request.method == 'POST':
        form = MakeExportZipForm(request.POST)
        if form.is_valid():
            task_type = f'make_export_zipfile'
            callback, report_id = make_asynch_callback_and_report_id(request, task_type)

            # Enqueue the task
            try:
                task_id = async_task(make_export_zipfile_with_messages, project, callback)

                # Redirect to the monitor view, passing the task ID and report ID as parameters
                return redirect('make_export_zipfile_monitor', project_id, report_id)
            except Exception as e:
                messages.error(request, f"An internal error occurred in export zipfile creation. Error details: {str(e)}\n{traceback.format_exc()}")
                form = MakeExportZipForm()
                return render(request, 'clara_app/make_export_zipfile.html', {'form': form, 'project': project})
    else:
        form = MakeExportZipForm()

        clara_version = get_user_config(request.user)['clara_version']
        
        return render(request, 'clara_app/make_export_zipfile.html', {'form': form, 'project': project, 'clara_version': clara_version})

def make_export_zipfile_with_messages(project, callback):
    try:
        zipfile = make_export_zipfile_internal(project)
        post_task_update(callback, f'--- Zipfile created and copied to {zipfile}')
        post_task_update(callback, 'finished')
        return zipfile
    except Exception as e:
        post_task_update(callback, f'*** Error when trying to create export zipfile')
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
        post_task_update(callback, error_message)
        post_task_update(callback, 'error')
        return False


# This is the API endpoint that the JavaScript will poll
@login_required
@user_has_a_project_role
def make_export_zipfile_status(request, project_id, report_id):
    messages = get_task_updates(report_id)
    print(f'{len(messages)} messages received')
    if 'error' in messages:
        status = 'error'
    elif 'finished' in messages:
        status = 'finished'  
    else:
        status = 'unknown'    
    return JsonResponse({'messages': messages, 'status': status})

# Render the monitoring page, which will use JavaScript to poll the task status API
@login_required
@user_has_a_project_role
def make_export_zipfile_monitor(request, project_id, report_id):
    project = get_object_or_404(CLARAProject, pk=project_id)

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/make_export_zipfile_monitor.html',
                  {'report_id': report_id, 'project_id': project_id, 'project': project, 'clara_version': clara_version})

# Display the final result of creating the zipfile
@login_required
@user_has_a_project_role
def make_export_zipfile_complete(request, project_id, status):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    if status == 'error':
        succeeded = False
        presigned_url = None
        messages.error(request, "Unable to create export zipfile. Try looking at the 'Recent task updates' view")
    else:
        succeeded = True
        messages.success(request, f'Export zipfile created')
        if _s3_storage:
            presigned_url = generate_s3_presigned_url(clara_project_internal.export_zipfile_pathname())
        else:
            presigned_url = None
        
    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/make_export_zipfile_complete.html', 
                  {'succeeded': succeeded,
                   'project': project,
                   'presigned_url': presigned_url,
                   'clara_version': clara_version} )

# ------------------------------------------
# Bulk export of project directories

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def start_bulk_source_exports(request):
    if request.method == "POST":
        form = BulkSourceExportForm(request.POST)
        if form.is_valid():
            callback, report_id = make_asynch_callback_and_report_id(request, "bulk_source_exports")
            params = form.cleaned_data
            async_task(export_all_project_zips_task, params, callback)
            return redirect("bulk_source_exports_monitor", report_id=report_id)
    else:
        form = BulkSourceExportForm()
    return render(request, "clara_app/bulk_source_exports_start.html", {"form": form})

def export_all_project_zips_task(params, callback):
    out_root = Path( params.get("dest_root") or absolute_file_name("$CLARA/tmp/bulk_source_exports") )
    out_root.mkdir(parents=True, exist_ok=True)

    if params.get("clear_output_dir"):
        _clear_dir(out_root)
        post_task_update(callback, f"Cleared existing contents in {out_root}")

    # filters
    only_ids   = set(int(x) for x in (params.get("only_ids") or "").split(",") if x.strip().isdigit())
    skip_ids   = set(int(x) for x in (params.get("skip_ids") or "").split(",") if x.strip().isdigit())

    qs = CLARAProject.objects.all()
    if only_ids:
        qs = [ project for project in qs if project.id in only_ids ]
    if skip_ids:
        qs = [ project for project in qs if project.id not in skip_ids ]

    total = len(qs)
    done = 0
    failures = []

    post_task_update(callback, f"Starting bulk source export: {total} projects")

    index = []
    for project in qs:
        try:
            unit_dir = out_root / str(project.id)
            unit_dir.mkdir(parents=True, exist_ok=True)

            post_task_update(callback, f"Preparing to export project {project.id} “{project.title}”")
            zip_path = make_export_zipfile_internal(project)  # returns Path to local zip
            dest_zip = unit_dir / "source.zip"
            dest_zip.write_bytes(Path(zip_path).read_bytes())

            meta = {
                "id": project.id,
                "title": project.title,
                "l2": project.l2,
                "l1": project.l1,
                "owner_username": project.user.username if project.user else None,
                "size_bytes": dest_zip.stat().st_size,
                "sha256": _sha256(dest_zip),
            }
            (unit_dir / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
            index.append(meta)

            done += 1
            post_task_update(callback, f"[{done}/{total}] exported {project.id} “{project.title}”")
        except Exception as e:
            failures.append({"project_id": project.id, "error": str(e)})
            post_task_update(callback, f"error exporting {project.id}: {e}\n{traceback.format_exc()}")

    (out_root / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2))
    (out_root / "failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2))
    if failures:
        post_task_update(callback, f"{len(failures)} failures")
        post_task_update(callback, "error")
    else:
        post_task_update(callback, "finished")

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def bulk_source_exports_monitor(request, report_id):
    return render(request, "clara_app/bulk_source_exports_monitor.html", {"report_id": report_id})

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def bulk_source_exports_status(request, report_id):
    msgs = get_task_updates(report_id)
    status = "error" if any("error" in m.lower() for m in msgs) else ("finished" if any("finished" in m.lower() for m in msgs) else "unknown")
    return JsonResponse({"messages": msgs, "status": status})

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def bulk_source_exports_complete(request, result):
    """
    Summarise what was written to $CLARA/tmp/bulk_source_exports:
      - successes: projects with both metadata.json and source.zip
      - failures: from failures.json if present
    """
    out_root = Path(os.environ.get("CLARA", "")) / "tmp" / "bulk_source_exports"
    successes = []
    failures = []
    total_units = 0

    if out_root.exists():
      for d in sorted(out_root.iterdir(), key=lambda p: p.name):
          if not d.is_dir():
              continue
          total_units += 1
          meta_p = d / "metadata.json"
          zip_p  = d / "source.zip"
          if meta_p.exists() and zip_p.exists():
              try:
                  meta = json.loads(meta_p.read_text(encoding="utf-8"))
                  successes.append(meta)
              except Exception:
                  # malformed metadata — treat as failure
                  failures.append({"project_id": d.name, "error": "malformed metadata.json"})
          else:
              failures.append({"project_id": d.name, "error": "missing source.zip or metadata.json"})

      # task-level failures file (e.g., exceptions)
      fail_file = out_root / "failures.json"
      if fail_file.exists():
          try:
              extra = json.loads(fail_file.read_text(encoding="utf-8"))
              # add only entries that aren’t already counted
              known = {str(f["project_id"]) for f in failures}
              for f in extra:
                  if str(f.get("project_id")) not in known:
                      failures.append(f)
          except Exception:
              failures.append({"project_id": None, "error": "malformed failures.json"})

    ctx = {
        "result": result,
        "out_root": str(out_root),
        "total_units": total_units,
        "success_count": len(successes),
        "failure_count": len(failures),
        "successes": successes[:30],  # show a sample; keep page light
        "failures": failures[:30],    # show a sample
        "has_more_successes": len(successes) > 30,
        "has_more_failures": len(failures) > 30,
    }
    return render(request, "clara_app/bulk_source_exports_complete.html", ctx)

# ------------------------------------------
# Bulk export of audio

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def start_bulk_audio_export(request):
    if request.method == "POST":
        form = BulkAudioExportForm(request.POST)
        if form.is_valid():
            callback, report_id = make_asynch_callback_and_report_id(request, "bulk_audio_exports")
            params = form.cleaned_data
            async_task(export_all_audio_task, params, callback)
            return redirect("bulk_audio_export_monitor", report_id=report_id)
    else:
        form = BulkAudioExportForm()
    return render(request, "clara_app/bulk_audio_export_start.html", {"form": form})

def export_all_audio_task(params, callback):
    out_root = Path( absolute_file_name("$CLARA/tmp/bulk_audio_exports") )
    out_root.mkdir(parents=True, exist_ok=True)

    if params.get("empty_dest_first"):
        _clear_dir(out_root)
        post_task_update(callback, f"Cleared existing contents in {out_root}")

    # filters
    engine_id = params.get("engine_id").strip() or None
    language_id = params.get("language_id").strip() or None
    voice_id = params.get("voice_id").strip() or None

    repo = AudioRepositoryORM(callback=callback)  # base_dir_orm resolved here
    base_dir = Path(repo.base_dir)

    post_task_update(callback, f"Starting bulk audio export {base_dir} → {out_root}")

    q = AudioMetadata.objects.all()
    if engine_id:   q = q.filter(engine_id=engine_id)
    if language_id: q = q.filter(language_id=language_id)
    if voice_id:    q = q.filter(voice_id=voice_id)

    total = q.count()
    post_task_update(callback, f"Found {total} audio metadata rows to process")

    # group by engine/language/voice
    triples = q.values_list("engine_id", "language_id", "voice_id").distinct()
    index = []
    failures = []
    processed = 0

    for eng, lang, voi in triples:
        rel_dir = Path(eng) / lang / voi
        dest_dir = out_root / rel_dir
        make_directory(str(dest_dir), parents=True, exist_ok=True)

        rows = q.filter(engine_id=eng, language_id=lang, voice_id=voi)
        count = 0
        bytes_ = 0
        manifest = {"engine_id": eng, "language_id": lang, "voice_id": voi, "items": []}

        post_task_update(callback, f"Exporting {eng}/{lang}/{voi} ({rows.count()} items)…")

        for r in rows.iterator():
            try:
                src = Path(absolute_file_name(r.file_path))
                if not src.exists():
                    failures.append({"engine_id": eng, "language_id": lang, "voice_id": voi,
                                     "text": r.text, "context": r.context,
                                     "error": "missing file", "file_path": r.file_path})
                    continue
                dst = dest_dir / src.name  # keep filename
                if not dst.exists():
                    shutil.copy2(src, dst)
                item = {
                    "text": r.text,
                    "context": r.context,
                    "file": dst.name,
                    "size": dst.stat().st_size,
                    "sha256": _sha256(dst),
                }
                manifest["items"].append(item)
                count += 1
                bytes_ += item["size"]

                processed += 1
                if processed % 500 == 0:
                    post_task_update(callback, f"…{processed}/{total} entries done")

            except Exception as e:
                failures.append({"engine_id": eng, "language_id": lang, "voice_id": voi,
                                 "text": r.text, "context": r.context, "error": str(e)})

        manifest_path = dest_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

        index.append({
            "engine_id": eng, "language_id": lang, "voice_id": voi,
            "count": count, "bytes": bytes_,
            "dir": str(rel_dir),
        })

    (out_root / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2))
    if failures:
        (out_root / "failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2))
        post_task_update(callback, f"finished with {len(failures)} errors")
    else:
        post_task_update(callback, "finished")

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def bulk_audio_export_monitor(request, report_id):
    return render(request, "clara_app/bulk_audio_export_monitor.html", {"report_id": report_id})

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def bulk_audio_export_status(request, report_id):
    msgs = get_task_updates(report_id)
    status = "error" if any("error" in m.lower() for m in msgs) else ("finished" if any("finished" in m.lower() for m in msgs) else "unknown")
    return JsonResponse({"messages": msgs, "status": status})

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def bulk_audio_export_complete(request, result):
    out_root = Path(os.environ.get("CLARA", "")) / "tmp" / "bulk_audio_exports"  # <-- audio, not source
    index_path = out_root / "index.json"
    fails_path = out_root / "failures.json"

    index = json.loads(index_path.read_text()) if index_path.exists() else []
    failures = json.loads(fails_path.read_text()) if fails_path.exists() else []

    counts = {
        "voices": len({(m.get("engine_id"), m.get("language_id"), m.get("voice_id")) for m in index}),
        "items": sum(int(m.get("count", 0)) for m in index),
        "bytes": sum(int(m.get("bytes", 0)) for m in index),
        "failures": len(failures),
    }

    return render(request, "clara_app/bulk_audio_export_complete.html", {
        "out_root": str(out_root),
        "voices_count": counts["voices"],
        "items_count": counts["items"],
        "bytes_count": counts["bytes"],
        "failure_count": counts["failures"],
        "failures": failures[:50],  # peek
        "has_more_failures": len(failures) > 50,
        "result": result,  # keep if you also show a simple status
    })

# ------------------------------------------

def _clear_dir(root: Path) -> None:
    """Delete only the contents of `root`, not the directory itself."""
    for child in root.iterdir():
        try:
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        except Exception:
            # best effort; leave a note in failures.json if needed
            pass

def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

