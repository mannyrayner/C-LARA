from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from .models import CLARAProject

from django_q.tasks import async_task
from .forms import ImageFormSet, ImageDescriptionFormSet, StyleImageForm, ImageSequenceForm 
from .utils import get_user_config, user_has_open_ai_key_or_credit, store_api_calls, make_asynch_callback_and_report_id
from .utils import user_has_a_project_role
from .utils import get_task_updates
from .utils import uploaded_file_to_file

from .clara_main import CLARAProjectInternal
from .clara_image_repository_orm import ImageRepositoryORM

from .clara_dall_e_3_image import ( create_and_add_dall_e_3_image_for_whole_text,
                                    create_and_add_dall_e_3_image_for_style )

from .clara_images_utils import numbered_page_list_for_coherent_images
from .save_page_texts_multiple_utils import save_page_texts_multiple

from .clara_internalise import internalize_text
from .clara_mwe import annotate_mwes_in_text
from .clara_chatgpt4 import call_chat_gpt4, interpret_chat_gpt4_response_as_json, call_chat_gpt4_image, call_chat_gpt4_interpret_image
from .clara_classes import InternalCLARAError, InternalisationError, MWEError
from .clara_utils import get_config, file_exists, basename
from .clara_utils import post_task_update

import os
import json
import shutil
import logging
import pprint
import traceback
import tempfile

config = get_config()
logger = logging.getLogger(__name__)

