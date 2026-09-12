"""Fresh machine-file decoding, conservative metrics and illustrative rendering."""

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw
import pyembroidery as emb


def render_proof(path, output, threads=None):
    path, output = Path(path), Path(output)
    decoded = emb.read(str(path))
    if decoded is None or not decoded.stitches:
        raise ValueError("Exported file contains no commands.")
    names = {emb.STITCH: "STITCH", emb.JUMP: "JUMP", emb.TRIM: "TRIM", emb.COLOR_CHANGE: "COLOR_CHANGE", emb.END: "END", emb.STOP: "STOP"}
    counts, lengths, segments, jumps = Counter(), [], [], []
    previous, color, zeros, untrimmed = (0.0, 0.0), 0, 0, 0
    sewn, trimmed = False, True
    coordinates = []
    for x, y, raw_command in decoded.stitches:
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("Export contains non-finite coordinates.")
        command = raw_command & emb.COMMAND_MASK
        counts[names.get(command, str(command))] += 1
        point = (x/10, y/10)
        coordinates.append(point)
        if command == emb.STITCH:
            distance = math.dist(previous, point)
            lengths.append(distance)
            zeros += distance < .001
            segments.append((previous, point, color))
            sewn, trimmed = True, False
        elif command == emb.JUMP:
            jumps.append((previous, point))
            if sewn and not trimmed and math.dist(previous, point) > 2:
                untrimmed += 1
        elif command in (emb.TRIM, emb.COLOR_CHANGE):
            trimmed = True
            if command == emb.COLOR_CHANGE:
                color += 1
        previous = point
    if (decoded.stitches[-1][2] & emb.COMMAND_MASK) != emb.END or not segments:
        raise ValueError("Export must have stitches and a final END.")
    if max(lengths) > 7.2:
        raise ValueError("Export contains a sewing stitch longer than 7.2 mm.")
    if untrimmed:
        raise ValueError("Export contains an untrimmed transfer longer than 2 mm.")
    embedded = [{"hex": t.hex_color(), "description": t.description} for t in decoded.threadlist]
    palette = threads if path.suffix.lower() == ".dst" else embedded
    if path.suffix.lower() == ".dst" and threads is None:
        raise ValueError("A DST proof requires an external thread chart.")
    if len(palette) != color+1:
        raise ValueError("Thread chart does not match the decoded color sequence.")
    if path.suffix.lower() == ".pes" and threads is not None:
        if [t["hex"].lower() for t in palette] != [t["hex"].lower() for t in threads]:
            raise ValueError("Decoded PES palette does not match the planned thread sequence.")
    if path.suffix.lower() == ".dst":
        raw_travel = emb.read(str(path), settings={"clipping": False})
        coordinates = [(0.0, 0.0)] + [(x/10, y/10) for x, y, _ in raw_travel.stitches]
    else:
        coordinates.append((0.0, 0.0))
    xs, ys = zip(*coordinates)
    bounds = (min(xs), min(ys), max(xs), max(ys))
    scale = min(12.0, 1600/max(bounds[2]-bounds[0], bounds[3]-bounds[1], 1))
    margin = 28
    width = math.ceil((bounds[2]-bounds[0])*scale)+2*margin
    height = math.ceil((bounds[3]-bounds[1])*scale)+2*margin+40
    def pixel(p):
        return ((p[0]-bounds[0])*scale+margin, (p[1]-bounds[1])*scale+margin+40)
    for mode in ("proof", "needle", "travel"):
        canvas = Image.new("RGB", (width, height), "#e6e1d7")
        draw = ImageDraw.Draw(canvas)
        draw.text((12, 10), f"{path.suffix[1:].upper()} decoded {mode} | DRAFT | mm", fill="#252b30")
        for a, b, index in segments:
            thread = palette[index]["hex"]
            if mode == "travel":
                draw.line((pixel(a), pixel(b)), fill="#8f9499", width=1)
            else:
                stroke = max(1, round(.42*scale)) if mode == "proof" else 1
                if mode == "proof":
                    draw.line((pixel(a), pixel(b)), fill="#60605b", width=stroke+1)
                draw.line((pixel(a), pixel(b)), fill=thread, width=stroke)
                if mode == "needle":
                    x, y = pixel(b)
                    draw.point((x, y), fill="#222222")
        if mode == "travel":
            for a, b in jumps:
                draw.line((pixel(a), pixel(b)), fill="#c12875", width=1)
        canvas.save(output/f"{path.stem}-{path.suffix[1:]}-{mode}.png")
    audit = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size,
             "command_counts": dict(counts), "travel_bounds_mm": list(bounds),
             "travel_size_mm": [bounds[2]-bounds[0], bounds[3]-bounds[1]],
             "max_stitch_mm": max(lengths), "short_stitches_under_0_5_mm": sum(0 < round(length*10, 6) < 5 for length in lengths),
             "short_stitches_under_0_2_mm": sum(0 < round(length*10, 6) < 2 for length in lengths),
             "zero_length_stitches": zeros, "untrimmed_transfers_over_2_mm": untrimmed,
             "final_end": True, "palette_source": "external thread chart" if path.suffix.lower() == ".dst" else "PES thread sequence",
             "threads": palette, "proof_note": "Illustrative 0.42 mm thread spread; not a physical sew-out."}
    (output/f"{path.stem}-{path.suffix[1:]}-audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return audit
