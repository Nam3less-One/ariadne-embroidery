# Quality and review boundaries

Ariadne 0.1 is useful for drafting flat-color shapes and for experimenting with explicit stitch objects. It is not a replacement for an experienced digitizer or physical machine validation. An attractive rendered proof does not establish density, tension, registration, thread breaks or puckering on fabric.

Automatic conversion deliberately starts at `draft_requires_review` with no independent score. It does not fabricate a critic, assign itself a passing score, or mark a design production-ready. No model weights or paid image-generation service are part of this release.

## Inspect every design

Compare the source against the decoded proof and needle path. Check retained detail, letter counters, edges, color assignment, object sequence, underlay and excessive short stitches. The travel view highlights jumps in pink; trimmed movements are still visible. Review the audit's travel bounds against the hoop's usable sewing area, not only the artwork width.

Use the thread chart to set the machine, particularly for DST. Confirm three-jump trim behavior on the specific machine. Test sew using the intended fabric and stabilizer, then adjust spacing, direction, object geometry and routing as needed. Satin typically needs material-specific compensation; no automatic compensation is currently applied.

## Matt's independent review workflow

The original studio workflow can be used around this free engine:

1. Create several embroidery finish concepts from source artwork and have an independent reviewer score source fidelity and credible stitch construction. Select the strongest concept scoring above 7/10; otherwise revise concepts.
2. Plan editable geometry from original artwork, using the selected concept as a finish target. Generated thread texture is not geometry.
3. Export, freshly decode, and have a separate reviewer capture and inspect a screenshot of the actual stitch rendering. Score similarity and digitizing quality independently; revise any score below 8/10.
4. Preserve revisions, critique, file hashes and physical sew-out results.

This app automates tracing, planning, encoding and proof generation. Concept generation, independent criticism and sew-outs remain external steps; users may use human reviewers or their own agent tooling. The free app does not require or silently call any service. The release example review, when included, evaluates that exact sample and does not certify arbitrary images.

## Known limitations in 0.1

- Photographs, gradients, tiny text and detailed multicolor artwork can trace poorly. Simplify artwork and inspect discarded regions.
- Raster import produces fills and recognizes nearly rectangular straight bars for satin. Compound lettering still requires manually planned columns; general automatic column inference is future work.
- Tiny screenshots can contain colored text-rendering fringes. For monochrome art, use one thread and choose its color. Low-resolution geometry cannot be restored by enlarging the screenshot.
- Fills use a single angle per object. Boundary routing reduces trims but may accumulate stitches around counters. Audit and adjust challenging geometry.
- No automatic pull compensation, fabric simulation, hoop database, machine connection, thread-brand matching or batch background monitoring.
- No graphical object editor, SVG/PDF import, physical machine certification or signed executable.
- PES and DST are the supported exports. Adding another encoder requires its own bounds, thread, trim and round-trip tests.
