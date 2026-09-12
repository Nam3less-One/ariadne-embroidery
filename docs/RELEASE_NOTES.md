# Ariadne Embroidery Studio 0.1.1

A free, open-source local tool for turning simple artwork into editable embroidery drafts and real PES/DST files.

This update fixes the multi-color `cannot convert float NaN to integer` failure and one-color background collapse. Background selection now happens before thread reduction; similar edge shades no longer create unnecessary thread changes. Empty underlay geometry is handled safely. Covered fill transfers reduce short stitches, and simple narrow straight bars use satin.

The redesigned studio separates artwork preview from decoded stitch proof, displays actual thread counts, provides a one-thread color picker, and clears stale results after settings change. Width can fit cropped artwork. Advanced stitch settings have a separate dialog; Open output folder leads directly to the exported bundle.

**Windows users:** download `Ariadne-0.1.1-Windows-x64-Setup.exe`. It includes Python and required libraries, installs for your account, and runs offline. The installer is unsigned. Source ZIP, wheel and sdist are also available; Ariadne code is MIT licensed. No account or paid service is required to use it.

Independent digital critics drove repeated source/proof and actual desktop GUI reviews. Four original test designs reached at least 8/10 digitizing quality, and the GUI reached 8.2/10. Exact examples, scores and limitations are recorded in `examples/quality-0.1.1/review.md` and `docs/VALIDATION.md`.

**Review and test sew every design.** Tiny text, photographs and complex artwork still need skilled digitizing. Low-resolution text fringes can produce ambiguous colors; use one thread and a chosen color for monochrome artwork. No physical sew-out or machine certification is claimed. DST requires the supplied thread chart and machine-specific trim verification.
