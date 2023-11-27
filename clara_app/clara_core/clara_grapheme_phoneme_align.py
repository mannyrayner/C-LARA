
from .clara_grapheme_phoneme_resources import load_grapheme_phoneme_lexical_resources, get_phonetic_representation_for_word, grapheme_phoneme_alignments_for_key

from .clara_classes import InternalCLARAError

_trace = 'off'

def find_grapheme_phoneme_alignment_using_lexical_resources(Letters, L2):
    load_grapheme_phoneme_lexical_resources(L2)

    Phonemes = get_phonetic_representation_for_word(Letters, L2)
    #print(f'--- Aligning "{Letters}" against "{Phonemes}"')
    if Phonemes:
        return dp_phonetic_align(Letters, Phonemes, L2)
    else:
        return None

def dp_phonetic_align(Letters, Phonemes, L2):
    if Letters == '' and Phonemes == '':
        return ( '', '' )
    ( N, N1 ) = ( len(Letters), len(Phonemes) )
    DPDict = {}
    DPDict[(0, 0)] = ( 0, [], [] )
    for TotalMatchLength in range(0, N + N1 ):
        for MatchLengthL in range(0, TotalMatchLength + 1):
            MatchLengthR = TotalMatchLength - MatchLengthL
            extend(Letters, Phonemes, MatchLengthL, MatchLengthR, N, N1, DPDict, L2)
    if ( N, N1 ) in DPDict:
        ( BestCost, BestAlignedLetters, BestAlignedPhonemes ) = DPDict[( N, N1 )]
        return ( '|'.join(BestAlignedLetters), '|'.join(BestAlignedPhonemes) )
    else:
        print(f'*** Error: unable to do DP match between "{Letters}" and "{Phonemes}"')
        return False

def extend(Letters, Phonemes, MatchLengthL, MatchLengthP, NL, NP, DPDict, L2):
    if _trace == 'on':
        print(f'--- extend({Letters}, {Phonemes}, {MatchLengthL}, {MatchLengthP}, {NL}, {NP}, DPDict)')
    if MatchLengthL > NL or MatchLengthP > NP:
        if _trace == 'on': print(f'--- Length exceeded')
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
                PossibleAlignments = grapheme_phoneme_alignments_for_key(Key, L2)
                if PossibleAlignments:
                    for ( AlignedLetters, AlignedPhonemes ) in PossibleAlignments:
                        Cost = 2 if '' in ( AlignedLetters, AlignedPhonemes ) else 1
                        extend1(Letters, Phonemes, MatchLengthL, MatchLengthP, AlignedLetters, AlignedPhonemes, Cost, DPDict)
            # If we extend by skipping a character in either Letters or Phonemes, we charge 5 
            elif KeyL == 'skip' and KeyP == '':
                ( AlignedLetters, AlignedPhonemes, Cost ) = ( Letters[MatchLengthL], '', 5 )
                extend1(Letters, Phonemes, MatchLengthL, MatchLengthP, AlignedLetters, AlignedPhonemes, Cost, DPDict)
            elif KeyL == '' and KeyP == 'skip':
                ( AlignedLetters, AlignedPhonemes, Cost ) = ( '', Phonemes[MatchLengthP], 5 )
                extend1(Letters, Phonemes, MatchLengthL, MatchLengthP, AlignedLetters, AlignedPhonemes, Cost, DPDict)

def extend1(Letters, Phonemes, MatchLengthL, MatchLengthP, AlignedLetters, AlignedPhonemes, ExtraCost, DPDict):
    if _trace == 'on':
        print(f'--- extend1({Letters}, {Phonemes}, {MatchLengthL}, {MatchLengthP}, "{AlignedLetters}", "{AlignedPhonemes}", {ExtraCost}, DPDict)')
    if Letters[MatchLengthL:].startswith(AlignedLetters) and Phonemes[MatchLengthP:].startswith(AlignedPhonemes):
        ( CurrentCost, CurrentMatchL, CurrentMatchP ) = DPDict[ ( MatchLengthL, MatchLengthP ) ]
        ( NewCost, NewMatchL, NewMatchP ) = ( CurrentCost + ExtraCost, CurrentMatchL + [ AlignedLetters ], CurrentMatchP + [ AlignedPhonemes ] )
        NewKey = ( MatchLengthL + len(AlignedLetters), MatchLengthP + len(AlignedPhonemes) )
        if not NewKey in DPDict or DPDict[NewKey][0] > NewCost:
            DPDict[NewKey] = ( NewCost, NewMatchL, NewMatchP )
