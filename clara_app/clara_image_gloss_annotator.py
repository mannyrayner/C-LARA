"""
clara_image_gloss_annotator.py

Image gloss annotator for C-LARA.

This module annotates Words/MWEs with picture-gloss references (image popups),
based on approved entries in the ImageGlossRepositoryORM.

Unlike audio:
- We ONLY create image glosses for words/MWEs (not segments/pages).
- We do NOT generate missing images here; instead we collect missing entries
  so they can be queued into the persistent image dictionary project for
  subsequent generation/review.

Key:
- Images are keyed by (language_id, style_id, lemma, lemma_gloss, status='approved').

"""

from .clara_classes import InternalCLARAError
from .clara_utils import (
    post_task_update,
    remove_duplicates_general,
    absolute_file_name,
)
from .clara_image_gloss_repository_orm import ImageGlossRepositoryORM

from .models import ImageGlossMetadata

import traceback


class ImageGlossAnnotator:
    def __init__(
        self,
        l2_language_id,
        style_id,
        lemma_gloss_resolver=None,
        callback=None
    ):
        """
        l2_language_id: language for the text being annotated (the L2 text language)
        style_id: coherent image style id for dictionary images
        lemma_gloss_resolver: optional callable to compute canonical lemma gloss for a lemma.
            Signature:
                resolver(lemma: str, example_contexts: list[str]) -> str
            For V1 Option B, this will call an AI API and should be cached externally.
            If None, we fall back to '' which means "no disambiguation".
        """
        self.language_id = l2_language_id
        self.style_id = style_id
        self.image_repository = ImageGlossRepositoryORM(callback=callback)
        self.lemma_gloss_resolver = lemma_gloss_resolver
        post_task_update(callback, f"--- Using ImageGlossAnnotator(language_id={self.language_id}, style_id={self.style_id})")

    def annotate_text(self, text_obj, callback=None):
        """
        Annotate a Text object in-place.

        Returns a list of "missing entries" dicts, each of which can be used
        to add pages to the persistent image dictionary project:
            {
              'lemma': ...,
              'is_mwe': bool,
              'lemma_gloss': ...,
              'example_context': ...,
            }
        """
        try:
            post_task_update(callback, f"--- Collecting word/MWE items for image glossing")
            post_task_update(callback, f"--- Text object = {text_obj}")

            items = self._collect_word_mwe_items(text_obj, callback=callback)

            # Resolve lemma_gloss for each item (Option B hook)
            self._fill_lemma_glosses(items, callback=callback)

            # Batch lookup approved image paths
            image_meta_data_dict = self.image_repository.get_entry_batch(
                language_id=self.language_id,
                lemmas=[it['lemma'] for it in items],
                style_id=self.style_id,
                lemma_glosses=[it.get('lemma_gloss', '') for it in items],
                status='approved'
            )

            # Mark missing and attach annotations
            missing = self._add_image_gloss_annotations(text_obj, items, image_meta_data_dict, callback=callback)

            post_task_update(callback, "--- Image gloss annotation complete")
            return text_obj, missing

