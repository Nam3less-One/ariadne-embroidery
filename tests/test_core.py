import copy
import json
import math
import re
from pathlib import Path

import pyembroidery as emb
import pytest
from PIL import Image, ImageDraw
from shapely.geometry import LineString, Polygon, shape

from ariadne_embroidery.core import Settings, convert_image, digitize, export_plan, fill_paths, load_plan, trace_image, validate_plan
from ariadne_embroidery.cli import main


@pytest.fixture
def artwork(tmp_path):
    image = Image.new("RGBA", (160, 120), (255, 0, 255, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 100, 110), fill="#226655")
    draw.rectangle((30, 30, 70, 75), fill=(0, 0, 0, 0))
    draw.rectangle((120, 10, 150, 50), fill="#DD9933")
    path = tmp_path/"source.png"
    image.save(path)
    return path


def test_trace_preserves_hole_alpha_and_colors(artwork):
    plan = trace_image(artwork, Settings(width_mm=40, colors=2, resolution=256))
    assert len(plan["threads"]) == 2
    assert len(plan["objects"]) == 2
    assert sum(len(shape(obj["geometry"]).interiors) for obj in plan["objects"]) == 1
    assert plan["height_mm"] == 30
    assert {thread["hex"] for thread in plan["threads"]} == {"#226655", "#DD9933"}


@pytest.mark.parametrize("angle", [0, 37, 90, -125])
def test_paths_never_cross_holes(angle):
    polygon = Polygon([(0, 0), (30, 0), (30, 25), (0, 25)], holes=[[(8, 5), (22, 5), (22, 19), (8, 19)]])
    paths = fill_paths(polygon, .42, angle, 3)
    assert paths
    for path in paths:
        for a, b in zip(path, path[1:]):
            assert polygon.buffer(1e-6).covers(LineString([a, b]))
            assert math.dist(a, b) <= 3.00001


def test_roundtrip_bundle_and_dst_header(artwork, tmp_path):
    result = convert_image(artwork, tmp_path/"bundle", Settings(width_mm=40, colors=2))
    report = json.loads((result/"review.json").read_text())
    assert report["status"] == "draft_requires_review"
    assert report["independent_score"] is None
    for fmt in ("pes", "dst"):
        pattern = emb.read(str(result/f"design.{fmt}"))
        assert pattern.stitches[-1][2] & emb.COMMAND_MASK == emb.END
        assert report["files"][fmt]["max_stitch_mm"] <= 7.2
        assert report["files"][fmt]["untrimmed_transfers_over_2_mm"] == 0
        assert (result/f"design-{fmt}-proof.png").is_file()
    data = (result/"design.dst").read_bytes()
    assert int(re.search(rb"ST:([ 0-9]{7})", data[:512])[1]) == (len(data)-512)//3
    assert data[-3:] == b"\x00\x00\xf3"
    raw = emb.read(str(result/"design.dst"), settings={"clipping": False})
    xs, ys = [0]+[s[0] for s in raw.stitches], [0]+[s[1] for s in raw.stitches]
    for key, value in {"+X": max(xs), "-X": -min(xs), "+Y": max(ys), "-Y": -min(ys)}.items():
        assert int(re.search(re.escape(key.encode())+rb":([ 0-9]{5})", data[:512])[1]) == value
    assert report["files"]["dst"]["travel_bounds_mm"] == [min(xs)/10, min(ys)/10, max(xs)/10, max(ys)/10]
    assert report["files"]["dst"]["zero_length_stitches"] == 0
    master = emb.read(str(result/"stitch-master.json"))
    dst = emb.read(str(result/"design.dst"))
    endpoints = lambda pattern: [(round(x), round(y)) for x, y, c in pattern.stitches if c & emb.COMMAND_MASK == emb.STITCH]
    assert endpoints(master) == endpoints(dst)
    with pytest.raises(FileExistsError):
        export_plan(load_plan(result/"plan.json"), result)


def test_invalid_settings_and_transparency(tmp_path):
    for kwargs in ({"width_mm": float("nan")}, {"spacing_mm": 0}, {"colors": 2.5}, {"resolution": 99999}, {"underlay": "no"}):
        with pytest.raises(ValueError):
            Settings(**kwargs).validate()
    path = tmp_path/"empty.png"
    Image.new("RGBA", (10, 10)).save(path)
    with pytest.raises(ValueError, match="opaque"):
        trace_image(path)


def test_invalid_plan_rejected(artwork):
    plan = trace_image(artwork, Settings(width_mm=40, colors=2))
    for key, value in (("thread", -1), ("type", "unknown"), ("spacing_mm", float("inf"))):
        changed = copy.deepcopy(plan)
        changed["objects"][0][key] = value
        with pytest.raises(ValueError):
            validate_plan(changed)


def test_background_exclusion(artwork):
    # Transparent corner must not delete an actual thread.
    plan = trace_image(artwork, Settings(width_mm=40, colors=2, skip_corner_color=True))
    assert len(plan["threads"]) == 2


def test_cli_failure_has_nonzero_status(tmp_path, capsys):
    assert main(["convert", str(tmp_path/"missing.png"), str(tmp_path/"out")]) == 2
    assert "Ariadne:" in capsys.readouterr().err


def test_satin_plan_roundtrip(tmp_path):
    path = Path(__file__).parents[1]/"examples"/"satin-plan.json"
    plan = load_plan(path)
    pattern, _ = digitize(plan)
    assert len(pattern.stitches) > 100
    result = export_plan(plan, tmp_path/"satin")
    assert (result/"design.pes").is_file()


def test_failure_does_not_leave_partial_bundle(artwork, tmp_path, monkeypatch):
    from ariadne_embroidery import proof
    plan = trace_image(artwork, Settings(width_mm=40, colors=2))
    def fail(*args, **kwargs):
        raise ValueError("Simulated decoder rejection")
    monkeypatch.setattr(proof, "render_proof", fail)
    with pytest.raises(ValueError, match="decoder"):
        export_plan(plan, tmp_path/"incomplete")
    assert not (tmp_path/"incomplete").exists()
    assert not list(tmp_path.glob(".ariadne-*"))


def test_curved_sample_has_no_duplicate_dst_needles(tmp_path):
    source = Path(__file__).parents[1]/"examples"/"geometric-mark.png"
    result = convert_image(source, tmp_path/"curves", Settings(width_mm=80, colors=2, spacing_mm=.4))
    report = json.loads((result/"review.json").read_text())["files"]["dst"]
    assert report["zero_length_stitches"] == 0
    assert report["command_counts"]["TRIM"] < 20


def test_invalid_format_never_creates_output(artwork, tmp_path):
    plan = trace_image(artwork, Settings(width_mm=40, colors=2))
    with pytest.raises(ValueError, match="formats"):
        export_plan(plan, tmp_path/"wrong-format", ["jef"])
    assert not (tmp_path/"wrong-format").exists()
