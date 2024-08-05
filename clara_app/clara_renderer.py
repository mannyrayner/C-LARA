"""
clara_renderer.py

This module implements a renderer for the CLARA application that generates static HTML pages for Text objects and their annotations.

Classes:
- StaticHTMLRenderer: A renderer that creates static HTML files for a given Text object and its annotations.

The StaticHTMLRenderer class provides methods for rendering pages, concordance pages, and vocabulary lists.
The renderer also supports self-contained rendering, which means that all multimedia assets are copied to the output directory.
"""

from .clara_inflection_tables import get_inflection_table_url

from .clara_utils import _s3_storage, absolute_file_name
from .clara_utils import remove_directory, make_directory, copy_directory, copy_directory_to_s3, directory_exists
from .clara_utils import copy_file, basename, read_txt_file, write_txt_file, output_dir_for_project_id
from .clara_utils import get_config, is_rtl_language, replace_punctuation_with_underscores, post_task_update 

from pathlib import Path
import os
from jinja2 import Environment, FileSystemLoader
import shutil
import traceback

config = get_config()

class StaticHTMLRenderer:
    def __init__(self, project_id, project_id_internal, l2,
                 phonetic=False, format_preferences_info=None,
                 normal_html_exists=False, phonetic_html_exists=False, callback=None):
        post_task_update(callback, f'--- Creating StaticHTMLRenderer, format_preferences_info = {format_preferences_info}')
        #self.title = title
        self.l2 = l2
        self.phonetic = phonetic
        self.format_preferences_info = format_preferences_info
        self.template_env = Environment(loader=FileSystemLoader(absolute_file_name(config.get('renderer', 'template_dir'))))
        self.template_env.filters['replace_punctuation'] = replace_punctuation_with_underscores

        self.project_id = str(project_id)
        self.project_id_internal = str(project_id_internal)
        self.normal_html_exists = normal_html_exists
        self.phonetic_html_exists = phonetic_html_exists
        
        # Create the new output_dir
        # Define the output directory based on the phonetic parameter
        phonetic_or_normal = "phonetic" if self.phonetic else "normal"
        self.output_dir = Path(output_dir_for_project_id(project_id, phonetic_or_normal))
        
