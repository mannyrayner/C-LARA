from .clara_utils import file_exists, absolute_file_name, make_tmp_file, make_tmp_dir, copy_file, copy_directory
from .clara_utils import output_dir_for_project_id, content_zipfile_path_for_project_id
from .clara_utils import make_zipfile, create_start_page_for_self_contained_dir

import os, re, mimetypes
from pathlib import Path
from urllib.parse import unquote

SERVE_PREFIX = "/accounts/projects/serve_project_image/"

_img_tag_src_pat = re.compile(
    r"""(?P<prefix><img\b[^>]*?\bsrc\s*=\s*["'])           # <img ... src="
        (?P<src>[^"']+)                                     # the URL
        (?P<suffix>["'][^>]*>)                              # closing quote + rest of tag
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Matches /accounts/projects/serve_project_image/<project_id>/<file...>
_serve_url_pat = re.compile(
    r"^/accounts/projects/serve_project_image/(?P<project_id>[^/]+)/(?P<file>.+)$"
)

def _rewrite_imgs_and_collect_sources(html_text: str):
    """Find serve_project_image urls, return (new_html, [(project_id, filename)]).
    filename is the tail (not URL-decoded yet)."""
    to_copy = []
    def _sub(m):
        src = m.group("src")
        m2 = _serve_url_pat.match(src)
        if not m2:
            # Not one of ours; leave unchanged
            return m.group(0)
        proj_id = m2.group("project_id")
        rel_file = m2.group("file")  # may include % escapes
        # Rewrite src to 'multimedia/<basename>'
        basename = os.path.basename(rel_file)
        new_src = f"multimedia/{basename}"
        to_copy.append((proj_id, rel_file))
        return f"{m.group('prefix')}{new_src}{m.group('suffix')}"
    new_html = _img_tag_src_pat.sub(_sub, html_text)
    return new_html, to_copy

def build_content_zip(project, text_type: str, callback=None) -> str:
    """
    Create/refresh the zip from the current rendered output.
    Returns the final zip filepath on success; raises exception on failure.
    """
    if callback: post_task_update(callback, f"--- Creating zipfile")
    tmp_zipfile_path = make_tmp_file('project_zip', 'zip')
    tmp_zipfile_dir_path = make_tmp_dir('project_zip_dir')

    out_dir = project.rendered_output_dir(text_type)
    if not os.path.isdir(out_dir):
        raise RuntimeError(f"Rendered output not found: {out_dir}")

    # 1) Copy rendered output into tmp/content and add a start page
    copy_directory(out_dir, f'{tmp_zipfile_dir_path}/content')
    create_start_page_for_self_contained_dir(tmp_zipfile_dir_path)

    # 2) Ensure multimedia dir exists inside content
    content_dir = Path(tmp_zipfile_dir_path) / "content"
    multimedia_dir = content_dir / "multimedia"
    os.makedirs(multimedia_dir, exist_ok=True)

    # 3) Walk all HTML files, rewrite <img> src and collect needed images
    #    We de-duplicate copy ops via a set of basenames we've already handled.
    copied_basenames = set()

    # Optional: aggregate warnings to show once
    missing = []

    for root, _dirs, files in os.walk(content_dir):
        for fname in files:
            if not fname.lower().endswith(".html"):
                continue
            html_path = Path(root) / fname
            try:
                with open(html_path, "r", encoding="utf-8") as f:
                    html = f.read()
            except UnicodeDecodeError:
                # Fallback if a rare non-utf8 page sneaks in
                with open(html_path, "r", encoding="latin-1") as f:
                    html = f.read()

            new_html, to_copy = _rewrite_imgs_and_collect_sources(html)
            if new_html != html:
                # Write back the rewritten HTML
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(new_html)

            # Copy required images for this page
            for proj_id, rel_file in to_copy:
                # Decode any %XX escapes from the URL
                decoded_rel = unquote(rel_file)
                basename = os.path.basename(decoded_rel)

                # Skip if we've already copied this basename
                if basename in copied_basenames:
                    continue

                # Resolve source path on disk using the same logic as serve_project_image
                # image_dir_for_project_id(proj_id) can accept the string proj_id used in the URL
                # If your project ids are numeric internally, make sure image_dir_for_project_id can handle str ids.
                src_path = Path(absolute_file_name(Path(image_dir_for_project_id(proj_id)) / basename))

                if file_exists(src_path):
                    # Copy to content/multimedia/<basename>
                    dst_path = multimedia_dir / basename
                    try:
                        copy_file(src_path, dst_path)
                        copied_basenames.add(basename)
                    except Exception as e:
                        missing.append(f"Failed to copy {src_path} -> {dst_path}: {e}")
                else:
                    missing.append(f"Missing image for zip: project={proj_id} file={basename}")

    if missing and callback:
        for msg in missing:
            post_task_update(callback, f"WARNING: {msg}")

    # 4) Zip it up
    make_zipfile(tmp_zipfile_dir_path, tmp_zipfile_path, callback=callback)
    final_path = project.zip_filepath(text_type)
    os.makedirs(os.path.dirname(final_path), exist_ok=True)
    copy_file(tmp_zipfile_path, final_path)
    if callback: post_task_update(callback, f"--- Zipfile created: {final_path}")
    return final_path
