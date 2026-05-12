import json
import shutil
import traceback
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from clara_app.clara_export_import import make_export_zipfile_internal
from clara_app.create_project_views import create_CLARAProjectInternal_from_zipfile
from clara_app.models import CLARAProject, HumanAudioInfo, PhoneticHumanAudioInfo
from clara_app.utils import create_internal_project_id

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Convert a folder of legacy C-LARA project export bundles into a matching "
        "folder of JSON-format export bundles."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "source_root",
            help="Folder containing one subfolder per project. Each project subfolder must contain one .zip and one .json metadata file.",
        )
        parser.add_argument(
            "dest_root",
            help="Destination folder to create. It will contain matching project subfolders with JSON-format zips and copied metadata.",
        )
        parser.add_argument(
            "--username",
            default=None,
            help="Django username to own the temporary imported projects. Defaults to the first superuser, then staff user, then any user.",
        )
        parser.add_argument(
            "--existing",
            choices=["skip", "overwrite", "error"],
            default="skip",
            help="What to do when an output project subfolder already exists (default: skip).",
        )
        parser.add_argument(
            "--keep-imported-projects",
            action="store_true",
            help="Keep temporary CLARAProject database rows after conversion. By default they are deleted after each project is exported.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report which project folders would be converted without importing or writing bundles.",
        )

    def handle(self, *args, **options):
        source_root = Path(options["source_root"]).expanduser().resolve()
        dest_root = Path(options["dest_root"]).expanduser().resolve()

        if not source_root.is_dir():
            raise CommandError(f"Source root is not a directory: {source_root}")
        if source_root == dest_root:
            raise CommandError("Source and destination roots must be different directories")

        owner = self._owner_user(options["username"])
        existing = options["existing"]
        dry_run = options["dry_run"]
        keep_imported_projects = options["keep_imported_projects"]

        project_dirs = [path for path in sorted(source_root.iterdir()) if path.is_dir()]
        if not project_dirs:
            raise CommandError(f"No project subdirectories found under {source_root}")

        if not dry_run:
            dest_root.mkdir(parents=True, exist_ok=True)

        successes = []
        failures = []
        skipped = []

        self.stdout.write(self.style.NOTICE(f"Source root: {source_root}"))
        self.stdout.write(self.style.NOTICE(f"Destination root: {dest_root}"))
        self.stdout.write(self.style.NOTICE(f"Project folders found: {len(project_dirs)}"))
        self.stdout.write(self.style.NOTICE(f"Temporary project owner: {owner.username}"))

        for source_project_dir in project_dirs:
            try:
                zip_path, metadata_path = self._input_files(source_project_dir)
                dest_project_dir = dest_root / source_project_dir.name
                dest_zip_path = dest_project_dir / zip_path.name
                dest_metadata_path = dest_project_dir / metadata_path.name

                if dest_project_dir.exists():
                    if existing == "skip":
                        self.stdout.write(f"- skip existing output: {dest_project_dir}")
                        skipped.append(source_project_dir.name)
                        continue
                    if existing == "error":
                        raise CommandError(f"Output project directory already exists: {dest_project_dir}")
                    if not dry_run:
                        shutil.rmtree(dest_project_dir)

                self.stdout.write(f"- convert {source_project_dir.name}: {zip_path.name} -> {dest_zip_path}")
                if dry_run:
                    successes.append(source_project_dir.name)
                    continue

                dest_project_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(metadata_path, dest_metadata_path)
                self._convert_one_project(zip_path, metadata_path, dest_zip_path, owner, keep_imported_projects)
                successes.append(source_project_dir.name)

            except Exception as e:
                message = f"{type(e).__name__}: {e}"
                self.stderr.write(self.style.ERROR(f"  ERROR {source_project_dir.name}: {message}"))
                failures.append({
                    "project_dir": source_project_dir.name,
                    "error": message,
                    "traceback": traceback.format_exc(),
                })

        if not dry_run:
            (dest_root / "conversion_index.json").write_text(
                json.dumps({
                    "source_root": str(source_root),
                    "dest_root": str(dest_root),
                    "converted": successes,
                    "skipped": skipped,
                    "failures": failures,
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        self.stdout.write(self.style.SUCCESS(
            f"Done. converted={len(successes)} skipped={len(skipped)} failures={len(failures)}"
        ))
        if failures:
            raise CommandError(f"{len(failures)} project(s) failed; see conversion_index.json in {dest_root}")

    def _owner_user(self, username):
        if username:
            try:
                return User.objects.get(username=username)
            except User.DoesNotExist as e:
                raise CommandError(f"No Django user found with username '{username}'") from e

        user = User.objects.filter(is_superuser=True).order_by("id").first()
        if not user:
            user = User.objects.filter(is_staff=True).order_by("id").first()
        if not user:
            user = User.objects.order_by("id").first()
        if not user:
            raise CommandError("No Django users exist. Create a user first or pass --username.")
        return user

    def _input_files(self, source_project_dir):
        zip_files = sorted(source_project_dir.glob("*.zip"))
        json_files = sorted(source_project_dir.glob("*.json"))

        if len(zip_files) != 1:
            raise CommandError(f"Expected exactly one .zip file in {source_project_dir}, found {len(zip_files)}")
        if len(json_files) != 1:
            raise CommandError(f"Expected exactly one .json metadata file in {source_project_dir}, found {len(json_files)}")
        return zip_files[0], json_files[0]

    def _convert_one_project(self, zip_path, metadata_path, dest_zip_path, owner, keep_imported_project):
        metadata = self._read_metadata(metadata_path)
        title = (metadata.get("title") or zip_path.stem or "Imported C-LARA project")[:200]
        l1 = metadata.get("l1") or "english"
        l2 = metadata.get("l2") or "english"

        clara_project = CLARAProject.objects.create(
            title=title,
            internal_id="",
            user=owner,
            l1=l1,
            l2=l2,
        )
        clara_project.internal_id = create_internal_project_id(title, clara_project.id)
        clara_project.save()

        try:
            clara_project_internal, global_metadata = create_CLARAProjectInternal_from_zipfile(
                str(zip_path), clara_project.internal_id, callback=None
            )
            if clara_project_internal is None:
                raise CommandError(f"Unable to import legacy bundle {zip_path}")

            self._update_project_from_import(clara_project, clara_project_internal, global_metadata)
            exported_zip_path = Path(make_export_zipfile_internal(clara_project, export_format="json", callback=None))
            if not exported_zip_path.exists():
                raise FileNotFoundError(f"JSON-format export zip was not created: {exported_zip_path}")
            shutil.copy2(exported_zip_path, dest_zip_path)
        finally:
            if not keep_imported_project:
                clara_project.delete()

    def _read_metadata(self, metadata_path):
        try:
            return json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _update_project_from_import(self, clara_project, clara_project_internal, global_metadata):
        clara_project.l1 = clara_project_internal.l1_language
        clara_project.l2 = clara_project_internal.l2_language

        if global_metadata and isinstance(global_metadata, dict):
            for field_name in [
                "simple_clara_type",
                "uses_coherent_image_set",
                "uses_coherent_image_set_v2",
                "use_translation_for_images",
                "uses_picture_glossing",
                "picture_gloss_style",
            ]:
                if field_name in global_metadata:
                    setattr(clara_project, field_name, global_metadata[field_name])

            if global_metadata.get("human_voice_id"):
                human_audio_info, _ = HumanAudioInfo.objects.get_or_create(project=clara_project)
                human_audio_info.voice_talent_id = global_metadata["human_voice_id"]
                human_audio_info.use_for_words = global_metadata.get("audio_type_for_words") == "human"
                human_audio_info.use_for_segments = global_metadata.get("audio_type_for_segments") == "human"
                human_audio_info.save()

            if global_metadata.get("human_voice_id_phonetic"):
                phonetic_human_audio_info, _ = PhoneticHumanAudioInfo.objects.get_or_create(project=clara_project)
                phonetic_human_audio_info.voice_talent_id = global_metadata["human_voice_id_phonetic"]
                phonetic_human_audio_info.use_for_words = True
                phonetic_human_audio_info.save()

        clara_project.save()