##        # Remove the existing output_dir if we're not on S3 and it exists
##        if not _s3_storage and directory_exists(self.output_dir):
##            remove_directory(self.output_dir)

        self.delete_rendered_html_directory()
        
        make_directory(self.output_dir, parents=True)

        self._copy_static_files()

    def delete_rendered_html_directory(self):
        # Remove the existing output_dir if we're not on S3 and it exists
        if not _s3_storage and directory_exists(self.output_dir):
            remove_directory(self.output_dir)
        
    # Copy the files in the 'static' folder to the output_dir
    # Use format_preferences_info to modify the parametrised CSS file,
    # creating two versions: clara_styles.css and clara_styles_conconcordance.css
    def _copy_static_files(self):
        l2 = self.l2
        static_src = absolute_file_name('$CLARA/static')
        static_dst = self.output_dir / 'static'
        
        FONT_SIZE_MAP = {
            'small': '0.8em',
            'medium': '1.2em',
            'large': '1.6em',
            'huge': '2.4em',
            'HUGE': '3.2em',
            }

        DEFAULT_FORMAT_PREFERENCES = {
            'font_type': 'sans-serif',
            'font_size': 'medium',
            'text_align': 'left' if not is_rtl_language(l2) else 'right',
            
            'concordance_font_type': 'sans-serif',
            'concordance_font_size': 'medium',
            'concordance_text_align': 'left' if not is_rtl_language(l2) else 'right',
            }

        if _s3_storage:
            copy_directory_to_s3(static_src, s3_pathname=static_dst)
        else:
            copy_directory(static_src, static_dst)

        # Define default format preferences
        format_preferences = self.format_preferences_info.to_dict() if self.format_preferences_info else DEFAULT_FORMAT_PREFERENCES

        # Read the parametrized CSS file
        css_content = read_txt_file(static_dst / 'clara_styles_parametrised.css')

        # We want to align gloss popups with words on the left in an LTR language and on the right in an RTL language
        left_or_right_for_gloss_popup = 'left' if not is_rtl_language(l2) else 'right'

        # Replace placeholders with actual values
        css_content_main = css_content.replace('{{ font_size }}', FONT_SIZE_MAP[format_preferences['font_size']])
        css_content_main = css_content_main.replace('{{ font_type }}', format_preferences['font_type'])
        css_content_main = css_content_main.replace('{{ text_align }}', format_preferences['text_align'])
        css_content_main = css_content_main.replace('{{ left_or_right_for_gloss_popup }}', left_or_right_for_gloss_popup)

        css_content_concordance = css_content.replace('{{ font_size }}', FONT_SIZE_MAP[format_preferences['concordance_font_size']])
        css_content_concordance = css_content_concordance.replace('{{ font_type }}', format_preferences['concordance_font_type'])
        css_content_concordance = css_content_concordance.replace('{{ text_align }}', format_preferences['concordance_text_align'])
        css_content_concordance = css_content_concordance.replace('{{ left_or_right_for_gloss_popup }}', left_or_right_for_gloss_popup)

        # Write the modified CSS to the output directory
        write_txt_file(css_content_main, static_dst / 'clara_styles_main.css')
        write_txt_file(css_content_concordance, static_dst / 'clara_styles_concordance.css')


    def render_page(self, page, page_number, total_pages, l2_language, l1_language):
        is_rtl = is_rtl_language(l2_language)
        template = self.template_env.get_template('clara_page.html')
        rendered_page = template.render(page=page,
                                        total_pages=total_pages,
                                        project_id=self.project_id,
                                        #project_id_internal=self.project_id_internal,
                                        l2_language=l2_language,
                                        is_rtl=is_rtl,
                                        l1_language=l1_language,
                                        #title=self.title,
                                        page_number=page_number,
                                        page_number_str=str(page_number),
                                        phonetic=self.phonetic,
                                        normal_html_exists=self.normal_html_exists,
                                        phonetic_html_exists=self.phonetic_html_exists)
        return rendered_page 

    def render_concordance_page(self, lemma, concordance_segments, l2_language):
        inflection_table_url = get_inflection_table_url(lemma, l2_language)
        template = self.template_env.get_template('concordance_page.html')
        rendered_page = template.render(
            lemma=lemma,
            concordance_segments=concordance_segments,
            l2_language=l2_language,
            phonetic=self.phonetic,
            inflection_table_url=inflection_table_url
        )
        return rendered_page

    def render_alphabetical_vocabulary_list(self, vocabulary_list, l2_language):
        template = self.template_env.get_template('alphabetical_vocabulary_list.html')
        rendered_page = template.render(vocabulary_list=vocabulary_list,
                                        l2_language=l2_language)
        return rendered_page

    def render_frequency_vocabulary_list(self, vocabulary_list, l2_language):
        template = self.template_env.get_template('frequency_vocabulary_list.html')
        rendered_page = template.render(vocabulary_list=vocabulary_list,
                                        l2_language=l2_language)
        return rendered_page 
 
    def render_text(self, text, self_contained=False, callback=None):
        post_task_update(callback, f"--- Rendering_text") 
        # Create multimedia directory if self-contained is True
        if self_contained:
            multimedia_dir = self.output_dir / 'multimedia'
            make_directory(multimedia_dir, exist_ok=True)
            copy_operations = {}

            # Traverse the Text object, replacing each multimedia file with a
            # reference to the new multimedia directory and storing the copy operations
            for page in text.pages:
                adjust_audio_file_paths_in_segment_list(page.segments, copy_operations, multimedia_dir)                     
            n_files_to_copy = len(copy_operations)
            n_files_copied = 0
            post_task_update(callback, f"--- Copying {n_files_to_copy} audio files")
            for old_audio_file_path in copy_operations:
                new_audio_file_path = copy_operations[old_audio_file_path]
                try:
                    copy_file(old_audio_file_path, new_audio_file_path)
                    n_files_copied += 1
                    if n_files_copied % 10 == 0:
                        post_task_update(callback, f'--- Copied {n_files_copied}/{n_files_to_copy} files')
                except Exception as e:
                    post_task_update(callback, f'*** Warning: error when copying audio from {old_audio_file_path} to {new_audio_file_path}')
                    error_message = f'"{str(e)}"\n{traceback.format_exc()}'
                    post_task_update(callback, error_message)
            post_task_update(callback, f"--- Done. {n_files_copied}/{n_files_to_copy} files successfully copied")
                        
        total_pages = len(text.pages)
        post_task_update(callback, f"--- Creating text pages")
        for index, page in enumerate(text.pages):
            rendered_page = self.render_page(page, index + 1, total_pages, text.l2_language, text.l1_language)
            output_file_path = self.output_dir / f'page_{index + 1}.html'
            write_txt_file(rendered_page, output_file_path)
            post_task_update(callback, f"--- Written page {index}")
        post_task_update(callback, f"--- Text pages created")
        
        index = 0
        n_lemmas = len(text.annotations['concordance'].items())
        post_task_update(callback, f"--- Creating {n_lemmas} concordance pages")
        for lemma, lemma_data in text.annotations['concordance'].items():
            index += 1
            rendered_page = self.render_concordance_page(lemma, lemma_data["segments"], text.l2_language)
            lemma = replace_punctuation_with_underscores(lemma)
            output_file_path = self.output_dir / f"concordance_{lemma}.html"
            write_txt_file(rendered_page, output_file_path)
            if index % 10 == 0:
                post_task_update(callback, f"--- Written {index}/{n_lemmas} concordance pages")
        post_task_update(callback, f"--- Written all concordance pages")

        post_task_update(callback, f"--- Creating vocabulary lists")
        # Render alphabetical vocabulary list
        alphabetical_vocabulary_list = sorted(text.annotations['concordance'].items(), key=lambda x: x[0].lower())
        rendered_page = self.render_alphabetical_vocabulary_list(alphabetical_vocabulary_list, text.l2_language)
        output_file_path = self.output_dir / "vocab_list_alphabetical.html"
        write_txt_file(rendered_page, output_file_path)

        # Render frequency vocabulary list
        frequency_vocabulary_list = sorted(text.annotations['concordance'].items(), key=lambda x: x[1]["frequency"], reverse=True)
        rendered_page = self.render_frequency_vocabulary_list(frequency_vocabulary_list, text.l2_language)
        output_file_path = self.output_dir / "vocab_list_frequency.html"
        write_txt_file(rendered_page, output_file_path)
        post_task_update(callback, f"--- Vocabulary lists created")
        