@login_required
@user_has_a_project_role
def edit_images(request, project_id, dall_e_3_image_status):
    actions_requiring_openai = ( 'create_dalle_image_for_whole_text',
                                 'create_dalle_style_image',
                                 'generate_image_descriptions',
                                 'create_image_request_sequence')
    user = request.user
    can_use_ai = user_has_open_ai_key_or_credit(user)
    config_info = get_user_config(user)
    username = user.username
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    clara_version = get_user_config(request.user)['clara_version']

    if project.uses_coherent_image_set and project.use_translation_for_images and not clara_project_internal.load_text_version("translated"):
        messages.error(request, f"Project is marked as using translations to create images, but there are no translations yet")
        return render(request, 'clara_app/edit_images.html', {
                            'formset': ImageFormSet(initial=[], prefix='images'),
                            'description_formset': None,
                            'style_form': None,
                            'image_request_sequence_form': None,
                            'project': project,
                            'uses_coherent_image_set': False,
                            'clara_version': clara_version,
                            'errors': None,
                        })

    page_texts = None
    segmented_texts = None
    translated_texts = None
    mwe_texts = None
    lemma_texts = None
    gloss_texts = None
    
    try:
        # Don't try to correct syntax errors here, there should not be any.
        all_page_texts = clara_project_internal.get_page_texts()
        #pprint.pprint(all_page_texts)
        page_texts = all_page_texts['plain']
        segmented_texts = all_page_texts['segmented']
        translated_texts = all_page_texts['translated']
        mwe_texts = all_page_texts['mwe']
        lemma_texts = all_page_texts['lemma']
        gloss_texts = all_page_texts['gloss']
        try:
            mwe_text = clara_project_internal.load_text_version_or_null("mwe")
            if mwe_text:
                internalised_mwe_text = clara_project_internal.internalize_text(mwe_text, "mwe")
                # Do this so that we get an exception we can report if the MWEs don't match the text
                annotate_mwes_in_text(internalised_mwe_text)
        except MWEError as e:
             messages.error(request, f"{e.message}")
    except InternalisationError as e:
        messages.error(request, f"{e.message}")
    except InternalCLARAError as e:
        messages.error(request, f"{e.message}")
    except Exception as e:
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
   
    # Retrieve existing images
    images = clara_project_internal.get_all_project_images()
    initial_data = [{'image_file_path': img.image_file_path,
                     'image_base_name': basename(img.image_file_path) if img.image_file_path else None,
                     'image_name': img.image_name,
                     'associated_text': img.associated_text,
                     'associated_areas': img.associated_areas,
                     'page': img.page,
                     'page_text': page_texts[img.page - 1] if page_texts and img.page <= len(page_texts) else '',
                     'segmented_text': segmented_texts[img.page - 1] if segmented_texts and img.page <= len(segmented_texts) else '',
                     'translated_text': translated_texts[img.page - 1] if translated_texts and img.page <= len(translated_texts) else '',
                     'mwe_text': mwe_texts[img.page - 1] if mwe_texts and img.page <= len(mwe_texts) else '',
                     'lemma_text': lemma_texts[img.page - 1] if lemma_texts and img.page <= len(lemma_texts) else '',
                     'gloss_text': gloss_texts[img.page - 1] if gloss_texts and img.page <= len(gloss_texts) else '',
                     'position': img.position,
                     'style_description': img.style_description,
                     'content_description': img.content_description,
                     'request_type': img.request_type,
                     'description_variable': img.description_variable,
                     'description_variables': ', '.join(img.description_variables) if img.description_variables else '',
                     'user_prompt': img.user_prompt,
                     'display_text_fields': ( img.request_type != 'image-understanding' ),
                     'display_text_fields_label': 'Text versions' if ( img.request_type != 'image-understanding' ) else 'none',
                     }
                    for img in images ]
    pprint.pprint(initial_data)

    # Create placeholder image lines for pages that don't have an image, so that we can display the text versions for those pages.
    if page_texts:
        used_page_numbers = [ item['page'] for item in initial_data ]
        for page_number in range(1, len(page_texts) + 1):
            if not page_number in used_page_numbers:
                placeholder_data = {'image_file_path': None,
                                    'image_base_name': None,
                                    'image_name': f'image_{page_number}_top',
                                    'associated_text': '',
                                    'associated_areas': '',
                                    'page': page_number,
                                    'page_text': page_texts[page_number - 1] if page_number <= len(page_texts) else '',
                                    'segmented_text': segmented_texts[page_number - 1] if page_number <= len(segmented_texts) else '',
                                    'translated_text': translated_texts[page_number - 1] if page_number <= len(translated_texts) else '',
                                    'mwe_text': mwe_texts[page_number - 1] if page_number <= len(mwe_texts) else '',
                                    'lemma_text': lemma_texts[page_number - 1] if page_number <= len(lemma_texts) else '',
                                    'gloss_text': gloss_texts[page_number - 1] if page_number <= len(gloss_texts) else '',
                                    'position': 'top',
                                    'style_description': '',
                                    'content_description': '',
                                    'request_type': 'image-generation',
                                    'description_variable': None,
                                    'description_variables': '',
                                    'user_prompt': '',
                                    'display_text_fields': True,
                                    'display_text_fields_label': 'Text versions'
                                    }
                initial_data.append(placeholder_data)
    # Sort by page number with generation requests first
    initial_data = sorted(initial_data, key=lambda x: ( x['page'] + ( 0 if x['request_type'] == 'image-generation' else 0.1 ) ) )

    # Make sure that we only display text fields for the first image line with a given page number.
    page_numbers_already_mentioned = []
    for data in initial_data:
        page_number = data['page']
        if page_number in page_numbers_already_mentioned:
            data['display_text_fields'] = False
            data['display_text_fields_label'] = 'none'
        else:
            page_numbers_already_mentioned.append(page_number)

    #print(f'initial_data')
    #pprint.pprint(initial_data)
    
    if len(initial_data) != 0 and initial_data[0]['page'] == 0:
        # We have a style image on the notional page 0, move that information to the style image template
        style_image_record = initial_data[0]
        initial_style_image_data = { 'image_base_name': style_image_record['image_base_name'],
                                     'user_prompt': style_image_record['user_prompt'],
                                     'style_description': style_image_record['style_description']
                                     }
        style_description = style_image_record['style_description']
        # The other data is normal images that will appear in the text
        initial_data = initial_data[1:]
    elif project.uses_coherent_image_set:
        initial_style_image_data = { 'image_base_name': None,
                                     'user_prompt': ''
                                     }
        style_description = None
    else:
        initial_style_image_data = None
        style_description = None

    descriptions = clara_project_internal.get_all_project_image_descriptions()
    initial_description_data = [{'description_variable': desc.description_variable,
                                 'explanation': desc.explanation
                                 }
                                for desc in descriptions ]

    valid_description_variables = [desc['description_variable'] for desc in initial_description_data]

    if request.method == 'POST':
        if 'action' in request.POST: 
            action = request.POST['action']
            print(f'--- action = {action}')
            if action in actions_requiring_openai:
                if not can_use_ai:
                    messages.error(request, f"Sorry, you need a registered OpenAI API key or money in your account to create images")
                    return redirect('edit_images', project_id=project_id, dall_e_3_image_status='no_image')
                if action == 'create_dalle_image_for_whole_text':
                    task_type = f'create_dalle_e_3_images'
                    callback, report_id = make_asynch_callback_and_report_id(request, task_type)

                    async_task(create_and_add_dall_e_3_image_for_whole_text, project_id, callback=callback)
                    print(f'--- Started DALL-E-3 image generation task')
                    #Redirect to the monitor view, passing the task ID and report ID as parameters
                    return redirect('create_dall_e_3_image_monitor', project_id, report_id)
                elif action == 'generate_image_descriptions':
                    task_type = f'generate_image_descriptions'
                    callback, report_id = make_asynch_callback_and_report_id(request, task_type)

                    async_task(generate_image_descriptions, project_id, callback=callback)
                    print(f'--- Started image descriptions generation task')
                    #Redirect to the monitor view, passing the task ID and report ID as parameters
                    return redirect('create_dall_e_3_image_monitor', project_id, report_id)
                elif action == 'create_image_request_sequence':
                    task_type = f'create_image_request_sequence'
                    callback, report_id = make_asynch_callback_and_report_id(request, task_type)

                    async_task(create_image_request_sequence, project_id, callback=callback)
                    print(f'--- Started image request sequence generation task')
                    #Redirect to the monitor view, passing the task ID and report ID as parameters
                    return redirect('create_dall_e_3_image_monitor', project_id, report_id)
                elif action == 'create_dalle_style_image':
                    style_image_form = StyleImageForm(request.POST)
                    if not style_image_form.is_valid():
                        messages.error(request, "Invalid form data (form #{i}): {form}")
                        return redirect('edit_images', project_id=project_id, dall_e_3_image_status='no_image')
                    if not style_image_form.cleaned_data.get('user_prompt'):
                        messages.error(request, "No instructions given for creating style image.")
                        return redirect('edit_images', project_id=project_id, dall_e_3_image_status='no_image')
                    user_prompt = style_image_form.cleaned_data.get('user_prompt')
                    task_type = f'create_dalle_e_3_images'
                    callback, report_id = make_asynch_callback_and_report_id(request, task_type)

                    async_task(create_and_add_dall_e_3_image_for_style, project_id, user_prompt, callback=callback)
                    print(f'--- Started DALL-E-3 image generation task')
                    #Redirect to the monitor view, passing the task ID and report ID as parameters
                    return redirect('create_dall_e_3_image_monitor', project_id, report_id)
                
            elif action == 'save_image_descriptions':
                description_formset = ImageDescriptionFormSet(request.POST, prefix='descriptions')
                #print(description_formset)
                for i in range(0, len(description_formset)):
                    form = description_formset[i]
                    # Only use the last row if a new description variable has been filled in
                    if not ( i == len(description_formset) - 1 and not 'description_variable' in form.changed_data ):
                        if not form.is_valid():
                            print(f'--- Invalid description form data (form #{i}): {form}')
                            messages.error(request, "Invalid descrimption form data.")
                            return redirect('edit_images', project_id=project_id, dall_e_3_image_status='no_image')
                        description_variable = form.cleaned_data['description_variable']
                        explanation = form.cleaned_data['explanation']
                        delete = form.cleaned_data['delete']
                        if delete:
                            # We are deleting a variable
                            clara_project_internal.remove_project_image_description(description_variable)
                            messages.success(request, f"Deleted description variable: {description_variable}")
                        else:
                           # We are saving a possibly added or modified variable
                            clara_project_internal.add_project_image_description(description_variable, explanation)
                messages.success(request, "Description data saved")
                return redirect('edit_images', project_id=project_id, dall_e_3_image_status='no_image')
            else:
                image_requests = []
                new_plain_texts = []
                new_segmented_texts = []
                new_translated_texts = []
                new_mwe_texts = []
                new_lemma_texts = []
                new_gloss_texts = []
                formset = ImageFormSet(request.POST, request.FILES, prefix='images', form_kwargs={'valid_description_variables': valid_description_variables})
                
                errors = None
                if not formset.is_valid():
                    errors = formset.errors
                    print(f'errors = "{errors}"')
                    # Pass errors to the template
                    if project.uses_coherent_image_set:
                        style_form = StyleImageForm(initial=initial_style_image_data)
                        description_formset = ImageDescriptionFormSet(initial=initial_description_data, prefix='descriptions')
                        image_request_sequence_form = ImageSequenceForm()
                    else:
                        style_form = None
                        description_formset = None
                        image_request_sequence_form = None
                    return render(request, 'clara_app/edit_images.html', {
                        'formset': formset,
                        'description_formset': description_formset,
                        'style_form': style_form,
                        'image_request_sequence_form': image_request_sequence_form,
                        'project': project,
                        'uses_coherent_image_set': project.uses_coherent_image_set,
                        'clara_version': clara_version,
                        'errors': errors,
                    })
                for i in range(0, len(formset)):
                    form = formset[i]
                    #print(f"i = {i}. form.cleaned_data['display_text_fields_label'] = {form.cleaned_data['display_text_fields_label']}")
                    previous_record = initial_data[i] if i < len(initial_data) else None
                    #print(f'previous_record#{i} = {previous_record}')
                    # Ignore the last (extra) form if image_file_path has not been changed, i.e. we are not uploading a file
                    #print(f"--- form #{i}: form.changed_data = {form.changed_data}")
                    if not ( i == len(formset) - 1 and not 'image_file_path' in form.changed_data and not 'user_prompt' in form.changed_data ):

                        # form.cleaned_data.get('image_file_path') is special, since we get it from uploading a file.
                        # If there is no file upload, the value is null
                        if form.cleaned_data.get('image_file_path'):
                            uploaded_image_file_path = form.cleaned_data.get('image_file_path')
                            real_image_file_path = uploaded_file_to_file(uploaded_image_file_path)
                            uploaded_file = True
                            #print(f'--- real_image_file_path for {image_name} (from upload) = {real_image_file_path}')
                        elif previous_record:
                            real_image_file_path = previous_record['image_file_path']
                            #print(f'--- real_image_file_path for {image_name} (previously stored) = {real_image_file_path}')
                            uploaded_file = False
                        else:
                            real_image_file_path = None
                            uploaded_file = False

                        #print(f"i = {i}, page_text = '{form.cleaned_data['page_text']}', translated_text = '{form.cleaned_data['translated_text']}'")     

                        if 'display_text_fields_label' in form.cleaned_data and form.cleaned_data['display_text_fields_label'] == 'Text versions':
                            new_plain_texts.append(form.cleaned_data['page_text'])
                            new_segmented_texts.append(form.cleaned_data['segmented_text'])
                            new_translated_texts.append(form.cleaned_data['translated_text'])
                            new_mwe_texts.append(form.cleaned_data['mwe_text'])
                            new_lemma_texts.append(form.cleaned_data['lemma_text'])
                            new_gloss_texts.append(form.cleaned_data['gloss_text'])
                            
                        associated_text = form.cleaned_data.get('associated_text')
                        associated_areas = form.cleaned_data.get('associated_areas')
                        page = form.cleaned_data.get('page', 1)
                        position = form.cleaned_data.get('position', 'bottom')
                        user_prompt = form.cleaned_data.get('user_prompt')
                        generate = form.cleaned_data.get('generate')
                        delete = form.cleaned_data.get('delete')
                        request_type = form.cleaned_data.get('request_type')
                        content_description = form.cleaned_data.get('content_description')
                        description_variable = form.cleaned_data.get('description_variable')
                        description_variables = form.cleaned_data.get('description_variables')
                        if form.cleaned_data.get('image_name'):
                            image_name = form.cleaned_data.get('image_name')
                        elif previous_record and previous_record['image_name']:
                            image_name = previous_record['image_name']
                        else:
                            # If we're adding a new description, there will be no image name
                            image_name = f'get_{description_variable}'
                        
                        if previous_record and not content_description:
                            content_description = previous_record['content_description']
                        #print(f'--- real_image_file_path = {real_image_file_path}, image_name = {image_name}, page = {page}, delete = {delete}')

                        #print(f'image_name = "{image_name}", real_image_file_path = "{real_image_file_path}"')
                        #print(f'user_prompt = "{user_prompt}", content_description = "{content_description}"')
                        #print(f'description_variables = "{description_variables}"')

                        if image_name and delete and not errors:
                            # We are deleting an image
                            clara_project_internal.remove_project_image(image_name)
                            messages.success(request, f"Deleted image: {image_name}")
                        elif generate and user_prompt and not errors:
                            # We are generating or understanding an image. Put it on the queue for async processing at the end
                            image_request = { 'image_name': image_name,
                                              'page': page,
                                              'position': position,
                                              'user_prompt': user_prompt,
                                              'content_description': content_description,
                                              'style_description': style_description,
                                              'current_image': previous_record['image_file_path'] if previous_record else None,
                                              'request_type': request_type,
                                              'description_variable': description_variable,
                                              'description_variables': description_variables
                                              }
                            image_requests.append(image_request)
                            clara_project_internal.add_project_image(image_name, real_image_file_path,
                                                                     associated_text=associated_text,
                                                                     associated_areas=associated_areas,
                                                                     page=page, position=position,
                                                                     request_type=request_type,
                                                                     user_prompt=user_prompt,
                                                                     content_description=content_description,
                                                                     description_variable=description_variable,
                                                                     description_variables=description_variables,
                                                                     archive=False
                                                                     )
                        elif ( ( image_name and real_image_file_path ) or user_prompt ) and not errors:

                            clara_project_internal.add_project_image(image_name, real_image_file_path,
                                                                     associated_text=associated_text,
                                                                     associated_areas=associated_areas,
                                                                     page=page, position=position,
                                                                     request_type=request_type,
                                                                     user_prompt=user_prompt,
                                                                     content_description=content_description,
                                                                     description_variable=description_variable,
                                                                     description_variables=description_variables,
                                                                     archive=uploaded_file # Unless it's an uploaded file, we don't want to archive
                                                                     )
                            
                # Save the concatenated texts back to the project
                try:
                    types_and_texts = { 'plain': new_plain_texts,
                                        'segmented': new_segmented_texts,
                                        'translated': new_translated_texts,
                                        'mwe': new_mwe_texts,
                                        'lemma': new_lemma_texts,
                                        'gloss': new_gloss_texts }
                    #print(f'types_and_texts:')
                    #pprint.pprint(types_and_texts)
                    api_calls = clara_project_internal.save_page_texts_multiple(types_and_texts, user=username, can_use_ai=False, config_info=config_info)
                    store_api_calls(api_calls, project, project.user, 'correct')
                except ( InternalisationError, MWEError ) as e:
                    if not can_use_ai:
                        messages.error(request, f"There appears to be an inconsistency. Error details: {e.message}")
                        return redirect('edit_images', project_id=project_id, dall_e_3_image_status='no_image')
                    else:
                        task_type = f'correct_syntax'
                        callback, report_id = make_asynch_callback_and_report_id(request, task_type)

                        print(f'--- About to start syntax correction task')
                        async_task(save_page_texts_multiple, project, clara_project_internal, types_and_texts, username,
                                   config_info=config_info, callback=callback)
                        print(f'--- Started syntax correction task')
                        #Redirect to the monitor view, passing the project ID and report ID as parameters
                        return redirect('save_page_texts_multiple_monitor', project_id, report_id)
                                                   
                if len(image_requests) != 0:
                    if not can_use_ai:
                        messages.error(request, f"Sorry, you need a registered OpenAI API key or money in your account to create images")
                        return redirect('edit_images', project_id=project_id, dall_e_3_image_status='no_image')
                    task_type = f'create_dalle_e_3_images'
                    callback, report_id = make_asynch_callback_and_report_id(request, task_type)
                    async_task(create_and_add_coherent_dall_e_3_images, project_id, image_requests, callback=callback)
                    return redirect('create_dall_e_3_image_monitor', project_id, report_id)
                else:            
                    messages.success(request, "Image data updated")
                    return redirect('edit_images', project_id=project_id, dall_e_3_image_status='no_image')
    else:
        formset = ImageFormSet(initial=initial_data, prefix='images', form_kwargs={'valid_description_variables': valid_description_variables})
        description_formset = ImageDescriptionFormSet(initial=initial_description_data, prefix='descriptions')
        style_form = StyleImageForm(initial=initial_style_image_data)
        if project.uses_coherent_image_set:
            image_request_sequence_form = ImageSequenceForm()
        else:
            image_request_sequence_form = None
        #print(f'--- image_request_sequence_form = {image_request_sequence_form}')
        
        if dall_e_3_image_status == 'finished':
            messages.success(request, "Image task successfully completed")
        elif dall_e_3_image_status == 'error':
            messages.error(request, "Something went wrong when performing image task. Look at the 'Recent task updates' view for further information.")
        elif dall_e_3_image_status == 'finished_syntax_correction':
            messages.success(request, "There was an error in the syntax. This has been corrected and the text has been saved")
        elif dall_e_3_image_status == 'error_syntax_correction':
            messages.error(request, "There was an error in the syntax, and something went wrong when trying to fix it. Look at the 'Recent task updates' view for further information.")

    return render(request, 'clara_app/edit_images.html', {'formset': formset,
                                                          'description_formset': description_formset,
                                                          'style_form': style_form,
                                                          'image_request_sequence_form': image_request_sequence_form,
                                                          'project': project,
                                                          'uses_coherent_image_set': project.uses_coherent_image_set,
                                                          'clara_version': clara_version,
                                                          'errors': []})

