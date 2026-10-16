"""Sistema visual de 72 HORAS (versión clara): paleta, retícula y fondos de página.

Los fondos se dibujan como imagen (2560x1440 = 2x de la página de 1280x720) y los
visuales de Power BI se colocan encima con fondo transparente, en las mismas
coordenadas que define LAYOUT. Sin texto en las imágenes salvo las etiquetas del mapa.
Mapa: códigos postales de la CDMX (open-mexico/mexico-geojson, licencia MIT)
disueltos por los dos primeros dígitos = alcaldía.
"""
from __future__ import annotations
import json, math
from collections import defaultdict
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = 2  # escala de la imagen respecto a la página
W, H = 1280, 720

# ------------------------------------------------------------------ paleta
NAVY, STEEL, STEEL_L, STEEL_XL = "#0B1F33", "#1F5F9E", "#C9D8E8", "#E8EEF5"
SLATE, SLATE_L, GRID = "#5B6B7F", "#93A1B2", "#E3E8EE"
ORANGE, GREY_BAR, WHITE = "#D2601A", "#B8C2CE", "#FFFFFF"
CANVAS_TOP, CANVAS_BOT = "#F4F6F9", "#E7EBF0"

# ------------------------------------------------------------------ retícula (coordenadas de página)
SIDEBAR_W = 72
NAV_Y0, NAV_STEP = 140, 64
PAGES = ["resumen", "sensibilidad", "desenlace", "caracteristicas", "alcaldia"]
LAYOUT = {
    "resumen": {"A": (96, 88, 320, 150), "B": (96, 252, 320, 168), "C": (96, 434, 320, 258),
                "M": (432, 88, 504, 604),
                "D": (952, 88, 304, 330), "E": (952, 432, 304, 260)},
    "sensibilidad": {"L": (96, 88, 700, 604), "R": (812, 88, 444, 604)},
    "desenlace": {"L": (96, 88, 700, 604), "RT": (812, 88, 444, 236), "RB": (812, 338, 444, 354)},
    "caracteristicas": {"A": (96, 88, 572, 294), "B": (684, 88, 572, 294),
                        "C": (96, 398, 572, 294), "D": (684, 398, 572, 294)},
    "alcaldia": {"L": (96, 88, 572, 604), "RT": (684, 88, 572, 230), "RB": (684, 332, 572, 360)},
}
CHIPS = [(156, 266), (316, 266)]  # cuadros de ícono en la tarjeta B (resumen)
RINGS: list = []  # (cx, cy, pct, color) anillos de desenlace en la tarjeta E; los llena el generador


def hx(c, a=255):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def _canvas():
    img = Image.new("RGBA", (W * S, H * S))
    top, bot = hx(CANVAS_TOP), hx(CANVAS_BOT)
    px = ImageDraw.Draw(img)
    for y in range(H * S):
        t = y / (H * S - 1)
        px.line([(0, y), (W * S, y)], fill=tuple(round(top[i] + (bot[i] - top[i]) * t) for i in range(3)) + (255,))
    return img


def _shadow(img, box, radius, alpha=22, blur=22, dy=8):
    x, y, w, h = [v * S for v in box]
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).rounded_rectangle([x, y + dy * S, x + w, y + h + dy * S], radius * S, fill=hx(NAVY, alpha))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur * S / 2)))


def card(img, box, radius=18, fill=WHITE):
    _shadow(img, box, radius)
    x, y, w, h = [v * S for v in box]
    ImageDraw.Draw(img).rounded_rectangle([x, y, x + w, y + h], radius * S, fill=hx(fill))


