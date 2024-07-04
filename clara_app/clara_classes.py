"""
This module defines the following classes to represent a text and its components:

1. ContentElement: Represents a single content element, such as a word or a punctuation mark.
2. Segment: Represents a segment of text, containing a list of ContentElements.
3. Page: Represents a page of text, containing a list of Segments.
4. Text: Represents a full text, containing a list of Pages and metadata about the text, such as L1 and L2 languages.

Each class also includes methods to convert the objects to and from JSON and plain text formats.

It also defines the following classes:

5. APICall, which represents an API call to gpt-4
6. DiffElement, which is used when constructing a smart diff of two texts

7. Various kinds of exceptions
"""
 
import json
import os
import regex

class ContentElement:
    def __init__(self, element_type, content, annotations=None):
        self.type = element_type
        self.content = content
        self.annotations = annotations if annotations else {}

    def to_text(self, annotation_type=None):
        def escape_special_chars(text):
            return text.replace("#", r"\#").replace("@", r"\@").replace("<", r"\<").replace(">", r"\>")

        # If a Word element contains spaces, we need to add @ signs around it for the annotated text to be well-formed
        def put_at_signs_around_text_if_necessary(text, annotation_type):
            if ' ' in text and annotation_type in ( 'segmented', 'mwe', 'translated', 'gloss', 'lemma' ):
                return f'@{text}@'
            else:
                return text
        
        if self.type == "Word":
            escaped_content = escape_special_chars(self.content)
            escaped_content = put_at_signs_around_text_if_necessary(escaped_content, annotation_type)
            annotations = self.annotations
            # For texts tagged with lemma, POS and gloss, we have the special notation Word#Lemma/POS/Gloss#
            if annotation_type == 'lemma_and_gloss':
                gloss = annotations['gloss'] if 'gloss' in annotations else 'NO_GLOSS'
                lemma = annotations['lemma'] if 'lemma' in annotations else 'NO_LEMMA'
                pos = annotations['pos'] if 'pos' in annotations else 'NO_POS'
                escaped_lemma = escape_special_chars(lemma)
                escaped_gloss = escape_special_chars(gloss)
                return f"{escaped_content}#{escaped_lemma}/{pos}/{escaped_gloss}#"
            # For lemma-tagged texts, we have the special notation Word#Lemma/POS# for words with POS tags as well
            elif annotation_type == 'lemma' and 'lemma' in annotations and 'pos' in annotations:
                lemma, pos = ( annotations['lemma'], annotations['pos'] )
                escaped_lemma = escape_special_chars(lemma)
                return f"{escaped_content}#{escaped_lemma}/{pos}#"
            elif annotation_type in ( 'plain', 'segmented', 'mwe', 'translated' ):
                return self.content
            elif annotation_type and annotation_type in annotations:
                escaped_annotation = escape_special_chars(annotations[annotation_type])
                return f"{escaped_content}#{escaped_annotation}#"
            elif annotation_type:
                return f"{escaped_content}#-#"
            else:
                return escaped_content
        else:
            return self.content

    def word_count(self):
        return 1 if self.type == "Word" else 0

    def __repr__(self):
        return f"ContentElement(type={self.type}, content={self.content}, annotations={self.annotations})"
        
class Segment:
    def __init__(self, content_elements, annotations=None):
        self.content_elements = content_elements
        self.annotations = annotations or {}

    def to_text(self, annotation_type=None):
        out_text = ''
        last_type = None
        for element in self.content_elements:
            this_type = element.type
            # When producing 'segmented' or 'phonetic' text, we need to add | markers between continuous Words.
            if annotation_type in ( 'segmented', 'mwe', 'translated', 'phonetic' ) and this_type == 'Word' and last_type == 'Word':
                out_text += '|'
            if annotation_type == 'segmented_for_labelled':
                if element.type in ( 'Word', 'NonWordText' ):
                    # We don't want @ ... @ around multiwords
                    out_text += element.to_text('plain')
            else:
                if element.type in ( 'Word', 'NonWordText', 'Markup' ):
                    out_text += element.to_text(annotation_type)
            last_type = this_type
        if annotation_type == 'mwe':
            annotations = self.annotations
            if 'analysis' in annotations and 'mwes' in annotations:
                analysis_text = annotations['analysis']
                mwes = annotations['mwes']
                #print(f'annotations["mwes"] = {mwes}')
                mwes_text = ','.join([ ' '.join([ word for word in mwe ]) for mwe in mwes ])
                out_text += f"\n_analysis: {analysis_text}\n_MWEs: {mwes_text}"
        if annotation_type == 'translated':
            annotations = self.annotations
            if 'translated' in annotations:
                translated = annotations['translated']
                out_text += f"#{translated}#"
            
        return out_text

    def add_annotation(self, annotation_type, annotation_value):
        self.annotations[annotation_type] = annotation_value

    def word_count(self, phonetic=False):
        if not phonetic:
            return sum([ element.word_count() for element in self.content_elements ])
        # In a phonetic text, a Segment represents a word.
        else:
            return 0 if string_is_only_punctuation_spaces_and_separators(self.to_text()) else 1

    def __repr__(self):
        return f"Segment(content_elements={self.content_elements}, annotations={self.annotations})"

