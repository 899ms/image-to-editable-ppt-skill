---
name: image-to-editable-ppt
description: Use when the user gives one or more slide images, an image-based PPT/PPTX, or a PDF and asks for an editable PowerPoint/PPTX, slide reconstruction, image-only presentation conversion, per-page editable rebuilds, or preservation of PPT speaker notes.
---
# Image to Editable PPT

## Overview

Convert image, PDF, and image-based PPT/PPTX inputs into editable PowerPoint output. The workflow is input normalization -> per-page reconstruction -> deck assembly -> validation and repair. A single image produces a one-page PPTX. Multiple images produce a multi-page PPTX with one page per image, but image order is not guaranteed. A PDF produces one output page per PDF page in the same order. A PPT/PPTX produces the same number of output pages in the same order, and any source speaker notes must be copied to the matching output page unchanged.

This skill owns input splitting, job folder setup, subagent page assignment, editable text reconstruction, asset provenance, PPTX assembly, validation, visual QA, note preservation, and targeted repair. It delegates visual generation and visual decomposition to `$imagegen`.

## Priority And Non-Negotiable Dispatch

When this skill is invoked, its workflow and dispatch rules are the highest-priority task-specific instructions for the conversion job. For multi-image, PDF, and PPT/PPTX inputs, using subagents is mandatory, not optional: create exactly one page subagent per output page before page reconstruction begins.

Do not silently replace the required subagent workflow with parent-agent sequential processing. If subagents are unavailable, blocked by the current platform, or disallowed by higher-priority system rules, stop before rebuilding pages and report that subagent dispatch is the blocker. Continue without subagents only if the user explicitly approves a single-agent fallback after that blocker is stated.

Subagents must return a page with `completion_status: "ready_for_assembly"` or `completion_status: "blocked"` in `manifest.json`. The parent must assemble only pages marked `ready_for_assembly`. A page marked `blocked`, missing this field, or failing `validate_pptx.py --manifest` is not an input to deck assembly.

## Input Modes And Output Contract

- One image (`.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.gif`, `.tif`, `.tiff`) -> one-page `.pptx`.
- Multiple images -> multi-page `.pptx`; every image becomes a page, but do not promise relative order.
- PDF -> multi-page `.pptx`; PDF page N must become output slide N.
- PPT/PPTX -> multi-page `.pptx`; source slide N must become output slide N.
- PPT/PPTX speaker notes -> output speaker notes on the matching page, unchanged. Do not OCR, summarize, translate, rewrite, or send notes to subagents.

## Runtime And Dependencies

Use this skill's local runtime for dependency-based scripts. Let `{skill_root}` mean the directory containing this `SKILL.md`.

```bash
python3 {skill_root}/scripts/image_to_editable_ppt_runtime.py bootstrap
python3 {skill_root}/scripts/image_to_editable_ppt_runtime.py doctor
```

The runtime creates `{skill_root}/.venv` and installs `{skill_root}/requirements.txt`. The `.venv` and `.env` files are local state and must not be committed. PDF rendering uses PyMuPDF. PPT/PPTX rendering requires LibreOffice/`soffice` as a system dependency; if it is missing, stop and report the blocker.

## Job Folder Contract

Every run must create a fresh job folder and keep all intermediate and final files inside it:

```text
output/image-to-editable-ppt/<job-id>/
├── input/
├── deck_manifest.json
├── rebuilt.pptx
├── validation.json
├── notes_manifest.json
└── pages/
    └── page_001/
        ├── source.png
        ├── run_request.json
        ├── imagegen-jobs.json
        ├── assets/
        ├── split_assets_contact.png
        ├── manifest.json
        ├── preview.png
        ├── diff.png
        ├── diff.json
        ├── validation.json
        └── qa_notes.md
```

Use `scripts/prepare_inputs.py` to normalize inputs and create `deck_manifest.json`:

```bash
python3 {skill_root}/scripts/prepare_inputs.py input1.png input2.png
python3 {skill_root}/scripts/prepare_inputs.py deck.pdf
python3 {skill_root}/scripts/prepare_inputs.py image_based_deck.pptx
```

## Generation Delegation

Use `$imagegen` as the default source for clean visual layers, then use deterministic local scripts only for alpha cleanup, splitting, placement, packaging, and validation. For dense infographic, technical-route, dashboard, architecture, or diagram-heavy slides, prefer a layered imagegen workflow instead of one full-slide background: generate a clean layout/base layer with all readable text removed and standalone reusable icons removed; generate one or more sparse chroma-key asset sheets for icons, arrows, checks, magnifiers, badges, pictograms, chart glyphs, and reusable diagram parts; remove the key locally; split the transparent sheets; then rebuild the slide with the clean base image, independent PNG assets, editable PPT text, and simple editable geometry.

Asset sheets must be sparse. Require at least 260 px of pure chroma-key space between visible assets for dense slides, at least 220 px for simpler slides, allow assets to shrink to preserve spacing, and require each listed icon/object to be internally complete as one visual object. Do not accept crowded sheets as final inputs to splitting; regenerate the sheet before trying to rescue severe crowding with post-processing.

For complex infographic pages, do not rely on OCR as the truth source. Build or verify a `text_inventory` from visual inspection, user-provided text, or manual correction, then recreate readable text as native PowerPoint text. `$imagegen` is for clean non-text visual assets, not for exact text rendering.

Before generating an asset sheet or repair asset, load and follow the installed image generation skill:

```text
${CODEX_HOME:-$HOME/.codex}/skills/.system/imagegen/SKILL.md
```

Do not call the Image API directly for the normal path. Let `$imagegen` choose its built-in-first path and its own fallback rules. If `$imagegen` says a fallback requires confirmation, ask the user before continuing.

Use this skill's scripts only for deterministic work: removing/splitting `$imagegen` asset-sheet images, cropping `$imagegen` asset-sheet regions when generated components touch, mapping generated assets to source coordinates, building manifests, assembling PPTX files, producing local previews, contact sheets, and validating package structure, provenance, and editable text. Do not crop non-text visual assets directly from the original source image as the default decomposition path. Source-image crops are allowed only as explicit visual-99 fallback or as diagnostic/alignment references. Do not locally draw, synthesize, trace, or replace complex visual assets with Python/Pillow, SVG, canvas, HTML/CSS, source crops, or hand-made placeholders as a substitute for `$imagegen`.

Photo-background exception: when the page is primarily one complex photo or texture background with only overlay text, do not decompose the photo into objects and do not use local blur/darken/inpaint as the final cleanup. Use `$imagegen` image editing to produce a clean no-text background image, then rebuild all readable text as visible native PPT text boxes. Treat the edited no-text background as one background asset with provenance; it is acceptable because the editable layer is the text overlay, not individual trees/buildings/waves in the photo.

Exception: when the user explicitly asks for pixel-level, near-original, or 99% visual fidelity and accepts the editability tradeoff, use a `visual-99` / fidelity-first mode only as a clearly labeled visual fallback. In that mode, source-region rasterization is allowed for approved single objects or fidelity-critical regions, but it must be recorded as `source_type: "user-approved-rasterization"` with `source_region_px` or `source_bbox_px`, `approval_note`, and `qa_note`. Any readable text left inside a source crop must be declared in `rasterized_or_omitted_text`; primary readable text must still be recreated as visible native editable text when the deliverable is called editable. Never present full-slide raster, tiled full-page raster mosaics, hidden/tiny text overlays, or grid crops as object-level editable reconstruction.

Hard boundary: do not mark visual decomposition complete by inventing assets, cropping assets from the original source image, editing manifests to hide missing assets, or recording temporary placeholder art as final. If the task requires generated separation, repair, or redraw and `$imagegen` is unavailable, stop and explain the blocker instead of fabricating the visual layer.

