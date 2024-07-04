from django import forms
from django.forms import formset_factory
from django.contrib.auth.forms import UserCreationForm

from .models import Content, UserProfile, UserConfiguration, LanguageMaster, SatisfactionQuestionnaire, FundingRequest, Acknowledgements
from .models import CLARAProject, HumanAudioInfo, PhoneticHumanAudioInfo, PhoneticHumanAudioInfo, Rating, Comment, FormatPreferences
from .models import Activity, ActivityRegistration, ActivityComment, ActivityVote

from django.contrib.auth.models import User

from .constants import SUPPORTED_LANGUAGES, SUPPORTED_LANGUAGES_AND_DEFAULT, SUPPORTED_LANGUAGES_AND_OTHER, SIMPLE_CLARA_TYPES
from .constants import ACTIVITY_CATEGORY_CHOICES, ACTIVITY_STATUS_CHOICES, ACTIVITY_RESOLUTION_CHOICES, RECENT_TIME_PERIOD_CHOICES, DEFAULT_RECENT_TIME_PERIOD
from .constants import TTS_CHOICES

from .clara_utils import is_rtl_language, is_chinese_language
        
class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']

class UserSelectForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.all().order_by('username'),
                                  label="Select a user", empty_label="Choose a user")

class AdminPasswordResetForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.all())
    new_password = forms.CharField(widget=forms.PasswordInput())
        
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['bio', 'location', 'birth_date', 'profile_picture', 'is_private']

class UserPermissionsForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['is_admin', 'is_moderator', 'is_funding_reviewer', 'is_questionnaire_reviewer']

class FriendRequestForm(forms.Form):
    action = forms.CharField(widget=forms.HiddenInput())
    friend_request_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)

class UserConfigForm(forms.ModelForm):
    class Meta:
        model = UserConfiguration
        fields = ['clara_version', 'open_ai_api_key', 'gpt_model', 'max_annotation_words']  
        widgets = {
            'clara_version': forms.Select(choices=[('simple_clara', 'Simple C-LARA'),
                                                   ('full_clara', 'Full C-LARA'),]),
            'gpt_model': forms.Select(choices=[('gpt-4o', 'GPT-4o'),
                                               ('gpt-4-turbo', 'GPT-4 Turbo'),
                                               ('gpt-4-1106-preview', 'GPT-4 Turbo 2023-11-06'),
                                               ('gpt-4', 'GPT-4')]),
            'max_annotation_words': forms.Select(choices=[(100, '100'),
                                                          (250, '250'),
                                                          (500, '500'),
                                                          (1000, '1000')])
        }

    def __init__(self, *args, **kwargs):
        super(UserConfigForm, self).__init__(*args, **kwargs)
        self.fields['gpt_model'].required = False
        self.fields['max_annotation_words'].required = False
        
class AssignLanguageMasterForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.all())
    language = forms.ChoiceField(choices=SUPPORTED_LANGUAGES_AND_DEFAULT)

class InitialiseORMRepositoriesForm(forms.Form):
    pass

class DeleteTTSDataForm(forms.Form):
    language = forms.ChoiceField(choices=SUPPORTED_LANGUAGES)

class DeleteContentForm(forms.Form):
    pass

class ContentRegistrationForm(forms.ModelForm):
    class Meta:
        model = Content
        fields = [
            'external_url', 'title', 'text_type', 'l2', 'l1', 'length_in_words', 'author',
            'voice', 'annotator', 'difficulty_level'
        ]

class FormatPreferencesForm(forms.ModelForm):
    class Meta:
        model = FormatPreferences
        fields = ['font_type', 'font_size', 'text_align',
                  'concordance_font_type', 'concordance_font_size', 'concordance_text_align']

class ContentSearchForm(forms.Form):
    title = forms.CharField(max_length=255, required=False)
    l2 = forms.ChoiceField(choices=[('', 'Any')] + SUPPORTED_LANGUAGES, required=False)
    l1 = forms.ChoiceField(choices=[('', 'Any')] + SUPPORTED_LANGUAGES, required=False)
    time_period = forms.ChoiceField(choices=[('', 'Any time')] + RECENT_TIME_PERIOD_CHOICES, required=False, label="Most recently active")

class UnifiedSearchForm(forms.Form):
    time_period = forms.ChoiceField(
        choices=RECENT_TIME_PERIOD_CHOICES,
        required=False,
        label="Showing updates for",
        initial=DEFAULT_RECENT_TIME_PERIOD
    )

class ProjectCreationForm(forms.ModelForm):
    #title = forms.CharField(widget=forms.TextInput(attrs={'style': 'width: 100%;'}))  # Uses full width of its container
    title = forms.CharField(widget=forms.TextInput(attrs={'size': '60'}))
    uses_coherent_image_set = forms.BooleanField(required=False, label='Use Coherent Image Set',
                                                 help_text="Check this if the project should use a coherent style for all images.")
    use_translation_for_images = forms.BooleanField(required=False, label='Use Translations for Images',
                                                    help_text="Check this if the project should use translations for generating coherent image sets.")

    class Meta:
        model = CLARAProject
        fields = ['title', 'l2', 'l1', 'uses_coherent_image_set', 'use_translation_for_images']

class AcknowledgementsForm(forms.ModelForm):
    class Meta:
        model = Acknowledgements
        fields = ['short_text', 'long_text', 'long_text_location']