# Create the description variables for the text
def generate_image_descriptions(project_id, callback=None):
    try:
        project = get_object_or_404(CLARAProject, pk=project_id)
        clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
        user = project.user
        config_info = get_user_config(user)

        numbered_page_list = numbered_page_list_for_coherent_images(project, clara_project_internal)
        numbered_page_list_text = json.dumps(numbered_page_list)
        prompt = f"""
        You are to perform the first step in a process that will guide DALL-E-3 and GPT-4o in creating a set of
        illustrations for a text, provided in JSON form, which has been divided into numbered pages. In this
        step, you will analyse the text and create a list of items that are referred to more than
        once and whose appearance needs to be kept consistent across illustrations. Typical examples of such
        items are characters in a story (e.g. people, animals) and settings (e.g. buildings, rooms, background scenery).
        In a later stage of the process, we will use DALL-E-3 to create images, and then use GPT-4o to create
        a description for each item the first time it appears. These descriptions will then be inserted in later calls
        to DALL-E-3.

        Each item will be represented as a pair consisting of an identifier (a "description variable") and a
        phrase saying what the variable refers to (an "explanation"), in the format

        {{
            "description_variable": <variable>,
            "explanation": <explanation>
        }},

        The "explanations" will later be used to create instructions of the form

        "Depict <explanation> according to this description: <value of description_variable>"

        Write out the list of pairs in JSON form.

        Here is a simple example:

        Input:

        [
          {{
            "page": 1,
            "text": "Once upon a time, in a faraway kingdom, there lived a brave princess named Elara."
          }},
          {{
            "page": 2,
            "text": "Elara loved exploring the lush forest that surrounded her castle."
          }},
          {{
            "page": 3,
            "text": "One day, when she was out in the forest, Elana met a lost dragon called Ember."
          }},
          {{
            "page": 4,
            "text": "Elana and Ember soon became good friends and were always together."
          }}
        ]

        Output:

        [
          {{
            "description_variable": "Elara-description",
            "explanation": "Princess Elara"
          }},
          {{
            "description_variable": "forest-description",
            "explanation": "the forest"
          }},
          {{
            "description_variable": "Ember-description",
            "explanation": "Ember the dragon"
          }},
          
        ]

        Here is the JSON representation of the text:

        {numbered_page_list_text}

        Only write out the JSON representation of the sequence of ( description variables, explanation ) pairs, since the result will be read by a Python script.
        """
        n_attempts = 0
        limit = int(config.get('chatgpt4_annotation', 'retry_limit'))
        while n_attempts < limit:
            n_attempts += 1
            post_task_update(callback, f'--- Calling ChatGPT-4 (attempt #{n_attempts}) to create description variables')
            try: 
                api_call = call_chat_gpt4(prompt, config_info=config_info, callback=callback)
                store_api_calls([api_call], project, user, 'image_description_generation')
                response = api_call.response
                response_object = interpret_chat_gpt4_response_as_json(response, object_type='list', callback=callback)
                if not isinstance(response_object, list):
                    raise ValueError('Response is not a JSON list')
                if not is_well_formed_description_list(response_object, callback=callback):
                    raise ValueError(f'Error: response {response_object} is not a well-formed description list')
                clara_project_internal.remove_all_project_image_descriptions(callback=callback)
                for description in response_object:
                    description_variable = description['description_variable']
                    explanation = description['explanation']
                    clara_project_internal.add_project_image_description(description_variable, explanation, callback=callback)
                post_task_update(callback, "finished")
                return True
            except Exception as e:
                post_task_update(callback, f'Error: {str(e)}')
        post_task_update(callback, f'*** Giving up, have tried sending this to ChatGPT-4 {limit} times')
        post_task_update(callback, "error")
        return False
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, "error")
        return False

