# C-LARA Overview (Project, Functionality, and Code Map)

**C-LARA** is a Django-based platform for creating and publishing **multimodal learner texts** with strong AI assistance. In practice we use **OpenAI models**—notably **gpt-5** for text/analysis and **gpt-image-1** for image generation/editing—to help with every stage of the pipeline.

Users can **either upload an existing text** or **ask the platform’s AI to draft a text from a short description**. From there, C-LARA supports segmentation, multiple layers of linguistic annotation (translation, MWE, lemma/POS, gloss, pinyin), audio (TTS or human), and **coherent AI image sets** (style → elements → pages), culminating in a rendered HTML reader.

Finished texts are **rendered as navigable HTML** and can be **posted** within the C-LARA social network, where readers can **add ratings and comments**, enabling lightweight quality feedback and iteration.

This document is a concise, implementation-oriented map that ties user-facing features to code structure so a maintainer (or AI assistant) can quickly answer: *“Where is this implemented, how does it flow, and what do I read next?”*

---

## 1) Landmarks: Files You Will Use Constantly

**Routes index**
- `clara_app/urls.py`  
  The canonical directory of features. Every user-facing action maps to a **route name** (`name="…"`) and an **entry view** (module + callable). Treat this as your search root: “find route → jump to entry view.”

**Global UI (top navbar)**
- `clara_app/templates/clara_app/base.html`  
  The fixed navigation bar with **tooltipped** links to global, social, admin, language-master, and user settings. Tooltips describe the feature at a glance and often imply route names.

**Per-project action hub**
- `clara_app/templates/clara_app/project_detail.html`  
  The project dashboard. Think of this as the “checklist” of the project pipeline. Each action links to the route implementing it (again with useful tooltips) and displays ✓ markers when outputs are up-to-date.

**Image generation v2 dashboard**
- `clara_app/templates/clara_app/edit_images_v2.html`  
  A consolidated interface for **Style → Elements → Pages**, with background advice, batch ops, and live toggles to show segmented/translated/MWE/lemma/gloss text per page. This page mirrors the orchestration logic in views for image pipelines.

---

## 2) Core Data Concepts and Models


### Historical split and where things live
For historical reasons there is a split between **`CLARAProject`** and **`CLARAProjectInternal`**. The original idea was that `CLARAProjectInternal` could be used independently; in practice they are now used together, but the split persists in the code layout:

- **Django-level models** used by `CLARAProject` live in `models.py`.
- Several **domain models** used by `CLARAProjectInternal` (and by the pipeline generally) live in **`clara_models.py`**.

### Projects

- **`CLARAProject`** (`models.py`) stores durable metadata: title; languages (**L2** text language, **L1** annotation language); switches (e.g., `uses_coherent_image_set_v2`, `has_image_questionnaire`); ownership/roles; community links; **cost accounting**; and a critical **`internal_id`** used to resolve the on-disk project.
- **`CLARAProjectInternal`** (`clara_main.py`) encapsulates **filesystem paths and staging** (raw vs derived artifacts, rendered HTML, temp dirs, zips, etc.). 

A very common pattern is:

  clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
  
 ### Text segmentation hierarchy (domain models in clara_models.py)

Segmentation is driven by an AI call that divides a text into a hierarchy:

**Text** → list of **Pages**

**Page** → list of **Segments** (roughly sentences)

**Segment** → list of **ContentElements** (roughly word-like units)

These classes (**Text**, **Page**, **Segment**, **ContentElement**) are defined in clara_models.py.

Each of these objects includes an annotations field used to store layer-specific data, e.g.:

**ContentElement**: glosses, lemma/POS, pinyin, translations

**Segment**: translations, MWE markup, etc.

### Multi-Word Expressions (MWE)

MWE annotation is central. A **Segment** carries MWE information indicating which **ContentElements** belong to the same expression. Downstream effects:

**ContentElements** in the same MWE are presented as a single unit for glossing and lemma tagging (shared gloss/lemma).

The rendered HTML includes JavaScript so that hovering one element highlights the entire MWE.

### Annotation products (conceptual layers)

Segmentation (pages, sentence-like segments, compound splitting)

Per-segment / per-element annotations: translation, MWE tags, lemma/POS, gloss, pinyin

Audio: TTS or human-uploaded (plus phonetic audio path for phonetic texts)

Images v2: style description + style sample, element list + element images, page images, optional questionnaire and community review artifacts


## 3) The Main Functional Clusters (User-Facing)

Think in **stages**, each surfaced clearly in `project_detail.html`:

1. **Authoring & metadata**
   - Create/Edit **plain text**, **title**, **summary**, **CEFR** estimate.
   - Outcome: baseline artifacts enabling later steps.

2. **Segmentation**
   - Split text into **pages** and **segments**, and **split compounds**.
   - Outcome: structured text units for per-segment operations.