Hard boundary: never use the full source slide image (`source.png`) as a full-slide background and then overlay editable text boxes as a normal editable reconstruction. That creates duplicate baked-in text underneath editable text. It is a failed page, not a documented limitation. The validator rejects this pattern.

Before skipping `$imagegen`, make an explicit page-level gate decision in `run_request.json`, `manifest.json`, or `qa_notes.md`:

```json
{
  "page_type": "dense_dashboard",
  "imagegen_required": true,
  "skip_imagegen_allowed": false,
  "imagegen_skip_reason": null
}
```

Skip `$imagegen` only after positively confirming that every non-text visual object is a plain editable primitive, such as straight lines, rectangles, round rectangles, circles, or structural chart bars. This is a reverse-proof gate: if any standalone icon, pictogram, badge, sticker, tape, paper texture, shadowed illustration, decorative mark, sketchy arrow/underline, hand-drawn mark, or other style-bearing reusable visual object is present, `$imagegen` is required even if the rest of the page is simple geometry. Dashboard, dense infographic, technical-route, and architecture pages default to `imagegen_required: true`; set `skip_imagegen_allowed: true` only when the QA notes list concrete evidence that no style-bearing visual objects exist. Do not use local drawing code or native PowerPoint preset shapes to approximate required `$imagegen` assets unless the user explicitly accepts that downgrade as a visual-fidelity/editability tradeoff.

If `$imagegen` is unavailable and the user explicitly asks for a usable fallback instead of blocking, use `fallback_mode: "editable-layout-draft"`: rebuild a clean native-PPT layout with editable text, simple shapes, and no full-slide raster source background. This fallback sacrifices visual fidelity and may omit complex icons/photos, but it must not overlap editable text on baked-in source text. Record omitted visual assets in `rasterized_or_omitted_text` or `qa_notes.md`.

## Visible Progress Plan

For every normal run, keep a visible checklist with one active step at a time:

1. Preparing inputs and job folder.
2. Assigning page reconstruction.
3. Rebuilding editable pages.
4. Assembling the PPTX deck.
5. Checking and repairing.

What each step means:

- `Preparing inputs and job folder.` Copy inputs to `input/`, normalize each page to `pages/page_NNN/source.png`, create `deck_manifest.json`, and extract PPT/PPTX notes into `notes_manifest.json`.
- `Assigning page reconstruction.` For multi-image, PDF, and PPT/PPTX inputs, dispatch one subagent per page. This is mandatory. If subagent dispatch cannot happen, stop and report the blocker instead of rebuilding pages in the parent agent. Single-image jobs may stay in the parent agent.
- `Rebuilding editable pages.` Each page job creates its own manifest, assets, preview, diff, validation, and QA notes inside its `pages/page_NNN/` folder.
- `Assembling the PPTX deck.` The parent agent reads `deck_manifest.json`, ordered page manifests, and notes manifest; then writes `rebuilt.pptx`.
- `Checking and repairing.` Run page and deck validation, inspect previews or renderer screenshots, compare against sources, treat visibly poor placeholder-like icons or style-bearing assets as blockers, repair the smallest failing scope, and report final paths.

Only mark a step complete when the real file, image, manifest, validation report, or decision exists. For a repair-only request, start from the first relevant step instead of restarting the whole workflow.

## Workflow