def is_well_formed_description_list(description_list, callback=None):
    try:
        for item in description_list:
            if not isinstance(item, dict):
                raise ValueError(f'Item {item} is not a dict')
            if 'description_variable' not in item or 'explanation' not in item:
                raise ValueError(f'Item {item} does not contain the fields "description_variable" and "explanation"')
        return True
    except ValueError as ve:
        post_task_update(callback, f'Error: {ve}')
        post_task_update(callback, "error")
        return False

def create_image_request_sequence(project_id, callback=None):
    try:
        project = get_object_or_404(CLARAProject, pk=project_id)
        clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
        user = project.user
        config_info = get_user_config(user)
        
        numbered_page_list = numbered_page_list_for_coherent_images(project, clara_project_internal)
        numbered_page_list_text = json.dumps(numbered_page_list)

        #print(f'numbered_page_list')
        #pprint.pprint(numbered_page_list)

        descriptions = clara_project_internal.get_all_project_image_descriptions(formatting='plain_lists', callback=callback)
        descriptions_text = json.dumps(descriptions)

        prompt = f"""
        You are to write a set of requests, in JSON form, that will guide DALL-E-3 and GPT-4o in creating a set of
        illustrations for a text, also provided in JSON form, which has been divided into numbered pages.

        To maintain visual consistency, a previous processing step has extracted a set of "description_variables"
        which refer to items (characters, objects, locations etc), which may occur in more than one image.

        Take all description variables from the list provided. Each description variable is paired with a brief
        explanation of its purpose, in the format

        {{
            "description_variable": <variable>,
            "explanation": <explanation>
        }},

        Each description variable will add a piece of text to a  DALL-E-3 prompt of the form

        "Depict <explanation> according to this description: <value of description_variable>"
        
        A DALL-E-3 image-generation request to create the image on page <page-number> of the text will be of the form:

        {{
          "request_type": "image-generation",
          "page": <page-number>,
          "prompt": "<main-request-text>",
          "description_variables": <list-of-description-variables>
        }}

        where <list-of-description-variables> is a list of "description_variables" 
        holding relevant descriptions created by previously executed GPT-4o image understanding requests.

        A GPT-4o image-understanding request to extract visual information from the previously generated image on page <page-number>
        of the text and store it in the "description_variable" <variable-name> will be of the form:

        {{
          "request_type": "image-understanding",
          "page": <page-number>,
          "prompt": "<request-text>",
          "description_variable": "<variable-name>"
        }}

        When generating the image requests, ensure that the description_variables from relevant image-understanding requests are included in the prompts
        for subsequent image-generation requests. This ensures visual consistency throughout the story.

        Here is a simple example:

        Text:

        [
          {{
            "page": 1,
            "text": "Once upon a time, in a faraway kingdom, there lived a brave princess named Elara."
          }},
          {{
            "page": 2,
            "text": "Elara loved exploring the lush forest that surrounded her castle."
          }},
          {{
            "page": 3,
            "text": "One day, when she was out in the forest, Elara met a lost dragon called Ember."
          }}
        ]

        Description variables:

        [
          {{
            "description_variable": "Elara-description",
            "explanation": "Princess Elara"
          }},
          {{
            "description_variable": "forest-description",
            "explanation": "the forest"
          }}

        ]

        Output:

        [
          {{
            "request_type": "image-generation",
            "page": 1,
            "prompt": "An image of a brave princess named Elara standing in front of a grand castle, with the lush forest in the background.
            Elara is wearing a simple yet elegant dress, and she has a determined look on her face."
          }},
          {{
            "request_type": "image-understanding",
            "page": 1,
            "prompt": "Analyze this image depicting Princess Elara. Provide a comprehensive description that focuses on her appearance and attire.
            Detail her apparent age, ethnicity, facial features, hair style and colour, body build, clothing style, and overall demeanor. If it
            is not easy to extract this information from the image, e.g. regarding ethnicity, make a plausible decision.
            A detailed description is crucial for ensuring consistency in her portrayal across all subsequent images in the series.
            Use precise, descriptive language to capture her essence, as this information will directly influence the generation of future images.",
            "description_variable": "Elara-description"
          }},
          {{
            "request_type": "image-generation",
            "page": 2,
            "prompt": "An image of Princess Elara exploring the forest, surrounded by tall trees, colorful flowers, and playful animals like rabbits and birds.",
            "description_variables": [ "Elara-description" ]
          }},
          {{
            "request_type": "image-understanding",
            "page": 2,
            "prompt": "Analyze this image depicting Princess Elara in the forest. Provide a comprehensive description of the forest.
            Detail the types, sizes and general appearance of trees and other vegetation, the quality of the lighting, and
            kinds of wildlife (animals, birds). If it is not easy to extract this information from the image, make a plausible decision.
            A detailed description is crucial for ensuring consistency across all subsequent images in the series.
            Use precise, descriptive language to capture the essence of the forest, as this information will directly influence the generation of future images.",
            "description_variable": "forest-description"
          }},
          {{
            "request_type": "image-generation",
            "page": 3,
            "prompt": "An image of Princess Elara and the dragon Ember in the forest. They have just met. Ember looks sad and lost, Elara looks kind
            and sympathetic.",
            "description_variables": [ "Elara-description", "forest-description" ]
          }}
        ]

        Here is the JSON representation of the text:

        {numbered_page_list_text}

        Here are the description variables you can use:

        {descriptions_text}

        Only write out the JSON representation of the sequence of image requests, since the result will be read by a Python script.
        """
        n_attempts = 0
        limit = int(config.get('chatgpt4_annotation', 'retry_limit'))
        while n_attempts < limit:
            n_attempts += 1
            post_task_update(callback, f'--- Calling ChatGPT-4 (attempt #{n_attempts}) to create image request sequence')
            try:
                api_call = call_chat_gpt4(prompt, config_info=config_info, callback=callback)
                store_api_calls([api_call], project, user, 'image_request_sequence')
                response = api_call.response

                sequence = interpret_chat_gpt4_response_as_json(response, object_type='list', callback=callback)
                check_well_formed_image_request_sequence(sequence, numbered_page_list, callback=callback)
                corrected_sequence = check_and_correct_initialization_in_image_request_sequence(sequence, project_id, user, config_info, callback=callback)
                
                clara_project_internal.remove_all_project_images_except_style_images(callback=callback)
                print(f'--- Saving image request sequence with {len(corrected_sequence)} records')
                for req in corrected_sequence:
                    request_type = req['request_type']
                    user_prompt = req['prompt']
                    page = req['page']
                    description_variable = req.get('description_variable', '')
                    position = req.get('position', 'bottom')
                    description_variables = req.get('description_variables', [])
                    image_name = f'image_{page}_{position}' if request_type == 'image-generation' else f'get_{description_variable}'
                    image_file_path = None
                    clara_project_internal.add_project_image(image_name, image_file_path,
                                                             page=page, position=position,
                                                             user_prompt=user_prompt,
                                                             request_type=request_type,
                                                             description_variable=description_variable,
                                                             description_variables=description_variables,
                                                             callback=callback)
                post_task_update(callback, "finished")
                return True
            except Exception as e:
                post_task_update(callback, f'Error: {str(e)}')
        post_task_update(callback, f'*** Giving up, have tried sending this to ChatGPT-4 {limit} times')
        post_task_update(callback, "error")
        return False
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, "error")
        return False

