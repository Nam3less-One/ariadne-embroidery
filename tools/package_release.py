"""Assemble a shareable source ZIP, built distributions and checksums.

Run after `python -m build`. A whitelist keeps local artifacts out of the ZIP.
Existing output folders are never overwritten.
"""
import argparse
import hashlib
import json
import shutil
import tomllib
import zipfile
from pathlib import Path


def package(output):
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root/"pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    root_files = {"pyproject.toml", "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "CHANGELOG.md", "CONTRIBUTING.md", "MANIFEST.in", ".gitignore"}
    directories = {"src", "docs", "examples", "tests", "tools", ".github"}
    extensions = {".py", ".md", ".json", ".png", ".txt", ".pes", ".dst", ".yml", ".nsi"}
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part == "__pycache__" or part.endswith(".egg-info") for part in rel.parts):
            continue
        if str(rel) in root_files or (rel.parts[0] in directories and path.suffix in extensions):
            files.append(path)
    distributions = [root/"dist"/f"ariadne_embroidery-{version}-py3-none-any.whl", root/"dist"/f"ariadne_embroidery-{version}.tar.gz"]
    if not all(path.is_file() for path in distributions):
        raise SystemExit("Build the wheel and sdist first: python -m build")
    output.mkdir(parents=True, exist_ok=False)
    archive = output/f"ariadne-embroidery-{version}-source.zip"
    manifest = []
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for path in files:
            rel = path.relative_to(root).as_posix()
            data = path.read_bytes()
            info = zipfile.ZipInfo(f"ariadne-embroidery-{version}/{rel}", date_time=(2026, 9, 12, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zip_file.writestr(info, data)
            manifest.append({"path": rel, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    for path in distributions:
        shutil.copyfile(path, output/path.name)
    shutil.copyfile(root/"docs"/"DOWNLOAD_START.txt", output/"START-HERE.txt")
    (output/"SOURCE_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    checksums = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}" for path in sorted(output.iterdir()) if path.is_file()]
    (output/"SHA256SUMS.txt").write_text("\n".join(checksums)+"\n", encoding="utf-8")
    print(f"Created {output} ({len(files)} public source files)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New release folder")
    package(parser.parse_args().output.resolve())
