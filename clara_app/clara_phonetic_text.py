
from .clara_grapheme_phoneme_align import find_grapheme_phoneme_alignment_using_lexical_resources
from .clara_grapheme_phoneme_resources import grapheme_phoneme_resources_available, add_plain_entries_to_resources, remove_accents_from_phonetic_string
from .clara_grapheme_phoneme_resources import get_phonetic_lexicon_resources_for_words_and_l2, get_phonetic_representation_for_word_and_resources, get_encoding
from .clara_phonetic_orthography_repository import PhoneticOrthographyRepository, phonetic_orthography_resources_available
from .clara_phonetic_chatgpt4 import get_phonetic_entries_for_words_using_chatgpt4
from .clara_internalise import internalize_text
from .clara_classes import Text, Page, Segment, ContentElement, InternalCLARAError 
from .clara_utils import remove_duplicates_from_list_of_hashable_items, merge_dicts

import pprint

# ------------------------------------------

def segmented_text_to_phonetic_text(segmented_text, l2_language, config_info={}, callback=None):
    l1_language = None
    segmented_text_object = internalize_text(segmented_text, l2_language, l1_language, 'segmented')

    parameters = {}
    guessed_plain_entries = {}
    guessed_aligned_entries = {}
    api_calls = []
    
    if phonetic_orthography_resources_available(l2_language):
        repository = PhoneticOrthographyRepository()
        orthography, accents = repository.get_parsed_entry(l2_language)
        alphabet_internalised = internalise_alphabet_for_phonetically_spelled_language(orthography)
        phonetic_orthography_resources = { 'alphabet_internalised': alphabet_internalised, 'accents': accents }
        parameters['phonetic_orthography_resources'] = phonetic_orthography_resources
        
    if grapheme_phoneme_resources_available(l2_language):
        unique_words = get_unique_words_for_segmented_text_object(segmented_text_object)
        grapheme_phoneme_resources = get_phonetic_lexicon_resources_for_words_and_l2(unique_words, l2_language)
        #pprint.pprint(grapheme_phoneme_resources)
        
        chatgpt4_phonetic_entries, api_calls = get_missing_phonetic_entries_for_words_and_resources(unique_words, grapheme_phoneme_resources, l2_language,
                                                                                                    config_info=config_info, callback=callback)
        guessed_plain_entries = [ { 'word': word, 'phonemes': chatgpt4_phonetic_entries[word] }
                                  for word in chatgpt4_phonetic_entries ]
        full_grapheme_phoneme_resources = add_plain_entries_to_resources(grapheme_phoneme_resources, chatgpt4_phonetic_entries)
        parameters['grapheme_phoneme_alignment_resources'] = full_grapheme_phoneme_resources 

    if len(parameters) == 0:
        return { 'text': '',
                 'guessed_plain_entries': [],
                 'guessed_aligned_entries': [],
                 'api_calls': []}
    else:
        phonetic_text_object, guessed_aligned_entries = segmented_text_object_to_phonetic_text_object(segmented_text_object, parameters)
        phonetic_text = phonetic_text_object.to_text(annotation_type='phonetic')
        print(f'--- Guessed {len(guessed_plain_entries)} plain entries and {len(guessed_aligned_entries)} aligned entries')
        return { 'text': phonetic_text,
                 'guessed_plain_entries': guessed_plain_entries,
                 'guessed_aligned_entries': guessed_aligned_entries,
                 'api_calls': api_calls }
                                
def segmented_text_object_to_phonetic_text_object(segmented_text_object, parameters):
    guessed_aligned_entries_dict = {}
    phonetic_pages = []
    for page in segmented_text_object.pages:
        phonetic_segments = []
        for segment in page.segments:
            for content_element in segment.content_elements:
                if content_element.type == 'Word':
                    phonetic_segment = word_to_phonetic_segment(content_element.content, parameters, guessed_aligned_entries_dict)
                else:
                    phonetic_segment = Segment([content_element])
                phonetic_segments += [ phonetic_segment ]
        phonetic_pages += [ Page(phonetic_segments, annotations=page.annotations) ]
    guessed_aligned_entries_list = guessed_aligned_entries_dict_to_list(guessed_aligned_entries_dict)
    return ( Text(phonetic_pages, segmented_text_object.l2_language, segmented_text_object.l1_language),
             guessed_aligned_entries_list )