class ProjectImportForm(forms.Form):
    title = forms.CharField(label='Project Title', max_length=255)
    zipfile = forms.FileField(label='Project Zipfile')

class SimpleClaraForm(forms.Form):
    status = forms.CharField(initial='No project', required=False)
    l2 = forms.ChoiceField(label='Text language', choices=SUPPORTED_LANGUAGES, required=False)
    l1 = forms.ChoiceField(label='Annotation language', choices=SUPPORTED_LANGUAGES, required=False)
    # Name of the Django-level project (CLARAProject)
    title = forms.CharField(label='Title', max_length=200, required=False,
                            widget=forms.TextInput(attrs={'size': '60'}))
    # What we are going to do in this project
    simple_clara_type = forms.ChoiceField(choices=SIMPLE_CLARA_TYPES,
                                          widget=forms.RadioSelect,
                                          initial='create_text_and_image',
                                          required=False)
    # Need to find a clean way to allow coherent image sets in Simple C-LARA
    #uses_coherent_image_set = forms.BooleanField(required=False, label='Use Coherent Image Set',
    #                                             help_text="Check this if the project should use an AI-generated coherent style for all images.")
    # Id of the CLARAProjectInternal
    internal_title = forms.CharField(label='Title', max_length=200, required=False)
    # L2 title to appear on the first page of the text
    text_title = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
        initial='' )
    prompt = forms.CharField(label='Prompt', widget=forms.Textarea, required=False)
    image_file_path = forms.ImageField(label='Image File', required=False)
    image_advice_prompt = forms.CharField(label='Prompt', widget=forms.Textarea, required=False)
    plain_text = forms.CharField(label='Plain text', widget=forms.Textarea, required=False)
    segmented_text = forms.CharField(label='Segmented text', widget=forms.Textarea, required=False)
    segmented_title = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        initial='' )
    image_basename = forms.CharField(required=False)
    preferred_tts_engine = forms.ChoiceField(label='Preferred TTS engine', choices=TTS_CHOICES, required=False)
    rendered_text_available = forms.BooleanField(label='Rendered text available', required=False)
    content_id = forms.CharField(required=False)

    def __init__(self, *args, is_rtl_language=False, **kwargs):
        super(SimpleClaraForm, self).__init__(*args, **kwargs)

        # For right-to-left languages like Arabic, Farsi, Urdu and Hebrew
        if is_rtl_language:
            self.fields['text_title'].widget.attrs['dir'] = 'rtl'
            self.fields['plain_text'].widget.attrs['dir'] = 'rtl'
            self.fields['segmented_text'].widget.attrs['dir'] = 'rtl'

class ProjectSearchForm(forms.Form):
    title = forms.CharField(required=False)
    l2 = forms.ChoiceField(choices=[('', 'Any')] + list(SUPPORTED_LANGUAGES), required=False)
    l1 = forms.ChoiceField(choices=[('', 'Any')] + list(SUPPORTED_LANGUAGES), required=False)

class ProjectSelectionForm(forms.Form):
    select = forms.BooleanField(required=False, widget=forms.CheckboxInput)
    project_id = forms.IntegerField(widget=forms.HiddenInput)
    
ProjectSelectionFormSet = formset_factory(ProjectSelectionForm, extra=0)

class L2LanguageSelectionForm(forms.Form):
    l2 = forms.ChoiceField(required=False)

    def __init__(self, *args,
                 languages_available=None, l2=None,
                 **kwargs):
        super(L2LanguageSelectionForm, self).__init__(*args, **kwargs)
        
        if languages_available:
            self.fields['l2'].choices = [ ( language, language.capitalize() ) for language in languages_available ]
        if l2:
            self.fields['l2'].initial = l2

class RequirePhoneticTextForm(forms.Form):
    require_phonetic_text = forms.BooleanField(
        required=False,  # Make it optional so users can choose not to require phonetic texts
        label='Require phonetic texts',
        help_text='Check this box if you want your reading history to include only texts with phonetic versions.'
    )

class AddProjectToReadingHistoryForm(forms.Form):
    project_id = forms.ChoiceField(required=False)

    def __init__(self, *args,
                 projects_available=None, l2=None,
                 **kwargs):
        super(AddProjectToReadingHistoryForm, self).__init__(*args, **kwargs)
        
        if projects_available:
            self.fields['project_id'].choices = [ ( project.id, project.title ) for project in projects_available ]

class AddProjectMemberForm(forms.Form):
    ROLE_CHOICES = [
        ('VIEWER', 'Viewer'),
        ('ANNOTATOR', 'Annotator'),
        ('OWNER', 'Owner'),        
        # Add more roles as needed...
    ]
    
    user = forms.ModelChoiceField(queryset=User.objects.all().order_by('username'))
    role = forms.ChoiceField(choices=ROLE_CHOICES)
       
class UpdateProjectTitleForm(forms.Form):
    new_title = forms.CharField(max_length=200, required=False)

class UpdateCoherentImageSetForm(forms.Form):
    uses_coherent_image_set = forms.BooleanField(required=False)
    use_translation_for_images = forms.BooleanField(required=False)

class AddCreditForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.all())
    credit = forms.DecimalField()

class ConfirmTransferForm(forms.Form):
    confirmation_code = forms.CharField(label='Confirmation Code', max_length=100)

