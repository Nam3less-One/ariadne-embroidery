"""Regression inputs independently reproduced from the 0.1.0 color failures."""

from dataclasses import asdict
import json
import math

from PIL import Image, ImageDraw
import pyembroidery as emb
import pytest
from shapely.geometry import LineString, Point, Polygon, box, mapping, shape
from shapely.ops import unary_union

from ariadne_embroidery.core import Settings, export_plan, fill_paths, trace_image


def _decoded_bundle(plan, target):
    output = export_plan(plan, target)
    audits = json.loads((output / "review.json").read_text())["files"]
    for extension in ("pes", "dst"):
        decoded = emb.read(str(output / f"design.{extension}"))
        assert decoded.stitches[-1][2] & emb.COMMAND_MASK == emb.END
        assert all(math.isfinite(x) and math.isfinite(y) for x, y, _ in decoded.stitches)
        assert audits[extension]["untrimmed_transfers_over_2_mm"] == 0
        assert audits[extension]["max_stitch_mm"] <= 7.2
        assert audits[extension]["command_counts"]["STITCH"] > 0
    return output, audits


@pytest.mark.parametrize("transparent", [False, True])
@pytest.mark.parametrize("colors", [1, 2, 4])
def test_thin_multicolor_regions_export_without_nan(tmp_path, transparent, colors):
    # The rule survives area filtering, but its 0.39 mm thickness cannot fit
    # the 0.3 mm inset on each side. This was the reported NaN crash.
    image = Image.new("RGBA", (256, 192), (255, 255, 255, 0 if transparent else 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 25, 95, 100), fill="#185D44")
    draw.ellipse((125, 30, 215, 120), fill="#E48B30")
    draw.rectangle((35, 150, 220, 150), fill="#185D44")
    source = tmp_path / "thin-rule.png"
    image.save(source)
    plan = trace_image(source, Settings(width_mm=100, colors=colors, underlay=True))
    assert any(shape(obj["geometry"]).buffer(-.3).is_empty for obj in plan["objects"])
    _, audits = _decoded_bundle(plan, tmp_path / "bundle")
    assert len(audits["pes"]["threads"]) == min(colors, 2)


@pytest.mark.parametrize("thickness", [.05, .2, .59, .6, .61])
def test_collapsed_underlay_retains_the_top_stitches(tmp_path, thickness):
    polygon = box(2, 2, 22, 2 + thickness)
    plan = {
        "schema": "ariadne-plan", "version": 1, "units": "mm",
        "width_mm": 30, "height_mm": 20,
        "settings": asdict(Settings(width_mm=30)),
        "threads": [{"hex": "#185D44"}],
        "objects": [{"id": "thin", "type": "fill", "thread": 0,
                     "underlay": True, "geometry": mapping(polygon)}],
    }
    _decoded_bundle(plan, tmp_path / "thin")


@pytest.mark.parametrize("background", ["auto", "corner"])
def test_one_thread_preserves_ring_counter_and_foreground_color(tmp_path, background):
    image = Image.new("RGB", (128, 96), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((16, 8, 112, 88), fill="#185D44")
    draw.ellipse((37, 28, 91, 68), fill="white")
    source = tmp_path / "ring.png"
    image.save(source)
    plan = trace_image(source, Settings(width_mm=50, colors=1, background_mode=background))
    outline = unary_union([shape(obj["geometry"]) for obj in plan["objects"]])
    assert not outline.covers(Point(25, 18.75))
    assert not outline.covers(Point(1, 1))
    assert outline.covers(Point(9, 18.75))
    assert len(plan["objects"]) == 1
    assert len(shape(plan["objects"][0]["geometry"]).interiors) == 1
    assert plan["threads"] == [{"hex": "#185D44", "description": "Color 1"}]
    _, audits = _decoded_bundle(plan, tmp_path / "ring")
    assert len(audits["pes"]["threads"]) == 1


def test_explicit_keep_background_preserves_full_field(tmp_path):
    image = Image.new("RGB", (100, 80), "white")
    ImageDraw.Draw(image).rectangle((25, 20, 75, 60), fill="#185D44")
    source = tmp_path / "patch.png"
    image.save(source)
    plan = trace_image(source, Settings(width_mm=50, colors=2, background_mode="keep"))
    outline = unary_union([shape(obj["geometry"]) for obj in plan["objects"]])
    assert {thread["hex"] for thread in plan["threads"]} == {"#FFFFFF", "#185D44"}
    assert outline.covers(Point(1, 1))
    assert outline.area == pytest.approx(2000, abs=.2)


def test_transparent_white_artwork_is_not_deleted(tmp_path):
    image = Image.new("RGBA", (100, 80), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 40, 60), fill="#FFFFFF")
    draw.rectangle((55, 10, 85, 60), fill="#185D44")
    source = tmp_path / "white-artwork.png"
    image.save(source)
    plan = trace_image(source, Settings(width_mm=50, colors=2))
    assert {thread["hex"] for thread in plan["threads"]} == {"#FFFFFF", "#185D44"}
    assert len(plan["objects"]) == 2


