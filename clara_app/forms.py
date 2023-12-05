from django import forms
from django.forms import formset_factory
from django.contrib.auth.forms import UserCreationForm

from .models import Content, UserProfile, UserConfiguration, LanguageMaster
from .models import CLARAProject, HumanAudioInfo, PhoneticHumanAudioInfo, PhoneticHumanAudioInfo, Rating, Comment
from django.contrib.auth.models import User

from .constants import SUPPORTED_LANGUAGES, SUPPORTED_LANGUAGES_AND_DEFAULT

# Remove custom User
# Custom version of django.contrib.auth.forms.UserCreationForm
# which uses clara_app.models.User instead of auth.User
# class ClaraUserCreationForm(UserCreationForm):
    # class Meta(UserCreationForm.Meta):
        # model = User
        # fields = UserCreationForm.Meta.fields
        
class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']
        
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['bio', 'location', 'birth_date', 'profile_picture']

class UserConfigForm(forms.ModelForm):
    class Meta:
        model = UserConfiguration
        fields = ['gpt_model', 'max_annotation_words']  
        widgets = {
            'gpt_model': forms.Select(choices=[('gpt-4', 'GPT-4'),
                                               ('gpt-4-1106-preview', 'GPT-4 Turbo')]),
            'max_annotation_words': forms.Select(choices=[(100, '100'),
                                                          (250, '250'),
                                                          (500, '500'),
                                                          (1000, '1000')])
        }
        
class AssignLanguageMasterForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.all())
    language = forms.ChoiceField(choices=SUPPORTED_LANGUAGES_AND_DEFAULT)

class DeleteTTSDataForm(forms.Form):
    language = forms.ChoiceField(choices=SUPPORTED_LANGUAGES)

class ContentRegistrationForm(forms.ModelForm):
    class Meta:
        model = Content
        fields = [
            'external_url', 'title', 'text_type', 'l2', 'l1', 'length_in_words', 'author',
            'voice', 'annotator', 'difficulty_level'
        ]

class ContentSearchForm(forms.Form):
    l2 = forms.ChoiceField(choices=[('', 'Any')] + SUPPORTED_LANGUAGES, required=False)
    l1 = forms.ChoiceField(choices=[('', 'Any')] + SUPPORTED_LANGUAGES, required=False)
    title = forms.CharField(max_length=255, required=False)

class ProjectCreationForm(forms.ModelForm):
    class Meta:
        model = CLARAProject
        fields = ['title', 'l2', 'l1']

class ProjectSearchForm(forms.Form):
    title = forms.CharField(required=False)
    l2 = forms.ChoiceField(choices=[('', 'Any')] + list(SUPPORTED_LANGUAGES), required=False)
    l1 = forms.ChoiceField(choices=[('', 'Any')] + list(SUPPORTED_LANGUAGES), required=False)

class AddProjectMemberForm(forms.Form):
    ROLE_CHOICES = [
        ('VIEWER', 'Viewer'),
        ('ANNOTATOR', 'Annotator'),
        ('OWNER', 'Owner'),        
        # Add more roles as needed...
    ]
    
    user = forms.ModelChoiceField(queryset=User.objects.all())
    role = forms.ChoiceField(choices=ROLE_CHOICES)
       
class UpdateProjectTitleForm(forms.Form):
    new_title = forms.CharField(max_length=200)

class AddCreditForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.all())
    credit = forms.DecimalField()

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
    
    def __init__(self, *args, prompt=None, **kwargs):
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
            ('improve', 'Improve existing segmented text using AI'),
            ('manual', 'Manually enter/edit segmented text'),
            ('load_archived', 'Load archived version')
        ]

    def __init__(self, *args, prompt=None, jieba_supported=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text_choice'].choices = self.TEXT_CHOICES if jieba_supported else [
            choice for choice in self.TEXT_CHOICES if choice[0] != 'jieba'
            ]
    
