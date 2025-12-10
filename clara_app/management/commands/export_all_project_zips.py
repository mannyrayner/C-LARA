import hashlib
import json
import os
import time
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.contrib.auth import get_user_model

from clara_app.models import (
    CLARAProject,
    HumanAudioInfo,
    PhoneticHumanAudioInfo,
    ProjectPermissions,  # <- ensure this import path matches your models layout
)
from clara_app.clara_main import CLARAProjectInternal

User = get_user_model()

class Command(BaseCommand):
    help = "Export an 'all projects' set of C-LARA source zipfiles to $CLARA/tmp/all_exports/..."

    def add_arguments(self, parser):
        parser.add_argument("--dest", default=None, help="Destination root (default: $CLARA/tmp/all_exports)")
        parser.add_argument("--only", default="", help="Comma-separated list of project IDs (or empty for all)")
        parser.add_argument("--skip", default="", help="Comma-separated list of project IDs to skip")
        parser.add_argument("--existing", choices=["skip", "overwrite"], default="skip",
                            help="What to do if a project export already exists (default: skip)")
        parser.add_argument("--checksums", action="store_true", help="Compute sha256 for each zip")
        parser.add_argument("--dry-run", action="store_true", help="List what would be exported and exit")

    def handle(self, *args, **opts):
        # --- Source CLARA root from the environment (hard fail if missing) ---
        clara_env = os.environ.get("CLARA")
        if not clara_env:
            raise SystemExit("ERROR: $CLARA env var is not set. Export CLARA=/abs/path/to/C-LARA first.")
        clara_root = Path(clara_env).resolve()

        dest_root = Path(opts["dest"] or (clara_root / "tmp" / "all_exports")).resolve()
        dest_root.mkdir(parents=True, exist_ok=True)

        only = {x.strip() for x in opts["only"].split(",") if x.strip()}
        skip = {x.strip() for x in opts["skip"].split(",") if x.strip()}
        existing = opts["existing"]
        do_checksums = opts["checksums"]
        dry = opts["dry_run"]

        # Pull projects; bring owner inline, and prefetch permissions in one round-trip
        qs = (
            CLARAProject.objects
            .select_related("user")
            .order_by("id")
        )
        if only:
            qs = qs.filter(id__in=[int(x) for x in only if x.isdigit()])

        # Prefetch permissions (users + roles) to avoid N+1
        # (If your ProjectPermissions model lives elsewhere, adjust the path.)
        perms_by_project = self._prefetch_permissions(qs)

        index = []
        failures = []

        self.stdout.write(self.style.NOTICE(f"Export root: {dest_root}"))
        self.stdout.write(self.style.NOTICE(f"Projects to process: {qs.count()}"))

        for project in qs:
            if str(project.id) in skip:
                self.stdout.write(f"- skip project {project.id} ({project.title}) [in --skip]")
                continue

            pid = project.id
            slug = slugify(project.title or f"project-{pid}") or f"project-{pid}"
            proj_dir = dest_root / f"{pid}_{slug}"
            zip_path = proj_dir / "source.zip"
            meta_path = proj_dir / "metadata.json"

            if existing == "skip" and zip_path.exists():
                self.stdout.write(f"- exists, skipping: {zip_path}")
                index.append({
                    "project_id": pid,
                    "title": project.title,
                    "path": str(zip_path),
                    "size_bytes": zip_path.stat().st_size,
                    "sha256": self._sha256(zip_path) if do_checksums else None,
                })
                continue

            # Owner info (safe-guard for nulls)
            owner = getattr(project, "user", None)
            owner_meta = self._user_meta(owner)

            # Resolve audio flags (match view behavior)
            human_audio = HumanAudioInfo.objects.filter(project=project).first()
            human_audio_ph = PhoneticHumanAudioInfo.objects.filter(project=project).first()

            if human_audio and human_audio.voice_talent_id:
                human_voice_id = human_audio.voice_talent_id
                at_words = "human" if human_audio.use_for_words else "tts"
                at_segs = "human" if human_audio.use_for_segments else "tts"
            else:
                human_voice_id = None
                at_words = "tts"
                at_segs = "tts"

            human_voice_id_ph = human_audio_ph.voice_talent_id if (human_audio_ph and human_audio_ph.voice_talent_id) else None

            # Permissions for this project (from prefetch map)
            project_perms = [
                {
                    "user": self._user_meta(pp.user),
                    "role": pp.role,
                }
                for pp in perms_by_project.get(pid, [])
            ]

            self.stdout.write(f"- export project {pid} ({project.title}) -> {proj_dir}")
            if dry:
                index.append({"project_id": pid, "title": project.title, "path": str(zip_path)})
                continue

            proj_dir.mkdir(parents=True, exist_ok=True)

            try:
                cpi = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
                # Create the same export as the web flow (writes into $CLARA/tmp/<title>_<id>_zipfile.zip)
                cpi.create_export_zipfile(
                    simple_clara_type=project.simple_clara_type,
                    uses_coherent_image_set=project.uses_coherent_image_set,
                    uses_coherent_image_set_v2=project.uses_coherent_image_set_v2,
                    use_translation_for_images=project.use_translation_for_images,
                    human_voice_id=human_voice_id,
                    human_voice_id_phonetic=human_voice_id_ph,
                    audio_type_for_words=at_words,
                    audio_type_for_segments=at_segs,
                    callback=None,
                )

                export_src = Path(cpi.export_zipfile_pathname())
                if not export_src.exists():
                    raise FileNotFoundError(f"Expected export zip not found: {export_src}")

                if zip_path.exists() and existing == "overwrite":
                    zip_path.unlink()
                export_src.replace(zip_path)

                sha = self._sha256(zip_path) if do_checksums else None

                meta = {
                    "project_id": pid,
                    "title": project.title,
                    "l1": getattr(project, "l1", None),
                    "l2": getattr(project, "l2", None),
                    "owner": owner_meta,
                    "permissions": project_perms,   # <- all user/role entries for this project
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "size_bytes": zip_path.stat().st_size,
                    "sha256": sha,
                }
                meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

                index.append({
                    "project_id": pid,
                    "title": project.title,
                    "path": str(zip_path),
                    "size_bytes": meta["size_bytes"],
                    "sha256": sha,
                })

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  ERROR {pid} {project.title}: {e}"))
                failures.append({"project_id": pid, "title": project.title, "error": str(e)})
                continue

        (dest_root / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        if failures:
            (dest_root / "failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"Done. Exported {len(index)} projects; failures={len(failures)}"))
        self.stdout.write(self.style.NOTICE(f"Output root: {dest_root}"))

    # ---------- helpers ----------

    def _sha256(self, p: Path) -> str:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _user_meta(self, u: User | None) -> dict | None:
        if not u:
            return None
        # include stable identifiers useful for recreation on a new host
        return {
            "id": getattr(u, "id", None),
            "username": getattr(u, "username", None),
            "email": getattr(u, "email", None),
            "first_name": getattr(u, "first_name", None),
            "last_name": getattr(u, "last_name", None),
            "is_active": getattr(u, "is_active", None),
            "is_staff": getattr(u, "is_staff", None),
            "is_superuser": getattr(u, "is_superuser", None),
        }

    def _prefetch_permissions(self, projects_qs):
        """Return a dict: {project_id: [ProjectPermissions, ...]}."""
        project_ids = list(projects_qs.values_list("id", flat=True))
        if not project_ids:
            return {}
        perms = (
            ProjectPermissions.objects
            .filter(project_id__in=project_ids)
            .select_related("user", "project")
        )
        by_pid = {}
        for pp in perms:
            by_pid.setdefault(pp.project_id, []).append(pp)
        return by_pid
