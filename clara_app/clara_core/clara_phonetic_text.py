
from .clara_grapheme_phoneme_align import find_grapheme_phoneme_alignment_using_lexical_resources
from .clara_grapheme_phoneme_resources import grapheme_phoneme_alignment_available, load_grapheme_phoneme_lexical_resources
from .clara_grapheme_phoneme_resources import get_phonetic_representation_for_word, remove_accents_from_phonetic_string
from .clara_phonetic_orthography_repository import PhoneticOrthographyRepository
from .clara_phonetic_chatgpt4 import get_phonetic_entries_for_words_using_chatgpt4
from .clara_internalise import internalize_text
from .clara_classes import Text, Page, Segment, ContentElement, InternalCLARAError 
from .clara_utils import remove_duplicates_from_list_of_hashable_items

# ------------------------------------------

def segmented_text_to_phonetic_text(segmented_text, l2_language, config_info={}, callback=None):
    l1_language = None
    segmented_text_object = internalize_text(segmented_text, l2_language, l1_language, 'segmented')
    repository = PhoneticOrthographyRepository()
    
    orthography, accents = repository.get_parsed_entry(l2_language)
    if orthography:
        alphabet_internalised = internalise_alphabet_for_phonetically_spelled_language(orthography)
        parameters = ( 'phonetic_orthography', alphabet_internalised, accents )
    elif grapheme_phoneme_alignment_available(l2_language):
        load_grapheme_phoneme_lexical_resources(l2_language)
        chatgpt4_phonetic_entries = get_missing_phonetic_entries_for_segmented_text_object(segmented_text_object, l2_language,
                                                                                           config_info=config_info, callback=callback)
        parameters = ( 'grapheme_phoneme_alignment', l2_language, chatgpt4_phonetic_entries )
    else:
        return ''
    l1_language = None

    phonetic_text_object = segmented_text_object_to_phonetic_text_object(segmented_text_object, parameters)
    return phonetic_text_object.to_text(annotation_type='phonetic')
                                
def segmented_text_object_to_phonetic_text_object(segmented_text_object, parameters):
    phonetic_pages = []
    for page in segmented_text_object.pages:
        phonetic_segments = []
        for segment in page.segments:
            for content_element in segment.content_elements:
                if content_element.type == 'Word':
                    phonetic_segment = word_to_phonetic_segment(content_element.content, parameters)
                else:
                    phonetic_segment = Segment([content_element])
                phonetic_segments += [ phonetic_segment ]
        phonetic_pages += [ Page(phonetic_segments) ]
    return Text(phonetic_pages, segmented_text_object.l2_language, segmented_text_object.l1_language)

def word_to_phonetic_segment(word, parameters):
    word1 = normalise_word_for_phonetic_decomposition(word)
    aligned_word, aligned_phonetic = guess_alignment_for_word(word1, parameters)
    aligned_word1 = transfer_casing_to_aligned_word(word, aligned_word)
    word_components = aligned_word1.split('|')
    phonetic_components = aligned_phonetic.split('|')
    phonetic_components1 = [ '(silent)' if not component else component for component in phonetic_components ]
    #print(f'word_components: {word_components}')
    #print(f'phonetic_components1: {phonetic_components1}')
    phonetic_pairs = zip(word_components, phonetic_components1)
    phonetic_elements = [ word_phonetic_pair_to_element(phonetic_pair) for phonetic_pair in phonetic_pairs ]
    return Segment(phonetic_elements)

def normalise_word_for_phonetic_decomposition(word):
    return word.lower().replace("’", "'")

def word_phonetic_pair_to_element(pair):
    word, phonetic = pair
    return ContentElement('Word', word, annotations={'phonetic': phonetic})

def transfer_casing_to_aligned_word(word, aligned_word):
    try:
        return transfer_casing_to_aligned_word1(word, aligned_word)
    except:
        print(f'*** Error: bad call: transfer_casing_to_aligned_word({word}, {aligned_word})')
        return aligned_word

def transfer_casing_to_aligned_word1(word, aligned_word):
    aligned_word1 = ''
    for letter in aligned_word:
        if letter == '|':
            aligned_word1 += letter
        else:
            letter1 = word[0]
            aligned_word1 += letter1
            word = word[1:]
    return aligned_word1

