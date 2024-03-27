
from .clara_phonetic_lexicon_repository import PhoneticLexiconRepository
from .clara_classes import InternalCLARAError
from .clara_utils import local_file_exists, read_local_json_file, post_task_update, merge_dicts

def grapheme_phoneme_resources_available(l2):
    repository = PhoneticLexiconRepository()
    # Only request the plain entries, since initially there will be no aligned entries.
    #return repository.aligned_entries_exist_for_language(l2) and repository.plain_phonetic_entries_exist_for_language(l2)
    return repository.plain_phonetic_entries_exist_for_language(l2)

def get_phonetic_lexicon_resources_for_words_and_l2(words, l2, callback=None):
    encoding = get_phonetic_encoding_for_language(l2, callback=callback)
    plain_entries = get_plain_entries_for_words(words, l2, callback=callback)
    aligned_entries = get_aligned_entries_for_words(words, l2, callback=callback)
    internalised_aligned_lexicon = get_internalised_aligned_grapheme_phoneme_lexicon(l2, callback=callback)
    return { 'encoding': encoding,
             'plain_lexicon_entries': plain_entries,
             'aligned_lexicon_entries': aligned_entries,
             'internalised_aligned_lexicon': internalised_aligned_lexicon }

def get_phonetic_encoding_for_language(l2, callback=None):
    repository = PhoneticLexiconRepository()
    return repository.get_encoding_for_language(l2, callback=callback)

def add_plain_entries_to_resources(resources, new_plain_entries):
   resources['plain_lexicon_entries'] = merge_dicts(resources['plain_lexicon_entries'], new_plain_entries)
   return resources

def get_plain_entries_for_words(words, l2, callback=None):
    repository = PhoneticLexiconRepository()
    plain_entries = repository.get_plain_entries_batch(words, l2, callback=callback)
    data = { plain_entry['word']: plain_entry['phonemes']
             for plain_entry in plain_entries
             if plain_entry['status'] != 'generated' }
    post_task_update(callback, f'--- Found {len(data)} plain {l2} lexicon entries ({len(words)} words submitted)')
    return data

def get_aligned_entries_for_words(words, l2, callback=None):
    repository = PhoneticLexiconRepository()
    aligned_entries = repository.get_aligned_entries_batch(words, l2, callback=callback)
    data = { aligned_entry['word']: ( aligned_entry['aligned_graphemes'], aligned_entry['aligned_phonemes'] )
             for aligned_entry in aligned_entries
             if aligned_entry['status'] != 'generated' }
    post_task_update(callback, f'--- Found {len(data)} aligned {l2} lexicon entries ({len(words)} words submitted)')
    return data

def get_internalised_aligned_grapheme_phoneme_lexicon(l2, callback=None):
    repository = PhoneticLexiconRepository()
    aligned_entries = repository.get_all_aligned_entries_for_language(l2, callback=callback)
    encoding = repository.get_encoding_for_language(l2, callback=callback)
    data = { aligned_entry['word']: ( aligned_entry['aligned_graphemes'], aligned_entry['aligned_phonemes'] )
             for aligned_entry in aligned_entries
             if aligned_entry['status'] != 'generated' }
    internalised_lexicon, count = internalise_aligned_grapheme_phoneme_lexicon(data, l2, encoding)
    post_task_update(callback, f'--- Created internalised aligned {l2} lexicon, {count} different letter/phoneme correspondences')
    return internalised_lexicon

def get_encoding(resources):
    return resources['encoding'] if 'encoding' else None

def get_phonetic_representation_for_word_and_resources(word, resources):
    if 'plain_lexicon_entries' in resources and word in resources['plain_lexicon_entries']:
        return remove_accents_from_phonetic_string(resources['plain_lexicon_entries'][word])
    else:
        return None

def get_aligned_entry_for_word_and_resources(word, resources):
    if 'aligned_lexicon_entries' in resources and word in resources['aligned_lexicon_entries']:
        return resources['aligned_lexicon_entries'][word]
    else:
        return None

def get_grapheme_phoneme_alignments_for_key_and_resources(key, resources):
    if 'internalised_aligned_lexicon' in resources and key in resources['internalised_aligned_lexicon']:
        return resources['internalised_aligned_lexicon'][key]
    else:
        return []

