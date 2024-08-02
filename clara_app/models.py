from django.db import models
from django.urls import reverse

from .constants import TEXT_TYPE_CHOICES, SUPPORTED_LANGUAGES, SUPPORTED_LANGUAGES_AND_DEFAULT, SUPPORTED_LANGUAGES_AND_OTHER, SIMPLE_CLARA_TYPES
from .constants import ACTIVITY_CATEGORY_CHOICES, ACTIVITY_STATUS_CHOICES, ACTIVITY_RESOLUTION_CHOICES
from .constants import TTS_CHOICES

from django.contrib.auth.models import User, Group, Permission 
from django.db import models

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
 
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    is_admin = models.BooleanField(default=False)
    is_moderator = models.BooleanField(default=False)
    is_funding_reviewer = models.BooleanField(default=False)
    is_questionnaire_reviewer = models.BooleanField(default=False)
    credit = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    is_private = models.BooleanField(default=False)

    def is_language_master(self):
        return self.user.language_master_set.exists()

class FriendRequest(models.Model):
    STATUS_CHOICES = [
        ('SENT', 'Sent'),
        ('ACCEPTED', 'Accepted'),
        ('DECLINED', 'Declined'),
        ('CANCELED', 'Canceled'),
    ]

    sender = models.ForeignKey(User, related_name='friend_requests_sent', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='friend_requests_received', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='SENT')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('sender', 'receiver')

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username}: {self.status}"

