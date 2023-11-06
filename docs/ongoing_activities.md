<div style="overflow: hidden; background-color: #f1f1f1;">

  <a href="index.html" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Overview</a>
  <a href="examples.html" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Example content</a>
  <a href="ongoing_activities.html" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Ongoing Activities</a>
  <a href="collaborators.html" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Contributors</a>
  <a href="documents.html" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Documents</a>
  <a href="performance.html" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Technical issues</a>
  <a href="blog.html" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Blog</a>
  <a href="contact.html" style="float: left; display: block; color: black; text-align: center; padding: 14px 16px; text-decoration: none;">Contact</a>

</div>

## Ongoing Activities

Our current activities include:

**Melbourne University student projects**

Under the supervision of Alex Xiang, six five-person teams of Melbourne University computer science students are 
carrying out C-LARA-related projects. In each project, the students are reimplementing a standalone piece of functionality
that was part of the previous LARA platform, with the goal of later integrating it into C-LARA. 
The projects started at the beginning of August 2023 and are now nearly complete.

**UniSA server**

The current provisional deployment of C-LARA on Heroku is adequate for internal testing, but too slow for public use.
We are deploying a faster version on a UniSA server, with the intention of going live in November 2023.

**Multi-words**

Our evaluations show that multi-words are still a major problem for the glossing and lemma annotation phases
of C-LARA. When texts contain multi-words (phrases) like "how much" or "fall asleep", these should be annotated as
single units, but we have still not found reliable ways to give the AI the right instructions. Our language
teacher collaborators consider that this is currently one of the platform's most serious shortcomings, and
we are investigating various ways to address it.

**ChatGPT-4 and long-term memory**

One of the biggest practical problems when working with ChatGPT-4 as a software collaborator is that the AI has
a limited memory window, forgetting interactions that may have occurred only the previous day and being unable
to keep a global view of their activities in the project. We have been experimenting with the
<a href="https://www.papr.ai/memory" target="_blank">Papr Memory plugin</a>, which automates the process
of keeping an external long-term memory which ChatGPT can access autonomously. Anecdotally, this makes it 
much easier for Chat to keep an overview of the project.
