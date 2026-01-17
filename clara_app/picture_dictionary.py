# clara_app/picture_dictionary.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
import re
import time

from django.contrib.auth.models import User
from django.db import transaction

from clara_app.models import CLARAProject, Community
from clara_app.clara_main import CLARAProjectInternal

# Adjust these imports to wherever the internal text classes live in your codebase
# (names based on your description).
from clara_app.clara_classes import Text, Page, Segment, ContentElement

from clara_app.clara_utils import post_task_update

DICT_INTERNAL_ID_PREFIX = "picture_dict"


@dataclass(frozen=True)
class PictureDictionaryKey:
    community_id: int
    l2: str
    l1: str
    style: str  # 'any' | 'children' | 'adults'


def _slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "x"


def dictionary_internal_id(key: PictureDictionaryKey) -> str:
    # Deterministic and stable: no dependence on project.id/title hashing
    return f"{DICT_INTERNAL_ID_PREFIX}__c{key.community_id}__l2_{_slug(key.l2)}__l1_{_slug(key.l1)}__style_{_slug(key.style)}"


def dictionary_title(key: PictureDictionaryKey, community_name: str) -> str:
    # Friendly but deterministic enough
    return f"[Picture Dictionary] {community_name} / {key.l2} → {key.l1} / {key.style}"


@dataclass
class PictureDictionaryEntry:
    lemma: str
    is_mwe: bool
    lemma_gloss: str  # may be empty in toy mode
    pos: str = ""     # optional, but we include it in dedupe key
    # Optional; not used in V1 dictionary text, but useful later:
    example_context: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "PictureDictionaryEntry":
        return cls(
            lemma=(d.get("lemma") or "").strip(),
            is_mwe=bool(d.get("is_mwe")),
            lemma_gloss=(d.get("lemma_gloss") or "").strip(),
            pos=(d.get("pos") or "").strip(),
            example_context=(d.get("example_context") or "").strip(),
        )

class PictureDictionary:
    """
    Thin orchestration layer over:
      - CLARAProject (DB row)
      - CLARAProjectInternal (filesystem-backed project)
    """

    def __init__(self, community: Community, l2: str, l1: str, style: str = "any") -> None:
        self.key = PictureDictionaryKey(
            community_id=community.id,
            l2=l2,
            l1=l1,
            style=style or "any",
        )
        self.community = community

    @transaction.atomic
    def get_or_create_project(self, owner_user: User) -> Tuple[CLARAProject, CLARAProjectInternal, bool]:
        """
        Returns (project, project_internal, created_bool).
        """
        internal_id = dictionary_internal_id(self.key)
        title = dictionary_title(self.key, self.community.name)

        proj = CLARAProject.objects.filter(internal_id=internal_id).first()
        created = False

        if proj is None:
            proj = CLARAProject(
                title=title,
                internal_id=internal_id,
                user=owner_user,
                l2=self.key.l2,
                l1=self.key.l1,
                uses_coherent_image_set=False,
                uses_coherent_image_set_v2=True,
                use_translation_for_images=False,
                uses_picture_glossing=False,  # dictionary project itself doesn't need this flag
                picture_gloss_style="",
                has_image_questionnaire=False,
                community=self.community,
            )
            proj.save()
            created = True
        else:
            # Ensure key invariants (harmless if already correct)
            changed = False
            if proj.community_id != self.community.id:
                proj.community = self.community
                changed = True
            if not proj.uses_coherent_image_set_v2:
                proj.uses_coherent_image_set_v2 = True
                changed = True
            if proj.uses_coherent_image_set:
                proj.uses_coherent_image_set = False
                changed = True
            if proj.use_translation_for_images:
                proj.use_translation_for_images = False
                changed = True
            if proj.title != title:
                proj.title = title
                changed = True
            if changed:
                proj.save()

        proj_internal = CLARAProjectInternal(internal_id, self.key.l2, self.key.l1)
        return proj, proj_internal, created

    def append_entries(
        self,
        proj_internal: CLARAProjectInternal,
        entries: Iterable[PictureDictionaryEntry],
        *,
        user_display_name: str = "Unknown",
        source: str = "human_revised",
        callback=None
    ) -> Dict[str, Any]:
        """
        Appends entries as new pages (one per entry) to the dictionary project.

        Returns dict with counts and keys.
        """
        # Load existing lemma text as authoritative internal representation.
        text_obj = self._load_or_create_text(proj_internal, version="lemma")

        existing_keys = self._existing_entry_keys(text_obj)

        to_add: List[PictureDictionaryEntry] = []
        skipped: List[Tuple[str, bool, str, str]] = []
                
        for e in entries:
            post_task_update(callback, f'Trying to add entry {e}')
            k = (e.lemma.strip(), bool(e.is_mwe), (e.lemma_gloss or "").strip(), (e.pos or "").strip())
            if not k[0]:
                continue
            if k in existing_keys:
                skipped.append(k)
            else:
                to_add.append(e)
                existing_keys.add(k) 

        # Append pages
        for e in to_add:
            page = self._make_page(e, callback)
            text_obj.pages.append(page)

        # Write all six versions
        versions = ["plain", "segmented", "mwe", "translated", "lemma", "gloss"]
        saved_versions: List[str] = []
        for v in versions:
            out_text = text_obj.to_text(annotation_type=("mwe_minimal" if v == "mwe" else v))
            out_text = out_text.strip()
            proj_internal.save_text_version(v, out_text, source=source, user=user_display_name)
            time.sleep(0.1) # Sleep briefly to avoid making it look like things might be out of date
            saved_versions.append(v)

        # Some code depends on having a title and a segmented title, so add this information too
