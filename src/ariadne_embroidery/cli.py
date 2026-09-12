"""Command-line entry point. Errors are actionable and return a nonzero status."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core import Settings, convert_image, export_plan, load_plan, trace_image


def main(argv=None):
    parser = argparse.ArgumentParser(description="Ariadne: free offline embroidery drafting")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("convert", "trace"):
        p = commands.add_parser(name, help="Create a draft bundle" if name == "convert" else "Create an editable geometry plan")
        p.add_argument("image", type=Path)
        p.add_argument("output", type=Path)
        p.add_argument("--width", type=float, default=100, help="Design width in mm (default 100)")
        p.add_argument("--colors", type=int, default=4)
        p.add_argument("--spacing", type=float, default=.42, help="Fill row spacing in mm")
        p.add_argument("--angle", type=float, default=0)
        p.add_argument("--min-area", type=float, default=.6, help="Discard regions smaller than this area in mm²")
        p.add_argument("--no-underlay", action="store_true")
        p.add_argument("--skip-corner-color", action="store_true", help="Exclude the whole palette color at the top-left pixel")
        if name == "convert":
            p.add_argument("--format", nargs="+", choices=("pes", "dst"), default=["pes", "dst"])
    p = commands.add_parser("export", help="Digitize an edited plan into a new bundle")
    p.add_argument("plan", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--format", nargs="+", choices=("pes", "dst"), default=["pes", "dst"])
    commands.add_parser("gui", help="Open the local desktop studio")
    args = parser.parse_args(argv)
    try:
        if args.command == "gui":
            from .gui import main as gui_main
            gui_main()
            return 0
        if args.command in ("convert", "trace"):
            settings = Settings(width_mm=args.width, colors=args.colors, spacing_mm=args.spacing,
                                angle_deg=args.angle, min_area_mm2=args.min_area, underlay=not args.no_underlay,
                                skip_corner_color=args.skip_corner_color)
            if args.command == "convert":
                result = convert_image(args.image, args.output, settings, args.format)
            else:
                plan = trace_image(args.image, settings)
                with args.output.open("x", encoding="utf-8") as file:
                    json.dump(plan, file, indent=2, allow_nan=False)
                result = args.output
        else:
            result = export_plan(load_plan(args.plan), args.output, args.format)
        print(f"Created {result}\nDraft only: inspect decoded proofs and test sew before production.")
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f"Ariadne: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
