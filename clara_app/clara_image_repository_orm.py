"""
clara_image_repository_orm.py

This module implements an image repository that stores image files and associated metadata. The code is based
on the earlier class AudioRepositoryORM, defined in clara_audio_repository_orm.py.

Classes:
- ImageRepositoryORM: Class for managing the audio repository.

The ImageRepositoryORM class provides methods for adding entries, retrieving entries,
getting the image directory, and storing image files.
"""

from django.core.exceptions import ObjectDoesNotExist

from .models import ImageMetadata, ImageDescription

#from .clara_image_repository import ImageRepository

from .clara_utils import get_config, absolute_file_name, absolute_local_file_name, file_exists, local_file_exists, copy_local_file, basename
from .clara_utils import make_directory, remove_directory, directory_exists, local_directory_exists, make_local_directory, copy_directory
from .clara_utils import list_files_in_directory, post_task_update, generate_unique_file_name
from .clara_utils import adjust_file_path_for_imported_data, generate_thumbnail_name

from .clara_classes import Image, ImageDescriptionObject, InternalCLARAError

from pathlib import Path

from PIL import Image as PILImage

import os
import traceback
#import json

config = get_config()

class ImageRepositoryORM:
    def __init__(self, callback=None):
        self.base_dir = absolute_file_name(config.get('image_repository', 'base_dir_orm'))

        if not directory_exists(self.base_dir):
            make_directory(self.base_dir, parents=True, exist_ok=True)
            post_task_update(callback, f'--- Created base directory for image repository, {self.base_dir}')

    def delete_entries_for_project(self, project_id, callback=None):
        try:
            project_id = str(project_id)
            post_task_update(callback, f'--- Deleting image repository DB entries for {project_id}')
            
            # Delete database entries for the specified project
            entries_deleted = ImageMetadata.objects.filter(project_id=project_id).delete()
            post_task_update(callback, f'--- Deleted {entries_deleted[0]} DB entries for project ID {project_id}')

            # Delete associated image files from the file system
            project_dir = self.get_project_directory(project_id)
            if directory_exists(project_dir):
                remove_directory(project_dir)
                post_task_update(callback, f'--- Image files for project ID {project_id} deleted')
            
            post_task_update(callback, 'Finished deletion process successfully.')

        except Exception as e:
            error_message = f'*** Error when trying to delete image data for project ID {project_id}: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)

    def add_entry(self, project_id, image_name, file_path, associated_text='', associated_areas='',
                  page=1, position='bottom', style_description='', content_description='',
                  user_prompt='', request_type='image-generation', description_variable='',
                  description_variables=[], callback=None):  
        try:
            project_id = str(project_id)
            page = int(page)

            obj, created = ImageMetadata.objects.update_or_create(
                project_id=project_id, 
                image_name=image_name,
                defaults={
                    'file_path': file_path,
                    'associated_text': associated_text,
                    'associated_areas': associated_areas,
                    'page': page,
                    'position': position,
                    'style_description': style_description,
                    'content_description': content_description,
                    'request_type': request_type,
                    'description_variable': description_variable,
                    'description_variables': description_variables,  
                    'user_prompt': user_prompt
                }
            )

            if created:
                post_task_update(callback, f'--- Created new image entry for project_id={project_id} and image_name={image_name}')
            else:
                post_task_update(callback, f'--- Updated existing image entry for project_id={project_id} and image_name={image_name}')

        except Exception as e:
            error_message = f'*** Error when adding/updating image entry "{project_id}/{image_name}" in the database: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Image database inconsistency')

    def store_associated_areas(self, project_id, image_name, associated_areas, callback=None):
        try:
            # Ensure project_id is a string
            project_id = str(project_id)

            # Try to update the existing entry with the new associated_areas
            updated_count = ImageMetadata.objects.filter(project_id=project_id, image_name=image_name).update(associated_areas=associated_areas)

            if updated_count > 0:
                post_task_update(callback, f'--- Updated associated_areas for project_id={project_id} and image_name={image_name}')
            else:
                post_task_update(callback, f'*** No matching entry found to update associated_areas for "{project_id}/{image_name}"')
            
        except Exception as e:
            error_message = f'*** Error when updating associated_areas for "{project_id}/{image_name}": "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Image database inconsistency')

