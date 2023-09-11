
1. Purpose of C-LARA

C-LARA is a complete reimplementation of the Learning And Reading Assistant
(LARA; https://www.unige.ch/callector/lara/) with ChatGPT-4 in the centre.
As with the original LARA, it provides a web platform where users can create and read
multimedia learner texts in many languages. In the original LARA, much of the work
needed to produce a multimedia text had to be performed manually. However, in C-LARA,
all the steps, including writing the text, can be carried out by ChatGPT-4, though
the result will typically contain a few minor errors. If a native speaker of the language
in question is available, the errors are usually very quick and easy to correct.
A simple editing interface is included.

In order to perform many of the key C-LARA operations, you need an OpenAI license key
enabled for gpt-4 API access. Unfortunately, the generally available gpt-3.5-turbo
license does not provide adequate performance for the kind of multilingual processing
required here.

2. Installation

C-LARA can currently be run in two configurations: local machine, or Heroku.

The database can be either SQLite or Postgres.

Files can either be kept in the local filesystem, or on S3.

For Heroku, Postgres + S3 is necessary. The following sections refer primarily to
installing on a local machine. Section (2e) describes installing on Heroku.

2a. Python and packages

C-LARA is implemented in Python using the Django framework, with Django-Q for asynchrony.
You first need to install Python 3.11. Make sure that 'python3' points to this version.

IMPORTANT: EARLIER VERSIONS OF PYTHON 3 MAY NOT WORK. WE KNOW THAT 3.9 IS INSUFFICIENT.

Install the Python packages listed in the file requirements.txt (sister to this file).

2b. Downloading the code and other resources

Download the code from GitHub at https://github.com/mannyrayner/C-LARA.

2c. TreeTagger

If you want to be able to use TreeTagger to do conventional tagging, follow the
instructions at https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/ to
install it, together with parameter files for the languages you are interested in.
This is quick and easy.

2d. Environment variables

The following environment variables are used:

OPENAI_API_KEY. Value of your OpenAI license key.
Unfortunately, you need a license enabled for the gpt-4 language model.

CLARA_ENVIRONMENT. Set to 'local' for local machine or 'heroku' for Heroku.

CLARA. Points to the root directory of the material downloaded from GitHub.
On my machine, it is set to C:\cygwin64\home\github\c-lara

FILE_STORAGE_TYPE. Set to 'local' for local file or 'S3' for AWS S3 files.

AWS_ACCESS_KEY, AWS_REGION, AWS_S3_REGION_NAME, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME.
Set these to appropriate values if you are using S3 files. You need to have set up
an S3 bucket for them to point to.

DB_TYPE. Set to 'postgres' or 'sqlite' depending on which database you use.

DJANGO_DEBUG. Set to 'True' to enable Django debugging.

GOOGLE_CREDENTIALS_JSON. Set to a suitable JSON value if you are going to use Google TTS.
You need have set up a suitable Google account for it to point to.

TREETAGGER. If you are using TreeTagger, set to the root TreeTagger directory.

TMPDIR. On Heroku, set to '/tmp'.

2e. Installing on Heroku

Specify a Python 3 project.

Set the environment variables as described in (2d).

Link to the GitHub repository.

There are two processes, as specified in Procfile (sister to this file).
These are currently allocated the following resources:

gunicorn clara_project.wsgi:application
Standard 1X dynos.

python manage.py qcluster
Standard 2X dynos.

The database is Heroku Postgres.
This is currently allocation to the Standard 0 tier.

3. Running in development mode on a local machine

Make sure that packages are installed and environment variables set as in (2) above. 

You should then be able to start the server in development mode (i.e. running the system
on your local machine), by opening two command prompts and doing the following:

First command prompt (Q-cluster for Django-Q asynchrony):

cd $CLARA
python3 manage.py qcluster

Second command prompt (server):

cd $CLARA
python3 manage.py runserver

Note that the server may not immediately connect to the Q-cluster.

C-LARA should then be accessible at http://localhost:8000/accounts/login/

If this does not work, please send a full trace to Manny.Rayner@unisa.edu.au.
We are still debugging the installation process and I will be responsive!

4. Organisation of material

Assuming the environment variable settings described in (2c) above, we will refer to
the root C-LARA directory as $CLARA.

The code is conceptually divided into two parts: the core Python code, and the Django layer.
Because of the way Django organises its directory structure, it is however technically
cleanest to make the core Python code a subdirectory of the Django directory.
The Django layer code is thus in the directory $CLARA/clara_app, and the core Python code
is in the directory $CLARA/clara_app/clara_core. Other directories are as described below.

4a. Core Python code

The top-level file in $CLARA/clara_app/clara_core is clara_main.py. This implements the
class CLARAProjectInternal, which performs all the internal operations associated
with CLARA projects. There is documentation in clara_main.py describing what
they are. A CLARAProjectInternal object is associated with a directory which keeps the
necessary text files.

The next most important file in $CLARA/clara_app/clara_code is clara_classes.py.
This defines the classes used for internal representation of text objects.

The file $CLARA/clara_app/clara_code/clara_prompt_templates.py defines the class
PromptTemplateRepository, which provides the interface for managing language-specific
prompt templates and prompt examples. 

A full list of files follows.

clara_cefr.py: Call ChatGPT-4 to estimate CEFR reading level.

clara_chatgpt4.py: Send request to ChatGPT-4 through API.

clara_chatgpt4_manual.py: Send request to ChatGPT-4 through popup window (not used in live system).

clara_chinese.py: Chinese-specific processing, in particular accessing the Jieba package.

clara_classes.py: Define classes used to for internal text representation.
The top-level class is called Text.

clara_concordance_annotator.py: Annotate a Text object with concordance information.

clara_conventional_tagging.py: Invoke TreeTagger tagger-lemmatiser. May later include other tagger-lemmatisers.

clara_correct_syntax.py: Call ChatGPT-4 to correct malformed C-LARA annotated text.

clara_create_annotations.py: Call ChatGPT-4 to add segmentation, gloss and lemma annotations to Text object.

clara_create_story.py: Call ChatGPT-4 to create a text.

clara_database_adapted.py: SQLite/Postgres compatibility.

clara_diff.py: Compare two versions of a CLARA file and present the results.

clara_doc_summary.py: Collect together docstrings from files (not used in live system).

clara_internalise.py: Create Text object from human-friendly string representation.

clara_main.py: Top-level file: defines CLARAProjectInternal class, which gives access to all other functionality.
This file includes full documentation of the CLARAProjectInternal methods.

clara_merge_glossed_and_tagged.py: Combine Text objects derived by internalising "glossed" and "lemma-tagged"
strings into single Text object.

clara_openai.py: OpenAI utility functions.

clara_prompt_templates.py: Parametrized prompts for ChatGPT-4-based annotation.

clara_renderer.py: Render Text object as optionally self-contained directory of static HTML multimedia files.

clara_summary.py: Create summary of text by calling ChatGPT.

clara_test.py: Test other functionality (not used in live system).

clara_tts_annotator.py: Annotate a Text object with TTS-generated audio information.

clara_tts_api.py: Code for calling third-party TTS engines.

clara_tts_repository.py: Manage repository which associates text strings with TTS-generated audio files.

clara_universal_dependencies.py: Convert part-of-speech tags to Universal Dependencies v2 tagset. Used by TreeTagger integration.

clara_utils.py: Utility functions.

config.ini: Config file.

4b. Django layer

The Django layer is organised according to the standard conventions of Django MVC web apps.
The main material is in the directory $CLARA/clara_app. There is also some config and associated
material in the directory $CLARA/clara_project.

views.py defines the possible operations (creating a project, listing projects, performing some kind of
annotation, etc). An operation will in may cases involve accessing a CLARAProject object (defined in models.py)
and an associated CLARAProjectInternal object (defined in $CLARA/clara_core/clara_main.py).
Typically an operation may reference some or all of the following: a template from
$CLARA/clara_app/templates/clara_app, another database table from models.py and a form from forms.py.

urls.py defines an association between URL patterns in web requests and operations defined in views.py.

models.py defines SQLite3 database tables.

forms.py defines forms associated with database tables.

The 'templates' directory defines templates used for rendering the results of operations.
All the templates are in the subdirectory 'templates/clara_app'.

utils.py defines utility functions.

backends.py defines backend functionality.

4c. HTML templates used by core Python code

These are in the directory $CLARA/templates. There are four files:

alphabetical_vocabulary_list.html: Template for creating alphabetical vocabulary list page.

clara_page.html: Template for creating main C-LARA content page.

concordance_page.html: Template for creating concordance page.

frequency_vocabulary_list.html: Template for creating frequency-ordered vocabulary list page.

4d. CSS and JavaScript used by core Python code

These are in the directory $CLARA/static. There are two files:

clara_styles.css: CSS used by core Python code and included in generated multimedia.

clara_scripts.js: JavaScript used by core Python code and included in generated multimedia.

4e. Prompt templates and examples

These are in the directory $CLARA/prompt_templates. There is one subdirectory for every
language with prompt templates, plus a 'default' directory with language-independent
defaults.

Files with .txt extension are prompt templates. Files with .json extension are examples to
be inserted into the prompt templates after appropriate preprocessing.

The associated code is in the file $CLARA/clara_app/clara_core/clara_prompt_templates.py and
the 'edit_prompt' view of $CLARA/clara_app/views.py.




