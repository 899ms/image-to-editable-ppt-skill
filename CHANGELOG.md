# Changelog

Release notes are generated from this file. Keep changelog entries in English.

## Unreleased

### Features

- Expand the image-to-editable-ppt skill to normalize images, PDFs, and PPT/PPTX inputs into page jobs, assemble deck manifests into multi-page PPTX files, and preserve PPT/PPTX speaker notes.
- Add skill-local runtime management scripts and dependencies for input preparation, deck assembly, and validation.

### Fixes

- Reject page manifests that combine a full-slide source raster background with editable text overlays, preventing baked-text overlap from passing validation.

### Documentation

- Add repository README files, contribution guidance, changelog, license, PR template, and lightweight GitHub checks.
- Add README badges for language switching, GitHub stars, and GitHub forks.
- Document mandatory one-subagent-per-page dispatch for multi-image, PDF, and PPT/PPTX conversions, including the required blocker behavior when subagents are unavailable.
- Clarify that dashboard and dense infographic pages require an explicit `$imagegen` gate decision, and that style-bearing icons or pictograms must use `$imagegen` assets unless the user approves a downgrade.
- Document that preview-visible crude or placeholder-like icons are blockers that require targeted `$imagegen` asset repair before reporting completion.
- Require page manifests to declare `completion_status` and document the clean `editable-layout-draft` fallback for cases where the user explicitly prefers a usable low-fidelity output while `$imagegen` is unavailable.
