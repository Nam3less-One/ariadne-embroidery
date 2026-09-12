# Ariadne Embroidery Studio

**A free, offline image-to-embroidery drafting tool.** Open artwork, create editable stitch objects, and export real PES and DST files with decoded proofs. No account, subscription, paid API, telemetry or cloud upload.

Ariadne 0.1 is a geometry-based converter, not a trained AI model. Automatic raster import produces **draft fill embroidery**, best suited to simple, flat-color artwork. It does not automatically create professional satin lettering, infer fabric behavior or certify production readiness. Explicit paired satin rails are supported in editable plans.

## Install and launch

**Windows:** [Download the Windows x64 installer](https://github.com/Nam3less-One/ariadne-embroidery/releases/download/v0.1.0/Ariadne-0.1.0-Windows-x64-Setup.exe), run it, then open **Ariadne** from the Start menu. Python and the required libraries are included. Requires 64-bit Windows 10 or newer; this installer is unsigned.

Start with the [small-business guide](docs/SMALL_BUSINESS_START.md). Version 0.1.0 is early access; every design needs review and test sewing.

### Install from source (developers, macOS and Linux)

Requires Python 3.11 or newer. Windows Python normally includes Tk; Linux distributions may require their `python3-tk` package. Installation downloads open-source dependencies once; conversion then works offline.

Download and extract the source release. In its folder:

```console
python -m venv .venv
```

Windows:

```console
.venv\Scripts\python -m pip install .
.venv\Scripts\ariadne-studio
```

macOS / Linux:

```console
.venv/bin/python -m pip install .
.venv/bin/ariadne-studio
```

Or install the supplied wheel with `python -m pip install path/to/ariadne_embroidery-0.1.0-py3-none-any.whl`, then run `ariadne gui`. The source archives and wheel are separate from the Windows installer.

## Make a design

1. Open PNG, JPEG, WebP, BMP or TIFF artwork. Transparent pixels remain unstitched; alpha below 128 is treated as transparent. Crop screenshot margins before importing.
2. Set canvas width, color count, fill spacing and direction. Width includes transparent margins. The actual stitch and travel dimensions appear in the exported audit.
3. Choose **Create PES + DST bundle** and a parent directory. Each result gets a new folder; previous designs are preserved.
4. Inspect decoded proof, needle and travel images. Read `SETUP.txt` and `review.json`, verify the usable hoop area and thread order, and test sew on matching materials.

`Exclude top-left palette color` omits **every region** assigned that palette color, including interior regions. It is not background recognition. Start with a transparent source when possible.

## Command line

```console
ariadne convert examples/geometric-mark.png my-design --width 80 --colors 2 --spacing 0.4
ariadne convert artwork.png pes-only --width 100 --format pes
ariadne trace artwork.png plan.json --colors 3 --angle 45
ariadne export plan.json revised-design --format pes dst
ariadne export examples/satin-plan.json satin-demo
```

Every conversion bundle contains:

| File | Purpose |
| --- | --- |
| `plan.json` | Editable geometry, object sequence, fill settings and thread choices, in mm |
| `stitch-master.json` | Lossless pyembroidery stitch master for future export work |
| `objects.json` | Object spans in the unencoded master |
| `design.pes`, `design.dst` | Machine embroidery files, encoded independently |
| `threads.json` | Operator thread order; essential for DST |
| `design-*-proof.png` | Actual decoded stitches with illustrative thread spread |
| `design-*-needle.png`, `design-*-travel.png` | Needle paths and pink jump movements |
| `design-*-audit.json`, `review.json` | Hashes, lengths, dimensions, counts and review status |
| `SETUP.txt` | Setup assumptions and review instructions |

DST does not embed the displayed colors. Three-jump trim requests depend on machine settings; check your machine's behavior. The DST header record count is checked after trim expansion. A PES decoder may expose extra zero-length transition stitches; the audit reports them rather than editing format-specific transitions away.

## Python API

```python
from ariadne_embroidery import Settings, convert_image

convert_image("artwork.png", "new-bundle", Settings(width_mm=100, colors=3))
```

See [editable plans](docs/PLANS.md), [limitations and review](docs/QUALITY.md), [contributing](CONTRIBUTING.md), and [release instructions](docs/RELEASING.md).

## Free to use, modify and share

New Ariadne code and original geometric examples are licensed under the [MIT License](LICENSE), including commercial use. Dependencies retain their own licenses; see [third-party notices](THIRD_PARTY_NOTICES.md). You retain responsibility for rights to artwork you import. No private project artwork, third-party logos, generated concept images, credentials or conversation history are included.

PES/DST encoding is provided by [pyembroidery](https://github.com/EmbroidePy/pyembroidery). Ariadne provides the geometry and stitch planning above that encoder. Physical machine testing remains necessary for each design.