3. **Linguistic annotations**
   - **Translation** per segment.
   - **MWE tagging** (drives highlighting and can affect glossing/pipeline).
   - **Lemma/POS**, **gloss**, **pinyin** (language-dependent).
   - These typically run **in parallel** (async) across segments with editable prompt templates (language-master role).

4. **Audio**
   - **Normal** (usually TTS); **phonetic** path (IPA or dedicated phonetic tools); **human audio** upload pipelines.
   - Forms guide option selection; rendering consolidates audio tracks.

5. **Rendering & Registration**
   - Build final **HTML + media** bundles; serve locally; optionally **register** in the C-LARA social network for discovery.

6. **Images v2**
   - **Parameters** → **Style** (AI description + sample image) → **Elements** (recurring visual components) → **Pages** (page images).
   - Batches execute **async in parallel**; community review & questionnaire flows hang off the same project.
   - The v1 editor remains for legacy compatibility; v2 is the current path.

7. **Admin & Language Masters**
   - Admin: users, roles, communities, maintenance actions (e.g., clean old tasks, reset TTS cache), manual password reset, funding credits.
   - Language master: **localization bundles**, **annotation prompt editing**, **phonetic lexicon** management.

---

## 4) How to Navigate the Code for Any Feature

**Recipe (use this every time):**
1. **Find the route** in `clara_app/urls.py`. Note `name="…"`, the **callable** and **module**.
2. **Jump to the entry view** (module file). This is the authoritative starting point.
3. Scan for:
   - `render(request, "…html", ctx)` → open the **template** (load the UI surface).
   - calls to **helpers** (same module first), then **imported helpers**.
   - how it obtains **CLARAProject** and **CLARAProjectInternal** (look for project ID plumbing).
   - **async/task orchestration** (fan-out/fan-in patterns) and any **OpenAI** usage.
   - **file paths** resolved via `CLARAProjectInternal` (where the artifacts are written/read).
4. Cross-check with the **template**:
   - Inputs (forms/formsets, hidden fields, POST `action` values).
   - Batch buttons and links to sub-routes (e.g., community review, questionnaire).
   - Conditionals that reveal dependencies (e.g., “only active if segmented text exists”).
5. If still unclear, search for the route name in **templates** and re-grep the module for the helper names you saw.

**Tip:** Start from UI → route → entry view → helpers → models. The template’s buttons often encode POST `action` values that map to specific helper functions in the view module.

---

## 5) Two Canonical Patterns in the Code

### A. Straight-through, file-system oriented “tooling” view (e.g., Export zipfile)
- **Entry view** validates the project, constructs a **self-contained directory** (copying/normalizing assets), zips it, and returns a streaming response.
- The important bits: reliable path resolution via `CLARAProjectInternal`, careful filtering (what to include/exclude), and stable HTTP response.

### B. Multistage orchestration “dashboard” view (e.g., Edit Images v2)
- **Single page** controlling multiple, semi-independent stages:
  - **Parameters**: save tuning knobs.
  - **Style**: use AI to expand advice & generate a representative style image.
  - **Elements**: generate recurring component images (parallel).
  - **Pages**: generate (or regenerate) specific page images (parallel; may be range-limited).
- The view typically:
  - Renders a formset per stage (see `edit_images_v2.html`).
  - On POST, reads an **action** string to decide which sub-routine to invoke.
  - Queues **parallel tasks** (per element/page) and aggregates results.
  - Updates disk artifacts in project directories (with predictable naming).
  - Serves preview images by stable routes (e.g., `serve_coherent_images_v2_file`).
- Auxiliary flows:
  - **Overview document** generation (summarizes choices & assets).
  - **Download zip** of all images.
  - **Community review**: organizer/member/external variants.
  - **Questionnaires**: activate, respond, and summarize by project.

---

## 6) Async & AI: What to Expect

- **Fan-out/fan-in** structure for segment-wise or page-wise jobs:
  - Launch many small jobs (e.g., “generate element images”) concurrently.
  - Collect completion, write files, update indices/JSON, show progress via status logs.
- **Prompt templates** (language master role):
  - The annotation steps use editable templates with examples; model-selection and guardrails are configurable per language.
- **Cost accounting**:
  - Calls that hit the OpenAI API are tracked per user/project. `project_detail.html` shows a running **API cost** total.

---

## 7) Permissions & Roles

- **User**: normal pipeline and personal settings.
- **Language Master**: prompt templates, phonetic lexicon, localization bundles.
- **Admin**: user management, communities/roles, maintenance ops, password resets, funding credits.
- **Community roles**: organizer/member (for image review), plus a **public view** (read-only results).

**Practical effect in code/templates**: menu visibility, enabling/disabling actions, extra admin-only forms/routes.

---

