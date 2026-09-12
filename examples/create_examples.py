"""Create original, redistributable geometric artwork and an explicit satin plan."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).parent
image = Image.new("RGBA", (600, 500), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
draw.ellipse((65, 35, 355, 325), fill="#286B62")
draw.ellipse((130, 100, 290, 260), fill=(0, 0, 0, 0))
draw.polygon([(390, 65), (555, 325), (330, 325)], fill="#C47939")
draw.rounded_rectangle((70, 375, 535, 440), radius=25, fill="#286B62")
image.save(root/"geometric-mark.png")
plan = {"schema": "ariadne-plan", "version": 1, "units": "mm", "status": "draft",
        "width_mm": 40, "height_mm": 40, "settings": {},
        "threads": [{"hex": "#286B62", "description": "Deep teal"}],
        "objects": [{"id": "satin-column", "type": "satin", "thread": 0,
                     "left": [[8, 5], [8, 30], [28, 30]],
                     "right": [[12, 5], [12, 26], [28, 26]],
                     "spacing_mm": .4, "underlay": True}],
        "warnings": ["Original demonstration of paired satin rails. Review the corner and test sew."]}
(root/"satin-plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