class UserConfiguration(models.Model):
    CLARA_VERSION_CHOICES = [
        ('simple_clara', 'Simple C-LARA'),
        ('full_clara', 'Full C-LARA'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    clara_version = models.CharField(max_length=20, choices=CLARA_VERSION_CHOICES, default='full_clara')
    open_ai_api_key = models.CharField(max_length=200, blank=True, null=True)
    gpt_model = models.CharField(max_length=50, default='gpt-4-1106-preview')
    max_annotation_words = models.IntegerField(default=250)

class LanguageMaster(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='language_master_set')
    language = models.CharField(max_length=50, choices=SUPPORTED_LANGUAGES_AND_DEFAULT)

    #class Meta:
    #    unique_together = ['user', 'language']

class CLARAProject(models.Model):
    title = models.CharField(max_length=200)
    internal_id = models.CharField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    l2 = models.CharField(max_length=50, choices=SUPPORTED_LANGUAGES)
    l1 = models.CharField(max_length=50, choices=SUPPORTED_LANGUAGES)
    simple_clara_type = models.CharField(max_length=50, choices=SIMPLE_CLARA_TYPES, default='create_text_and_image')
    uses_coherent_image_set = models.BooleanField(default=False, help_text="Specifies whether the project uses a coherent AI-generated image set.")
    use_translation_for_images = models.BooleanField(default=False, help_text="Use translations for generating coherent image sets.")

# Move this to utils.py to avoid circular import

##    def has_saved_internalised_and_annotated_text(self, phonetic=False):
##        clara_project_internal = CLARAProjectInternal(self.internal_id, self.l2, self.l1)
##        return clara_project_internal.get_saved_internalised_and_annotated_text(phonetic=phonetic)
    
class ProjectPermissions(models.Model):
    ROLE_CHOICES = [
        ('OWNER', 'Owner'),
        ('ANNOTATOR', 'Annotator'),
        ('VIEWER', 'Viewer'),
        # More roles as needed...
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(CLARAProject, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    class Meta:
        unique_together = ("user", "project")

class Acknowledgements(models.Model):
    project = models.OneToOneField('CLARAProject', on_delete=models.CASCADE, related_name='acknowledgements')
    short_text = models.TextField("Short Acknowledgements Text", blank=True,
                                  help_text="To appear in the footer of every page.")
    long_text = models.TextField("Long Acknowledgements Text", blank=True,
                                 help_text="To be included once in the final rendered text.")
    long_text_location = models.CharField("Location of Long Acknowledgements", max_length=20,
                                          choices=[('first_page', 'Bottom of First Page'),
                                                   ('extra_page', 'Extra Page at End')], blank=True)

    # Timestamps for dependency tracking
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return f"Acknowledgements for {self.project.title}"

# This is used if we have human-recorded audio instead of TTS
class HumanAudioInfo(models.Model):
    # Choices for the 'method' field
    METHOD_CHOICES = [
        ('tts_only', 'TTS only'),
        ('upload', 'Upload'),
        #('record', 'Record'),
        ('manual_align', 'Manual Align'),
        #('automatic_align', 'Automatic Align'),
    ]

    VOICE_CHOICES = [
        ( 'none', 'None' ),
        ( 'alloy', 'Alloy (OpenAI)' ),
        ( 'echo', 'Echo (OpenAI)' ),
        ( 'fable', 'Fable (OpenAI)' ),
        ( 'onyx', 'Onyx (OpenAI)' ),
        ( 'nova', 'Nova (OpenAI)' ),
        ( 'shimmer', 'Shimmer (OpenAI)' ),
        ( 'ga_UL_anb_nemo', 'ga_UL_anb_nemo (ABAIR)' ),
        ( 'ga_UL_anb_exthts', 'ga_UL_anb_exthts (ABAIR)' ),
        ( 'ga_UL_anb_piper', 'ga_UL_anb_piper (ABAIR)' ),
        ( 'ga_CO_snc_nemo', 'ga_CO_snc_nemo (ABAIR)' ),
        ( 'ga_CO_snc_exthts', 'ga_CO_snc_exthts (ABAIR)' ),
        ( 'ga_CO_snc_piper', 'ga_CO_snc_piper (ABAIR)' ),
        ( 'ga_CO_pmc_exthts', 'ga_CO_pmc_exthts (ABAIR)' ),
        ( 'ga_CO_pmc_nemo', 'ga_CO_pmc_nemo (ABAIR)' ),
        ( 'ga_MU_nnc_nemo', 'ga_MU_nnc_nemo (ABAIR)' ),
        ( 'ga_MU_nnc_exthts', 'ga_MU_nnc_exthts (ABAIR)' ),
        ( 'ga_MU_dms_nemo', 'ga_MU_dms_nemo (ABAIR)' ),
        ( 'ga_MU_dms_piper', 'ga_MU_dms_piper (ABAIR)' ),
    ]
    
    # Fields
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    preferred_tts_engine = models.CharField(max_length=20, choices=TTS_CHOICES, default='none')
    preferred_tts_voice = models.CharField(max_length=20, choices=VOICE_CHOICES, default='none')
    use_for_segments = models.BooleanField(default=False)
    use_for_words = models.BooleanField(default=False)
    use_context = models.BooleanField(default=False)
    voice_talent_id = models.CharField(max_length=200, default='anonymous')
    audio_file = models.CharField(max_length=500, blank=True, null=True)
    manual_align_metadata_file = models.CharField(max_length=500, blank=True, null=True)
    # Timestamps for dependency tracking
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    
    # Relationship with CLARAProject
    project = models.OneToOneField(
        'CLARAProject', 
        on_delete=models.CASCADE, 
        related_name='human_audio_info'
    )

    def __str__(self):
        return f"Human Audio Info for {self.project.title}"

# Simpler version of above for phonetic info
class PhoneticHumanAudioInfo(models.Model):
    # Choices for the 'method' field
    METHOD_CHOICES = [
        ('upload_individual', 'Upload single files'),
        ('upload_zipfile', 'Upload zipfile with metadata'),
    ]

    TTS_CHOICES = [
        ( 'none', 'None' ),
    ]

    VOICE_CHOICES = [
        ( 'none', 'None' ),
    ]
    
    # Fields
    method = models.CharField(max_length=40, choices=METHOD_CHOICES, default='upload_individual')
    preferred_tts_engine = models.CharField(max_length=20, choices=TTS_CHOICES, default='none')
    preferred_tts_voice = models.CharField(max_length=20, choices=VOICE_CHOICES, default='none')
    use_for_segments = models.BooleanField(default=False)
    use_for_words = models.BooleanField(default=True)
    voice_talent_id = models.CharField(max_length=200, default='anonymous')
    # Timestamps for dependency tracking
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    # Relationship with CLARAProject
    project = models.OneToOneField(
        'CLARAProject', 
        on_delete=models.CASCADE, 
        related_name='phonetic_human_audio_info'
    )

    def __str__(self):
        return f"Phonetic Human Audio Info for {self.project.title}"
        
class CLARAProjectAction(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('edit', 'Edit'),
    ]

    TEXT_VERSION_CHOICES = [
        ('plain', 'Plain'),
        ('segmented', 'Segmented'),
        ('gloss', 'Gloss'),
        ('lemma', 'Lemma'),
    ]

    project = models.ForeignKey(CLARAProject, on_delete=models.CASCADE)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    text_version = models.CharField(max_length=50, choices=TEXT_VERSION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-timestamp']

class FormatPreferences(models.Model):
    project = models.OneToOneField(CLARAProject, on_delete=models.CASCADE, related_name='format_preferences')
    
    font_type = models.CharField(max_length=50, choices=[('sans-serif', 'Sans Serif'), ('serif', 'Serif')], default='serif')
    font_size = models.CharField(max_length=50,
                                 choices=[('small', 'Small'), ('medium', 'Medium'), ('large', 'Large'), ('huge', 'Huge'), ('HUGE', 'HUGE')],
                                 default='medium')
    text_align = models.CharField(max_length=50, choices=[('left', 'Left'), ('center', 'Center'), ('right', 'Right')], default='left')

    concordance_font_type = models.CharField(max_length=50, choices=[('sans-serif', 'Sans Serif'), ('serif', 'Serif')], default='serif')
    concordance_font_size = models.CharField(max_length=50, choices=[('small', 'Small'), ('medium', 'Medium'), ('large', 'Large')], default='medium')
    concordance_text_align = models.CharField(max_length=50, choices=[('left', 'Left'), ('center', 'Center'), ('right', 'Right')], default='left')

    # Timestamps for dependency tracking
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def to_dict(self):
        return { 'font_type': self.font_type,
                 'font_size': self.font_size,
                 'text_align': self.text_align,

                 'concordance_font_type': self.concordance_font_type,
                 'concordance_font_size': self.concordance_font_size,
                 'concordance_text_align': self.concordance_text_align,
                 }

    def __str__(self):
        return f"Format Preferences for {self.project.title}"

class Content(models.Model):
    external_url = models.URLField(max_length=255, blank=True, null=True)
    project = models.OneToOneField(CLARAProject, on_delete=models.CASCADE, null=True, blank=True, unique=True, related_name='related_content')
    title = models.CharField(max_length=255)
    text_type = models.CharField(max_length=10, choices=TEXT_TYPE_CHOICES, default='normal')
    l2 = models.CharField(max_length=100, verbose_name='L2 Language')
    l1 = models.CharField(max_length=100, verbose_name='L1 Language')
    length_in_words = models.IntegerField()
    author = models.CharField(max_length=255)
    voice = models.CharField(max_length=255)
    annotator = models.CharField(max_length=255)
    difficulty_level = models.CharField(max_length=100)
    summary = models.TextField(default='', blank=True)
    # Timestamps for dependency tracking
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    unique_access_count = models.IntegerField(default=0)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('content_detail', args=[str(self.id)])

    def get_public_absolute_url(self):
        return reverse('public_content_detail', args=[str(self.id)])
        
    def url(self):
        if self.project:
            return reverse('serve_rendered_text', args=[self.project.id, self.text_type, 'page_1.html'])
        else:
            return self.external_url

class ContentAccess(models.Model):
    content = models.ForeignKey(Content, on_delete=models.CASCADE, related_name='accesses')
    ip_address = models.GenericIPAddressField()
    access_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('content', 'ip_address')  # Ensure unique accesses per content and IP
            
class APICall(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(CLARAProject, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    operation = models.CharField(max_length=100)
    api_type = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.DecimalField(max_digits=10, decimal_places=2)
    retries = models.IntegerField()
    prompt = models.TextField()
    response = models.TextField()

    class Meta:
        ordering = ['-timestamp']
        
# Used by asynchronous processes to report results
##class TaskUpdate(models.Model):
##    report_id = models.CharField(max_length=255)
##    message = models.CharField(max_length=1024)
##    timestamp = models.DateTimeField(auto_now_add=True)
##
##    class Meta:
##        indexes = [
##            models.Index(fields=['report_id', 'timestamp']),
##        ]

class TaskUpdate(models.Model):
    report_id = models.CharField(max_length=255)
    user_id = models.CharField(max_length=255, null=True, blank=True)  # Assuming user_id is a string; adjust as needed.
    task_type = models.CharField(max_length=255, null=True, blank=True)  # Add choices if you have predefined task types.
    message = models.CharField(max_length=1024)
    read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['report_id', 'timestamp']),
            # Consider adding additional indexes if needed for query optimization
        ]


class Rating(models.Model):
    RATING_CHOICES = [
        (1, '1 - Poor'),
        (2, '2 - Fair'),
        (3, '3 - Good'),
        (4, '4 - Very Good'),
        (5, '5 - Excellent'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    

    class Meta:
        unique_together = (('user', 'content'),)
        
class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    comment = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
class Update(models.Model):
    UPDATE_TYPES = [
        ('PUBLISH', 'Publish'),
        ('RATE', 'Rate'),
        ('COMMENT', 'Comment'),
        ('FRIEND', 'Friend'),
        # Add more types as needed
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    update_type = models.CharField(max_length=10, choices=UPDATE_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Generic foreign key setup
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f"{self.user.username} {self.update_type} at {self.timestamp}. Content: {self.content_object}"

    class Meta:
        ordering = ['-timestamp']
        
# Through model to maintain order in the ReadingHistory ManyToMany relationship
class ReadingHistoryProjectOrder(models.Model):
    reading_history = models.ForeignKey('ReadingHistory', on_delete=models.CASCADE)
    project = models.ForeignKey('CLARAProject', on_delete=models.CASCADE)  # Direct reference to CLARAProject
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']

# Main ReadingHistory model
class ReadingHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reading_histories')
    l2 = models.CharField(max_length=50, choices=SUPPORTED_LANGUAGES)
    project = models.OneToOneField(CLARAProject, on_delete=models.CASCADE, null=True, blank=True, unique=True)
    internal_id = models.CharField(max_length=200, null=True)
    projects = models.ManyToManyField('CLARAProject', through=ReadingHistoryProjectOrder, related_name='included_in_reading_histories')
    require_phonetic_text = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'l2')

    def __str__(self):
        return f"Reading History for {self.user.username} in {self.l2}"

    def add_project(self, project):
        """Add a project to the reading history."""
        max_order = self.projects_through.order_by('-order').first()
        next_order = max_order.order + 1 if max_order else 0
        ReadingHistoryProjectOrder.objects.create(reading_history=self, project=project, order=next_order)

    def remove_project(self, project):
        """Remove a project from the reading history and adjust order of remaining projects."""
        project_order = self.projects_through.get(project=project)
        project_order.delete()
        # Adjust the order of the remaining projects
        for remaining_project in self.projects_through.filter(order__gt=project_order.order):
            remaining_project.order -= 1
            remaining_project.save()

    def get_ordered_projects(self):
        """Retrieve the ordered list of projects in the reading history."""
        return [project_order.project for project_order in self.projects_through.order_by('order')]

    @property
    def projects_through(self):
        """Helper property to access the through model directly."""
        return ReadingHistoryProjectOrder.objects.filter(reading_history=self)

class SatisfactionQuestionnaire(models.Model):
    CLARA_VERSION_CHOICES = [
        ('simple_clara', 'Simple C-LARA'),
        ('advanced_clara', 'Advanced C-LARA'),
    ]

    GENERATED_BY_AI_CHOICES = [
        (True, 'Generated by C-LARA/another AI'),
        (False, 'Written by a human'),
    ]

    TEXT_TYPE_CHOICES = [
        ('story', 'Story'),
        ('essay', 'Essay'),
        ('poem', 'Poem'),
        ('play', 'Play'),
        ('newspaper_article', 'Newspaper Article'),
        ('annotated_existing_text', 'Annotating Existing Text'),
        ('other', 'Other'),
    ]

    TIME_SPENT_CHOICES = [
        ('NOT APPLICABLE', 'Not applicable'),
        ('did_not_correct', "Didn't correct"),
        ('1_2_mins', '1-2 mins'),
        ('3_5_mins', '3-5 mins'),
        ('6_10_mins', '6-10 mins'),
        ('11_20_mins', '11-20 mins'),
        ('more_than_20_mins', 'More than 20 mins'),
    ]

    TIME_SPENT_CHOICES_IMAGES = [
        ('NOT APPLICABLE', 'Not applicable'),
        ('did_not_correct', "Didn't correct"),
        ('1_5_mins', '1-5 mins'),
        ('6_15_mins', '6-15 mins'),
        ('15_mins_hour', '15 mins to an hour'),
        ('more_than_an_hour', 'More than an hour'),
    ]

    SHARE_CHOICES = [
        ('have_shared', 'Have shared'),
        ('will_certainly_share', 'Will certainly share'),
        ('may_share', 'May share'),
        ('wont_share', "Won't share"),
    ]

    LIKERT_CHOICES = [
        (0, 'NOT APPLICABLE'),
        (5, 'Strongly agree'),
        (4, 'Agree'),
        (3, 'Neutral'),
        (2, 'Disagree'),
        (1, 'Strongly disagree'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    project = models.ForeignKey('CLARAProject', on_delete=models.CASCADE)
    clara_version = models.CharField("Which version of C-LARA do your answers apply to?", max_length=20, choices=CLARA_VERSION_CHOICES, null=True)
    generated_by_ai = models.BooleanField("Was your text generated by C-LARA/another AI, or was it written by a human?", choices=GENERATED_BY_AI_CHOICES, null=True)
    text_type = models.CharField("What type of text did you produce?", max_length=30, choices=TEXT_TYPE_CHOICES, null=True)
    grammar_correctness = models.IntegerField("The grammar in the text was correct", choices=LIKERT_CHOICES, null=True)
    vocabulary_appropriateness = models.IntegerField("The vocabulary/choice of words was appropriate", choices=LIKERT_CHOICES, null=True)
    style_appropriateness = models.IntegerField("The style was appropriate", choices=LIKERT_CHOICES, null=True)
    content_appropriateness = models.IntegerField("The overall content was appropriate", choices=LIKERT_CHOICES, null=True)
    cultural_elements = models.IntegerField("The text included appropriate elements of local culture", choices=LIKERT_CHOICES, null=True)
    text_engagement = models.IntegerField("I found the text engaging (funny/cute/moving/etc)", choices=LIKERT_CHOICES, null=True)
    correction_time_text = models.CharField("Time I spent correcting the text:", max_length=30, choices=TIME_SPENT_CHOICES, null=True)
    correction_time_annotations = models.CharField("Time I spent correcting the annotations (segmentation/glosses/lemmas)", max_length=20,
                                                   choices=TIME_SPENT_CHOICES, null=True)
    image_match = models.IntegerField("The image(s) matched the content of the text", choices=LIKERT_CHOICES, null=True)
    image_editing_time = models.CharField("Time spent regenerating/editing the image(s)", max_length=30, choices=TIME_SPENT_CHOICES_IMAGES, null=True)
    shared_intent = models.CharField("I have shared/intend to share this text with other people", max_length=30, choices=SHARE_CHOICES, null=True)
    purpose_text = models.TextField("Tell us about the purpose of the text you created (e.g. educational material, professional report, creative writing, articles for public use, technical documentation, personal use, social media content, research and analysis, entertainment, etc.)", blank=True)
    functionality_suggestion = models.TextField("What other functionality would you like to add to C-LARA?", blank=True)
    ui_improvement_suggestion = models.TextField("How would you suggest we could improve the user interface design in C-LARA?", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "project")

class FundingRequest(models.Model):
    CONTENT_TYPE_CHOICES = [
        ('short_stories', 'Short stories'),
        ('essays', 'Essays'),
        ('poems', 'Poems'),
        ('picturebooks', 'Picture books'),
        ('existing_texts', 'Annotating existing texts'),
        ('other', 'Other'),
        ]

    PURPOSE_CHOICES = [
        ('just_curious', 'Just curious'),
        ('improve_own_skills', 'Want to improve own language skills'),
        ('classroom', 'Use for language teaching'),
        ('other', 'Other'),
        ]

    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ]
        
    user = models.ForeignKey(User, related_name='funding_request_user', on_delete=models.SET_NULL, null=True, blank=True)
    purpose = models.CharField("Why are you interested in using C-LARA?", max_length=50, choices=PURPOSE_CHOICES)
    language = models.CharField("In which language will you mostly be creating texts?", max_length=50, choices=SUPPORTED_LANGUAGES_AND_OTHER)
    other_language = models.CharField("Specify the language if it was not listed in the menu", max_length=50, blank=True)
    native_or_near_native = models.BooleanField("Are you a native/near-native speaker of this language?", default=False)
    text_type = models.CharField("What kind of texts are you most interested in creating?", max_length=50, choices=CONTENT_TYPE_CHOICES)
    other_purpose = models.TextField("Explain briefly what you want to do and why you cannot use an API key.", blank=True)
    status = models.CharField("Current status of request", max_length=50, choices=STATUS_CHOICES, default='submitted')
    funder = models.ForeignKey(User, related_name='funding_request_funder', on_delete=models.SET_NULL, null=True, blank=True)
    credit_assigned = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    decision_comment = models.TextField("Comment on Decision", blank=True, help_text="Feedback or reason for decision.")
    decision_made_at = models.DateTimeField("Decision Made At", null=True, blank=True)

# Models for activities

class Activity(models.Model):
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=ACTIVITY_CATEGORY_CHOICES)
    status = models.CharField(max_length=20, choices=ACTIVITY_STATUS_CHOICES, default='posted')
    resolution = models.CharField(max_length=20, choices=ACTIVITY_RESOLUTION_CHOICES, default='unresolved')
    description = models.TextField()
    creator = models.ForeignKey(User, related_name='created_activities', on_delete=models.CASCADE)
    registered_users = models.ManyToManyField(User, through='ActivityRegistration', related_name='registered_activities')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_absolute_url(self):
        return reverse('activity_detail', args=[str(self.id)])

class ActivityRegistration(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    wants_email = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'activity')  # Prevent duplicate registrations

class ActivityComment(models.Model):
    activity = models.ForeignKey(Activity, related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class ActivityVote(models.Model):
    ACTIVITY_VOTE_CHOICES = [(0, 'No vote'),
                             (1, 'Most important'),
                             (2, 'Second most important'),
                             (3, 'Third most important')
                             ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    importance = models.IntegerField(choices=ACTIVITY_VOTE_CHOICES)
    week = models.DateField()  # To group votes by week. Value will be start date of the week in which vote was posted

    class Meta:
        unique_together = ('user', 'activity', 'week')

class CurrentActivityVote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    importance = models.IntegerField(choices=ActivityVote.ACTIVITY_VOTE_CHOICES)

    class Meta:
        unique_together = ('user', 'activity')
        
# Django ORM versions of database relations for repository classes

class AudioMetadata(models.Model):
    engine_id = models.CharField(max_length=255)
    language_id = models.CharField(max_length=255)
    voice_id = models.CharField(max_length=255)
    text = models.TextField()
    context = models.TextField(default='')
    file_path = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orm_audio_metadata'
        verbose_name = 'Audio Metadata'
        verbose_name_plural = 'Audio Metadata'
        # Unique audio file for combination of engine, language, voice, text and context
        # Unfortunately, adding this line reveals that the current database is inconsistent
        #unique_together = ('engine_id', 'language_id', 'voice_id', 'text', 'context')
        indexes = [
            models.Index(fields=['engine_id', 'language_id', 'voice_id', 'text', 'context'], name='audio_meta_composite_idx')
        ]

    def __str__(self):
        return f"{self.engine_id} | {self.language_id} | {self.voice_id} | {self.text[:50]}"


class ImageMetadata(models.Model):
    POSITION_CHOICES = [
        ('top', 'Top'),
        ('bottom', 'Bottom'),
        ('inline', 'Inline'),
    ]

    REQUEST_TYPE_CHOICES = [
        ('image-generation', 'Generation'),
        ('image-understanding', 'Understanding'),
    ]

    project_id = models.CharField(max_length=255)
    image_name = models.CharField(max_length=255)
    file_path = models.TextField(blank=True, default='')
    associated_text = models.TextField(blank=True, default='')
    associated_areas = models.TextField(blank=True, default='')
    page = models.IntegerField(default=1)
    position = models.CharField(max_length=10, choices=POSITION_CHOICES, default='top')
    style_description = models.TextField(blank=True, default='',
                                         help_text='AI-generated description of the image style.')
    content_description = models.TextField(blank=True, default='',
                                           help_text='AI-generated description of the image content.')
    user_prompt = models.TextField(blank=True, default='',
                                   help_text='Most recent user prompt for generating or modifying this image.')
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES, default='image-generatio')
    description_variable = models.CharField(max_length=255, blank=True, default='',
                                            help_text='Variable name for storing image understanding result.')
    description_variables = models.JSONField(blank=True, default=list, help_text='List of description variables for this image generation request.')

    class Meta:
        db_table = 'orm_image_metadata'
        verbose_name = 'Image Metadata'
        verbose_name_plural = 'Image Metadata'
        # Unique image for combination of project and image_name
        unique_together = ('project_id', 'image_name')

    def __str__(self):
        return f"{self.project_id} | {self.image_name} | {self.position} | Page {self.page}"

class ImageDescription(models.Model):
    project_id = models.CharField(max_length=255)
    description_variable = models.CharField(max_length=255)
    explanation = models.TextField(help_text='Explanation of the image element.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orm_image_description'
        verbose_name = 'Image Description'
        verbose_name_plural = 'Image Descriptions'
        unique_together = ('project_id', 'description_variable')

    def __str__(self):
        return f"{self.project_id} | {self.description_variable}"

class PhoneticEncoding(models.Model):
    language = models.CharField(max_length=255, choices=SUPPORTED_LANGUAGES, primary_key=True)
    encoding = models.CharField(max_length=255, choices=(('ipa', 'IPA'), ('arpabet_like', 'Arpabet-like')))

    class Meta:
        db_table = 'orm_phonetic_encoding'

class PlainPhoneticLexicon(models.Model):
    word = models.TextField()
    phonemes = models.TextField()
    language = models.CharField(max_length=255, choices=SUPPORTED_LANGUAGES)
    status = models.CharField(
        max_length=255,
        choices=(('uploaded', 'Uploaded'), ('generated', 'Generated'), ('reviewed', 'Reviewed'))
    )

    class Meta:
        db_table = 'orm_phonetic_lexicon'
        # Unique plain phonetic lexicon entry for combination of language, word and phoneme
        unique_together = ('language', 'word', 'phonemes')
        indexes = [
            models.Index(fields=['word'], name='idx_orm_word_plain'),
        ]

class AlignedPhoneticLexicon(models.Model):
    word = models.TextField()
    phonemes = models.TextField()
    aligned_graphemes = models.TextField()
    aligned_phonemes = models.TextField()
    language = models.CharField(max_length=255, choices=SUPPORTED_LANGUAGES)
    status = models.CharField(
        max_length=255,
        choices=(('uploaded', 'Uploaded'), ('generated', 'Generated'), ('reviewed', 'Reviewed'))
    )

    class Meta:
        db_table = 'orm_aligned_phonetic_lexicon'
        # Unique aligned phonetic lexicon entry for combination of language, word and phoneme
        unique_together = ('language', 'word', 'phonemes')
        indexes = [
            models.Index(fields=['word'], name='idx_orm_word_aligned'),
        ]

class PhoneticLexiconHistory(models.Model):
    word = models.TextField()
    modification_date = models.DateTimeField()
    previous_value = models.JSONField()
    new_value = models.JSONField()
    modified_by = models.CharField(max_length=255)
    comments = models.TextField()

    class Meta:
        db_table = 'orm_phonetic_lexicon_history'
        indexes = [
            models.Index(fields=['word'], name='idx_orm_word_history'),
        ]
