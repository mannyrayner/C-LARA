from .clara_internalise import internalize_text

def numbered_page_list_for_coherent_images(project, clara_project_internal):
    if project.use_translation_for_images:
        translated_text = clara_project_internal.load_text_version_or_null("translated")
        if translated_text:
            translated_text_object = internalize_text(translated_text, project.l2, project.l1, "translated")
            numbered_page_list = translated_text_object.to_numbered_page_list(translated=True)
        else:
            segmented_text = clara_project_internal.load_text_version("segmented_with_title")
            segmented_text_object = internalize_text(segmented_text, project.l2, project.l1, "segmented")
            numbered_page_list = segmented_text_object.to_numbered_page_list()
            for item in numbered_page_list:
                item['original_page_text'] = item['text']
                item['text'] = ''
    else:
        segmented_text = clara_project_internal.load_text_version("segmented_with_title")
        segmented_text_object = internalize_text(segmented_text, project.l2, project.l1, "segmented")
        numbered_page_list = segmented_text_object.to_numbered_page_list()
        
    return numbered_page_list
