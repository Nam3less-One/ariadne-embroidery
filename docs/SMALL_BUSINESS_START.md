# Start here: Ariadne for a small embroidery business

Ariadne creates editable embroidery drafts from simple artwork and exports PES and DST files. Its MIT license permits business use, modification and sharing; retain required notices when redistributing the software. You still need permission to use imported artwork, fonts and logos.

## Is this release right for you?

Version 0.1.0 is an early-access **Python/source release**. It includes a desktop app, but you must install Python and the package first. A standalone Windows installer is not included. For advanced lettering and visual editing, [Ink/Stitch](https://inkstitch.org/) is another free open-source option to investigate.

Start with a few solid colors, large clear shapes and a transparent background. Photographs, gradients and tiny text require significant editing and experienced digitizing.

## Choose the right file

| Download | Purpose |
| --- | --- |
| `ariadne-embroidery-0.1.0-source.zip` | First-time installation with examples and instructions |
| `ariadne_embroidery-0.1.0-py3-none-any.whl` | Installation by someone familiar with Python packages |
| `ariadne_embroidery-0.1.0.tar.gz` | Source packaging and developer workflows |
| `SHA256SUMS.txt` | Verify release file checksums |

If you downloaded the combined release ZIP, extract it, then extract the source ZIP inside. The folder containing `README.md` and `pyproject.toml` is the source folder. Do not send the program ZIP to an embroidery machine: only the exported machine file belongs there.

## Install once on Windows

Install Python 3.11 or newer from [python.org](https://www.python.org/downloads/), including Tk support. Open a terminal in the extracted source folder:

```console
python -m venv .venv
.venv\Scripts\python -m pip install .
.venv\Scripts\ariadne-studio
```

Installation downloads open-source dependencies. Conversion runs locally afterward. In future sessions, run `.venv\Scripts\ariadne-studio` from the same folder. See the [README](../README.md) for macOS and Linux commands.

## Make your first sample

Open `examples/geometric-mark.png`. Set width to 80 mm, colors to 2 and fill spacing to 0.4 mm, leaving support underlay enabled. Choose **Create PES + DST bundle**, then a parent folder. Ariadne creates a new output folder and shows the decoded PES proof.

Width describes the entire image canvas, including transparent margins. The example's shapes occupy less space than its 80 mm canvas. Read the actual machine travel dimensions before selecting a hoop.

The output contains `design.pes`, `design.dst`, a thread chart, editable `plan.json`, proofs and setup notes. Use the format supported by your machine. A matching extension alone does not establish hoop or machine compatibility.

## Before sewing a customer order

Compare artwork against the decoded proof and needle image. Check edges, missing small regions, holes, letters, colors and dense stitch clusters. The travel view shows jumps, including movement between separate shapes.

Read `SETUP.txt` and `review.json`. Verify the full travel fits the usable hoop area. Assign DST colors using `threads.json`; DST does not embed that palette. Confirm how your machine handles the three-jump trim convention.

Test sew on the intended fabric with matching stabilizer, thread and needle. Check coverage, distortion, registration, thread breaks, trim tails and puckering. Adjust the plan and export into a new folder. Every new design remains a draft until reviewed; the included example's score is not approval of customer artwork.

## Get help

Use the issue form in the repository that distributes your copy. Include version, operating system, settings, exact error and a small image you have permission to share. Public issues are not suitable for private customer files or account details. If sharing a test-sew photo, describe the machine and materials.

Automated tests and previews catch some file errors. They cannot establish how a design sews on your materials. See [quality and review boundaries](QUALITY.md).