1. Normalize inputs with `prepare_inputs.py`. Stop if PPT/PPTX input needs LibreOffice and `soffice` is unavailable.
2. For multi-image, PDF, and PPT/PPTX jobs, dispatch one Codex subagent per page. The parent owns `deck_manifest.json`, `notes_manifest.json`, final assembly, and final validation. Do not proceed to page reconstruction in the parent agent when subagent dispatch is unavailable; stop and ask for explicit fallback approval.
3. For each page, inspect `source.png` and identify canvas size, layout regions, all visible text, reusable graphic assets, required non-text visual objects, and which elements must remain editable. Record the page-level `imagegen_required` / `skip_imagegen_allowed` decision and evidence before rebuilding the page.
4. Choose the visual strategy for that page. For complex photo-background pages with only overlay text, use `$imagegen` image editing to create a no-text background, then skip asset-sheet splitting. For dense infographic or technical-route pages, use the layered imagegen strategy: first generate a clean no-readable-text layout/base layer, and when icons or reusable diagram glyphs need to be movable, ask `$imagegen` to remove those standalone icons from the base too; then generate sparse chroma-key asset sheets for the standalone icons, arrows, checks, magnifiers, pictograms, chart glyphs, and reusable diagram parts. For simpler illustrated slides, use `$imagegen` asset sheets directly. Do not satisfy this step by cropping those visual objects from `source.png`, or by approximating style-bearing icons/pictograms with local drawing code or PowerPoint preset shapes.
5. Remove the chroma-key background, then split the transparent asset sheet into individual PNG assets. Generate `split_assets_contact.png` for every multi-asset sheet and inspect it before building the page manifest.
6. Record provenance for the clean base and for each `$imagegen` asset, then create `pages/page_NNN/manifest.json` describing slide size, background/base image placements, independent image placements, editable text boxes, simple shapes, a complete `text_inventory`, required visual object coverage, and `completion_status`.
7. Validate each page output with `validate_pptx.py output.pptx --manifest manifest.json --report validation.json`. This validator includes the assembly-readiness contract and rejects full-slide `source.png` backgrounds with editable text overlays. Each subagent must write `pages/page_NNN/qa_notes.md` and must not edit the final deck manifest or final PPTX.
8. Assemble the final PPTX from `deck_manifest.json` with `build_pptx_from_manifest.py --deck-manifest deck_manifest.json --out rebuilt.pptx` only after every page manifest has `completion_status: "ready_for_assembly"` and page validation passes. For PPT/PPTX input, copy notes from `notes_manifest.json` to the matching slide.
9. Run deck validation with `validate_pptx.py rebuilt.pptx --deck-manifest deck_manifest.json --report validation.json` before reporting completion.
10. If page or deck validation shows missing words, missing assets, clipped text, broken relationships, notes mismatch, missing page outputs, obvious layout drift, or preview-visible poor icons/assets, repair only the smallest failing scope and rebuild. Do not report completion while the preview contains crude placeholder shapes, wrong icon metaphors, broken pictograms, illegible generated marks, or visually downgraded assets that should be regenerated through `$imagegen`.

For detailed prompt patterns, manifest schema, and validation criteria, read `references/workflow.md`.

## Editing Policy

- Prefer visible editable text boxes for all readable text, including labels inside diagrams whenever practical. Hidden, transparent, 1 pt, off-canvas, or metadata-only text boxes do not satisfy text editability.
- Use raster images only for non-text visual assets: clean layout bases, illustrations, icons, handwritten decorations, texture, tape, shadows, folders, cards, backgrounds, chart/diagram glyphs, and decorative marks.
- For photo-background slides, use one edited no-text background image plus visible editable text boxes. Do not leave baked-in text in the background, and do not accept local blur/darken patches with visible ghosting as final.
- If the user values visual fidelity over editability, explicitly state the tradeoff and rasterize only the agreed elements. Record this as user-approved rasterization in provenance and document any rasterized readable text in `rasterized_or_omitted_text`. Do not call that output object-level editable unless visible text and required visual objects are independently represented.
- If the user values a usable fallback over fidelity while `$imagegen` is unavailable, create an `editable-layout-draft` with no full-slide source raster background. This is allowed only as a clearly labeled fallback and should look clean rather than visually identical.
- Keep source images, generated asset sheets, split assets, `split_assets_contact.png`, manifest, PPTX, preview, `original_vs_rebuilt_diff.png`, `diff.json`, and validation report in a single output folder.

## Subagent Use

For a single image, subagents are optional. The parent agent may do the whole one-page job.

