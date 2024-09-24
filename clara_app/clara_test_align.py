
from .clara_align_with_segmented import align_segmented_text_with_non_segmented_text

def test_kok_kaper1():
    segmented = """<h1>||Koyew @ngop’rrwiny@ nganthentu||</h1><page>
Pa nganhthentu la @yip’rri@ pangkent yentu.|| Koyew @ngop’rrwiny@ nganhthentu.||
<page>Kut yirrmp @thap’kany@ nhakal nganhthentu.|| @K’lawiny@ miny @trraperr’ny@ yongkorr.|| @Wakathak’l@ nganhthentu.||
<page>Koy @w’ti@ li @w’thent@, @yukarr’l@ @pit’ngamp’nt@ @karenhth’l@.|| @Th’merr@ @pit’winy@ nganhthentu.|| Pa-ngamayerr ngatherru, pa-yipeyerr ngatherru, @pa-yingkeng’yerr@ ngatherru.|| Pa kantherr nganhthentu kari kunchawiny.||
<page>@Pit’l@ nganhthentu.|| Kut nganhthentu @m’ngent@ pamel.||
<page>Pa la @warr’mp@ nyinawiny yurr la @yip’rri@? || @Ngop’rrwiny@ nganhthentu @m’lkany@ yongkorr koyew. || @Langk’rr@ nyinhey yurr @w’ti@.||
<page>Nganhthentu @th’merr@ @pit-pit@, path @kach’ker@.|| Ket.||
<page>
"""

    non_segmented = """<page><h1>||Koyew#Koyew/fish.PURP# @ngop’rrwiny@#-/be.in.water.PAST.PROGR# nganthentu#-/1.PL(Excl).NOM#||</h1>
<page>
Pa#-/CLASS.people# nganhthentu#-/1.PL(Excl).NOM# la#-/here# @yip’rri@#-/south# pangkent#-/hunt.PAST# yentu#-/n.Adv.in the past#.|| Koyew#-/fish.PURP# @ngop’rrwiny@#-/be.in.water.PAST.PROGR# nganhthentu#-/1.PL(Excl).NOM#.||

<page>Kut#/then# yirrmp#-/dark cloud# @thap’kany@#-/big# nhakal#-/see.PAST# nganhthentu#-/1.PL(Excl).NOM#.|| @K’lawiny@#-/go.PAST.PROGR# miny#-/CLASS.animal# @trraperr’ny@#-/lightning# yongkorr#-/with#.|| @Wakathak’l@#-/get out.PAST# nganhthentu#-/1.PL(Excl).NOM#.||

<page>Koy#-/fish# @w’ti@#-/neg# li#-/there# @w’thent@#-/cook.PAST#, @yukarr’l@#-/all# @pit’ngamp’nt@#-/bring back.PAST# @karenhth’l@#-/raw#.|| @Th’merr@#-/foot.INSTR# @pit’winy@#-/come back.PAST# nganhthentu#-/1PL(Excl).NOM#.|| Pa#-/CLASS.person#-ngamayerr#-/X# ngatherru#-/1.SG.POSS#, pa#-/CLASS.person#-yipeyerr#-/X# ngatherru#-/1.SG.POSS#, @pa-yingkeng’yerr@#-/younger sister# ngatherru#-/1.SG.POSS#.|| Pa#-/CLASS.person# kantherr#-/small# nganhthentu#-/1.PL(Excl).NOM# kari#-/many# kunchawiny#-/run.PAST.PROGR#.||

<page>@Pit’l@#-/return.PAST# nganhthentu#-/1.PL(Excl).NOM#.|| Kut#-/then# nganhthentu#-/1.PL(Excl).ACC?# @m’ngent@#-/meet.PAST# pamel#-/man.ERG#.||

<page>Pa#-/CLASS.person# la#-/here# @warr’mp@#-/where.LOC# nyinawiny#-/stay.PAST.PROGR# yurr#-/2.PL.NOM# la#-/here# @yip’rri@#-/south#? || @Ngop’rrwiny@#-/be.in.water.PAST.PROGR# nganhthentu#-/1.PL(Excl).NOM# @m’lkany@#-/fishing net# yongkorr#-/with# koyew#-/fish.PURP#. || @Langk’rr@#-/here# nyinhey#-/stay.IMP# yurr#-/2.PL.NOM# @w’ti@#-/NEG#.||

<page>Nganhthentu#-/X# @th’merr@#-/X# @pit-pit@#-/X#, path#-/X# @kach’ker@#-/X#.|| Ket#ket/X#.||

<page>
"""

    l2_language = "kok_kaper"
    l1_language = "english"
    text_type = "lemma"
    use_words_for_lemmas = False

    result = align_segmented_text_with_non_segmented_text(segmented, non_segmented,
                                                          l2_language, l1_language, text_type, use_words_for_lemmas=use_words_for_lemmas)

    print(f'result = "{result}"')

