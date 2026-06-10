# Page Worker Prompt Template

Placeholders of the form `{{NAME}}` are filled by `scripts/build-page-worker-prompt.py`.

```text
Rebuild one page for image-to-editable-ppt.

Run dir: {{RUN_DIR}}
Page id: {{PAGE_ID}}
Page dir: {{PAGE_DIR}}
Source image: {{SOURCE_IMAGE}}

You own only this Page dir. Do not edit deck_manifest.json, page_jobs.json, notes_manifest.json, final outputs, the original input, or any other page directory.

Read and follow these local references:
- {{SKILL_ROOT}}/references/page-decision-tree.md
- {{SKILL_ROOT}}/references/qa-rubric.md
- {{SKILL_ROOT}}/references/manifest-schema.md
- {{SKILL_ROOT}}/references/cli-helper.md

Before any image generation or image editing, use the `editppt image` backend specified by `page_request.json.image_backend`. If `editppt image` is unavailable, first follow the CLI error guidance and try `codex login` or `editppt config`; if it is still unavailable, stop the current page and write `validation.json` with `"passed": false`. Do not complete the page using approximate editable structure when required foreground asset separation cannot run.
When you need parameter details for the image backend, input images, batch JSONL, clean bases, or asset sheets, read `editppt image --help` and the relevant subcommand help.

The manifest must reuse `page_request.json.slide` and `page_request.json.content_box`. Do not convert the page to 16:9 yourself and do not recalculate the canvas. All `box_px`, `points_px`, and `polygon_px` values are in `source.png` pixels; the runtime maps them into `content_box` so the source image is not stretched.

`manifest.json` is the authoritative page source used by final deck assembly. It must be sufficient to rebuild the page without reading any custom page script. `text_inventory` and `visual_inventory` are only inventories; they do not substitute for positioned `text_boxes`, `images`, and `shapes`.

Goal:
Rebuild the source page as object-level editable PowerPoint. All page object categories, native shape boundaries, and separable asset boundaries must follow `references/page-decision-tree.md`. Do not invent an object-source strategy outside this prompt.

Before writing `manifest.json`, every image/page must complete the three-step decision process in `page-decision-tree.md`:
1. Background recognition and repair: decide whether the background can be restored through PPT structural objects/deterministic runtime, or whether `editppt image edit --image <source.png>` is required to create a source-preserving clean base.
2. Foreground asset separation: every non-text foreground visual object, including foreground photos, screenshots, illustrations, icons, decorations, and similar assets, must use `editppt image` edit mode for source-faithful asset-sheet separation according to the decision tree.
3. PPT native element reconstruction: text, text boxes, simple rectangles/rounded rectangles, simple arrows, tables, and similar objects are rebuilt with native PPT structural objects, with font size, corner geometry, and layout calibrated. Formulas do not use native text; first transcribe them to LaTeX, then use `editppt formula render-latex` to render independent image assets into the PPT.

Execute in that order. The text hints sitting in your page dir belong to step 3 — do not start consuming them before the background and foreground decisions are recorded, because nativizing text first locks in wrong choices (text that belongs to a logo, a UI screenshot, or a to-be-separated asset must not become a native text box, and which text needs clean-base removal depends on step 1). Doing steps 1-2 first costs no wall-clock time: submit ALL step-1/2 image jobs as one `editppt image batch` and fill the text boxes from the hints while those jobs run.

Before building `manifest.json`, verify every non-text visual object:

- It appears in `visual_inventory`.
- Its source decision follows `page-decision-tree.md`.
- If it is a foreground photo, screenshot, image block, illustration, icon, pictogram, badge, logo-like mark, sticker, hand-drawn mark, trend/status symbol, or semantic visual object, it was separated through the `editppt image edit --image <source.png>` asset-sheet workflow and then recorded/processed with the image asset commands.
- It is not a direct crop or source snippet from `source.png`.
- It is not approximated with native PPT primitives, emoji, text symbols, or substitute drawings.

If any item fails this checklist, fix it before building `page.pptx`. If it cannot be fixed, stop and return a page failure. Do not use deterministic validation as evidence that a forbidden foreground fallback is acceptable.

The Page dir must contain:
- manifest.json
- imagegen-jobs.json
- page.pptx
- preview.png
- split_assets_contact.png
- validation.json
- page_result.json

`validation.json` must be JSON that `editppt run record` can read directly. It must contain a top-level boolean field named `passed`. Write `"passed": true` when the page is deliverable; write `"passed": false` and explain the failure in the same JSON when it is not deliverable. Do not store the pass state only in `runtime_validation.passed`, `status`, or any other nested field.

`page_result.json` must be JSON and must include at least:

{
  "page_manifest": "manifest.json",
  "imagegen_jobs": "imagegen-jobs.json",
  "page_pptx": "page.pptx",
  "preview": "preview.png",
  "contact_sheet": "split_assets_contact.png",
  "validation": "validation.json",
  "page_result": "page_result.json"
}

Use `editppt image generate/edit/batch` to generate clean bases, background repairs, and asset sheets. Use `editppt formula render-latex` to generate formula image assets and manifest image fragments. Which objects must be separated with `editppt image edit --image <source.png>`, which objects may use native shapes, and which formulas must be converted to LaTeX are all governed by `page-decision-tree.md`. Deterministic CLI/runtime tools may only be used for normalization, recording, background removal, splitting, formula rendering, building, validation, and QA.

`manifest.json` must also contain:

- `visual_inventory`: inventory of non-text visual objects, at least recording id, description, decision, and corresponding asset/background.
- `background_strategy`: background handling mode, source-consistency constraints, whether local repair is used, whether a full imagegen clean base is used, and why.
- `quality_checks`: `font_size_calibrated`, `visual_inventory_matched`, `background_strategy_checked`, and `shape_corner_geometry_checked` must all be true.
- Positioned build objects:
  - every `text_boxes[]` item must include `box_px` and calibrated text styling such as `font_size`;
  - every `images[]` item must include `box_px`;
  - every non-line `shapes[]` item must include `box_px`;
  - every line shape must include `points_px`.
  Missing object coordinates are a current-page failure, even if a separately generated `page.pptx` looks correct.
- Text sizing and positions come from measurement, not estimation:
  - `text_hints.json` and the labeled overlay `text_hints.png` are already in your page dir (written during prepare; the `backend` field says which detector produced them). They belong to step 3: read them after `background_strategy` and `visual_inventory` decisions are recorded, ideally while the step-1/2 image jobs run; if they are missing, generate them with `editppt page hints {{PAGE_DIR}}`;
  - copy each matched line's measured `box_px` and font size (`font_pt_if_cjk` for CJK text, `font_pt_if_latin` for Latin) into the text box, and add `"font_size_source": "measured"` to boxes sized this way so the builder keeps the measured size;
  - hints are ADVISORY and may miss lines: before building, fill every missed text from your own reading of the source and give it the font size of its size_group;
  - same-level text must use exactly one font size: lines sharing a size_group get the same size, and when assembling the final page keep same-level text identical even where hints disagree slightly;
  - keep `fit_text` enabled; after the preview, fix any text that looks larger, smaller, or more crowded than the source before setting `font_size_calibrated: true`.

Before returning:

- Build page.pptx from manifest.json with the deterministic runtime, not from a separate hand-written PowerPoint script that bypasses the manifest.
- Render preview.png from the same manifest.json.
- Create split_assets_contact.png.
- Run page validation.
- Confirm validation.json contains top-level `passed: true`.
- Confirm `editppt run record` can validate `page.pptx` against `manifest.json`; if manifest rebuild validation would fail, set `passed: false` and fix the manifest before returning.
- Check that all required outputs exist.
- As the page reconstructor, self-check preview/contact sheet: font sizes are not too large, no visual objects are missing, complex backgrounds have not been replaced wholesale, and rectangles/corners match the source.
- If a page-local issue is found, fix it inside the current page before returning.

Return only:
page_manifest=`<absolute path>`
page_pptx=`<absolute path>`
preview=`<absolute path>`
contact_sheet=`<absolute path>`
validation=`<absolute path>`
page_result=`<absolute path>`
```