def check_well_formed_image_request_sequence(requests, numbered_page_list, callback=None):
    if not isinstance(requests, list):
        post_task_update(callback, f'Image request sequence is not a list: {requests}')
        raise ValueError('Bad image request sequence')
    
    for req in requests:
        if not (isinstance(req, dict) and 'request_type' in req and req['request_type'] in ('image-generation', 'image-understanding')):
            post_task_update(callback, f'Image request sequence item is not a dict containing a valid "request_type" field: {req}')
            raise ValueError('Bad image request sequence')
        
        if req['request_type'] == 'image-generation':
            if not ('prompt' in req and 'page' in req):
                post_task_update(callback, f'Image request sequence item of type "image-generation" does not contain "prompt" and "page" fields: {req}')
                raise ValueError('Bad image request sequence')
        
        if req['request_type'] == 'image-understanding':
            if not ('prompt' in req and 'page' in req and 'description_variable' in req):
                post_task_update(callback, f'Image request sequence item of type "image-understanding" does not contain "prompt", "page", and "description_variable" fields: {req}')
                raise ValueError('Bad image request sequence')

    page_numbers = [ item['page'] for item in numbered_page_list ]
    page_numbers_in_generation_requests = [ req['page'] for req in requests if req['request_type'] == 'image-generation' ]

    no_generation_page_numbers = [ page_number for page_number in page_numbers
                                   if not page_number in page_numbers_in_generation_requests and
                                   # We expect nothing to be generated for an empty page
                                   'text' in numbered_page_list[page_number - 1] and
                                   numbered_page_list[page_number - 1]['text'].strip() ]

    if no_generation_page_numbers:
        missing_pages_text = ', '.join([ str(page_number) for page_number in no_generation_page_numbers ])
        post_task_update(callback, f'Error: no image generation requests for page(s): {missing_pages_text}')
        raise ValueError('Bad image request sequence')
    else:
        page_numbers_text = ', '.join([ str(page_number) for page_number in page_numbers ])
        post_task_update(callback, f'--- Image generation requests found for pages: {page_numbers_text}')

    return True