def test_kok_kaper1a():
    segmented = """<h1>||Koyew @ngop’rrwiny@ nganthentu||</h1>
<page>Pa nganhthentu la @yip’rri@ pangkent yentu.|| Koyew @ngop’rrwiny@ nganhthentu.||
<page>Kut yirrmp @thap’kany@ nhakal nganhthentu.|| @K’lawiny@ miny @trraperr’ny@ yongkorr.|| @Wakathak’l@ nganhthentu.||
<page>Koy @w’ti@ li @w’thent@, @yukarr’l@ @pit’ngamp’nt@ @karenhth’l@.|| @Th’merr@ @pit’winy@ nganhthentu.|| Pa-ngamayerr ngatherru, pa-yipeyerr ngatherru, @pa-yingkeng’yerr@ ngatherru.|| Pa kantherr nganhthentu kari kunchawiny.||
<page>@Pit’l@ nganhthentu.|| Kut nganhthentu @m’ngent@ pamel.||
<page>Pa la @warr’mp@ nyinawiny yurr la @yip’rri@? || @Ngop’rrwiny@ nganhthentu @m’lkany@ yongkorr koyew. || @Langk’rr@ nyinhey yurr @w’ti@.||
<page>Nganhthentu @th’merr@ @pit-pit@, path @kach’ker@.|| Ket.||
<page>
"""

    non_segmented = """<page><h1>||Koyew#Koyew/fish.PURP# @ngop’rrwiny@#-/be.in.water.PAST.PROGR# nganthentu#-/1.PL(Excl).NOM#||</h1>
<page>Pa#-/CLASS.people# nganhthentu#-/1.PL(Excl).NOM# la#-/here# @yip’rri@#-/south# pangkent#-/hunt.PAST# yentu#-/n.Adv.in the past#.|| Koyew#-/fish.PURP# @ngop’rrwiny@#-/be.in.water.PAST.PROGR# nganhthentu#-/1.PL(Excl).NOM#.||

<page>Kut#/then# yirrmp#-/dark cloud# @thap’kany@#-/big# nhakal#-/see.PAST# nganhthentu#-/1.PL(Excl).NOM#.|| @K’lawiny@#-/go.PAST.PROGR# miny#-/CLASS.animal# @trraperr’ny@#-/lightning# yongkorr#-/with#.|| @Wakathak’l@#-/get out.PAST# nganhthentu#-/1.PL(Excl).NOM#.||

<page>Koy#-/fish# @w’ti@#-/neg# li#-/there# @w’thent@#-/cook.PAST#, @yukarr’l@#-/all# @pit’ngamp’nt@#-/bring back.PAST# @karenhth’l@#-/raw#.|| @Th’merr@#-/foot.INSTR# @pit’winy@#-/come back.PAST# nganhthentu#-/1PL(Excl).NOM#.|| Pa#-/CLASS.person#-ngamayerr#-/X# ngatherru#-/1.SG.POSS#, pa#-/CLASS.person#-yipeyerr#-/X# ngatherru#-/1.SG.POSS#, @pa-yingkeng’yerr@#-/younger sister# ngatherru#-/1.SG.POSS#.|| Pa#-/CLASS.person# kantherr#-/small# nganhthentu#-/1.PL(Excl).NOM# kari#-/many# kunchawiny#-/run.PAST.PROGR#.||

<page>@Pit’l@#-/return.PAST# nganhthentu#-/1.PL(Excl).NOM#.|| Kut#-/then# nganhthentu#-/1.PL(Excl).ACC?# @m’ngent@#-/meet.PAST# pamel#-/man.ERG#.||

<page>Pa#-/CLASS.person# la#-/here# @warr’mp@#-/where.LOC# nyinawiny#-/stay.PAST.PROGR# yurr#-/2.PL.NOM# la#-/here# @yip’rri@#-/south#? || @Ngop’rrwiny@#-/be.in.water.PAST.PROGR# nganhthentu#-/1.PL(Excl).NOM# @m’lkany@#-/fishing net# yongkorr#-/with# koyew#-/fish.PURP#. || @Langk’rr@#-/here# nyinhey#-/stay.IMP# yurr#-/2.PL.NOM# @w’ti@#-/NEG#.||

<page>Nganhthentu#-/X# @th’merr@#-/X# @pit-pit@#-/X#, path#-/X# @kach’ker@#-/X#.|| Ket#ket/X#.||
<page>
"""

    l2_language = "kok_kaper"
    l1_language = "english"
    text_type = "lemma"
    use_words_for_lemmas = False

    result = align_segmented_text_with_non_segmented_text(segmented, non_segmented,
                                                          l2_language, l1_language, text_type, use_words_for_lemmas=use_words_for_lemmas)

    print(f'result = "{result}"')