##        for v in ( 'title', 'segmented_title' ):
##            out_text = 'title'
##            proj_internal.save_text_version(v, out_text, source=source, user=user_display_name)
##            saved_versions.append(v)

        return {
            "added": len(to_add),
            "skipped": len(skipped),
            "saved_versions": saved_versions,
            "added_keys": [(e.lemma, e.is_mwe, e.lemma_gloss, e.pos) for e in to_add],
        }

    # -----------------------
    # Internal helpers
    # -----------------------

    def _load_or_create_text(self, proj_internal: CLARAProjectInternal, version: str) -> Text:
        try:
            raw = proj_internal.load_text_version(version)
        except Exception:
            raw = ""

        raw = (raw or "").strip()
        if raw:
            return proj_internal.internalize_text(raw, version)

        return Text(
            pages=[],
            l2_language=proj_internal.l2_language,
            l1_language=proj_internal.l1_language,
            annotations={},
            voice=None,
        )

    def _existing_entry_keys(self, text_obj: Text) -> set:
        """
        Deduping key: (lemma, is_mwe, lemma_gloss, pos)
        Extracted from internal lemma text structure.
        """
        keys = set()

        for page in getattr(text_obj, "pages", []) or []:
            segments = getattr(page, "segments", None) or getattr(page, "content", None) or []
            if not segments:
                continue
            seg = segments[0]

            seg_ann = getattr(seg, "annotations", {}) or {}
            lemma_gloss = (seg_ann.get("translated") or "").strip()

            content_elems = getattr(seg, "content_elements", None) or getattr(seg, "content", None) or []
            if not content_elems:
                continue

            # Determine lemma string
            # If it's an MWE page, lemma may be the concatenation of element contents.
            parts = []
            pos = ""
            for ce in content_elems:
                parts.append(getattr(ce, "content", "") or "")
                ann = getattr(ce, "annotations", {}) or {}
                if not pos:
                    pos = (ann.get("pos") or "").strip()
            lemma = " ".join([p for p in parts if p]).strip()

            # Determine is_mwe: from segment annotation 'mwes' if present,
            # otherwise infer by number of content elements.
            mwes = seg_ann.get("mwes") or []
            is_mwe = bool(mwes) or (len(content_elems) > 1)

            keys.add((lemma, is_mwe, lemma_gloss, pos))

        return keys

    def _make_page(self, e: PictureDictionaryEntry, callback) -> Page:
        """
        Build a Page containing exactly one Segment, containing 1+ ContentElements.

        Segment annotations:
          - translated: lemma_gloss
          - mwes: [] or [full_lemma]
        ContentElement annotations:
          - lemma: full lemma string
          - pos: pos
          - gloss: '' (we are not generating lemma glosses here; lemma_gloss is at segment level)
        """
        post_task_update(callback, f'Trying to make page for {e}')
        lemma = e.lemma.strip()
        lemma_components = lemma.split()
        lemma_gloss = (e.lemma_gloss or lemma).strip()
        pos = (e.pos or "").strip()

        content_elements = []

        n_lemma_components = len(lemma_components)

        for index in range(0, n_lemma_components):
            component = lemma_components[index]
            content_elements.append(ContentElement(element_type="Word",
                                                   content=component,
                                                   annotations={"lemma": lemma,
                                                                "pos": pos,
                                                                "gloss": lemma_gloss
                                                                }
                                                   )
                                    )
            if index < n_lemma_components - 1:
                content_elements.append(ContentElement(element_type = "NonWordText",
                                                           content = ' ',
                                                           annotations = {}
                                                           )
                                            )

        seg_annotations = {
            "translated": lemma_gloss,
            "mwes": [ lemma_components ] if e.is_mwe else [],
        }

        seg = Segment(content_elements=content_elements, annotations=seg_annotations)

        # Page signature may differ in your codebase; adjust here if needed.
        page = Page(segments=[seg], annotations={})
        post_task_update(callback, f'Page = {page}')
        return page
