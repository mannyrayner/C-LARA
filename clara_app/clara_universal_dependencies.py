
def convert_tags_to_ud_v2_in_internalised_text(internalised_text):
    l2_language = internalised_text.l2_language
    if not language_with_conversion_function(l2_language):
        print(f'--- Warning: unable to convert tags to UD v2')
    else:
        for page in internalised_text.pages:
            for segment in page.segments:
                for content_element in segment.content_elements:
                    annotations = content_element.annotations
                    if 'pos' in annotations:
                        annotations['pos'] = convert_tag_to_ud_v2(l2_language, annotations['pos'])
    return internalised_text

def language_with_conversion_function(language):
    languages_covered = [ 'dutch',
                          'english',
                          'french',
                          'german',
                          'italian' ]
    return language in languages_covered

def convert_tag_to_ud_v2(language, tag):
    if language == 'dutch':
        return dutch_to_ud(tag)
    if language == 'english':
        return bnc_to_ud(tag)
    if language == 'french':
        return french_to_ud(tag)
    if language == 'german':
        return german_treetagger_to_ud(tag)
    if language == 'italian':
        return italian_treetagger_to_ud
    else:
        return tag

# Conversion tables by ChatGPT-4, so far unrevised

def bnc_to_ud(bnc_tag):
    mapping = {
        'AJ0': 'ADJ', 'AJC': 'ADJ', 'AJS': 'ADJ',
        'AT0': 'DET',
        'AV0': 'ADV', 'AVP': 'ADV', 'AVQ': 'ADV',
        'CJC': 'CCONJ', 'CJS': 'SCONJ', 'CJT': 'SCONJ',
        'CRD': 'NUM',
        'DPS': 'DET', 'DT0': 'DET', 'DTQ': 'DET',
        'EX0': 'ADV',
        'ITJ': 'INTJ',
        'NN0': 'NOUN', 'NN1': 'NOUN', 'NN2': 'NOUN',
        'NP0': 'PROPN',
        'ORD': 'ADJ',
        'PNI': 'PRON', 'PNP': 'PRON', 'PNQ': 'PRON', 'PNX': 'PRON',
        'POS': 'PART',
        'PRF': 'ADP', 'PRP': 'ADP',
        'PUL': 'PUNCT', 'PUN': 'PUNCT', 'PUQ': 'PUNCT', 'PUR': 'PUNCT',
        'TO0': 'PART',
        'UNC': 'X',
        'VBB': 'AUX', 'VBD': 'AUX', 'VBG': 'AUX', 'VBI': 'AUX', 'VBN': 'AUX', 'VBZ': 'AUX',
        'VDB': 'AUX', 'VDD': 'AUX', 'VDG': 'AUX', 'VDI': 'AUX', 'VDN': 'AUX', 'VDZ': 'AUX',
        'VHB': 'AUX', 'VHD': 'AUX', 'VHG': 'AUX', 'VHI': 'AUX', 'VHN': 'AUX', 'VHZ': 'AUX',
        'VM0': 'AUX',
        'VVB': 'VERB', 'VVD': 'VERB', 'VVG': 'VERB', 'VVI': 'VERB', 'VVN': 'VERB', 'VVZ': 'VERB',
        'XX0': 'PART',
        'ZZ0': 'SYM',
    }
    return mapping.get(bnc_tag, 'X')

def french_to_ud(french_tag):
    mapping = {
        'ABR': 'X',
        'ADJ': 'ADJ',
        'ADV': 'ADV',
        'DET:ART': 'DET',
        'DET:POS': 'PRON',
        'INT': 'INTJ',
        'KON': 'CCONJ',
        'NAM': 'PROPN',
        'NOM': 'NOUN',
        'NUM': 'NUM',
        'PRO': 'PRON',
        'PRO:DEM': 'PRON',
        'PRO:IND': 'PRON',
        'PRO:PER': 'PRON',
        'PRO:POS': 'PRON',
        'PRO:REL': 'PRON',
        'PRP': 'ADP',
        'PRP:det': 'ADP',
        'PUN': 'PUNCT',
        'PUN:cit': 'PUNCT',
        'SENT': 'PUNCT',
        'SYM': 'X',
        'VER:cond': 'AUX',
        'VER:futu': 'AUX',
        'VER:impe': 'AUX',
        'VER:impf': 'AUX',
        'VER:infi': 'AUX',
        'VER:pper': 'VERB',
        'VER:ppre': 'VERB',
        'VER:pres': 'VERB',
        'VER:simp': 'VERB',
        'VER:subi': 'AUX',
        'VER:subp': 'AUX'
    }
    return mapping.get(french_tag, 'X')

