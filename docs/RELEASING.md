# Releasing Ariadne

## Build from the source folder

Install development dependencies in a virtual environment, run `python -m pytest`, then `python -m build` and `python -m twine check dist/*`. Test the wheel in a fresh environment: launch the GUI and run a conversion without the source tree on `PYTHONPATH`.

Build outputs are an sdist and a pure-Python wheel. Runtime dependencies are installed separately. Do not describe these as a standalone executable or upload bundled dependencies without their required license notices.

Run `python tools/package_release.py NEW-release-folder` after building to assemble the source ZIP, wheel, sdist, source manifest and SHA-256 checksums. The source ZIP uses an explicit public-file whitelist and does not include the parent studio workspace.

## Prepare the public repository

Publish only this `ariadne-converter` folder. The parent studio workspace contains private design history and is not part of the release. The source release intentionally excludes existing customer logos and local tool data.

Create the chosen public repository, push this source as its root, and run the provided CI workflow. Verify the repository owner's identity and intended destination before publishing. Do not invent a GitHub owner or release URL. No repository, package-index account or publishing token is embedded in this project.

## Release checklist

- Read the validation report and ensure it refers to the exact source version being released.
- Run Windows/Linux CI and record which environments actually passed. Run the Tk GUI checks with a display.
- Review licensing, original sample provenance, archive contents and dependency notices.
- Confirm the README matches the shipped capabilities and keeps draft/sew-out limitations visible.
- Create the version tag for the reviewed commit and attach the Windows installer, source ZIP, wheel, sdist and SHA-256 checksums to a GitHub release. Build and verify the installer using `docs/BUILD_WINDOWS.md`.
- Use the release description in `docs/RELEASE_NOTES.md`; update any candidate language after publishing.

The CI workflow builds downloadable artifacts but does not automatically publish to PyPI or create releases. Optional PyPI publication requires an available package name and the maintainer's account configuration; installation from the supplied wheel works without PyPI hosting.
