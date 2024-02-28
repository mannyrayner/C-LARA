from django.db import models
from django.urls import reverse

from .constants import TEXT_TYPE_CHOICES, SUPPORTED_LANGUAGES, SUPPORTED_LANGUAGES_AND_DEFAULT, SIMPLE_CLARA_TYPES

from django.contrib.auth.models import User, Group, Permission 
from django.db import models

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from .clara_core.clara_main import CLARAProjectInternal
 
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    is_admin = models.BooleanField(default=False)
    is_moderator = models.BooleanField(default=False)
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

    def has_saved_internalised_and_annotated_text(self, phonetic=False):
        clara_project_internal = CLARAProjectInternal(self.internal_id, self.l2, self.l1)
        return clara_project_internal.get_saved_internalised_and_annotated_text(phonetic=phonetic)
    
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

    TTS_CHOICES = [
        ( 'none', 'None' ),
        ( 'google', 'Google TTS' ),
        ( 'openai', 'OpenAI TTS' ),
        ( 'abair', 'ABAIR' ),
    ]

    VOICE_CHOICES = [
        ( 'none', 'None' ),
        ( 'alloy', 'Alloy (OpenAI)' ),
        ( 'echo', 'Echo (OpenAI)' ),
        ( 'fable', 'Fable (OpenAI)' ),
        ( 'onyx', 'Onyx (OpenAI)' ),
        ( 'nova', 'Nova (OpenAI)' ),
        ( 'shimmer', 'Shimmer (OpenAI)' ),
        ( 'ga_UL_anb_nnmnkwii', 'ga_UL_anb_nnmnkwii (ABAIR)' ),
        ( 'ga_MU_nnc_nnmnkwii', 'ga_MU_nnc_nnmnkwii (ABAIR)' ),
        ( 'ga_MU_cmg_nnmnkwii', 'ga_MU_cmg_nnmnkwii (ABAIR)' ),      
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

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('content_detail', args=[str(self.id)])
        
    def url(self):
        if self.project:
            return reverse('serve_rendered_text', args=[self.project.id, self.text_type, 'page_1.html'])
        else:
            return self.external_url
            
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