## 8) Storage, Paths, and Rendering

- `CLARAProjectInternal` standardizes the on-disk layout:
  - Where to read/write text, annotations, media, TTS/phonetic audio, image assets, render targets, and exports.
  - Rendering builds an **HTML bundle** (with page navigation, audio players, highlighting) per project.
- Serving:
  - Development: Django routes serve rendered content/pages.
  - Social registration: copies or points to the rendered output for discovery.

---

## 9) How to Investigate a Problem (Playbook)

1. Reproduce in the **UI** (look at the exact button/tooltip → route).
2. Open `urls.py`, find the **route**, jump to **entry view**.
3. Read the **template** used by the view (form names, POST `action` branches).
4. Follow helper calls and path operations (look for **per-page/segment loops**).
5. Confirm **preconditions** (e.g., segmentation must exist before translation; style must exist before elements/pages).
6. Check disk artifacts via `CLARAProjectInternal` path methods.
7. For AI steps, confirm **prompt sources** and **model configuration**.

---

## 10) How to Extend a Feature Safely

- Add a **new action** branch rather than mutating a working flow, if possible.
- Reuse existing **parallelization utilities** for per-segment/page jobs.
- Place new artifacts under `CLARAProjectInternal`’s expected directories.
- Create small **helpers** with clear inputs/outputs; keep entry view orchestration thin.
- Surface the new control in the **template** with:
  - a distinct POST action string,
  - clear tooltip,
  - and a minimal feedback UI (message/preview).
- Update the **route map** if you introduce new sub-views.

---

## 11) Reading the Image Pipeline (v2) via the Template

`edit_images_v2.html` is an excellent index of the orchestration:
- The presence of **three formsets** (Style, Elements, Pages) mirrors the three stages.
- Each **Save/Generate** button has a POST `action` value you can grep for in the view module.
- “Generate missing …” buttons typically **fan-out** per element/page and will correspond to helpers like `create_element_descriptions_and_images` or `create_page_descriptions_and_images`.
- Review links (e.g., `simple_clara_review_v2_images_for_page`) indicate additional **sub-routes** dedicated to targeted editing.

---

## 12) Minimal Conventions to Know

- **Route names are stable** and are the best dictionary between documentation and code.
- Templates live in `templates/clara_app/…` and are referenced by string literals in views.
- **POST `action`** strings act like sub-routes under a single view; use them to jump straight to the helper logic.
- **Two key models** (split for historical reasons) — `CLARAProject` (metadata/roles) and `CLARAProjectInternal` (paths/ops) — appear in nearly every non-trivial view.

---

## 13) Typical Q&A You Can Answer Quickly

- *“Where is ‘Create/Edit Segmented Text’ implemented?”*  
  In `project_detail.html`, find the link → route name → look up in `urls.py` → entry view in `…views.py` → follow helpers.

- *“Why is this link disabled?”*  
  The templates gate features with preconditions; check booleans like `can_create_segmented_text` in the context and trace how the view computes them.

- *“Where do page images get written?”*  
  In the image v2 view/helpers: look for path computations via `CLARAProjectInternal`, then inspect the serving route (`serve_coherent_images_v2_file`) for exact relative layout.

- *“How do we parallelize annotation?”*  
  Find the per-segment loop in the relevant view/helper; it will gather segments, launch **async calls** (OpenAI or image gen), and collate results.

---

## 14) What the AI Assistant Should Do (and Not Do)

**Do:**
- Start with this overview, then open `urls.py` and the relevant template to anchor yourself.
- Use the **route name** to keep yourself grounded when summarizing a feature.
- Cite **module.callable** names and **template paths** in any generated docs.
- If unsure between two possible helpers, say so and list both candidates with brief justification.

**Don’t:**
- Infer functions that do not appear in the code you’ve read.
- Hand-wave the async behavior; be explicit when fan-out/fan-in is used.
- Conflate v1 and v2 of the image editor; call out v2 as current.

---

## 15) Quick Start: Mapping a Feature End-to-End

1. In `project_detail.html`, identify the link and its tooltip. Copy the **route name**.
2. In `clara_app/urls.py`, find the `path` with that name; note `module.callable`.
3. Open the module → locate the **entry view** → skim for:
   - POST `action` branches
   - helper functions
   - template name(s)
   - `CLARAProject` + `CLARAProjectInternal` usage
4. Open the template → read forms/formsets and links; note any sub-routes.
5. Write a brief **“how it works”** paragraph + list 2–6 **main_processing** callables.

That’s usually enough context to fix issues, add small features, or draft user documentation.

---

*This overview is the priming scaffold. Pair it with (a) a per-route dependency slice (entry + helpers + templates), and (b) the repository vector store (including PDFs) to let the AI assistant produce accurate, source-cited maintainer docs feature by feature.*