class CreateAnnotatedTextForm(forms.Form):
    text_choice = forms.ChoiceField(
        choices=[
            ('generate', 'Annotate text using AI'), 
            ('improve', 'Improve existing annotated text using AI'),
            ('manual', 'Manually enter/edit annotated text'),
            ('load_archived', 'Load archived version')
        ],
        widget=forms.RadioSelect,
        initial='generate'
    )
    archived_version = forms.ChoiceField(required=False)
    current_version = forms.CharField(
        widget=forms.TextInput(attrs={'readonly':'readonly', 'size': '45'}),
        required=False,
        initial='' )
    text = forms.CharField(
        widget=forms.Textarea( 
           # attrs={'class': 'textarea-class'} 
           attrs={'rows': 15, 'cols': 100}
        ), 
    required=False
)
    label = forms.CharField(required=False, max_length=200)
    gold_standard = forms.BooleanField(required=False)
    
    def __init__(self, *args,
                 previous_version='default',
                 tree_tagger_supported=False, jieba_supported=False,
                 is_rtl_language=False, prompt=None,
                 archived_versions=None, current_version='',
                 **kwargs):
        super(CreateAnnotatedTextForm, self).__init__(*args, **kwargs)

        # For right-to-left languages like Arabic, Farsi, Urdu and Hebrew
        if is_rtl_language:
            self.fields['text'].widget.attrs['dir'] = 'rtl'
        
        if archived_versions:
            self.fields['archived_version'].choices = archived_versions
        if current_version:
            self.fields['current_version'].initial = current_version
            