def test_kok_kaper1c():
    segmented = """<page>Pa nganhthentu la @yip’rri@ pangkent yentu.|| Koyew @ngop’rrwiny@ nganhthentu.||
<page>Kut yirrmp @thap’kany@ nhakal nganhthentu.|| @K’lawiny@ miny @trraperr’ny@ yongkorr.|| @Wakathak’l@ nganhthentu.||
<page>Koy @w’ti@ li @w’thent@, @yukarr’l@ @pit’ngamp’nt@ @karenhth’l@.|| @Th’merr@ @pit’winy@ nganhthentu.|| Pa-ngamayerr ngatherru, pa-yipeyerr ngatherru, @pa-yingkeng’yerr@ ngatherru.|| Pa kantherr nganhthentu kari kunchawiny.||
<page>@Pit’l@ nganhthentu.|| Kut nganhthentu @m’ngent@ pamel.||
<page>Pa la @warr’mp@ nyinawiny yurr la @yip’rri@? || @Ngop’rrwiny@ nganhthentu @m’lkany@ yongkorr koyew. || @Langk’rr@ nyinhey yurr @w’ti@.||
<page>Nganhthentu @th’merr@ @pit-pit@, path @kach’ker@.|| Ket.||
<page>
"""

    non_segmented = """<page>Pa#-/CLASS.people# nganhthentu#-/1.PL(Excl).NOM# la#-/here# @yip’rri@#-/south# pangkent#-/hunt.PAST# yentu#-/n.Adv.in the past#.|| Koyew#-/fish.PURP# @ngop’rrwiny@#-/be.in.water.PAST.PROGR# nganhthentu#-/1.PL(Excl).NOM#.||

<page>Kut#/then# yirrmp#-/dark cloud# @thap’kany@#-/big# nhakal#-/see.PAST# nganhthentu#-/1.PL(Excl).NOM#.|| @K’lawiny@#-/go.PAST.PROGR# miny#-/CLASS.animal# @trraperr’ny@#-/lightning# yongkorr#-/with#.|| @Wakathak’l@#-/get out.PAST# nganhthentu#-/1.PL(Excl).NOM#.||

<page>Koy#-/fish# @w’ti@#-/neg# li#-/there# @w’thent@#-/cook.PAST#, @yukarr’l@#-/all# @pit’ngamp’nt@#-/bring back.PAST# @karenhth’l@#-/raw#.|| @Th’merr@#-/foot.INSTR# @pit’winy@#-/come back.PAST# nganhthentu#-/1PL(Excl).NOM#.|| Pa#-/CLASS.person#-ngamayerr#-/X# ngatherru#-/1.SG.POSS#, pa#-/CLASS.person#-yipeyerr#-/X# ngatherru#-/1.SG.POSS#, @pa-yingkeng’yerr@#-/younger sister# ngatherru#-/1.SG.POSS#.|| Pa#-/CLASS.person# kantherr#-/small# nganhthentu#-/1.PL(Excl).NOM# kari#-/many# kunchawiny#-/run.PAST.PROGR#.||

<page>@Pit’l@#-/return.PAST# nganhthentu#-/1.PL(Excl).NOM#.|| Kut#-/then# nganhthentu#-/1.PL(Excl).ACC?# @m’ngent@#-/meet.PAST# pamel#-/man.ERG#.||

<page>Pa#-/CLASS.person# la#-/here# @warr’mp@#-/where.LOC# nyinawiny#-/stay.PAST.PROGR# yurr#-/2.PL.NOM# la#-/here# @yip’rri@#-/south#? || @Ngop’rrwiny@#-/be.in.water.PAST.PROGR# nganhthentu#-/1.PL(Excl).NOM# @m’lkany@#-/fishing net# yongkorr#-/with# koyew#-/fish.PURP#. || @Langk’rr@#-/here# nyinhey#-/stay.IMP# yurr#-/2.PL.NOM# @w’ti@#-/NEG#.||

<page>Nganhthentu#-/X# @th’merr@#-/X# @pit-pit@#-/X#, path#-/X# @kach’ker@#-/X#.|| Ket#ket/X#.||
<page>
"""

    l2_language = "kok_kaper"
    l1_language = "english"
    text_type = "lemma"
    use_words_for_lemmas = False

    result = align_segmented_text_with_non_segmented_text(segmented, non_segmented,
                                                          l2_language, l1_language, text_type, use_words_for_lemmas=use_words_for_lemmas)

    print(f'result = "{result}"')