def guessed_aligned_entries_dict_to_list(guessed_aligned_entries_dict):
    return [ merge_dicts( { 'word': word }, guessed_aligned_entries_dict[word] )
             for word in guessed_aligned_entries_dict ]

def word_to_phonetic_segment(word, parameters, guessed_aligned_entries_dict):
    word1 = normalise_word_for_phonetic_decomposition(word)
    aligned_word, aligned_phonetic = guess_alignment_for_word(word1, parameters, guessed_aligned_entries_dict)
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
    if word in ( ' ', '-' ):
        return ContentElement('NonWordText', word)
    else:
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
# 2. ( 'grapheme_phoneme_alignment', resources )

def guess_alignment_for_word(word, parameters, guessed_aligned_entries_dict):
    # If we've already guessed an alignment for this word, use the same guess
    if word in guessed_aligned_entries_dict:
        previous_guessed_alignment = guessed_aligned_entries_dict[word]
        result = ( previous_guessed_alignment['aligned_graphemes'], previous_guessed_alignment['aligned_phonemes'] )
        return result

    # If we can split up the word, do each piece separately and then glue them back together again
    # Only do this when we are using the regular phonetic orthography method
    if 'phonetic_orthography_resources' in parameters:
        for separator in ( ' ', '-' ):
            components = word.split(separator)
            if len(components) > 1:
                results = [ guess_alignment_for_word(component, parameters, guessed_aligned_entries_dict)
                            for component in components ]
                #print(f'Component results: {results}')
                return ( f'|{separator}|'.join([ result[0] for result in results ]),
                         f'|{separator}|'.join([ result[1] for result in results ]) )

    result = None
    # If we can get an alignment using grapheme/phoneme alignment, use that
    if 'grapheme_phoneme_alignment_resources' in parameters:
        grapheme_phoneme_alignment_resources = parameters['grapheme_phoneme_alignment_resources']
        grapheme_phoneme_alignment_result = find_grapheme_phoneme_alignment_using_lexical_resources(word,
                                                                                                    grapheme_phoneme_alignment_resources,
                                                                                                    guessed_aligned_entries_dict=guessed_aligned_entries_dict)
        if grapheme_phoneme_alignment_result:
            return grapheme_phoneme_alignment_result

    # Otherwise, if we can get an alignment using phonetic orthography, use that
    if 'phonetic_orthography_resources' in parameters:
        phonetic_orthography_resources = parameters['phonetic_orthography_resources']
        alphabet_internalised = phonetic_orthography_resources['alphabet_internalised']
        accents = phonetic_orthography_resources['accents'] 
        phonetic_orthography_result = alignment_for_phonetically_spelled_language(word, alphabet_internalised, accents)
        if phonetic_orthography_result:
            return phonetic_orthography_result
        # Assume we don't need to check results of regular phonetic orthography alignment,
        # since if the phonetic entry is right there will only be one possibility.
        # So don't store in guessed_aligned_entries_dict
        
    # Otherwise give up and just align the word against itself
    else:
        if ' ' in word:
            return ( f'@{word}@', word )
        else:
            return ( word, word )
    
# ------------------------------------------

def get_missing_phonetic_entries_for_words_and_resources(unique_words, resources, l2_language,
                                                         config_info={}, callback=None):

    # For now, postpone the question of how to get gpt-4 to guess phonetic entries in non-IPA representations
    if get_encoding(resources) != 'ipa':
        return ( {}, [] )
    words_with_no_entries = [ word for word in unique_words
                              if not get_phonetic_representation_for_word_and_resources(word, resources) ]
    if not words_with_no_entries:
        return ( {}, [] )
    annotated_words_dict, api_calls = get_phonetic_entries_for_words_using_chatgpt4(words_with_no_entries, l2_language, config_info=config_info, callback=callback)
    return ( { word: cleaned_first_phonetic_entry(annotated_words_dict[word]) for word in annotated_words_dict },
             api_calls )

def cleaned_first_phonetic_entry(entry):
    if isinstance(entry, str):
        return remove_accents_from_phonetic_string(entry)
    elif isinstance(entry, ( list, tuple )):
        return cleaned_first_phonetic_entry(entry[0])

def get_unique_words_for_segmented_text_object(segmented_text):
    elements = segmented_text.content_elements()
    words = [ normalise_word_for_phonetic_decomposition(element.content) for element in elements
              if element.type == 'Word' ] 
    unique_words = remove_duplicates_from_list_of_hashable_items(words)
    return unique_words

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
    


