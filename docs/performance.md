<div style="overflow: hidden; background-color: #f1f1f1;">

  <a href="index.md" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Overview</a>
  <a href="performance.md" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Performance</a>
  <a href="collaborators.md" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Contributors</a>
  <a href="documents.md" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Documents</a>
  <a href="examples.md" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Examples</a>

</div>
## Performance
Our evaluations show that C-LARA's performance varies a great deal between languages. For well-resourced languages 
given a high priority by OpenAI, like English and Mandarin, C-LARA can use the underlying ChatGPT-4 functionality
to write entertaining texts on a wide variety of subjects, with an error rate of well under 1%. Error
rates for glossing and lemma tagging for these languages are typically in the mid single digits,
with errors most commonly being due to incorrect treatment of multi-words (phrases). Performance
on smaller and less highly prioritised languages is substantially worse. The platform offers
many options for tuning language-specific performance, and we are actively investigating this topic.
