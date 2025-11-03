"""
This module defines the following classes to represent a text and its components:

1. ContentElement: Represents a single content element, such as a word or a punctuation mark.
2. Segment: Represents a segment of text, containing a list of ContentElements.
3. Page: Represents a page of text, containing a list of Segments.
4. Text: Represents a full text, containing a list of Pages and metadata about the text, such as L1 and L2 languages.

Each class also includes methods to convert the objects to and from JSON and plain text formats.

It also defines the following classes:

5. APICall: Represents an API call to the AI
6. DiffElement: Used when constructing a smart diff of two texts
7. Image: Represents an image to be included in a text

8. Various kinds of exceptions
"""

from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Union
 
import json
import os
import regex
import string
import unicodedata

##class ContentElement:
##    def __init__(self, element_type, content, annotations=None):
##        self.type = element_type
##        self.content = content
##        self.annotations = annotations if annotations else {}
##
##    def to_text(self, annotation_type='plain'):
##        
##        if self.type == "Word":
##            escaped_content = escape_special_chars_and_put_at_signs_around_text_if_necessary(self.content, annotation_type)
##            annotations = self.annotations
##            # For texts tagged with lemma, POS and gloss, we have the special notation Word#Lemma/POS/Gloss#
##            if annotation_type == 'lemma_and_gloss':
##                gloss = annotations['gloss'] if 'gloss' in annotations else 'NO_GLOSS'
##                lemma = annotations['lemma'] if 'lemma' in annotations else 'NO_LEMMA'
##                pos = annotations['pos'] if 'pos' in annotations else 'NO_POS'
##                escaped_lemma = escape_special_chars(lemma)
##                escaped_gloss = escape_special_chars(gloss)
##                return f"{escaped_content}#{escaped_lemma}/{pos}/{escaped_gloss}#"
##            # For lemma-tagged texts, we have the special notation Word#Lemma/POS# for words with POS tags as well
##            elif annotation_type == 'lemma' and 'lemma' in annotations and 'pos' in annotations:
##                lemma, pos = ( annotations['lemma'], annotations['pos'] )
##                escaped_lemma = escape_special_chars(lemma)
##                return f"{escaped_content}#{escaped_lemma}/{pos}#"
##            elif annotation_type in ( 'plain', 'presegmented', 'segmented' ):
##                return self.content
##            elif annotation_type in ( 'mwe', 'mwe_minimal', 'translated' ):
##                return escaped_content
##                #return self.content
##            elif annotation_type and annotation_type in annotations:
##                escaped_annotation = escape_special_chars(annotations[annotation_type])
##                return f"{escaped_content}#{escaped_annotation}#"
##            elif annotation_type:
##                return f"{escaped_content}#-#"
##            else:
##                return escaped_content
##        else:
##            return self.content
##
##    def word_count(self):
##        return 1 if self.type == "Word" else 0
##
##    def __repr__(self):
##        return f"ContentElement(type={self.type}, content={self.content}, annotations={self.annotations})"

