"""Geometry-first draft digitization. Coordinates in editable plans are millimetres.

Raster import makes fill objects and recognizes simple straight satin bars.
It does not infer compound satin columns from lettering.
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
from scipy.ndimage import label, find_objects, binary_erosion
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
    background_mode: str = "auto"
    trim_margins: bool = False
    single_thread_color: str | None = None

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
        if any(type(getattr(self, name)) is not bool for name in ("underlay", "skip_corner_color", "trim_margins")):
            raise ValueError("underlay, skip_corner_color and trim_margins must be booleans.")
        if self.background_mode not in ("auto", "keep", "corner"):
            raise ValueError("Background mode must be auto, keep or corner.")
        if self.single_thread_color is not None and (not isinstance(self.single_thread_color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", self.single_thread_color)):
            raise ValueError("Single thread color must use #RRGGBB.")
        return self


def _polygons(geometry):
    if geometry.is_empty:
        return
    if geometry.geom_type == "Polygon":
        yield geometry
    elif hasattr(geometry, "geoms"):
        for child in geometry.geoms:
            yield from _polygons(child)


def _artwork_palette(pixels, opaque, maximum, background=None):
    """Choose substantive interior hues, not a separate thread for edge shading."""
    interior = binary_erosion(opaque, iterations=2)
    reliable_interior = interior.sum() >= max(8, opaque.sum()*.2)
    seeds = pixels[:, :, :3][interior if reliable_interior else opaque]
    if not reliable_interior and background is not None:
        # Erosion can erase thin dark stems while retaining only thick, pale
        # antialias fringes. Use the stronger half of foreground contrast instead.
        # A relative threshold preserves intentionally pale thin artwork too.
        contrast = np.linalg.norm(seeds.astype(np.float32)-background, axis=1)
        seeds = seeds[contrast >= np.quantile(contrast, .5)]
    quant = Image.fromarray(seeds.reshape(1, -1, 3)).quantize(colors=64, method=Image.Quantize.MEDIANCUT)
    lookup = quant.getpalette()
    candidates = [(count, np.array(lookup[index*3:index*3+3], dtype=np.float32)) for count, index in quant.getcolors()]
    chosen = []
    for count, rgb in sorted(candidates, key=lambda item: item[0], reverse=True):
        if not reliable_interior and background is not None and np.ptp(rgb) <= 12 and any(np.ptp(c) <= 12 for c in chosen):
            # Sparse grayscale stems on paper acquire several gray edge shades;
            # splitting these into thread groups breaks a single letter apart.
            continue
        if chosen and (count < max(3, len(seeds)*.005) or min(np.linalg.norm(rgb-c) for c in chosen) < 65):
            continue
        chosen.append(rgb)
        if len(chosen) == maximum:
            break
    visible = pixels[:, :, :3][opaque].astype(np.float32)
    distance = np.stack([np.sum((visible-color)**2, axis=1) for color in chosen], axis=1)
    return np.array(chosen), distance.argmin(axis=1)


def _straight_satin_bar(polygon):
    """Recognize only a nearly rectangular narrow bar; never infer letter columns."""
    if polygon.interiors:
        return None
    rectangle = polygon.minimum_rotated_rectangle
    if rectangle.is_empty or rectangle.area <= 0 or polygon.area/rectangle.area < .995:
        return None
    corners = list(rectangle.exterior.coords)[:-1]
    lengths = [math.dist(corners[i], corners[(i+1)%4]) for i in range(4)]
    length, width = max(lengths), min(lengths)
    if not .6 <= width <= 3 or length/width < 5:
        return None
    start = lengths.index(length)
    a, b, c, d = [corners[(start+i)%4] for i in range(4)]
    for inset in (0, .025, .05, .075, .1, .15, .2):
        t = inset/length
        interpolate = lambda p, q, f: tuple(x+(y-x)*f for x, y in zip(p, q))
        left = [interpolate(a, b, t), interpolate(a, b, 1-t)]
        right = [interpolate(d, c, t), interpolate(d, c, 1-t)]
        if polygon.buffer(1e-7).covers(Polygon(left+list(reversed(right)))):
            return {"type": "satin", "left": left, "right": right, "auto_stitch_type": "straight rectangular bar"}
    return None


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
    pixels = np.asarray(rgba).copy()
    opaque = pixels[:, :, 3] >= 128
    warnings = ["Automatic raster import creates draft fills and simple straight satin bars. Compound lettering needs manual stitch planning.",
                "No physical sew-out has been performed. Verify hoop, fabric, stabilizer, needle and tension."]
    # Background is an artwork-selection decision, before reducing thread colors.
    # Removing a quantized class would erase ALL artwork when colors == 1.
    mode = "corner" if settings.skip_corner_color else settings.background_mode
    sampled_background = pixels[0, 0, :3].astype(np.float32)
    removed = 0
    if mode == "corner" and opaque[0, 0]:
        distance = np.max(np.abs(pixels[:, :, :3].astype(float) - pixels[0, 0, :3]), axis=2)
        background = opaque & (distance <= 32)
        removed = int(background.sum())
        opaque[background] = False
        warnings.append("Pixels matching the top-left background were excluded before choosing thread colors, including matching interior areas.")
    elif mode == "corner":
        warnings.append("The top-left pixel is transparent; no additional background was removed.")
    elif mode == "auto":
        light = np.min(pixels[:, :, :3], axis=2) >= 235
        border = np.concatenate((light[0], light[-1], light[:, 0], light[:, -1]))
        border_opaque = np.concatenate((opaque[0], opaque[-1], opaque[:, 0], opaque[:, -1]))
        if border_opaque.mean() > .9 and (border & border_opaque).mean() > .75:
            background = opaque & light
            removed = int(background.sum())
            opaque[background] = False
            warnings.append("Light paper background removed, including matching interior areas. Choose Keep background if those areas should be white thread.")
    if removed:
        pixels[~opaque, 3] = 0
    if settings.trim_margins and opaque.any():
        ys, xs = np.where(opaque)
        pixels = pixels[ys.min():ys.max()+1, xs.min():xs.max()+1]
        opaque = opaque[ys.min():ys.max()+1, xs.min():xs.max()+1]
        rgba = Image.fromarray(pixels)
    if not opaque.any():
        raise ValueError("No opaque artwork remains. Choose Keep background or use an image with visible foreground shapes.")
    # Count distinct foreground hues. A requested maximum is not a demand to
    # turn antialias bands and slight shading into extra physical thread colors.
    background_rgb = (np.array([255, 255, 255], dtype=np.float32) if mode == "auto" else sampled_background) if removed else None
    if removed and binary_erosion(opaque, iterations=2).sum() < max(8, opaque.sum()*.2):
        warnings.append("Thin raster strokes: edge colors may be ambiguous. For monochrome text, choose one thread and a thread color; use the original vector artwork for detailed lettering.")
    colors, assigned = _artwork_palette(pixels, opaque, settings.colors, background_rgb)
    indices = np.full(opaque.shape, -1, dtype=np.int16)
    indices[opaque] = assigned
    if removed:
        rgb = pixels[:, :, :3][opaque].astype(np.float32)
        foreground_rgb = colors[assigned]
        vector = foreground_rgb-background_rgb
        coverage = np.sum((rgb-background_rgb)*vector, axis=1) / np.maximum(1, np.sum(vector*vector, axis=1))
        # Restore the half-coverage outline of antialiased art on paper. Pale
        # fringe pixels outside that outline are background, not extra stitches.
        keep = coverage >= .5
        yy, xx = np.where(opaque)
        opaque[yy[~keep], xx[~keep]] = False
        indices[~opaque] = -1
    palette = [int(value) for color in colors for value in color]
    scale = settings.width_mm / rgba.width
    if settings.colors == 1:
        # A single thread follows the foreground silhouette. Use a real dominant
        # foreground color, rather than averaging paper/antialias pixels into it.
        if settings.single_thread_color:
            palette[:3] = [int(settings.single_thread_color[i:i+2], 16) for i in (1, 3, 5)]
        if not removed and opaque.all():
            warnings.append("One thread with an opaque background creates a filled silhouette of the entire image. Remove the background to preserve the artwork shape.")
    excluded = -1
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
                obj = {"id": f"object-{len(objects)+len(group)+1}", "type": "fill",
                              "thread": thread_index, "geometry": mapping(polygon),
                              "angle_deg": settings.angle_deg,
                              "spacing_mm": settings.spacing_mm, "underlay": settings.underlay}
                bar = _straight_satin_bar(polygon)
                if bar:
                    obj.update(bar)
                group.append(obj)
        if group:
            objects.extend(group)
            threads.append({"hex": "#" + "".join(f"{n:02X}" for n in rgb), "description": f"Color {thread_index+1}"})
        if len(objects) > MAX_OBJECTS:
            raise ValueError("Too many objects. Simplify the image or increase minimum area.")
    if not objects:
        raise ValueError("No objects remain. Lower minimum area or include the background color.")
    if discarded:
        warnings.append(f"Discarded {discarded} regions below the minimum area setting.")
    if len(threads) < settings.colors:
        warnings.append(f"Using {len(threads)} distinct foreground color(s); similar edge shades do not need extra threads.")
    narrow = sum(shape(obj["geometry"]).buffer(-.3).is_empty for obj in objects)
    bars = sum(obj.get("auto_stitch_type") == "straight rectangular bar" for obj in objects)
    if bars:
        warnings.append(f"Used satin across {bars} straight narrow rectangular bar(s). Compound lettering still needs manual stitch planning.")
    if narrow:
        warnings.append(f"Fine-detail warning: {narrow} shapes are too narrow for underlay. Small text may merge or lose counters; use larger, cleaner artwork or manual lettering digitization.")
    if max(original_size) < 400:
        warnings.append("Low-resolution source: enlarge the original vector artwork before importing; stretching this image cannot restore missing detail.")
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
    if polygon.is_empty:
        return []
    if not polygon.is_valid or not all(math.isfinite(v) for v in polygon.bounds):
        raise ValueError("Cannot plan stitches for invalid or non-finite fill geometry.")
    rotated = rotate(polygon, -angle, origin=(0, 0))
    covered = rotated.buffer(.00001)
    rings = [LineString(rotated.exterior.coords)] + [LineString(r.coords) for r in rotated.interiors]
    # Put curved edge transfers a little inside the fill where possible. This
    # avoids reproducing each raster staircase vertex as a needle penetration.
    inner_rings = []
    for part in _polygons(rotated.buffer(-.12)):
        inner_rings.extend([LineString(part.exterior.coords)] + [LineString(r.coords) for r in part.interiors])

    def ring_routes(ring, a, b):
        da, db = ring.project(Point(a)), ring.project(Point(b))
        lo, hi = sorted((da, db))
        direct = list(substring(ring, lo, hi).coords)
        around = list(substring(ring, hi, ring.length).coords) + list(substring(ring, 0, lo).coords)
        if da > db:
            direct.reverse()
        else:
            around.reverse()
        return sorted((direct, around), key=lambda path: LineString(path).length if len(path) > 1 else 0)

    def compact_route(route):
        # Projection/contour vertices guide geometry; they are not all required
        # needle positions. Skip a vertex only when the whole chord stays covered.
        result, i = [route[0]], 0
        while i < len(route)-1:
            j = len(route)-1
            while j > i+1 and not covered.covers(LineString([route[i], route[j]])):
                j -= 1
            result.append(route[j])
            i = j
        return result

    def connect(a, b):
        if math.dist(a, b) > 8:
            return None
        if covered.covers(LineString([a, b])):
            return [a, b]
        for ring in inner_rings:
            if ring.distance(Point(a)) > .4 or ring.distance(Point(b)) > .4:
                continue
            route = ring_routes(ring, a, b)[0]
            smooth = list(LineString(route).simplify(.08).coords) if len(route) > 1 else route
            candidate = [a] + smooth + [b]
            if LineString(candidate).length <= 8 and covered.covers(LineString(candidate)):
                return compact_route(candidate)
        # Follow the actual boundary between adjacent rows when a straight chord
        # would cut across a curved counter or fall outside a curved edge.
        for ring in rings:
            if ring.distance(Point(a)) > .0001 or ring.distance(Point(b)) > .0001:
                continue
            route = ring_routes(ring, a, b)[0]
            if len(route) > 1 and LineString(route).length <= 8:
                # Trace vertices are not needle positions. A 0.03 mm geometric
                # simplification stays below the machine's 0.1 mm coordinate grid.
                smooth = list(LineString(route).simplify(.03).coords)
                candidate = [a] + smooth + [b]
                if not covered.covers(LineString(candidate)):
                    candidate = [a] + route + [b]
                if covered.covers(LineString(candidate)):
                    return compact_route(candidate)
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
            if len(distances) > 2 and distances[-1]-distances[-2] < .4:
                distances.pop(-2)
                if distances[-1]-distances[-2] > stitch:
                    distances.insert(-1, (distances[-1]+distances[-2])/2)
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
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("Stitch planning produced a non-finite coordinate.")
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
        paths = []
        if obj["type"] == "fill":
            polygon = shape(obj["geometry"])
            angle = obj.get("angle_deg", settings.angle_deg)
            if obj.get("underlay", settings.underlay):
                inset = polygon.buffer(-.3)
                for part in _polygons(inset):
                    for path in fill_paths(part, 2.5, angle+90, settings.stitch_mm):
                        paths.append((path, settings.stitch_mm))
            for path in fill_paths(polygon, obj.get("spacing_mm", settings.spacing_mm), angle, settings.stitch_mm):
                paths.append((path, settings.stitch_mm))
        else:
            for path in _satin_paths(obj):
                paths.append((path, 7.0))
        paths = [(path, maximum) for path, maximum in paths if len(path) >= 2 and sum(math.dist(a, b) for a, b in zip(path, path[1:])) >= .3]
        if not paths:
            builder.spans.append({"id": obj.get("id", ""), "start": len(builder.pattern.stitches),
                                  "end": len(builder.pattern.stitches), "skipped": "too small for usable stitches"})
            continue
        index = obj["thread"]
        if index != active_thread:
            if active_thread is not None:
                builder.emit(emb.COLOR_CHANGE, builder.cursor)
            builder.pattern.add_thread({"hex": plan["threads"][index]["hex"], "description": plan["threads"][index].get("description", "")})
            active_thread = index
        start = len(builder.pattern.stitches)
        for path, maximum in paths:
            builder.path(path, maximum)
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