def _icon(d, kind, cx, cy, col, s=1.0):
    """Íconos lineales simples, centrados en (cx, cy) en coordenadas de imagen."""
    k = S * s
    lw = max(2, round(2.2 * k))
    if kind == "resumen":  # cuadrícula 2x2
        for dx in (-7, 3):
            for dy in (-7, 3):
                d.rounded_rectangle([cx + dx * k, cy + dy * k, cx + (dx + 5) * k, cy + (dy + 5) * k], 1.5 * k, outline=col, width=lw)
    elif kind == "sensibilidad":  # barras
        for i, hh in enumerate((6, 12, 9)):
            x = cx + (-8 + i * 6) * k
            d.rounded_rectangle([x, cy + (7 - hh) * k, x + 3.5 * k, cy + 7 * k], 1 * k, fill=col)
    elif kind == "desenlace":  # pulso
        pts = [(-10, 0), (-4, 0), (-1, -7), (2, 7), (5, 0), (10, 0)]
        d.line([(cx + a * k, cy + b * k) for a, b in pts], fill=col, width=lw, joint="curve")
    elif kind == "caracteristicas":  # personas
        for dx in (-5, 5):
            d.ellipse([cx + (dx - 3) * k, cy - 8 * k, cx + (dx + 3) * k, cy - 2 * k], outline=col, width=lw)
            d.arc([cx + (dx - 6) * k, cy + 0 * k, cx + (dx + 6) * k, cy + 14 * k], 180, 360, fill=col, width=lw)
    elif kind == "alcaldia":  # pin
        d.ellipse([cx - 6 * k, cy - 9 * k, cx + 6 * k, cy + 3 * k], outline=col, width=lw)
        d.polygon([(cx - 4.5 * k, cy + 0 * k), (cx + 4.5 * k, cy + 0 * k), (cx, cy + 9 * k)], fill=col)
        d.ellipse([cx - 2 * k, cy - 5 * k, cx + 2 * k, cy - 1 * k], fill=col)
    elif kind == "pin_w":
        d.ellipse([cx - 6 * k, cy - 9 * k, cx + 6 * k, cy + 3 * k], fill=col)
        d.polygon([(cx - 4.5 * k, cy + 0 * k), (cx + 4.5 * k, cy + 0 * k), (cx, cy + 9 * k)], fill=col)
    elif kind == "reloj":
        d.ellipse([cx - 8 * k, cy - 8 * k, cx + 8 * k, cy + 8 * k], outline=col, width=lw)
        d.line([(cx, cy - 5 * k), (cx, cy), (cx + 4 * k, cy + 2.5 * k)], fill=col, width=lw)


