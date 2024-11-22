from .clara_utils import (
    read_txt_file,
    write_txt_file,
    read_json_file,
    write_json_to_file,
    make_directory,
    absolute_file_name,
    file_exists,
    directory_exists,
    copy_file,
    get_immediate_subdirectories_in_local_directory,
    post_task_update_async,
    post_task_update,
    )

import asyncio
import os
import json
from pathlib import Path

async def create_alternate_images_json(content_dir, project_dir, callback=None):
    """
    Create an alternate_images.json file in the specified content directory.
    
    Args:
        content_dir (str or Path): The path to the content directory.
        project_dir (str or Path): The path to the top level coherent images v2 directory for the project.
    """
    content_dir = Path(absolute_file_name(content_dir))
    project_dir = Path(absolute_file_name(project_dir))
    alternate_images = []
    id_counter = 1  # Initialize an ID counter for alternate images

    # Check if the content directory exists
    if not directory_exists(content_dir):
        post_task_update_async(callback, f"Content directory {content_dir} does not exist or is not a directory.")
        return

    # Iterate over description directories (e.g., description_v0, description_v1, ...)
    for description_dir in sorted(content_dir.glob('description_v*')):
        if directory_exists(description_dir):
            description_index = description_dir.name.split('_v')[-1]  # Get the version index
            # Paths to expanded description, interpretation, and evaluation
            expanded_description_path = description_dir / 'expanded_description.txt'
            interpretation_path = description_dir / 'interpretation.txt'
            evaluation_path = description_dir / 'evaluation.txt'

            # Iterate over image directories within the description directory
            for image_dir in sorted(description_dir.glob('image_v*')):
                if directory_exists(image_dir):
                    image_index = image_dir.name.split('_v')[-1]  # Get the image version index
                    image_path = image_dir / 'image.jpg'
                    image_interpretation_path = image_dir / 'image_interpretation.txt'
                    image_evaluation_path = image_dir / 'evaluation.txt'  # Sometimes evaluation might be here

                    # Build the relative paths (relative to the content directory)
                    relative_image_path = image_path.relative_to(project_dir)
                    relative_expanded_description_path = expanded_description_path.relative_to(project_dir) if expanded_description_path.exists() else None
                    relative_interpretation_path = interpretation_path.relative_to(project_dir) if interpretation_path.exists() else None
                    relative_evaluation_path = evaluation_path.relative_to(project_dir) if evaluation_path.exists() else None
                    relative_image_interpretation_path = image_interpretation_path.relative_to(project_dir) if image_interpretation_path.exists() else None
                    relative_image_evaluation_path = image_evaluation_path.relative_to(project_dir) if image_evaluation_path.exists() else None

                    # Create the alternate image record
                    alternate_image = {
                        'id': id_counter,
                        'description_index': description_index,
                        'image_index': image_index,
                        'image_path': str(relative_image_path),
                        'expanded_description_path': str(relative_expanded_description_path) if relative_expanded_description_path else None,
                        'image_interpretation_path': str(relative_image_interpretation_path) if relative_image_interpretation_path else None,
                        'image_evaluation_path': str(relative_image_evaluation_path) if relative_image_evaluation_path else None,
                    }

                    alternate_images.append(alternate_image)
                    id_counter += 1

    # Write the alternate_images.json file
    alternate_images_json_path = content_dir / 'alternate_images.json'
    write_json_to_file(alternate_images, alternate_images_json_path)

    post_task_update_async(callback, f"Created alternate_images.json in {content_dir}")