class Page:
    def __init__(self, segments, annotations=None):
        self.segments = segments
        self.annotations = annotations or {}  # This could contain 'img', 'page_number', and 'position'

    def __repr__(self):
        return f"Page(segments={self.segments}, annotations={self.annotations})"

    def content_elements(self):
        elements = []
        for segment in self.segments:
            elements.extend(segment.content_elements)
        return elements

    def to_text(self, annotation_type=None):
        segment_separator = '' if annotation_type == 'plain' else '||'
        segment_texts = segment_separator.join([segment.to_text(annotation_type) for segment in self.segments])
        if annotation_type == 'segmented_for_labelled':
            return segment_texts
        elif self.annotations:
            attributes_str = ' '.join([f"{key}='{value}'" for key, value in self.annotations.items()])
            return f"<page {attributes_str}>{segment_texts}"
        else:
            return f"<page>{segment_texts}"

    def to_translated_text(self):
        segment_separator = ' ' 
        segment_texts = segment_separator.join([segment.annotations['translated'] for segment in self.segments
                                                if 'translated' in segment.annotations])
        return segment_texts

    def word_count(self, phonetic=False):
        return sum([ segment.word_count(phonetic=phonetic) for segment in self.segments ])

    @classmethod
    def from_json(cls, json_str):
        page_dict = json.loads(json_str)
        segments = []
        for segment_dict in page_dict["segments"]:
            content_elements = []
            for element_dict in segment_dict["content_elements"]:
                content_element = ContentElement(
                    element_type=element_dict["type"],
                    content=element_dict["content"],
                    annotations=element_dict["annotations"],
                )
                content_elements.append(content_element)
            segment = Segment(content_elements)
            segments.append(segment)
        return cls(segments)

    def to_json(self):
        page_json = {"segments": []}
        for segment in self.segments:
            segment_json = {"content_elements": []}
            for element in segment.content_elements:
                content_element_json = {
                    "type": element.type,
                    "content": element.content,
                    "annotations": element.annotations,
                }
                segment_json["content_elements"].append(content_element_json)
            page_json["segments"].append(segment_json)
        return json.dumps(page_json)

class Text:
    def __init__(self, pages, l2_language, l1_language, annotations=None, voice=None):
        self.l2_language = l2_language
        self.l1_language = l1_language
        self.pages = pages
        self.annotations = annotations or {}
        self.voice = voice

    def __repr__(self):
        return f"Text(l2_language={self.l2_language}, l1_language={self.l1_language}, pages={self.pages}, annotations={self.annotations})"

    def content_elements(self):
        elements = []
        for page in self.pages:
            elements.extend(page.content_elements())
        return elements

    def to_numbered_page_list(self, translated=False):
        numbered_pages = []
        number = 1
        for page in self.pages:
            if translated:
                page_text = page.to_translated_text()
            else:
                page_text = page.to_text(annotation_type='plain').replace('<page>', '')
            numbered_pages.append({'page': number, 'text': page_text})
            number += 1
        return numbered_pages

    # Returns a list of lists of content elements, one per segment
    def segmented_elements(self):
        segment_list = []
        for page in self.pages:
            for segment in page.segments:
                segment_list.append(segment.content_elements)
        return segment_list

    # Return a list of segments
    def segments(self):
        segment_list = []
        for page in self.pages:
            segment_list += page.segments
        return segment_list
    
    def word_count(self, phonetic=False):
        return sum([ page.word_count(phonetic=phonetic) for page in self.pages ])

    def add_page(self, page):
        self.pages.append(page)

    def remove_page(self, page_object):
        if page_object in self.pages:
            self.pages.remove(page_object)

    def to_text(self, annotation_type=None):
        return "\n".join([page.to_text(annotation_type) for page in self.pages])

    def prettyprint(self):
        print(f"Text Language (L2): {self.l2_language}, Annotation Language (L1): {self.l1_language}\n")
        
        for page_number, page in enumerate(self.pages, start=1):
            print(f"  Page {page_number}: Annotations: {page.annotations}")
            
            for segment_number, segment in enumerate(page.segments, start=1):
                print(f"    Segment {segment_number}: Annotations: {segment.annotations}")

                for element_number, element in enumerate(segment.content_elements, start=1):
                    content_to_print = f"'{element.content}'" if isinstance(element.content, (str)) else f"{element.content}"
                    print(f"      Element {element_number}: Type: '{element.type}', Content: {content_to_print}, Annotations: {element.annotations}")
            
    def to_json(self):
        json_list = [json.loads(page.to_json()) for page in self.pages]
        return json.dumps({
            "l2_language": self.l2_language,
            "l1_language": self.l1_language,
            "pages": json_list
        })

    def find_page_by_image(self, image):
        for page in self.pages:
            if 'img' in page.annotations and page.annotations['img'] == image.image_name:
                return page
        return None

    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        text = cls(l2_language=data["l2_language"], l1_language=data["l1_language"])
        text.pages = [Page.from_json(page_json) for page_json in data["pages"]]
        return text

