# Release validation — 0.1.0

## Local verification

Environment: Windows, CPython 3.14.4, Tk 8.6. The automated suite passes 15 tests, covering transparency, color assignment, hole retention, fill routes at four angles, malformed settings, format rejection, non-overwrite behavior, failed-bundle cleanup, satin export, machine-file round trips, raw DST extents/counts and suppression of duplicate DST penetrations.

The Tk workflow test opens original sample artwork, runs the real conversion worker, decodes its result, populates the proof panel and clears stale results when new artwork is opened. The desktop automation service did not expose the running app window, so a manual/screenshot desktop layout review is still outstanding. This is distinct from the independently captured machine-file proof screenshot below.

The CI matrix is provided for Windows and Linux, Python 3.11 and 3.14. Remote CI has not run before public repository creation. On hosts without a display the Tk test is explicitly skipped. No macOS or physical embroidery machine result is claimed.

## Independent embroidery review

The original geometric example was revised across three independent reviews: quality 6.6, then 7.3, then **8.0/10**, with final source fidelity **8.4/10**. The fixes reduced trims, removed duplicate DST penetrations, and corrected DST extents to include raw trim movements.

The exact reviewed files, screenshots, advice and hashes are in [the example review](../examples/reviewed-geometric/review.md). It uses an 80 mm-wide canvas and 0.4 mm row spacing. The actual raw machine travel is 65.5 × 54.0 mm because the original image has transparent margins. The sample retains 258 positive stitches below 0.2 mm; reducing short edge fragments remains future refinement. No physical sew-out has been performed.

Scores apply only to the included sample. New app output remains an unreviewed draft regardless of those scores.

## Distribution boundary

The source ZIP/sdist and pure-Python wheel include only Ariadne source, documentation and original geometric examples. Runtime dependencies are installed separately. Private studio artwork, previous third-party logos, browser profiles, credentials and local absolute file paths are excluded. Build and installed-wheel checks are recorded alongside release artifacts.

The wheel was installed into a separate virtual environment with its declared dependencies; `pip check`, the installed command-line entry point and a complete sample conversion passed. The installed wheel regenerated the reviewed PES/DST byte-for-byte. Both wheel and sdist pass `twine check` metadata validation. Installation required a network step for dependencies; the subsequent wheel install and conversion were performed offline.
