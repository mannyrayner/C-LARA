import json, logging
from pathlib import Path
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.conf import settings
from django.contrib import messages

from .language_game_generate_images import game_data_file, kk_image_file, kk_image_file_relative
from .clara_utils import absolute_file_name, read_json_file, file_exists

log = logging.getLogger(__name__)

_GAME_DATA = None            # cache

def get_game_data():
    """
    Load the JSON the first time it’s needed.
    If the file is missing or corrupt, log an error and return {}.
    """
    global _GAME_DATA
    if _GAME_DATA is None:
        try:
            game_json = absolute_file_name(game_data_file)
            if not file_exists(game_json):
                raise FileNotFoundError(game_json)
            _GAME_DATA = read_json_file(game_json)
        except Exception as e:
            log.error("Kok Kaper game data failed to load: %s", e, exc_info=True)
            _GAME_DATA = {}          # graceful fallback
    return _GAME_DATA

#@login_required
def kok_kaper_animal_game(request):
    GAME_DATA = get_game_data()
    if not GAME_DATA:
        messages.error(request,
            "Game data is unavailable – please tell the administrator.")
        return render(request, "clara_app/kok_kaper_game_unavailable.html")
    
    # Restore last choices & gloss‑flag from session
    last = request.session.get("kk_game_last", {})
    def _default(listname):
        return GAME_DATA[listname][0]["id"]

    show_gloss = last.get("show_gloss", True)     # bool

    ctx = {
        "data": GAME_DATA,
        "sel_animal": last.get("animal", _default("animals")),
        "sel_part":   last.get("part",   _default("body_parts")),
        "sel_adj":    last.get("adj",    _default("adjectives")),
        "show_gloss": show_gloss,
        "kk_sentence": "",
        "en_sentence": "",
        "img_path":    ""
    }
    
    if request.method == "POST":
        animal_key   = request.POST["animal"]
        part_key     = request.POST["part"]
        adj_key      = request.POST["adj"]
        show_gloss = bool(request.POST.get("show_gloss"))

        # look up full records
        animal   = next(i for i in GAME_DATA["animals"] if i["id"] == animal_key)
        bodypart = next(i for i in GAME_DATA["body_parts"]   if i["id"] == part_key)
        adj      = next(i for i in GAME_DATA["adjectives"] if i["id"] == adj_key)

        kk_sentence = f"{animal['kk']} la {bodypart['kk']} {adj['kk']} yongkorr"
        en_sentence = f"This is a {animal['en']} with a {adj['en']} {bodypart['en']}"
        img_relative = kk_image_file_relative(animal, adj, bodypart)
        img_absolute = absolute_file_name(kk_image_file(animal, adj, bodypart))

        if not file_exists(img_absolute):
            messages.error(request, f"Image file missing: {img_absolute}.")

        ctx.update({
            "sel_animal": animal_key,
            "sel_part":   part_key,
            "sel_adj":    adj_key,
            "show_gloss": show_gloss,
            "kk_sentence": kk_sentence,
            "en_sentence": en_sentence,
            "img_path":    img_relative
        })

        # Persist selection to session so next GET shows same choices
        request.session["kk_game_last"] = {
            "animal": animal_key,
            "part":   part_key,
            "adj":    adj_key,
            "show_gloss": show_gloss
        }

    return render(request, "clara_app/kok_kaper_game.html", ctx)
