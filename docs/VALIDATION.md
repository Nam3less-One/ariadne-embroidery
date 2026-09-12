# Release validation — 0.1.1

## Regression and GUI checks

Windows, CPython 3.14.4, Tk 8.6: **53 tests passed with no skips**. This includes 36 color/geometry regression cases and three real Tk worker tests. Coverage includes one/two/four-color exports, collapsed underlay, empty thread groups, finite coordinates, PES/DST round trips, preserved counters, background selection before quantization, shading, sparse raster strokes, explicit swatches, invalid settings, preview invalidation, export recovery and output-folder access.

A separate diagnostic critic checked 20 curved routing cases at five angles, including a 0.2 mm ring: every segment stayed within geometry plus 0.000001 mm and obeyed the configured 3 mm limit. A test isolation issue was corrected by sharing one Tk interpreter and using fresh windows, matching the real app; unexpected Tcl initialization errors are no longer silently skipped as unavailable displays.

An independent critic inspected the actual Windows app, including file selection, one-thread preview, export with multiple colors allowed, stale-result clearing and output-folder launch. The GUI improved from **4.5/10** to **8.2/10** after an intermediate 7.5 review identified clipped controls and low-contrast palette labels. The final normal and minimum layouts and separate advanced-settings dialog were screenshot-reviewed. Source and prepared images fit independently; synchronized zoom and a graphical object editor remain future work.

## Independent embroidery review

Four original inputs, including one generated GROW graphic, were repeatedly exported and freshly decoded. Critique drove stable palettes, fewer short edge stitches, covered transfers and satin on a bounded straight bar. An intermediate routing revision was rejected when it increased short stitches. Final checks ran twelve one/multi-color cases; the exact four default results below and their hashes are included in [the reviewed examples](../examples/quality-0.1.1/review.md).

| Default sample | Source fidelity / 10 | Digitizing quality / 10 |
|---|---:|---:|
| Ring-arrow | 8.7 | 8.1 |
| Three-color botanical | 8.7 | 8.2 |
| Narrow monogram | 8.2 | 8.0 |
| Generated GROW | 8.5 | 8.0 |

Setup: 100 mm cropped artwork width, automatic background, margin trimming on, up to four threads, 0.42 mm row spacing and underlay on. Scores apply only to those exact digital files. GROW retains about 5.8% positive stitches below 0.2 mm and is about 100 × 109.9 mm before trim travel; it requires a larger usable hoop than 100 × 100 mm.

A private 186 × 79 pixel equation screenshot reproduced the reported crash. It now exports at one, two and four colors, but its tiny lettering remains below the professional gate: independent monochrome quality assessments were 5.5 and 6.5/10. Extra threads can misinterpret colored text-rendering fringes and fragment letters. The app warns about thin raster strokes and low resolution; use one chosen thread for monochrome artwork and larger original artwork or manual lettering for a credible finished design. The private source is excluded from the release.

**No physical sew-out was performed.** These scores do not certify tension, fabric behavior, registration, machine compatibility or arbitrary future designs. Every automatic result remains an unreviewed draft.

## Windows distribution

The exact 0.1.1 x64 installer was built with PyInstaller 6.22.2 and NSIS 3.12. Its isolated installation test passed with existing app registration preserved. The installed frozen runtime, with external Python/Tcl environment variables removed and PATH restricted to Windows System32, completed real GUI-worker previews and PES/DST exports at requested color limits 1, 2 and 4. Actual thread counts were 1, 2 and 2. Uninstall removed installed files while preserving an unrelated test file. The release's WINDOWS-VALIDATION.json and checksums identify the tested installer.

The installer includes Python, required libraries, dependency notices and corresponding GEOS source. It is unsigned and installs per user. Source ZIP, sdist and pure-Python wheel are separate distributions. The public source whitelist excludes private studio images, browser profiles, credentials and local absolute paths.

Windows/Linux CI on Python 3.11 and 3.14 is configured in the repository. Consult the Actions run for the release commit for its actual status; headless hosts explicitly skip GUI display checks. No macOS execution or physical machine result is claimed. The earlier 0.1.0 geometric review remains available as historical evidence in examples/reviewed-geometric; it is not the new default sample setup.
