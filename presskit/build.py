#!/usr/bin/env python3
"""Generate the Redevify press kit (SVG + hi-res PNG) from one source of geometry.

Run with a python that has fonttools+brotli:  python3 presskit/build.py
Needs Chromium headless shell (Playwright cache) for PNG rendering.
Text is converted to outlines using the site's own IBM Plex Mono, so SVGs are font-independent.
"""
import glob, os, subprocess
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

ROOT = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(ROOT, "..", "fonts")
CHROME = glob.glob(os.path.expanduser(
    "~/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell"))[-1]

INK, PAPER, SHEET, BLUE, MUTED, BODY, LINE = "#0E1013", "#F4F5F6", "#FAFBFB", "#1F5EFF", "#606874", "#5A6270", "#D5D8DD"

_fonts = {w: TTFont(os.path.join(FONTS, f"plex-mono-{w}.woff2")) for w in (400, 500, 600)}


def text(s, size, x, y, fill, weight=500, ls=0.0, anchor="start"):
    """Outlined text. ls = letter-spacing in em. y = baseline."""
    f = _fonts[weight]; upm = f["head"].unitsPerEm; gs = f.getGlyphSet(); cmap = f.getBestCmap()
    k = size / upm; step = f["hmtx"][cmap[ord("a")]][0] + ls * upm      # monospace advance
    width = (len(s) * step - ls * upm) * k
    x0 = x - (width if anchor == "end" else width / 2 if anchor == "middle" else 0)
    out = [f'<g transform="translate({x0:.2f} {y:.2f}) scale({k:.5f} {-k:.5f})" fill="{fill}">']
    for i, ch in enumerate(s):
        if ch == " ": continue
        pen = SVGPathPen(gs); gs[cmap[ord(ch)]].draw(pen)
        out.append(f'<path transform="translate({i*step:.1f} 0)" d="{pen.getCommands()}"/>')
    return "".join(out) + "</g>", width


def mark(cx, cy, size, hi, lo, lo_opacity=None):
    """Logo mark centred on its visible content (24,23 in 48-space). size = 48-unit box in px."""
    s = size / 48; op = f' opacity="{lo_opacity}"' if lo_opacity else ""
    return (f'<g transform="translate({cx - 24*s:.2f} {cy - 23*s:.2f}) scale({s:.4f})">'
            f'<path d="M24 18 L44 30 L24 42 L4 30 Z" fill="{lo}"{op}/><path d="M24 4 L44 16 L24 28 L4 16 Z" fill="{hi}"/></g>')


def svg(vb, body, px=None, bg=None):
    x, y, w, h = vb; size = f' width="{px[0]}" height="{px[1]}"' if px else ""
    rect = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{bg}"/>' if bg else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y} {w} {h}"{size}>{rect}{body}</svg>\n'