def dutch_to_ud(dutch_tag):
    mapping = {
        '$.': 'PUNCT',
        'adj': 'ADJ',
        'adj*kop': 'ADJ',
        'adjabbr': 'ADJ',
        'adv': 'ADV',
        'advabbr': 'ADV',
        'conjcoord': 'CCONJ',
        'conjsubo': 'SCONJ',
        'det__art': 'DET',
        'det__demo': 'DET',
        'det__indef': 'DET',
        'det__poss': 'DET',
        'det__quest': 'DET',
        'det__rel': 'DET',
        'int': 'INTJ',
        'noun*kop': 'NOUN',
        'nounabbr': 'NOUN',
        'nounpl': 'NOUN',
        'nounprop': 'PROPN',
        'nounsg': 'NOUN',
        'num__card': 'NUM',
        'num__ord': 'ADJ',
        'partte': 'PART',
        'prep': 'ADP',
        'prepabbr': 'ADP',
        'pronadv': 'PRON',
        'prondemo': 'PRON',
        'pronindef': 'PRON',
        'pronpers': 'PRON',
        'pronposs': 'PRON',
        'pronquest': 'PRON',
        'pronrefl': 'PRON',
        'pronrel': 'PRON',
        'punc': 'PUNCT',
        'verbinf': 'VERB',
        'verbpapa': 'VERB',
        'verbpastpl': 'VERB',
        'verbpastsg': 'VERB',
        'verbpresp': 'VERB',
        'verbprespl': 'VERB',
        'verbpressg': 'VERB'
    }
    return mapping.get(dutch_tag, 'X')

def italian_treetagger_to_ud(tag):
    mapping = {
        'ABR': 'X',
        'ADJ': 'ADJ',
        'ADV': 'ADV',
        'CON': 'CCONJ',
        'DET:def': 'DET',
        'DET:indef': 'DET',
        'FW': 'X',
        'INT': 'INTJ',
        'LS': 'SYM',
        'NOM': 'NOUN',
        'NPR': 'PROPN',
        'NUM': 'NUM',
        'PON': 'PUNCT',
        'PRE': 'ADP',
        'PRE:det': 'ADP',
        'PRO': 'PRON',
        'PRO:demo': 'PRON',
        'PRO:indef': 'PRON',
        'PRO:inter': 'PRON',
        'PRO:pers': 'PRON',
        'PRO:poss': 'PRON',
        'PRO:refl': 'PRON',
        'PRO:rela': 'PRON',
        'SENT': 'PUNCT',
        'SYM': 'SYM',
        'VER:cimp': 'VERB',
        'VER:cond': 'VERB',
        'VER:cpre': 'VERB',
        'VER:futu': 'VERB',
        'VER:geru': 'VERB',
        'VER:impe': 'VERB',
        'VER:impf': 'VERB',
        'VER:infi': 'VERB',
        'VER:pper': 'VERB',
        'VER:ppre': 'VERB',
        'VER:pres': 'VERB',
        'VER:refl:infi': 'VERB',
        'VER:remo': 'VERB',
    }
    return mapping.get(tag, 'X')

def german_treetagger_to_ud(tag):
    mapping = {
        'ADJA': 'ADJ',
        'ADJD': 'ADJ',
        'ADV': 'ADV',
        'APPR': 'ADP',
        'APPRART': 'ADP',
        'APPO': 'ADP',
        'APZR': 'ADP',
        'ART': 'DET',
        'CARD': 'NUM',
        'FM': 'X',
        'ITJ': 'INTJ',
        'KOUI': 'SCONJ',
        'KOUS': 'SCONJ',
        'KON': 'CCONJ',
        'KOKOM': 'CCONJ',
        'NN': 'NOUN',
        'NE': 'PROPN',
        'PDS': 'PRON',
        'PDAT': 'DET',
        'PIS': 'PRON',
        'PIAT': 'DET',
        'PIDAT': 'DET',
        'PPER': 'PRON',
        'PPOSS': 'PRON',
        'PPOSAT': 'DET',
        'PRELS': 'PRON',
        'PRELAT': 'DET',
        'PRF': 'PRON',
        'PWS': 'PRON',
        'PWAT': 'DET',
        'PWAV': 'ADV',
        'PAV': 'ADV',
        'PTKZU': 'PART',
        'PTKNEG': 'PART',
        'PTKVZ': 'PART',
        'PTKANT': 'PART',
        'PTKAP': 'PART',
        'TRUNC': 'X',
        'VVFIN': 'VERB',
        'VVIMP': 'VERB',
        'VVINF': 'VERB',
        'VVIZU': 'VERB',
        'VVPP': 'VERB',
        'VAFIN': 'AUX',
        'VAIMP': 'AUX',
        'VAINF': 'AUX',
        'VAPP': 'AUX',
        'VMFIN': 'AUX',
        'VMINF': 'AUX',
        'VMPP': 'AUX',
        'XY': 'X',
        'X': 'X',
        '$,': 'PUNCT',
        '$.': 'PUNCT',
        '$(': 'PUNCT',
    }
    return mapping.get(tag, 'X')
