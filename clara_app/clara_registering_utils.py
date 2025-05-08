
from django.shortcuts import get_object_or_404

from .models import Content
from .models import CLARAProject, HumanAudioInfo, PhoneticHumanAudioInfo
from .utils import create_update

from .clara_main import CLARAProjectInternal
from .clara_utils import post_task_update

import traceback


def register_project_content_helper(project_id, phonetic_or_normal):
    try:
        project = get_object_or_404(CLARAProject, pk=project_id)
        clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
        phonetic = True if phonetic_or_normal == 'phonetic' else False

        # Check if human audio info exists for the project and if voice_talent_id is set
        if phonetic_or_normal == 'phonetic':
            human_audio_info = PhoneticHumanAudioInfo.objects.filter(project=project).first()
        else:
            human_audio_info = HumanAudioInfo.objects.filter(project=project).first()
        if human_audio_info:
            human_voice_id = human_audio_info.voice_talent_id
            audio_type_for_words = 'human' if human_audio_info.use_for_words else 'tts'
            audio_type_for_segments = 'human' if human_audio_info.use_for_segments else 'tts'
        else:
            audio_type_for_words = 'tts'
            audio_type_for_segments = 'tts'
            human_voice_id = None

        word_count0 = clara_project_internal.get_word_count(phonetic=phonetic)
        voice0 = clara_project_internal.get_voice(human_voice_id=human_voice_id, 
                                                  audio_type_for_words=audio_type_for_words, 
                                                  audio_type_for_segments=audio_type_for_segments)
        
        # CEFR level and summary are not essential, just continue if they're not available
        try:
            cefr_level0 = clara_project_internal.load_text_version("cefr_level")
        except Exception as e:
            cefr_level0 = None
        try:
            summary0 = clara_project_internal.load_text_version("summary")
        except Exception as e:
            summary0 = None
        word_count = 0 if not word_count0 else word_count0 # Dummy value if real one unavailable
        voice = "Unknown" if not voice0 else voice0 # Dummy value if real one unavailable
        cefr_level = "Unknown" if not cefr_level0 else cefr_level0 # Dummy value if real one unavailable
        summary = "Unknown" if not summary0 else summary0 # Dummy value if real one unavailable

        title = f'{project.title} (phonetic)' if phonetic_or_normal == 'phonetic' else project.title
        
        content, created = Content.objects.get_or_create(
                                project = project,  
                                defaults = {
                                    'title': title,  
                                    'l2': project.l2,  
                                    'l1': project.l1,
                                    'text_type': phonetic_or_normal,
                                    'length_in_words': word_count,  
                                    'author': project.user.username,  
                                    'voice': voice,  
                                    'annotator': project.user.username,  
                                    'difficulty_level': cefr_level,  
                                    'summary': summary
                                    }
                                )
        # Update any fields that might have changed
        if not created:
            content.title = title
            content.l2 = project.l2
            content.l1 = project.l1
            content.text_type = phonetic_or_normal
            content.length_in_words = word_count  
            content.author = project.user.username
            content.voice = voice 
            content.annotator = project.user.username
            content.difficulty_level = cefr_level
            content.summary = summary
            content.save()

        return content

    except Exception as e:
        post_task_update(callback, f"Exception when posting content: {str(e)}\n{traceback.format_exc()}")
        return None