##    def store_understanding_result(self, project_id, description_variable, result, callback=None):
##        try:
##            post_task_update(callback, f"--- Storing understanding result in database for {description_variable}")
##            image_metadata = ImageMetadata.objects.get(project_id=project_id, description_variable=description_variable)
##            image_metadata.content_description = result
##            image_metadata.save()
##            post_task_update(callback, f"--- Understanding result stored in database")
##        except ImageMetadata.DoesNotExist:
##            post_task_update(callback, f"*** Error: ImageMetadata not found for {description_variable}")
##        except Exception as e:
##            post_task_update(callback, f"*** Error storing understanding result in database for {description_variable}")
##            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
##            post_task_update(callback, error_message)

    def store_understanding_result(self, project_id, description_variable, result,
                                   image_name=None, page=None, position=None, user_prompt=None, callback=None):
        try:
            print(f"store_understanding_result({project_id}, {description_variable}, {result}, image_name={image_name}, page={page}, position={position}, user_prompt={user_prompt})")
            # Try to update the existing entry with the new associated_areas
            updated_count = ImageMetadata.objects.filter(project_id=project_id, description_variable=description_variable).update(content_description=result)

            if updated_count > 0:
                post_task_update(callback, f'--- Updated value for project_id={project_id} and description_variable={description_variable}')
            elif image_name and page and position:
                # If it's a new description variable that hasn't previously been entered, we need to fill all the fields
                file_path = ''
                self.add_entry(project_id, image_name, file_path,
                               page=page, position=position, request_type='image-understanding',
                               user_prompt=user_prompt,
                               description_variable=description_variable, content_description=result,
                               callback=None)
                post_task_update(callback, f'--- Added new description for project_id={project_id} and description_variable={description_variable}, page={page}')
            else:
                post_task_update(callback, f'*** No entry found to update result for project_id={project_id}, description_variable={description_variable}, image_name={image_name}')
        except Exception as e:
            post_task_update(callback, f"*** Error storing understanding result in database for description_variable={description_variable}, image_name={image_name}")
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)

    def get_understanding_result(self, project_id, description_variable, callback=None):
        try:
            post_task_update(callback, f"--- Retrieving understanding result from database for {description_variable}")
            image_metadata = ImageMetadata.objects.get(project_id=project_id, description_variable=description_variable)
            post_task_update(callback, f"--- Understanding result retrieved from database")
            return image_metadata.content_description
        except ImageMetadata.DoesNotExist:
            return None
        except Exception as e:
            post_task_update(callback, f"*** Error retrieving understanding result from database for {description_variable}")
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            return None

    def get_entry(self, project_id, image_name, callback=None):
        try:
            project_id = str(project_id)
            
            entry = ImageMetadata.objects.get(project_id=project_id, image_name=image_name)
            thumbnail = generate_thumbnail_name(entry.file_path)
            
            image = Image(
                entry.file_path,
                thumbnail,
                entry.image_name,
                entry.associated_text,
                entry.associated_areas,
                entry.page,
                entry.position,
                style_description=entry.style_description,
                content_description=entry.content_description,
                request_type=entry.request_type,
                description_variable=entry.description_variable,
                description_variables=entry.description_variables,
                user_prompt=entry.user_prompt
            )

            return image

        except ObjectDoesNotExist:
            post_task_update(callback, f'*** No entry found for "{image_name}" in Image database.')
            return None
        except Exception as e:
            error_message = f'*** Error when looking for "{image_name}" in Image database: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Image database inconsistency')

    def get_generated_entry_by_position(self, project_id, page, position, callback=None):
        try:
            project_id = str(project_id)
            
            entry = ImageMetadata.objects.get(project_id=project_id,
                                              page=page,
                                              position=position,
                                              request_type='image-generation')
            thumbnail = generate_thumbnail_name(entry.file_path)
            
            image = Image(
                entry.file_path,
                thumbnail,
                entry.image_name,
                entry.associated_text,
                entry.associated_areas,
                entry.page,
                entry.position,
                style_description=entry.style_description,
                content_description=entry.content_description,
                request_type=entry.request_type,
                description_variable=entry.description_variable,
                description_variables=entry.description_variables, 
                user_prompt=entry.user_prompt
            )

            return image
                    
        except ObjectDoesNotExist:
            post_task_update(callback, f'*** No entry found for page={page}, position={position}, request_type=image-generation in Image database.')
            return None
        except Exception as e:
            error_message = f'*** Error when looking for page={page}, position={position}, request_type=image-generation in Image database: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Image database inconsistency')

    def get_all_entries(self, project_id, callback=None):
        try:
            project_id = str(project_id)
            post_task_update(callback, f'--- Retrieving all images for project {project_id}')

            # Fetch all entries for the given project_id from the ORM
            entries = ImageMetadata.objects.filter(project_id=project_id)

            images = []
            for entry in entries:
                # Generate thumbnail name
                thumbnail = generate_thumbnail_name(entry.file_path)
                
                # Construct an Image object for each entry
                image = Image(entry.file_path,
                              thumbnail,
                              entry.image_name,
                              entry.associated_text,
                              entry.associated_areas,
                              entry.page,
                              entry.position,
                              style_description=entry.style_description,
                              content_description=entry.content_description,
                              request_type=entry.request_type,
                              description_variable=entry.description_variable,
                              description_variables=entry.description_variables,
                              user_prompt=entry.user_prompt)
                images.append(image)

            post_task_update(callback, f'--- Retrieved {len(images)} images for project {project_id}')
            return images
                
        except Exception as e:
            error_message = f'*** Error when retrieving images for project {project_id}: {str(e)}\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Image database inconsistency')

    def store_image(self, project_id, source_file, keep_file_name=True, callback=None):
        try:
            project_id = str(project_id)
            project_dir = self.get_project_directory(project_id)
            make_directory(project_dir, parents=True, exist_ok=True)

            # Use UUID for generating a unique file name if not keeping the original file name
            file_name = basename(source_file) if keep_file_name else generate_unique_file_name(f'project_{project_id}', extension='png')
            destination_path = str(Path(project_dir) / file_name)
            copy_local_file(source_file, destination_path)

            # Generate and store thumbnail
            try:
                original_image = PILImage.open(source_file)
                thumbnail_size = (100, 100)  # Example size, adjust as needed
                original_image.thumbnail(thumbnail_size)
                thumbnail_destination_path = generate_thumbnail_name(destination_path)
                original_image.save(thumbnail_destination_path)

                post_task_update(callback, f'--- Image and thumbnail stored at {destination_path} and {thumbnail_destination_path}')
            except Exception as e:
                error_message = f'*** Error when generating thumbnail for {file_name}: {str(e)}\n{traceback.format_exc()}'
                post_task_update(callback, error_message)
                raise InternalCLARAError(message='Error generating thumbnail')

            return destination_path
        except Exception as e:
            error_message = f'*** Error when storing image "{source_file}" in image repository: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Image repository error')

    def remove_all_entries_except_style_images(self, project_id, callback=None):
        try:
            images = self.get_all_entries(project_id, callback=callback)
            for image in images:
                if image.page != 0:
                    self.remove_entry(project_id, image.image_name, callback=callback)
        except Exception as e:
            error_message = f'*** Error when deleting all images for project "{project_id}" in image repository: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Image repository error')

    def remove_entry(self, project_id, image_name, callback=None):
        try:
            project_id = str(project_id)
            post_task_update(callback, f'--- Attempting to remove entry for image {image_name} in project {project_id}')
            
            # Attempt to fetch and delete the specified entry
            entry = ImageMetadata.objects.get(project_id=project_id, image_name=image_name)
            entry.delete()
            
            post_task_update(callback, f'--- Entry for image {image_name} in project {project_id} removed successfully')
        except ObjectDoesNotExist:
            post_task_update(callback, f'*** No entry found for image {image_name} in project {project_id}')
        except Exception as e:
            error_message = f'*** Error when removing entry for image {image_name} in project {project_id}: {str(e)}\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Image database inconsistency')

    def get_annotated_image_text(self, project_id, callback=None):
        try:
            project_id = str(project_id)
            post_task_update(callback, f'--- Retrieving annotated image text for project {project_id}')
            
            entries = ImageMetadata.objects.filter(project_id=project_id).order_by('page', 'position')
            
            annotated_image_text = ""
            for entry in entries:
                image_name = entry.image_name
                associated_text = entry.associated_text
                page = entry.page
                position = entry.position
                annotated_image_text += f"<page img='{image_name}' page='{page}' position='{position}'>\n{associated_text}\n"

            post_task_update(callback, f'--- Annotated image text for project {project_id} generated')
            return annotated_image_text

        except ObjectDoesNotExist:
            return "" # Return an empty string if no entries found
        except Exception as e:
            error_message = f'*** Error when retrieving annotated image text for project {project_id}: {str(e)}\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Image database inconsistency')

    # Get a single image description
    def get_description(self, project_id, description_variable, formatting='objects', callback=None):
        try:
            project_id = str(project_id)
            description_variable = str(description_variable)
            
            entry = ImageDescription.objects.get(project_id=project_id, description_variable=description_variable)
            if formatting == 'plain_lists':
                description = { 'description_variable': entry.description_variable,
                                'explanation': entry.explanation }
            else:
                description = ImageDescriptionObject(
                    entry.project_id,
                    entry.description_variable,
                    entry.explanation
                )

            return description

        except ObjectDoesNotExist:
            post_task_update(callback, f'*** No description found for "{description_variable}" in project {project_id}.')
            return None
        except Exception as e:
            error_message = f'*** Error when looking for "{description_variable}" in project {project_id}: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Image description database inconsistency')

    # Get all descriptions for a project
    def get_all_descriptions(self, project_id, formatting='objects', callback=None):
        try:
            project_id = str(project_id)
            post_task_update(callback, f'--- Retrieving all descriptions for project {project_id}')

            entries = ImageDescription.objects.filter(project_id=project_id)
            if formatting == 'plain_lists':
                descriptions = [ { 'description_variable': entry.description_variable,
                                   'explanation': entry.explanation }
                                 for entry in entries ]
            else:
                descriptions = [ ImageDescriptionObject(entry.project_id, entry.description_variable, entry.explanation)
                                 for entry in entries ]

            post_task_update(callback, f'--- Retrieved {len(descriptions)} descriptions for project {project_id}')
            return descriptions

        except Exception as e:
            error_message = f'*** Error when retrieving descriptions for project {project_id}: {str(e)}\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Image description database inconsistency')

    # Add or update an image description
    def add_description(self, project_id, description_variable, explanation, callback=None):
        try:
            project_id = str(project_id)
            description_variable = str(description_variable)

            obj, created = ImageDescription.objects.update_or_create(
                project_id=project_id, 
                description_variable=description_variable,
                defaults={'explanation': explanation}
            )

            if created:
                post_task_update(callback, f'--- Created new description for project_id={project_id} and description_variable={description_variable}')
            else:
                post_task_update(callback, f'--- Updated existing description for project_id={project_id} and description_variable={description_variable}')

        except Exception as e:
            error_message = f'*** Error when adding/updating description "{project_id}/{description_variable}" in the database: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Image description database inconsistency')

    # Remove a single description
    def remove_description(self, project_id, description_variable, callback=None):
        try:
            project_id = str(project_id)
            description_variable = str(description_variable)
            post_task_update(callback, f'--- Attempting to remove description {description_variable} in project {project_id}')
            
            entry = ImageDescription.objects.get(project_id=project_id, description_variable=description_variable)
            entry.delete()
            
            post_task_update(callback, f'--- Description {description_variable} in project {project_id} removed successfully')
        except ObjectDoesNotExist:
            post_task_update(callback, f'*** No description found for {description_variable} in project {project_id}')
        except Exception as e:
            error_message = f'*** Error when removing description {description_variable} in project {project_id}: {str(e)}\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Image description database inconsistency')

    # Remove all descriptions for a project
    def delete_descriptions_for_project(self, project_id, callback=None):
        try:
            project_id = str(project_id)
            post_task_update(callback, f'--- Deleting image description DB entries for {project_id}')
            
            entries_deleted = ImageDescription.objects.filter(project_id=project_id).delete()
            post_task_update(callback, f'--- Deleted {entries_deleted[0]} DB entries for project ID {project_id}')

            post_task_update(callback, 'Finished deletion process successfully.')

        except Exception as e:
            error_message = f'*** Error when trying to delete image description data for project ID {project_id}: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)

    def get_project_directory(self, project_id):
        # Returns the directory path where images for a specific project are stored
        return absolute_file_name(Path(self.base_dir) / str(project_id))


