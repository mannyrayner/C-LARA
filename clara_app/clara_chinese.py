
"""
- segment_text_using_jieba(text)
Use the Jieba package to segment a Chinese plain text string and produce a segmented text string.
Legacy code from LARA, slightly adapted.

- pinyin_tag_text_using_pypinyin(text)
Use pypinyin to add pinyin annotations to a Chinese segmented text string and produce a pinyin-annotated text string
"""

from pypinyin import pinyin, Style
import jieba
import regex

from .clara_internalise import internalize_text
from .clara_classes import Text, Page, Segment, ContentElement
from .clara_utils import print_and_flush

def is_chinese_language(LangId):
    return LangId in ( 'chinese', 'mandarin', 'cantonese', 'taiwanese', 'shanghaiese' )

def segment_text_using_jieba(InText):
    Sentences = sentence_segment_string(InText)
    SegmentedSentences = [ segment_sentence_using_jieba(Sentence) for Sentence in Sentences ]
    Segments = [ Segment for SegmentedSentence in SegmentedSentences for Segment in SegmentedSentence ]
    return apply_tokenise_result_to_string(Segments, InText)

# It's annoying that we're duplicating work done in add_end_of_segment_mark_to_punctuation_token_if_necessary.
# In LARA, we also needed to be able to use another Chinese tokeniser.
def sentence_segment_string(InStr):
    ( I, N, Sentences, CurrentSentence ) = ( 0, len(InStr), [], '' )
    while True:
        if I >= N:
            if CurrentSentence != '':
                Sentences += [ CurrentSentence ]
            return Sentences
        c1 = InStr[I]
        c2 = InStr[I+1] if I+1 < N else False
        if is_sentence_final_chinese_punctuation_mark(c1) and c2 != False and is_chinese_close_quote(c2):
            CurrentSentence += f'{c1}{c2}'
            Sentences += [ CurrentSentence ]
            CurrentSentence = ''
            I += 2
        elif is_sentence_final_chinese_punctuation_mark(c1):
            CurrentSentence += f'{c1}'
            Sentences += [ CurrentSentence ]
            CurrentSentence = ''
            I += 1
        else:
            CurrentSentence += c1
            I += 1
    # Should never get here but just in case
    return Sentences

def segment_sentence_using_jieba(Sentence):
    import jieba
    Segments = jieba.cut(Sentence, cut_all=False)
    SegmentsAsList = list(Segments)
    return consolidate_punctuation_tokens(SegmentsAsList)

def consolidate_punctuation_tokens(Segments):
    ( OutSegments, CurrentPunctuation ) = ( [], '' )
    for Segment in Segments:
        if punctuation_token(Segment):
            CurrentPunctuation += Segment
        else:
            if CurrentPunctuation != '':
                OutSegments += [ CurrentPunctuation]
                CurrentPunctuation = ''
            OutSegments += [ Segment ]
    if CurrentPunctuation != '':
        OutSegments += [ CurrentPunctuation]
    return OutSegments

def apply_tokenise_result_to_string(Tokens, InStr):
    ( I, N, OutStr ) = ( 0, len(InStr), '' )
    for Token in Tokens:
        NextI = InStr.find(Token, I)
        if NextI < I:
            print_and_flush(f'*** Warning: unable to find "{Token}" in text')
            break
        Skipped = InStr[I:NextI]
        I = NextI + len(Token)
        if punctuation_token(Token):
            Token1 = add_end_of_segment_mark_to_punctuation_token_if_necessary(Token)
            OutStr += f'{Skipped}{Token1}'
        else:
            OutStr += f'{Skipped}{Token}|'
    Rest = InStr[I:N]
    OutStr += Rest
    return OutStr

def punctuation_token(Token):        
    for Char in Token:
        if not is_chinese_punctuation_char(Char) and not Char.isspace():
            return False
    return True

def add_end_of_segment_mark_to_punctuation_token_if_necessary(Token):
    ( OutToken, I, N ) = ( '', 0, len(Token) )
    while True:
        if I >= N:
            return OutToken
        c1 = Token[I]
        c2 = Token[I+1] if I+1 < N else False
        if is_sentence_final_chinese_punctuation_mark(c1) and c2 != False and is_chinese_close_quote(c2):
            OutToken += f'{c1}{c2}||'
            I += 2
        elif is_sentence_final_chinese_punctuation_mark(c1):
            OutToken += f'{c1}||'
            I += 1
        else:
            OutToken += c1
            I += 1
    # Should never get here but just in case
    return OutToken

# ----------------------------------------------

def pinyin_tag_text_using_pypinyin(input_text):
    l2_language = 'mandarin'
    l1_language = 'irrelevant'
    text_object = internalize_text(input_text, l2_language, l1_language, 'segmented')

    out_pages = []
    for page in text_object.pages:
        out_segments = []
        for segment in page.segments:
            out_content_elements = []
            for content_element in segment.content_elements:
                out_content_element = pinyin_tagged_version_of_content_element(content_element)
                out_content_elements.append(out_content_element)
            out_segment = Segment(out_content_elements)
            out_segments.append(out_segment)
        out_page = Page(out_segments)
        out_pages.append(out_page)
    out_text_object = Text(out_pages, l2_language, l1_language)

    return out_text_object.to_text(annotation_type='pinyin')

# The output of calling pinyin on text looks like this:
#
# pinyin('中心')
# [['zhōng'], ['xīn']]
#
# We concatenate the first elements in each sublist with spaces between so that here we get "zhōng xīn"
def pinyin_tagged_version_of_content_element(content_element):
    if content_element.type == 'Word':
        pinyin_annotation = ' '.join([ item[0] for item in pinyin(content_element.content) ])
        content_element.annotations['pinyin'] = pinyin_annotation

    return content_element

# ----------------------------------------------

def is_chinese_punctuation_char(Char):
    return is_punctuation_char(Char) or Char in '。？！，、：”“'
    
def is_sentence_final_chinese_punctuation_mark(Char):
    return Char in '。？！'

def is_chinese_close_quote(Char):
    return Char in '”'

def is_punctuation_char(char):
    return regex.match(r"\p{P}", char)
