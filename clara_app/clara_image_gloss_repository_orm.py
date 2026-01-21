"""
clara_image_gloss_repository_orm.py

Repository for image gloss assets.

Stores metadata in Django ORM (ImageGlossMetadata) and stores the actual image files
in a repository folder on disk (base_dir_orm), analogous to clara_audio_repository_orm.py.

Key idea:
- Images are keyed by (language_id, style_id, lemma, lemma_gloss, status)
- The "approved" image is what we use during picture-gloss annotation/rendering.

The repository supports:
- add/update metadata entries
- store image files under base_dir_orm
- get single entries / batch lookup
- delete entries for a language (and optionally style)
- import/export bulk metadata

"""

from django.db.models import Q

from .models import ImageGlossMetadata
from .clara_classes import InternalCLARAError

from .clara_utils import (
    get_config,
    absolute_file_name,
    local_file_exists,
    copy_local_file,
    make_directory,
    remove_directory,
    directory_exists,
    list_files_in_directory,
    post_task_update,
    generate_unique_file_path,
)

import traceback
from pathlib import Path
import hashlib


class ImageGlossRepositoryORM:
    def __init__(self, callback=None):
        """
        Initialise the repository. Creates base directory if needed.
        """
        config = get_config()
        self.base_dir = absolute_file_name(config.get('image_gloss_repository', 'base_dir_orm'))

        if not directory_exists(self.base_dir):
            make_directory(self.base_dir, parents=True, exist_ok=True)
            post_task_update(callback, f'--- Created base directory for image gloss repository, {self.base_dir}')

    # ---------------------------
    # Deletion
    # ---------------------------

    def delete_entries_for_language(self, language_id, style_id=None, callback=None):
        """
        Delete DB entries and associated files for the given language.
        If style_id is provided, restrict deletion to that style.
        """
        try:
            qs = ImageGlossMetadata.objects.filter(language_id=language_id)
            if style_id is not None:
                qs = qs.filter(style_id=style_id)

            deleted = qs.delete()
            post_task_update(callback, f'--- Deleted {deleted[0]} image gloss metadata entries for language {language_id}'
                                      + (f' and style {style_id}' if style_id else ''))

            # Delete files on disk
            if style_id:
                style_dir = self.get_style_directory(language_id, style_id)
                if directory_exists(style_dir):
                    remove_directory(style_dir)
                    post_task_update(callback, f'--- Deleted image gloss files under {style_dir}')
            else:
                lang_dir = self.get_language_directory(language_id)
                if directory_exists(lang_dir):
                    remove_directory(lang_dir)
                    post_task_update(callback, f'--- Deleted image gloss files under {lang_dir}')

            post_task_update(callback, 'Finished deletion process successfully.')

        except Exception as e:
            error_message = (
                f'*** Error when trying to delete image gloss entries for language {language_id}'
                + (f' style {style_id}' if style_id else '')
                + f': "{str(e)}"\n{traceback.format_exc()}'
            )
            post_task_update(callback, error_message)

    # ---------------------------
    # Add/update metadata
    # ---------------------------

    def add_or_update_entry(
        self,
        language_id,
        lemma,
        style_id,
        file_path,
        lemma_gloss='',
        status='proposed',
        is_mwe=False,
        example_context='',
        callback=None
    ):
        """
        Upsert a metadata entry.

        Note: for V1 speed we allow update_or_create on the full key (including status).
        This means you can have multiple rows for different statuses; and multiple candidates
        can be represented by different file_path values across calls.

        If you decide later you want multiple candidates per key, we can switch to create-only
        and add a separate "approved pointer" mechanism.
        """
        try:
            obj, created = ImageGlossMetadata.objects.update_or_create(
                language_id=language_id,
                style_id=style_id,
                lemma=lemma,
                lemma_gloss=lemma_gloss or '',
                status=status,
                defaults={
                    'file_path': file_path,
                    'is_mwe': bool(is_mwe),
                    'example_context': example_context or '',
                }
            )

            if created:
                post_task_update(callback, f'--- Inserted new image gloss metadata for {language_id} {lemma[:50]}')
            else:
                post_task_update(callback, f'--- Updated image gloss metadata for {language_id} {lemma[:50]}')

            return obj

        except Exception as e:
            error_message = (
                f'*** Error when trying to add/update image gloss metadata for {language_id} {lemma[:50]}: '
                f'"{str(e)}"\n{traceback.format_exc()}'
            )
            post_task_update(callback, error_message)
            raise

    # ---------------------------
    # Store image file
    # ---------------------------

    def store_image(
        self,
        local_image_file,
        language_id,
        style_id,
        lemma,
        lemma_gloss='',
        callback=None
    ):
        """
        Copy a local image file into the repository and return the stored path.

        We store under:
            base_dir / language_id / style_id / <bucket>/<slug>/filename.ext

        Where bucket is a short hash prefix to keep directories small.
        """
        if not local_file_exists(local_image_file):
            raise InternalCLARAError(f'Local image file not found: {local_image_file}')

        ext = Path(local_image_file).suffix.lower()
        if ext not in ['.png', '.jpg', '.jpeg', '.webp']:
            # allow, but default to .png-ish behaviour
            post_task_update(callback, f'--- Warning: unusual image extension "{ext}" for {local_image_file}')

        lemma_dir = self.get_lemma_directory(language_id, style_id, lemma, lemma_gloss)
        if not directory_exists(lemma_dir):
            make_directory(lemma_dir, parents=True, exist_ok=True)

        # Use a stable-ish base name, then uniquify
        base = self._safe_slug(f'{lemma}-{lemma_gloss}'.strip('-')) or 'lemma'
        dest_file = generate_unique_file_path(lemma_dir, base, ext)

        copy_local_file(local_image_file, dest_file)
        post_task_update(callback, f'--- Stored image gloss file: {dest_file}')

        return dest_file

    # ---------------------------
    # Lookup
    # ---------------------------

    def get_entry(self, language_id, lemma, style_id, lemma_gloss='', status='approved'):
        """
        Return the file_path for the matching entry, or None.
        """
        qs = ImageGlossMetadata.objects.filter(
            language_id=language_id,
            style_id=style_id,
            lemma=lemma,
            lemma_gloss=lemma_gloss or '',
        )
        if status:
            qs = qs.filter(status=status)

        obj = qs.order_by('-updated_at').first()
        return obj.file_path if obj else None

    def get_entry_batch(self, language_id, lemmas, style_id, lemma_glosses=None, status='approved'):
        """
        Batch lookup: returns a dict mapping (lemma, lemma_gloss) -> file_path (or None if missing).

        If lemma_glosses is None, uses '' for all.
        """
        if not lemmas:
            return {}

        if lemma_glosses is None:
            lemma_glosses = [''] * len(lemmas)
        if len(lemma_glosses) != len(lemmas):
            raise InternalCLARAError('get_entry_batch: lemma_glosses length must match lemmas length')

        wanted_pairs = {(lemmas[i], lemma_glosses[i] or '') for i in range(len(lemmas))}

        # If all lemma_glosses are empty, we can do a simpler query
        all_empty = all((d or '') == '' for d in lemma_glosses)

        qs = ImageGlossMetadata.objects.filter(language_id=language_id, style_id=style_id)
        if status:
            qs = qs.filter(status=status)

        if all_empty:
            qs = qs.filter(lemma__in=lemmas, lemma_gloss='')
        else:
            # Build OR query over (lemma, lemma_gloss)
            q = Q()
            for (lemma, lemma_gloss) in wanted_pairs:
                q |= Q(lemma=lemma, lemma_gloss=lemma_gloss)
            qs = qs.filter(q)

        # Prefer the most recently updated entry when duplicates exist
        qs = qs.order_by('lemma', 'lemma_gloss', '-updated_at')

        result = {(lemma, lemma_gloss): None for (lemma, lemma_gloss) in wanted_pairs}
        seen = set()

        for obj in qs:
            key = (obj.lemma, obj.lemma_gloss or '')
            if key in result and key not in seen:
                result[key] = obj.file_path
                seen.add(key)

        return result

    # ---------------------------
    # Export / Import (bulk primitives)
    # ---------------------------

    def export_image_gloss_metadata(self, language_id=None, style_id=None, status=None):
        """
        Export metadata rows as a list of dicts. File paths are included as stored.
        """
        qs = ImageGlossMetadata.objects.all()
        if language_id:
            qs = qs.filter(language_id=language_id)
        if style_id:
            qs = qs.filter(style_id=style_id)
        if status:
            qs = qs.filter(status=status)

        out = []
        for obj in qs.iterator():
            out.append({
                'language_id': obj.language_id,
                'style_id': obj.style_id,
                'lemma': obj.lemma,
                'lemma_gloss': obj.lemma_gloss or '',
                'status': obj.status,
                'is_mwe': obj.is_mwe,
                'example_context': obj.example_context or '',
                'file_path': obj.file_path,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
        return out

    def import_image_gloss_metadata(self, items, callback=None):
        """
        Import metadata items previously exported.
        This does NOT copy image files; it assumes file_path is valid in the target environment.
        (If we need to support copying directories across machines, we can add that later.)
        """
        try:
            count = 0
            for it in items:
                self.add_or_update_entry(
                    language_id=it['language_id'],
                    lemma=it['lemma'],
                    style_id=it['style_id'],
                    file_path=it['file_path'],
                    lemma_gloss=it.get('lemma_gloss', ''),
                    status=it.get('status', 'proposed'),
                    is_mwe=it.get('is_mwe', False),
                    example_context=it.get('example_context', ''),
                    callback=callback
                )
                count += 1
            post_task_update(callback, f'--- Imported {count} image gloss metadata entries')
        except Exception as e:
            error_message = f'*** Error during import_image_gloss_metadata: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise

    # ---------------------------
    # Directory helpers
    # ---------------------------

    def get_language_directory(self, language_id):
        return str(Path(self.base_dir) / language_id)

    def get_style_directory(self, language_id, style_id):
        return str(Path(self.base_dir) / language_id / style_id)

    def get_lemma_directory(self, language_id, style_id, lemma, lemma_gloss=''):
        """
        Create a stable directory location for lemma assets, using a small hash bucket.

        This keeps directory sizes reasonable even with many entries.
        """
        style_dir = Path(self.get_style_directory(language_id, style_id))
        key = f'{lemma}||{lemma_gloss or ""}'
        h = hashlib.md5(key.encode('utf-8')).hexdigest()
        bucket = h[:2]
        slug = self._safe_slug(lemma)[:64] or 'lemma'
        return str(style_dir / bucket / slug)

    def _safe_slug(self, s):
        """
        Convert a string to a filesystem-safe slug.
        """
        if s is None:
            return ''
        s = s.strip().lower()
        # Replace path separators and other awkward characters
        bad = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\n', '\r', '\t']
        for ch in bad:
            s = s.replace(ch, ' ')
        # Collapse spaces and keep a conservative set
        s = '_'.join(s.split())
        s = ''.join([c for c in s if (c.isalnum() or c in ['_', '-', '.'])])
        return s