##        except Exception as e:
##            post_task_update(callback, f"*** Error in ImageGlossAnnotator.annotate_text: '{str(e)}'\n{traceback.format_exc()}")
##            return text_obj, []

        except Exception as e:
            msg = f"*** Error in ImageGlossAnnotator.annotate_text: '{str(e)}'\n{traceback.format_exc()}"
            post_task_update(callback, msg)
            raise

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------

    def _collect_word_mwe_items(self, text_obj, callback=None):
        """
        Walk through the text and collect candidate word/MWE items.
        We collect at the level we will annotate: Word content elements.
        If the Word has an MWE lemma, use that (one image for the MWE).
        """
        items = []
        # We also collect a few example contexts per lemma, to help the lemma_gloss resolver.
        contexts_by_lemma = {}

        for page in text_obj.pages:
            post_task_update(callback, f'Extracting word items from {page}')
            for segment in page.segments:
                segment_plain = segment.to_text()
                segment_ann = segment.annotations

                if not 'translated' in segment_ann:
                    post_task_update(callback, f'Skipping segment because no translation, {segment}')
                    continue
                else:
                    segment_translation = segment_ann.get('translated')

                for content_element in segment.content_elements:
                    if content_element.type != 'Word':
                        continue

                    ann = content_element.annotations

                    if not 'lemma' in ann or not 'gloss' in ann:
                        post_task_update(callback, f'Skipping content element because no lemma or gloss, {content_element}')
                        continue

                    # We assume lemma tagging has already run.
                    # Common patterns:
                    # - ann['lemma'] for ordinary tokens
                    # - ann['mwe_lemma'] (or similar) when token belongs to an MWE
                    # You may need to adjust these keys to match your lemma tagger.
                    lemma = ann.get('lemma') 
                    is_mwe = bool(len(lemma.split()) != 1)
                    gloss = ann.get('gloss') 

                    items.append({
                        'lemma': lemma,
                        'is_mwe': is_mwe,
                        'gloss': gloss,
                        'example_context': segment_plain,
                        'example_context_translation': segment_translation,
                        # lemma_gloss filled later
                    })

                    contexts_by_lemma.setdefault(lemma, [])
                    if len(contexts_by_lemma[lemma]) < 3:
                        contexts_by_lemma[lemma].append(segment_plain)

        post_task_update(callback, f'Found {len(items)} items before deduplication')

        # Deduplicate by lemma + is_mwe for repository lookup purposes.
        # Keep one example_context (first encountered).
        dedup = {}
        for it in items:
            key = (it['lemma'], it['is_mwe'])
            if key not in dedup:
                dedup[key] = it
        items = list(dedup.values())

        post_task_update(callback, f'Found {len(items)} items after deduplication')

        # Store contexts for resolver use
        self._contexts_by_lemma = contexts_by_lemma

        post_task_update(callback, f"--- Collected {len(items)} unique lemma items for image glossing")
        return items

    def _fill_lemma_glosses(self, items, callback=None):
        """
        Fill lemma_gloss for each item using:
        - existing text gloss annotation if present (only as a weak fallback), OR
        - resolver callable (Option B), OR
        - '' if nothing available.
        """
        if not self.lemma_gloss_resolver:
            # V1 fallback: no disambiguation
            for it in items:
                it['lemma_gloss'] = it.get('gloss', '') or ''
            return

        post_task_update(callback, "--- Resolving lemma_gloss values")
        for it in items:
            lemma = it['lemma']
            example_contexts = self._contexts_by_lemma.get(lemma, [])
            try:
                lemma_gloss = self.lemma_gloss_resolver(lemma, example_contexts)
                it['lemma_gloss'] = lemma_gloss or ''
            except Exception as e:
                post_task_update(callback, f"*** lemma_gloss_resolver failed for lemma '{lemma}': {str(e)}")
                it['lemma_gloss'] = ''

    def _add_image_gloss_annotations(self, text_obj, items, image_meta_data_dict, callback=None):
        """
        Attach image gloss annotations to the actual Word elements in the text.
        Also return a list of missing dictionary entries to queue.
        """
        # Build quick lookup
        wanted = {(it['lemma'], it.get('lemma_gloss', '') or ''): it for it in items}

        missing_entries = {}
        hits = 0

        for page in text_obj.pages:
            for segment in page.segments:
                for content_element in segment.content_elements:
                    if content_element.type != 'Word':
                        continue

                    ann = content_element.annotations
                    lemma = ann.get('mwe_lemma') or ann.get('lemma')
                    if not isinstance(lemma, str):
                        continue
                    pos = (ann.get('pos') or '').strip()
                    is_mwe = bool(len(lemma.split()) != 1)
                    
                    # Determine lemma_gloss for this lemma (use resolved canonical value if available)
                    # Note: for V1 we use the canonical lemma_gloss from `wanted` if present, else ''.
                    # Later: we may store lemma_gloss directly on lemma annotation output.
                    # Try both MWE and non-MWE keys.
                    lemma_gloss = ''
                    # Prefer entry matching lemma (ignore is_mwe for lookup)
                    for key in [(lemma, ''), *[(lemma, lg) for (lm, lg) in wanted.keys() if lm == lemma]]:
                        if key in wanted:
                            lemma_gloss = wanted[key].get('lemma_gloss', '') or ''
                            break

                    fp = image_meta_data_dict.get((lemma, lemma_gloss), None)

                    if fp:
                        # Store a structured annotation. Keep it analogous in spirit to audio's 'tts' dict.
                        # Renderer can later decide how to turn file_path into a served URL.
                        content_element.annotations['image_gloss'] = {
                            "language_id": self.language_id,
                            "style_id": self.style_id,
                            "lemma": lemma,
                            "lemma_gloss": lemma_gloss,
                            "file_path": fp,
                        }
                        hits += 1
                    else:
                        # Record missing entry (dedup)
                        k = (lemma, lemma_gloss, is_mwe, pos)
                        if k not in missing_entries:
                            missing_entries[k] = {
                                "lemma": lemma,
                                "is_mwe": is_mwe,
                                "lemma_gloss": lemma_gloss,
                                "pos": pos,
                                # Provide a sample context if we have one
                                "example_context": wanted.get((lemma, lemma_gloss), {}).get('example_context', '') if wanted else '',
                            }

        post_task_update(callback, f"--- Added image_gloss annotations for {hits} items")
        post_task_update(callback, f"--- Missing image gloss entries: {len(missing_entries)}")

        return list(missing_entries.values())