def adjust_audio_file_paths_in_segment_list(segments, copy_operations, multimedia_dir):
    if not segments:
        return
    for segment in segments:
        if 'tts' in segment.annotations and 'file_path' in segment.annotations['tts']:
            old_audio_file_path = segment.annotations['tts']['file_path']
            if old_audio_file_path and old_audio_file_path != 'placeholder.mp3':
                new_audio_file_path = multimedia_dir / basename(old_audio_file_path)
                new_audio_file_path_relative = os.path.join('./multimedia', basename(old_audio_file_path))
                copy_operations[old_audio_file_path] = new_audio_file_path
                segment.annotations['tts']['file_path'] = new_audio_file_path_relative
        for element in segment.content_elements:
            if element.type == "Word" and 'tts' in element.annotations and 'file_path' in element.annotations['tts']:
                old_audio_file_path = element.annotations['tts']['file_path']
                if old_audio_file_path and old_audio_file_path != 'placeholder.mp3':
                    new_audio_file_path = multimedia_dir / basename(old_audio_file_path)
                    new_audio_file_path_relative = os.path.join('./multimedia', basename(old_audio_file_path))
                    copy_operations[old_audio_file_path] = new_audio_file_path
                    element.annotations['tts']['file_path'] = new_audio_file_path_relative
            if element.type == "Image" and 'transformed_segments' in element.content:
                adjust_audio_file_paths_in_segment_list(element.content['transformed_segments'], copy_operations, multimedia_dir)


