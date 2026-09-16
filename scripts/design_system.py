"""
Ooops Phase 2 design system — slide layout renderer.

Not wired into daily-post.yml yet: the live cron still runs the old
single-text render_post.py against the old queue.json schema. This
module becomes the renderer once Phase 4 (queue schema) and Phase 5
(batch content) exist — see docs/build-plan.md's status log.

Typography: Nunito Bold, -3% letter-spacing, 100% line-height (user-
confirmed spec, docs/build-plan.md 2026-09-15). Pillow has no native
letter-spacing or Figma-style percentage line-height, so both are
implemented manually below rather than left to font defaults — do not
"simplify" this back to draw.multiline_text, that's what silently loses
the spec.

Colors are pulled from the Figma SVG exports' literal hex fills
(assets/design-reference/*.svg), not eyeballed off the PNGs.

Font loading is by explicit filename map, never "first file found" —
see docs/build-plan.md's note on why that was a real bug.
"""

import json
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(__file__), "..")
FONT_DIR = os.path.join(ROOT, "assets", "fonts")
EMOJI_DIR = os.path.join(ROOT, "assets", "emoji")
BG_DIR = os.path.join(ROOT, "assets", "backgrounds")
LOGO_DIR = os.path.join(ROOT, "assets", "logo")

W, H = 1080, 1350

COLORS = {
    "coral": "#EA4330",   # brand accent; main body text on light (BG1) slides
    "maroon": "#83261B",  # small watermark / caption text on light slides
    "cream": "#FFFAF8",   # main body text on dark/coral (BG2) slides
    "white": "#FFFFFF",
}

FONT_FILES = {
    "regular": "Nunito-Regular.ttf",
    "medium": "Nunito-Medium.ttf",
    "semibold": "Nunito-SemiBold.ttf",
    "bold": "Nunito-Bold.ttf",
    "extrabold": "Nunito-ExtraBold.ttf",
    "black": "Nunito-Black.ttf",
    "regular_italic": "Nunito-Italic.ttf",
    "medium_italic": "Nunito-MediumItalic.ttf",
    "semibold_italic": "Nunito-SemiBoldItalic.ttf",
    "bold_italic": "Nunito-BoldItalic.ttf",
    "extrabold_italic": "Nunito-ExtraBoldItalic.ttf",
    "black_italic": "Nunito-BlackItalic.ttf",
    "light": "Nunito-Light.ttf",
    "light_italic": "Nunito-LightItalic.ttf",
    "extralight": "Nunito-ExtraLight.ttf",
    "extralight_italic": "Nunito-ExtraLightItalic.ttf",
}

DEFAULT_WEIGHT = "bold"          # confirmed default: Nunito Bold
DEFAULT_TRACKING_PCT = -0.03     # -3% letter-spacing
DEFAULT_LINE_HEIGHT_PCT = 1.00   # 100% line-height

_font_cache = {}


def load_font(weight=DEFAULT_WEIGHT, size=64):
    if weight not in FONT_FILES:
        raise ValueError(f"Unknown font weight '{weight}'. Known: {sorted(FONT_FILES)}")
    key = (weight, size)
    if key not in _font_cache:
        path = os.path.join(FONT_DIR, FONT_FILES[weight])
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


_emoji_manifest = None


def _load_emoji_manifest():
    global _emoji_manifest
    if _emoji_manifest is None:
        with open(os.path.join(EMOJI_DIR, "manifest.json"), encoding="utf-8") as f:
            _emoji_manifest = json.load(f)
    return _emoji_manifest


def _split_emoji_runs(text):
    """Yield (is_emoji, chunk) runs. Only splits on emoji we actually have assets for."""
    manifest = _load_emoji_manifest()
    i = 0
    buf = ""
    while i < len(text):
        matched = None
        for emoji in manifest:
            if text.startswith(emoji, i):
                matched = emoji
                break
        if matched:
            if buf:
                yield False, buf
                buf = ""
            yield True, matched
            i += len(matched)
        else:
            buf += text[i]
            i += 1
    if buf:
        yield False, buf


def _char_advance(font, ch, tracking_px):
    return font.getlength(ch) + tracking_px


def _run_width(font, text, tracking_px, emoji_size):
    """Width of a line, accounting for emoji glyphs sized to emoji_size."""
    width = 0.0
    for is_emoji, chunk in _split_emoji_runs(text):
        if is_emoji:
            width += emoji_size + tracking_px
        else:
            for ch in chunk:
                width += _char_advance(font, ch, tracking_px)
    return width