def sidebar(img, active):
    x0, w = 0, SIDEBAR_W * S
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).rectangle([0, 0, w + 6 * S, H * S], fill=hx(NAVY, 18))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(8 * S)))
    d = ImageDraw.Draw(img)
    d.rectangle([x0, 0, w, H * S], fill=hx(WHITE))
    d.rounded_rectangle([16 * S, 20 * S, 56 * S, 60 * S], 11 * S, fill=hx(NAVY))  # marca (texto «72» en Power BI)
    for i, p in enumerate(PAGES):
        cy = (NAV_Y0 + i * NAV_STEP) * S
        cx = (SIDEBAR_W // 2) * S
        if p == active:
            d.rounded_rectangle([cx - 22 * S, cy - 22 * S, cx + 22 * S, cy + 22 * S], 12 * S, fill=hx(NAVY))
            _icon(d, p, cx, cy, hx(WHITE))
        else:
            _icon(d, p, cx, cy, hx(SLATE_L))


# ------------------------------------------------------------------ mapa CDMX
CP_ALCALDIA = {"01": "ALVARO OBREGON", "02": "AZCAPOTZALCO", "03": "BENITO JUAREZ", "04": "COYOACAN",
               "05": "CUAJIMALPA DE MORELOS", "06": "CUAUHTEMOC", "07": "GUSTAVO A. MADERO", "08": "IZTACALCO",
               "09": "IZTAPALAPA", "10": "LA MAGDALENA CONTRERAS", "11": "MIGUEL HIDALGO", "12": "MILPA ALTA",
               "13": "TLAHUAC", "14": "TLALPAN", "15": "VENUSTIANO CARRANZA", "16": "XOCHIMILCO"}
LABEL = {"ALVARO OBREGON": "Álvaro Obregón", "GUSTAVO A. MADERO": "Gustavo A. Madero", "IZTAPALAPA": "Iztapalapa",
         "CUAUHTEMOC": "Cuauhtémoc", "VENUSTIANO CARRANZA": "Venustiano Carranza", "COYOACAN": "Coyoacán",
         "TLALPAN": "Tlalpan", "AZCAPOTZALCO": "Azcapotzalco", "BENITO JUAREZ": "Benito Juárez",
         "XOCHIMILCO": "Xochimilco", "MIGUEL HIDALGO": "Miguel Hidalgo", "TLAHUAC": "Tláhuac",
         "IZTACALCO": "Iztacalco", "CUAJIMALPA DE MORELOS": "Cuajimalpa", "LA MAGDALENA CONTRERAS": "Magdalena Contreras",
         "MILPA ALTA": "Milpa Alta"}


def alcaldias(geojson: Path):
    from shapely.geometry import shape
    from shapely.ops import unary_union
    g = defaultdict(list)
    for f in json.loads(geojson.read_text(encoding="utf-8"))["features"]:
        g[f["properties"]["d_codigo"][:2]].append(shape(f["geometry"]).buffer(0))
    return {CP_ALCALDIA[k]: unary_union(v).buffer(0) for k, v in g.items() if k in CP_ALCALDIA}


def draw_map(img, box, polys, cases, font_path):
    """Mapa en relieve claro con puntos proporcionales a casos recibidos."""
    from shapely.ops import unary_union
    bx, by, bw, bh = box
    union = unary_union(list(polys.values()))
    minx, miny, maxx, maxy = union.bounds
    kx = math.cos(math.radians((miny + maxy) / 2))
    sx = (bw - 40) / ((maxx - minx) * kx)
    sy = (bh - 40) / (maxy - miny)
    sc = min(sx, sy)
    ox = bx + (bw - (maxx - minx) * kx * sc) / 2
    oy = by + (bh - (maxy - miny) * sc) / 2
    proj = lambda lon, lat: ((ox + (lon - minx) * kx * sc) * S, (oy + (maxy - lat) * sc) * S)

    def rings(geom):
        for p in getattr(geom, "geoms", [geom]):
            yield [proj(*c) for c in p.exterior.coords]

    # sombra profunda + borde de relieve
    for blur, dy, a in ((34, 26, 20), (5, 5, 30)):
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        for r in rings(union):
            dl.polygon([(x, y + dy * S) for x, y in r], fill=hx(NAVY, a))
        img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur * S / 2)))
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    for r in rings(union):
        dl.polygon([(x, y + 4 * S) for x, y in r], fill=hx("#C5CFDA"))
    img.alpha_composite(lay)
    # alcaldías: tonos claros escalonados (relieve), bordes blancos
    d = ImageDraw.Draw(img)
    tones = ["#FBFCFD", "#F3F6F9", "#EDF1F5", "#F7F9FB"]
    for i, (name, geom) in enumerate(sorted(polys.items())):
        for r in rings(geom):
            d.polygon(r, fill=hx(tones[i % len(tones)]))
    for name, geom in polys.items():
        for r in rings(geom):
            d.line(r + [r[0]], fill=hx(WHITE), width=3 * S, joint="curve")
            d.line(r + [r[0]], fill=hx("#D5DDE6"), width=1 * S, joint="curve")
    # puntos proporcionales (área ∝ casos)
    mx = max(cases.values())
    pts = []
    for name, geom in polys.items():
        n = cases.get(name, 0)
        p = geom.representative_point()
        cx, cy = proj(p.x, p.y)
        r = (6 + 22 * math.sqrt(n / mx)) * S
        pts.append((n, name, cx, cy, r))
    for n, name, cx, cy, r in sorted(pts):
        halo = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(halo).ellipse([cx - r, cy - r, cx + r, cy + r], fill=hx(STEEL, 46))
        img.alpha_composite(halo)
        d = ImageDraw.Draw(img)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=hx(STEEL, 150), width=max(2, S))
        d.ellipse([cx - 5.5 * S, cy - 5.5 * S, cx + 5.5 * S, cy + 5.5 * S], fill=hx(WHITE))
        d.ellipse([cx - 3.6 * S, cy - 3.6 * S, cx + 3.6 * S, cy + 3.6 * S], fill=hx(NAVY))
    # etiquetas: las 5 alcaldías con más casos
    f1 = ImageFont.truetype(font_path["semibold"], 11 * S)
    f2 = ImageFont.truetype(font_path["regular"], 10 * S)
    placed = []
    pins = {name: (cx - r, cy - r, cx + r, cy + r) for n, name, cx, cy, r in pts}
    def free(b):
        return all(b[2] < q[0] or b[0] > q[2] or b[3] < q[1] or b[1] > q[3] for q in placed)
    for n, name, cx, cy, r in sorted(pts, reverse=True)[:5]:
        t1, t2 = LABEL[name], f"{n:,} casos"
        wbox = max(d.textlength(t1, font=f1), d.textlength(t2, font=f2)) + 16 * S
        hb = 32 * S
        g = 6 * S
        cands = [(cx + r + g, cy - hb / 2), (cx - r - g - wbox, cy - hb / 2),
                 (cx + 0.6 * r, cy - r - g - hb), (cx - 0.6 * r - wbox, cy - r - g - hb),
                 (cx + 0.6 * r, cy + r + g), (cx - 0.6 * r - wbox, cy + r + g),
                 (cx - wbox / 2, cy - r - g - hb), (cx - wbox / 2, cy + r + g)]
        others = [v for k, v in pins.items() if k != name]
        def cost(c):
            tx, ty = c
            b_ = (tx - 4 * S, ty - 4 * S, tx + wbox + 4 * S, ty + hb + 4 * S)
            ov = lambda q: max(0, min(b_[2], q[2]) - max(b_[0], q[0])) * max(0, min(b_[3], q[3]) - max(b_[1], q[1]))
            out = 0 if (bx * S) <= tx and tx + wbox <= (bx + bw) * S else 1e12
            return out + sum(ov(q) for q in others) + 10 * sum(ov(q) for q in placed)
        tx, ty = min(cands, key=cost)
        placed.append((tx - 4 * S, ty - 4 * S, tx + wbox + 4 * S, ty + hb + 4 * S))
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).rounded_rectangle([tx, ty + 2 * S, tx + wbox, ty + hb + 2 * S], 8 * S, fill=hx(NAVY, 26))
        img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(5 * S)))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([tx, ty, tx + wbox, ty + hb], 8 * S, fill=hx(WHITE, 242))
        d.text((tx + 8 * S, ty + 3 * S), t1, font=f1, fill=hx(NAVY))
        d.text((tx + 8 * S, ty + 17 * S), t2, font=f2, fill=hx(SLATE))