def check_and_correct_initialization_in_image_request_sequence(sequence, project_id, user, config_info, callback=None):
    initialized_vars = set()
    corrected_sequence = []

    for i, req in enumerate(sequence):
        if req["request_type"] == "image-understanding":
            initialized_vars.add(req["description_variable"])
        elif req["request_type"] == "image-generation":
            # Fill in description_variables field if missing
            if not "description_variables" in req:
                req["description_variables"] = []
            # Only keep description variables from previous image-understanding steps
            req["description_variables"] = [var for var in req["description_variables"] if var in initialized_vars]

        corrected_sequence.append(req)

    return corrected_sequence

# Go through the generation requests, creating and storing the images.

def create_and_add_coherent_dall_e_3_images(project_id, requests, callback=None):
    try:
        project = get_object_or_404(CLARAProject, pk=project_id)
        clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
        user = project.user
        config_info = get_user_config(user)
        temp_dir = tempfile.mkdtemp()
        
        for request in requests:
            n_tries = 0
            retry_limit = int(config.get('dall_e_3', 'retry_limit'))
            request_succeeded = False
            
            while not request_succeeded and n_tries <= retry_limit:
                try:
                    request_type = request['request_type']
                    image_name = request['image_name']
                    page = request['page']
                    position = request['position']
                    user_prompt = request['user_prompt']
                    content_description = request['content_description']
                    style_description = request['style_description']
                    current_image = request['current_image']
                    description_variable = request['description_variable']
                    description_variables = request['description_variables']

                    if request_type not in ('image-generation', 'image-understanding'):
                        post_task_update(callback, f"*** Error: unknown request type in image generation sequence: {request_type}")
                        post_task_update(callback, "error")
                        return False

                    if request_type == 'image-generation':
                        full_prompt = f"""Create an image based on the following request: {user_prompt}

Make the style of the image consistent with the style of the previously generated image described here: {style_description}
        """
                        for description_variable in description_variables:
                            image_description = clara_project_internal.get_project_image_description(description_variable, callback=callback)
                            description_text = clara_project_internal.get_image_understanding_result(description_variable, callback=callback)
                            if image_description and description_text:
                                explanation_text = image_description.explanation
                                full_prompt += f"\n\nDepict {explanation_text} according to this description: {description_text}"

                        tmp_image_file = os.path.join(temp_dir, f'{image_name}_{page}_{position}.jpg')
                        post_task_update(callback, f"--- Creating DALL-E-3 image: name {image_name}, page {page}, position {position}")
                        api_calls_generate = call_chat_gpt4_image(full_prompt, tmp_image_file, config_info=config_info, callback=callback)
                        store_api_calls(api_calls_generate, project, project.user, 'image')
                        post_task_update(callback, f"--- Image created: {tmp_image_file}")

                        clara_project_internal.add_project_image(image_name, tmp_image_file, keep_file_name=False,
                                                                 associated_text='', associated_areas='',
                                                                 page=page, position=position,
                                                                 user_prompt=user_prompt,
                                                                 description_variables=description_variables,
                                                                 request_type=request_type)
                        post_task_update(callback, f"--- Image stored")
                        request_succeeded = True

                    elif request_type == 'image-understanding':
                        post_task_update(callback, f"--- Creating a description of part of image")
                        generated_image_object = clara_project_internal.get_generated_project_image_by_position(page, position, callback=callback)
                        if not generated_image_object:
                            post_task_update(callback, "error")
                            return False

                        generated_image_file_path = generated_image_object.image_file_path
                        if not file_exists(generated_image_file_path):
                            post_task_update(callback, f"Error: unable to find generated image for page={page}, position={position}")
                            post_task_update(callback, "error")
                            return False
                        api_call_interpret = call_chat_gpt4_interpret_image(user_prompt, generated_image_file_path,
                                                                            config_info=config_info, callback=callback)
                        description = api_call_interpret.response
                        clara_project_internal.store_image_understanding_result(description_variable, description,
                                                                                image_name=image_name, page=page, position=position, user_prompt=user_prompt,
                                                                                callback=callback)
                        post_task_update(callback, f"--- Description created for '{description_variable}': '{description}'")
                        request_succeeded = True

                except Exception as e:
                    post_task_update(callback, f"{request_type} task failed for page = {page}, position = {position}")
                    post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
                    n_tries += 1
            
            if not request_succeeded:
                post_task_update(callback, f"*** Error: giving up on {request_type} task after {retry_limit} unsuccessful attempts")
                post_task_update(callback, "error")
                return False
        
        post_task_update(callback, "finished")
        return True
    
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, "error")
        return False
    
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

