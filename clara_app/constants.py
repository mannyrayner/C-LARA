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

SUPPORTED_LANGUAGES = [
    ('american english', 'American English'),
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
    ('italian', 'Italian'),
    ('japanese', 'Japanese'),
    ('korean', 'Korean'),
    ('latin', 'Latin'),
    ('malay', 'Malay'),
    ('mandarin', 'Mandarin'),
    ('māori', 'Māori'),
    ('norwegian', 'Norwegian'),
    ('old norse', 'Old Norse'),
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
]

SUPPORTED_LANGUAGES_AND_DEFAULT = [ ('default', 'Default') ] + SUPPORTED_LANGUAGES

SUPPORTED_LANGUAGES_AND_OTHER = SUPPORTED_LANGUAGES + [ ('other', 'Other') ]