# Since we are creating the initial text, the names of the choices need to be customised            
class CreatePlainTextForm(CreateAnnotatedTextForm):
    TEXT_CHOICES = [
        ('generate', 'Generate text using AI'),
        ('improve', 'Improve existing text using AI'),
        ('manual', 'Manually enter/edit text'),
        ('load_archived', 'Load archived version')
    ]
    prompt = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3, 'cols': 100}))
    
    def __init__(self, *args, prompt=None, previous_version='default', **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text_choice'].choices = self.TEXT_CHOICES
        if prompt:
            self.fields['prompt'].initial = prompt
        # This doesn't seem to work, for some so far unidentified reason. Fix in template.
        #self.field_order = ['text_choice', 'archived_version', 'prompt', 'text', 'current_version', 'gold_standard']
            
class CreateSegmentedTextForm(CreateAnnotatedTextForm):
    TEXT_CHOICES=[
            ('jieba', 'Segment text using Jieba'),
            ('generate', 'Segment text using AI'),
            ('correct', 'Try to fix errors in malformed segmented text using AI'), 
            #('improve', 'Improve segmentation of words using AI'),
            ('manual', 'Manually enter/edit segmented text'),
            ('load_archived', 'Load archived version')
        ]

    def __init__(self, *args, prompt=None, jieba_supported=False, previous_version='default', **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text_choice'].choices = self.TEXT_CHOICES if jieba_supported else [
            choice for choice in self.TEXT_CHOICES if choice[0] != 'jieba'
            ]

class CreateSegmentedTitleTextForm(CreateAnnotatedTextForm):
    TEXT_CHOICES = [
        ('generate', 'Generate title using AI'),
        ('manual', 'Manually enter/edit title'),
        ('load_archived', 'Load archived version')
    ]
    
    def __init__(self, *args, prompt=None, previous_version='default', **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text_choice'].choices = self.TEXT_CHOICES

class CreateTitleTextForm(CreateAnnotatedTextForm):
    TEXT_CHOICES = [
        ('generate', 'Generate title using AI'),
        ('improve', 'Improve existing title using AI'),
        ('manual', 'Manually enter/edit title'),
        ('load_archived', 'Load archived version')
    ]
    
    def __init__(self, *args, prompt=None, previous_version='default', **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text_choice'].choices = self.TEXT_CHOICES

class CreateSummaryTextForm(CreateAnnotatedTextForm):
    TEXT_CHOICES = [
        ('generate', 'Generate summary using AI'),
        ('improve', 'Improve existing summary using AI'),
        ('manual', 'Manually enter/edit text'),
        ('load_archived', 'Load archived version')
    ]
    
    def __init__(self, *args, prompt=None, previous_version='default', **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text_choice'].choices = self.TEXT_CHOICES

class CreateCEFRTextForm(CreateAnnotatedTextForm):
    TEXT_CHOICES = [
        ('generate', 'Estimate CEFR level using AI'),
        ('manual', 'Manually enter/edit CEFR level'),
        ('load_archived', 'Load archived version')
    ]
    
    def __init__(self, *args, prompt=None, previous_version='default', **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text_choice'].choices = self.TEXT_CHOICES

class CreatePhoneticTextForm(CreateAnnotatedTextForm):
    TEXT_CHOICES = [
        ('generate', 'Generate phonetic text from segmented text'),
        ('manual', 'Manually edit/enter phonetic text'),
        ('load_archived', 'Load archived version')
    ]

    def __init__(self, *args, prompt=None, previous_version='default', **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text_choice'].choices = self.TEXT_CHOICES

class CreateTranslatedTextForm(CreateAnnotatedTextForm):
    TEXT_CHOICES = [
        ('generate', 'Use AI to translate text from segmented text'),
        ('manual', 'Manually edit/enter translations'),
        ('load_archived', 'Load archived version')
    ]

    def __init__(self, *args, prompt=None, previous_version='default', **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text_choice'].choices = self.TEXT_CHOICES
      
##class CreateGlossedTextForm(CreateAnnotatedTextForm):
##    TEXT_CHOICES = [
##        ('generate', 'Generate annotated text from segmented text using AI'),
##        ('correct', 'Try to fix errors in malformed annotated text using AI'), 
##        ('improve', 'Improve existing annotated text using AI'),
##        ('manual', 'Manually enter annotated text'),
##        ('load_archived', 'Load archived version'),
##        ('delete', 'Delete current glossed text')
##    ]
##
##    TEXT_CHOICES_FROM_LEMMA = [
##        ('generate', 'Generate annotated text from lemma-tagged text using AI'),
##        ('correct', 'Try to fix errors in malformed annotated text using AI'), 
##        ('improve', 'Improve existing annotated text using AI'),
##        ('manual', 'Manually enter annotated text'),
##        ('load_archived', 'Load archived version'),
##        ('delete', 'Delete current glossed text')
##    ]
##
##    def __init__(self, *args, prompt=None, previous_version='default', **kwargs):
##        super().__init__(*args, **kwargs)
##        self.fields['text_choice'].choices = self.TEXT_CHOICES_FROM_LEMMA if previous_version == 'lemma' else self.TEXT_CHOICES

class CreateGlossedTextForm(CreateAnnotatedTextForm):
    TEXT_CHOICES = [
        ('generate', 'Generate annotated text from segmented text using AI'),
        #('generate_gloss_from_lemma', 'Generate annotated text from LEMMA-TAGGED text using AI'),
        ('correct', 'Try to fix errors in malformed annotated text using AI'), 
        ('improve', 'Improve existing annotated text using AI'),
        ('manual', 'Manually enter annotated text'),
        ('load_archived', 'Load archived version'),
        ('delete', 'Delete current glossed text')
    ]

    def __init__(self, *args, prompt=None, previous_version='default', **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text_choice'].choices = self.TEXT_CHOICES

class CreateLemmaTaggedTextForm(CreateAnnotatedTextForm):
    TEXT_CHOICES = [
        ('generate', 'Generate annotated text from segmented text using AI'),
        ('tree_tagger', 'Generate annotated text from segmented text using TreeTagger'),
        ('correct', 'Try to fix errors in malformed annotated text using AI'), 
        ('improve', 'Improve existing annotated text using AI'),
        ('trivial', 'Generate annotated text from segmented text with trivial tags'),
        ('manual', 'Manually enter annotated text'),
        ('load_archived', 'Load archived version')
    ]

    def __init__(self, *args, tree_tagger_supported=False, archived_versions=None, current_version='', previous_version='default', **kwargs):
        super(CreateLemmaTaggedTextForm, self).__init__(*args, archived_versions=archived_versions, current_version=current_version, **kwargs)
        self.fields['text_choice'].choices = self.TEXT_CHOICES if tree_tagger_supported else [
            choice for choice in self.TEXT_CHOICES if choice[0] != 'tree_tagger'
        ]

class CreateMWETaggedTextForm(CreateAnnotatedTextForm):
    TEXT_CHOICES = [
        ('generate', 'Generate annotated text from segmented text using AI'),
        #('correct', 'Try to fix errors in malformed annotated text using AI'), 
        ('manual', 'Manually enter annotated text'),
        ('load_archived', 'Load archived version')
    ]

    def __init__(self, *args, tree_tagger_supported=False, archived_versions=None, current_version='', previous_version='default', **kwargs):
        super(CreateMWETaggedTextForm, self).__init__(*args, archived_versions=archived_versions, current_version=current_version, **kwargs)
        self.fields['text_choice'].choices = self.TEXT_CHOICES if tree_tagger_supported else [
            choice for choice in self.TEXT_CHOICES if choice[0] != 'tree_tagger'
        ]


class CreatePinyinTaggedTextForm(CreateAnnotatedTextForm):
    TEXT_CHOICES = [
        ('generate', 'Generate pinyin-tagged text from segmented text using AI'),
        ('pypinyin', 'Generate pinyin-tagged text from segmented text using pypinyin'),
        ('correct', 'Try to fix errors in malformed annotated text using AI'), 
        ('improve', 'Improve existing annotated text using AI'),
        ('manual', 'Manually enter annotated text'),
        ('load_archived', 'Load archived version')
    ]

    def __init__(self, *args, tree_tagger_supported=False, archived_versions=None, current_version='', previous_version='default', **kwargs):
        super(CreatePinyinTaggedTextForm, self).__init__(*args, archived_versions=archived_versions, current_version=current_version, **kwargs)
        self.fields['text_choice'].choices = self.TEXT_CHOICES
        
class CreateLemmaAndGlossTaggedTextForm(CreateAnnotatedTextForm):
    TEXT_CHOICES = [
        ('improve', 'Improve existing annotated text using AI'),
        ('manual', 'Manually enter annotated text'),
        ('load_archived', 'Load archived version')
    ]

    def __init__(self, *args, tree_tagger_supported=False, archived_versions=None, current_version='', previous_version='default', **kwargs):
        super(CreateLemmaAndGlossTaggedTextForm, self).__init__(*args, archived_versions=archived_versions, current_version=current_version, **kwargs)
        self.fields['text_choice'].choices = self.TEXT_CHOICES if tree_tagger_supported else [
            choice for choice in self.TEXT_CHOICES if choice[0] != 'tree_tagger'
        ]

class MakeExportZipForm(forms.Form):
    pass

class RenderTextForm(forms.Form):
    pass

class RegisterAsContentForm(forms.Form):
    register_as_content = forms.BooleanField(required=False, initial=False)

class RatingForm(forms.ModelForm):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]  # Assuming 1-5 rating

    rating = forms.ChoiceField(choices=reversed(RATING_CHOICES),
                               widget=forms.RadioSelect)
    
    class Meta:
        model = Rating
        fields = ['rating']

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['comment']

class ActivitySearchForm(forms.Form):
    id = forms.IntegerField(required=False, label="Activity ID", widget=forms.NumberInput(attrs={'placeholder': 'Enter Activity ID'}))
    category = forms.ChoiceField(choices=[('', 'Any')] + ACTIVITY_CATEGORY_CHOICES, required=False, label="Category")
    status = forms.ChoiceField(choices=[('', 'Any')] + ACTIVITY_STATUS_CHOICES, required=False, label="Status")
    resolution = forms.ChoiceField(choices=[('', 'Any')] + ACTIVITY_RESOLUTION_CHOICES, required=False, label="Resolution")
    time_period = forms.ChoiceField(choices=[('', 'Any time')] + RECENT_TIME_PERIOD_CHOICES, required=False, label="Most recently active")

class ActivityCommentForm(forms.ModelForm):
    class Meta:
        model = ActivityComment
        fields = ['comment']

class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['title', 'category', 'description']

class ActivityStatusForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['status']

class ActivityResolutionForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['resolution']

class ActivityRegistrationForm(forms.ModelForm):
    wants_email = forms.BooleanField(required=False, label='Receive email notifications for updates')

    class Meta:
        model = ActivityRegistration
        fields = ['wants_email']

class ActivityVoteForm(forms.ModelForm):
    class Meta:
        model = ActivityVote
        fields = ['importance']

class AIActivitiesUpdateForm(forms.Form):
    updates_json = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'Enter JSON with updates'}), label="AI Updates JSON")
        
class DiffSelectionForm(forms.Form):
    version_choices = [  
        ('plain', 'Plain'),
        ('summary', 'Summary'),
        ('segmented', 'Segmented'),
        ('gloss', 'Gloss'),
        ('lemma', 'Lemma'),
    ]

    version = forms.ChoiceField(choices=version_choices)
    file1 = forms.ChoiceField(choices=[])  # Choices for file1 and file2 should be populated dynamically
    file2 = forms.ChoiceField(choices=[])
    required = forms.MultipleChoiceField(
        choices=[('error_rate', 'Error Rate'), ('details', 'Details')],
        initial=['error_rate', 'details'],  # set these options as selected by default
        widget=forms.CheckboxSelectMultiple)
              
class PromptSelectionForm(forms.Form):
    template_or_examples_choices = [
        ("template", "Template"),
        ("examples", "Examples"),
    ]
    
    operation_choices = [
        ("annotate", "Annotate"),
        ("improve", "Improve"),
    ]
    
    annotation_type_choices = [
        ("segmented", "Segmented"),
        ("morphology", "Morphology"),
        ("translated", "Translated"),
        ("mwe", "Multi Word Expressions"),
        ("lemma", "Lemma"),
        ("lemma_with_mwe", "Lemma using MWEs"),
        ("gloss", "Gloss"),
        ("gloss_with_mwe", "Gloss using MWEs"),
        ("gloss_with_lemma", "Gloss using lemmas"),
        ("pinyin", "Pinyin"),
    ]

    language = forms.ChoiceField(choices=[])  # Empty choices initially
    default_language = forms.ChoiceField(choices=SUPPORTED_LANGUAGES_AND_DEFAULT)
    annotation_type = forms.ChoiceField(choices=annotation_type_choices)
    operation = forms.ChoiceField(choices=operation_choices)
    template_or_examples = forms.ChoiceField(choices=template_or_examples_choices)
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(PromptSelectionForm, self).__init__(*args, **kwargs)

        if user:
            # Query the languages for which the user is a language master
            languages = LanguageMaster.objects.filter(user=user).values_list('language', flat=True)
            self.fields['language'].choices = [(lang, lang.capitalize()) for lang in languages]

            chinese_language_included = any([ is_chinese_language(lang) for lang in languages ])
            if not chinese_language_included:
                self.fields['annotation_type'].choices = [ ( choice, label ) for ( choice, label ) in self.annotation_type_choices
                                                           if choice != 'pinyin' ]

class TemplateForm(forms.Form):
    template = forms.CharField(widget=forms.Textarea)

class CustomTemplateFormSet(forms.BaseFormSet):
    def __init__(self, *args, **kwargs):
        self.rtl_language = kwargs.pop('rtl_language', None)
        super(CustomTemplateFormSet, self).__init__(*args, **kwargs)
        for form in self:
            form.fields['template'].widget.attrs['dir'] = 'rtl' if self.rtl_language else 'ltr'

class StringForm(forms.Form):
    string = forms.CharField(widget=forms.TextInput(attrs={'size': '60'}))
    
class CustomStringFormSet(forms.BaseFormSet):
    def __init__(self, *args, **kwargs):
        self.rtl_language = kwargs.pop('rtl_language', None)
        super(CustomStringFormSet, self).__init__(*args, **kwargs)
        for form in self:
            form.fields['string'].widget.attrs['dir'] = 'rtl' if self.rtl_language else 'ltr'

class StringPairForm(forms.Form):
    string1 = forms.CharField(widget=forms.TextInput(attrs={'size': '60'}))
    string2 = forms.CharField(widget=forms.TextInput(attrs={'size': '60'}))
    
class CustomStringPairFormSet(forms.BaseFormSet):
    def __init__(self, *args, **kwargs):
        self.rtl_language = kwargs.pop('rtl_language', None)
        super(CustomStringPairFormSet, self).__init__(*args, **kwargs)
        for form in self:
            form.fields['string1'].widget.attrs['dir'] = 'rtl' if self.rtl_language else 'ltr'
            form.fields['string2'].widget.attrs['dir'] = 'rtl' if self.rtl_language else 'ltr'

class ExampleWithMWEForm(forms.Form):
    string1 = forms.CharField(
        widget=forms.TextInput(attrs={'size': '60'}),
        label="Annotated text",
        help_text="Annotated text, where each word is followed by the annotation enclosed in hashes"
        )
    string2 = forms.CharField(
        widget=forms.TextInput(attrs={'size': '60'}),
        required=False,
        label="MWEs",
        help_text="Multi-Word Expressions in the example, if any. Comma-separated list"
        )
    
class ExampleWithMWEFormSet(forms.BaseFormSet):
    def __init__(self, *args, **kwargs):
        self.rtl_language = kwargs.pop('rtl_language', None)
        super(ExampleWithMWEFormSet, self).__init__(*args, **kwargs)
        for form in self:
            form.fields['string1'].widget.attrs['dir'] = 'rtl' if self.rtl_language else 'ltr'
            form.fields['string2'].widget.attrs['dir'] = 'rtl' if self.rtl_language else 'ltr'

class MorphologyExampleForm(forms.Form):
    # Input example text
    string1 = forms.CharField(
        widget=forms.TextInput(attrs={'size': '60'}),
        label="Input Text Example",
        help_text="Text with segmented words"
    )

    # Text with improved segmentation
    string2 = forms.CharField(
        widget=forms.TextInput(attrs={'size': '60'}),
        label="Improved Text",
        help_text="Words with improved segmentation"
    )

    # Analysis or explanation of MWEs
    string3 = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'cols': 80}),
        label="Analysis or Explanation",
        help_text="Provide a detailed analysis, word by word, of changes to the segmentation of the words"
    )

class CustomMorphologyExampleFormSet(forms.BaseFormSet):
    def __init__(self, *args, **kwargs):
        self.rtl_language = kwargs.pop('rtl_language', None)
        super(CustomMorphologyExampleFormSet, self).__init__(*args, **kwargs)
        for form in self:
            form.fields['string1'].widget.attrs['dir'] = 'rtl' if self.rtl_language else 'ltr'
            form.fields['string2'].widget.attrs['dir'] = 'rtl' if self.rtl_language else 'ltr'
            form.fields['string3'].widget.attrs['dir'] = 'rtl' if self.rtl_language else 'ltr'


class MWEExampleForm(forms.Form):
    # Input example text
    string1 = forms.CharField(
        widget=forms.TextInput(attrs={'size': '60'}),
        label="Input Text Example",
        help_text="The original text example where the MWEs are found"
    )

    # List of MWEs identified in the input
    string2 = forms.CharField(
        widget=forms.TextInput(attrs={'size': '60'}),
        label="MWEs Identified",
        help_text="Comma-separated list of MWEs identified in the input"
    )

    # Analysis or explanation of MWEs
    string3 = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'cols': 80}),
        label="Analysis or Explanation",
        help_text="Provide a detailed analysis of the MWEs found, explaining why each phrase is or is not considered an MWE"
    )

