
from .clara_internalise import internalize_text

def simplify_mwe_tagged_text(mwe_tagged_text):
    ( l2_language, l1_language ) = ( 'irrelevant', 'irrelevant' )
    text_object = internalize_text(mwe_tagged_text, l2_language, l1_language, 'mwe')
    simplify_mwe_tagged_text_object(text_object)
    return text_object.to_text(annotation_type='mwe')

def simplify_mwe_tagged_text_object(text_object):
    for page in text_object.pages:
        for segment in page.segments:
            if 'analysis' in segment.annotations:
                segment.annotations['analysis'] = '(removed)'

                
