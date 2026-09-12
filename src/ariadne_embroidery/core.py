"""Geometry-first draft digitization. Coordinates in editable plans are millimetres.

Raster import makes fill objects, never guesses satin columns from lettering.
An advanced editable plan can supply explicit paired satin rails.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from scipy.ndimage import label, find_objects
from shapely.geometry import LineString, Point, Polygon, shape, mapping
from shapely import make_valid
from skimage.measure import find_contours
import pyembroidery as emb

MAX_INPUT_PIXELS = 40_000_000
MAX_STITCHES = 250_000
MAX_OBJECTS = 2500
FORMATS = ("pes", "dst")


@dataclass(frozen=True)
class Settings:
    width_mm: float = 100.0
    colors: int = 4
    spacing_mm: float = 0.42
    stitch_mm: float = 3.0
    angle_deg: float = 0.0
    underlay: bool = True
    min_area_mm2: float = 0.6
    resolution: int = 768
    skip_corner_color: bool = False

    def validate(self):
        ranges = {"width_mm": (10, 400), "spacing_mm": (0.25, 1.2),
                  "stitch_mm": (1, 5), "angle_deg": (-180, 180),
                  "min_area_mm2": (0, 100)}
        for key, (low, high) in ranges.items():
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f"{key} must be between {low} and {high}.")
        for key, low, high in (("colors", 1, 12), ("resolution", 128, 1200)):
            value = getattr(self, key)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{key} must be an integer between {low} and {high}.")
        if type(self.underlay) is not bool or type(self.skip_corner_color) is not bool:
            raise ValueError("underlay and skip_corner_color must be booleans.")
        return self


def _polygons(geometry):
    if geometry.geom_type == "Polygon":
        yield geometry
    elif hasattr(geometry, "geoms"):
        for child in geometry.geoms:
            yield from _polygons(child)


def trace_image(source: str | Path, settings: Settings = Settings()) -> dict:
    """Quantize opaque pixels and trace connected objects with preserved counters."""
    settings.validate()
    source = Path(source)
    with Image.open(source) as original:
        if original.width * original.height > MAX_INPUT_PIXELS:
            raise ValueError("Image exceeds the 40 megapixel input limit.")
        rgba = ImageOps.exif_transpose(original).convert("RGBA")
    original_size = rgba.size
    rgba.thumbnail((settings.resolution, settings.resolution), Image.Resampling.LANCZOS)
    pixels = np.asarray(rgba)
    opaque = pixels[:, :, 3] >= 128
    if not opaque.any():
        raise ValueError("Image has no opaque artwork (alpha must be at least 128).")
    # Quantize only visible pixels: invisible RGB values must not consume colors.
    visible = Image.fromarray(pixels[:, :, :3][opaque].reshape(1, -1, 3))
    quant = visible.quantize(colors=settings.colors, method=Image.Quantize.MEDIANCUT)
    indices = np.full(opaque.shape, -1, dtype=np.int16)
    indices[opaque] = np.asarray(quant).reshape(-1)
    palette = quant.getpalette()
    scale = settings.width_mm / rgba.width
    warnings = ["Automatic raster import creates draft fill objects. Small lettering and narrow strokes need manual satin planning.",
                "No physical sew-out has been performed. Verify hoop, fabric, stabilizer, needle and tension."]
    excluded = int(indices[0, 0]) if settings.skip_corner_color else -1
    if settings.skip_corner_color and excluded < 0:
        warnings.append("The top-left pixel is transparent; no palette color was excluded.")
    objects, threads, discarded = [], [], 0
    counts = [(int((indices == c).sum()), int(c)) for c in np.unique(indices) if c >= 0 and c != excluded]
    for _, c in sorted(counts, reverse=True):
        rgb = palette[3*c:3*c+3]
        thread_index = len(threads)
        group = []
        connected, count = label(indices == c)
        if count > 20000:
            raise ValueError("Artwork is too fragmented. Simplify it or reduce the color count.")
        for component, region in enumerate(find_objects(connected), 1):
            if region is None:
                continue
            mask = connected[region] == component
            if mask.sum() * scale * scale < settings.min_area_mm2:
                discarded += 1
                continue
            geometry = Polygon()
            for contour in find_contours(np.pad(mask.astype(float), 1), 0.5):
                coords = [((x - 0.5 + region[1].start) * scale, (y - 0.5 + region[0].start) * scale) for y, x in contour]
                if len(coords) >= 4:
                    # XOR nested contour rings keeps holes and islands independent of winding.
                    geometry = geometry.symmetric_difference(make_valid(Polygon(coords)))
            for polygon in _polygons(make_valid(geometry)):
                polygon = polygon.simplify(scale * 0.25, preserve_topology=True)
                if polygon.area < settings.min_area_mm2:
                    discarded += 1
                    continue
                group.append({"id": f"object-{len(objects)+len(group)+1}", "type": "fill",
                              "thread": thread_index, "geometry": mapping(polygon),
                              "angle_deg": settings.angle_deg,
                              "spacing_mm": settings.spacing_mm, "underlay": settings.underlay})
        if group:
            objects.extend(group)
            threads.append({"hex": "#" + "".join(f"{n:02X}" for n in rgb), "description": f"Color {thread_index+1}"})
        if len(objects) > MAX_OBJECTS:
            raise ValueError("Too many objects. Simplify the image or increase minimum area.")
    if not objects:
        raise ValueError("No objects remain. Lower minimum area or include the background color.")
    if discarded:
        warnings.append(f"Discarded {discarded} regions below the minimum area setting.")
    return {"schema": "ariadne-plan", "version": 1, "units": "mm", "status": "draft",
            "source": {"name": source.name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                       "pixels": list(original_size)},
            "width_mm": settings.width_mm, "height_mm": rgba.height * scale,
            "settings": asdict(settings), "threads": threads, "objects": objects,
            "warnings": warnings}


def validate_plan(plan: dict) -> dict:
    if not isinstance(plan, dict) or plan.get("schema") != "ariadne-plan" or plan.get("version") != 1 or plan.get("units") != "mm":
        raise ValueError("Expected an Ariadne version 1 plan in millimetres.")
    Settings(**plan.get("settings", {})).validate()
    for key in ("width_mm", "height_mm"):
        value = plan.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 1 <= value <= 400:
            raise ValueError(f"Plan {key} must be between 1 and 400 mm.")
    threads, objects = plan.get("threads"), plan.get("objects")
    if not isinstance(threads, list) or not 1 <= len(threads) <= 12:
        raise ValueError("Plan must have 1–12 threads.")
    for thread in threads:
        if not isinstance(thread, dict) or not re.fullmatch(r"#[0-9a-fA-F]{6}", thread.get("hex", "")):
            raise ValueError("Thread colors must use #RRGGBB.")
    if not isinstance(objects, list) or not 1 <= len(objects) <= MAX_OBJECTS:
        raise ValueError(f"Plan must have 1–{MAX_OBJECTS} objects.")
    vertices = 0
    for obj in objects:
        if type(obj.get("thread")) is not int or not 0 <= obj["thread"] < len(threads):
            raise ValueError("Object refers to a missing thread.")
        if type(obj.get("underlay", True)) is not bool:
            raise ValueError("Object underlay must be boolean.")
        for name, default, low, high in (("spacing_mm", .42, .25, 1.2), ("angle_deg", 0, -180, 180)):
            value = obj.get(name, default)
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f"Object {name} must be between {low} and {high}.")
        if obj.get("type") == "fill":
            geometry = shape(obj["geometry"])
            if geometry.geom_type != "Polygon" or not geometry.is_valid or geometry.is_empty or geometry.area <= 0:
                raise ValueError("Fill geometry must be a valid nonempty Polygon, with optional holes.")
            coords = list(geometry.exterior.coords)
            for ring in geometry.interiors:
                coords.extend(ring.coords)
        elif obj.get("type") == "satin":
            left, right = obj.get("left", []), obj.get("right", [])
            if len(left) != len(right) or len(left) < 2:
                raise ValueError("Satin requires matching left/right rails with at least two points.")
            coords = left + right
            widths = [math.dist(a, b) for a, b in zip(left, right)]
            if any(not .6 <= w <= 7 for w in widths):
                raise ValueError("Satin columns must be between 0.6 and 7 mm wide.")
            if any(math.dist(a, b) == 0 and math.dist(c, d) == 0 for a, b, c, d in zip(left, left[1:], right, right[1:])):
                raise ValueError("Satin rails contain duplicate paired stations.")
            outline = Polygon(left + list(reversed(right)))
            if not outline.is_valid or outline.area <= 0:
                raise ValueError("Satin rails must form a simple, uncrossed column.")
            for a, b in zip(left, right):
                if not outline.buffer(.00001).covers(LineString([a, b])):
                    raise ValueError("Paired satin stations cross outside the column.")
        else:
            raise ValueError("Object type must be fill or satin.")
        vertices += len(coords)
        if vertices > 100_000:
            raise ValueError("Plan exceeds the geometry vertex limit.")
        for coordinate in coords:
            if len(coordinate) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in coordinate):
                raise ValueError("Geometry coordinates must be finite [x, y] pairs.")
            if not -.01 <= coordinate[0] <= plan["width_mm"]+.01 or not -.01 <= coordinate[1] <= plan["height_mm"]+.01:
                raise ValueError("Geometry lies outside the plan dimensions.")
    return plan


def load_plan(path: str | Path) -> dict:
    path = Path(path)
    if path.stat().st_size > 20_000_000:
        raise ValueError("Plan exceeds the 20 MB limit.")
    return validate_plan(json.loads(path.read_text(encoding="utf-8")))


def _lines(geometry):
    if geometry.geom_type == "LineString":
        if geometry.length > .08:
            yield geometry
    elif hasattr(geometry, "geoms"):
        for child in geometry.geoms:
            yield from _lines(child)


def fill_paths(polygon: Polygon, spacing: float, angle: float, stitch: float) -> list[list[tuple]]:
    """Split scan runs at holes, then join only nearby runs along covered segments.

    A path never bridges a counter with stitches. Disconnected paths are trimmed.
    """
    from shapely.affinity import rotate
    from shapely.ops import substring
    rotated = rotate(polygon, -angle, origin=(0, 0))
    covered = rotated.buffer(.00001)
    rings = [LineString(rotated.exterior.coords)] + [LineString(r.coords) for r in rotated.interiors]

    def connect(a, b):
        if math.dist(a, b) > 8:
            return None
        if covered.covers(LineString([a, b])):
            return [a, b]
        # Follow the actual boundary between adjacent rows when a straight chord
        # would cut across a curved counter or fall outside a curved edge.
        for ring in rings:
            if ring.distance(Point(a)) > .0001 or ring.distance(Point(b)) > .0001:
                continue
            da, db = ring.project(Point(a)), ring.project(Point(b))
            lo, hi = sorted((da, db))
            direct = list(substring(ring, lo, hi).coords)
            around = list(substring(ring, hi, ring.length).coords) + list(substring(ring, 0, lo).coords)
            if da > db:
                direct.reverse()
            else:
                around.reverse()
            route = min((direct, around), key=lambda path: LineString(path).length)
            if LineString(route).length <= 8:
                # Trace vertices are not needle positions. A 0.03 mm geometric
                # simplification stays below the machine's 0.1 mm coordinate grid.
                route = list(LineString(route).simplify(.03).coords)
                return [a] + route + [b]
        return None
    xmin, ymin, xmax, ymax = rotated.bounds
    rows = max(1, math.ceil((ymax-ymin) / spacing))
    pitch = (ymax-ymin) / rows
    paths, active = [], []
    for row in range(rows):
        y = ymin + (row+.5)*pitch
        runs = sorted(_lines(rotated.intersection(LineString([(xmin-1, y), (xmax+1, y)]))), key=lambda line: line.bounds[0])
        next_active, used = [], set()
        for run in runs:
            a, b = tuple(run.coords[0]), tuple(run.coords[-1])
            if a[0] > b[0]:
                a, b = b, a
            choices = []
            for index in active:
                if index in used:
                    continue
                end = paths[index][-1]
                for start, finish in ((a, b), (b, a)):
                    route = connect(end, start)
                    if route is not None:
                        distance = sum(math.dist(a, b) for a, b in zip(route, route[1:]))
                        choices.append((distance, index, start, finish, route))
            if choices:
                _, index, a, b, route = min(choices)
                used.add(index)
                # Boundary runs also obey the configured running-stitch limit.
                for start, finish in zip(route, route[1:]):
                    count = max(1, math.ceil(math.dist(start, finish)/stitch))
                    paths[index].extend([tuple(a+(b-a)*i/count for a, b in zip(start, finish)) for i in range(1, count+1)])
            else:
                if row % 2:
                    a, b = b, a
                index = len(paths)
                paths.append([])
            # Stagger interior needle positions, while keeping every stitch <= stitch.
            length = math.dist(a, b)
            distances = [0.0]
            distance = stitch * (.25 + .25*(row % 3))
            while distance < length:
                distances.append(distance)
                distance += stitch
            distances.append(length)
            paths[index].extend([(a[0]+(b[0]-a[0])*d/length, y) for d in distances])
            next_active.append(index)
        active = next_active
    radians = math.radians(angle)
    c, s = math.cos(radians), math.sin(radians)
    return [[(x*c-y*s, x*s+y*c) for x, y in path] for path in paths if len(path) >= 2]


class _Builder:
    def __init__(self, plan):
        self.plan = plan
        self.pattern = emb.EmbPattern()
        self.spans = []
        self.cursor = None

    def emit(self, command, point):
        x, y = point
        machine_x = round((x-self.plan["width_mm"]/2)*10)
        machine_y = round((y-self.plan["height_mm"]/2)*10)
        point = (machine_x/10+self.plan["width_mm"]/2, machine_y/10+self.plan["height_mm"]/2)
        if command == emb.STITCH and self.cursor is not None and math.dist(self.cursor, point) < .001:
            return
        self.pattern.add_stitch_absolute(command, machine_x, machine_y)
        if len(self.pattern.stitches) > MAX_STITCHES:
            raise ValueError("Design exceeds the 250,000 command limit. Reduce size or complexity.")
        self.cursor = point

    def stitch(self, point, maximum=3.0):
        if self.cursor is None:
            self.emit(emb.JUMP, point)
        distance = math.dist(self.cursor, point)
        if distance < .06:
            return
        start = self.cursor
        for i in range(1, max(1, math.ceil(distance/maximum))+1):
            fraction = i/max(1, math.ceil(distance/maximum))
            self.emit(emb.STITCH, (start[0]+(point[0]-start[0])*fraction, start[1]+(point[1]-start[1])*fraction))

    def path(self, points, maximum=3.0):
        if len(points) < 2 or sum(math.dist(a, b) for a, b in zip(points, points[1:])) < .3:
            return
        # Secure along the first/last actual straight segments, inside the path.
        self.emit(emb.JUMP, points[0])
        first = next((p for p in points[1:] if math.dist(p, points[0]) >= .3), points[1])
        # Only use the first nontrivial segment; never jump ahead across a curved edge.
        first = next((p for p in points[1:] if math.dist(p, points[0]) >= .06), first)
        distance = math.dist(first, points[0])
        if distance:
            anchor = tuple(a+(b-a)*min(.7/distance, 1) for a, b in zip(points[0], first))
            self.stitch(anchor, maximum)
            self.stitch(points[0], maximum)
        for point in points[1:]:
            self.stitch(point, maximum)
        previous = next((p for p in reversed(points[:-1]) if math.dist(p, points[-1]) >= .06), points[-1])
        distance = math.dist(previous, points[-1])
        if distance:
            anchor = tuple(a+(b-a)*min(.7/distance, 1) for a, b in zip(points[-1], previous))
            self.stitch(anchor, maximum)
            self.stitch(points[-1], maximum)
        self.emit(emb.TRIM, self.cursor)


def _satin_paths(obj):
    left, right = obj["left"], obj["right"]
    stations = []
    for a, b, c, d in zip(left, left[1:], right, right[1:]):
        count = max(1, math.ceil(max(math.dist(a, b), math.dist(c, d))/(obj.get("spacing_mm", .4)/2)))
        for i in range(count):
            t = i/count
            stations.append((tuple(x+(y-x)*t for x, y in zip(a, b)), tuple(x+(y-x)*t for x, y in zip(c, d))))
    stations.append((tuple(left[-1]), tuple(right[-1])))
    if obj.get("underlay", True):
        center = [tuple((a+b)/2 for a, b in zip(l, r)) for l, r in stations]
        # Resample a center walk to avoid hundreds of tiny underlay penetrations.
        line = LineString(center)
        count = max(1, math.ceil(line.length/2))
        yield [tuple(line.interpolate(i/count, normalized=True).coords[0]) for i in range(count+1)]
    yield [pair[i % 2] for i, pair in enumerate(stations)] + [stations[-1][(len(stations)) % 2]]


def digitize(plan: dict):
    validate_plan(plan)
    builder = _Builder(plan)
    settings = Settings(**plan.get("settings", {}))
    active_thread = None
    for obj in plan["objects"]:
        index = obj["thread"]
        if index != active_thread:
            if active_thread is not None:
                builder.emit(emb.COLOR_CHANGE, builder.cursor)
            builder.pattern.add_thread({"hex": plan["threads"][index]["hex"], "description": plan["threads"][index].get("description", "")})
            active_thread = index
        start = len(builder.pattern.stitches)
        if obj["type"] == "fill":
            polygon = shape(obj["geometry"])
            angle = obj.get("angle_deg", settings.angle_deg)
            if obj.get("underlay", settings.underlay):
                inset = polygon.buffer(-.3)
                for part in _polygons(inset):
                    for path in fill_paths(part, 2.5, angle+90, settings.stitch_mm):
                        builder.path(path, settings.stitch_mm)
            for path in fill_paths(polygon, obj.get("spacing_mm", settings.spacing_mm), angle, settings.stitch_mm):
                builder.path(path, settings.stitch_mm)
        else:
            for path in _satin_paths(obj):
                builder.path(path, 7.0)
        builder.spans.append({"id": obj.get("id", ""), "start": start, "end": len(builder.pattern.stitches)})
    if not any((s[2] & emb.COMMAND_MASK) == emb.STITCH for s in builder.pattern.stitches):
        raise ValueError("Objects are too small to produce usable stitches.")
    builder.emit(emb.END, builder.cursor)
    return builder.pattern, builder.spans


def _fix_dst_header(path):
    data = path.read_bytes()
    header, body = data[:512], data[512:]
    if len(body) % 3 or body[-3:] != b"\x00\x00\xf3":
        raise ValueError("Invalid DST record framing or END.")
    field = re.search(rb"(?:^|\r)ST:([ 0-9]{7})\r", header)
    if not field:
        raise ValueError("Missing DST stitch count header.")
    count = len(body)//3
    header = header[:field.start(1)] + f"{count:7d}".encode("ascii") + header[field.end(1):]
    # Default DST decoding clips the trim wiggles; include all machine travel.
    raw = emb.read(str(path), settings={"clipping": False})
    xs = [0] + [s[0] for s in raw.stitches]
    ys = [0] + [s[1] for s in raw.stitches]
    extents = {"+X": max(xs), "-X": -min(xs), "+Y": max(ys), "-Y": -min(ys)}
    for key, value in extents.items():
        field = re.search(rb"(?:^|\r)" + re.escape(key.encode("ascii")) + rb":([ 0-9]{5})\r", header)
        if not field:
            raise ValueError("Missing DST extent header.")
        header = header[:field.start(1)] + f"{int(value):5d}".encode("ascii") + header[field.end(1):]
    path.write_bytes(header+body)
    return {"raw_records": count, "header_ST": count, "header_extents_tenths_mm": extents,
            "trim_convention": "three jump records; machine configuration determines cutting"}


def export_plan(plan: dict, destination: str | Path, formats=("pes", "dst")) -> Path:
    """Create a new, complete bundle. Never overwrite an existing destination."""
    validate_plan(plan)
    formats = tuple(dict.fromkeys(str(f).lower().lstrip(".") for f in formats))
    if not formats or any(f not in FORMATS for f in formats):
        raise ValueError("Supported formats are PES and DST.")
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(f"Output already exists: {destination}. Choose a new folder.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    pattern, spans = digitize(plan)
    from .proof import render_proof
    temporary = Path(tempfile.mkdtemp(prefix=".ariadne-", dir=destination.parent))
    try:
        (temporary/"plan.json").write_text(json.dumps(plan, indent=2, allow_nan=False), encoding="utf-8")
        emb.write(pattern, str(temporary/"stitch-master.json"))
        (temporary/"objects.json").write_text(json.dumps(spans, indent=2), encoding="utf-8")
        threads = [{"sequence": i+1, "hex": t.hex_color(), "description": t.description or f"Color {i+1}"} for i, t in enumerate(pattern.threadlist)]
        (temporary/"threads.json").write_text(json.dumps({"note": "DST has no embedded colors. This chart defines the proof and operator thread order.", "threads": threads}, indent=2), encoding="utf-8")
        reports = {}
        for fmt in formats:
            path = temporary/f"design.{fmt}"
            options = {"explicit_trim": True, "max_stitch": 70}
            if fmt == "pes":
                options["version"] = 6
            else:
                options["trim_at"] = 3
            emb.write(pattern, str(path), options)
            extra = _fix_dst_header(path) if fmt == "dst" else {}
            report = render_proof(path, temporary, threads=threads)
            report.update(extra)
            reports[fmt] = report
        review = {"status": "draft_requires_review", "physical_sewout": "not performed", "independent_score": None,
                  "design_mm": [plan["width_mm"], plan["height_mm"]], "warnings": plan.get("warnings", []), "files": reports}
        (temporary/"review.json").write_text(json.dumps(review, indent=2), encoding="utf-8")
        (temporary/"SETUP.txt").write_text("ARIADNE DRAFT — REVIEW AND TEST SEW BEFORE PRODUCTION\n\n"
            + f"Artwork envelope: {plan['width_mm']:.2f} x {plan['height_mm']:.2f} mm.\n"
            + "Confirm actual machine travel bounds in review.json against your hoop's usable sewing area.\n"
            + "Assumptions: stable woven fabric, suitable stabilizer, 40-weight thread.\n"
            + "No machine or hoop has been selected; no physical sew-out has been performed.\n"
            + "Load threads in threads.json order; DST does not embed these colors.\n"
            + "DST uses three-jump trim requests: verify your machine's interpretation.\n"
            + "Proofs show decoded stitches; thread spread is illustrative, not a sew-out.\n"
            + "Edit plan.json geometry, object sequence, fill angles, spacing or explicit satin rails; export again to a NEW folder.\n\n"
            + "\n".join(plan.get("warnings", [])), encoding="utf-8")
        # A directory rename commits the bundle only after every proof/audit succeeds.
        temporary.rename(destination)
    except BaseException:
        shutil.rmtree(temporary)
        raise
    return destination


def convert_image(source: str | Path, destination: str | Path, settings: Settings = Settings(), formats=("pes", "dst")) -> Path:
    return export_plan(trace_image(source, settings), destination, formats)