def wrap_tracked(font, text, max_width, tracking_pct=DEFAULT_TRACKING_PCT):
    """Greedy word-wrap that accounts for per-character tracking and emoji width."""
    tracking_px = font.size * tracking_pct
    emoji_size = int(font.size * 0.95)
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if _run_width(font, candidate, tracking_px, emoji_size) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_tracked_line(draw, xy, text, font, fill, tracking_pct=DEFAULT_TRACKING_PCT,
                       emoji_layer=None):
    """Draw one line with manual letter-spacing and inline emoji compositing.

    emoji_layer: the PIL Image to paste emoji onto (usually the same image
    `draw` was created from). Required if `text` contains emoji.
    """
    x, y = xy
    tracking_px = font.size * tracking_pct
    emoji_size = int(font.size * 0.95)
    ascent, descent = font.getmetrics()
    for is_emoji, chunk in _split_emoji_runs(text):
        if is_emoji:
            manifest = _load_emoji_manifest()
            emoji_path = os.path.join(EMOJI_DIR, manifest[chunk])
            emoji_img = Image.open(emoji_path).convert("RGBA").resize(
                (emoji_size, emoji_size), Image.LANCZOS
            )
            paste_y = int(y + (ascent - emoji_size) * 0.5)
            if emoji_layer is not None:
                emoji_layer.alpha_composite(emoji_img, (int(x), paste_y))
            x += emoji_size + tracking_px
        else:
            for ch in chunk:
                draw.text((x, y), ch, font=font, fill=fill)
                x += _char_advance(font, ch, tracking_px)
    return x


def draw_paragraph(img, draw, xy, text, font, fill, max_width,
                    tracking_pct=DEFAULT_TRACKING_PCT,
                    line_height_pct=DEFAULT_LINE_HEIGHT_PCT, align="left"):
    """Draws possibly-multi-paragraph text (blank-line-separated), wrapped to
    max_width, with manual tracking and 100%-style line-height. Returns the
    y-coordinate just below the last line drawn."""
    x0, y = xy
    line_advance = font.size * line_height_pct
    tracking_px = font.size * tracking_pct
    emoji_size = int(font.size * 0.95)
    for paragraph in text.split("\n\n"):
        for line in wrap_tracked(font, paragraph, max_width, tracking_pct):
            if align == "left":
                lx = x0
            else:
                line_w = _run_width(font, line, tracking_px, emoji_size)
                lx = x0 + (max_width - line_w) / 2 if align == "center" else x0 + max_width - line_w
            draw_tracked_line(draw, (lx, y), line, font, fill, tracking_pct, emoji_layer=img)
            y += line_advance
        y += line_advance * 0.4  # small paragraph gap
    return y


def load_background(variant):
    """BG1 (light) or BG2 (coral). Uploaded at 1620x2025 — same 4:5 ratio as
    the 1080x1350 canvas, so a straight resize is correct, no crop needed."""
    fname = "BG1.png" if variant == 1 else "BG2.png"
    bg = Image.open(os.path.join(BG_DIR, fname)).convert("RGBA")
    if bg.size != (W, H):
        bg = bg.resize((W, H), Image.LANCZOS)
    return bg


def _load_logo():
    """The only logo source file, per the user's explicit instruction
    (2026-09-17): use assets/logo/Logo.png only — no recolored variants
    committed to the repo."""
    return Image.open(os.path.join(LOGO_DIR, "Logo.png")).convert("RGBA")


def draw_watermark(img, draw, bg_variant):
    """Small corner branding for an app_promo SINGLE post only. Never call
    this for relatable posts or for non-last carousel slides — see the
    2026-09-16 logo-placement ruling in docs/build-plan.md.

    Logo.png already has its white outline baked into the artwork (it was
    invisible against a white preview backdrop, which is why an earlier
    pass wrongly tried to synthesize one — that synthesis dilated the
    alpha channel without expanding the canvas, clipping the outline at
    the logo's tight crop edges. Fixed 2026-09-17: paste Logo.png as-is,
    no processing, per the user's explicit correction)."""
    text_color = COLORS["maroon"] if bg_variant == 1 else COLORS["white"]
    small_font = load_font("bold", 24)
    label = "ooopsapp.com"
    tracking_px = small_font.size * DEFAULT_TRACKING_PCT
    label_w = _run_width(small_font, label, tracking_px, int(small_font.size * 0.95))
    draw_tracked_line(draw, ((W - label_w) / 2, 48), label, small_font, text_color, emoji_layer=img)

    logo = _load_logo()
    logo_w = 130
    logo_h = int(logo.height * (logo_w / logo.width))
    logo_resized = logo.resize((logo_w, logo_h), Image.LANCZOS)
    img.alpha_composite(logo_resized, (W - logo_resized.width - 48, H - logo_resized.height - 48))


