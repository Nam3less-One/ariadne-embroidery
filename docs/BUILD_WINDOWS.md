# Build the Windows installer

Build on Windows x64 using an isolated Python environment containing Ariadne's runtime dependencies and PyInstaller 6.22.2. No cloud service, API key or commercial packager is needed. The output contains a per-user setup wizard, Start menu entries and an uninstaller. The app runs without a separately installed Python interpreter.

Obtain NSIS 3.12 from its [official download page](https://nsis.sourceforge.io/Download) or the Chocolatey `nsis.portable` 3.12.0 package. The official ZIP SHA-256 is `56581f90db321581c5381193d796fffcf2d24b2f8fed2160a6c6a3baa67f2c4f`. Extract the compiler; do not execute Chocolatey scripts when only extraction is needed.

This build uses Shapely 2.1.2 with GEOS 3.13.1. Download the [corresponding GEOS source](https://download.osgeo.org/geos/geos-3.13.1.tar.bz2) and [Tcl license](https://raw.githubusercontent.com/tcltk/tcl/core-8-6-15/license.terms). The packager copies these plus dependency, Python and Tk license notices into the installed application. GEOS stays in replaceable DLLs. When changing dependencies, review bundled native libraries and update the corresponding source and notices.

```console
python -m pip install . pyinstaller==6.22.2
python tools/windows/build_windows.py --output NEW_OUTPUT_FOLDER --nsis PATH/TO/makensis.exe --geos-source PATH/TO/geos-3.13.1.tar.bz2 --tcl-license PATH/TO/tcl-license.terms
```

The output folder must not exist. Build logs, a frozen app folder, setup EXE, component inventory and checksum are produced. `Ariadne.exe --self-test NEW_TEST_FOLDER` runs a bundled Tk workflow: creates artwork on white paper with a hole, two colors and a thin rule, previews and converts at one, two and four requested colors, checks stale-proof invalidation, saves PES/DST, decodes the proof and records the results. No installed Python or network access is used by that test.

`python tools/windows/verify_installer.py SETUP_EXE NEW_TEST_FOLDER --no-integration` tests extraction, the installed executable and uninstall without changing an existing Ariadne registration or Start menu shortcut. The installer flag `/NOINTEGRATION` is reserved for this isolated test. Without the flag, the verifier requires an account without Ariadne and also checks normal registration and shortcut creation. Always test normal installation or upgrade separately before publishing.

Before distributing, test the final setup EXE, installed app, Start menu entry and uninstaller. Check that an unrecognized file survives uninstall. Inspect the visible UI as well as running the bundled self-test. Archive the exact build scripts and component inventory beside the binary. The current setup is unsigned; do not disable operating-system security protections as part of setup or testing. A test sew is still required for embroidery production.