class ContentElement:
    """Word-like token or non-word unit with per-element annotations.

    This object is the atomic unit inside a `Segment`. For words, it can
    render itself under multiple annotation views (plain, translated, MWE,
    lemma/gloss, etc.) using a compact inline markup the renderer understands.

    Attributes:
        type: Element category, typically `"Word"` for tokens; other values
            (e.g., punctuation markers) are passed through verbatim.
        content: Surface string for this element (unescaped source form).
        annotations: Per-element layer data. Common keys include:
            - 'translation': str
            - 'lemma': str
            - 'pos': str
            - 'gloss': str
            - 'pinyin': str
            Additional keys are allowed; unknown keys are ignored by default.
    """

    def __init__(
        self,
        element_type: str,
        content: str,
        annotations: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize a ContentElement.

        Args:
            element_type: Category for the element; `"Word"` triggers
                word-specific rendering behavior in `to_text`.
            content: Surface string.
            annotations: Optional dictionary of layer values.

        Notes:
            This class does not validate annotation schemas; downstream
            pipeline stages (e.g., glossing/lemmatization) are responsible for
            populating consistent keys/values.
        """
        self.type: str = element_type
        self.content: str = content
        self.annotations: Dict[str, Any] = annotations if annotations else {}

    def to_text(self, annotation_type: str = "plain") -> str:
        """Render the element as inline text for a given annotation layer.

        The rendering protocol uses `#...#` fragments appended to the escaped
        surface form to encode layer values understood by the HTML renderer.

        Supported modes (for `type == "Word"`):
            - 'plain' | 'presegmented' | 'segmented':
                Return raw `content` without inline layer markup.
            - 'translated' | 'mwe' | 'mwe_minimal':
                Return escaped surface only (no trailing layer payload).
            - 'lemma_and_gloss':
                Return `Surface#Lemma/POS/Gloss#` where missing fields fall back
                to 'NO_LEMMA'/'NO_POS'/'NO_GLOSS'.
            - 'lemma':
                If both 'lemma' and 'pos' exist, return `Surface#Lemma/POS#`;
                otherwise fall back to generic key lookup below.
            - <any other key present in `annotations`>:
                Return `Surface#<escaped value>#`.
            - <any other key absent>:
                Return `Surface#-#` as an explicit “no data” marker.

        Non-word elements:
            Returned verbatim as `content`.

        Args:
            annotation_type: Name of the layer to render (see above).

        Returns:
            A string ready for downstream composition (HTML builder).

        Notes:
            - Uses escaping helpers:
              `escape_special_chars_and_put_at_signs_around_text_if_necessary`
              for the surface, and `escape_special_chars` for payloads.
            - The `#...#` convention is relied upon by the renderer and diff/
              compare tools; preserve this contract.
        """
        if self.type != "Word":
            return self.content

        escaped_content = escape_special_chars_and_put_at_signs_around_text_if_necessary(
            self.content, annotation_type
        )
        annotations = self.annotations

        if annotation_type == "lemma_and_gloss":
            gloss = annotations["gloss"] if "gloss" in annotations else "NO_GLOSS"
            lemma = annotations["lemma"] if "lemma" in annotations else "NO_LEMMA"
            pos = annotations["pos"] if "pos" in annotations else "NO_POS"
            escaped_lemma = escape_special_chars(lemma)
            escaped_gloss = escape_special_chars(gloss)
            return f"{escaped_content}#{escaped_lemma}/{pos}/{escaped_gloss}#"

        if annotation_type == "lemma" and "lemma" in annotations and "pos" in annotations:
            lemma, pos = annotations["lemma"], annotations["pos"]
            escaped_lemma = escape_special_chars(lemma)
            return f"{escaped_content}#{escaped_lemma}/{pos}#"

        if annotation_type in ("plain", "presegmented", "segmented"):
            return self.content

        if annotation_type in ("mwe", "mwe_minimal", "translated"):
            return escaped_content

        if annotation_type and annotation_type in annotations:
            escaped_annotation = escape_special_chars(annotations[annotation_type])
            return f"{escaped_content}#{escaped_annotation}#"

        if annotation_type:
            # Explicit "no data" marker keeps downstream logic simple/robust.
            return f"{escaped_content}#-#"

        return escaped_content

    def word_count(self) -> int:
        """Return 1 for words, else 0.

        Returns:
            1 if `type == "Word"`, otherwise 0.

        Notes:
            Used by simple statistics and layout heuristics.
        """
        return 1 if self.type == "Word" else 0

    def __repr__(self) -> str:
        """Debug-friendly representation."""
        return (
            f"ContentElement(type={self.type!r}, content={self.content!r}, "
            f"annotations={self.annotations!r})"
        )
        
##class Segment:
##    def __init__(self, content_elements, annotations=None):
##        self.content_elements = content_elements
##        self.annotations = annotations or {}
##
##    def to_text(self, annotation_type='plain'):
##        out_text = ''
##        last_type = None
##        for element in self.content_elements:
##            this_type = element.type
##            # When producing 'segmented' or 'phonetic' text, we need to add | markers between continuous Words.
##            if annotation_type in ( 'segmented', 'mwe', 'mwe_minimal', 'translated', 'phonetic' ) and this_type == 'Word' and last_type == 'Word':
##                out_text += '|'
##            if annotation_type == 'segmented_for_labelled':
##                if element.type in ( 'Word', 'NonWordText' ):
##                    # We don't want @ ... @ around multiwords
##                    out_text += element.to_text('plain')
##            else:
##                if element.type in ( 'Word', 'NonWordText', 'Markup' ):
##                    out_text += element.to_text(annotation_type)
##            last_type = this_type
##        if annotation_type == 'mwe':
##            annotations = self.annotations
##            if 'analysis' in annotations and 'mwes' in annotations:
##                analysis_text = annotations['analysis']
##                mwes = annotations['mwes']
##                #print(f'annotations["mwes"] = {mwes}')
##                mwes_text = ','.join([ ' '.join([ escape_special_chars(word) for word in mwe ]) for mwe in mwes ])
##                out_text += f"\n_analysis: {analysis_text}\n_MWEs: {mwes_text}"
##        if annotation_type == 'mwe_minimal':
##            annotations = self.annotations
##            if 'mwes' in annotations:
##                mwes = annotations['mwes']
##                if mwes:
##                    mwes_text = ','.join([ ' '.join([ escape_special_chars(word) for word in mwe ]) for mwe in mwes ])
##                    out_text += f"#{mwes_text}#"
##        if annotation_type == 'translated':
##            annotations = self.annotations
##            translated = annotations['translated'] if 'translated' in annotations else ''
##            escaped_translated = escape_special_chars(translated)
##            out_text += f"#{escaped_translated}#"
##            
##        return out_text
##
##    def add_annotation(self, annotation_type, annotation_value):
##        self.annotations[annotation_type] = annotation_value
##
##    def word_count(self, phonetic=False):
##        if not phonetic:
##            return sum([ element.word_count() for element in self.content_elements ])
##        # In a phonetic text, a Segment represents a word.
##        else:
##            return 0 if string_is_only_punctuation_spaces_and_separators(self.to_text()) else 1
##
##    def __repr__(self):
##        return f"Segment(content_elements={self.content_elements}, annotations={self.annotations})"

class Segment:
    """A linear sequence of `ContentElement`s with segment-level annotations.

    Segments are the unit that carry higher-level annotations such as:
    - translation (for the whole segment),
    - multi-word expression (MWE) analysis,
    - and any additional layer outputs.

    Rendering conventions:
      • For views {'segmented','mwe','mwe_minimal','translated','phonetic'},
        a '|' is inserted between adjacent word tokens to mark word boundaries.
      • 'segmented_for_labelled' returns only plain text for words/non-word text
        (i.e., suppresses the inline @…@ or #…# markup used elsewhere).
      • 'mwe' appends two newlines with `_analysis:` and `_MWEs:` trailers.
      • 'mwe_minimal' appends a single `#…#` trailer containing MWE surface forms.
      • 'translated' appends a single `#…#` trailer with the segment translation.

    Attributes:
        content_elements: Ordered list of child `ContentElement`s.
        annotations: Free-form dict holding segment-level layers.
            Common keys:
              - 'translated': str
              - 'analysis': str   (free-text explanation for MWE analysis)
              - 'mwes': List[List[str]]  (each inner list is an MWE word sequence)
            Unknown keys are allowed and ignored by the built-in renderers.
    """

    def __init__(
        self,
        content_elements: Iterable["ContentElement"],
        annotations: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.content_elements: List["ContentElement"] = list(content_elements)
        self.annotations: Dict[str, Any] = annotations or {}

    def to_text(self, annotation_type: str = "plain") -> str:
        """Render the segment under an annotation view.

        Args:
            annotation_type: One of:
                - 'plain'
                - 'segmented' | 'mwe' | 'mwe_minimal' | 'translated' | 'phonetic'
                - 'segmented_for_labelled' (plain words/non-word text only)
                - or any other mode supported by `ContentElement.to_text`

        Returns:
            A string suitable for downstream composition.

        Notes:
            - Word-boundary '|' insertion is applied for certain views
              between *adjacent* word elements only.
            - MWE and translation trailers are appended after the main text.
            - For 'segmented_for_labelled', we suppress `ContentElement` inline
              markup by forcing 'plain' for Word/NonWordText and skipping Markup.
        """
        out_text: str = ""
        last_type: Optional[str] = None

        for element in self.content_elements:
            this_type = element.type

            # Word-boundary bar for selected views (between adjacent words).
            if (
                annotation_type in ("segmented", "mwe", "mwe_minimal", "translated", "phonetic")
                and this_type == "Word"
                and last_type == "Word"
            ):
                out_text += "|"

            if annotation_type == "segmented_for_labelled":
                # Only surface forms; no inline #…# or @…@ markup.
                if element.type in ("Word", "NonWordText"):
                    out_text += element.to_text("plain")
            else:
                if element.type in ("Word", "NonWordText", "Markup"):
                    out_text += element.to_text(annotation_type)

            last_type = this_type

        # Postfix trailers for segment-level layers
        if annotation_type == "mwe":
            analysis_text = self.annotations.get("analysis", "")
            mwes = self.annotations.get("mwes", [])
            if analysis_text or mwes:
                mwes_text = ",".join(
                    [" ".join([escape_special_chars(w) for w in mwe]) for mwe in mwes]
                )
                out_text += f"\n_analysis: {analysis_text}\n_MWEs: {mwes_text}"

        if annotation_type == "mwe_minimal":
            mwes = self.annotations.get("mwes", [])
            if mwes:
                mwes_text = ",".join(
                    [" ".join([escape_special_chars(w) for w in mwe]) for mwe in mwes]
                )
                out_text += f"#{mwes_text}#"

        if annotation_type == "translated":
            translated = self.annotations.get("translated", "")
            escaped_translated = escape_special_chars(translated)
            out_text += f"#{escaped_translated}#"

        return out_text

    def add_annotation(self, annotation_type: str, annotation_value: Any) -> None:
        """Attach or overwrite a segment-level annotation value."""
        self.annotations[annotation_type] = annotation_value

    def word_count(self, phonetic: bool = False) -> int:
        """Count words in this segment.

        Args:
            phonetic: If True, interpret this segment as a *single word* iff the
                rendered plain text isn't only punctuation/space/separators.

        Returns:
            Non-phonetic: Sum of child word counts.
            Phonetic: 1 for non-empty non-punctuation, else 0.
        """
        if not phonetic:
            return sum(e.word_count() for e in self.content_elements)
        # In phonetic mode, a Segment corresponds to a word if its plain text
        # has non-punctuation content.
        return 0 if string_is_only_punctuation_spaces_and_separators(self.to_text()) else 1

    def __repr__(self) -> str:
        return f"Segment(content_elements={self.content_elements!r}, annotations={self.annotations!r})"


##class Page:
##    def __init__(self, segments, annotations=None):
##        self.segments = segments
##        self.annotations = annotations or {}  # This could contain 'img', 'page_number', and 'position'
##
##    def __repr__(self):
##        return f"Page(segments={self.segments}, annotations={self.annotations})"
##
##    def content_elements(self):
##        elements = []
##        for segment in self.segments:
##            elements.extend(segment.content_elements)
##        return elements
##
##    def to_text(self, annotation_type='plain'):
##        segment_separator = '' if annotation_type == 'plain' else '||'
##        segment_texts = segment_separator.join([segment.to_text(annotation_type) for segment in self.segments])
##        if annotation_type == 'segmented_for_labelled':
##            return segment_texts
##        elif self.annotations:
##            attributes_str = ' '.join([f"{key}='{value}'" for key, value in self.annotations.items()])
##            return f"<page {attributes_str}>{segment_texts}"
##        else:
##            return f"<page>{segment_texts}"
##
##    def to_translated_text(self):
##        segment_separator = ' ' 
##        segment_texts = segment_separator.join([segment.annotations['translated'] for segment in self.segments
##                                                if 'translated' in segment.annotations])
##        return segment_texts
##
##    def word_count(self, phonetic=False):
##        return sum([ segment.word_count(phonetic=phonetic) for segment in self.segments ])
##
##    @classmethod
##    def from_json(cls, json_str):
##        page_dict = json.loads(json_str)
##        segments = []
##        for segment_dict in page_dict["segments"]:
##            content_elements = []
##            for element_dict in segment_dict["content_elements"]:
##                content_element = ContentElement(
##                    element_type=element_dict["type"],
##                    content=element_dict["content"],
##                    annotations=element_dict["annotations"],
##                )
##                content_elements.append(content_element)
##            segment = Segment(content_elements)
##            segments.append(segment)
##        return cls(segments)
##
##    def to_json(self):
##        page_json = {"segments": []}
##        for segment in self.segments:
##            segment_json = {"content_elements": []}
##            for element in segment.content_elements:
##                content_element_json = {
##                    "type": element.type,
##                    "content": element.content,
##                    "annotations": element.annotations,
##                }
##                segment_json["content_elements"].append(content_element_json)
##            page_json["segments"].append(segment_json)
##        return json.dumps(page_json)

class Page:
    """A page of text consisting of ordered `Segment`s and optional page-level annotations.

    Common page-level annotations include:
      - 'img'          : path/identifier of the page image
      - 'page_number'  : 1-based page index
      - 'position'     : e.g., layout hints

    Rendering:
      • Default `to_text('plain')` concatenates segment text *without* separators.
      • Other views insert '||' between segments (matching existing behavior).
      • For 'segmented_for_labelled', returns the concatenation of segment
        surfaces (no inline markup) and **does not** wrap with <page…>.
      • Otherwise, the page is wrapped with `<page ...>` including page annotations
        as attributes if any exist; if none exist, `<page>` is used (no close tag
        to preserve legacy behavior).
    """

    def __init__(
        self,
        segments: Iterable["Segment"],
        annotations: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.segments: List["Segment"] = list(segments)
        self.annotations: Dict[str, Any] = annotations or {}

    def __repr__(self) -> str:
        return f"Page(segments={self.segments!r}, annotations={self.annotations!r})"

    def content_elements(self) -> List["ContentElement"]:
        """Flattened list of all `ContentElement`s from this page’s segments."""
        elements: List["ContentElement"] = []
        for seg in self.segments:
            elements.extend(seg.content_elements)
        return elements

    def to_text(self, annotation_type: str = "plain") -> str:
        """Render the page by concatenating rendered segments.

        Args:
            annotation_type: Passed through to `Segment.to_text`.
                Special handling:
                  - 'plain' → no segment separator
                  - any other view → '||' between segments (legacy)
                  - 'segmented_for_labelled' → returns bare segment text (no <page…>)

        Returns:
            Rendered string for this page in the selected view.
        """
        segment_separator = "" if annotation_type == "plain" else "||"
        segment_texts = segment_separator.join(
            seg.to_text(annotation_type) for seg in self.segments
        )

        if annotation_type == "segmented_for_labelled":
            # Historical behavior: do not wrap in <page …> for this mode.
            return segment_texts

        if self.annotations:
            attrs = " ".join(f"{k}='{v}'" for k, v in self.annotations.items())
            return f"<page {attrs}>{segment_texts}"
        else:
            return f"<page>{segment_texts}"

    def to_translated_text(self) -> str:
        """Concatenate segment-level translations (if present) with spaces.

        Returns:
            A single string containing the `translated` annotation for each
            segment that provides one, separated by spaces.
        """
        return " ".join(
            seg.annotations["translated"]
            for seg in self.segments
            if "translated" in seg.annotations
        )

    def word_count(self, phonetic: bool = False) -> int:
        """Sum of child segment word counts (or phonetic word counts)."""
        return sum(seg.word_count(phonetic=phonetic) for seg in self.segments)

    def add_annotation(self, key: str, value: Any) -> None:
        """Attach/overwrite a page-level annotation."""
        self.annotations[key] = value

    # -------- JSON (de)serialization --------
    @classmethod
    def from_json(cls, json_str: str) -> "Page":
        """Deserialize a Page.

        Accepts legacy payloads without annotations. Expected shape:

        {
          "segments": [
            {
              "content_elements": [
                {"type": "...", "content": "...", "annotations": {...}}
              ],
              "annotations": {...}  # optional
            }
          ],
          "annotations": {...}      # optional (page-level)
        }
        """
        data = json.loads(json_str)
        page_ann = data.get("annotations", {}) or {}
        segs: List["Segment"] = []

        for seg_dict in data["segments"]:
            ce_list: List["ContentElement"] = []
            for el in seg_dict["content_elements"]:
                ce_list.append(
                    ContentElement(
                        element_type=el["type"],
                        content=el["content"],
                        annotations=el.get("annotations", {}) or {},
                    )
                )
            seg_ann = seg_dict.get("annotations", {}) or {}
            segs.append(Segment(ce_list, annotations=seg_ann))

        return cls(segs, annotations=page_ann)

    def to_json(self) -> str:
        """Serialize a Page including page and segment annotations.

        Output shape (backwards-compatible with legacy readers that ignore
        unknown keys):

        {
          "segments": [
            {
              "content_elements": [
                {"type": "...", "content": "...", "annotations": {...}}
              ],
              "annotations": {...}
            }
          ],
          "annotations": {...}
        }
        """
        payload = {
            "segments": [],
            "annotations": self.annotations,
        }

        for seg in self.segments:
            seg_obj = {
                "content_elements": [],
                "annotations": seg.annotations,
            }
            for el in seg.content_elements:
                seg_obj["content_elements"].append(
                    {
                        "type": el.type,
                        "content": el.content,
                        "annotations": el.annotations,
                    }
                )
            payload["segments"].append(seg_obj)

        return json.dumps(payload, ensure_ascii=False)


##class Text:
##    def __init__(self, pages, l2_language, l1_language, annotations=None, voice=None):
##        self.l2_language = l2_language
##        self.l1_language = l1_language
##        self.pages = pages
##        self.annotations = annotations or {}
##        self.voice = voice
##
##    def __repr__(self):
##        return f"Text(l2_language={self.l2_language}, l1_language={self.l1_language}, pages={self.pages}, annotations={self.annotations})"
##
##    def content_elements(self):
##        elements = []
##        for page in self.pages:
##            elements.extend(page.content_elements())
##        return elements
##
##    def to_numbered_page_list(self, translated=False):
##        numbered_pages = []
##        number = 1
##        for page in self.pages:
##            if translated:
##                page_text = page.to_translated_text()
##                original_page_text = page.to_text(annotation_type='plain').replace('<page>', '')
##                numbered_pages.append({'page_number': number,
##                                       'original_page_text': original_page_text,
##                                       'text': page_text})
##            else:
##                page_text = page.to_text(annotation_type='plain').replace('<page>', '')
##                translated_text = page.to_translated_text()
##                if not translated_text.replace(' ', ''):
##                    numbered_pages.append({'page_number': number,
##                                           'text': page_text})
##                else:
##                    numbered_pages.append({'page_number': number,
##                                           'text': page_text,
##                                           'translated_text': translated_text})
##            number += 1
##        return numbered_pages
##
##    # Returns a list of lists of content elements, one per segment
##    def segmented_elements(self):
##        segment_list = []
##        for page in self.pages:
##            for segment in page.segments:
##                segment_list.append(segment.content_elements)
##        return segment_list
##
##    # Return a list of segments
##    def segments(self):
##        segment_list = []
##        for page in self.pages:
##            segment_list += page.segments
##        return segment_list
##    
##    def word_count(self, phonetic=False):
##        return sum([ page.word_count(phonetic=phonetic) for page in self.pages ])
##
##    def add_page(self, page):
##        self.pages.append(page)
##
##    def remove_page(self, page_object):
##        if page_object in self.pages:
##            self.pages.remove(page_object)
##
##    def to_text(self, annotation_type='plain'):
##        #return "\n".join([page.to_text(annotation_type) for page in self.pages])
##        return "".join([page.to_text(annotation_type) for page in self.pages])
##
##    def prettyprint(self):
##        print(f"Text Language (L2): {self.l2_language}, Annotation Language (L1): {self.l1_language}\n")
##        
##        for page_number, page in enumerate(self.pages, start=1):
##            print(f"  Page {page_number}: Annotations: {page.annotations}")
##            
##            for segment_number, segment in enumerate(page.segments, start=1):
##                print(f"    Segment {segment_number}: Annotations: {segment.annotations}")
##
##                for element_number, element in enumerate(segment.content_elements, start=1):
##                    content_to_print = f"'{element.content}'" if isinstance(element.content, (str)) else f"{element.content}"
##                    print(f"      Element {element_number}: Type: '{element.type}', Content: {content_to_print}, Annotations: {element.annotations}")
##            
##    def to_json(self):
##        json_list = [json.loads(page.to_json()) for page in self.pages]
##        return json.dumps({
##            "l2_language": self.l2_language,
##            "l1_language": self.l1_language,
##            "pages": json_list
##        })
##
##    def find_page_by_image(self, image):
##        for page in self.pages:
##            if 'img' in page.annotations and page.annotations['img'] == image.image_name:
##                return page
##        return None
##
##    @classmethod
##    def from_json(cls, json_str):
##        data = json.loads(json_str)
##        text = cls(l2_language=data["l2_language"], l1_language=data["l1_language"])
##        text.pages = [Page.from_json(page_json) for page_json in data["pages"]]
##        return text

class Text:
    """Top-level container for a C-LARA text.

    A `Text` owns:
      • language metadata (`l2_language` = text language, `l1_language` = annotation language),
      • an ordered list of `Page`s,
      • optional free-form `annotations` (experiment flags, provenance, etc.),
      • an optional `voice` (used by rendering/audio pipelines).

    Rendering conventions:
      • `to_text('plain')` concatenates page renderings (each page starts with `<page>`).
      • Other annotation views pass through to `Page.to_text(view)`.
      • `to_numbered_page_list()` returns convenient dicts for UI and exports,
        preserving legacy conventions (e.g., stripping leading `<page>`).
    """

    def __init__(
        self,
        pages: Optional[Iterable["Page"]] = None,
        l2_language: str = "",
        l1_language: str = "",
        annotations: Optional[Dict[str, Any]] = None,
        voice: Optional[str] = None,
    ) -> None:
        self.l2_language: str = l2_language
        self.l1_language: str = l1_language
        self.pages: List["Page"] = list(pages) if pages is not None else []
        self.annotations: Dict[str, Any] = annotations or {}
        self.voice: Optional[str] = voice

    def __repr__(self) -> str:
        return (
            "Text("
            f"l2_language={self.l2_language!r}, "
            f"l1_language={self.l1_language!r}, "
            f"pages={self.pages!r}, "
            f"annotations={self.annotations!r}, "
            f"voice={self.voice!r}"
            ")"
        )

    # ---------- Structure & accessors ----------

    def content_elements(self) -> List["ContentElement"]:
        """Flattened list of all content elements in reading order."""
        out: List["ContentElement"] = []
        for page in self.pages:
            out.extend(page.content_elements())
        return out

    def segments(self) -> List["Segment"]:
        """Flattened list of all segments (page order preserved)."""
        segs: List["Segment"] = []
        for page in self.pages:
            segs.extend(page.segments)
        return segs

    def segmented_elements(self) -> List[List["ContentElement"]]:
        """List of lists: content elements grouped by segment."""
        return [seg.content_elements for seg in self.segments()]

    def add_page(self, page: "Page") -> None:
        """Append a page."""
        self.pages.append(page)

    def remove_page(self, page_object: "Page") -> None:
        """Remove a page if present (no-op if missing)."""
        try:
            self.pages.remove(page_object)
        except ValueError:
            pass

    def find_page_by_image(self, image) -> Optional["Page"]:
        """Return first page whose annotation 'img' equals `image.image_name`, if any."""
        for page in self.pages:
            if page.annotations.get("img") == getattr(image, "image_name", None):
                return page
        return None

    # ---------- Rendering & counts ----------

    def to_text(self, annotation_type: str = "plain") -> str:
        """Concatenate page renderings for `annotation_type`."""
        return "".join(page.to_text(annotation_type) for page in self.pages)

    def to_numbered_page_list(self, translated: bool = False) -> List[Dict[str, Any]]:
        """Return UI-friendly page dicts, optionally focusing on translations.

        When `translated=True`:
          [{'page_number': n, 'original_page_text': <plain>, 'text': <translated>}]

        When `translated=False`:
          [{'page_number': n, 'text': <plain>[, 'translated_text': <joined translations>]}]

        Notes:
          • Legacy behavior: leading '<page>' is stripped from the plain rendering.
        """
        numbered: List[Dict[str, Any]] = []
        for idx, page in enumerate(self.pages, start=1):
            plain = page.to_text(annotation_type="plain").replace("<page>", "")
            translated_text = page.to_translated_text()

            if translated:
                numbered.append(
                    {"page_number": idx, "original_page_text": plain, "text": translated_text}
                )
            else:
                if translated_text.replace(" ", ""):
                    numbered.append(
                        {"page_number": idx, "text": plain, "translated_text": translated_text}
                    )
                else:
                    numbered.append({"page_number": idx, "text": plain})
        return numbered

    def word_count(self, phonetic: bool = False) -> int:
        """Total word count (or phonetic count) across pages."""
        return sum(page.word_count(phonetic=phonetic) for page in self.pages)

    def prettyprint(self) -> None:
        """Human-readable dump (debug only)."""
        print(
            f"Text Language (L2): {self.l2_language}, "
            f"Annotation Language (L1): {self.l1_language}\n"
        )
        for pno, page in enumerate(self.pages, start=1):
            print(f"  Page {pno}: Annotations: {page.annotations}")
            for sno, segment in enumerate(page.segments, start=1):
                print(f"    Segment {sno}: Annotations: {segment.annotations}")
                for eno, element in enumerate(segment.content_elements, start=1):
                    content_to_print = (
                        f"'{element.content}'"
                        if isinstance(element.content, str)
                        else f"{element.content}"
                    )
                    print(
                        f"      Element {eno}: "
                        f"Type: '{element.type}', Content: {content_to_print}, "
                        f"Annotations: {element.annotations}"
                    )

    # ---------- JSON (de)serialization ----------

    def to_json(self) -> str:
        """Serialize the text (languages, pages, annotations, voice)."""
        pages_payload = [json.loads(page.to_json()) for page in self.pages]
        payload = {
            "l2_language": self.l2_language,
            "l1_language": self.l1_language,
            "pages": pages_payload,
            "annotations": self.annotations,  # new but backward-compatible
            "voice": self.voice,              # optional
        }
        return json.dumps(payload, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "Text":
        """Deserialize a text.

        Accepts legacy payloads missing 'annotations' or 'voice'.
        Expected shape:

        {
          "l2_language": "...",
          "l1_language": "...",
          "pages": [ <Page JSON objects> ],
          "annotations": {...},   # optional
          "voice": "..."          # optional
        }
        """
        data = json.loads(json_str)
        l2 = data.get("l2_language", "")
        l1 = data.get("l1_language", "")
        anns = data.get("annotations", {}) or {}
        voice = data.get("voice")

        pages = [Page.from_json(json.dumps(p)) for p in data.get("pages", [])]
        return cls(
            pages=pages,
            l2_language=l2,
            l1_language=l1,
            annotations=anns,
            voice=voice,
        )


##def escape_special_chars(text):
##    if text == '':
##        return ''
##    if not text:
##        return '-'
##    if not isinstance(text, (str)):
##        raise ValueError(f'Non-string argument to escape_special_chars: {text}') 
##    return text.replace("#", r"\#").replace("@", r"\@").replace("<", r"\<").replace(">", r"\>")
##
### If a Word element contains spaces or punctuation, we need to add @ signs around it
### for the annotated text to be well-formed
##def escape_special_chars_and_put_at_signs_around_text_if_necessary(text, annotation_type):
##    if not isinstance(text, (str)):
##        raise ValueError(f'Non-string argument to escape_special_chars_and_put_at_signs_around_text_if_necessary: {text}')
##    
##    put_at_signs = False
##    # Check if text contains spaces or any Unicode punctuation
##    if any( not char in "#@<>" and unicodedata.category(char).startswith('P') for char in text) or ' ' in text:
##        if annotation_type in ('segmented', 'mwe', 'mwe_minimal', 'translated', 'gloss', 'lemma'):
##            put_at_signs = True
##
##    escaped_text = escape_special_chars(text)
##            
##    if escaped_text == '':
##        return ''
##    elif not escaped_text:
##        return '-'
##    else:
##        return f'@{escaped_text}@' if put_at_signs else escaped_text

ANNOTATION_TYPES_REQUIRING_ATS = {
    "segmented", "mwe", "mwe_minimal", "translated", "gloss", "lemma"
}

def escape_special_chars(text: Optional[str]) -> str:
    """Escape special delimiter characters used in C-LARA annotated text.

    Rules:
      - Return '' for empty string.
      - Return '-' for falsy non-empty (e.g., None) to match legacy semantics.
      - Only strings are accepted; raise on non-string inputs (other than None).

    Escaped characters:
      '#' -> '\\#'
      '@' -> '\\@'
      '<' -> '\\<'
      '>' -> '\\>'

    Examples:
      >>> escape_special_chars("A#B@C<D>")
      'A\\#B\\@C\\<D\\>'
      >>> escape_special_chars("")
      ''
      >>> escape_special_chars(None)
      '-'
    """
    if text == "":
        return ""
    if not text:
        return "-"
    if not isinstance(text, str):
        raise ValueError(f"Non-string argument to escape_special_chars: {text!r}")
    return (
        text.replace("#", r"\#")
            .replace("@", r"\@")
            .replace("<", r"\<")
            .replace(">", r"\>")
    )


def escape_special_chars_and_put_at_signs_around_text_if_necessary(
    text: str,
    annotation_type: str,
) -> str:
    """Escape a 'Word' token and (optionally) wrap it with @...@ for certain views.

    We wrap with @...@ when BOTH of these hold:
      1) The token contains at least one space OR a Unicode punctuation character
         (per `unicodedata.category(ch).startswith('P')`), ignoring the four
         reserved delimiter chars '#', '@', '<', '>' which we escape separately.
      2) `annotation_type` is one of:
         {'segmented','mwe','mwe_minimal','translated','gloss','lemma'}

    Returns:
      The escaped token (possibly wrapped with '@' on both sides).
      Preserves legacy edge cases:
        • ''  -> ''
        • None (not allowed here) would have been handled upstream.

    Examples:
      >>> escape_special_chars_and_put_at_signs_around_text_if_necessary("ice-cream","segmented")
      '@ice-cream@'
      >>> escape_special_chars_and_put_at_signs_around_text_if_necessary("hello","segmented")
      'hello'
      >>> escape_special_chars_and_put_at_signs_around_text_if_necessary("A#B","mwe")
      '@A\\#B@'
      >>> escape_special_chars_and_put_at_signs_around_text_if_necessary("New York","lemma")
      '@New York@'
      >>> escape_special_chars_and_put_at_signs_around_text_if_necessary("New York","plain")
      'New York'
    """
    if not isinstance(text, str):
        raise ValueError(
            "Non-string argument to escape_special_chars_and_put_at_signs_around_text_if_necessary: "
            f"{text!r}"
        )

    # Determine if token visually spans multiple symbols (spaces or Unicode punctuation)
    has_space = " " in text
    has_unicode_punct = any(
        (ch not in "#@<>") and unicodedata.category(ch).startswith("P")
        for ch in text
    )
    needs_wrapping = (has_space or has_unicode_punct) and (
        annotation_type in ANNOTATION_TYPES_REQUIRING_ATS
    )

    escaped = escape_special_chars(text)
    if escaped == "":
        return ""
    if not escaped:
        return "-"
    return f"@{escaped}@" if needs_wrapping else escaped

##class Image:
##    def __init__(self, image_file_path, thumbnail_file_path, image_name,
##                 associated_text, associated_areas,
##                 page, position, style_description=None,
##                 content_description=None, user_prompt=None,
##                 request_type='image-generation',
##                 description_variable=None,
##                 description_variables=None,
##                 advice='',
##                 image_type='page',
##                 element_name='',
##                 page_object=None):
##        self.image_file_path = image_file_path
##        self.thumbnail_file_path = thumbnail_file_path
##        self.image_name = image_name
##        self.associated_text = associated_text
##        self.associated_areas = associated_areas
##        self.page = page
##        self.position = position
##        self.style_description = style_description
##        self.content_description = content_description
##        self.user_prompt = user_prompt
##        self.request_type = request_type
##        self.description_variable = description_variable
##        self.description_variables = description_variables or []
##        self.advice=advice
##        self.image_type=image_type
##        self.element_name=element_name
##        self.page_object = page_object
##
##    def to_json(self):
##        return {
##            'image_file_path': self.image_file_path,
##            'thumbnail_file_path': self.thumbnail_file_path,
##            'image_name': self.image_name,
##            'associated_text': self.associated_text,
##            'associated_areas': self.associated_areas,
##            'page': self.page,
##            'position': self.position,
##            'style_description': self.style_description,
##            'content_description': self.content_description,
##            'request_type': self.request_type,
##            'description_variable': self.description_variable,
##            'description_variables': self.description_variables,  
##            'user_prompt': self.user_prompt,
##            'image_type': self.image_type,
##            'advice': self.advice,
##            'element_name': self.element_name
##        }
##
##    def merge_page(self, page_object):
##        self.page_object = page_object
##
##    def __repr__(self):
##        return f"""Image(image_file_path={self.image_file_path}, image_type={self.image_type},
##image_name={self.image_name}, advice={self.advice}, element_name={self.element_name})"""

class Image:
    """Represents an image artifact used in C-LARA (style, element, or page image).

    An Image may be:
      • a page-level illustration (image_type='page'),
      • a style sample (image_type='style'),
      • an element image (image_type='element'), etc.

    Attributes:
        image_file_path: Absolute/relative path to the full-size image file.
        thumbnail_file_path: Path to a thumbnail version (if created).
        image_name: Logical name/identifier (often used for lookups in the project).
        associated_text: Free text associated with the image (e.g., page text or prompt).
        associated_areas: Arbitrary structure describing regions (e.g., bounding boxes).
        page: Page number (1-based) or other page identifier relevant to this image.
        position: Placement hint (e.g., 'top', 'bottom'); semantics defined by the renderer.
        style_description: Natural-language description of the style (v2 pipeline).
        content_description: Natural-language description of the content (v2 pipeline).
        user_prompt: Original user prompt used to produce/modify this image (if any).
        request_type: Kind of request that produced this image (e.g., 'image-generation',
                      'image-edit', or 'image-variation').
        description_variable: Name of a variable used in templated prompts (legacy).
        description_variables: List of variable names used in templated prompts (v2 supports multiple).
        advice: Free-form guidance or reviewer notes for this image.
        image_type: One of {'page','style','element',...}; determines UI/flow treatment.
        element_name: For element images, the canonical element label (e.g., 'cat', 'boat').
        page_object: Optional reference to the Page object this image was merged with.
    """

    def __init__(
        self,
        image_file_path: str,
        thumbnail_file_path: str,
        image_name: str,
        associated_text: str,
        associated_areas: Any,
        page: Optional[int],
        position: Optional[str],
        style_description: Optional[str] = None,
        content_description: Optional[str] = None,
        user_prompt: Optional[str] = None,
        request_type: str = "image-generation",
        description_variable: Optional[str] = None,
        description_variables: Optional[List[str]] = None,
        advice: str = "",
        image_type: str = "page",
        element_name: str = "",
        page_object: Optional[Any] = None,
    ):
        self.image_file_path = image_file_path
        self.thumbnail_file_path = thumbnail_file_path
        self.image_name = image_name
        self.associated_text = associated_text
        self.associated_areas = associated_areas
        self.page = page
        self.position = position
        self.style_description = style_description
        self.content_description = content_description
        self.user_prompt = user_prompt
        self.request_type = request_type
        self.description_variable = description_variable
        self.description_variables = description_variables or []
        self.advice = advice
        self.image_type = image_type
        self.element_name = element_name
        self.page_object = page_object

    def to_json(self) -> Dict[str, Any]:
        """Serialize the image metadata for persistence (JSON-serializable dict)."""
        return {
            "image_file_path": self.image_file_path,
            "thumbnail_file_path": self.thumbnail_file_path,
            "image_name": self.image_name,
            "associated_text": self.associated_text,
            "associated_areas": self.associated_areas,
            "page": self.page,
            "position": self.position,
            "style_description": self.style_description,
            "content_description": self.content_description,
            "request_type": self.request_type,
            "description_variable": self.description_variable,
            "description_variables": self.description_variables,
            "user_prompt": self.user_prompt,
            "image_type": self.image_type,
            "advice": self.advice,
            "element_name": self.element_name,
        }

    def merge_page(self, page_object: Any) -> None:
        """Attach a Page object reference after images have been resolved/loaded."""
        self.page_object = page_object

    def __repr__(self) -> str:
        return (
            f"Image(image_file_path={self.image_file_path}, image_type={self.image_type}, "
            f"image_name={self.image_name}, advice={self.advice}, element_name={self.element_name})"
        )
                
class ImageDescriptionObject:
    def __init__(self, project_id, description_variable, explanation):
        self.project_id = project_id
        self.description_variable = description_variable
        self.explanation = explanation

    def to_json(self):
        return {
            'description_variable': self.description_variable,
            'explanation': self.explanation
            }

    def __str__(self):
        return f"{self.project_id} | {self.description_variable} | {self.explanation}"

##class APICall:
##    def __init__(self, prompt, response, cost, duration, timestamp, retries):
##        self.prompt = prompt
##        self.response = response
##        self.cost = cost
##        self.duration = duration
##        self.timestamp = timestamp
##        self.retries = retries

class APICall:
    """Lightweight record of an AI API call made by the platform.

    Attributes:
        prompt: The prompt/request sent to the model (may be a str or structured dict).
        response: The raw response object (as returned by the client) or extracted content.
        cost: Monetary cost (USD) attributed to this call (if tracked).
        duration: Wall-clock duration in seconds for the call (including retries).
        timestamp: When the call was made (datetime or ISO8601 string).
        retries: Number of retry attempts performed before success (0 if none).
    """

    def __init__(
        self,
        prompt: Union[str, Dict[str, Any]],
        response: Any,
        cost: float,
        duration: float,
        timestamp: Union[datetime, str],
        retries: int,
    ):
        self.prompt = prompt
        self.response = response
        self.cost = cost
        self.duration = duration
        self.timestamp = timestamp
        self.retries = retries

    def __repr__(self) -> str:
        return (
            "APICall("
            f"cost={self.cost}, duration={self.duration}s, retries={self.retries}, "
            f"timestamp={self.timestamp})"
        )

##class DiffElement:
##    def __init__(self, type, content = '', annotations = {}):
##        self.type = type
##        self.content = content
##        self.annotations = annotations
##
##    def __repr__(self):
##        return f"DiffElement(type={self.type}, content={self.content}, annotations={self.annotations})"

class DiffElement:
    """Represents a unit in a textual diff for comparisons between versions.

    `type` can describe the diff operation or token class, e.g., 'equal', 'insert',
    'delete', or a finer-grained tag used by the renderer.

    Attributes:
        type: Category/operation of this diff element (e.g., 'insert').
        content: Human-readable payload (e.g., the text span).
        annotations: Optional metadata for display or alignment (e.g., indices).
    """

    def __init__(
        self,
        type: str,
        content: str = "",
        annotations: Optional[Dict[str, Any]] = None,
    ):
        self.type = type
        self.content = content
        # Avoid mutable default argument pitfalls
        self.annotations = annotations if annotations is not None else {}

    def __repr__(self) -> str:
        return (
            f"DiffElement(type={self.type}, content={self.content}, "
            f"annotations={self.annotations})"
        )

class InternalCLARAError(Exception):
    def __init__(self, message = 'Internal CLARA error'):
        self.message = message

class InternalisationError(Exception):
    def __init__(self, message = 'Internalisation error'):
        self.message = message

class MWEError(Exception):
    def __init__(self, message = 'MWE error'):
        self.message = message
        
class TemplateError(Exception):
    def __init__(self, message = 'Template error'):
        self.message = message

class ChatGPTError(Exception):
    def __init__(self, message = 'ChatGPT error'):
        self.message = message

class TreeTaggerError(Exception):
    def __init__(self, message = 'TreeTagger error'):
        self.message = message

class ImageGenerationError(Exception):
    def __init__(self, message = 'Image generation error'):
        self.message = message

class ReadingHistoryError(Exception):
    def __init__(self, message = 'ReadingHistory error'):
        self.message = message

# Can't import from these functions from other files because we get a circular import
def basename(pathname):
    return os.path.basename(pathname)

def string_is_only_punctuation_spaces_and_separators(s):
    return all(regex.match(r"[\p{P} \n|]", c) for c in s)


