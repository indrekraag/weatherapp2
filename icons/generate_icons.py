#!/usr/bin/env python3
"""Generate PWA icons for the Madise Ilmaradar weather app.

Design: dark navy background with the "MADISE" wordmark centered in
accent blue, preceded by the same pulse-dot used in the app's topbar.
The icon stays static (iOS PWAs cannot redraw home-screen icons), so we
deliberately avoid any temperature number that would imply it's live.

Run from this directory: python3 generate_icons.py
"""

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pathlib import Path

OUT_DIR = Path(__file__).parent

BG_DEEP = (6, 13, 20)
BG_GLOW_CENTER = (20, 60, 100)
WARM = (255, 204, 119)
ACCENT = (111, 193, 236)
TEXT_SOFT = (220, 235, 250)

FONT_PATH = "/System/Library/Fonts/SFNSMono.ttf"


def make_background(size: int, padding_ratio: float = 0.0) -> Image.Image:
    """Dark navy with a soft radial glow from the top, like the app body."""
    img = Image.new("RGB", (size, size), BG_DEEP)
    glow = Image.new("RGB", (size, size), BG_DEEP)
    gdraw = ImageDraw.Draw(glow, "RGB")
    cx, cy = size / 2, size * 0.3
    max_r = size * 0.7
    steps = 60
    for i in range(steps, 0, -1):
        t = i / steps
        r = max_r * t
        # Blend BG_GLOW_CENTER into BG_DEEP based on radial distance
        alpha = (1 - t) ** 1.5 * 0.35
        col = tuple(int(BG_DEEP[k] + (BG_GLOW_CENTER[k] - BG_DEEP[k]) * alpha) for k in range(3))
        gdraw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=size * 0.05))
    img = Image.blend(img, glow, 0.85)
    return img


def draw_glow_text(base: Image.Image, xy, text: str, font: ImageFont.FreeTypeFont,
                   fill, glow_color, glow_radius: float, glow_alpha: float = 0.55,
                   anchor: str = "mm") -> None:
    """Draw text with a soft outer glow."""
    size = base.size[0]
    glow_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    gd.text(xy, text, font=font, fill=glow_color + (int(255 * glow_alpha),), anchor=anchor)
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=glow_radius))
    base.paste(glow_layer, (0, 0), glow_layer)
    d = ImageDraw.Draw(base)
    d.text(xy, text, font=font, fill=fill, anchor=anchor)


def render_icon(size: int, maskable: bool = False) -> Image.Image:
    """Render the MADISE wordmark icon at a given output size.

    When maskable=True the content is scaled into the central ~78% so
    Android's adaptive-icon mask can crop the edges without clipping
    anything important.
    """
    work = size * 4 if size < 512 else size
    img = make_background(work).convert("RGBA")

    safe_scale = 0.78 if maskable else 1.0
    cx = work / 2
    label_y = work * 0.5

    # The wordmark is the hero element, so size it generously.
    label = "MADISE"
    label_font_size = int(work * 0.175 * safe_scale)
    label_font = ImageFont.truetype(FONT_PATH, label_font_size)

    # Measure letter-spaced label width to place the pulse-dot prefix.
    tracking = work * 0.018 * safe_scale
    char_widths = [label_font.getbbox(c)[2] - label_font.getbbox(c)[0] for c in label]
    total_w = sum(char_widths) + tracking * (len(label) - 1)

    dot_r = work * 0.022 * safe_scale
    gap = work * 0.045 * safe_scale
    group_w = total_w + gap + dot_r * 2
    group_left = cx - group_w / 2

    dot_cx = group_left + dot_r
    dot_cy = label_y

    # Soft glow behind the wordmark for legibility on the dark bg.
    glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    x_cursor = group_left + dot_r * 2 + gap
    for ch, w in zip(label, char_widths):
        gd.text((x_cursor, label_y), ch, font=label_font,
                fill=ACCENT + (140,), anchor="lm")
        x_cursor += w + tracking
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=work * 0.03))
    img.paste(glow_layer, (0, 0), glow_layer)

    # Pulse dot — same look as the app's topbar pulse-dot.
    dot_glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dgg = ImageDraw.Draw(dot_glow_layer)
    dgg.ellipse(
        [dot_cx - dot_r * 3, dot_cy - dot_r * 3,
         dot_cx + dot_r * 3, dot_cy + dot_r * 3],
        fill=ACCENT + (140,),
    )
    dot_glow_layer = dot_glow_layer.filter(ImageFilter.GaussianBlur(radius=work * 0.02))
    img.paste(dot_glow_layer, (0, 0), dot_glow_layer)
    d = ImageDraw.Draw(img)
    d.ellipse(
        [dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r],
        fill=ACCENT,
    )

    # Sharp wordmark on top of the glow.
    x_cursor = group_left + dot_r * 2 + gap
    for ch, w in zip(label, char_widths):
        d.text((x_cursor, label_y), ch, font=label_font, fill=ACCENT, anchor="lm")
        x_cursor += w + tracking

    # Subtle accent line below the wordmark, like the topbar divider.
    line_w = total_w * 0.85
    line_y = label_y + label_font_size * 0.55
    d.line(
        [(cx - line_w / 2, line_y), (cx + line_w / 2, line_y)],
        fill=ACCENT + (70,), width=max(1, int(work * 0.003)),
    )

    # Round corners on the non-maskable variant so the tile looks tidy
    # if surfaced without OS rounding (e.g. browser favicon menus).
    if not maskable:
        mask = Image.new("L", (work, work), 0)
        md = ImageDraw.Draw(mask)
        radius = int(work * 0.22)
        md.rounded_rectangle([0, 0, work, work], radius=radius, fill=255)
        out = Image.new("RGBA", (work, work), (0, 0, 0, 0))
        out.paste(img, (0, 0), mask)
        img = out

    if work != size:
        img = img.resize((size, size), Image.LANCZOS)
    return img


def render_favicon(size: int) -> Image.Image:
    """At 16/32 px a wordmark won't read, so fall back to a stylised 'M'."""
    work = max(256, size * 4)
    img = make_background(work).convert("RGBA")
    font = ImageFont.truetype(FONT_PATH, int(work * 0.62))
    draw_glow_text(
        img, (work / 2, work / 2), "M", font,
        fill=ACCENT, glow_color=ACCENT,
        glow_radius=work * 0.05, glow_alpha=0.55,
    )
    mask = Image.new("L", (work, work), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, work, work], radius=int(work * 0.22), fill=255)
    out = Image.new("RGBA", (work, work), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out.resize((size, size), Image.LANCZOS)


def main() -> None:
    targets = [
        ("icon-180.png", 180, False),
        ("icon-192.png", 192, False),
        ("icon-512.png", 512, False),
        ("icon-512-maskable.png", 512, True),
        ("apple-touch-icon.png", 180, False),
    ]
    for name, size, maskable in targets:
        img = render_icon(size, maskable=maskable)
        img.save(OUT_DIR / name, "PNG", optimize=True)
        print(f"  wrote {name} ({size}x{size}{', maskable' if maskable else ''})")

    for sz in (32, 16):
        img = render_favicon(sz)
        img.save(OUT_DIR / f"favicon-{sz}.png", "PNG", optimize=True)
        print(f"  wrote favicon-{sz}.png")

    print("Done.")


if __name__ == "__main__":
    main()
