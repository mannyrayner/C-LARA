from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django import forms
from .models import LocalisationBundle, BundleTranslation, LanguageMaster
from .forms import TemplateForm, PromptSelectionForm, StringForm, StringPairForm, CustomTemplateFormSet, CustomStringFormSet, CustomStringPairFormSet
from .forms import MorphologyExampleForm, CustomMorphologyExampleFormSet, MWEExampleForm, CustomMWEExampleFormSet, ExampleWithMWEForm, ExampleWithMWEFormSet
from .utils import get_user_config
from .utils import language_master_required, user_can_translate
from .clara_prompt_templates import PromptTemplateRepository
from .clara_classes import TemplateError
from .clara_utils import get_config
from .clara_utils import is_rtl_language
import logging

from .constants import (
    SUPPORTED_LANGUAGES,
    SUPPORTED_LANGUAGES_AND_DEFAULT
    )

config = get_config()
logger = logging.getLogger(__name__)

# Allow a language master to edit templates and examples
@login_required
@language_master_required
def edit_prompt(request):
    if request.method == 'POST':
        prompt_selection_form = PromptSelectionForm(request.POST, user=request.user)
        if prompt_selection_form.is_valid():
            language = prompt_selection_form.cleaned_data['language']
            default_language = prompt_selection_form.cleaned_data['default_language']
            template_or_examples = prompt_selection_form.cleaned_data['template_or_examples']
            # Assume the template is in English, i.e. an ltr language, but the examples are in "language"
            rtl_language = False if template_or_examples == 'template' else is_rtl_language(language) 
            operation = prompt_selection_form.cleaned_data['operation']
            annotation_type = prompt_selection_form.cleaned_data['annotation_type']
            if template_or_examples == 'template':
                PromptFormSet = forms.formset_factory(TemplateForm, formset=CustomTemplateFormSet, extra=0)
            elif annotation_type == 'morphology':
                PromptFormSet = forms.formset_factory(MorphologyExampleForm, formset=CustomMorphologyExampleFormSet, extra=1)
            elif annotation_type == 'mwe':
                PromptFormSet = forms.formset_factory(MWEExampleForm, formset=CustomMWEExampleFormSet, extra=1)
            elif annotation_type in ( 'gloss_with_mwe', 'lemma_with_mwe' ):
                PromptFormSet = forms.formset_factory(ExampleWithMWEForm, formset=ExampleWithMWEFormSet, extra=1)
            elif ( operation == 'annotate' or annotation_type in ('presegmented', 'segmented') ):
                PromptFormSet = forms.formset_factory(StringForm, formset=CustomStringFormSet, extra=1)
            else:
                PromptFormSet = forms.formset_factory(StringPairForm, formset=CustomStringPairFormSet, extra=1)
                
            prompt_repo = PromptTemplateRepository(language)

            if request.POST.get('action') == 'Load':
                # Start by trying to get the data from our current language
                try:
                    prompts = prompt_repo.load_template_or_examples(template_or_examples, annotation_type, operation)
                except TemplateError as e1:
                    # If we're editing 'default' and we didn't find anything on the previous step, there's nothing to use, so return blank values
                    if language == 'default':
                        messages.success(request, f"Warning: nothing found, you need to write the default {template_or_examples} from scratch")
                        prompt_repo_default = PromptTemplateRepository('default')
                        prompts = prompt_repo_default.blank_template_or_examples(template_or_examples, annotation_type, operation)
                    # If we're not editing 'default' and the default language is different, try that next
                    elif language != default_language:
                        try:
                            prompt_repo_default_language = PromptTemplateRepository(default_language)
                            prompts = prompt_repo_default_language.load_template_or_examples(template_or_examples, annotation_type, operation)
                        except TemplateError as e2:
                            # If we haven't already done that, try 'default'
                            if default_language != 'default':
                                try:
                                    prompt_repo_default = PromptTemplateRepository('default')
                                    prompts = prompt_repo_default.load_template_or_examples(template_or_examples, annotation_type, operation)
                                except TemplateError as e3:
                                    messages.error(request, f"{e3.message}")
                                    prompt_formset = None  # No formset because we couldn't get the data
                                    return render(request, 'clara_app/edit_prompt.html', {'prompt_selection_form': prompt_selection_form, 'prompt_formset': prompt_formset})
                            else:
                                messages.error(request, f"{e2.message}")
                                prompt_formset = None  # No formset because we couldn't get the data
                                return render(request, 'clara_app/edit_prompt.html', {'prompt_selection_form': prompt_selection_form, 'prompt_formset': prompt_formset})
                    else:
                        messages.error(request, f"{e1.message}")
                        prompt_formset = None  # No formset because we couldn't get the data
                        return render(request, 'clara_app/edit_prompt.html', {'prompt_selection_form': prompt_selection_form, 'prompt_formset': prompt_formset})

                # Prepare data
                if template_or_examples == 'template':
                    initial_data = [{'template': prompts}]
                elif annotation_type in ( 'morphology', 'mwe' ):
                    initial_data = [{'string1': triple[0], 'string2': triple[1], 'string3': triple[2]} for triple in prompts]
                elif annotation_type in ( 'gloss_with_mwe', 'lemma_with_mwe' ):
                    initial_data = [{'string1': pair[0], 'string2': pair[1]} for pair in prompts]
                elif template_or_examples == 'examples' and (operation == 'annotate' or annotation_type == 'segmented'):
                    initial_data = [{'string': example} for example in prompts]
                else:
                    initial_data = [{'string1': pair[0], 'string2': pair[1]} for pair in prompts]

                prompt_formset = PromptFormSet(initial=initial_data, prefix='prompts', rtl_language=rtl_language)

            elif request.POST.get('action') == 'Save':
                prompt_formset = PromptFormSet(request.POST, prefix='prompts', rtl_language=rtl_language)
                if prompt_formset.is_valid():
                    # Prepare data for saving
                    if template_or_examples == 'template':
                        new_prompts = prompt_formset[0].cleaned_data.get('template')
                    elif annotation_type in ( 'morphology', 'mwe' ):
                        new_prompts = [[form.cleaned_data.get('string1'), form.cleaned_data.get('string2'), form.cleaned_data.get('string3')]
                                       for form in prompt_formset]
                        if not new_prompts[-1][0] or not new_prompts[-1][1]:
                            # We didn't use the extra last field
                            new_prompts = new_prompts[:-1]
                    elif annotation_type in ( 'gloss_with_mwe', 'lemma_with_mwe' ):
                        new_prompts = [[form.cleaned_data.get('string1'), form.cleaned_data.get('string2')] for form in prompt_formset]
                        if not new_prompts[-1][0]:
                            # We didn't use the extra last field
                            new_prompts = new_prompts[:-1]
                    elif template_or_examples == 'examples' and (operation == 'annotate' or annotation_type in ( 'presegmented', 'segmented') ):
                        new_prompts = [form.cleaned_data.get('string') for form in prompt_formset]
                        if not new_prompts[-1]:
                            # We didn't use the extra last field
                            new_prompts = new_prompts[:-1]
                    else:
                        new_prompts = [[form.cleaned_data.get('string1'), form.cleaned_data.get('string2')] for form in prompt_formset]
                        if not new_prompts[-1][0] or not new_prompts[-1][1] or not new_prompts[-1][2]:
                            # We didn't use the extra last field
                            new_prompts = new_prompts[:-1]
                    #print(f'new_prompts:')
                    #pprint.pprint(new_prompts)
                    try:
                        prompt_repo.save_template_or_examples(template_or_examples, annotation_type, operation, new_prompts, request.user.username)
                        messages.success(request, "Data saved successfully")
                    except TemplateError as e:
                        messages.error(request, f"{e.message}")
                    
            else:
                raise Exception("Internal error: neither Load nor Save found in POST request to edit_prompt")

            clara_version = get_user_config(request.user)['clara_version']

            return render(request, 'clara_app/edit_prompt.html',
                          {'prompt_selection_form': prompt_selection_form, 'prompt_formset': prompt_formset, 'clara_version': clara_version})

    else:
        prompt_selection_form = PromptSelectionForm(user=request.user)
        prompt_formset = None  # No formset when the page is first loaded

    return render(request, 'clara_app/edit_prompt.html', {'prompt_selection_form': prompt_selection_form, 'prompt_formset': prompt_formset})