def test_kok_kaper2():
    segmented = """<page>Koy @w’ti@ li @w’thent@, @yukarr’l@ @pit’ngamp’nt@ @karenhth’l@.|| @Th’merr@ @pit’winy@ nganhthentu.|| Pa-ngamayerr ngatherru, pa-yipeyerr ngatherru, @pa-yingkeng’yerr@ ngatherru.|| Pa kantherr nganhthentu kari kunchawiny.||
<page>@Pit’l@ nganhthentu.|| Kut nganhthentu @m’ngent@ pamel.||
<page>Pa la @warr’mp@ nyinawiny yurr la @yip’rri@? || @Ngop’rrwiny@ nganhthentu @m’lkany@ yongkorr koyew. || @Langk’rr@ nyinhey yurr @w’ti@.||
<page>Nganhthentu @th’merr@ @pit-pit@, path @kach’ker@.|| Ket.||
<page>
"""

    non_segmented = """<page>Koy#-/fish# @w’ti@#-/neg# li#-/there# @w’thent@#-/cook.PAST#, @yukarr’l@#-/all# @pit’ngamp’nt@#-/bring back.PAST# @karenhth’l@#-/raw#.|| @Th’merr@#-/foot.INSTR# @pit’winy@#-/come back.PAST# nganhthentu#-/1PL(Excl).NOM#.|| Pa#-/CLASS.person#-ngamayerr#-/X# ngatherru#-/1.SG.POSS#, pa#-/CLASS.person#-yipeyerr#-/X# ngatherru#-/1.SG.POSS#, @pa-yingkeng’yerr@#-/younger sister# ngatherru#-/1.SG.POSS#.|| Pa#-/CLASS.person# kantherr#-/small# nganhthentu#-/1.PL(Excl).NOM# kari#-/many# kunchawiny#-/run.PAST.PROGR#.||

<page>@Pit’l@#-/return.PAST# nganhthentu#-/1.PL(Excl).NOM#.|| Kut#-/then# nganhthentu#-/1.PL(Excl).ACC?# @m’ngent@#-/meet.PAST# pamel#-/man.ERG#.||
<page>Pa#-/CLASS.person# la#-/here# @warr’mp@#-/where.LOC# nyinawiny#-/stay.PAST.PROGR# yurr#-/2.PL.NOM# la#-/here# @yip’rri@#-/south#? || @Ngop’rrwiny@#-/be.in.water.PAST.PROGR# nganhthentu#-/1.PL(Excl).NOM# @m’lkany@#-/fishing net# yongkorr#-/with# koyew#-/fish.PURP#. || @Langk’rr@#-/here# nyinhey#-/stay.IMP# yurr#-/2.PL.NOM# @w’ti@#-/NEG#.||

<page>Nganhthentu#-/X# @th’merr@#-/X# @pit-pit@#-/X#, path#-/X# @kach’ker@#-/X#.|| Ket#ket/X#.||

<page>
"""

    l2_language = "kok_kaper"
    l1_language = "english"
    text_type = "lemma"
    use_words_for_lemmas = False

    result = align_segmented_text_with_non_segmented_text(segmented, non_segmented,
                                                          l2_language, l1_language, text_type, use_words_for_lemmas=use_words_for_lemmas)

    print(f'result = "{result}"')

def test_kok_kaper3():
    segmented = """<h1>||Koyew @ngop’rrwiny@ nganthentu||</h1><page>
<page>Pa la @warr’mp@ nyinawiny yurr la @yip’rri@? || @Ngop’rrwiny@ nganhthentu @m’lkany@ yongkorr koyew. || @Langk’rr@ nyinhey yurr @w’ti@.||
<page>Nganhthentu @th’merr@ @pit-pit@, path @kach’ker@.|| Ket.||
<page>
"""

    non_segmented = """<page><h1>||Koyew#Koyew/fish.PURP# @ngop’rrwiny@#-/be.in.water.PAST.PROGR# nganthentu#-/1.PL(Excl).NOM#||</h1>
<page>

<page>Pa#-/CLASS.person# la#-/here# @warr’mp@#-/where.LOC# nyinawiny#-/stay.PAST.PROGR# yurr#-/2.PL.NOM# la#-/here# @yip’rri@#-/south#? || @Ngop’rrwiny@#-/be.in.water.PAST.PROGR# nganhthentu#-/1.PL(Excl).NOM# @m’lkany@#-/fishing net# yongkorr#-/with# koyew#-/fish.PURP#. || @Langk’rr@#-/here# nyinhey#-/stay.IMP# yurr#-/2.PL.NOM# @w’ti@#-/NEG#.||

<page>Nganhthentu#-/X# @th’merr@#-/X# @pit-pit@#-/X#, path#-/X# @kach’ker@#-/X#.|| Ket#ket/X#.||

<page>
"""

    l2_language = "kok_kaper"
    l1_language = "english"
    text_type = "lemma"
    use_words_for_lemmas = False

    result = align_segmented_text_with_non_segmented_text(segmented, non_segmented,
                                                          l2_language, l1_language, text_type, use_words_for_lemmas=use_words_for_lemmas)

    print(f'result = "{result}"')