class CustomMWEExampleFormSet(forms.BaseFormSet):
    def __init__(self, *args, **kwargs):
        self.rtl_language = kwargs.pop('rtl_language', None)
        super(CustomMWEExampleFormSet, self).__init__(*args, **kwargs)
        for form in self:
            form.fields['string1'].widget.attrs['dir'] = 'rtl' if self.rtl_language else 'ltr'
            form.fields['string2'].widget.attrs['dir'] = 'rtl' if self.rtl_language else 'ltr'
            form.fields['string3'].widget.attrs['dir'] = 'rtl' if self.rtl_language else 'ltr'

class AudioMetadataForm(forms.Form):
    metadata = forms.CharField(widget=forms.Textarea)

class ImageForm(forms.Form):
    image_file_path = forms.ImageField(label='Image File', required=False)
    image_base_name = forms.CharField(label='Image File Base Name',
                                      max_length=100,
                                      widget=forms.TextInput(attrs={'readonly': 'readonly'}),
                                      required=False)
    image_name = forms.CharField(label='Image Name', max_length=100, required=False)
    associated_text = forms.CharField(label='Associated Text', widget=forms.Textarea, required=False)
    associated_areas = forms.CharField(label='Associated Areas', widget=forms.Textarea, required=False)
    page_text = forms.CharField(label='Page Text',
                                widget=forms.Textarea(attrs={'rows': 4, 'cols': 100, 'readonly': 'readonly'}),
                                required=False)
    page = forms.IntegerField(label='Page Number', min_value=0, required=False)
    position = forms.ChoiceField(label='Position', choices=[('top', 'Top'), ('bottom', 'Bottom')], required=False)
    user_prompt = forms.CharField(label='Instructions for creating image', widget=forms.Textarea(attrs={'rows': 12}), required=False)
    style_description = forms.CharField(label='AI-generated style description', widget=forms.Textarea(attrs={'rows': 12}), required=False)
    content_description = forms.CharField(label='AI-generated content description', widget=forms.Textarea(attrs={'rows': 12}), required=False)
    request_type = forms.ChoiceField(label='Request Type',
                                     choices=[('image-generation', 'Generation'),
                                              ('image-understanding', 'Understanding')],
                                     required=False)
    description_variable = forms.CharField(label='Description Variable', max_length=100, required=False)
    description_variables = forms.CharField(label='Description Variables', widget=forms.Textarea(attrs={'rows': 4}), required=False)
    generate = forms.BooleanField(label='Generate Image', required=False)
    delete = forms.BooleanField(label='Delete Image', required=False)

    def __init__(self, *args, **kwargs):
        self.valid_description_variables = kwargs.pop('valid_description_variables', [])
        super().__init__(*args, **kwargs)

    def clean_description_variables(self):
        data = self.cleaned_data['description_variables']
        if data:
            variables = [var.strip() for var in data.split(',')]
            invalid_vars = [var for var in variables if var not in self.valid_description_variables]
            if invalid_vars:
                raise forms.ValidationError(f"Undeclared description variables: {', '.join(invalid_vars)}")
            return variables
        return []

