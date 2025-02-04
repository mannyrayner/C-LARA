# clara_app/constants.py

TEXT_TYPE_CHOICES = [
    ('normal', 'Normal'),
    ('phonetic', 'Phonetic'),
]

SIMPLE_CLARA_TYPES = [
        ('create_text_and_image', 'Use the AI to create text and a single image based on your instructions'),
        ('create_text_and_multiple_images', 'Use the AI to create text and an image for each page based on your instructions'),
        ('create_text_from_image', 'Upload an image and use the AI to create text from it'),
        ('annotate_existing_text', 'Paste in your own text and use the AI to convert it to multimodal form'),        
    ]

ACTIVITY_CATEGORY_CHOICES = [
    ('human_ai_interaction', 'Analysis of human/AI collaboration'),
    ('annotation', 'Annotation of texts by AI'),
    ('classroom', 'Classroom experiments'),
    ('creating_images', 'Creating images'),
    ('creating_texts', 'Creation of texts by AI'),
    ('design', 'Design issues for C-LARA platform'),
    ('multimodal_formatting', 'Formatting/behaviour of multimodal texts'),
    ('languages_covered_by_ai', 'Languages covered by AI'),
    ('languages_not_covered_by_ai', 'Languages not covered by AI'),
    ('legacy_content', 'Legacy content'),
    ('legacy_software', 'Legacy software'),
    ('mwes', 'Multi-Word Expressions'),
    ('new_functionality', 'New C-LARA functionality not in other categories'),
    ('phonetic_texts', 'Phonetic texts'),
    ('publications_and_conferences', 'Publications, conferences and workshops'),
    ('refactoring', 'Refactoring software'),
    ('simple_clara', 'Simple C-LARA'),
    ('social_network', 'Social network'),
    ('ukrainian', 'Ukrainian learners'),
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

SUPPORTED_LANGUAGES_WITH_AI_ENABLED_STATUS = [
    ('american english', 'American English', True),
    ('ancient egyptian', 'Ancient Egyptian', False), #Not AI-enabled
    ('arabic', 'Arabic', True),
    ('australian english', 'Australian English', True),
    ('barngarla', 'Barngarla', False), #Not AI-enabled
    ('bengali', 'Bengali', True),
    ('bulgarian', 'Bulgarian', True),
    ('cantonese', 'Cantonese', True),
    ('chinese', 'Chinese', True),
    ('croatian', 'Croatian', True),
    ('czech', 'Czech', True),
    ('danish', 'Danish', True),
    ('drehu', 'Drehu', False), #Not AI-enabled
    ('dutch', 'Dutch', True),
    ('english', 'English', True),
    ('esperanto', 'Esperanto', True),
    ('estonian', 'Estonian', True),
    ('faroese', 'Faroese', True),
    ('farsi', 'Farsi', True),
    ('finnish', 'Finnish', True),
    ('french', 'French', True),
    ('german', 'German', True),
    ('greek', 'Greek', True),
    ('hebrew', 'Hebrew', True),
    ('hindi', 'Hindi', True),
    ('hungarian', 'Hungarian', True),
    ('iaai', 'Iaai', False), #Not AI-enabled
    ('icelandic', 'Icelandic', True),
    ('indonesian', 'Indonesian', True),
    ('irish', 'Irish', True),
    ('italian', 'Italian', True),
    ('japanese', 'Japanese', True),
    ('kok kaper', 'Kok Kaper', False), #Not AI-enabled
    ('korean', 'Korean', True),
    ('kunjen', 'Kunjen', False), #Not AI-enabled
    ('latin', 'Latin', True),
    ('malay', 'Malay', True),
    ('mandarin', 'Mandarin', True),
    ('māori', 'Māori', True),
    ('norwegian', 'Norwegian', True),
    ('old norse', 'Old Norse', True),
    ('paicî', 'Paicî', False), #Not AI-enabled
    ('pitjantjatjara', 'Pitjantjatjara', False), #Not AI-enabled
    ('polish', 'Polish', True),
    ('portuguese', 'Portuguese', True),
    ('romanian', 'Romanian', True),
    ('russian', 'Russian', True),
    ('serbian', 'Serbian', True),
    ('slovak', 'Slovak', True),
    ('slovenian', 'Slovenian', True),
    ('spanish', 'Spanish', True),
    ('swedish', 'Swedish', True),
    ('thai', 'Thai', True),
    ('turkish', 'Turkish', True),
    ('ukrainian', 'Ukrainian', True),
    ('vietnamese', 'Vietnamese', True),
    ('welsh', 'Welsh', True),
    ('west greenlandic', 'West Greenlandic', True),
    ('yirr yorront', 'Yirr Yorront', False), #Not AI-enabled
]

SUPPORTED_LANGUAGES = [ ( item[0], item[1] ) for item in SUPPORTED_LANGUAGES_WITH_AI_ENABLED_STATUS ]

SUPPORTED_LANGUAGES_AI_ENABLED_DICT = { item[0]: item[2] for item in SUPPORTED_LANGUAGES_WITH_AI_ENABLED_STATUS }

SUPPORTED_LANGUAGES_AND_DEFAULT = [ ('default', 'Default') ] + SUPPORTED_LANGUAGES

SUPPORTED_LANGUAGES_AND_OTHER = SUPPORTED_LANGUAGES + [ ('other', 'Other') ]

TTS_CHOICES = [
    ( 'none', 'None' ),
    ( 'google', 'Google TTS' ),
    ( 'openai', 'OpenAI TTS' ),
    ( 'eleven_labs', 'Eleven Labs TTS' ),
    ( 'abair', 'ABAIR' ),
    ]

SUPPORTED_MODELS_FOR_COHERENT_IMAGES_V2 = [
    ( 'gpt-4o', 'gpt-4o' ),
    ( 'o1-mini', 'o1-mini' )
    ]

SUPPORTED_PAGE_INTERPRETATION_PROMPTS_FOR_COHERENT_IMAGES_V2 = [
    ( 'default', 'Default' ),
    ( 'with_context', 'With context' ),
    ( 'with_context_v2',  'With context v2' ),
    ( 'multiple_questions', 'Multiple questions' )
    ]

SUPPORTED_PAGE_EVALUATION_PROMPTs_FOR_COHERENT_IMAGES_V2 = [
    ( 'default', 'Default' ),
    ( 'with_context_lenient', 'With context, lenient' )
    ]

