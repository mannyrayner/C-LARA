from .clara_coherent_images_utils import (
    get_all_element_images,
    get_all_relative_page_images,
    project_pathname,
    )

from .clara_utils import (
    absolute_file_name,
    )

import os
import io
import zipfile
from PIL import Image

def create_images_zipfile(params):
    """
    Gather all element/page images for the project, add a watermark,
    zip them up in-memory, and return the raw bytes of the ZIP file.
    """
    # 1. Gather images
    element_images = get_all_element_images(params)
    page_images = get_all_relative_page_images(params)
    all_images = element_images + page_images  # Combine them (and remove duplicates if necessary)

    # 2. Load the watermark image in memory
    #    This example assumes the watermark is a normal JPG or PNG at $CLARA/logo/logo.jpg.
    #    If you need an absolute path, adapt accordingly:
    watermark_path = absolute_file_name('$CLARA/logo/logo.jpg')
    watermark = Image.open(watermark_path).convert("RGBA")

    # 3. Create in-memory ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for image_relpath in all_images:
            full_path = project_pathname(params['project_dir'], image_relpath)
            if not os.path.exists(full_path):
                continue  # skip missing

            # Load the image
            try:
                with Image.open(full_path) as base_img:
                    base_img = base_img.convert("RGBA")  # So we can handle alpha if needed
                    # Compose watermark onto the base image
                    watermarked_img = add_watermark(base_img, watermark)

                    # Write the watermarked image as JPG (or PNG) into an in-memory buffer
                    img_buffer = io.BytesIO()
                    # If you prefer PNG, use "PNG". For JPEG, use "JPEG".
                    watermarked_img.convert("RGB").save(img_buffer, format="JPEG", quality=90)
                    img_buffer.seek(0)

                    # Write it to the ZIP with the same relative path
                    arcname = image_relpath  # "pages/pageX/image.jpg", etc.
                    zf.writestr(arcname, img_buffer.read())
            except Exception:
                # If there's any issue reading or processing the image,
                # you might skip or log it. We'll just skip here.
                pass

    # 4. Return ZIP bytes
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def add_watermark(base_img, watermark):
    """
    Overlay 'watermark' onto 'base_img' at a chosen position.
    Returns a new RGBA image.
    """
    # You can resize the watermark if you want. For example:
    # watermark = watermark.resize((100, 100), Image.ANTIALIAS)

    # We'll place it near the bottom-right corner with some padding
    base_w, base_h = base_img.size
    wm_w, wm_h = watermark.size
    margin = 10
    x_pos = base_w - wm_w - margin
    y_pos = base_h - wm_h - margin

    # Create a copy so as not to modify the original in memory
    watermarked = base_img.copy()
    # Paste the watermark image (with alpha) onto the base image
    watermarked.alpha_composite(watermark, dest=(x_pos, y_pos))
    return watermarked
