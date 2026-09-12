"""Frozen desktop entry point; --self-test exercises the actual shipped runtime."""
import json
import sys
import time
import traceback
from pathlib import Path

from ariadne_embroidery.gui import Studio, main, tk, filedialog, messagebox


def self_test(destination):
    destination.mkdir(parents=True, exist_ok=False)
    root = None
    try:
        from PIL import Image, ImageDraw
        artwork = destination / "sample.png"
        im = Image.new("RGB", (120, 100), "white")
        draw = ImageDraw.Draw(im)
        draw.ellipse((10, 10, 80, 80), fill="#286b62")
        draw.ellipse((25, 25, 65, 65), fill="white")
        draw.rectangle((90, 20, 110, 80), fill="#df9b45")
        draw.line((10, 90, 110, 90), fill="#286b62", width=1)
        im.save(artwork)
        root = tk.Tk()
        root.withdraw()
        app = Studio(root)
        filedialog.askopenfilename = lambda **kw: str(artwork)
        filedialog.askdirectory = lambda **kw: str(destination)
        errors = []
        messagebox.showerror = lambda *args, **kw: errors.append(str(args))
        app.open_source()
        app.width.set("60")
        results = []
        for count in (1, 2, 4):
            app.colors.set(str(count))
            assert app.proof_label.image is None
            app.preview()
            deadline = time.monotonic() + 90
            while app.busy and time.monotonic() < deadline:
                root.update()
                time.sleep(0.02)
            if errors or app.prepared_plan is None:
                raise RuntimeError(f"Frozen artwork preview failed: {errors}")
            assert len(app.prepared_plan["threads"]) == min(count, 2)
            app.convert()
            deadline = time.monotonic() + 90
            while app.busy and time.monotonic() < deadline:
                root.update()
                time.sleep(0.02)
            if errors or app.busy or app.result is None:
                raise RuntimeError(f"Frozen GUI conversion failed: {errors}")
            for name in ("design.pes", "design.dst", "design-pes-proof.png", "review.json"):
                assert (app.result / name).is_file(), name
            assert app.proof_label.image is not None
            results.append({"requested_colors": count, "actual_colors": len(app.prepared_plan["threads"]), "passed": True})
        (destination / "self-test.json").write_text(json.dumps({
            "passed": True, "frozen": bool(getattr(sys, "frozen", False)),
            "python": sys.version, "tk": root.tk.call("info", "patchlevel"),
            "bundle": str(app.result), "gui_worker_and_proof": True,
            "color_regressions": results,
        }, indent=2), encoding="utf-8")
        return 0
    except Exception:
        (destination / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        return 1
    finally:
        if root is not None:
            root.destroy()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
        sys.exit(self_test(Path(sys.argv[2]).resolve()))
    main()