class Image:
    def __init__(self, image_file_path, thumbnail_file_path, image_name,
                 associated_text, associated_areas,
                 page, position, style_description=None,
                 content_description=None, user_prompt=None,
                 request_type='image-generation',
                 description_variable=None,
                 description_variables=None,  # New field
                 page_object=None):
        self.image_file_path = image_file_path
        self.thumbnail_file_path = thumbnail_file_path
        self.image_name = image_name
        self.associated_text = associated_text
        self.associated_areas = associated_areas
        self.page = page
        self.position = position
        self.style_description = style_description
        self.content_description = content_description
        self.user_prompt = user_prompt
        self.request_type = request_type
        self.description_variable = description_variable
        self.description_variables = description_variables or []  # New field
        self.page_object = page_object

    def to_json(self):
        return {
            'image_file_path': self.image_file_path,
            'thumbnail_file_path': self.thumbnail_file_path,
            'image_name': self.image_name,
            'associated_text': self.associated_text,
            'associated_areas': self.associated_areas,
            'page': self.page,
            'position': self.position,
            'style_description': self.style_description,
            'content_description': self.content_description,
            'request_type': self.request_type,
            'description_variable': self.description_variable,
            'description_variables': self.description_variables,  # New field
            'user_prompt': self.user_prompt
        }

    def merge_page(self, page_object):
        self.page_object = page_object

    def __repr__(self):
        return (f"Image(image_file_path={self.image_file_path}, image_name={self.image_name}, "
                f"style_description={self.style_description}, content_description={self.content_description}, "
                f"user_prompt={self.user_prompt}, description_variables={self.description_variables})")


class ImageDescriptionObject:
    def __init__(self, project_id, description_variable, explanation):
        self.project_id = project_id
        self.description_variable = description_variable
        self.explanation = explanation

    def to_json(self):
        return {
            'description_variable': self.description_variable,
            'explanation': self.explanation
            }

    def __str__(self):
        return f"{self.project_id} | {self.description_variable} | {self.explanation}"

class APICall:
    def __init__(self, prompt, response, cost, duration, timestamp, retries):
        self.prompt = prompt
        self.response = response
        self.cost = cost
        self.duration = duration
        self.timestamp = timestamp
        self.retries = retries

class DiffElement:
    def __init__(self, type, content = '', annotations = {}):
        self.type = type
        self.content = content
        self.annotations = annotations

class InternalCLARAError(Exception):
    def __init__(self, message = 'Internal CLARA error'):
        self.message = message

class InternalisationError(Exception):
    def __init__(self, message = 'Internalisation error'):
        self.message = message

class TemplateError(Exception):
    def __init__(self, message = 'Template error'):
        self.message = message

class ChatGPTError(Exception):
    def __init__(self, message = 'ChatGPT error'):
        self.message = message

class TreeTaggerError(Exception):
    def __init__(self, message = 'TreeTagger error'):
        self.message = message

class ImageGenerationError(Exception):
    def __init__(self, message = 'Image generation error'):
        self.message = message

class ReadingHistoryError(Exception):
    def __init__(self, message = 'ReadingHistory error'):
        self.message = message

# Can't import from these functions from other files because we get a circular import
def basename(pathname):
    return os.path.basename(pathname)

def string_is_only_punctuation_spaces_and_separators(s):
    return all(regex.match(r"[\p{P} \n|]", c) for c in s)