def test_kok_kaper4():
    segmented = """Pa nganhthentu la @yip’rri@ pangkent yentu.|| Koyew @ngop’rrwiny@ nganhthentu.||
<page>Koy @w’ti@ li @w’thent@, @yukarr’l@ @pit’ngamp’nt@ @karenhth’l@.|| @Th’merr@ @pit’winy@ nganhthentu.|| Pa-ngamayerr ngatherru, pa-yipeyerr ngatherru, @pa-yingkeng’yerr@ ngatherru.|| Pa kantherr nganhthentu kari kunchawiny.||
<page>@Pit’l@ nganhthentu.|| Kut nganhthentu @m’ngent@ pamel.||
<page>Pa la @warr’mp@ nyinawiny yurr la @yip’rri@? || @Ngop’rrwiny@ nganhthentu @m’lkany@ yongkorr koyew. || @Langk’rr@ nyinhey yurr @w’ti@.||
<page>Nganhthentu @th’merr@ @pit-pit@, path @kach’ker@.|| Ket.||
<page>
"""

    non_segmented = """<page>
Pa#-/CLASS.people# nganhthentu#-/1.PL(Excl).NOM# la#-/here# @yip’rri@#-/south# pangkent#-/hunt.PAST# yentu#-/n.Adv.in the past#.|| Koyew#-/fish.PURP# @ngop’rrwiny@#-/be.in.water.PAST.PROGR# nganhthentu#-/1.PL(Excl).NOM#.||
<page>Koy#-/fish# @w’ti@#-/neg# li#-/there# @w’thent@#-/cook.PAST#, @yukarr’l@#-/all# @pit’ngamp’nt@#-/bring back.PAST# @karenhth’l@#-/raw#.|| @Th’merr@#-/foot.INSTR# @pit’winy@#-/come back.PAST# nganhthentu#-/1PL(Excl).NOM#.|| Pa#-/CLASS.person#-ngamayerr#-/X# ngatherru#-/1.SG.POSS#, pa#-/CLASS.person#-yipeyerr#-/X# ngatherru#-/1.SG.POSS#, @pa-yingkeng’yerr@#-/younger sister# ngatherru#-/1.SG.POSS#.|| Pa#-/CLASS.person# kantherr#-/small# nganhthentu#-/1.PL(Excl).NOM# kari#-/many# kunchawiny#-/run.PAST.PROGR#.||

<page>@Pit’l@#-/return.PAST# nganhthentu#-/1.PL(Excl).NOM#.|| Kut#-/then# nganhthentu#-/1.PL(Excl).ACC?# @m’ngent@#-/meet.PAST# pamel#-/man.ERG#.||
<page>Pa#-/CLASS.person# la#-/here# @warr’mp@#-/where.LOC# nyinawiny#-/stay.PAST.PROGR# yurr#-/2.PL.NOM# la#-/here# @yip’rri@#-/south#? || @Ngop’rrwiny@#-/be.in.water.PAST.PROGR# nganhthentu#-/1.PL(Excl).NOM# @m’lkany@#-/fishing net# yongkorr#-/with# koyew#-/fish.PURP#. || @Langk’rr@#-/here# nyinhey#-/stay.IMP# yurr#-/2.PL.NOM# @w’ti@#-/NEG#.||

<page>Nganhthentu#-/X# @th’merr@#-/X# @pit-pit@#-/X#, path#-/X# @kach’ker@#-/X#.|| Ket#ket/X#.||

<page>
"""

    l2_language = "kok_kaper"
    l1_language = "english"
    text_type = "lemma"
    use_words_for_lemmas = False

    result = align_segmented_text_with_non_segmented_text(segmented, non_segmented,
                                                          l2_language, l1_language, text_type, use_words_for_lemmas=use_words_for_lemmas)

    print(f'result = "{result}"')

    
