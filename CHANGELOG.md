# Changelog

## 0.1.1 — 2026-09-12

- Fixed the NaN crash caused by narrow regions whose underlay collapses to empty geometry.
- Remove background pixels before choosing thread colors, preserving one-color silhouettes and counters.
- Choose substantive foreground hues instead of allocating threads to antialias fringes; merge similar shading and retain actual color counts.
- Restore half-coverage outlines on light paper, skip unusable thread groups, and simplify covered edge transfers without crossing holes.
- Recognize simple narrow rectangular bars for satin and avoid sparse text-edge pixels dominating the one-thread palette.
- Added automatic/keep/corner background modes, optional margin trimming, and a one-thread color picker.
- Added prepared-artwork preview, separate decoded stitch proof, output-folder access, stale-result invalidation and fine-detail warnings.
- Improved fit-to-view image scaling and moved advanced stitch settings into a separate dialog for small windows.
- Added independent regression fixtures and GUI workflow checks. See the release validation document for exact review scores and limits.

## 0.1.0 — 2026-09-12

Initial public source release candidate.

- Local Tk desktop studio, command line and Python API.
- Transparent raster tracing, color reduction, editable fill polygons and explicit satin rails.
- Directional tatami, support underlay, bounded stitches, securing paths and trimmed transfers.
- Real PES/DST export, DST record-count correction, external thread chart and editable master.
- Fresh decoded proof, needle and travel images with file hashes and machine metrics.
- Original examples, regression tests, build metadata, CI and MIT licensing.

All automatic designs are drafts requiring independent review and physical sew-out. Public hosting and broader platform CI must be verified before describing a release as published or cross-platform tested.
