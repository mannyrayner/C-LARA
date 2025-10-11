from django.contrib import messages

from .clara_audio_repository_orm import AudioRepositoryORM

from .clara_utils import file_exists, absolute_file_name, make_tmp_file, make_tmp_dir, copy_file, copy_directory
from .clara_utils import output_dir_for_project_id, image_dir_for_project_id, content_zipfile_path_for_project_id
from .clara_utils import post_task_update, make_zipfile, create_start_page_for_self_contained_dir

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
##_serve_url_pat = re.compile(
##    r"^/accounts/projects/serve_project_image/(?P<project_id>[^/]+)/(?P<file>.+)$"
##)

_serve_url_pat = re.compile(
    r"""^(?:https?://[^/]+)?                             # optional scheme+host
        /accounts/projects/serve_project_image/
        (?P<project_id>[^/]+)/
        (?P<file>[^?#]+)                                 # stop at ? or #
        (?:[?#].*)?$                                     # allow trailing ?query or #frag
    """,
    re.IGNORECASE | re.VERBOSE,
)

# <source ... src="..."> (used inside <audio> and <video>)
_source_tag_src_pat = re.compile(
    r"""(?P<prefix><source\b[^>]*?\bsrc\s*=\s*["'])
        (?P<src>[^"']+)
        (?P<suffix>["'][^>]*>)
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Also handle <audio src="..."> (some browsers/emitters use it)
_audio_tag_src_pat = re.compile(
    r"""(?P<prefix><audio\b[^>]*?\bsrc\s*=\s*["'])
        (?P<src>[^"']+)
        (?P<suffix>["'][^>]*>)
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Accept optional scheme/host, then /accounts/serve_audio_file/<engine>/<l2>/<voice>/<file>(?…)
_serve_audio_url_pat = re.compile(
    r"""^(?:https?://[^/]+)?
        /accounts/serve_audio_file/
        (?P<engine>[^/]+)/(?P<l2>[^/]+)/(?P<voice>[^/]+)/(?P<file>[^?#]+)
        (?:[?#].*)?$
    """,
    re.IGNORECASE | re.VERBOSE,
)

def _rewrite_imgs_and_collect_sources(request, html_text: str):
    """Find serve_project_image urls, return (new_html, [(project_id, filename)])."""
    to_copy = []

    def _sub(m):
        src = m.group("src")
        m2 = _serve_url_pat.match(src)
        if not m2:
            # Not one of ours; leave unchanged
            return m.group(0)

        proj_id_raw = m2.group("project_id")
        rel_file_raw = m2.group("file")

        # Decode any %XX escapes; strip any trailing ?/# just in case
        rel_file = unquote(rel_file_raw).split("?", 1)[0].split("#", 1)[0]
        basename = os.path.basename(rel_file)

        # Rewrite src to 'multimedia/<basename>'
        new_src = f"multimedia/{basename}"
        to_copy.append((_coerce_project_id(proj_id_raw), basename, src))

        #messages.success(request, f"Rewriting <img>: {src} → {new_src}")

        return f"{m.group('prefix')}{new_src}{m.group('suffix')}"

    new_html = _img_tag_src_pat.sub(_sub, html_text)
    return new_html, to_copy

##def _coerce_project_id(s: str):
##    """Return a project id suitable for image_dir_for_project_id.
##    If s ends with _<digits>, return the numeric tail. Else return s as-is."""
##    tail = re.search(r"_(\d+)$", s)
##    if tail:
##        return int(tail.group(1))
##    return int(s) if s.isdigit() else s

def _coerce_project_id(s: str):
    """Use numeric id *only* if s is purely digits; otherwise keep the slug."""
    return int(s) if s.isdigit() else s

def _rewrite_audio_and_collect_sources(html_text: str):
    """
    Find serve_audio_file URLs in <source src="..."> and <audio src="...">,
    rewrite to multimedia/<basename>, and return (new_html, [copy tuples]).
    copy tuples: (engine, l2, voice, basename, original_src)
    """
    to_copy = []

    def _sub_generic(m):
        src = m.group("src")
        m2 = _serve_audio_url_pat.match(src)
        if not m2:
            return m.group(0)

        engine = m2.group("engine")
        l2     = m2.group("l2")
        voice  = m2.group("voice")
        rel    = unquote(m2.group("file")).split("?", 1)[0].split("#", 1)[0]
        basename = os.path.basename(rel)

        new_src = f"multimedia/{basename}"
        to_copy.append((engine, l2, voice, basename, src))
        return f"{m.group('prefix')}{new_src}{m.group('suffix')}"

    # Apply to <source> tags
    new_html = _source_tag_src_pat.sub(_sub_generic, html_text)
    # And to <audio src="..."> if present
    new_html = _audio_tag_src_pat.sub(_sub_generic, new_html)

    return new_html, to_copy

def build_content_zip_for_text_type(request, project, text_type: str) -> str:
    """
    Create/refresh the zip from the current rendered output.
    Returns the final zip filepath on success; raises exception on failure.
    """
    messages.success(request, f"--- Creating zipfile")
    #if callback: post_task_update(callback, f"--- Creating zipfile")
    tmp_zipfile_path = make_tmp_file('project_zip', 'zip')
    tmp_zipfile_dir_path = make_tmp_dir('project_zip_dir')

    out_dir = project.rendered_output_dir(text_type)
    if not os.path.isdir(out_dir):
        raise RuntimeError(f"Rendered output not found: {out_dir}")

    # 1) Copy rendered output into tmp/content and add a start page
    copy_directory(out_dir, f'{tmp_zipfile_dir_path}/content')
    create_start_page_for_self_contained_dir(tmp_zipfile_dir_path)

    # 2) Ensure multimedia dir exists inside content
    content_dir = absolute_file_name(f'{tmp_zipfile_dir_path}/content')
    multimedia_dir = absolute_file_name(f'{content_dir}/multimedia')
    os.makedirs(multimedia_dir, exist_ok=True)

    # 3) Walk all HTML files, rewrite <img> src and collect needed images
    #    We de-duplicate copy ops via a set of basenames we've already handled.
    copied_basenames = set()

    # Optional: aggregate warnings to show once
    missing = []

    #for root, _dirs, files in os.walk(content_dir):
    files = os.listdir(content_dir)
    #print(f'content_dir: {content_dir}')
    #print(f'files: {files}')
    for fname in files:
        if not fname.lower().endswith(".html") or not fname.lower().startswith("page"):
            continue
        #html_path = Path(root) / fname
        html_path = absolute_file_name(f'{content_dir}/{fname}')
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                html = f.read()
        except UnicodeDecodeError:
            # Fallback if a rare non-utf8 page sneaks in
            with open(html_path, "r", encoding="latin-1") as f:
                html = f.read()

        #new_html, to_copy = _rewrite_imgs_and_collect_sources(request, html)
        new_html_imgs, img_to_copy = _rewrite_imgs_and_collect_sources(request, html)
        new_html, audio_to_copy    = _rewrite_audio_and_collect_sources(new_html_imgs)

        if new_html == html:
            #messages.success(request, f"--- HTML not changed: {fname}")
            continue
        else:
            #messages.success(request, f"--- HTML changed: {fname}")
            # Write back the rewritten HTML
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(new_html)

            # 1) Copy images
            for proj_id, basename, original_src in img_to_copy:
                # Resolve source path on disk using image_dir_for_project_id
                    try:
                        img_dir = Path(image_dir_for_project_id(proj_id))
                    except Exception as e:
                        msg = f"Failed to resolve image dir for project_id={proj_id} (from src={original_src}): {e}"
                        messages.error(request, f"WARNING: {msg}") 
                        continue

                    src_path = absolute_file_name(f'{img_dir}/{basename}')
                    #print(f'src_path = {src_path}')
                    if file_exists(src_path):
                        dst_path = absolute_file_name(f'{multimedia_dir}/{basename}')
                        #print(f'dst_path = {dst_path}')
                        try:
                            copy_file(src_path, dst_path)
                            copied_basenames.add(basename)
                            #messages.success(request, f"Copied image: {src_path} → {dst_path}")
                        except Exception as e:
                            msg = f"Failed to copy {src_path} -> {dst_path}: {e}"
                            messages.error(request, f"WARNING: {msg}")
                    else:
                        msg = f"Missing image for zip (project={proj_id} basename={basename} from {original_src}: {src_path})"
                        messages.error(request, f"WARNING: {msg}")

            # 2) Copy audio files
            if audio_to_copy:
                try:
                    audio_repo = AudioRepositoryORM()  # same class as in serve_audio_file
                    audio_base = Path(audio_repo.base_dir)
                except Exception as e:
                    messages.error(request, f"WARNING: Audio repo unavailable: {e}")
                    audio_base = None

                for engine, l2, voice, basename, original_src in audio_to_copy:
                    if not audio_base:
                        # Can't resolve; we already reported the repo error
                        continue

                    src_path = absolute_file_name(audio_base / engine / l2 / voice / basename)
                    if file_exists(src_path):
                        dst_path = absolute_file_name(f"{multimedia_dir}/{basename}")
                        try:
                            copy_file(src_path, dst_path)
                        except Exception as e:
                            messages.error(request, f"WARNING: Failed to copy audio {src_path} -> {dst_path}: {e}")
                    else:
                        messages.error(request, f"WARNING: Missing audio for zip ({engine}/{l2}/{voice}/{basename} from {original_src}: {src_path})")

    # 3) Zip it up
    make_zipfile(tmp_zipfile_dir_path, tmp_zipfile_path, callback=None)
    final_path = project.zip_filepath(text_type)
    os.makedirs(os.path.dirname(final_path), exist_ok=True)
    copy_file(tmp_zipfile_path, final_path)
    messages.success(request, f"--- Zipfile created: {final_path}")
    return final_path