class CreateSummaryTextForm(CreateAnnotatedTextForm):
    TEXT_CHOICES = [
        ('generate', 'Generate summary using AI'),
        ('improve', 'Improve existing summary using AI'),
        ('manual', 'Manually enter/edit text'),
        ('load_archived', 'Load archived version')
    ]
    
    def __init__(self, *args, prompt=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text_choice'].choices = self.TEXT_CHOICES

class CreateCEFRTextForm(CreateAnnotatedTextForm):
    TEXT_CHOICES = [
        ('generate', 'Estimate CEFR level using AI'),
        ('manual', 'Manually enter/edit CEFR level'),
        ('load_archived', 'Load archived version')
    ]
    
    def __init__(self, *args, prompt=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text_choice'].choices = self.TEXT_CHOICES

class CreatePhoneticTextForm(CreateAnnotatedTextForm):
    TEXT_CHOICES = [
        ('generate', 'Generate phonetic text'),
        ('manual', 'Manually edit/enter phonetic text'),
        ('load_archived', 'Load archived version')
    ]

    def __init__(self, *args, prompt=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text_choice'].choices = self.TEXT_CHOICES
    
class CreateGlossedTextForm(CreateAnnotatedTextForm):
    TEXT_CHOICES = [
        ('generate', 'Generate annotated text using AI'),
        ('correct', 'Try to fix errors in malformed annotated text using AI'), 
        ('improve', 'Improve existing annotated text using AI'),
        ('manual', 'Manually enter annotated text'),
        ('load_archived', 'Load archived version')
    ]

    def __init__(self, *args, prompt=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text_choice'].choices = self.TEXT_CHOICES

class CreateLemmaTaggedTextForm(CreateAnnotatedTextForm):
    TEXT_CHOICES = [
        ('trivial', 'Generate annotated text with trivial tags'),
        ('tree_tagger', 'Generate annotated text using TreeTagger'),
        ('generate', 'Generate annotated text using AI'),
        ('correct', 'Try to fix errors in malformed annotated text using AI'), 
        ('improve', 'Improve existing annotated text using AI'),
        ('manual', 'Manually enter annotated text'),
        ('load_archived', 'Load archived version')
    ]

    def __init__(self, *args, tree_tagger_supported=False, archived_versions=None, current_version='', **kwargs):
        super(CreateLemmaTaggedTextForm, self).__init__(*args, archived_versions=archived_versions, current_version=current_version, **kwargs)
        self.fields['text_choice'].choices = self.TEXT_CHOICES if tree_tagger_supported else [
            choice for choice in self.TEXT_CHOICES if choice[0] != 'tree_tagger'
        ]
        
class CreateLemmaAndGlossTaggedTextForm(CreateAnnotatedTextForm):
    TEXT_CHOICES = [
        ('improve', 'Improve existing annotated text using AI'),
        ('manual', 'Manually enter annotated text'),
        ('load_archived', 'Load archived version')
    ]

    def __init__(self, *args, tree_tagger_supported=False, archived_versions=None, current_version='', **kwargs):
        super(CreateLemmaAndGlossTaggedTextForm, self).__init__(*args, archived_versions=archived_versions, current_version=current_version, **kwargs)
        self.fields['text_choice'].choices = self.TEXT_CHOICES if tree_tagger_supported else [
            choice for choice in self.TEXT_CHOICES if choice[0] != 'tree_tagger'
        ]

class RenderTextForm(forms.Form):
    pass

class RegisterAsContentForm(forms.Form):
    register_as_content = forms.BooleanField(required=False, initial=False)

class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['rating']

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['comment']
        
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
        ("gloss", "Gloss"),
        ("lemma", "Lemma"),
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

class AudioMetadataForm(forms.Form):
    metadata = forms.CharField(widget=forms.Textarea)

class ImageForm(forms.Form):
    image_file_path = forms.ImageField(label='Image File', required=False)
    image_base_name = forms.CharField(label='Image File Base Name',
                                      max_length=100,
                                      widget=forms.TextInput(attrs={'readonly': 'readonly'}),
                                      required=False)
    image_name = forms.CharField(label='Image Name', max_length=100, required=True)
    associated_text = forms.CharField(label='Associated Text', widget=forms.Textarea, required=False)
    associated_areas = forms.CharField(label='Associated Areas', widget=forms.Textarea, required=False)
    page = forms.IntegerField(label='Page Number', min_value=1, required=True)
    position = forms.ChoiceField(label='Position', choices=[('top', 'Top'), ('bottom', 'Bottom')], required=True)
    delete = forms.BooleanField(label='Delete Image', required=False)

ImageFormSet = formset_factory(ImageForm, extra=1)

class HumanAudioInfoForm(forms.ModelForm):
    class Meta:
        model = HumanAudioInfo
        fields = ['method', 'use_for_segments', 'use_for_words', 'voice_talent_id',
                  'audio_file', 'manual_align_metadata_file']

class PhoneticHumanAudioInfoForm(forms.ModelForm):
    class Meta:
        model = PhoneticHumanAudioInfo
        fields = ['method', 'use_for_segments', 'use_for_words', 'voice_talent_id']

class AudioItemForm(forms.Form):
    text = forms.CharField(
        label='Text',
        max_length=500,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        required=True
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

AudioItemFormSet = formset_factory(AudioItemForm, extra=1)
    
class PhoneticLexiconForm(forms.Form):
    language = forms.ChoiceField(choices=[])  # Empty choices initially
    letter_groups = forms.CharField(label='Letter Groups', widget=forms.Textarea, required=False)
    accents = forms.CharField(label='Accents', widget=forms.Textarea, required=False)
    plain_phonetic_lexicon_entries_exist = forms.FileField(
        label='Plain phonetic lexicon entries exist',
        max_length=5,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        required=False)
    plain_lexicon_file = forms.FileField(
        label='Plain phonetic lexicon file (JSON)',
        required=False)
    aligned_phonetic_lexicon_entries_exist = forms.FileField(
        label='Aligned phonetic lexicon entries exist',
        max_length=5,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        required=False)
    aligned_lexicon_file = forms.FileField(
        label='Aligned phonetic lexicon file (JSON)',
        required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(PhoneticLexiconForm, self).__init__(*args, **kwargs)

        self.fields['letter_groups'].help_text = 'Use one line per character. If there are several forms for a character, separate them with spaces and put the canonical form first.'
        self.fields['accents'].help_text = 'Use one line per accent character. Enter Unicode code points (e.g., U+064B) for non-printable characters.'

        if user:
            # Query the languages for which the user is a language master
            languages = LanguageMaster.objects.filter(user=user).values_list('language', flat=True)
            self.fields['language'].choices = [(lang, lang.capitalize()) for lang in languages]
