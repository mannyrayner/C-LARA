# clara_hindi.py

from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
import regex
import unicodedata

from .clara_internalise import internalize_text
from .clara_classes import Text, Page, Segment, ContentElement

def is_supported_indian_language(LangId):
    return LangId in ( 'hindi' )

def romanise_tag_text_using_indic_transliteration(input_text):
    l2_language = 'hindi'
    l1_language = 'irrelevant'
    text_object = internalize_text(input_text, l2_language, l1_language, 'segmented')

    out_pages = []
    for page in text_object.pages:
        out_segments = []
        for segment in page.segments:
            out_content_elements = []
            for content_element in segment.content_elements:
                out_content_element = romanise_tagged_version_of_content_element(content_element)
                out_content_elements.append(out_content_element)
            out_segment = Segment(out_content_elements)
            out_segments.append(out_segment)
        out_page = Page(out_segments)
        out_pages.append(out_page)

    out_text_object = Text(out_pages, l2_language, l1_language)

    # Quick first cut: keep using the existing pinyin slot/rendering path
    return out_text_object.to_text(annotation_type='pinyin')


def romanise_tagged_version_of_content_element(content_element):
    if content_element.type == 'Word':
        reading_annotation = hindi_word_to_romanised_reading(content_element.content)
        content_element.annotations['pinyin'] = reading_annotation

    return content_element


def hindi_word_to_romanised_reading(word):
    # Leave non-Devanagari tokens alone if you prefer
    if not contains_devanagari(word):
        return word

    raw = transliterate(word, sanscript.DEVANAGARI, sanscript.IAST)
    cooked = apply_hindi_postprocessing(raw)
    return normalise_romanised_hindi(cooked)


def contains_devanagari(s):
    return bool(regex.search(r'\p{Devanagari}', s))


def apply_hindi_postprocessing(s):
    s = apply_final_schwa_deletion(s)
    s = apply_basic_medial_schwa_deletion(s)
    s = normalise_nasalisation(s)
    return s


def apply_final_schwa_deletion(s):
    # Very first approximation:
    # vikāsa -> vikās, karana -> करण? depends on transliteration scheme
    # Conservative version: only remove final 'a'
    return regex.sub(r'a$', '', s)


def apply_basic_medial_schwa_deletion(s):
    # Placeholder for a few common Hindi patterns.
    # Best kept conservative in version 1.
    return s


def normalise_nasalisation(s):
    # Placeholder for handling ṃ / ṅ / ñ / vowel nasalisation consistently
    return s


def normalise_romanised_hindi(s):
    s = unicodedata.normalize('NFC', s)
    s = regex.sub(r'\s+', ' ', s).strip()
    return s
