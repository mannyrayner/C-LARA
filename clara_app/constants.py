# clara_app/constants.py

TEXT_TYPE_CHOICES = [
    ('normal', 'Normal'),
    ('phonetic', 'Phonetic'),
]

SIMPLE_CLARA_TYPES = [
        ('create_text_and_image', 'Use the AI to create text and an image based on your instructions'),
        ('create_text_from_image', 'Upload an image and use the AI to create text from it'),
        ('annotate_existing_text', 'Paste in your own text and use the AI to convert it to multimodal form'),        
    ]

ACTIVITY_CATEGORY_CHOICES = [
    ('human_ai_interaction', 'Analysis of human/AI collaboration'),
    ('annotation', 'Annotation of texts by AI'),
    ('classroom', 'Classroom experiments'),
    ('creating_texts', 'Creation of texts by AI'),
    ('design', 'Design issues for C-LARA platform'),
    ('multimodal_formatting', 'Formatting/behaviour of multimodal texts'),
    ('languages_covered_by_ai', 'Languages covered by AI'),
    ('languages_not_covered_by_ai', 'Languages not covered by AI'),
    ('legacy_content', 'Legacy content'),
    ('legacy_software', 'Legacy software'),
    ('new_functionality', 'New C-LARA functionality not in other categories'),
    ('phonetic_texts', 'Phonetic texts'),
    ('publications_and_conferences', 'Publications, conferences and workshops'),
    ('refactoring', 'Refactoring software'),
    ('simple_clara', 'Simple C-LARA'),
    ('social_network', 'Social network'),
    ('other', 'Other'),
    ]

ACTIVITY_STATUS_CHOICES = [
    ('posted', 'Posted'),
    ('in_progress', 'In Progress'),
    ('resolved', 'Resolved'),
    ]

ACTIVITY_RESOLUTION_CHOICES = [
    ('unresolved', 'Unresolved'),
    ('solved', 'Solved'),
    ('wont_do', "Won't Do"),
    ]

RECENT_TIME_PERIOD_CHOICES = [
    (1, 'Last day'),
    (3, 'Last three days'),
    (7, 'Last week'),
    (31, 'Last month'),
    (93, 'Last three months'),
    ]

DEFAULT_RECENT_TIME_PERIOD = 3

SUPPORTED_LANGUAGES = [
    ('american english', 'American English'),
    ('ancient egyptian', 'Ancient Egyptian'),
    ('arabic', 'Arabic'),
    ('australian english', 'Australian English'),
    ('barngarla', 'Barngarla'),
    ('bengali', 'Bengali'),
    ('bulgarian', 'Bulgarian'),
    ('cantonese', 'Cantonese'),
    ('chinese', 'Chinese'),
    ('croatian', 'Croatian'),
    ('czech', 'Czech'),
    ('danish', 'Danish'),
    ('drehu', 'Drehu'),
    ('dutch', 'Dutch'),
    ('english', 'English'),
    ('esperanto', 'Esperanto'),
    ('faroese', 'Faroese'),
    ('farsi', 'Farsi'),
    ('finnish', 'Finnish'),
    ('french', 'French'),
    ('german', 'German'),
    ('greek', 'Greek'),
    ('hebrew', 'Hebrew'),
    ('hindi', 'Hindi'),
    ('hungarian', 'Hungarian'),
    ('iaai', 'Iaai'),
    ('icelandic', 'Icelandic'),
    ('indonesian', 'Indonesian'),
    ('irish', 'Irish'),
    ('italian', 'Italian'),
    ('japanese', 'Japanese'),
    ('korean', 'Korean'),
    ('latin', 'Latin'),
    ('malay', 'Malay'),
    ('mandarin', 'Mandarin'),
    ('māori', 'Māori'),
    ('norwegian', 'Norwegian'),
    ('old norse', 'Old Norse'),
    ('paicî', 'Paicî'),
    ('pitjantjatjara', 'Pitjantjatjara'),
    ('polish', 'Polish'),
    ('portuguese', 'Portuguese'),
    ('romanian', 'Romanian'),
    ('russian', 'Russian'),
    ('serbian', 'Serbian'),
    ('slovak', 'Slovak'),
    ('slovenian', 'Slovenian'),
    ('spanish', 'Spanish'),
    ('swedish', 'Swedish'),
    ('thai', 'Thai'),
    ('turkish', 'Turkish'),
    ('ukrainian', 'Ukrainian'),
    ('vietnamese', 'Vietnamese'),
    ('welsh', 'Welsh'),
    ('west greenlandic', 'West Greenlandic'),
]

SUPPORTED_LANGUAGES_AND_DEFAULT = [ ('default', 'Default') ] + SUPPORTED_LANGUAGES

SUPPORTED_LANGUAGES_AND_OTHER = SUPPORTED_LANGUAGES + [ ('other', 'Other') ]

TTS_CHOICES = [
    ( 'none', 'None' ),
    ( 'google', 'Google TTS' ),
    ( 'openai', 'OpenAI TTS' ),
    ( 'eleven_labs', 'Eleven Labs TTS' ),
    ( 'abair', 'ABAIR' ),
]