def blend(c, bg, a):
    p = lambda h: [int(h[i:i+2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(a*u + (1-a)*v) for u, v in zip(p(c), p(bg)))


def render(svg_path, png_path, w, h, transparent=True):
    subprocess.run([CHROME, "--headless", "--hide-scrollbars", "--force-device-scale-factor=1",
                    f"--window-size={w},{h}", f"--screenshot={png_path}",
                    "--default-background-color=00000000" if transparent else "--default-background-color=FFFFFFFF",
                    "file://" + svg_path], check=True, capture_output=True)


def emit(path, vb, body, w, bg=None, transparent=True):
    """Write SVG (scalable) and a PNG rendered at pixel width w."""
    h = round(w * vb[3] / vb[2])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(svg(vb, body, bg=bg))
    tmp = path[:-4] + ".tmp.svg"; open(tmp, "w").write(svg(vb, body, (w, h), bg=bg))
    render(tmp, path[:-4].replace("/svg/", "/png/") + ".png", w, h, transparent)
    os.remove(tmp)


# ---------------------------------------------------------------- logos
THEMES = {"ink": (INK, INK, 0.32), "white": (PAPER, PAPER, 0.32)}
for name, (hi, lo, op) in THEMES.items():
    d = f"{ROOT}/logo"
    os.makedirs(f"{d}/png", exist_ok=True)
    # mark — square, centred, clear-space baked in
    emit(f"{d}/svg/redevify-mark-{name}.svg", (0, -1, 48, 48), mark(24, 23, 48, hi, lo, op), 2048)
    # wordmark (text size 36 => ascenders align with mark height, see lockup)
    t, tw = text("redevify", 36, 0, 32.3, hi, 600, -0.025)
    emit(f"{d}/svg/redevify-wordmark-{name}.svg", (-8, -4, tw + 16, 54), t, 3200)
    # horizontal lockup: mark left, wordmark right (ascender top == mark top)
    t, tw = text("redevify", 36, 58, 32.3, hi, 600, -0.025)
    emit(f"{d}/svg/redevify-lockup-horizontal-{name}.svg", (-4, -4, 58 + tw + 4 + 4, 54),
         mark(24, 23, 48, hi, lo, op) + t, 4000)
    # stacked lockup: mark above wordmark, centred
    t, tw = text("redevify", 40, 0, 0, hi, 600, -0.025, "middle")
    emit(f"{d}/svg/redevify-lockup-stacked-{name}.svg", (-110, -22, 220, 192),
         mark(0, 52, 150, hi, lo, op) + f'<g transform="translate(0 150)">{t}</g>', 3000)

# ---------------------------------------------------------------- banners 1500x500 (3:1) -> 3600x1200 PNG
W, H, PX = 1500, 500, 3600
B = f"{ROOT}/banner"; os.makedirs(f"{B}/png", exist_ok=True)

# A — Sheet: the website's blueprint frame, extended to a banner
a = [f'<rect width="{W}" height="{H}" fill="{PAPER}"/>', f'<rect x="20.5" y="20.5" width="1459" height="459" fill="{SHEET}" stroke="{LINE}"/>']
for ln in ('M20 84.5H1480', 'M20 416.5H1480', 'M500.5 84V416'): a.append(f'<path d="{ln}" stroke="{LINE}" fill="none"/>')
a.append(mark(260, 250, 210, INK, INK, 0.32))
a.append(text("redevify", 26, 52, 60, INK, 600, -0.025)[0])
a.append(text("SOFTWARE STUDIO", 13, 1448, 57, MUTED, 400, 0.16, "end")[0])
a.append(text("We love making", 62, 556, 214, INK, 500, -0.035)[0])
a.append(text("software products.", 62, 556, 282, INK, 500, -0.035)[0])
a.append(text("Ideas into shipped products — for businesses and individuals.", 19, 556, 338, BODY, 400)[0])
t, tw = text("hello@redevify.com", 24, 52, 456, BLUE, 500, -0.025); a.append(t)
a.append(f'<path d="M52 463.5H{52+tw:.1f}" stroke="{BLUE}"/>')
a.append(text("REDEVIFY.COM", 13, 1448, 453, MUTED, 400, 0.14, "end")[0])
emit(f"{B}/svg/banner-wide-3600x1200.svg", (0, 0, W, H), "".join(a), PX, transparent=False)

# A at 16:9 (slides 1920x1080, YouTube 2560x1440) and 1.91:1 (link preview 1200x630).
# Layout is in 1920-wide units. YouTube safe area (shows on every device) is the centre 1160x317 of the 1080-high
# canvas: label, headline, lede and mark all sit inside it; header/footer chrome is allowed to crop.
def sheet(H):
    W = 1920; cy = H / 2; top, bot = 112.5, H - 112.5; dx = 675.5
    p = [f'<rect width="{W}" height="{H}" fill="{PAPER}"/>', f'<rect x="30.5" y="30.5" width="{W-61}" height="{H-61}" fill="{SHEET}" stroke="{LINE}"/>']
    for ln in (f'M30 {top}H{W-30}', f'M30 {bot}H{W-30}', f'M{dx} {top}V{bot}'): p.append(f'<path d="{ln}" stroke="{LINE}" fill="none"/>')
    p.append(mark(525, cy, 225, INK, INK, 0.32))
    p.append(text("redevify", 30, 68, 78, INK, 600, -0.025)[0])
    p.append(text("SOFTWARE STUDIO", 15, W-68, 76, MUTED, 400, 0.16, "end")[0])
    p.append(text("We love making", 72, 740, cy - 41, INK, 500, -0.035)[0])
    p.append(text("software products.", 72, 740, cy + 36, INK, 500, -0.035)[0])
    p.append(text("Ideas into shipped products — for businesses and individuals.", 21, 740, cy + 92, BODY, 400)[0])
    t, tw = text("hello@redevify.com", 28, 68, bot + 62, BLUE, 500, -0.025); p.append(t)
    p.append(f'<path d="M68 {bot+70.5}H{68+tw:.1f}" stroke="{BLUE}"/>')
    p.append(text("REDEVIFY.COM", 15, W-68, bot + 58, MUTED, 400, 0.14, "end")[0])
    return (0, 0, W, H), "".join(p)

vb, body = sheet(1080)
emit(f"{B}/svg/banner-youtube-2560x1440.svg", vb, body, 2560, transparent=False)
emit(f"{B}/svg/banner-16x9-1920x1080.svg", vb, body, 1920, transparent=False)
vb, body = sheet(1008)
emit(f"{B}/svg/banner-link-preview-1200x630.svg", vb, body, 1200, transparent=False)
print("done")