ImageFormSet = formset_factory(ImageForm, extra=1)

class ImageDescriptionForm(forms.Form):
    description_variable = forms.CharField(label='Description Variable', max_length=255, required=False)
    explanation = forms.CharField(label='Explanation', widget=forms.Textarea(attrs={'rows': 4}), required=False)
    delete = forms.BooleanField(label='Delete Image', required=False)

ImageDescriptionFormSet = formset_factory(ImageDescriptionForm, extra=1)

class StyleImageForm(forms.Form):
    image_base_name = forms.CharField(label='Image File Base Name',
                                      max_length=100,
                                      widget=forms.TextInput(attrs={'readonly': 'readonly'}),
                                      required=False)
    user_prompt = forms.CharField(label='Instructions for creating image', widget=forms.Textarea(attrs={'rows': 12}), required=False)
    style_description = forms.CharField(label='AI-generated style description', widget=forms.Textarea(attrs={'rows': 12}), required=False)

class ImageSequenceForm(forms.Form):
    pass

class HumanAudioInfoForm(forms.ModelForm):
    class Meta:
        model = HumanAudioInfo
        fields = ['method', 'preferred_tts_engine', 'preferred_tts_voice',
                  'use_for_segments', 'use_for_words', 'use_context', 'voice_talent_id',
                  'audio_file', 'manual_align_metadata_file']

