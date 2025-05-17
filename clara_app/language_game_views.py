import json
from pathlib import Path
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.conf import settings

from .language_game_generate_images import game_data_file, kk_image_file
from .clara_utils import absolute_file_name, read_json_file

# Helper: load the JSON once per process
GAME_DATA = read_json_file(game_data_file)

@login_required
def kok_kaper_animal_game(request):
    ctx = {
        "data": GAME_DATA,   # used to fill the dropdowns
        "kk_sentence": "",
        "en_sentence": "",
        "img_path": ""
    }

    if request.method == "POST":
        animal_key   = request.POST["animal"]
        part_key     = request.POST["part"]
        adj_key      = request.POST["adj"]

        # look up full records
        animal   = next(i for i in GAME_DATA["animals"] if i["kk"] == animal_key)
        bodypart = next(i for i in GAME_DATA["parts"]   if i["kk"] == part_key)
        adj      = next(i for i in GAME_DATA["adjectives"] if i["kk"] == adj_key)

        kk_sentence = f"{animal_key} la {part_key} {adj_key} yongkorr"
        en_sentence = f"This is a {animal['en']} with a {adj['en']} {bodypart['en']}"
        img_static  = absolute_file_name(kk_image_file(animal, adj, bodypart))

        ctx.update({
            "kk_sentence": kk_sentence,
            "en_sentence": en_sentence,
            "img_path":    img_static
        })

    return render(request, "clara_app/kok_kaper_game.html", ctx)