# This is the API endpoint that the JavaScript will poll
@login_required
@user_has_a_project_role
def create_dall_e_3_image_status(request, project_id, report_id):
    messages = get_task_updates(report_id)
    print(f'{len(messages)} messages received')
    if 'error' in messages:
        status = 'error'
    elif 'finished' in messages:
        status = 'finished'  
    else:
        status = 'unknown'    
    return JsonResponse({'messages': messages, 'status': status})

@login_required
@user_has_a_project_role
def create_dall_e_3_image_monitor(request, project_id, report_id):
    project = get_object_or_404(CLARAProject, pk=project_id)

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/create_dall_e_3_image_monitor.html',
                  {'project_id': project_id, 'project': project, 'report_id': report_id, 'clara_version': clara_version})


def access_archived_images(request, project_id, image_name):
    project = get_object_or_404(CLARAProject, id=project_id)
    image_repo = ImageRepositoryORM()
    archived_images = image_repo.get_archived_images(project.internal_id, image_name)
    
    return render(request, 'clara_app/access_archived_images.html', {
        'project': project,
        'image_name': image_name,
        'archived_images': archived_images,
    })

def restore_image(request, project_id, archived_image_id):
    if request.method == "POST":
        project = get_object_or_404(CLARAProject, id=project_id)
        image_repo = ImageRepositoryORM()
        image_repo.restore_image(project.internal_id, archived_image_id)
        return redirect('edit_images', project_id=project_id, dall_e_3_image_status='no_image')
    else:
        return HttpResponseNotAllowed(['POST'])

def delete_archive_image(request, project_id, archived_image_id):
    if request.method == "POST":
        project = get_object_or_404(CLARAProject, id=project_id)
        image_repo = ImageRepositoryORM()
        image_repo.delete_archived_image(project.internal_id, archived_image_id)
        return redirect('access_archived_images', project_id=project_id, image_name=request.POST.get('image_name'))
    else:
        return HttpResponseNotAllowed(['POST'])