For multiple images, PDF, and PPT/PPTX inputs, use one subagent per page. This is a hard requirement of this skill. The parent agent assigns each subagent exactly one `pages/page_NNN/` folder and source image. A subagent may create or edit only files inside its assigned page folder. It must return the page manifest path, preview/diff paths, validation path, QA notes, and any known limits.

If the current runtime cannot spawn subagents, do not mark `Assigning page reconstruction.` complete and do not continue as a parent-only rebuild. Report the blocker clearly and wait for the user to either enable subagents or explicitly authorize a single-agent fallback.

Subagents must not edit `deck_manifest.json`, `notes_manifest.json`, other page folders, source input files, or the final `rebuilt.pptx`. Speaker notes are handled only by the parent agent and must not be sent to subagents for rewriting or analysis.

Subagent prompt must include this exact gate: "If you cannot produce a clean no-text visual layer or an explicitly allowed editable-layout-draft, set `completion_status` to `blocked`, write the blocker in `qa_notes.md`, and do not create a ready page manifest." Do not weaken this gate in the parent prompt.

## Repair Workflow

Repair the smallest failing scope:

- Missing or incorrect text: update `text_inventory`, add or fix editable text boxes, and rerun validation.
- Clipped or overlapping text: resize boxes, split text boxes, or reduce font size.
- Low-fidelity asset: rerun `$imagegen` for that asset or a narrower asset sheet, then resplit or recrop only the affected asset.
- Preview-visible placeholder icon or crude native-shape approximation: classify it as a missing `$imagegen` asset, generate a focused sparse asset sheet for only the affected icon(s), replace the approximation, rerun preview/diff/validation, and record the repair in `qa_notes.md`.
- Broken image relationship: fix the asset path in the manifest or regenerate the missing asset file.
- Incorrect background: fix `slide.background` or use an explicit full-slide shape when the background needs layered texture.
- Text overlaps baked-in source text: do not move the text boxes around as a repair. Replace the source background with a clean no-text `$imagegen` background, or switch to an approved `editable-layout-draft` with no source raster background.
- Layout drift: adjust manifest coordinates and regenerate preview/diff before touching the visual assets.

Do not regenerate the whole slide when a text box, one asset, or one coordinate change is enough.

## Commands

Prepare inputs and create a job folder:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/image-to-editable-ppt"
python3 "$SKILL_DIR/scripts/prepare_inputs.py" slide1.png slide2.png
python3 "$SKILL_DIR/scripts/prepare_inputs.py" deck.pdf
python3 "$SKILL_DIR/scripts/prepare_inputs.py" image_based_deck.pptx
```

Assemble a multi-page deck after page manifests are ready:

```bash
python3 "$SKILL_DIR/scripts/build_pptx_from_manifest.py" \
  --deck-manifest output/image-to-editable-ppt/<job-id>/deck_manifest.json \
  --out output/image-to-editable-ppt/<job-id>/rebuilt.pptx
```

Validate a multi-page deck:

```bash
python3 "$SKILL_DIR/scripts/validate_pptx.py" \
  output/image-to-editable-ppt/<job-id>/rebuilt.pptx \
  --deck-manifest output/image-to-editable-ppt/<job-id>/deck_manifest.json \
  --report output/image-to-editable-ppt/<job-id>/validation.json
```

Crop one `$imagegen` asset-sheet region into a reusable image and append provenance. This helper is for generated asset sheets only; do not use it to crop non-text assets from `source.png`:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/image-to-editable-ppt"
python3 "$SKILL_DIR/scripts/crop_image_asset.py" \
  --input imagegen_asset_sheet_alpha.png \
  --out assets/icon_trigger.png \
  --box 120,80,260,220 \
  --manifest manifest.json \
  --source-type imagegen \
  --qa-note "Icon cropped from the selected imagegen asset sheet and visually inspected."
```

Split a transparent asset sheet into component PNG assets after chroma-key removal:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/image-to-editable-ppt"
python3 "$SKILL_DIR/scripts/split_alpha_components.py" \
  --input imagegen_asset_sheet_alpha.png \
  --out-dir assets \
  --names icon_doc.png,icon_book.png,icon_bulb.png,icon_chart.png,icon_target.png \
  --sort x \
  --square