class LabelledSegmentedTextForm(forms.Form):
    labelled_segmented_text = forms.CharField(widget=forms.Textarea(attrs={'rows': 15,
                                                                           'cols': 80,
                                                                           'readonly': 'readonly'}))

class PhoneticHumanAudioInfoForm(forms.ModelForm):
    class Meta:
        model = PhoneticHumanAudioInfo
        fields = ['method', 'preferred_tts_engine', 'preferred_tts_voice',
                  'use_for_segments', 'use_for_words', 'voice_talent_id']

class AudioItemForm(forms.Form):
    text = forms.CharField(
        label='Text',
        max_length=500,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        required=True
    )
    context = forms.CharField(
        label='Context',
        max_length=500,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        required=False
    )
    audio_file_path = forms.FileField(
        label='Audio File',
        required=False
    )
    audio_file_base_name = forms.CharField(
        label='Audio File Base Name',
        max_length=100,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        required=False
    )

AudioItemFormSet = formset_factory(AudioItemForm, extra=0)
    
class PhoneticLexiconForm(forms.Form):
    language = forms.ChoiceField(choices=[])  # Empty choices initially
    encoding = forms.ChoiceField(
        label='Encoding Type',
        choices=[('ipa', 'IPA'), ('arpabet_like', 'ARPAbet-like')],
        required=False
    )
##    letter_groups = forms.CharField(label='Letter Groups', widget=forms.Textarea, required=False)
##    accents = forms.CharField(label='Accents', widget=forms.Textarea, required=False)
    grapheme_phoneme_correspondence_entries_exist = forms.CharField(
        label='Grapheme to phoneme entries exist',
        max_length=5,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        required=False)
    plain_phonetic_lexicon_entries_exist = forms.CharField(
        label='Plain phonetic lexicon entries exist',
        max_length=5,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        required=False)
    plain_lexicon_file = forms.FileField(
        label='Plain phonetic lexicon file (txt or JSON)',
        required=False)
    aligned_phonetic_lexicon_entries_exist = forms.CharField(
        label='Aligned phonetic lexicon entries exist',
        max_length=5,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        required=False)
    aligned_lexicon_file = forms.FileField(
        label='Aligned phonetic lexicon file (JSON)',
        required=False)
    display_grapheme_to_phoneme_entries = forms.BooleanField(required=False)
    display_new_plain_lexicon_entries = forms.BooleanField(required=False)
    display_approved_plain_lexicon_entries = forms.BooleanField(required=False)
    display_new_aligned_lexicon_entries = forms.BooleanField(required=False)
    display_approved_aligned_lexicon_entries = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(PhoneticLexiconForm, self).__init__(*args, **kwargs)

        if user:
            # Query the languages for which the user is a language master
            languages = LanguageMaster.objects.filter(user=user).values_list('language', flat=True)
            self.fields['language'].choices = [(lang, lang.capitalize()) for lang in languages]

