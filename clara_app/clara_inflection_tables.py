
# Define the URLs for different languages
INFLECTION_TABLE_URLS = {
    'icelandic': 'http://bin.arnastofnun.is/leit/?q={}',
    #'old_norse': 'https://skaldic.abdn.ac.uk/m.php?p=lemma&i={}',
    'japanese': 'https://jisho.org/search/{}',
    'polish': 'http://sgjp.pl/leksemy/#{}',
    'german': 'https://www.verbformen.com/?w={}',
    'french': 'https://www.linternaute.fr/dictionnaire/fr/definition/{}/#conjugaison',
    'english': 'https://www.merriam-webster.com/dictionary/{}'
}

def get_inflection_table_url(lemma, language):
    if language in INFLECTION_TABLE_URLS:
        return INFLECTION_TABLE_URLS[language].format(lemma)
    return None
