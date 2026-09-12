"""Tk widget/workflow tests; skipped when the host has no graphical display.

These exercise the real worker, output decode and stale-result controls. They
do not substitute for a human or screenshot-based layout review.
"""
import time
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def tk_runtime():
    """Use one Tcl/Tk interpreter, as the real application does.

    Repeated Tk() destruction/recreation on the Windows CPython 3.14 host can
    fail transiently while rereading init.tcl. A fresh Toplevel per test keeps
    the windows isolated without repeatedly initializing the native runtime.
    """
    tkinter = pytest.importorskip("tkinter")
    try:
        root = tkinter.Tk()
    except tkinter.TclError as exc:
        if any(reason in str(exc).lower() for reason in
               ("no display name", "couldn't connect to display")):
            pytest.skip(f"Tk display unavailable: {exc}")
        raise
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def tk_window(tk_runtime):
    import tkinter
    window = tkinter.Toplevel(tk_runtime)
    window.withdraw()
    yield window
    # Studio schedules polling callbacks. Cancel pending timers between tests
    # so a later test cannot inherit callbacks for a destroyed window.
    for timer in tk_runtime.tk.call("after", "info"):
        tk_runtime.after_cancel(timer)
    if window.winfo_exists():
        window.destroy()


def wait_for_worker(root, app):
    deadline = time.monotonic()+20
    while app.busy and time.monotonic() < deadline:
        root.update()
        time.sleep(.01)
    assert not app.busy


def test_desktop_conversion_workflow(tmp_path, monkeypatch, tk_window):
    root = tk_window
    try:
        from ariadne_embroidery import gui
        app = gui.Studio(root)
        source = Path(__file__).parents[1]/"examples"/"geometric-mark.png"
        monkeypatch.setattr(gui.filedialog, "askopenfilename", lambda **kwargs: str(source))
        monkeypatch.setattr(gui.filedialog, "askdirectory", lambda **kwargs: str(tmp_path))
        errors = []
        monkeypatch.setattr(gui.messagebox, "showerror", lambda *args: errors.append(args))
        app.open_source()
        assert app.source == source
        assert str(app.convert_button["state"]) == "normal"
        app.colors.set("2")
        app.width.set("80")
        app.convert()
        assert app.busy
        assert str(app.open_button["state"]) == "disabled"
        deadline = time.monotonic()+20
        while app.busy and time.monotonic() < deadline:
            root.update()
            time.sleep(.01)
        assert not app.busy
        assert not errors
        assert (app.result/"design.dst").exists()
        assert app.proof_label.image is not None
        assert "Saved" in app.status.get()
        # Opening new input must clear the prior output and displayed proof.
        app.open_source()
        assert app.result is None
        assert app.proof_label.image is None
    finally:
        root.destroy()


def test_preview_color_changes_export_and_folder_action(tmp_path, monkeypatch, tk_window):
    """A first-time user can inspect a silhouette before making machine files."""
    root = tk_window
    try:
        from PIL import Image, ImageDraw
        from ariadne_embroidery import gui
        source = tmp_path/"two-color-on-paper.png"
        artwork = Image.new("RGB", (200, 120), "white")
        draw = ImageDraw.Draw(artwork)
        draw.ellipse((20, 20, 90, 100), fill="#b42432")
        draw.rectangle((115, 25, 175, 95), fill="#235ca6")
        artwork.save(source)
        app = gui.Studio(root)
        errors, opened = [], []
        monkeypatch.setattr(gui.filedialog, "askopenfilename", lambda **kwargs: str(source))
        monkeypatch.setattr(gui.filedialog, "askdirectory", lambda **kwargs: str(tmp_path))
        monkeypatch.setattr(gui.messagebox, "showerror", lambda *args: errors.append(args))
        monkeypatch.setattr(gui.sys, "platform", "win32")
        monkeypatch.setattr(gui.os, "startfile", lambda path: opened.append(path), raising=False)
        app.open_source()
        app.width.set("60")
        app.colors.set("1")
        app.thread_color.set("#123456")
        app.preview()
        wait_for_worker(root, app)
        assert not errors
        assert app.result is None
        assert app.prepared_label.image is not None
        assert app.proof_label.image is None
        assert str(app.folder_button["state"]) == "disabled"
        assert len(app.prepared_plan["threads"]) == 1
        assert app.prepared_plan["threads"][0]["hex"].lower() == "#123456"
        assert len(app.prepared_plan["objects"]) == 2
        assert not list(tmp_path.glob("*-ariadne"))

        app.colors.set("2")
        assert app.prepared_plan is None
        assert app.prepared_label.image is None
        app.convert()
        wait_for_worker(root, app)
        assert not errors
        assert len(app.prepared_plan["threads"]) == 2
        destination = app.result
        assert (destination/"design.pes").is_file()
        assert (destination/"design.dst").is_file()
        assert app.proof_label.image is not None
        assert str(app.folder_button["state"]) == "normal"
        app.open_output()
        assert opened == [destination]

        app.spacing.set("0.45")
        assert app.result is None
        assert app.prepared_plan is None
        assert app.proof_label.image is None
        assert app.prepared_label.image is None
        assert str(app.folder_button["state"]) == "disabled"
        app.open_output()
        assert opened == [destination]

        app.width.set("NaN")
        app.preview()
        assert errors and not app.busy
        assert app.proof_label.image is None
        app.width.set("60")
        app.preview()
        wait_for_worker(root, app)
        assert len(errors) == 1
        assert app.prepared_plan is not None
    finally:
        root.destroy()


def test_failed_export_clears_current_machine_proof(tmp_path, monkeypatch, tk_window):
    root = tk_window
    try:
        from ariadne_embroidery import gui
        app = gui.Studio(root)
        source = Path(__file__).parents[1]/"examples"/"geometric-mark.png"
        errors = []
        monkeypatch.setattr(gui.filedialog, "askopenfilename", lambda **kwargs: str(source))
        monkeypatch.setattr(gui.filedialog, "askdirectory", lambda **kwargs: str(tmp_path))
        monkeypatch.setattr(gui.messagebox, "showerror", lambda *args: errors.append(args))
        app.open_source()
        app.convert()
        wait_for_worker(root, app)
        assert app.result is not None
        assert app.proof_label.image is not None

        def fail_export(*args):
            raise ValueError("Synthetic export failure for GUI recovery verification")

        monkeypatch.setattr(gui, "export_plan", fail_export)
        app.convert()
        assert app.result is None
        assert app.proof_label.image is None
        wait_for_worker(root, app)
        assert errors
        assert app.result is None
        assert app.proof_label.image is None
        assert str(app.folder_button["state"]) == "disabled"
        assert str(app.convert_button["state"]) == "normal"
    finally:
        root.destroy()
