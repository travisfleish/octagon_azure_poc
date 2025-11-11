#!/usr/bin/env python3
"""
Generate a PNG flow diagram for the Staffing Plan Generator data flow.
"""

from pathlib import Path
from math import atan2, cos, sin
from PIL import Image, ImageDraw, ImageFont


def draw_centered_text(draw: ImageDraw.ImageDraw, xy: tuple, box_w: int, box_h: int, text: str, font: ImageFont.FreeTypeFont, fill=(0, 0, 0)):
    x, y = xy
    lines = []
    for line in text.split("\n"):
        lines.append(line)
    line_heights = []
    max_line_w = 0
    for line in lines:
        w, h = draw.textbbox((0, 0), line, font=font)[2:]
        max_line_w = max(max_line_w, w)
        line_heights.append(h)
    total_h = sum(line_heights) + (len(lines) - 1) * 6
    start_y = y + (box_h - total_h) // 2
    for i, line in enumerate(lines):
        w, h = draw.textbbox((0, 0), line, font=font)[2:]
        draw.text((x + (box_w - w) // 2, start_y), line, font=font, fill=fill)
        start_y += h + 6


def draw_box(draw: ImageDraw.ImageDraw, top_left: tuple, size: tuple, text: str, font: ImageFont.FreeTypeFont, fill=(255, 255, 255), outline=(0, 0, 0)):
    x, y = top_left
    w, h = size
    draw.rectangle([x, y, x + w, y + h], fill=fill, outline=outline, width=2)
    draw_centered_text(draw, (x, y), w, h, text, font)


def draw_arrow(draw: ImageDraw.ImageDraw, start: tuple, end: tuple, color=(0, 0, 0), width=3, head_len=16, head_w=10):
    x1, y1 = start
    x2, y2 = end
    draw.line([x1, y1, x2, y2], fill=color, width=width)
    angle = atan2(y2 - y1, x2 - x1)
    hx = x2 - head_len * cos(angle)
    hy = y2 - head_len * sin(angle)
    left = (hx + head_w * sin(angle), hy - head_w * cos(angle))
    right = (hx - head_w * sin(angle), hy + head_w * cos(angle))
    draw.polygon([end, left, right], fill=color)


def main():
    project_root = Path(__file__).resolve().parents[2]
    out_dir = project_root / "docs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "staffing_flow_diagram.png"

    img_w, img_h = 1400, 1100
    img = Image.new("RGB", (img_w, img_h), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("Arial.ttf", 20)
        title_font = ImageFont.truetype("Arial.ttf", 28)
        small_font = ImageFont.truetype("Arial.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
        title_font = font
        small_font = font

    # Title
    title = "Streamlit App Functions and Data Flow – Staffing Plan Generator POC"
    title_w, title_h = draw.textbbox((0, 0), title, font=title_font)[2:]
    draw.text(((img_w - title_w) // 2, 30), title, font=title_font, fill=(0, 0, 0))

    # Boxes layout (services)
    box_w, box_h = 320, 110  # service box size
    x_center = img_w // 2

    # Row Y positions
    y1 = 110   # Streamlit app
    y2 = y1 + 130  # function row
    y3 = y2 + 170  # extraction/structured JSON
    y4 = y3 + 170  # storage/indexing
    y5 = y4 + 170  # cognitive search
    y6 = y5 + 170  # generator note (optional)

    # Streamlit App header box
    app_box_w = 360
    app_box_h = 90
    app_box = (x_center - app_box_w // 2, y1)
    draw_box(draw, app_box, (app_box_w, app_box_h), "Streamlit App (app.py)\nFour Functions", font)

    # Function row (4 boxes)
    func_w, func_h = 280, 110
    spacing = 60
    total_w = 4 * func_w + 3 * spacing
    start_x = (img_w - total_w) // 2
    f1 = (start_x + 0 * (func_w + spacing), y2)
    f2 = (start_x + 1 * (func_w + spacing), y2)
    f3 = (start_x + 2 * (func_w + spacing), y2)
    f4 = (start_x + 3 * (func_w + spacing), y2)
    draw_box(draw, f1, (func_w, func_h), "1) Upload SOW\n(PDF/DOCX)", font)
    draw_box(draw, f2, (func_w, func_h), "2) Historical Analog\n(similar SOWs)", font)
    draw_box(draw, f3, (func_w, func_h), "3) Search\n(lexical/semantic/hybrid)", font)
    draw_box(draw, f4, (func_w, func_h), "4) Staffing Plan Generator\n(DEMO)", font)

    # Services row (extraction -> structured JSON)
    gap = 60
    left_x = x_center - box_w - gap // 2
    right_x = x_center + gap // 2
    s3_left = (left_x, y3)
    s3_right = (right_x, y3)
    draw_box(draw, s3_left, (box_w, box_h), "SOWExtractionService\n(Azure OpenAI +\nDocument Intelligence)", font)
    draw_box(draw, s3_right, (box_w, box_h), "Structured JSON\n(parsed SOW data)", font)

    # Storage / Indexing
    s4_left = (left_x, y4)
    s4_right = (right_x, y4)
    draw_box(draw, s4_left, (box_w, box_h), "Azure Storage (optional)\nContainers:\n`sows` / `extracted` / `parsed`", font)
    draw_box(draw, s4_right, (box_w, box_h), "Indexing Scripts\n(`scripts/indexing/*.py`)\nCreate/Populate Indexes", font)

    # Cognitive Search and Generator anchor
    s5_left = (left_x, y5)
    s5_right = (right_x, y5)
    draw_box(draw, s5_left, (box_w, box_h), "Azure Cognitive Search\nLexical / Semantic /\nHybrid Vector", font)
    draw_box(draw, s5_right, (box_w, box_h), "Generator (in App)\nAnalyze patterns +\nSkeleton plan (DEMO)", font)

    # Annotations for index names
    idx_note = "Indexes: `octagon-sows-parsed`, `octagon-sows-hybrid`"
    note_w, note_h = draw.textbbox((0, 0), idx_note, font=small_font)[2:]
    draw.text((s5_left[0] + (box_w - note_w) // 2, y5 + box_h + 8), idx_note, font=small_font, fill=(60, 60, 60))

    # Arrows
    def center_of(box):
        return (box[0] + box_w // 2, box[1] + box_h // 2)

    # Streamlit App -> functions
    app_cx = app_box[0] + app_box_w // 2
    app_bottom = y1 + app_box_h
    # Arrow to each function
    for fx in [f1, f2, f3, f4]:
        draw_arrow(draw, (app_cx, app_bottom), (fx[0] + func_w // 2, y2 - 12))

    # Upload SOW -> Extraction
    draw_arrow(draw, (f1[0] + func_w // 2, y2 + func_h), (left_x + box_w // 2, y3 - 12))
    # Extraction -> Structured JSON
    draw_arrow(draw, (left_x + box_w, y3 + box_h // 2), (right_x - 12, y3 + box_h // 2))
    # Structured JSON -> Storage
    draw_arrow(draw, (right_x + box_w // 2, y3 + box_h), (left_x + box_w // 2, y4 - 12))
    # Storage -> Indexing
    draw_arrow(draw, (left_x + box_w, y4 + box_h // 2), (right_x - 12, y4 + box_h // 2))
    # Indexing -> Cognitive Search
    draw_arrow(draw, (right_x + box_w // 2, y4 + box_h), (left_x + box_w // 2, y5 - 12))

    # Historical Analog -> Cognitive Search
    draw_arrow(draw, (f2[0] + func_w // 2, y2 + func_h), (left_x + box_w // 2, y5 - 12))
    # Search -> Cognitive Search
    draw_arrow(draw, (f3[0] + func_w // 2, y2 + func_h), (left_x + box_w // 2, y5 - 12))
    # Cognitive Search -> Generator (DEMO)
    draw_arrow(draw, (left_x + box_w, y5 + box_h // 2), (right_x - 12, y5 + box_h // 2))
    # Optional: Upload SOW -> Generator (to indicate using uploaded data)
    draw_arrow(draw, (f1[0] + func_w, y2 + func_h // 2), (f4[0] - 12, y2 + func_h // 2))

    img.save(out_path, format="PNG")
    print(f"✅ Wrote flow diagram to: {out_path}")


if __name__ == "__main__":
    main()


