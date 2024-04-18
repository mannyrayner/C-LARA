
from .clara_grapheme_phoneme_resources import get_aligned_entry_for_word_and_resources, get_phonetic_representation_for_word_and_resources
from .clara_grapheme_phoneme_resources import get_grapheme_phoneme_alignments_for_key_and_resources, get_encoding, phoneme_string_to_list

from .clara_classes import InternalCLARAError

import pprint

_trace = 'off'
#_trace = 'on'

def trace_on():
    global _trace
    _trace = 'on'

def trace_off():
    global _trace
    _trace = 'off'

def find_grapheme_phoneme_alignment_using_lexical_resources(Letters, Resources, guessed_aligned_entries_dict=None):
    #print(f'_trace: {_trace}')
    ExistingAlignedEntry = get_aligned_entry_for_word_and_resources(Letters, Resources)
    if ExistingAlignedEntry:
        return ExistingAlignedEntry
    Phonemes = get_phonetic_representation_for_word_and_resources(Letters, Resources)
    if not Phonemes:
        return None
    else:
        if _trace == 'on': print(f'--- Aligning "{Letters}" against "{Phonemes}"')
        Result = dp_phonetic_align(Letters, Phonemes, Resources)
        if Result and guessed_aligned_entries_dict != None:
            AlignedGraphemes, AlignedPhonemes = Result
            guessed_aligned_entries_dict[Letters] = { 'aligned_graphemes': AlignedGraphemes, 'aligned_phonemes': AlignedPhonemes }
        if _trace == 'on': print(f'--- Result "{Result}"')
        return Result
        
   
def dp_phonetic_align(Letters, Phonemes0, Resources):
    if Letters == '' and Phonemes0 == '':
        return ( '', '' )
    Encoding = get_encoding(Resources)
    Phonemes = phoneme_string_to_list(Phonemes0, Encoding)
    if _trace == 'on': print(f'--- Phonemes = {Phonemes}')
    ( N, N1 ) = ( len(Letters), len(Phonemes) )
    DPDict = {}
    DPDict[(0, 0)] = ( 0, [], [] )
    for TotalMatchLength in range(0, N + N1 ):
        for MatchLengthL in range(0, TotalMatchLength + 1):
            MatchLengthR = TotalMatchLength - MatchLengthL
            extend(Letters, Phonemes, MatchLengthL, MatchLengthR, N, N1, DPDict, Resources, Encoding)
    if ( N, N1 ) in DPDict:
        ( BestCost, BestAlignedLetters, BestAlignedPhonemes0 ) = dp_dict_lookup(DPDict, ( N, N1 ))
        if Encoding == 'arpabet_like':
            BestAlignedPhonemes = [ ' '.join(Phonemes) for Phonemes in BestAlignedPhonemes0 ]
        else:
            #BestAlignedPhonemes = BestAlignedPhonemes0
            BestAlignedPhonemes = [ ''.join(Phonemes) for Phonemes in BestAlignedPhonemes0 ]
        return ( '|'.join(BestAlignedLetters), '|'.join(BestAlignedPhonemes) )
    else:
        print(f'*** Error: unable to do DP match between "{Letters}" and "{Phonemes}"')
        if _trace == 'on':
            pprint.pprint(DPDict)
        return None

def extend(Letters, Phonemes, MatchLengthL, MatchLengthP, NL, NP, DPDict, Resources, Encoding):
    if _trace == 'on':
        print(f'--- extend(Letters = {Letters}, Phonemes = {Phonemes}, MatchLengthL = {MatchLengthL}, MatchLengthP = {MatchLengthP}, NL = {NL}, NP = {NP}, DPDict)')
    if MatchLengthL > NL or MatchLengthP > NP:
        if _trace == 'on': print(f'--- Length exceeded: MatchLengthL = {MatchLengthL}, NL = {NL}, MatchLengthP = {MatchLengthP}, NP = {NP}')
        return
    KeysL = [ '' ] if MatchLengthL == NL else [ '', Letters[MatchLengthL], 'skip' ]
    KeysP = [ '' ] if MatchLengthP == NP else [ '', Phonemes[MatchLengthP], 'skip' ]
    if _trace == 'on': print(f'--- KeysL = {KeysL}, KeysP = {KeysP}')
    for KeyL in KeysL:
        for KeyP in KeysP:
            if _trace == 'on': print(f'--- KeyL = "{KeyL}", KeyP = "{KeyP}"')
            # If we extend using a known match loaded from the aligned lexicon, we charge 2 if a null string is used, otherwise 1
            if KeyL != 'skip' and KeyP != 'skip':
                Key = ( KeyL, KeyP )
                PossibleAlignments = get_grapheme_phoneme_alignments_for_key_and_resources(Key, Resources)
                if _trace == 'on': print(f'--- Alignments for {Key}: {PossibleAlignments}')
                if PossibleAlignments:
                    for ( AlignedLetters, AlignedPhonemes ) in PossibleAlignments:
                        Cost = 2 if '' in ( AlignedLetters, AlignedPhonemes ) else 1
                        extend1(Letters, Phonemes, MatchLengthL, MatchLengthP, AlignedLetters, AlignedPhonemes, Cost, DPDict)
            # If we extend by skipping a character in either Letters or Phonemes (i.e. deletion/insertion), we charge 5 
            elif KeyL == 'skip' and KeyP == '':
                ( AlignedLetters, AlignedPhonemes, Cost ) = ( Letters[MatchLengthL], [], 5 )
                extend1(Letters, Phonemes, MatchLengthL, MatchLengthP, AlignedLetters, AlignedPhonemes, Cost, DPDict)
            elif KeyL == '' and KeyP == 'skip':
                ( AlignedLetters, AlignedPhonemes, Cost ) = ( '', [ Phonemes[MatchLengthP] ], 5 )
                extend1(Letters, Phonemes, MatchLengthL, MatchLengthP, AlignedLetters, AlignedPhonemes, Cost, DPDict)
            # If we skip in both (i.e. unknown substitution), we charge 4
            elif KeyL == 'skip' and KeyP == 'skip':
                ( AlignedLetters, AlignedPhonemes, Cost ) = ( Letters[MatchLengthL], [ Phonemes[MatchLengthP] ], 4 )
                extend1(Letters, Phonemes, MatchLengthL, MatchLengthP, AlignedLetters, AlignedPhonemes, Cost, DPDict)