@pytest.mark.parametrize("tiny_position", [0, 1, 2])
def test_empty_color_group_does_not_create_phantom_thread(tmp_path, tiny_position):
    polygons = [box(4, 4, 10, 10), box(14, 4, 20, 10)]
    colors = ["#185D44", "#E48B30"]
    polygons.insert(tiny_position, box(1, 1, 1.1, 1.1))
    colors.insert(tiny_position, "#0000FF")
    plan = {
        "schema": "ariadne-plan", "version": 1, "units": "mm",
        "width_mm": 30, "height_mm": 20,
        "settings": asdict(Settings(width_mm=30, underlay=False, min_area_mm2=0)),
        "threads": [{"hex": color} for color in colors],
        "objects": [{"id": f"object-{i}", "type": "fill", "thread": i,
                     "underlay": False, "geometry": mapping(polygon)}
                    for i, polygon in enumerate(polygons)],
    }
    _, audits = _decoded_bundle(plan, tmp_path / "sparse")
    for extension in ("pes", "dst"):
        assert [thread["hex"].upper() for thread in audits[extension]["threads"]] == ["#185D44", "#E48B30"]
        assert audits[extension]["command_counts"]["COLOR_CHANGE"] == 1


def test_margin_trim_changes_dimensions_without_losing_counter(tmp_path):
    image = Image.new("RGBA", (160, 120), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 30, 119, 89), fill="#185D44")
    draw.rectangle((65, 45, 94, 74), fill=(0, 0, 0, 0))
    source = tmp_path / "margin.png"
    image.save(source)
    plan = trace_image(source, Settings(width_mm=40, colors=1, trim_margins=True, single_thread_color="#CC0000"))
    outline = shape(plan["objects"][0]["geometry"])
    assert plan["width_mm"] == 40
    assert plan["height_mm"] == 30
    assert outline.bounds == pytest.approx((0, 0, 40, 30))
    assert len(outline.interiors) == 1
    assert plan["threads"][0]["hex"] == "#CC0000"


@pytest.mark.parametrize("maximum", [3, 6, 12])
def test_extra_requested_colors_do_not_turn_antialias_into_threads(tmp_path, maximum):
    # Draw at four times the import resolution to create genuine antialias
    # edge shades around three substantive hues.
    image = Image.new("RGB", (800, 400), "white")
    draw = ImageDraw.Draw(image)
    hues = ["#185D44", "#E48B30", "#245AB8"]
    for (cx, cy), hue in zip([(135, 195), (405, 195), (665, 195)], hues):
        draw.ellipse((cx - 90, cy - 90, cx + 90, cy + 90), fill=hue)
    image = image.resize((200, 100), Image.Resampling.LANCZOS)
    source = tmp_path / "three-hues-antialias.png"
    image.save(source)
    plan = trace_image(source, Settings(width_mm=60, colors=maximum, trim_margins=True))
    assert {thread["hex"] for thread in plan["threads"]} == set(hues)
    assert len(plan["objects"]) == 3
    _, audits = _decoded_bundle(plan, tmp_path / "three-hues")
    assert len(audits["pes"]["threads"]) == 3


