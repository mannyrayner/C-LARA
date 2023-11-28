
from .clara_classes import InternalCLARAError
from .clara_utils import local_file_exists, read_local_json_file

def grapheme_phoneme_alignment_available(l2):
    return l2 in _plain_lexicon_files and l2 in _aligned_lexicon_files

def load_grapheme_phoneme_lexical_resources(l2):
    load_plain_grapheme_phoneme_lexicon(l2)
    load_aligned_grapheme_phoneme_lexicon(l2)

_plain_grapheme_phoneme_dicts = {}

_aligned_grapheme_phoneme_dicts = {}

_internalised_aligned_grapheme_phoneme_dicts = {}

_plain_lexicon_files = { 'english': '$CLARA/linguistic_data/english/en_UK_pronunciation_dict.json',
                         'french': '$CLARA/linguistic_data/french/fr_FR_pronunciation_dict.json' }

_aligned_lexicon_files = { 'english': '$CLARA/linguistic_data/english/en_UK_pronunciation_dict_aligned.json',
                           'french': '$CLARA/linguistic_data/french/fr_FR_pronunciation_dict_aligned.json' }

def load_plain_grapheme_phoneme_lexicon(l2):
    if l2 in _plain_grapheme_phoneme_dicts:
        return
    
    _plain_grapheme_phoneme_dicts[l2] = read_local_json_file(_plain_lexicon_files[l2])

def load_aligned_grapheme_phoneme_lexicon(l2):
    if l2 in _internalised_aligned_grapheme_phoneme_dicts:
        return
    
    _aligned_grapheme_phoneme_dicts[l2] = read_local_json_file(_aligned_lexicon_files[l2])
    internalised_aligned_lexicon = {}
    Data =  _aligned_grapheme_phoneme_dicts[l2]
    Count = 0
    for Word in Data:
        Value = Data[Word]
        if not isinstance(Value, list) or not len(Value) == 2 or not isinstance(Value[0], str) or not isinstance(Value[1], str):
            print(f'*** Warning: bad entry for "{Word}" in aligned {l2} lexicon, not a pair')
        ( Letters, Phonemes0 ) = Value
        Phonemes = remove_accents_from_phonetic_string(Phonemes0)
        ( LetterComponents, PhonemeComponents ) = ( Letters.split('|'), Phonemes.split('|') )
        if not len(LetterComponents) == len(PhonemeComponents):
            print(f'*** Warning: bad entry for "{Word}" in aligned {l2} lexicon, not aligned')
        for ( LetterGroup, PhonemeGroup ) in zip( LetterComponents, PhonemeComponents ):
            Key = ( '' if LetterGroup == '' else LetterGroup[0], '' if PhonemeGroup == '' else PhonemeGroup[0] )
            Current = internalised_aligned_lexicon[Key] if Key in internalised_aligned_lexicon else []
            Correspondence = ( LetterGroup, PhonemeGroup )
            if not Correspondence in Current:
                internalised_aligned_lexicon[Key] = Current + [ Correspondence ]
                Count += 1
    _internalised_aligned_grapheme_phoneme_dicts[l2] = internalised_aligned_lexicon
    print(f'--- Loaded aligned {l2} lexicon, {Count} different letter/phoneme correspondences')

def get_phonetic_representation_for_word(word, l2):
    if l2 in _plain_grapheme_phoneme_dicts and word in _plain_grapheme_phoneme_dicts[l2]:
        return remove_accents_from_phonetic_string(_plain_grapheme_phoneme_dicts[l2][word])
    else:
        return None

def grapheme_phoneme_alignments_for_key(key, l2):
    if l2 in _internalised_aligned_grapheme_phoneme_dicts and key in _internalised_aligned_grapheme_phoneme_dicts[l2]:
        return _internalised_aligned_grapheme_phoneme_dicts[l2][key]
    else:
        return []

def remove_accents_from_phonetic_string(Str):
    return Str.replace('ˈ', '').replace('ˌ', '').replace('.', '').replace('\u200d', '')
