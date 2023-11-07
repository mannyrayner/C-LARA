
from .clara_main import CLARAProjectInternal

projects = { 'test_english1': { 'id': 'test_english1',
                                'external_id': '10000',
                                'l2': 'english',
                                'l1': 'french',
                                'prompt': 'Write a four line poem about why kittens are cute' }
             }

def run_test(test_id, project_id='test_english1'):

    if not project_id in projects:
        print(f'*** Unknown project_id: {project_id}')
        return
    project_info = projects[project_id]

    if test_id == 'create_project':
        create_project(project_info)
    elif test_id == 'create_text':
        create_text(project_info)
    elif test_id == 'segment':
        segment(project_info)
    elif test_id == 'gloss':
        gloss(project_info)
    elif test_id == 'lemma':
        lemma(project_info)
    elif test_id == 'render':
        render(project_info)
    else:
        print(f'*** Unknown value: {dir}')
        return
                   
def create_project(project_info):
    return CLARAProjectInternal(project_info['id'], project_info['l2'], project_info['l1'])

def create_text(project_info):
    project = create_project(project_info)
    project.create_plain_text(project_info['prompt'])
    return project.load_text_version('plain')
                              
def segment(project_info):
    project = create_project(project_info)
    project.create_segmented_text()
    return project.load_text_version('segmented')

def gloss(project_info):
    project = create_project(project_info)
    project.create_glossed_text()
    return project.load_text_version('gloss')

def lemma(project_info):
    project = create_project(project_info)
    project.create_lemma_tagged_text()
    return project.load_text_version('lemma')

def render(project_info):
    project = create_project(project_info)
    return project.render_text(project_info['external_id'])



