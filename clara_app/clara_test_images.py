
from .clara_chatgpt4 import call_chat_gpt4_image
from .clara_utils import absolute_file_name

# --------------------------------

def test_imagen(test_id):
    if test_id == 1:
        prompt = 'Create an image of a tabby cat sitting on top of a garden shed.'
        file_name = 'cat_on_shed'
    elif test_id == 2:
        prompt = """Create an image in the style of Klimt of a tabby cat and
a beautiful woman in a diaphanous dress, sitting together on top of a garden shed.
Use a lot of gold leaf.
"""
        file_name = 'cat_on_shed_klimt'
    elif test_id == 3:
        prompt = """Create an image in the style of a stained glass window,
showing this cat (https://c-lara.unisa.edu.au/accounts/accounts/projects/serve_coherent_images_v2_file/480/elements/Whiskers/description_v0/image_v1/image.jpg/)
and this bat (https://c-lara.unisa.edu.au/accounts/accounts/projects/serve_coherent_images_v2_file/480/elements/Batley/description_v0/image_v1/image.jpg/)
playfully leaping between house roofs in a picturesque town.
"""
        file_name = 'cat_and_bat'
    elif test_id == 4:
        prompt = """Create an image in the stained glass window style exemplified by this image:
https://c-lara.unisa.edu.au/accounts/accounts/projects/serve_coherent_images_v2_file/480/style/description_v0/image_v0/image.jpg/,
showing this cat (https://c-lara.unisa.edu.au/accounts/accounts/projects/serve_coherent_images_v2_file/480/elements/Whiskers/description_v0/image_v1/image.jpg/)
and this bat (https://c-lara.unisa.edu.au/accounts/accounts/projects/serve_coherent_images_v2_file/480/elements/Batley/description_v0/image_v1/image.jpg/)
playfully leaping between house roofs in a picturesque town.
"""
        file_name = 'cat_and_bat_2'
    elif test_id == 5:
        prompt = """Create an image 
showing this cat (https://c-lara.unisa.edu.au/accounts/accounts/projects/serve_coherent_images_v2_file/480/elements/Whiskers/description_v0/image_v1/image.jpg/)
and this bat (https://c-lara.unisa.edu.au/accounts/accounts/projects/serve_coherent_images_v2_file/480/elements/Batley/description_v0/image_v1/image.jpg/)
playfully leaping between house roofs at night in a picturesque town. Use a stained glass window style, emphasizing vibrant, translucent colors that capture light
and create a luminous effect. Use a rich color palette, including deep blues, emerald greens, warm ambers, and soft purples, to convey the beauty of the
night sky and town. Ensure bold, black outlines define each segment, mimicking the lead lines in traditional stained glass.
Incorporate intricate details like delicate textures in the cat's fur and the bat's wings. 
"""
        file_name = 'cat_and_bat_3'
    elif test_id == 6:
        prompt = """Create an image 
showing this cat (https://c-lara.unisa.edu.au/accounts/accounts/projects/serve_coherent_images_v2_file/480/elements/Whiskers/description_v0/image_v1/image.jpg/)
and this bat (https://c-lara.unisa.edu.au/accounts/accounts/projects/serve_coherent_images_v2_file/480/elements/Batley/description_v0/image_v1/image.jpg/)
companionably sitting together at night in a garden. Use a stained glass window style, emphasizing vibrant, translucent colors that capture light
and create a luminous effect. Use a rich color palette, including deep blues, emerald greens, warm ambers, and soft purples, to convey the beauty of the
night sky and garden. Ensure bold, black outlines define each segment, mimicking the lead lines in traditional stained glass.
Incorporate intricate details like delicate textures in the cat's fur and the bat's wings. 
"""
        file_name = 'cat_and_bat_garden'
    elif test_id == 7:
        prompt = """Create an image 
showing this cat (https://c-lara.unisa.edu.au/accounts/accounts/projects/serve_coherent_images_v2_file/480/elements/Whiskers/description_v0/image_v1/image.jpg/)
and this bat (https://c-lara.unisa.edu.au/accounts/accounts/projects/serve_coherent_images_v2_file/480/elements/Batley/description_v0/image_v1/image.jpg/)
in a classroom. The bat is standing in front of the chalkboard explaining the dynamics of flight, and the cat, seated at a desk, is watching attentively.
Use a stained glass window style, emphasizing vibrant, translucent colors that capture light
and create a luminous effect. Use a rich color palette, including deep blues, emerald greens, warm ambers, and soft purples, to convey the beauty of the
night sky and garden. Ensure bold, black outlines define each segment, mimicking the lead lines in traditional stained glass.
Incorporate intricate details like delicate textures in the cat's fur and the bat's wings. 
"""
        file_name = 'cat_and_bat_classroom'
    elif test_id == 8:
        prompt = """Create an image 
showing this cat (https://c-lara.unisa.edu.au/accounts/accounts/projects/serve_coherent_images_v2_file/480/elements/Whiskers/description_v0/image_v1/image.jpg/)
and this bat (https://c-lara.unisa.edu.au/accounts/accounts/projects/serve_coherent_images_v2_file/480/elements/Batley/description_v0/image_v1/image.jpg/)
in a classroom. The bat is standing in front of the chalkboard explaining the dynamics of flight, and the cat, seated at a desk, is watching attentively.
Neither the bat nor the cat is clothed.
Use a stained glass window style, emphasizing vibrant, translucent colors that capture light
and create a luminous effect. Use a rich color palette, including deep blues, emerald greens, warm ambers, and soft purples, to convey the beauty of the
night sky and garden. Ensure bold, black outlines define each segment, mimicking the lead lines in traditional stained glass.
Incorporate intricate details like delicate textures in the cat's fur and the bat's wings. 
"""
        file_name = 'cat_and_bat_classroom_v2'
    elif test_id == 9:
        prompt = """Create an image 
showing this cat (https://c-lara.unisa.edu.au/accounts/accounts/projects/serve_coherent_images_v2_file/480/elements/Whiskers/description_v0/image_v1/image.jpg/)
and this bat (https://c-lara.unisa.edu.au/accounts/accounts/projects/serve_coherent_images_v2_file/480/elements/Batley/description_v0/image_v1/image.jpg/)
eating breakfast together. The cat is eating catfood from a bowl on the ground, and the bat has a plate of small insects.
Use a stained glass window style, emphasizing vibrant, translucent colors that capture light
and create a luminous effect. Use a rich color palette, including deep blues, emerald greens, warm ambers, and soft purples, to convey the beauty of the
night sky and garden. Ensure bold, black outlines define each segment, mimicking the lead lines in traditional stained glass.
Incorporate intricate details like delicate textures in the cat's fur and the bat's wings. 
"""
        file_name = 'cat_and_bat_eating'
    elif test_id == 10:
        prompt = """Create an image 
showing this cat (https://c-lara.unisa.edu.au/accounts/accounts/projects/serve_coherent_images_v2_file/480/elements/Whiskers/description_v0/image_v1/image.jpg/)
and this bat (https://c-lara.unisa.edu.au/accounts/accounts/projects/serve_coherent_images_v2_file/480/elements/Batley/description_v0/image_v1/image.jpg/)
attending the World Interspecies Friendship Conference. There are many different species at a fanciful convention hall,
all having a good time together.
Use a stained glass window style, emphasizing vibrant, translucent colors that capture light
and create a luminous effect. Use a rich color palette, including deep blues, emerald greens, warm ambers, and soft purples, to convey the beauty of the
night sky and garden. Ensure bold, black outlines define each segment, mimicking the lead lines in traditional stained glass.
Incorporate intricate details like delicate textures in the cat's fur and the bat's wings. 
"""
        file_name = 'cat_and_bat_conference'
    elif test_id == 11:
        prompt = """Create an image 
showing this cat (https://c-lara.unisa.edu.au/accounts/accounts/projects/serve_coherent_images_v2_file/480/elements/Whiskers/description_v0/image_v1/image.jpg/)
and this bat (https://c-lara.unisa.edu.au/accounts/accounts/projects/serve_coherent_images_v2_file/480/elements/Batley/description_v0/image_v1/image.jpg/)
attending the World Interspecies Friendship Conference. There are many different species at a fanciful convention hall,
all having a good time together. There is a prominent sign saying "World Interspecies Friendship Conference".
Use a stained glass window style, emphasizing vibrant, translucent colors that capture light
and create a luminous effect. Use a rich color palette, including deep blues, emerald greens, warm ambers, and soft purples, to convey the beauty of the
night sky and garden. Ensure bold, black outlines define each segment, mimicking the lead lines in traditional stained glass.
Incorporate intricate details like delicate textures in the cat's fur and the bat's wings. 
"""
        file_name = 'cat_and_bat_conference_v2'
    else:
        raise ValueError('Unknow test_id: {test_id}')

    image_file = absolute_file_name(f'$CLARA/tmp/imagen_3/{file_name}.jpg')

    call_chat_gpt4_image(prompt,
                         image_file,
                         config_info={ 'image_model': 'imagen_3' },
                         callback=None)


# --------------------------------