def chip(img, x, y, kind, bg):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x * S, y * S, (x + 40) * S, (y + 40) * S], 11 * S, fill=hx(bg))
    _icon(d, kind, (x + 20) * S, (y + 20) * S, hx(WHITE), 0.95)


def ring(img, cx, cy, pct, col, r=58, t=15, track="#E6EBF1"):
    """Anillo de proporción dibujado con supermuestreo (inicio a las 12, sentido horario)."""
    ss = 4
    size = (2 * r + 4) * S * ss
    lay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    bb = [2 * S * ss, 2 * S * ss, size - 2 * S * ss, size - 2 * S * ss]
    dr.arc(bb, 0, 360, fill=hx(track), width=t * S * ss)
    dr.arc(bb, -90, -90 + 360 * pct / 100, fill=hx(col), width=t * S * ss)
    lay = lay.resize((size // ss, size // ss), Image.LANCZOS)
    img.alpha_composite(lay, ((cx - r - 2) * S, (cy - r - 2) * S))


def render_all(out_dir: Path, geojson: Path, cases: dict, font_path: dict) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    polys = alcaldias(geojson)
    files = []
    for p in PAGES:
        img = _canvas()
        for k, box in LAYOUT[p].items():
            card(img, box, radius=18)
        if p == "resumen":
            chip(img, *CHIPS[0], "pin_w", STEEL)
            chip(img, *CHIPS[1], "reloj", SLATE)
            for cx, cy, pct, col in RINGS:
                ring(img, cx, cy, pct, col)
        sidebar(img, p)
        f = out_dir / f"bg_{p}.png"
        img.convert("RGB").save(f, optimize=True)
        files.append(f)
    return files
