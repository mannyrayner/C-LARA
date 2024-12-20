
from .clara_utils import write_txt_file

fifty_words = """Makerr (wind)
Mim-marpany (cyclone, rainbow snake)
Min-trraperriny (lightning)
Path-ch’rrich (sky)
Pathali (star)
Per (fire, firewood)
Pung (sun)
Wany (rain) 
Yirrmp (rain cloud)
Yok (tree)
Chel (eye)
Ch’kont (head)
Ch’rrich (leg)
Kaker (moon)
Kapew’rr (river)
Ko-minchen (saltwater barramundi)
Ko-ngamelngen (bull shark)
Kow (nose)
Koy (fish)
Kuch (stick, pencil)
Kulng (tooth)
Kutew (dog)
Ma-k’rreth (rice)
Ma-keyp’r (apple, native apple)
Ma-ngolkor (sugar)
Mar (hand, finger)
May (non protein food, vegetable food source)
Mim-pang’rr (long necked turtle)
Mim-parrcherr (saltwater crocodile)
Mim-peyu (freshwater crab)
Mim-pongkol (seawater turtle)
Ming-kular (plain wallaby, wallaby’s meat)
Miny (animal, animal food source)
Miny pikipik (wild pig, pig, ham, pig’s meat in general - except sausages)
Mirrm (hut, house)
Motika (car)
Ngolkor (sand)
Nyalp’r (tongue)
Pa-ch’lali (old woman)
Pa-kantherr (child)
Pa-ngamayerr (mother)
Pa-pingerr (father)
Pa-wegkena (old man)
Plinth’kel (ear)
Pirr (leaf)
Th’mel (foot)
Thaw (mouth)
Yarraman (horse)
Yengkay (water)
Yungkal (sea)"""

def parse_fifty_words():
    fifty_words_list = fifty_words.split('\n')
    fifty_words_parsed = [ parse_line(line) for line in fifty_words_list ]
    make_fifty_words_plain(fifty_words_parsed)
    make_fifty_words_segmented(fifty_words_parsed)
    make_fifty_words_glossed(fifty_words_parsed)

def parse_line(line):
    components = line.split('(')
    word = components[0].strip()
    translation = components[1].replace(')', '').strip()
    return { 'word': word, 'translation': translation }

def make_fifty_words_plain(fifty_words_parsed):
    text = '\n'.join([ parsed_line['word'] for parsed_line in fifty_words_parsed ])
    write_txt_file(text, '$CLARA/tmp/KokKaper/fifty_words_plain.txt')

def make_fifty_words_segmented(fifty_words_parsed):
    text = '\n'.join([ f"<page>@{parsed_line['word']}@||" for parsed_line in fifty_words_parsed ])
    write_txt_file(text, '$CLARA/tmp/KokKaper/fifty_words_segmented.txt')

def make_fifty_words_glossed(fifty_words_parsed):
    text = '\n'.join([ f"<page>@{parsed_line['word']}@#{parsed_line['translation']}#||" for parsed_line in fifty_words_parsed ])
    write_txt_file(text, '$CLARA/tmp/KokKaper/fifty_words_glossed.txt')
