"""Local studio: prepare foreground, review colors, export and inspect machine files."""
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk
from PIL import Image, ImageDraw, ImageOps, ImageTk
from . import __version__
from .core import Settings, export_plan, load_plan, trace_image

BACKGROUNDS = {"Auto · remove light paper": "auto", "Keep background as thread": "keep", "Remove color at top-left": "corner"}


def artwork_preview(plan):
    scale = min(1000/plan["width_mm"], 1000/plan["height_mm"])
    size = (max(1, round(plan["width_mm"]*scale)), max(1, round(plan["height_mm"]*scale)))
    image = Image.new("RGBA", size)
    for obj in plan["objects"]:
        mask = Image.new("L", size)
        draw = ImageDraw.Draw(mask)
        if obj["type"] == "fill":
            rings = obj["geometry"]["coordinates"]
            draw.polygon([(x*scale, y*scale) for x, y in rings[0]], fill=255)
            for ring in rings[1:]:
                draw.polygon([(x*scale, y*scale) for x, y in ring], fill=0)
        else:
            draw.polygon([(x*scale, y*scale) for x, y in obj["left"]+list(reversed(obj["right"]))], fill=255)
        image.paste(Image.new("RGBA", size, plan["threads"][obj["thread"]]["hex"]), (0, 0), mask)
    return image


