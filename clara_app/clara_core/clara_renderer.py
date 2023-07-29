"""
clara_renderer.py

This module implements a renderer for the CLARA application that generates static HTML pages for Text objects and their annotations.

Classes:
- StaticHTMLRenderer: A renderer that creates static HTML files for a given Text object and its annotations.

The StaticHTMLRenderer class provides methods for rendering pages, concordance pages, and vocabulary lists.
The renderer also supports self-contained rendering, which means that all multimedia assets are copied to the output directory.
"""

from .clara_utils import _s3_storage, absolute_file_name
from .clara_utils import remove_directory, make_directory, copy_directory, copy_directory_to_s3, directory_exists
from .clara_utils import copy_file, basename, write_txt_file, output_dir_for_project_id
from .clara_utils import get_config, is_rtl_language, replace_punctuation_with_underscores

from pathlib import Path
import os
from jinja2 import Environment, FileSystemLoader
import shutil

config = get_config()

class StaticHTMLRenderer:
    def __init__(self, project_id):
        self.template_env = Environment(loader=FileSystemLoader(absolute_file_name(config.get('renderer', 'template_dir'))))
        self.output_dir = Path(output_dir_for_project_id(project_id))
        
        # Remove the existing output_dir if it exists
        if directory_exists(self.output_dir):
            remove_directory(self.output_dir)
        
        # Create the new output_dir
        make_directory(self.output_dir)

        # Copy the 'static' folder to the output_dir
        static_src = absolute_file_name('$CLARA/static')
        static_dst = self.output_dir / 'static'
        if _s3_storage:
            copy_directory_to_s3(static_src, s3_pathname=static_dst)
        else:
            copy_directory(static_src, static_dst)

    def render_page(self, page, page_number, total_pages, l2_language, l1_language):
        is_rtl = is_rtl_language(l2_language)
        template = self.template_env.get_template('clara_page.html')
        rendered_page = template.render(page=page,
                                        total_pages=total_pages,
                                        l2_language=l2_language,
                                        is_rtl=is_rtl,
                                        l1_language=l1_language,
                                        page_number=page_number)
        return rendered_page

    def render_concordance_page(self, lemma, concordance_segments, l2_language):
        template = self.template_env.get_template('concordance_page.html')
        rendered_page = template.render(lemma=lemma,
                                        concordance_segments=concordance_segments,
                                        l2_language=l2_language)
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

    def render_text(self, text, self_contained=False):
        # Create multimedia directory if self-contained is True
        if self_contained:
            multimedia_dir = self.output_dir / 'multimedia'
            make_directory(multimedia_dir, exist_ok=True)

            # Traverse the Text object, copying each multimedia file
            # referenced to the new multimedia directory and update the reference
            for page in text.pages:
                for segment in page.segments:
                    if 'tts' in segment.annotations and 'file_path' in segment.annotations['tts']:
                        old_audio_file_path = segment.annotations['tts']['file_path']
                        try:
                            new_audio_file_path = multimedia_dir / basename(old_audio_file_path)
                            new_audio_file_path_relative = os.path.join('./multimedia', basename(old_audio_file_path))
                            copy_file(old_audio_file_path, new_audio_file_path)
                            segment.annotations['tts']['file_path'] = new_audio_file_path_relative
                        except:
                            print(f'*** Warning: could not copy audio for {old_audio_file_path}')
                    for element in segment.content_elements:
                        if element.type == "Word" and 'tts' in element.annotations and 'file_path' in element.annotations['tts']:
                            old_audio_file_path = element.annotations['tts']['file_path']
                            try:
                                new_audio_file_path = multimedia_dir / basename(old_audio_file_path)
                                new_audio_file_path_relative = os.path.join('./multimedia', basename(old_audio_file_path))
                                copy_file(old_audio_file_path, new_audio_file_path)
                                element.annotations['tts']['file_path'] = new_audio_file_path_relative
                            except:
                                print(f'*** Warning: could not copy audio for {old_audio_file_path}')
                        
        total_pages = len(text.pages)
        for index, page in enumerate(text.pages):
            rendered_page = self.render_page(page, index + 1, total_pages, text.l2_language, text.l1_language)
            output_file_path = self.output_dir / f'page_{index + 1}.html'
            write_txt_file(rendered_page, output_file_path)
                
        for lemma, lemma_data in text.annotations['concordance'].items():
            rendered_page = self.render_concordance_page(lemma, lemma_data["segments"], text.l2_language)
            lemma = replace_punctuation_with_underscores(lemma)
            output_file_path = self.output_dir / f"concordance_{lemma}.html"
            write_txt_file(rendered_page, output_file_path)

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
        



