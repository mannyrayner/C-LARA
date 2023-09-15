
# C-LARA: ChatGPT-based Learning And Reading Assistant

## Overview
C-LARA, or **ChatGPT-based Learning And Reading Assistant**, is an open source web platform,
currently under development by an international open source consortium, whose purpose is to 
make it easy to create engaging multimedia texts that can help language learners develop their reading and listening skills.
The platform draws inspiration from the earlier [LARA project](https://www.unige.ch/callector/lara) but has been
completely rewritten. An initial deployment of C-LARA is currently being tested on the Heroku platform. 
We plan to release a generally available version in October/November 2023.

As the name suggests, ChatGPT-4 is at the centre of our activities. It is used in two complementary ways, both 
as a software *component* and as a software *engineer*. In its software component role, ChatGPT-4 performs
all the core language processing functions in the platform. It can write texts, divide them into sentences and 
lexical units, add glosses in another language, and annotate words with lemmas (root form) information.
Audio is automatically added for the wide range of languages where a TTS engine is available.

As a software engineer, ChatGPT-4 has played a central role in creating the codebase, which is freely
accessible on [GitHub](https://github.com/mannyrayner/C-LARA). ChatGPT-4 has produced about 90% 
of the code, working in close collaboration with its human partner Manny Rayner. It is also responsible for the greater 
part of the software design, and has written a substantial portion of the academic publications which
the project has produced. We consider that ChatGPT-4 has amply demonstrated its right to be considered
a core member of the project; our policy of consistently crediting it as a coauthor has already led to 
some controversy.

## Performance
Our evaluations show that C-LARA's performance varies a great deal between languages. For well-resourced languages 
given a high priority by OpenAI, like English and Mandarin, C-LARA can use the underlying ChatGPT-4 functionality
to write entertaining texts on a wide variety of subjects, with an error rate of well under 1%. Error
rates for glossing and lemma tagging for these languages are typically in the mid single digits,
with errors most commonly being due to incorrect treatment of multi-words (phrases). Performance
on smaller and less highly prioritised languages is substantially worse. The platform offers
many options for tuning language-specific performance, and we are actively investigating this topic.

## Contributors
- **BRANISLAV BEDI**: Pedagogical aspects, user studies, Icelandic evaluation
- **CHATGPT-4**: Software implementation and design
- **BELINDA CHIERA**: Project coordination, statistical analysis
- **CATHY CHUA**: Project coordination, ethical aspects
- **CATIA CUCCHIARINI**: User studies, Italian and Dutch evaluation
- **MARTA MYKHATS**: Pedagogical aspects, Ukrainian evaluation
- **NEASA NÍ CHIARÁIN**: User studies, Irish evaluation
- **MANNY RAYNER**: Software implementation and design, project coordination, English evaluation
- **CHADI RAHEB**: Farsi evaluation
- **ANNIKA SIMONSEN**: Linguistic annotation, user studies, Faroese, Danish and Icelandic evaluation
- **YAO CHUNLIN**: Pedagogical aspects, Mandarin evaluation
- **ALEX XIANG**: Supervision of student projects, Mandarin evaluation
- **RINA ZVIEL-GIRSHIN**: Russian evaluation

## Documents
- [ChatGPT-Based Learning And Reading Assistant: Initial Report](https://www.researchgate.net/publication/372526096_ChatGPT-Based_Learning_And_Reading_Assistant_Initial_Report) A comprehensive report as of late July 2023

- [README file](https://github.com/mannyrayner/C-LARA/blob/main/README.txt) Installation instructions, list of files.

- [FUNCTIONALITIES file](https://github.com/mannyrayner/C-LARA/blob/main/FUNCTIONALITY.txt) List of all top-level platform functionalities.

- [TODO file](https://github.com/mannyrayner/C-LARA/blob/main/TODO.txt) Remaining and completed to-do items.

- ["Continuity journal"](https://github.com/mannyrayner/C-LARA/blob/main/CONTINUITY_JOURNAL.txt) This file, continually updated by ChatGPT-4 with assistance from project members, is used by the AI to refresh its understanding of the project and its own role in it.






