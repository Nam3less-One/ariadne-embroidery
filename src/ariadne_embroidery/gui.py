"""Tk desktop studio. Conversion runs off the UI thread; files remain local."""

import json
import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageTk

from .core import Settings, convert_image, export_plan, load_plan


class Studio:
    def __init__(self, root):
        self.root, self.source, self.result = root, None, None
        self.events = queue.Queue()
        self.busy = False
        root.title("Ariadne · Embroidery Studio")
        root.geometry("1120x820")
        root.minsize(900, 700)
        root.configure(background="#f1eee7")
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background="#f1eee7")
        style.configure("TLabel", background="#f1eee7", foreground="#243735", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 24, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        style.configure("TCheckbutton", background="#f1eee7", font=("Segoe UI", 10))
        outer = ttk.Frame(root, padding=24)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Ariadne", style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Your artwork, stitched locally. Free and open source.").pack(anchor="w", pady=(0, 15))
        controls = ttk.Frame(outer)
        controls.pack(fill="x")
        self.open_button = ttk.Button(controls, text="Open artwork or plan…", command=self.open_source)
        self.open_button.pack(side="left")
        self.filename = tk.StringVar(value="Choose a PNG, JPEG, WebP or editable Ariadne JSON plan")
        ttk.Label(controls, textvariable=self.filename).pack(side="left", padx=14)
        settings = ttk.Frame(outer, padding=(0, 18))
        settings.pack(fill="x")
        self.width, self.colors, self.spacing, self.angle = (tk.StringVar(value=v) for v in ("100", "4", "0.42", "0"))
        self.entries = []
        for column, (title, var) in enumerate((("Width · mm", self.width), ("Thread colors", self.colors), ("Fill spacing · mm", self.spacing), ("Fill angle · degrees", self.angle))):
            frame = ttk.Frame(settings)
            frame.grid(row=0, column=column, padx=(0, 24), sticky="w")
            ttk.Label(frame, text=title).pack(anchor="w")
            entry = ttk.Entry(frame, textvariable=var, width=15)
            entry.pack(pady=(5, 0))
            self.entries.append(entry)
        self.underlay, self.skip = tk.BooleanVar(value=True), tk.BooleanVar(value=False)
        options = ttk.Frame(outer)
        options.pack(fill="x", pady=(0, 14))
        self.checks = [ttk.Checkbutton(options, text="Support underlay", variable=self.underlay),
                       ttk.Checkbutton(options, text="Exclude top-left palette color", variable=self.skip)]
        for check in self.checks:
            check.pack(side="left", padx=(0, 24))
        panes = ttk.Frame(outer)
        panes.pack(fill="both", expand=True)
        panes.columnconfigure(0, weight=1)
        panes.columnconfigure(1, weight=1)
        panes.rowconfigure(1, weight=1)
        ttk.Label(panes, text="SOURCE ARTWORK").grid(row=0, column=0, sticky="w", pady=(0, 7))
        ttk.Label(panes, text="EXPORTED PES · DECODED PROOF").grid(row=0, column=1, sticky="w", pady=(0, 7))
        self.source_label = tk.Label(panes, text="Open your artwork to begin", bg="#dedfd5", fg="#455952")
        self.proof_label = tk.Label(panes, text="The saved machine file will be decoded here", bg="#dedfd5", fg="#455952")
        self.source_label.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        self.proof_label.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        self.status = tk.StringVar(value="Ready. No uploads, account or paid service required.")
        ttk.Label(outer, textvariable=self.status, wraplength=1000).pack(anchor="w", pady=(14, 6))
        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.pack(fill="x", pady=(0, 8))
        actions = ttk.Frame(outer)
        actions.pack(fill="x")
        self.convert_button = ttk.Button(actions, text="Create PES + DST bundle…", command=self.convert, state="disabled")
        self.convert_button.pack(side="left")
        ttk.Label(actions, text="DRAFT  ·  Inspect paths, verify hoop fit, then test sew.").pack(side="left", padx=18)
        root.after(100, self.poll)

    def show_image(self, label, path):
        with Image.open(path) as original:
            image = ImageOps.exif_transpose(original).convert("RGBA")
            image.thumbnail((460, 390), Image.Resampling.LANCZOS)
            background = Image.new("RGBA", image.size, "#dedfd5")
            background.alpha_composite(image)
            photo = ImageTk.PhotoImage(background.convert("RGB"))
        label.configure(image=photo, text="")
        label.image = photo

    def open_source(self):
        path = filedialog.askopenfilename(title="Choose artwork or an Ariadne plan", filetypes=[("Artwork and plans", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff *.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            candidate = Path(path)
            is_plan = candidate.suffix.lower() == ".json"
            if is_plan:
                load_plan(candidate)
                self.source_label.configure(image="", text="Editable geometry plan\n"+candidate.name)
                self.source_label.image = None
            else:
                self.show_image(self.source_label, candidate)
            self.source, self.result = candidate, None
            self.proof_label.configure(image="", text="Create a bundle to see its decoded proof")
            self.proof_label.image = None
            self.filename.set(candidate.name)
            self.status.set("Plan settings are preserved; edit the JSON to change objects or size." if is_plan else "Adjust settings, then choose a new output folder.")
            for widget in self.entries + self.checks:
                widget.configure(state="disabled" if is_plan else "normal")
            self.convert_button.configure(state="normal")
        except Exception as exc:
            messagebox.showerror("Cannot open artwork", str(exc))

    def convert(self):
        if self.busy or self.source is None:
            return
        try:
            settings = Settings() if self.source.suffix.lower() == ".json" else Settings(width_mm=float(self.width.get()), colors=int(self.colors.get()),
                                spacing_mm=float(self.spacing.get()), angle_deg=float(self.angle.get()),
                                underlay=self.underlay.get(), skip_corner_color=self.skip.get()).validate()
        except ValueError as exc:
            messagebox.showerror("Check settings", str(exc))
            return
        parent = filedialog.askdirectory(title="Choose a parent folder for a NEW draft bundle")
        if not parent:
            return
        destination = Path(parent)/(self.source.stem+"-ariadne")
        index = 2
        while destination.exists():
            destination = Path(parent)/f"{self.source.stem}-ariadne-{index}"
            index += 1
        self.busy = True
        self.open_button.configure(state="disabled")
        self.convert_button.configure(state="disabled")
        for widget in self.entries+self.checks:
            widget.configure(state="disabled")
        self.progress.start(12)
        self.status.set("Tracing objects, planning stitches and decoding both exports…")
        source = self.source
        def work():
            try:
                result = export_plan(load_plan(source), destination) if source.suffix.lower() == ".json" else convert_image(source, destination, settings)
                self.events.put(("done", result))
            except Exception as exc:
                self.events.put(("error", str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            kind, value = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            self.progress.stop()
            self.open_button.configure(state="normal")
            self.convert_button.configure(state="normal")
            for widget in self.entries+self.checks:
                widget.configure(state="disabled" if self.source.suffix.lower() == ".json" else "normal")
            if kind == "done":
                self.result = value
                self.show_image(self.proof_label, value/"design-pes-proof.png")
                report = json.loads((value/"review.json").read_text(encoding="utf-8"))["files"]["pes"]
                w, h = report["travel_size_mm"]
                self.status.set(f"Saved {value}  |  {report['command_counts']['STITCH']:,} stitches  |  {w:.1f} × {h:.1f} mm. Review SETUP.txt and proof images.")
            else:
                self.status.set("Conversion stopped. Correct the issue and try again.")
                messagebox.showerror("Could not create bundle", value)
        self.root.after(100, self.poll)


def main():
    root = tk.Tk()
    Studio(root)
    root.mainloop()


if __name__ == "__main__":
    main()