# parameters is of one of the following forms:
#
# 1. ( 'phonetic_orthography', alphabet_internalised, accents  )
#
# 2. ( 'grapheme_phoneme_alignment', l2_language, chatgpt4_entries )
#     where chatgpt4_entries is a dict indexed with words, where the value is either a str or a list

def guess_alignment_for_word(word, parameters):
    if parameters[0] == 'phonetic_orthography':
        alphabet_internalised, accents = parameters[1:]
        return alignment_for_phonetically_spelled_language(word, alphabet_internalised, accents)
    elif parameters[0] == 'grapheme_phoneme_alignment':
        l2_language, chatgpt4_entries = parameters[1:]
        result = find_grapheme_phoneme_alignment_using_lexical_resources(word, l2_language, ExtraPhoneticEntries=chatgpt4_entries)
        if result:
            return result
        else:
            return ( word, word )
    
# ------------------------------------------

def get_missing_phonetic_entries_for_segmented_text_object(segmented_text, l2_language,
                                                           config_info={}, callback=None):
    elements = segmented_text.content_elements()
    words = [ normalise_word_for_phonetic_decomposition(element.content) for element in elements
              if element.type == 'Word' ] 
    unique_words = remove_duplicates_from_list_of_hashable_items(words)
    words_with_no_entries = [ word for word in unique_words
                              if not get_phonetic_representation_for_word(word, l2_language) ]
    annotated_words_dict, api_calls = get_phonetic_entries_for_words_using_chatgpt4(words_with_no_entries, l2_language, config_info=config_info, callback=callback)
    return { word: remove_accents_from_phonetic_string(annotated_words_dict[word]) for word in annotated_words_dict }

# ------------------------------------------

def alignment_for_phonetically_spelled_language(word, alphabet_internalised, accent_chars):
    ( decomposition_word, decomposition_phonetic ) = greedy_decomposition_of_word(word, alphabet_internalised, accent_chars)
    if decomposition_word == False:
        print(f'*** Warning: unable to spell out "{word}"')
        return ( word, word )
    word_with_separators = '|'.join(decomposition_word)
    phonetic_with_separators = '|'.join(decomposition_phonetic)
    return ( word_with_separators, phonetic_with_separators )

def greedy_decomposition_of_word(word, alphabet_internalised, accent_chars):
    ( decomposition_word, decomposition_phonetic ) = ( [], [] )
    while True:
        if word == '':
            return ( decomposition_word, decomposition_phonetic )
        possible_next_components = [ letter for letter in alphabet_internalised if word.startswith(letter) == True ] 
        if possible_next_components == []:
            print(f'*** Warning: unable to match "{word}" against alphabet')
            return ( False, False )
        sorted_possible_next_components = sorted(possible_next_components, key=lambda x: len(x), reverse=True)
        next_component = sorted_possible_next_components[0]
        accents = initial_accent_chars(word[len(next_component):], accent_chars)
        next_component_with_accents = next_component + accents
        decomposition_word += [ next_component_with_accents ]
        if not next_component in _hyphens_and_apostrophes:
            decomposition_phonetic += [ alphabet_internalised[next_component] ]
        else:
            decomposition_phonetic += [ '' ]
        word = word[len(next_component_with_accents):]
    # Shouldn't ever get here, but just in case...
    print(f'*** Warning: unable to match "{word}" against alphabet')
    return ( False, False )

def initial_accent_chars(string, accent_chars):
    if len(string) != 0 and string[0] in accent_chars:
        return string[0] + initial_accent_chars(str[1:], accent_chars)
    else:
        return ''

_half_space = "\u200c"

_hyphens_and_apostrophes = [ "-", "'", "’", _half_space ]

def internalise_alphabet_for_phonetically_spelled_language(orthography_list):
    orthography_list1 = orthography_list + [ { 'letter_variants': [ letter ], 'display_form': letter } for letter in _hyphens_and_apostrophes ]
    internalised = {}
    try:
        for item in orthography_list1:
            for letter in item['letter_variants']:
                internalised[letter] = item['display_form']
        return internalised
    except:
        raise InternalCLARAError(message = f'Malformed orthography data')
    


