"""Tk widget/workflow tests; skipped when the host has no graphical display.

These exercise the real worker, output decode and stale-result controls. They
do not substitute for a human or screenshot-based layout review.
"""
import time
from pathlib import Path

import pytest


def test_desktop_conversion_workflow(tmp_path, monkeypatch):
    tkinter = pytest.importorskip("tkinter")
    try:
        root = tkinter.Tk()
    except tkinter.TclError:
        pytest.skip("Tk display unavailable")
    root.withdraw()
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
