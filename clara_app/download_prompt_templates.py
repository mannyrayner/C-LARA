
from .clara_utils import make_local_directory, copy_directory_from_s3

def download_template_dir(dir='full'):

    if dir == 'full':
        s3_dir = '$CLARA/prompt_templates'
        local_dir = '$CLARA/tmp/tmp_templates'
    elif dir == 'french':
        s3_dir = '$CLARA/prompt_templates/french'
        local_dir = '$CLARA/tmp/tmp_templates/french'
    else:
        print(f'*** Unknown value: {dir}')
        return

    make_local_directory(local_dir, parents=True, exist_ok=True)
    copy_directory_from_s3(s3_dir, local_pathname=local_dir)
