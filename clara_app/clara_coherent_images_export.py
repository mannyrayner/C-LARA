from .clara_coherent_images_utils import (
    get_all_element_images,
    get_all_relative_page_images,
    project_pathname,
    )

import os
import io
import zipfile

def create_images_zipfile(params):
    """
    Gather all element/page images for the project, zip them up in-memory,
    and return the raw bytes of the ZIP file.
    """
    # 1. Gather images
    all_images = []
    element_images = get_all_element_images(params)
    page_images = get_all_relative_page_images(params)
    
    # Combine them (and remove duplicates if necessary)
    all_images = element_images + page_images
    
    # 2. Create in-memory zip
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for image_path in all_images:
            # Full path on the server
            full_path = project_pathname(params['project_dir'], image_path)
            if os.path.exists(full_path):
                # Store images in the ZIP with a nice path
                # e.g. "elements/<basename>" or "pages/<basename>"
                # If you want the same structure inside the zip, just do:
                arcname = image_path  # or maybe some other cleaned-up path

                zf.write(full_path, arcname)
            else:
                # If you want to log or skip missing images:
                # Or simply ignore them
                pass
    
    # 3. Return bytes
    zip_buffer.seek(0)
    return zip_buffer.getvalue()