def test_antialiased_white_on_alpha_remains_a_real_thread(tmp_path):
    image = Image.new("RGBA", (600, 400), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((30, 30, 260, 350), fill="#FFFFFF")
    draw.ellipse((340, 30, 570, 350), fill="#185D44")
    image = image.resize((150, 100), Image.Resampling.LANCZOS)
    source = tmp_path / "alpha-white-antialias.png"
    image.save(source)
    plan = trace_image(source, Settings(width_mm=60, colors=8, trim_margins=True))
    assert {thread["hex"] for thread in plan["threads"]} == {"#FFFFFF", "#185D44"}
    assert len(plan["objects"]) == 2
    _decoded_bundle(plan, tmp_path / "alpha-white")


def test_corner_matte_is_sampled_before_trimming(tmp_path):
    image = Image.new("RGB", (100, 80), "#285082")
    draw = ImageDraw.Draw(image)
    # 25% foreground coverage stays outside the foreground silhouette.
    # Its RGB distance from the background exceeds the initial corner mask.
    draw.rectangle((19, 19, 80, 60), fill="#524875")
    draw.rectangle((20, 20, 79, 59), fill="#D03050")
    source = tmp_path / "colored-paper.png"
    image.save(source)
    plan = trace_image(source, Settings(width_mm=62, colors=4, background_mode="corner", trim_margins=True))
    assert len(plan["objects"]) == 1
    assert plan["threads"][0]["hex"] == "#D03050"
    outline = shape(plan["objects"][0]["geometry"])
    assert outline.covers(Point(31, 21))
    assert not outline.covers(Point(.2, 21))
    assert outline.bounds == pytest.approx((1, 1, 61, 41))


@pytest.mark.parametrize("swatch", [123, True, [], {}, "red", "#GG0000"])
def test_invalid_single_thread_swatch_has_controlled_error(swatch):
    with pytest.raises(ValueError, match="Single thread color"):
        Settings(single_thread_color=swatch).validate()


def test_compacted_narrow_ring_transfers_preserve_the_counter():
    # A 0.2 mm ring has no usable inset route. Simplifying its inner boundary
    # must not shortcut through the counter, even when the excursion is small.
    center = Point(20, 20)
    ring = center.buffer(16, quad_segs=32).difference(center.buffer(15.8, quad_segs=32))
    paths = fill_paths(ring, .42, 17, 3)
    assert paths
    for path in paths:
        for start, end in zip(path, path[1:]):
            assert ring.buffer(1e-6).covers(LineString([start, end]))
            assert math.dist(start, end) <= 3.00001


@pytest.mark.parametrize("ink, colored_fringe", [("#353535", True), ("#E6B4C5", False)])
def test_sparse_cores_use_relative_contrast_without_erasing_pale_ink(tmp_path, ink, colored_fringe):
    # Original synthetic sparse-core input is generated publicly by this test.
    # One-pixel stems disappear under erosion; a handful of wider fringe
    # patches must not overrule hundreds of substantive dark stem pixels.
    image = Image.new("RGB", (180, 80), "white")
    draw = ImageDraw.Draw(image)
    for x in range(15, 166, 15):
        draw.line((x, 15, x, 64), fill=ink)
    draw.line((15, 40, 165, 40), fill=ink)
    if colored_fringe:
        for x in (35, 80, 125):
            draw.rectangle((x, 50, x + 6, 56), fill="#FEF8B9")
    source = tmp_path / "sparse-strokes.png"
    image.save(source)
    plan = trace_image(source, Settings(width_mm=80, colors=1, trim_margins=True))
    assert len(plan["threads"]) == 1
    assert plan["threads"][0]["hex"] == ink
    assert any("thin raster" in warning.lower() for warning in plan["warnings"])
    _decoded_bundle(plan, tmp_path / "sparse-strokes")


@pytest.mark.parametrize("transparent", [False, True])
def test_intentional_broad_gray_areas_keep_distinct_threads(tmp_path, transparent):
    image = Image.new("RGBA", (180, 90), (255, 255, 255, 0 if transparent else 255))
    draw = ImageDraw.Draw(image)
    hues = ["#000000", "#555555", "#AAAAAA"]
    for x, hue in zip((10, 65, 120), hues):
        draw.rectangle((x, 10, x + 40, 79), fill=hue)
    source = tmp_path / "intentional-gray-areas.png"
    image.save(source)
    plan = trace_image(source, Settings(width_mm=60, colors=8, trim_margins=True))
    assert {thread["hex"] for thread in plan["threads"]} == set(hues)
    assert len(plan["objects"]) == 3


def test_transparent_thin_gray_artwork_keeps_distinct_threads(tmp_path):
    image = Image.new("RGBA", (120, 80), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    hues = ["#000000", "#555555", "#FFFFFF"]
    for x, hue in zip((20, 60, 100), hues):
        draw.line((x, 10, x, 69), fill=hue)
    source = tmp_path / "transparent-thin-gray.png"
    image.save(source)
    plan = trace_image(source, Settings(width_mm=60, colors=8))
    assert {thread["hex"] for thread in plan["threads"]} == set(hues)
