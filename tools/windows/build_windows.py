"""Build a self-contained Windows x64 app and per-user NSIS installer.

Run with the same virtualenv that contains Ariadne and PyInstaller 6.22.2.
Inputs are explicit; output must be new. No download or system installation occurs.
"""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ["ariadne-embroidery", "Pillow", "numpy", "scipy", "shapely", "scikit-image",
           "pyembroidery", "networkx", "imageio", "tifffile", "lazy_loader", "packaging"]


def copy_notices(output, geos_source, tcl_license, nsis):
    licenses = output / "licenses"
    licenses.mkdir()
    inventory = []
    for name in RUNTIME + ["pyinstaller"]:
        dist = metadata.distribution(name)
        target = licenses / f"{dist.metadata['Name']}-{dist.version}"
        target.mkdir()
        for file in dist.files or []:
            parts = Path(str(file)).parts
            if any("dist-info" in p for p in parts) and (
                "licenses" in parts or any(w in Path(file).name.lower() for w in ("license", "copying", "notice"))
            ):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    rel = Path(*parts[next(i for i, p in enumerate(parts) if "dist-info" in p) + 1:])
                    dest = target / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
        (target / "METADATA.txt").write_text(dist.read_text("METADATA") or "", encoding="utf-8")
        inventory.append({"name": dist.metadata["Name"], "version": dist.version})
    shutil.copy2(Path(sys.base_prefix) / "LICENSE.txt", licenses / "Python-LICENSE.txt")
    shutil.copy2(tcl_license, licenses / "Tcl-license.terms")
    shutil.copy2(Path(sys.base_prefix) / "tcl/tk8.6/license.terms", licenses / "Tk-license.terms")
    shutil.copy2(nsis.parent / "COPYING", licenses / "NSIS-COPYING.txt")
    source_dir = licenses / "corresponding-source"
    source_dir.mkdir()
    shutil.copy2(geos_source, source_dir / geos_source.name)
    (licenses / "GEOS-RELINKING.txt").write_text(
        "GEOS 3.13.1 is LGPL-2.1 and dynamically linked through Shapely. Its complete upstream source is\n"
        "in corresponding-source/geos-3.13.1.tar.bz2, including CMake build instructions.\n"
        "The replaceable GEOS DLLs are in _internal/shapely.libs. You may modify and replace them\n"
        "with ABI-compatible builds, and reverse engineer this application to debug such modifications.\n"
        "Ariadne imposes no restriction on those rights. Other components keep their own licenses.\n",
        encoding="utf-8")
    (output / "COMPONENTS.json").write_text(json.dumps({
        "python": platform.python_version(), "platform": platform.platform(), "components": inventory,
        "geos_source_sha256": hashlib.sha256(geos_source.read_bytes()).hexdigest(),
    }, indent=2), encoding="utf-8")


def nsis_quote(value):
    return str(value).replace("$", "$$").replace('"', '$\\"')


def build(args):
    if sys.platform != "win32" or platform.machine().lower() not in ("amd64", "x86_64"):
        raise SystemExit("Build on Windows x64 with x64 Python")
    args.output.mkdir(parents=True, exist_ok=False)
    frozen = args.output / "frozen"
    work = args.output / "work"
    work.mkdir()
    env = dict(os.environ, PYINSTALLER_CONFIG_DIR=str(work / "cache"))
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--onedir",
               "--name", "Ariadne", "--distpath", str(frozen), "--workpath", str(work / "pyinstaller"),
               "--specpath", str(work), "--paths", str(ROOT / "src"),
               "--collect-all", "pyembroidery", "--copy-metadata", "scikit-image",
               str(Path(__file__).with_name("launcher.py"))]
    with (args.output / "build.log").open("w", encoding="utf-8") as log:
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    app = frozen / "Ariadne"
    copy_notices(app, args.geos_source, args.tcl_license, args.nsis)
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / name, app / name)
    shutil.copy2(ROOT / "docs/WINDOWS_START.txt", app / "START-HERE.txt")
    shutil.copytree(ROOT / "examples", app / "examples", ignore=shutil.ignore_patterns("__pycache__", "*.py"))
    # Only delete files installed by this exact package; never recursively delete the app folder.
    files = sorted(p for p in app.rglob("*") if p.is_file())
    lines = [f'Delete "$INSTDIR\\{nsis_quote(p.relative_to(app))}"' for p in files]
    dirs = sorted((p for p in app.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True)
    lines += [f'RMDir "$INSTDIR\\{nsis_quote(p.relative_to(app))}"' for p in dirs]
    uninstall = work / "uninstall-files.nsh"
    uninstall.write_text("\n".join(lines), encoding="utf-8")
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    setup = args.output / f"Ariadne-{version}-Windows-x64-Setup.exe"
    command = [str(args.nsis), f"/DAPP_DIR={app}", f"/DOUTPUT_FILE={setup}",
               f"/DAPP_VERSION={version}", f"/DUNINSTALL_FILES={uninstall}", str(Path(__file__).with_name("installer.nsi"))]
    with (args.output / "installer-build.log").open("w", encoding="utf-8") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    (args.output / "WINDOWS-SHA256SUMS.txt").write_text(
        f"{hashlib.sha256(setup.read_bytes()).hexdigest()}  {setup.name}\n", encoding="utf-8")
    print(setup)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "nsis", "geos-source", "tcl-license"):
        parser.add_argument("--" + name, required=True, type=lambda s: Path(s).resolve())
    build(parser.parse_args())