def extend1(Letters, Phonemes, MatchLengthL, MatchLengthP, AlignedLetters, AlignedPhonemes, ExtraCost, DPDict):
    if _trace == 'on':
        print(f'--- extend1({Letters}, {Phonemes}, {MatchLengthL}, {MatchLengthP}, "{AlignedLetters}", "{AlignedPhonemes}", {ExtraCost}, DPDict)')
    # Recall that Phonemes can be a list if we're using an arpabet_like encoding, so we use the more general str_or_list_startswith on the Phonemes
    #if Letters[MatchLengthL:].startswith(AlignedLetters) and str_or_list_startswith(Phonemes[MatchLengthP:], AlignedPhonemes):
    if Letters[MatchLengthL:].startswith(AlignedLetters) and list_startswith(Phonemes[MatchLengthP:], AlignedPhonemes):
        if _trace == 'on':
            print(f'--- "{Letters[MatchLengthL:]}".startswith("{AlignedLetters}") and list_startswith("{Phonemes[MatchLengthP:]}", "{AlignedPhonemes}")') 
        ( CurrentCost, CurrentMatchL, CurrentMatchP ) = dp_dict_lookup(DPDict, ( MatchLengthL, MatchLengthP ))
        ( NewCost, NewMatchL, NewMatchP ) = ( CurrentCost + ExtraCost, CurrentMatchL + [ AlignedLetters ], CurrentMatchP + [ AlignedPhonemes ] )
        NewKey = ( MatchLengthL + len(AlignedLetters), MatchLengthP + len(AlignedPhonemes) )
        if not NewKey in DPDict or dp_dict_lookup(DPDict, NewKey)[0] > NewCost:
            DPDict[NewKey] = ( NewCost, NewMatchL, NewMatchP )
            if _trace == 'on':
                print(f'--- DPDict[{NewKey}] = ( {NewCost}, {NewMatchL}, {NewMatchP} )')
    else:
        if _trace == 'on':
            if not Letters[MatchLengthL:].startswith(AlignedLetters):
                print(f'--- {"Letters[MatchLengthL:]"}.startswith("{AlignedLetters}") failed')
            elif not list_startswith(Phonemes[MatchLengthP:], AlignedPhonemes):
                print(f'--- list_startswith("{Phonemes[MatchLengthP:]}", "{AlignedPhonemes}") failed')

##def str_or_list_startswith(StrOrList, StrOrListPrefix):
##    if isinstance(StrOrList, (str)) and isinstance(StrOrListPrefix, (str)):
##        return StrOrList.startswith(StrOrListPrefix)
##    elif isinstance(StrOrList, (list, tuple)) and isinstance(StrOrListPrefix, (list, tuple)):
##        return list_startswith(StrOrList, StrOrListPrefix)
##    else:
##        return False

def list_startswith(List, Prefix):
    if Prefix == []:
        return True
    elif List == []:
        return False
    elif List[0] != Prefix[0]:
        return False
    else:
        return list_startswith(List[1:], Prefix[1:])
    
def dp_dict_lookup(Dict, Key):
    if Key in Dict:
        return Dict[Key]
    else:
        if _trace == 'on': print(f'--- No entry in DPDict for {Key}, adding dummy value')
        ( CurrentCost, CurrentMatchL, CurrentMatchP ) = ( 1000, [], [] )
        return ( CurrentCost, CurrentMatchL, CurrentMatchP )

