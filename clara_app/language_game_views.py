import json
from pathlib import Path
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.conf import settings
from django.contrib import messages

from .language_game_generate_images import game_data_file, kk_image_file, kk_image_file_relative
from .clara_utils import absolute_file_name, read_json_file, file_exists

# Helper: load the JSON once per process
GAME_DATA = read_json_file(game_data_file)

@login_required
def kok_kaper_animal_game(request):
    # Restore last choices from session, if any, else default to first list item.
    last = request.session.get("kk_game_last", {})
    def _default(listname):
        return GAME_DATA[listname][0]["id"]

    ctx = {
        "data": GAME_DATA,
        "sel_animal": last.get("animal", _default("animals")),
        "sel_part":   last.get("part",   _default("body_parts")),
        "sel_adj":    last.get("adj",    _default("adjectives")),
        "kk_sentence": "",
        "en_sentence": "",
        "img_path":    ""
    }
    
    if request.method == "POST":
        animal_key   = request.POST["animal"]
        part_key     = request.POST["part"]
        adj_key      = request.POST["adj"]

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
            "kk_sentence": kk_sentence,
            "en_sentence": en_sentence,
            "img_path":    img_relative
        })

        # Persist selection to session so next GET shows same choices
        request.session["kk_game_last"] = {
            "animal": animal_key,
            "part":   part_key,
            "adj":    adj_key
        }

    return render(request, "clara_app/kok_kaper_game.html", ctx)
