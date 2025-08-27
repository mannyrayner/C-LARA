# views_public_api.py
import json, mimetypes, re
from pathlib import Path
from urllib.parse import unquote
from django.http import JsonResponse, Http404, HttpResponse
from django.views.decorators.http import require_GET
from django.views.decorators.cache import never_cache, cache_control
from django.views.decorators.clickjacking import xframe_options_exempt

from .models import Content  # adjust import to your app
from .clara_utils import absolute_file_name, output_dir_for_project_id, file_exists, read_txt_file
from .html_utils import html_to_text

from urllib.parse import urljoin

@require_GET
@never_cache
@cache_control(no_store=True, no_cache=True, must_revalidate=True, max_age=0)
@xframe_options_exempt
def public_content_manifest1(request, content_id: int):
    resp = public_content_manifest(request, content_id)
    # hard no-cache at the HTTP layer
    resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp["Pragma"] = "no-cache"
    resp["Expires"] = "0"
    resp["Access-Control-Allow-Origin"] = "*"
    return resp    
  
def public_content_manifest(request, content_id: int):
    #print('Creating manifest for content: {content_id}')
    content = Content.objects.filter(id=content_id).first()
    if not content:
        raise Http404("Content not found")

    base_url = request.build_absolute_uri('/').rstrip('/')  # e.g. https://c-lara.unisa.edu.au

    project_id = content.project.id

    # Build pages list from compiled output (normal pages).
    base_dir = output_dir_for_project_id(project_id, "normal")
    pages = []
    idx = 1
    while True:
        page_name = f"page_{idx}.html"
        file_path = absolute_file_name(f'{base_dir}/{page_name}')
        #print(f'Looking for page file: {file_path}')
        if not file_exists(file_path):
            #print('Not found')
            #pages.append({ 'page_not_found': file_path })
            break
        #print('Found')
        html = read_txt_file(file_path)
        # naive image extraction; tighten if you know your DOM:
        imgs = re.findall(r'<img[^>]+src="([^"]+)"', html)
        # Images in HTML should already be publicly fetchable
        public_imgs = []
        for src in imgs:
            public_imgs.append(src)
        pages.append({
            "index": idx,
            #"text_html": html,
            "text_plain": html_to_text(html),
            "image_urls": public_imgs,
        })
        idx += 1

    manifest = {
        "schema": "clara.manifest.v1",
        "content_id": content.id,
        "project_id": project_id,
        "title": content.title,
        "l2": content.l2,
        "l1": content.l1,
        "summary": content.summary,
        "difficulty": content.difficulty_level,
        "length_in_words": content.length_in_words,
        "author_masked": (content.project.user.username[:3] + "***") if content.project_id else (content.author[:3] + "***"),
        "voice": content.voice,
        "ai_note": "Programmatic manifest for LLMs/agents.",
        "pages": pages,
        "base_url": base_url,
        "version": 1,
    }

    resp = JsonResponse(manifest, json_dumps_params={"ensure_ascii": False})
    return resp
