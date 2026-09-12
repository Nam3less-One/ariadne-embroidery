# Editable plans

`ariadne trace` separates geometry editing from stitch export. Edit the JSON in a text editor, then `ariadne export plan.json NEW-folder`. The desktop app also opens a plan, preserving its stored settings. It does not yet have a graphical vector editor.

The format has `schema: "ariadne-plan"`, `version: 1`, and `units: "mm"`. Coordinates use a top-left origin, positive X right and Y down. Machine exports are centered on the canvas. `width_mm` and `height_mm` describe the canvas, including empty margins. Scaling those numbers alone does not scale geometry: transform coordinates together, then redigitize to preserve spacing.

`threads` is a list of `{ "hex": "#RRGGBB", "description": "Name" }`. Each object refers to a zero-based thread index. Objects stitch in list order; switching back to an earlier color creates another operator color block. `threads.json` in the output records this expanded sequence.

## Fill objects

```json
{
  "id": "square",
  "type": "fill",
  "thread": 0,
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[5,5],[35,5],[35,35],[5,35],[5,5]]]
  },
  "angle_deg": 0,
  "spacing_mm": 0.42,
  "underlay": true
}
```

Geometry uses GeoJSON Polygon coordinates: exterior first, optional hole rings afterward. Use valid, nonintersecting closed rings inside the canvas. Arbitrarily overlapping objects are allowed for intentional layering; the app does not resolve excessive layered density for you. A fill angle of 0 makes horizontal rows; 90 makes vertical rows. Underlay uses a 0.3 mm inset, rows perpendicular to the top fill, and 2.5 mm row spacing. Empty insets are skipped.

## Satin objects

```json
{
  "id": "column",
  "type": "satin",
  "thread": 0,
  "left": [[5,5],[5,30]],
  "right": [[9,5],[9,30]],
  "spacing_mm": 0.4,
  "underlay": true
}
```

Rails must have equal numbers of corresponding stations, with widths between 0.6 and 7 mm. They are sampled according to the longer rail distance to improve curved coverage. Satin spacing denotes approximately the same-side penetration pitch; alternating stations use half that spacing. Underlay is a center walk. Keep rails simple and review corners, caps, compensation and coverage. The engine does not infer branching satin strokes, edge-run underlay or automatic pull compensation. Decompose complex letters manually into suitable columns; don't approximate them with one crossing rail pair.

## Limits

Raster settings: 1–12 colors, width 10–400 mm, spacing 0.25–1.2 mm, fill stitch length 1–5 mm, trace resolution 128–1200 pixels. Plans require a canvas between 1 and 400 mm on each axis, at most 2,500 objects and 100,000 vertices. A design stops above 250,000 commands. These resource limits are not hoop compatibility claims.

Small regions below `min_area_mm2` are discarded and counted in warnings. Anti-aliasing and reduction can create extra colors or modify very fine features. Source metadata records the original filename and SHA-256, not its absolute location. A bundle contains traced geometry, so treat it as artwork when sharing.