class Studio:
    def __init__(self, root):
        self.root, self.source, self.result = root, None, None
        self.prepared_plan, self.revision = None, 0
        self.events, self.busy, self.display_images = queue.Queue(), False, {}
        root.title(f"Ariadne {__version__} · Embroidery Studio")
        root.geometry("1240x850")
        root.minsize(980, 740)
        root.configure(background="#f4f1e9")
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background="#f4f1e9")
        style.configure("TLabel", background="#f4f1e9", foreground="#233e39", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 23, "bold"))
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=(10, 7))
        style.configure("Primary.TButton", foreground="white", background="#246b59")
        style.map("Primary.TButton", background=[("active", "#185747"), ("disabled", "#a5b5ac")])
        style.configure("TCheckbutton", background="#f4f1e9", font=("Segoe UI", 10))
        outer = ttk.Frame(root, padding=18)
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x")
        ttk.Label(header, text="Ariadne", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="  Artwork → preview → machine files\n  Free · offline · your files stay here").pack(side="left", padx=12)
        self.open_button = ttk.Button(header, text="1  Open artwork…", command=self.open_source, style="Primary.TButton")
        self.open_button.pack(side="right")
        self.filename = tk.StringVar(value="Start with a simple logo image or an editable Ariadne plan.")
        ttk.Label(outer, textvariable=self.filename).pack(fill="x", pady=(8, 14))
        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        panel = ttk.Frame(body, width=280)
        panel.pack(side="left", fill="y", padx=(0, 18))
        panel.pack_propagate(False)
        ttk.Label(panel, text="2  Prepare your artwork", style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        self.width, self.colors, self.spacing, self.angle = (tk.StringVar(value=v) for v in ("100", "4", "0.42", "0"))
        self.background = tk.StringVar(value=next(iter(BACKGROUNDS)))
        self.trim = tk.BooleanVar(value=True)
        self.underlay, self.skip = tk.BooleanVar(value=True), tk.BooleanVar(value=False)
        self.thread_color = tk.StringVar(value="#243735")
        self.entries, self.checks = [], []
        for title, var in (("Finished width (mm)", self.width), ("Maximum thread colors (1–12)", self.colors)):
            ttk.Label(panel, text=title).pack(anchor="w")
            entry = ttk.Entry(panel, textvariable=var)
            entry.pack(fill="x", pady=(3, 9))
            self.entries.append(entry)
        self.swatch_button = ttk.Button(panel, text="One-thread color: #243735", command=self.choose_thread, state="disabled")
        self.swatch_button.pack(fill="x", pady=(0, 8))
        ttk.Label(panel, text="Background").pack(anchor="w")
        self.background_box = ttk.Combobox(panel, textvariable=self.background, values=list(BACKGROUNDS), state="readonly")
        self.background_box.pack(fill="x", pady=(3, 6))
        ttk.Label(panel, text="Remove paper before counting colors.\nCheck the preview for missing areas.", wraplength=270).pack(anchor="w")
        trim = ttk.Checkbutton(panel, text="Fit width to artwork (trim margins)", variable=self.trim)
        trim.pack(anchor="w", pady=(9, 3))
        self.checks.append(trim)
        self.size_help = tk.StringVar(value="Width applies to foreground artwork.")
        ttk.Label(panel, textvariable=self.size_help, wraplength=270).pack(anchor="w", pady=(0, 8))
        self.advanced_button = ttk.Button(panel, text="Stitch settings ▸", command=self.toggle_advanced)
        self.advanced_button.pack(fill="x")
        self.advanced_window = tk.Toplevel(root)
        self.advanced_window.withdraw()
        self.advanced_window.title("Stitch settings · Ariadne")
        self.advanced_window.resizable(False, False)
        self.advanced_window.protocol("WM_DELETE_WINDOW", self.advanced_window.withdraw)
        self.advanced = ttk.Frame(self.advanced_window, padding=20)
        self.advanced.pack(fill="both", expand=True)
        for title, var in (("Fill spacing (mm) · lower is denser", self.spacing), ("Fill angle (degrees)", self.angle)):
            ttk.Label(self.advanced, text=title).pack(anchor="w", pady=(4, 0))
            entry = ttk.Entry(self.advanced, textvariable=var)
            entry.pack(fill="x", pady=(2, 2))
            self.entries.append(entry)
        underlay = ttk.Checkbutton(self.advanced, text="Support underlay", variable=self.underlay)
        underlay.pack(anchor="w", pady=4)
        self.checks.append(underlay)
        ttk.Button(self.advanced, text="Done", command=self.advanced_window.withdraw).pack(fill="x", pady=(10, 0))
        self.preview_button = ttk.Button(panel, text="Preview colors & shape", command=self.preview, state="disabled")
        self.preview_button.pack(fill="x", pady=(10, 5))
        self.palette_info = tk.StringVar(value="Actual colors appear after preview.")
        ttk.Label(panel, textvariable=self.palette_info, wraplength=270).pack(anchor="w")
        self.palette_frame = ttk.Frame(panel)
        self.palette_frame.pack(fill="x", pady=4)
        views = ttk.Frame(body)
        views.pack(side="left", fill="both", expand=True)
        views.columnconfigure((0, 1), weight=1)
        views.rowconfigure(1, weight=1)
        ttk.Label(views, text="SOURCE · fit to view", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 7))
        ttk.Label(views, text="REVIEW", style="Section.TLabel").grid(row=0, column=1, sticky="w", padx=(12, 0), pady=(0, 7))
        self.source_label = tk.Label(views, text="Open your artwork to begin", bg="#e0e4db", fg="#455952", width=1, height=1)
        self.source_label.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        self.notebook = ttk.Notebook(views)
        self.notebook.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        self.prepared_label = tk.Label(self.notebook, text="Preview the selected colors\nand foreground shape", bg="#e0e4db", fg="#455952", width=1, height=1)
        self.proof_label = tk.Label(self.notebook, text="Export to inspect decoded\nmachine stitches", bg="#e0e4db", fg="#455952", width=1, height=1)
        self.notebook.add(self.prepared_label, text="Artwork preview")
        self.notebook.add(self.proof_label, text="Stitch proof")
        for label in (self.source_label, self.prepared_label, self.proof_label):
            label.image = None
            label.bind("<Configure>", lambda event, target=label: self.redraw(target))
        self.review_note = tk.StringVar(value="Artwork preview shows selected shapes. Stitch proof comes from the saved PES file.")
        review_label = ttk.Label(views, textvariable=self.review_note, wraplength=650)
        review_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        views.bind("<Configure>", lambda event: review_label.configure(wraplength=max(240, event.width-10)))
        self.status = tk.StringVar(value="Ready. Open artwork, choose the background, then preview its shape.")
        status_label = ttk.Label(outer, textvariable=self.status, wraplength=900)
        status_label.pack(anchor="w", pady=(10, 5))
        outer.bind("<Configure>", lambda event: status_label.configure(wraplength=max(400, event.width-36)))
        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.pack(fill="x", pady=(0, 8))
        actions = ttk.Frame(outer)
        actions.pack(fill="x")
        self.convert_button = ttk.Button(actions, text="3  Export PES + DST…", command=self.convert, state="disabled", style="Primary.TButton")
        self.convert_button.pack(side="left")
        self.folder_button = ttk.Button(actions, text="Open output folder", command=self.open_output, state="disabled")
        self.folder_button.pack(side="left", padx=8)
        ttk.Label(actions, text="DRAFT · Review and test sew.").pack(side="right")
        for var in (self.width, self.colors, self.spacing, self.angle, self.background, self.trim, self.underlay, self.thread_color):
            var.trace_add("write", self.settings_changed)
        root.bind("<Control-o>", lambda event: self.open_source() if not self.busy else None)
        root.after(80, self.poll)

    def toggle_advanced(self):
        if self.advanced_window.state() != "withdrawn":
            self.advanced_window.withdraw()
        else:
            self.advanced_window.transient(self.root)
            self.advanced_window.deiconify()
            self.advanced_window.lift()

    def choose_thread(self):
        color = colorchooser.askcolor(self.thread_color.get(), title="Choose the single thread color")[1]
        if color:
            self.thread_color.set(color)

    def clear_image(self, label, text):
        self.display_images.pop(label, None)
        label.configure(image="", text=text)
        label.image = None

    def show_image(self, label, source):
        if isinstance(source, Image.Image):
            self.display_images[label] = source.convert("RGBA")
        else:
            with Image.open(source) as original:
                self.display_images[label] = ImageOps.exif_transpose(original).convert("RGBA")
        self.redraw(label)

    def redraw(self, label):
        if label not in self.display_images:
            return
        original = self.display_images[label]
        width, height = max(120, label.winfo_width()-18), max(120, label.winfo_height()-18)
        ratio = min(width/original.width, height/original.height)
        picture = original.resize((max(1, round(original.width*ratio)), max(1, round(original.height*ratio))), Image.Resampling.LANCZOS)
        background = Image.new("RGBA", picture.size, "#e0e4db")
        background.alpha_composite(picture)
        label.image = ImageTk.PhotoImage(background.convert("RGB"))
        label.configure(image=label.image, text="")

    def settings_changed(self, *args):
        self.revision += 1
        self.prepared_plan, self.result = None, None
        self.clear_image(self.prepared_label, "Settings changed.\nPreview colors & shape again.")
        self.clear_image(self.proof_label, "Settings changed.\nExport for a current stitch proof.")
        self.folder_button.configure(state="disabled")
        self.palette_info.set("Actual colors may be fewer than the maximum.")
        for child in self.palette_frame.winfo_children():
            child.destroy()
        self.swatch_button.configure(text=f"One-thread color: {self.thread_color.get()}", state="normal" if self.colors.get() == "1" and not self.busy else "disabled")
        self.size_help.set("Width applies to foreground artwork." if self.trim.get() else "Width includes the original image margins.")
        if self.source:
            self.status.set("Settings changed. Preview the foreground before exporting.")

    def open_source(self):
        if self.busy:
            return
        path = filedialog.askopenfilename(title="Choose artwork or an Ariadne plan", filetypes=[("Artwork and plans", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff *.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            candidate = Path(path)
            plan = load_plan(candidate) if candidate.suffix.lower() == ".json" else None
            self.show_image(self.source_label, artwork_preview(plan) if plan else candidate)
            self.source = candidate
            self.settings_changed()
            self.filename.set(candidate.name)
            self.notebook.select(self.prepared_label)
            self.set_busy(False)
            self.status.set("Editable plan loaded. Its geometry and settings are preserved." if plan else "Choose the background and maximum colors. Preview confirms what will be stitched.")
        except Exception as exc:
            messagebox.showerror("Cannot open artwork", str(exc))

    def settings(self):
        return Settings(width_mm=float(self.width.get()), colors=int(self.colors.get()), spacing_mm=float(self.spacing.get()),
                        angle_deg=float(self.angle.get()), underlay=self.underlay.get(), background_mode=BACKGROUNDS[self.background.get()],
                        trim_margins=self.trim.get(), single_thread_color=self.thread_color.get() if self.colors.get() == "1" else None).validate()

    def set_busy(self, busy):
        self.busy = busy
        is_plan = self.source is not None and self.source.suffix.lower() == ".json"
        for widget in self.entries+self.checks:
            widget.configure(state="disabled" if busy or is_plan else "normal")
        self.background_box.configure(state="disabled" if busy or is_plan else "readonly")
        self.swatch_button.configure(state="normal" if not busy and not is_plan and self.colors.get() == "1" else "disabled")
        self.open_button.configure(state="disabled" if busy else "normal")
        for button in (self.preview_button, self.convert_button):
            button.configure(state="normal" if self.source and not busy else "disabled")
        self.folder_button.configure(state="normal" if self.result and not busy else "disabled")

    def start(self, destination=None):
        if self.busy or self.source is None:
            return
        try:
            settings = None if self.source.suffix.lower() == ".json" else self.settings()
        except (ValueError, KeyError) as exc:
            self.settings_changed()
            messagebox.showerror("Check settings", str(exc))
            return
        revision, source, cached = self.revision, self.source, self.prepared_plan
        self.result = None
        self.clear_image(self.proof_label, "Preparing a new draft…" if destination else "Export to see decoded machine stitches.")
        self.set_busy(True)
        self.progress.start(12)
        self.status.set("Preparing foreground and thread colors…" if destination is None else "Preparing artwork, stitching and checking PES + DST…")
        def work():
            try:
                plan = cached or (load_plan(source) if settings is None else trace_image(source, settings))
                result = export_plan(plan, destination) if destination else None
                self.events.put(("done", (plan, result), revision))
            except Exception as exc:
                self.events.put(("error", str(exc), revision))
        threading.Thread(target=work, daemon=True).start()

    def preview(self):
        self.start()

    def convert(self):
        if self.busy or self.source is None:
            return
        try:
            if self.source.suffix.lower() != ".json":
                self.settings()
        except (ValueError, KeyError) as exc:
            self.settings_changed()
            messagebox.showerror("Check settings", str(exc))
            return
        parent = filedialog.askdirectory(title="Choose where to save your new PES + DST bundle")
        if not parent:
            return
        destination = Path(parent)/(self.source.stem+"-ariadne")
        index = 2
        while destination.exists():
            destination = Path(parent)/f"{self.source.stem}-ariadne-{index}"
            index += 1
        self.start(destination)

    def open_output(self):
        if self.result is not None and self.result.is_dir():
            if sys.platform == "win32":
                os.startfile(self.result)
            else:
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(self.result)])

    def poll(self):
        try:
            kind, value, revision = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.progress.stop()
            if revision != self.revision:
                self.set_busy(False)
                self.status.set("Settings changed during preparation. Preview again.")
            elif kind == "done":
                plan, self.result = value
                self.prepared_plan = plan
                self.show_image(self.prepared_label, artwork_preview(plan))
                self.palette_info.set(f"{len(plan['threads'])} actual thread color(s) · {len(plan['objects'])} shapes")
                for child in self.palette_frame.winfo_children():
                    child.destroy()
                for i, thread in enumerate(plan["threads"]):
                    rgb = [int(thread["hex"][j:j+2], 16) for j in (1, 3, 5)]
                    contrast = "#111111" if sum(v*w for v, w in zip(rgb, (.2126, .7152, .0722))) > 150 else "#ffffff"
                    tk.Label(self.palette_frame, text=f" {i+1} ", bg=thread["hex"], fg=contrast, relief="solid", borderwidth=1).grid(row=i//6, column=i%6, padx=2, pady=2)
                caution = [w for w in plan.get("warnings", []) if not w.startswith(("Automatic raster", "No physical"))]
                caution.sort(key=lambda text: not text.startswith(("Fine-detail", "Low-resolution")))
                self.review_note.set(" · ".join(caution[:2]) or "Every design needs review and test sewing.")
                if self.result:
                    self.show_image(self.proof_label, self.result/"design-pes-proof.png")
                    self.notebook.select(self.proof_label)
                    report = json.loads((self.result/"review.json").read_text(encoding="utf-8"))["files"]["pes"]
                    width, height = report["travel_size_mm"]
                    self.status.set(f"Saved {report['command_counts']['STITCH']:,} stitches · travel {width:.1f} × {height:.1f} mm · {self.result.name}. Use Open output folder for PES, DST and setup notes.")
                else:
                    self.notebook.select(self.prepared_label)
                    self.status.set(f"Artwork preview ready · {plan['width_mm']:.1f} × {plan['height_mm']:.1f} mm. Check holes, shapes and colors, then export.")
                self.set_busy(False)
            else:
                self.result, self.prepared_plan = None, None
                self.clear_image(self.proof_label, "Export did not complete.\nNo current machine-file proof.")
                self.set_busy(False)
                self.status.set("Stopped without saving a partial bundle. Adjust the input or settings and try again.")
                messagebox.showerror("Could not prepare this artwork", value)
        self.root.after(80, self.poll)


def main():
    root = tk.Tk()
    Studio(root)
    root.mainloop()


if __name__ == "__main__":
    main()
