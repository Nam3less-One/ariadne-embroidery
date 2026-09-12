"""Install the exact setup in a NEW test folder, exercise it, then uninstall.

Use a disposable Windows account or one without an existing Ariadne install.
Registry and Start menu entries are checked and then removed by the uninstaller.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import winreg


def installed_value(key, name):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
            return winreg.QueryValueEx(handle, name)[0]
    except FileNotFoundError:
        return None


def verify(setup, output):
    key = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Ariadne"
    if installed_value(key, "DisplayName") or installed_value(r"Software\Ariadne", "InstallDir"):
        raise SystemExit("Use an account without an existing Ariadne installation")
    output.mkdir(parents=True, exist_ok=False)
    installed = output / "Installed App"
    result = {"setup": setup.name, "setup_sha256": hashlib.sha256(setup.read_bytes()).hexdigest()}
    # /D is deliberately last and unquoted as required by NSIS command-line syntax.
    subprocess.run(f'"{setup}" /S /D={installed}', check=True, timeout=120)
    app = installed / "Ariadne.exe"
    assert app.is_file(), "Installer did not extract Ariadne"
    assert installed_value(key, "UninstallString") == f'"{installed / "Uninstall.exe"}"'
    shortcut = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Ariadne/Ariadne.lnk"
    assert shortcut.is_file(), "Start menu shortcut was not created"
    result["installation_and_shortcut"] = True
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "TCL", "TK"))}
    env["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
    subprocess.run([str(app), "--self-test", str(output / "installed-test")], env=env, check=True, timeout=120)
    result["installed_self_test"] = json.loads((output / "installed-test/self-test.json").read_text())
    sentinel = installed / "my-own-design.txt"
    sentinel.write_text("Preserve files not installed by Ariadne.", encoding="utf-8")
    uninstall = installed / "Uninstall.exe"
    subprocess.run(f'"{uninstall}" /S _?={installed}', check=True, timeout=120)
    deadline = time.monotonic() + 30
    while app.exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    assert not app.exists(), "Uninstaller left app executable"
    assert not installed_value(key, "DisplayName"), "Uninstall registration remains"
    assert not installed_value(r"Software\Ariadne", "InstallDir"), "App registration remains"
    assert not shortcut.exists(), "Start menu shortcut remains"
    assert sentinel.read_text(encoding="utf-8") == "Preserve files not installed by Ariadne."
    result["uninstalled_and_unrecognized_file_preserved"] = True
    result["passed"] = True
    (output / "installer-test.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("setup", type=lambda s: Path(s).resolve())
    parser.add_argument("output", type=lambda s: Path(s).resolve())
    args = parser.parse_args()
    verify(args.setup, args.output)