def render_logo_endcard():
    """The big branded slide — ONLY the last slide of an app_promo carousel,
    or a dedicated app_promo single post. Matches IG carousel.png's final
    slide: coral bg, big logo (as-is, see draw_watermark's note on why no
    outline processing is applied), tagline, waitlist CTA."""
    img = load_background(2)
    draw = ImageDraw.Draw(img)

    logo = _load_logo()
    logo_w = 620
    logo_h = int(logo.height * (logo_w / logo.width))
    logo_resized = logo.resize((logo_w, logo_h), Image.LANCZOS)
    logo_y = 520
    img.alpha_composite(logo_resized, ((W - logo_resized.width) // 2, logo_y))

    tagline_font = load_font("bold", 34)
    tagline = "we're building something for this."
    tracking_px = tagline_font.size * DEFAULT_TRACKING_PCT
    tagline_w = _run_width(tagline_font, tagline, tracking_px, int(tagline_font.size * 0.95))
    draw_tracked_line(
        draw, ((W - tagline_w) / 2, logo_y + logo_h + 60), tagline, tagline_font,
        COLORS["white"], emoji_layer=img,
    )

    cta_font = load_font("extrabold", 40)
    cta = "join the waitlist"
    tracking_px = cta_font.size * DEFAULT_TRACKING_PCT
    cta_w = _run_width(cta_font, cta, tracking_px, int(cta_font.size * 0.95))
    draw_tracked_line(
        draw, ((W - cta_w) / 2, logo_y + logo_h + 130), cta, cta_font,
        COLORS["white"], emoji_layer=img,
    )

    url_font = load_font("bold", 28)
    url = "ooopsapp.com"
    tracking_px = url_font.size * DEFAULT_TRACKING_PCT
    url_w = _run_width(url_font, url, tracking_px, int(url_font.size * 0.95))
    draw_tracked_line(
        draw, ((W - url_w) / 2, logo_y + logo_h + 200), url, url_font,
        COLORS["white"], emoji_layer=img,
    )
    return img


def render_hook(text, bg_variant=1, branded=False):
    """Big bold statement text, left-aligned block. `branded=True` only valid
    for an app_promo single post — never for relatable content."""
    img = load_background(bg_variant)
    draw = ImageDraw.Draw(img)
    text_color = COLORS["coral"] if bg_variant == 1 else COLORS["cream"]
    font = load_font("bold", 64)
    margin = 108
    draw_paragraph(img, draw, (margin, 430), text, font, text_color, W - margin * 2)
    if branded:
        draw_watermark(img, draw, bg_variant)
    return img


def render_bullet_list(items, bg_variant=1, branded=False):
    """Stacked emoji-prefixed lines, e.g. the offense-category rundown slide
    in IG carousel.png ("🚩 Left me on read", "❤️ Forgot date night", ...)."""
    img = load_background(bg_variant)
    draw = ImageDraw.Draw(img)
    text_color = COLORS["coral"] if bg_variant == 1 else COLORS["cream"]
    font = load_font("bold", 52)
    margin = 108
    y = 430
    for item in items:
        y = draw_paragraph(img, draw, (margin, y), item, font, text_color, W - margin * 2)
        y += font.size * 0.3
    if branded:
        draw_watermark(img, draw, bg_variant)
    return img


def render_stat_card(stat, caption, bg_variant=1, branded=False):
    """Big number/stat + supporting caption underneath.

    NOTE: there's no dedicated Figma reference for this layout type yet
    (only hook/bullet_list/photo are directly shown in the uploaded
    references) — this is a best-guess implementation modeled on the same
    typographic system, not a confirmed visual spec. Flag to the user
    before relying on this in production; revise once a stat_card sample
    is uploaded."""
    img = load_background(bg_variant)
    draw = ImageDraw.Draw(img)
    text_color = COLORS["coral"] if bg_variant == 1 else COLORS["cream"]
    margin = 108
    stat_font = load_font("black", 120)
    tracking_px = stat_font.size * DEFAULT_TRACKING_PCT
    stat_w = _run_width(stat_font, stat, tracking_px, int(stat_font.size * 0.95))
    draw_tracked_line(draw, ((W - stat_w) / 2, 480), stat, stat_font, text_color, emoji_layer=img)

    caption_font = load_font("bold", 44)
    draw_paragraph(
        img, draw, (margin, 480 + stat_font.size + 40), caption, caption_font, text_color,
        W - margin * 2, align="center",
    )
    if branded:
        draw_watermark(img, draw, bg_variant)
    return img


def render_photo(photo_path, caption, bg_variant=1, branded=False):
    """Photo with a colored border frame (matches Reference_image_post_*.png:
    ~32px inset border in the slide's bg color) and bottom text overlay."""
    img = load_background(bg_variant)
    draw = ImageDraw.Draw(img)
    border = 32
    corner_radius = 28
    inner_w, inner_h = W - border * 2, H - border * 2

    photo = Image.open(photo_path).convert("RGB")
    src_ratio = photo.width / photo.height
    dst_ratio = inner_w / inner_h
    if src_ratio > dst_ratio:
        new_h = inner_h
        new_w = int(new_h * src_ratio)
    else:
        new_w = inner_w
        new_h = int(new_w / src_ratio)
    photo = photo.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - inner_w) // 2
    top = (new_h - inner_h) // 2
    photo = photo.crop((left, top, left + inner_w, top + inner_h))

    mask = Image.new("L", (inner_w, inner_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, inner_w - 1, inner_h - 1], radius=corner_radius, fill=255)
    img.paste(photo, (border, border), mask)

    text_color = COLORS["cream"]
    font = load_font("bold", 56)
    draw_paragraph(
        img, draw, (border + 40, H - 320), caption, font, text_color,
        inner_w - 80, align="center",
    )
    if branded:
        draw_watermark(img, draw, bg_variant)
    return img