class PlainPhoneticLexiconEntryForm(forms.Form):
    word = forms.CharField(widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    phonemes = forms.CharField()
    approve = forms.BooleanField(required=False)
    delete = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super(PlainPhoneticLexiconEntryForm, self).__init__(*args, **kwargs)
        # Additional initialization can go here

PlainPhoneticLexiconEntryFormSet = formset_factory(PlainPhoneticLexiconEntryForm, extra=0)

class AlignedPhoneticLexiconEntryForm(forms.Form):
    word = forms.CharField(widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    phonemes = forms.CharField(widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    aligned_graphemes = forms.CharField()
    aligned_phonemes = forms.CharField()
    approve = forms.BooleanField(required=False)
    delete = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super(AlignedPhoneticLexiconEntryForm, self).__init__(*args, **kwargs)
        # Additional initialization can go here

AlignedPhoneticLexiconEntryFormSet = formset_factory(AlignedPhoneticLexiconEntryForm, extra=0)

class GraphemePhonemeCorrespondenceForm(forms.Form):
    grapheme_variants = forms.CharField(widget=forms.TextInput(attrs={'dir': 'ltr'}))  # Default direction
    phonemes = forms.CharField(widget=forms.TextInput(attrs={'dir': 'ltr'}))  # Default direction

    def __init__(self, *args, **kwargs):
        language_direction = kwargs.pop('language_direction', 'ltr')
        phoneme_direction = kwargs.pop('phoneme_direction', language_direction)
        super(GraphemePhonemeCorrespondenceForm, self).__init__(*args, **kwargs)
        self.fields['grapheme_variants'].widget.attrs['dir'] = language_direction
        self.fields['phonemes'].widget.attrs['dir'] = phoneme_direction

GraphemePhonemeCorrespondenceFormSet = formset_factory(GraphemePhonemeCorrespondenceForm, extra=1)

class AccentCharacterForm(forms.Form):
    unicode_value = forms.CharField(widget=forms.TextInput(attrs={'dir': 'ltr'}))

AccentCharacterFormSet = formset_factory(AccentCharacterForm, extra=1)

class SatisfactionQuestionnaireForm(forms.ModelForm):
    class Meta:
        model = SatisfactionQuestionnaire
        fields = [
            'clara_version',
            'generated_by_ai',
            'text_type',
            'grammar_correctness',
            'vocabulary_appropriateness',
            'style_appropriateness',
            'content_appropriateness',
            'cultural_elements',
            'text_engagement',
            'correction_time_text',
            'correction_time_annotations',
            'image_match',
            'image_editing_time',
            'shared_intent',
            'purpose_text',
            'functionality_suggestion',
            'ui_improvement_suggestion',
        ]
        widgets = {
            'clara_version': forms.Select(attrs={'class': 'form-control'}),
            'generated_by_ai': forms.Select(attrs={'class': 'form-control'}),
            'text_type': forms.Select(attrs={'class': 'form-control'}),
            'grammar_correctness': forms.Select(attrs={'class': 'form-control'}),
            'vocabulary_appropriateness': forms.Select(attrs={'class': 'form-control'}),
            'style_appropriateness': forms.Select(attrs={'class': 'form-control'}),
            'content_appropriateness': forms.Select(attrs={'class': 'form-control'}),
            'cultural_elements': forms.Select(attrs={'class': 'form-control'}),
            'text_engagement': forms.Select(attrs={'class': 'form-control'}),
            'correction_time_text': forms.Select(attrs={'class': 'form-control'}),
            'correction_time_annotations': forms.Select(attrs={'class': 'form-control'}),
            'image_match': forms.Select(attrs={'class': 'form-control'}),
            'image_editing_time': forms.Select(attrs={'class': 'form-control'}),
            'shared_intent': forms.Select(attrs={'class': 'form-control'}),
            'purpose_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'functionality_suggestion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ui_improvement_suggestion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class FundingRequestForm(forms.ModelForm):
    class Meta:
        model = FundingRequest
        exclude = ['user', 'status', 'funder', 'credit_assigned', 'decision_comment', 'decision_made_at']

class ApproveFundingRequestForm(forms.Form):
    id = forms.DecimalField(max_digits=10, required=True)
    credit_assigned = forms.DecimalField(max_digits=10, decimal_places=2, required=False, help_text="Amount of credit to assign")
    user = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    #language = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    #native_or_near_native = forms.CharField(max_length=3, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    language_native_or_near_native = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    text_type = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    purpose = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    other_purpose = forms.CharField(max_length=500, widget=forms.TextInput(attrs={'readonly': 'readonly'}), required=False)
    status = forms.CharField(max_length=500, widget=forms.TextInput(attrs={'readonly': 'readonly'}))

##    class Meta:
##        model = FundingRequest
##        fields = ['id', 'credit_assigned']

        #widgets = {'id': forms.HiddenInput()}

ApproveFundingRequestFormSet = formset_factory(ApproveFundingRequestForm, extra=0)
        
class FundingRequestSearchForm(forms.Form):
    language = forms.ChoiceField(choices=[('', 'Any')] + list(SUPPORTED_LANGUAGES_AND_OTHER), required=False)
    native_or_near_native = forms.ChoiceField(choices = [('', 'Any'), (True, 'Yes'), (False, 'No')], required=False)
    text_type = forms.ChoiceField(choices=[('', 'Any')] + FundingRequest.CONTENT_TYPE_CHOICES, required=False)
    purpose = forms.ChoiceField(choices=[('', 'Any')] + FundingRequest.PURPOSE_CHOICES, required=False)
    status = forms.ChoiceField(choices=[('', 'Any')] + FundingRequest.STATUS_CHOICES, required=False)