def internalise_aligned_grapheme_phoneme_lexicon(Data, l2, Encoding):
    internalised_aligned_lexicon = {}
    Count = 0
    for Word in Data:
        Value = Data[Word]
        if not isinstance(Value, ( list, tuple )) or not len(Value) == 2 or not isinstance(Value[0], str) or not isinstance(Value[1], str):
            print(f'*** Warning: bad entry for "{Word}" in aligned {l2} lexicon, not a pair')
        ( Letters, Phonemes0 ) = Value
        Phonemes = remove_accents_from_phonetic_string(Phonemes0)
        ( LetterComponents, PhonemeComponents ) = ( Letters.split('|'), Phonemes.split('|') )
        if not len(LetterComponents) == len(PhonemeComponents):
            print(f'*** Warning: bad entry for "{Word}" in aligned {l2} lexicon, not aligned')
            continue
        for ( LetterGroup, PhonemeGroup ) in zip( LetterComponents, PhonemeComponents ):
            PhonemeGroupList = phoneme_string_to_list(PhonemeGroup, Encoding)
            Key = ( '' if LetterGroup == '' else LetterGroup[0],
                    '' if PhonemeGroup == '' else PhonemeGroupList[0] )
            Current = internalised_aligned_lexicon[Key] if Key in internalised_aligned_lexicon else []
            Correspondence = ( LetterGroup, PhonemeGroupList )
            if not Correspondence in Current:
                internalised_aligned_lexicon[Key] = Current + [ Correspondence ]
                Count += 1
    return ( internalised_aligned_lexicon, Count )
    
def remove_accents_from_phonetic_string(Str):
    #return Str.replace("'", '').replace('ˈ', '').replace('ˌ', '').replace('.', '').replace('\u200d', '').replace('²', '')
    _accent_chars = "'ˈˌ.\u200d²"
    for char in _accent_chars:
        Str = Str.replace(char, '')
    return Str

def phoneme_string_to_list(phoneme_string, encoding):
    # In an arbabet-like encoding, the phoneme string is a space-separated representation of phonemes
    if encoding == 'arpabet_like':
        return phoneme_string.split()
    # In an IPA encoding, we may have diacritics after phonemes (e.g. lengthening), which need to be combined with them
    else:
        phoneme_list = [ char for char in phoneme_string ]         
        return combine_phonemes_with_diacritics(phoneme_list)

# Note that the first two characters are not the same.
# The ipa-dict lexica are not consistent about the character used to indicate lengthening.
ipa_diacritics = ':ːʰ̥̩ ̯'

ipa_linking_diacritics = '͡'

def combine_phonemes_with_diacritics(phoneme_list):
    if len(phoneme_list) < 2:
        return phoneme_list
    # Phoneme followed by diacritic, e.g. Icelandic kʰ
    if phoneme_list[1] in ipa_diacritics:
        return [ f'{phoneme_list[0]}{phoneme_list[1]}' ] + combine_phonemes_with_diacritics(phoneme_list[2:])
    # Linked phonemes, e.g. German t͡s
    if len(phoneme_list) >= 3 and phoneme_list[1] in ipa_linking_diacritics:
        return [ f'{phoneme_list[0]}{phoneme_list[1]}{phoneme_list[2]}' ] + combine_phonemes_with_diacritics(phoneme_list[3:])
    # Phoneme surrounded by parentheses, e.g. Dutch (n)
    if len(phoneme_list) >= 3 and phoneme_list[0] == '(' and phoneme_list[2] == ')':
        return [ f'({phoneme_list[1]})' ] + combine_phonemes_with_diacritics(phoneme_list[3:])
    else:
        return [ phoneme_list[0] ] + combine_phonemes_with_diacritics(phoneme_list[1:])

##def first_phoneme_of_phoneme_string(Str, Encoding):
##    if Str == '':
##        return ''
##    # If encoding is 'ipa', each character is a phoneme
##    elif Encoding == 'ipa':
##        return Str[0]
##    # Assume arpabet_like, where we have space-separated phoneme representations
##    else:
##        return Str.split()[0]
