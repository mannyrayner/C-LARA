
from .clara_internalise import internalize_text
from .clara_classes import Text, Page, Segment, ContentElement
from .clara_utils import basename, get_image_dimensions

def test(id):
    if id == 'barngarla_welcome_to_country':
        input_file = '$CLARA/tmp/welcome_to_country_segmented.txt'
        output_file = '$CLARA/tmp/welcome_to_country_phonetic.txt'
        language = 'barngarla'
        segmented_text_file_to_phonetic_text_file(input_file, output_file, language)
    else:
        print(f'*** Error: unknown id "{Id}"')

# ------------------------------------------

def segmented_text_to_phonetic_text(segmented_text, l2_language):
    l1_language = None
    segmented_text_object = internalize_text(segmented_text, l2_language, l1_language, 'segmented')
    phonetic_text_object = segmented_text_object_to_phonetic_text_object(segmented_text_object)
    return phonetic_text_object.to_text(annotation_type='phonetic')
                                
def segmented_text_object_to_phonetic_text_object(segmented_text_object):
    language = segmented_text_object.l2_language
    phonetic_pages = []
    for page in segmented_text_object.pages:
        phonetic_segments = []
        for segment in page.segments:
            for content_element in segment.content_elements:
                if content_element.type == 'Word':
                    phonetic_segment = word_to_phonetic_segment(content_element.content, language)
                else:
                    phonetic_segment = Segment([content_element])
                phonetic_segments += [ phonetic_segment ]
        phonetic_pages += [ Page(phonetic_segments) ]
    return Text(phonetic_pages)

def word_to_phonetic_segment(word, language):
    word1 = normalise_word_for_phonetic_decomposition(word)
    aligned_word, aligned_phonetic = guess_alignment_for_word(word1, language)
    aligned_word1 = transfer_casing_to_aligned_word(word, aligned_word)
    word_components = aligned_word1.split('|')
    phonetic_components = aligned_phonetic.split('|')
    phonetic_pairs = zip(word_components, phonetic_components)
    phonetic_elements = [ word_phonetic_pair_to_element for phonetic_pair in phonetic_pairs ]
    return Segment(phonetic_elements)

def word_phonetic_pair_to_element(pair):
    word, phonetic = pair
    return ContentElement('Word', word, annotations={'phonetic': phonetic})

def transfer_casing_to_aligned_word(word, aligned_word):
    try:
        return transfer_casing_to_aligned_word1(word, aligned_word)
    except:
        lara_utils.print_and_flush(f'*** Error: bad call: transfer_casing_to_aligned_word({word}, {aligned_word})')
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

def guess_alignment_for_word(word, language):
    if phonetically_spelled_language(language):
        return alignment_for_phonetically_spelled_language(word, language)

# ------------------------------------------

# Temporary solution. Really we want some kind of repository object with content that can be edited through a view
_phonetically_spelled_languages = { 'barngarla': [ 'a', 'ai', 'aw',
                                                   'b', 'd',
                                                   'dy', 'dh', 'g', 'i',
                                                   'ii', 'l', 'ly', 'm',
                                                   'n', 'ng', 'nh', 'ny',
                                                   'oo', 'r', 'rr', 'rd',
                                                   'rl', 'rn', 'w', 'y'
                                                   ]
                                    }

_accent_chars = {}

def phonetically_spelled_language(language):
    if not Language in _phonetically_spelled_languages:
        return False
    alphabet = _phonetically_spelled_languages[language]
    alphabet_internalised = internalise_alphabet_for_phonetically_spelled_language(alphabet + _hyphens_and_apostrophes)
    if alphabet_internalised == False:
        print(f'*** Error: malformed phonetic list for "{Language}"')
        return False
    else:
        return True

def alignment_for_phonetically_spelled_language(word, language):
    alphabet = _phonetically_spelled_languages[language]
    accent_chars = _accent_chars[language] if language in _accent_chars else []
    ( decomposition_word, decomposition_phonetic ) = greedy_decomposition_of_word(Word, alphabet, accent_chars)
    if decomposition_word == False:
        print_and_flush(f'*** Warning: unable to spell out "{word}" as {language} word')
        return ( word, word )
    word_with_separators = '|'.join(decomposition_word)
    phonetic_with_separators = '|'.join(decomposition_phonetic)
    return ( word_with_separators, phonetic_with_separators )

_half_space = "\u200c"

_hyphens_and_apostrophes = [ "-", "'", "’", _half_space ]

def greedy_decomposition_of_word(word, alphabet, accent_chars):
    ( decomposition_word, decomposition_phonetic ) = ( [], [] )
    alphabet_internalised = internalise_alphabet_for_phonetically_spelled_language(alphabet + _hyphens_and_apostrophes)
    while True:
        if word == '':
            return ( decomposition_word, decomposition_phonetic )
        possible_next_components = [ letter for letter in alphabet_internalised if word.startswith(letter) == True ] 
        if possible_next_components == []:
            lara_utils.print_and_flush(f'*** Warning: unable to match "{word}" against alphabet')
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
    print_and_flush(f'*** Warning: unable to match "{word}" against alphabet')
    return ( False, False )

def initial_accent_chars(string, accent_chars):
    if len(string) != 0 and string[0] in accent_chars:
        return string[0] + initial_accent_chars(str[1:], accent_chars)
    else:
        return ''

def internalise_alphabet_for_phonetically_spelled_language(alphabet):
    internalised = {}
    for item in alphabet:
        if isinstance(item, ( str )):
            internalised[item] = item
        elif isinstance(item, ( list, tuple )) and len(item) != 0:
            main_letter = item[0]
            for letter in item:
                internalised[Letter] = main_letter
        else:
            print(f'*** Error: bad item in alphabet for phonetically spelled language: {item}')
            return False
    return internalised


