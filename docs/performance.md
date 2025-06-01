<div style="overflow: hidden; background-color: #f1f1f1;">

  <a href="index.html" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Overview</a>
  <a href="using.html" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Use C-LARA</a>
  <a href="examples.html" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Example content</a>
  <a href="ongoing_activities.html" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Ongoing Activities</a>
  <a href="collaborators.html" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Contributors</a>
  <a href="documents.html" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Publications</a>
  <a href="performance.html" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Technical issues</a>
  <a href="blog.html" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Blog and Discord</a>
  <a href="contact.html" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Contact</a>
  <a href="flinders_2024_workshop.html" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">2024 workshop</a>

</div>
## Technical issues
C-LARA is implemented in Python using the Django framework, with Django-Q for asynchrony.
The code is available from the public [GitHub repository](https://github.com/mannyrayner/C-LARA).

The repository contains, in descending order of size, Python, HTML template, prompt template and example, documentation, JavaScript and CSS files.
It currently totals about 40K lines. All the material has been created by versions of ChatGPT working in close collaboration with Manny Rayner,
with the AI responsible for about 80% of the code and the greater part of the software design.

## Error rates for writing and annotation
Our evaluations show that C-LARA's performance varies a great deal between languages. For well-resourced languages 
given a high priority by OpenAI, like English and Mandarin, C-LARA can use the underlying ChatGPT-4o functionality
to write entertaining texts on a wide variety of subjects, with an error rate of under 1%. Error
rates for glossing and lemma tagging for these languages are typically in the low to mid single digits. Performance
on smaller and less highly prioritised languages is substantially worse. The platform offers
many options for tuning language-specific performance.
