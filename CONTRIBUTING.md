# Contributing

Contributions are welcome under the MIT License. Keep the engine usable offline, preserve editable masters, and never present an illustrative rendering as a real sew-out.

```console
python -m venv .venv
python -m pip install -e ".[dev]"
python -m pytest
python -m build
python -m twine check dist/*
```

Activate the virtual environment first, or use its full Python path. Tests use only original synthetic fixtures. Do not add third-party logos, private artwork, credentials, machine profiles containing personal data, generated browser profiles or local absolute paths.

For a digitizing change, include a small original fixture, decoded before/after proofs, relevant invariant checks, and a clear explanation of visual tradeoffs. Preserve holes, avoid stitched transfers outside shapes, obey stitch-length limits, and round-trip every changed encoder. Report physical sew-outs separately from digital review.

For new formats, implement a real encoder adapter and verify color sequence, hoop/travel bounds, trims and final END. File-extension renaming is not conversion. Changes to plan semantics must retain version compatibility or introduce a new explicit schema version.

Open an issue or pull request in the public repository that distributes your copy. Include the Ariadne version, Python/OS, exact settings, traceback and a redistributable minimal example. Do not attach private customer artwork without permission.
