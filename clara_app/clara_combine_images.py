from PIL import Image

def combine_images_pairwise_wanakat_kaori():
    input_folder = 'C:/cygwin64/home/sf/callector-lara-svn/trunk/Content/l_enfant_kaori/images'
    output_folder = 'C:/cygwin64//home/sf/callector-lara-svn/trunk/Content/l_enfant_kaori/double_page_images'
    image_paths = [
                    #'01_front_cover.jpg',
                    #'02_inside_front_cover.jpg',
                    #'03_coelho.jpg',
                    '04_credits.jpg',
                    '05_title_page.jpg',
                    
                    '06_son_mari_a_disparu_gauche.jpg',
                    '07_son_mari_a_disparu_droite.jpg',
                    '08_arrête_toi.jpg',
                    '09_tiens.jpg',
                    '10_même_si_tu_ne_vois.jpg',
                    '11_approche_du_trou.jpg',
                    '12_cest_bizarre_gauche.jpg',
                    '13_cest_bizarre_droite.jpg',
                    '14_tabou.jpg',
                    '15_la_gardienne.jpg',
                    '16_mon_mari_gauche.jpg',
                    '17_mon_mari_droite.jpg',
                    '18_aie_pitié.jpg',
                    '19_je_le_sais.jpg',
                    '20_jusqu_à_quand.jpg',
                    '21_tu_es_enceinte.jpg',
                    '22_impossible.jpg',
                    '23_d_accord.jpg',
                    '24_il_me_manque_gauche.jpg',
                    '25_il_me_manque_droite.jpg',
                    '26_mon_enfant_gauche.jpg',
                    '27_mon_enfant_droite.jpg',
                    '28_une_fine_pluie.jpg',
                    '29_je_te_pardonne.jpg',

                    #'30_les_mots.jpg',
                    #'31_inside_back_cover.jpg',
                    #'32_back_cover.jpg'
                    ]
    
    combine_images_pairwise(image_paths, input_folder, output_folder)

def combine_images_pairwise(image_paths, input_folder, output_folder):
    """
    Combine images in pairs and save the combined images to the output folder.
    Each new image will have the two original images side by side.

    Parameters:
    - image_paths: A list of paths to the images that need to be combined.
                   Images are combined in pairs according to their order in this list.
    - output_folder: The path to the folder where the combined images will be saved.

    Returns:
    - A list of paths to the combined images.
    """

    combined_image_paths = []

    # Process images in pairs
    for i in range(0, len(image_paths), 2):
        if i + 1 < len(image_paths):  # Ensure there is a pair
            # Open the images
            print(f'--- Combining {image_paths[i]} and {image_paths[i + 1]}')
                  
            image1 = Image.open(f"{input_folder}/{image_paths[i]}")
            image2 = Image.open(f"{input_folder}/{image_paths[i + 1]}")

            # Calculate dimensions for the combined image
            total_width = image1.width + image2.width
            max_height = max(image1.height, image2.height)

            # Create a new blank image with the appropriate dimensions
            combined_image = Image.new('RGB', (total_width, max_height))

            # Paste the original images into the combined image
            combined_image.paste(image1, (0, 0))
            combined_image.paste(image2, (image1.width, 0))

            # Generate a path for the combined image
            output_path = f"{output_folder}/combined_{i//2 + 1}.jpg"
            combined_image.save(output_path)
            combined_image_paths.append(output_path)

    return combined_image_paths

# Example usage (this code won't run here due to the absence of actual image files and directories)
# image_paths = ["path/to/image1.jpg", "path/to/image2.jpg", "path/to/image3.jpg", "path/to/image4.jpg"]
# output_folder = "path/to/output"
# combined_image_paths = combine_images_pairwise(image_paths, output_folder)
# print("Combined images saved to:", combined_image_paths)