# ------------------------------------------------------------------
#  List all localisation bundles
# ------------------------------------------------------------------
@login_required
def bundle_list(request):
    # helper -------------------------------------------------------
    def user_is_master(lang):
        return (LanguageMaster.objects.filter(user=request.user,
                                              language=lang).exists())

    # gather bundles + translation tallies ------------------------
    bundles = (LocalisationBundle.objects
               .prefetch_related('bundleitem_set')
               .order_by('-created_at'))

    # pass 1: which languages have ≥1 translated string?
    langs_with_data = (BundleTranslation.objects
                       .exclude(text='')
                       .values_list('lang', flat=True)
                       .distinct())

    # candidate language columns
    all_langs = [c for c, _ in SUPPORTED_LANGUAGES if c != 'english']
    lang_cols = [l for l in all_langs
                 #if (l in langs_with_data) or user_is_master(l)]
                 if user_is_master(l)]

    # build per-bundle rows ---------------------------------------
    rows = []
    for b in bundles:
        counts = {}
        total  = b.bundleitem_set.count()
        for lang in lang_cols:
            done = BundleTranslation.objects.filter(item__bundle=b,
                                                    lang=lang,
                                                    text__gt="").count()
            counts[lang] = (done, total)
        rows.append({"bundle": b, "total": total, "counts": counts})

    total_cols = 3 + len(lang_cols)          # for colspan in template

    print(f'rows: {rows}')
    print(f'lang_cols: {lang_cols}')
    print(f'total_cols: {total_cols}')

    return render(request, "clara_app/bundle_list.html",
                  {"rows": rows,
                   "lang_cols": lang_cols,
                   "total_cols": total_cols})


@login_required
def edit_bundle(request, bundle_name, lang_code):
    if not user_can_translate(request.user, lang_code):
        return HttpResponseForbidden()

    bundle = get_object_or_404(LocalisationBundle, name=bundle_name)
    items = bundle.bundleitem_set.order_by('key').select_related()

    if request.method == 'POST':
        for item in items:
            text = request.POST.get(f"txt_{item.id}", "").strip()
            BundleTranslation.objects.update_or_create(
                item=item, lang=lang_code,
                defaults={'text': text, 'editor': request.user})
        messages.success(request, "Translations saved.")
        return redirect(request.path)

    # build dict id→existing translation
    existing = {bt.item_id: bt.text for bt in
                BundleTranslation.objects.filter(item__bundle=bundle,
                                                 lang=lang_code)}
    return render(request, 'clara_app/edit_bundle.html',
                  {'bundle': bundle, 'items': items,
                   'lang': lang_code, 'existing': existing})