```

The splitter defaults are tuned for generated sparse asset sheets: `--connectivity 8`, `--close-radius 3`, and `--merge-gap 18`. If assets are intentionally close together, lower `--merge-gap` or set it to `0`; if broken strokes remain split, retry once with `--merge-gap 24` before manual crop boxes.

Build from a manifest:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/image-to-editable-ppt"
python3 "$SKILL_DIR/scripts/build_pptx_from_manifest.py" manifest.json --out output.pptx
```

Validate the result:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/image-to-editable-ppt"
python3 "$SKILL_DIR/scripts/validate_pptx.py" output.pptx --manifest manifest.json --required-text "标题" --report validation.json
```

Generate a local preview from the manifest when real PowerPoint/WPS rendering is unavailable:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/image-to-editable-ppt"
python3 "$SKILL_DIR/scripts/build_pptx_from_manifest.py" manifest.json --out output.pptx --preview preview.png
```

Render a simple image diff between the source and preview or renderer screenshot:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/image-to-editable-ppt"
python3 "$SKILL_DIR/scripts/render_diff.py" \
  --expected source.png \
  --actual preview.png \
  --out diff.png \
  --comparison original_vs_rebuilt_diff.png \
  --report diff.json
```

## Rules

- Use `$imagegen` clean visual layers as the primary and default decomposition path for non-text visual content. For dense infographic pages, this means a clean layout/base layer plus sparse asset sheets, not one all-purpose generated background.
- Treat the `imagegen_required` gate as mandatory page metadata. For dashboard, dense infographic, technical-route, and architecture pages, default it to `true`; if the final manifest has `images: []`, the page must document `skip_imagegen_allowed: true` plus concrete evidence that all non-text visuals are only plain primitives.
- Prompt asset sheets as sparse single-sheet layouts by default: at least 260 px of pure chroma-key spacing for dense pages and at least 220 px for simpler pages, spacing more important than asset size, no touching or cross-asset shadows, and each icon internally complete as one object.
- Prefer `$imagegen` when deciding whether a visual element is a shape or an asset. Keep only simple structural geometry editable; split style-bearing or reusable visual elements into PNG assets.
- Do not use the "simple primitives" exception for slides with hand-drawn small icons, tape, textured notes, decorative strokes, shadows, or pictograms. Recreate readable text as editable PPT text, but split those non-text visuals with `$imagegen`.
- Do not crop non-text visual assets directly from the original source image in editable-first mode. In explicit visual-99 mode, source-region crop assets are allowed only with strong provenance, source region coordinates, and approval notes; full-page raster mosaics are fidelity fallbacks, not object-level editable PPT.
- Do not use regular grid crops, tile mosaics, or large source regions that contain multiple unrelated objects as a substitute for element extraction. A crop that includes a surrounding card, neighboring text, or several icons is a page fragment, not an extracted asset.
- Keep source images attached/visible for `$imagegen` whenever the chosen path supports references.
- Do not rely on `$imagegen` for exact editable text; recreate readable text as editable PPT text boxes.
- Do not satisfy editable text coverage with hidden/tiny overlay text. The visible text in the reconstructed slide must come from native PPT text boxes when the text is claimed editable.
- Do not rely on generated images for exact slide geometry; use the manifest and deterministic scripts for placement. Use the source image only as an alignment reference unless the user explicitly accepts visual-99 source rasterization.
- Do not use local drawing code or native PowerPoint preset shapes to fake complex visual assets that should have come from `$imagegen`.
- Do not use local blur, dark rectangles, clone-like patches, or threshold masks as the final way to remove text from a complex photo background. They are acceptable only as diagnostic masks or prompt aids before `$imagegen` background repair.
- Do not use macOS Quick Look thumbnails as the visual acceptance renderer; they can distort PPT text layout. Prefer this skill's manifest preview, PowerPoint/WPS screenshots, or an explicitly trusted renderer.
- Do not accept a PPTX solely because deterministic validation passes; visually inspect the generated preview or a trusted renderer screenshot.
- Treat the visual preview as an active repair trigger, not a passive artifact. If icons, pictograms, badges, or decorative marks look crude, mismatched, placeholder-like, malformed, or obviously worse than the source, stop and repair those assets with `$imagegen` before final reporting.
- Do not skip the asset contact sheet when multiple assets are extracted; it catches clipped icons, wrong component order, and accidental fragments before PPT assembly.
- Treat contact-sheet crowding, cross-asset merges, clipped edges, and repeated fragments as blockers. Regenerate the asset sheet when spacing is the cause; use deterministic crop boxes only when one or two assets still need repair.
- Treat unapproved full-slide rasterization or tiled full-page source-raster mosaics as blockers for editable reconstruction, even when visual diff scores are excellent.
- Treat missing independent required visual objects as blockers. If the source has hand-drawn icons, arrows, notes, tapes, charts, badges, checkboxes, underlines, pictograms, KPI icons, management-insight icons, decorative illustrations, or other style-bearing visual objects, the final manifest must contain corresponding named `$imagegen` assets unless the user explicitly accepted a downgrade. Clean base images, page tiles, and native-shape approximations do not count for independently movable object coverage.
- Treat missing `text_inventory` entries, missing relationship targets, broken media files, and unreadable Chinese preview text as blockers.
- Treat visual drift, missing icons, missing labels, rasterized text that was meant to be editable, and clipped content as repair items.

## Acceptance Criteria

- PPTX opens as a valid zip package.
- Output is always `.pptx`.
- Single image output has one slide.
- Multiple image output has one slide per image, with no promise about relative source-image order.
- PDF output slide N corresponds to PDF page N.
- PPT/PPTX output slide N corresponds to source slide N.
- PPT/PPTX speaker notes, when present, are preserved on the matching output slide with identical text.
- Every readable source string is listed in `text_inventory`, and every item is present as editable text unless intentionally documented as rasterized or omitted.
- Every readable source string is visible as editable native text unless intentionally documented as a visual-only fallback.
- Every required non-text visual object is independently represented. Plain primitives may be native shapes; standalone style-bearing objects must be named `$imagegen` image assets unless the user explicitly accepts a documented downgrade or visual-only fallback.
- Every page records `imagegen_required`, `skip_imagegen_allowed`, and any `imagegen_skip_reason` or skip evidence. Dashboard, dense infographic, technical-route, and architecture pages with `images: []` pass only when the skip evidence proves there are no standalone icons, pictograms, badges, stickers, decorative marks, or other style-bearing reusable objects.
- If `imagegen_required` is true, every standalone style-bearing visual object has a named `$imagegen` asset with provenance, or a documented user-approved downgrade/fallback.
- Validation report includes slide count, image count, editable shape count, required-text results, missing package parts, missing relationship targets, media hash mismatches, and warnings.
- Every final raster asset has a validator-checked provenance entry with a valid `source_type`, existing `source`, and `qa_note`; user-approved rasterization also needs `approval_note` and source region coordinates.
- A local manifest preview is produced. A real PowerPoint/WPS renderer screenshot is also produced when a renderer is available.
- Preview-visible crude placeholder icons, wrong icon metaphors, malformed pictograms, or native-shape approximations of style-bearing assets are blockers and must be repaired with targeted `$imagegen` asset generation before completion.
- A split-assets contact sheet is produced when visual assets are decomposed, clean base images are inspected for leftover readable text or duplicated standalone icons, and a human-readable source/preview/diff comparison is produced for visual QA.
- For photo-background slides, a clean no-text background image is produced and inspected; old text ghosting, blur blocks, dark boxes, or generated replacement text are blockers.
- Any known visual-fidelity limits are documented rather than hidden.
- Final response names the PPTX path, validation report path, and any known fidelity limits.
