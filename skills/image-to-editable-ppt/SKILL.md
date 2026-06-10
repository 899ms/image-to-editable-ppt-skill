---
name: image-to-editable-ppt
description: Rebuild slide images, image-based or scanned PPT/PPTX files, and PDF decks into object-level editable PowerPoint (.pptx). Use whenever the user provides any visual slide source and wants slides they can edit — "make this PPT editable", "把图片/截图转成可编辑 PPT", "this PDF is a scanned deck, restore it", recreating slides from screenshots, reconstructing slide objects, or preserving speaker notes — even if they do not say "convert". Not for authoring new presentations from scratch.
---
# Image to Editable PPT

## Overview

This skill rebuilds visual slide inputs into object-level editable PowerPoint `.pptx` files.

Inputs can be a single image, multiple images, a PDF, or an image-based PPT/PPTX. The output is always `.pptx`. The goal is not to wrap a full-slide screenshot inside PowerPoint; the goal is to use the `editppt` runtime and page-level prompts to decompose, reconstruct, validate, and assemble editable slides.

## References

- `prompts/page-worker.md`: execution template for page workers. The parent agent uses it when generating page-worker prompts.
- `scripts/build-page-worker-prompt.py`: skill-local prompt builder. It reads `prompts/page-worker.md`, fills run/page paths, writes `worker-prompt.md`, and prints the dispatch command template.
- `references/cli-helper.md`: CLI install check (Pre-Run Check), command tree, and common command examples. Read it when deciding which `editppt` command to call.
- `references/manifest-schema.md`: JSON schemas and artifact contracts for deck/page/image jobs. Read it when writing manifests, writing `page_result.json`, or understanding run/page files.
- `references/page-decision-tree.md`: the single source of truth for page object decisions. Read it before reconstructing any page.
- `references/qa-rubric.md`: structural, text, asset, background, and visual QA standards. Read it before a page returns and before final delivery.

## Entry Contract

These rules are stated once here; the workflow and references below build on them without restating them.

- The `editppt` CLI is a required runtime surface. If `editppt --help` fails, install it first by following the Pre-Run Check in `references/cli-helper.md` before doing anything else.
- First run `editppt prepare <input...>` to create a run directory. After that, all key state transitions are advanced only through `editppt` commands; never hand-write run/page state JSON. This keeps run state deterministic and resumable.
- After `prepare`, determine the actual page count. When it is 1, the parent agent rebuilds that page directly. When it is greater than 1, the parent agent only orchestrates and must dispatch every page to a real subagent/page worker. If no subagent capability is available, stop and report this to the user; do not degrade into serial parent-agent page reconstruction.
- In multi-page runs the parent agent must not write any page reconstruction artifact — `manifest.json`, `page.pptx`, `preview.png`, `split_assets_contact.png`, `validation.json`, or `page_result.json`. These files may only be produced by the page worker that owns the page directory.
- All image generation, image editing, background repair, transparent bitmap assets, and asset sheets go through `editppt image generate/edit/batch`.
- Page object decisions — background handling, foreground asset separation, native shapes, LaTeX formulas — follow `references/page-decision-tree.md`. In particular, foreground visual objects (photos, screenshots, illustrations, icons, pictograms, logo-like marks, badges, trend/status icons) use source-faithful asset-sheet separation unless the tree explicitly classifies them as native structural shapes.
- There is no fallback mode for foreground visual objects. If a foreground photo, screenshot, illustration, icon, pictogram, logo-like mark, badge, sticker, hand-drawn mark, semantic symbol, or other visual object cannot be separated through the required asset-sheet workflow, the current page is blocked. Do not approximate it with native shapes, emoji, text symbols, or similar substitutes; do not crop it directly from `source.png`; do not mark the missing separation as a warning; do not record, finalize, or deliver that fallback.
- Deterministic validation is a structure gate, not a waiver for object-source decisions. `validation.json.passed=true` never makes a forbidden foreground fallback acceptable.
- `manifest.json` is the authoritative page build source for both page-level validation and final deck assembly. `page.pptx` must be generated from that manifest; a visually acceptable page PPTX produced by separate page-local code is not enough, because finalize rebuilds the deck from manifests.
- Positioned manifest objects carry source-pixel coordinates: `text_boxes[]` and `images[]` require `box_px`, non-line `shapes[]` require `box_px`, and line shapes require `points_px`. Missing coordinates are record/finalize failures.
- Text sizes and positions come from measurement: `editppt prepare` writes per-page `text_hints.json`/`text_hints.png` next to each `source.png`. The hints belong to the third reconstruction step — background and foreground asset decisions come first; fill `text_boxes` from the measured `box_px` and font sizes (tagging them with `"font_size_source": "measured"`), regenerating with `editppt page hints <page_dir>` when missing. Keep deterministic runtime fitting enabled as the overflow guard.
- Page workers are driven by prompts generated from `prompts/page-worker.md`.

## Roles

The parent agent owns orchestration and user interaction:

- Run `editppt prepare`. The image backend is chosen automatically (Codex OAuth first, then API fallback), so the normal path needs no extra backend configuration command.
- For a single-page input, rebuild the page directly and record the result with `editppt run record --agent-id main`.
- For a multi-page input, loop on `editppt run next` to obtain pages that need dispatch, generate worker prompts with `scripts/build-page-worker-prompt.py`, spawn page workers, record dispatches with `editppt run dispatch`, and record returned results with `editppt run record`.
- Assemble and validate the final PPTX with `editppt run finalize`, then report progress, the final path, and the validation result to the user.
- Do not repeat page-level visual QA that page workers already completed; `record` and `finalize` re-validate deterministically.

Each page worker owns exactly one `pages/page_NNN/` directory:

- Read only its own `page_request.json`, `source.png`, and the relevant references; write only inside its own page directory; use `page_request.json.image_backend`.
- Decide object sources with the page decision tree; generate or edit bitmaps with `editppt image generate/edit/batch`; render formula assets with `editppt formula render-latex`; record and process asset sheets with `editppt image import` and `editppt image process-sheet`.
- Build `page.pptx` and `preview.png` from `manifest.json`, write `manifest.json`, `page.pptx`, `preview.png`, `split_assets_contact.png`, `validation.json`, and `page_result.json`, and self-check the preview, contact sheet, and validation before returning. Page-local issues are fixed inside the current page by its author.
- Never edit `deck_manifest.json`, `page_jobs.json`, `notes_manifest.json`, the final PPTX, the original input, or any other page directory.

## Workflow

### Phase 1: Prepare

Read the prepare examples in `references/cli-helper.md` and the run/page file descriptions in `references/manifest-schema.md`.

```bash
editppt prepare <input...>
```

After this completes, there must be a run directory, `deck_manifest.json`, `page_jobs.json`, `notes_manifest.json`, and each page must have `source.png` plus `page_request.json`.

Prepare also writes per-page text hints. Whenever `editppt doctor` or prepare reports that no PaddleOCR token is configured (offline fallback), ask the user once before reconstructing any page: a free token from https://aistudio.baidu.com/account/accessToken stored via `editppt config --paddle-ocr-token <token>` makes the hints content-aware and noticeably improves text fidelity, and `editppt run hints <run>` regenerates the current run's hints in place. Tell the user the free personal quota is currently more than enough for this skill — applying is risk-free with no extra cost. Wait for their choice; if they decline or want to proceed, continue with the offline hints and do not ask again.

### Phase 2: Dispatch Pages

Determine the actual page count from `deck_manifest.json` or from `editppt run next <run> --json`.

When the actual page count is 1, the parent agent completes page outputs in `pages/page_001/`, then proceeds to Phase 3.

For multi-page inputs, read the run/dispatch examples in `references/cli-helper.md` and call repeatedly:

```bash
editppt run next <run>
```

When the dispatch stage is returned, the following steps are mandatory for each suggested page:

1. `python <skill-root>/scripts/build-page-worker-prompt.py <run> --page <page_id> --out <absolute-run-dir>/pages/<page_id>/worker-prompt.md`
2. Spawn a page worker using the current environment's available subagent/multi-agent tool.
3. `editppt run dispatch <run> --page <page_id> --agent-id <id> --prompt-file <absolute-run-dir>/pages/<page_id>/worker-prompt.md`

`--out` and `--prompt-file` must be absolute paths to avoid the page directory being prepended again to relative paths. The prompt builder only writes the prompt and prints a dispatch command template; it does not create the worker, so run `editppt run dispatch` only after a real spawn succeeds.

Concurrency slots come from `page_jobs.json.max_concurrent_pages` (default 6). In the normal flow prefer `editppt run next`; `editppt run status` is only for debugging or manual inspection.

### Phase 3: Record

Read the record examples in `references/cli-helper.md` and the `page_result.json` description in `references/manifest-schema.md`.

After a worker returns, run:

```bash
editppt run record <run> --page <page_id> --agent-id <id>
```

This command validates `page.pptx` against `manifest.json` before recording. It fails if positioned objects are missing source-pixel coordinates or if the manifest cannot independently rebuild the page.

For a directly rebuilt single-page input, use:

```bash
editppt run record <run> --page page_001 --agent-id main
```

### Phase 4: Finalize

Read the finalize examples in `references/cli-helper.md` and the deck-level QA points in `references/qa-rubric.md`.

When `editppt run next <run>` returns the finalize stage:

```bash
editppt run finalize <run>
```

`finalize` treats each recorded `pages/page_NNN/manifest.json` as the authoritative source: it rebuilds the final deck from page manifests in page order, then validates the resulting PPTX. `page.pptx` remains a page-level deliverability artifact for record-time checks.

The final reply must report the final PPTX path and validation result.

## State Principles

Agents continue only from file facts and `editppt run next`. Required states:

- `pending`: created by `editppt prepare`.
- `dispatched`: `editppt run dispatch` records a real spawned worker.
- `recorded`: `editppt run record` validates required outputs and writes the result; direct single-page reconstruction is also recorded through this command.
- `accepted` / `complete`: written by `editppt run finalize`.

`imagegen-jobs.json` is the page-local provenance/job record. Only these forced file states are kept:

- `recorded`: `editppt image import` has copied the selected output and written hash/metadata.
- `processed`: `editppt image process-sheet` has completed background removal and splitting.

## Delivery Principles

- Each page is self-checked once by the page reconstructor; the evidence is written into structured fields in `manifest.json` and into `validation.json`.
- The final output must be a currently openable, structurally valid `.pptx`. A full-slide `source.png` with editable text overlaid on top is not an acceptable fallback.
- Warnings are allowed only after the required object-source workflow has succeeded. A warning may describe small visual drift in an already separated asset or low-risk font differences; a warning may never replace a missing required workflow step.
- Minor drift in icons, bitmap assets, fonts, positions, shapes, and similar details may be delivered as warnings only after the object-source decision follows the page decision tree. Missing asset edges, forbidden source types for foreground assets, native approximations of foreground visuals, emoji/text-symbol substitutes, or replacing required asset-sheet separation with a direct source-image snippet are current-page failures, not warnings.

## Updating This Skill

Reinstall through the installation channel, refresh the CLI from the updated skill directory, then restart the agent session and verify:

```bash
npx -y skills@latest add ningzimu/image-to-editable-ppt-skill \
  --skill image-to-editable-ppt \
  --agent <agent-id> \
  --global
pipx install --force --editable <skill-root>/cli
editppt doctor
```
