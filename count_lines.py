import glob
import os
import traceback

categories = {
    'Core': {
        'Python': '$CLARA/clara_app/clara_*.py',
        'HTML templates': '$CLARA/templates/*.html',
        'Prompt templates and examples': '$CLARA/prompt_templates/*/*_*_*.*',
        'CSS': '$CLARA/static/*.css',
        'JavaScript': '$CLARA/static/*.js',
        'Config': '$CLARA/clara_app/clara_core/*.ini',
    },
    'Django': {
        'Python': [ '$CLARA/clara_app/constants.py',
                    '$CLARA/clara_app/forms.py',
                    '$CLARA/clara_app/models.py',
                    '$CLARA/clara_app/urls.py',
                    '$CLARA/clara_app/views.py'
                    ],
        'HTML templates': '$CLARA/clara_app/templates/clara_app/*.html',
        'CSS': '$CLARA/clara_app/static/clara_app/*.css',
        'JavaScript': '$CLARA/clara_app/static/clara_app/scripts/*.js',
        'Settings': '$CLARA/clara_project/settings.py',
    },
    'Documentation': {
        'README': '$CLARA/README.txt',
        'FUNCTIONALITY': '$CLARA/FUNCTIONALITY.txt',
        'TODO': '$CLARA/TODO.txt',
    }
}

def count_lines(files_pattern):
    if isinstance(files_pattern, (list, tuple)):
        return sum(count_lines(pattern) for pattern in files_pattern)
    else:
        files_pattern = os.path.expandvars(files_pattern)
        files = glob.glob(files_pattern)
        return sum(count_lines_in_file(file) for file in files)

def count_lines_in_file(file):
    try:
        return sum(1 for line in open(file, encoding='utf-8'))
    except Exception as e:
        print(f'*** Warning: error when processing {file}')
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
        print(error_message)
        return 0
        

def print_table():
    latex_table = "\\begin{tabular}{lr}\n\\toprule\n\\multicolumn{1}{c}{\\textbf{Type}} & \\multicolumn{1}{c}{\\textbf{Lines}} \\\\\n\\midrule"
    total = 0
    for category, types in categories.items():
        latex_table += "\n\\multicolumn{{2}}{{c}}{{\\textit{{{0}}}}} \\\\\n\\midrule".format(category)
        category_total = 0
        for type, pattern in types.items():
            lines = count_lines(pattern)
            latex_table += "\n{0} & {1} \\\\\n".format(type, lines)
            category_total += lines
        latex_table += "Total, {0} & {1} \\\\\n\\midrule".format(category, category_total)
        total += category_total

    latex_table += "\nTotal & {0} \\\\\n\\bottomrule\n\\end{{tabular}}".format(total)

    print(latex_table)

print_table()
