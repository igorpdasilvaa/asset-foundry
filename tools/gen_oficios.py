"""Gera os SVGs do grupo "oficios" (Hearth, hospedagem, ferraria, estábulos e alfaiataria de Candlekeep)
em assets/<id>/<id>_<estado>.svg e o fragmento de definições tools/fragmentos/oficios.json.
Tudo visto de cima, 1 quadrado = 200 unidades. Uso:
python3 tools/gen_oficios.py && NODE_PATH=$(npm root -g) node tools/render.js assets/{amplificador,fogueira,balcao,cadeira,poltrona,banco,cama,forja,bigorna,feno,cocho,tear,casulario}/*.svg"""
import math, random, pathlib, sys, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gen_pecas_mapa import noise, shade, wrap

ROOT = pathlib.Path(__file__).resolve().parent.parent
A = ROOT / "assets"
S = 200
INK = "#2a180a"   # contorno da madeira

COMMON = (
    '<filter id="bl4" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter>'
    '<filter id="bl8" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="8"/></filter>'
    '<radialGradient id="glow"><stop offset="0" stop-color="#ffb347" stop-opacity=".75"/><stop offset=".6" stop-color="#ff5a1a" stop-opacity=".3"/><stop offset="1" stop-color="#ff5a1a" stop-opacity="0"/></radialGradient>'
    '<radialGradient id="soot"><stop offset="0" stop-color="#0b0908" stop-opacity=".9"/><stop offset=".7" stop-color="#1a1410" stop-opacity=".55"/><stop offset="1" stop-color="#1a1410" stop-opacity="0"/></radialGradient>'
    '<radialGradient id="scorch"><stop offset="0" stop-color="#0b0908" stop-opacity=".75"/><stop offset=".6" stop-color="#1a1410" stop-opacity=".4"/><stop offset="1" stop-color="#1a1410" stop-opacity="0"/></radialGradient>'
    '<radialGradient id="ale"><stop offset="0" stop-color="#c98a2a" stop-opacity=".85"/><stop offset=".7" stop-color="#a86a1a" stop-opacity=".6"/><stop offset="1" stop-color="#a86a1a" stop-opacity="0"/></radialGradient>'
    '<radialGradient id="puddle"><stop offset="0" stop-color="#3f86b8" stop-opacity=".8"/><stop offset=".75" stop-color="#2f6a96" stop-opacity=".55"/><stop offset="1" stop-color="#2f6a96" stop-opacity="0"/></radialGradient>'
    # escurece o desenho (madeira pegando fogo) e carboniza (restos queimados)
    '<filter id="dk" x="-10%" y="-10%" width="120%" height="120%"><feComponentTransfer>'
    '<feFuncR type="linear" slope=".55"/><feFuncG type="linear" slope=".45"/><feFuncB type="linear" slope=".4"/></feComponentTransfer></filter>'
    '<filter id="ch" x="-10%" y="-10%" width="120%" height="120%"><feColorMatrix type="saturate" values=".25"/><feComponentTransfer>'
    '<feFuncR type="linear" slope=".32"/><feFuncG type="linear" slope=".28"/><feFuncB type="linear" slope=".26"/></feComponentTransfer></filter>'
)
WOOD = noise("wd", "0.012 0.22", 4, (.22, .12, .05))     # veio horizontal
WOODV = noise("wv", "0.22 0.012", 6, (.22, .12, .05))    # veio vertical
STONE = noise("st", "0.07", 7, (.16, .15, .13), 1.2, -.4)
CLOTH = noise("cl", "0.5", 3, (.1, .05, .05), 1.0, -.35)


SIZES = {"fogueira": (2, 2), "forja": (2, 2), "banco": (2, 1), "cocho": (2, 1), "tear": (2, 1), "cama": (1, 2)}


def write(asset, name, body, defs=""):
    w, h = SIZES.get(asset, (1, 1))
    d = A / asset
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.svg").write_text(wrap(w * S, h * S, body, COMMON + WOOD + WOODV + STONE + CLOTH + defs))


# ---------------- helpers (copiados de gen_estruturas.py) ----------------
def flames(R, cx, cy, spread, n=5, scale=1.0):
    out = f'<ellipse cx="{cx}" cy="{cy}" rx="{spread*1.4}" ry="{spread*1.1}" fill="url(#glow)"/>'
    for _ in range(n):
        x = cx + R.uniform(-spread, spread)
        y = cy + R.uniform(-spread * .5, spread * .6)
        h = R.uniform(30, 48) * scale
        w = h * .45
        out += (f'<path d="M{x-w/2:.0f},{y:.0f} Q{x-w*.6:.0f},{y-h*.5:.0f} {x:.0f},{y-h:.0f} Q{x+w*.2:.0f},{y-h*.55:.0f} {x+w*.35:.0f},{y-h*.6:.0f} Q{x+w*.7:.0f},{y-h*.3:.0f} {x+w/2:.0f},{y:.0f} Z" fill="#ff8a2a" opacity=".92"/>'
                f'<path d="M{x-w/4:.0f},{y:.0f} Q{x-w*.2:.0f},{y-h*.35:.0f} {x:.0f},{y-h*.6:.0f} Q{x+w*.25:.0f},{y-h*.3:.0f} {x+w/4:.0f},{y:.0f} Z" fill="#ffe27a"/>')
    return out


def soot(R, cx, cy, r, embers=6):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#soot)"/>' + "".join(
        f'<circle cx="{cx+R.uniform(-r,r)*.7:.0f}" cy="{cy+R.uniform(-r,r)*.7:.0f}" r="{R.uniform(1.5,3.5):.1f}" fill="#ff6a1a" opacity=".8"/>' for _ in range(embers))


def scorch(R, cx, cy, r):
    """Mancha de chamuscado (sem brasas)."""
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{r*R.uniform(.6,.9):.0f}" fill="url(#scorch)" transform="rotate({R.uniform(0,180):.0f} {cx} {cy})"/>'


def rubble(R, cx, cy, spread, n, colors, size=(8, 22), stroke="#1c1b19"):
    out = ""
    for _ in range(n):
        x, y = cx + R.gauss(0, spread), cy + R.gauss(0, spread)
        r = R.uniform(*size)
        k = R.randint(4, 6)
        a0 = R.uniform(0, math.pi)
        pts = " ".join(f"{x+r*R.uniform(.6,1)*math.cos(a0+i*2*math.pi/k):.1f},{y+r*R.uniform(.6,1)*math.sin(a0+i*2*math.pi/k):.1f}" for i in range(k))
        out += f'<polygon points="{pts}" fill="{R.choice(colors)}" stroke="{stroke}" stroke-width="1.5"/>'
    return out


def crack(R, x, y, steps, ang, width=2.2, color="#141210"):
    d = f"M{x:.0f},{y:.0f}"
    for _ in range(steps):
        ang += R.uniform(-.6, .6)
        L = R.uniform(10, 22)
        x, y = x + L * math.cos(ang), y + L * math.sin(ang)
        d += f" L{x:.0f},{y:.0f}"
    return f'<path d="{d}" stroke="{color}" stroke-width="{width}" fill="none" stroke-linejoin="round"/>'


def splinters(R, n, cx, cy, spread, color="#74482a"):
    out = ""
    for _ in range(n):
        x, y = cx + R.gauss(0, spread), cy + R.gauss(0, spread * .7)
        L, a = R.uniform(10, 34), R.uniform(0, math.pi)
        out += f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{x+L*math.cos(a):.0f}" y2="{y+L*math.sin(a):.0f}" stroke="{color}" stroke-width="{R.uniform(3,6):.1f}" stroke-linecap="round"/>'
    return out


# ---------------- helpers próprios ----------------
def shadow(x, y, w, h, rx=8, op=.4):
    return f'<rect x="{x+4}" y="{y+8}" width="{w}" height="{h}" rx="{rx}" fill="#000" opacity="{op}" filter="url(#bl8)"/>'


def planks(x, y, w, h, n, color, horizontal=True, R=None, filt="wd", rx=0):
    """Tábuas lado a lado com veio, emendas e contorno."""
    R = R or random.Random(int(x + y + w))
    out = f'<g filter="url(#{filt})">'
    seams = ""
    if horizontal:
        ph = h / n
        for i in range(n):
            out += f'<rect x="{x}" y="{y+i*ph:.1f}" width="{w}" height="{ph:.1f}" fill="{shade(color, R.uniform(.88, 1.1))}"/>'
            if i:
                seams += f'<line x1="{x}" y1="{y+i*ph:.1f}" x2="{x+w}" y2="{y+i*ph:.1f}"/>'
    else:
        pw = w / n
        for i in range(n):
            out += f'<rect x="{x+i*pw:.1f}" y="{y}" width="{pw:.1f}" height="{h}" fill="{shade(color, R.uniform(.88, 1.1))}"/>'
            if i:
                seams += f'<line x1="{x+i*pw:.1f}" y1="{y}" x2="{x+i*pw:.1f}" y2="{y+h}"/>'
    out += f'</g><g stroke="{INK}" stroke-width="2" opacity=".8">{seams}</g>'
    return out


def burning(R, base, spots, n=6, scale=1.0, sootr=46):
    """Desenho escurecido + fuligem + chamas em cada ponto (cx, cy, spread)."""
    out = f'<g filter="url(#dk)">{base}</g>'
    for cx, cy, sp in spots:
        out += soot(R, cx, cy, sootr)
    for cx, cy, sp in spots:
        out += flames(R, cx, cy, sp, n, scale)
    return out


def charred_bits(R, cx, cy, spread, n, L=(24, 50), t=12):
    return "".join(
        f'<g transform="translate({cx+R.gauss(0,spread):.0f} {cy+R.gauss(0,spread*.7):.0f}) rotate({R.uniform(0,180):.0f})">'
        f'<rect x="-{(l:=R.randint(*L))/2}" y="-{t/2}" width="{l}" height="{t}" rx="4" fill="{R.choice(["#1c120c","#2a1a10","#120c08"])}"/></g>' for _ in range(n))


def embers(R, cx, cy, sx, sy, n):
    return '<g opacity=".8">' + "".join(
        f'<circle cx="{cx+R.uniform(-sx,sx):.0f}" cy="{cy+R.uniform(-sy,sy):.0f}" r="{R.uniform(1,3):.1f}" fill="#ff7b2e"/>' for _ in range(n)) + '</g>'


def gear(cx, cy, r, teeth, color="#c9a24a", rot=0.0, op=1.0):
    pts = []
    for i in range(teeth):
        a = rot + i * 2 * math.pi / teeth
        d = math.pi / teeth
        for aa, rr in ((a - d * .55, r * .82), (a - d * .3, r), (a + d * .3, r), (a + d * .55, r * .82)):
            pts.append(f"{cx+rr*math.cos(aa):.1f},{cy+rr*math.sin(aa):.1f}")
    spokes = "".join(f'<line x1="{cx}" y1="{cy}" x2="{cx+r*.6*math.cos(rot+k*math.pi/2):.1f}" y2="{cy+r*.6*math.sin(rot+k*math.pi/2):.1f}"/>' for k in range(4))
    return (f'<g opacity="{op}"><polygon points="{" ".join(pts)}" fill="{color}" stroke="#4a3410" stroke-width="2"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r*.62:.1f}" fill="{shade(color, .8)}" stroke="#4a3410" stroke-width="1.5"/>'
            f'<g stroke="#4a3410" stroke-width="{max(1.5, r*.12):.1f}">{spokes}</g>'
            f'<circle cx="{cx}" cy="{cy}" r="{r*.18:.1f}" fill="#3a2a10"/></g>')


def straw(R, cx, cy, sx, sy, n, colors=("#e0c060", "#a8842e", "#f0d77a", "#c9a44a"), L=(8, 18), ang=None, width=1.8):
    out = ""
    for _ in range(n):
        x, y = cx + R.uniform(-sx, sx), cy + R.uniform(-sy, sy)
        a = R.uniform(0, math.pi) if ang is None else ang + R.gauss(0, .35)
        l = R.uniform(*L)
        out += f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{x+l*math.cos(a):.0f}" y2="{y+l*math.sin(a):.0f}" stroke="{R.choice(colors)}" stroke-width="{width}" stroke-linecap="round"/>'
    return out


# =====================================================================
# Amplificador geométrico (1x1): orbe de cristal com engrenagens de latão
# =====================================================================
AMP_DEFS = ('<radialGradient id="orb" cx=".42" cy=".38"><stop offset="0" stop-color="#f4fcff"/><stop offset=".45" stop-color="#bfe6ff"/><stop offset="1" stop-color="#4c94c8"/></radialGradient>'
            '<radialGradient id="orbd" cx=".42" cy=".38"><stop offset="0" stop-color="#d8eef8"/><stop offset=".5" stop-color="#8fbcd8"/><stop offset="1" stop-color="#3a6a8e"/></radialGradient>'
            '<radialGradient id="halo"><stop offset="0" stop-color="#9fd8ff" stop-opacity=".85"/><stop offset=".6" stop-color="#9fd8ff" stop-opacity=".3"/><stop offset="1" stop-color="#9fd8ff" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="brass" cx=".4" cy=".35"><stop offset="0" stop-color="#e2c070"/><stop offset="1" stop-color="#8a6a2a"/></radialGradient>')


def amp_stand():
    bolts = "".join(f'<circle cx="{100+80*math.cos(a):.1f}" cy="{100+80*math.sin(a):.1f}" r="3.5" fill="#5a4418" stroke="#2a1e08" stroke-width="1"/>'
                    for a in [i * math.pi / 4 + math.pi / 8 for i in range(8)])
    return ('<circle cx="104" cy="108" r="88" fill="#000" opacity=".4" filter="url(#bl8)"/>'
            '<circle cx="100" cy="100" r="88" fill="url(#brass)" stroke="#2a1e08" stroke-width="3"/>'
            '<circle cx="100" cy="100" r="72" fill="none" stroke="#5a4418" stroke-width="2"/>' + bolts)


def amp_orb(dim=False, rot=0.0):
    facets = ""
    hexa = [(100 + 46 * math.cos(a), 100 + 46 * math.sin(a)) for a in [i * math.pi / 3 + rot for i in range(6)]]
    for i, (x, y) in enumerate(hexa):
        x2, y2 = hexa[(i + 1) % 6]
        x3, y3 = hexa[(i + 2) % 6]
        facets += f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/><line x1="{x:.1f}" y1="{y:.1f}" x2="{x3:.1f}" y2="{y3:.1f}"/>'
    return (f'<circle cx="100" cy="100" r="68" fill="url(#{"orbd" if dim else "orb"})" stroke="#2c5a7e" stroke-width="3"/>'
            + gear(84, 90, 27, 10, rot=rot, op=.85) + gear(124, 106, 19, 8, rot=-rot * 1.4 + .2, op=.85)
            + gear(96, 130, 14, 7, rot=rot * 2, op=.85)
            + f'<g stroke="#f4fcff" stroke-width="1.6" opacity=".45">{facets}</g>'
            '<ellipse cx="78" cy="70" rx="24" ry="13" fill="#fff" opacity=".55" transform="rotate(-35 78 70)"/>'
            '<path d="M146,110 A48,48 0 0 1 112,146" stroke="#fff" stroke-width="4" fill="none" opacity=".35" stroke-linecap="round"/>')


write("amplificador", "amplificador_brilhando",
      '<circle cx="100" cy="100" r="100" fill="url(#halo)"/>' + amp_stand() + amp_orb()
      + '<circle cx="100" cy="100" r="68" fill="url(#halo)" opacity=".35"/>', AMP_DEFS)
R = random.Random(101)
write("amplificador", "amplificador_rachado",
      '<circle cx="100" cy="100" r="86" fill="url(#halo)" opacity=".45"/>' + amp_stand() + amp_orb(True, .35)
      + crack(R, 62, 62, 6, .7, 3, "#1c2a38") + crack(R, 62, 62, 6, .7, 1.2, "#eaf6ff")
      + crack(R, 150, 92, 5, 2.4, 2.6, "#1c2a38") + crack(R, 100, 100, 4, 1.9, 2, "#1c2a38")
      + crack(R, 100, 100, 4, -.9, 2, "#1c2a38"), AMP_DEFS)
R = random.Random(102)
shards = ""
for _ in range(16):
    x, y = 100 + max(-60, min(60, R.gauss(0, 38))), 100 + max(-60, min(60, R.gauss(0, 38)))
    r = R.uniform(7, 18)
    a0 = R.uniform(0, math.pi)
    pts = " ".join(f"{x+r*R.uniform(.5,1)*math.cos(a0+i*2*math.pi/3):.1f},{y+r*R.uniform(.5,1)*math.sin(a0+i*2*math.pi/3):.1f}" for i in range(3))
    shards += f'<polygon points="{pts}" fill="{R.choice(["#bfe6ff","#d8f2ff","#8fc4e8"])}" opacity=".85" stroke="#2c5a7e" stroke-width="1.5"/>'
glints = "".join(f'<circle cx="{100+R.gauss(0,50):.0f}" cy="{100+R.gauss(0,50):.0f}" r="{R.uniform(1,2.2):.1f}" fill="#eaf6ff"/>' for _ in range(18))
write("amplificador", "amplificador_estilhacado",
      amp_stand() + '<circle cx="100" cy="100" r="66" fill="#2a2418" stroke="#1a1408" stroke-width="2"/>'
      '<circle cx="100" cy="100" r="40" fill="none" stroke="#3a3220" stroke-width="2"/>'
      + shards + gear(58, 132, 22, 10, rot=.5) + gear(146, 64, 17, 8, rot=1.1) + gear(132, 150, 12, 7, rot=.2)
      + gear(70, 60, 10, 6, rot=.7) + glints, AMP_DEFS)

# =====================================================================
# Fogueira do Hearth (2x2): fosso de pedra com lenha
# =====================================================================
FIRE_DEFS = (noise("ash", "0.09", 5, (.2, .19, .18), 1.2, -.35)
             + '<radialGradient id="coal"><stop offset="0" stop-color="#ffd27a"/><stop offset=".35" stop-color="#ff7a1a"/><stop offset=".8" stop-color="#9a2a0a" stop-opacity=".8"/><stop offset="1" stop-color="#4a1a0a" stop-opacity="0"/></radialGradient>'
             + '<radialGradient id="coald"><stop offset="0" stop-color="#ff7a1a" stop-opacity=".8"/><stop offset=".5" stop-color="#8a2a0a" stop-opacity=".6"/><stop offset="1" stop-color="#3a1a0a" stop-opacity="0"/></radialGradient>'
             + '<radialGradient id="bigglow"><stop offset="0" stop-color="#ffb347" stop-opacity=".6"/><stop offset=".55" stop-color="#ff7a1a" stop-opacity=".22"/><stop offset="1" stop-color="#ff5a1a" stop-opacity="0"/></radialGradient>')


def firepit(R, lit=True):
    cx = cy = 200
    out = '<circle cx="206" cy="214" r="178" fill="#000" opacity=".4" filter="url(#bl8)"/>'
    if lit:
        out += '<circle cx="200" cy="200" r="200" fill="url(#bigglow)"/>'
    # anel de pedras
    out += '<circle cx="200" cy="200" r="168" fill="#3d3934" stroke="#1c1b19" stroke-width="3"/>'
    stones = ""
    n = 18
    for i in range(n):
        a = i * 2 * math.pi / n + R.uniform(-.05, .05)
        x, y = cx + 150 * math.cos(a), cy + 150 * math.sin(a)
        r = R.uniform(24, 30)
        k = R.randint(5, 7)
        a0 = R.uniform(0, math.pi)
        pts = " ".join(f"{x+r*R.uniform(.75,1)*math.cos(a0+j*2*math.pi/k):.1f},{y+r*R.uniform(.75,1)*math.sin(a0+j*2*math.pi/k):.1f}" for j in range(k))
        stones += f'<polygon points="{pts}" fill="{shade("#7a756c", R.uniform(.8, 1.15))}" stroke="#1c1b19" stroke-width="2.5"/>'
    out += f'<g filter="url(#st)">{stones}</g>'
    # cinza
    out += '<circle cx="200" cy="200" r="126" fill="#2a2420" stroke="#141210" stroke-width="3"/>'
    out += '<circle cx="200" cy="200" r="118" fill="#4a443e" filter="url(#ash)"/>'
    out += f'<circle cx="200" cy="200" r="{80 if lit else 70}" fill="url(#{"coal" if lit else "coald"})"/>'
    # lenha em estrela apontando para o centro
    logs = ""
    for i in range(6):
        a = i * math.pi / 3 + .3 + R.uniform(-.12, .12)
        deg = math.degrees(a)
        bark = shade("#5a3a22", R.uniform(.85, 1.1))
        logs += (f'<g transform="translate(200 200) rotate({deg:.1f})">'
                 f'<rect x="28" y="-14" width="86" height="28" rx="12" fill="{bark}" stroke="#1c120c" stroke-width="2.5" filter="url(#wd)"/>'
                 f'<rect x="28" y="-14" width="34" height="28" rx="12" fill="#1c120c" opacity=".85"/>'
                 f'<line x1="66" y1="-6" x2="104" y2="-6" stroke="#2a180a" stroke-width="2" opacity=".6"/>'
                 f'<line x1="72" y1="5" x2="108" y2="5" stroke="#2a180a" stroke-width="2" opacity=".6"/>'
                 f'<ellipse cx="114" cy="0" rx="5" ry="13" fill="#a87a4a" stroke="#1c120c" stroke-width="2"/>'
                 f'<ellipse cx="114" cy="0" rx="2.5" ry="7" fill="none" stroke="#6a4322" stroke-width="1.2"/>')
        if lit:
            logs += '<rect x="34" y="-3" width="20" height="6" rx="3" fill="#ff8a2a" opacity=".9"/>'
        else:
            logs += '<rect x="34" y="-3" width="16" height="5" rx="2.5" fill="#c84a14" opacity=".8"/>'
        logs += '</g>'
    out += logs
    return out


R = random.Random(201)
pit = firepit(R, True)
R2 = random.Random(202)
write("fogueira", "fogueira_acesa", pit + flames(R2, 200, 210, 42, 10, 1.9) + flames(R2, 200, 205, 22, 5, 1.3), FIRE_DEFS)
R = random.Random(201)
pit = firepit(R, False)
R2 = random.Random(203)
write("fogueira", "fogueira_brasas", pit + embers(R2, 200, 200, 60, 60, 40)
      + '<circle cx="200" cy="200" r="34" fill="url(#coal)" opacity=".7"/>', FIRE_DEFS)

# =====================================================================
# Balcão do bar (1x1, segmento: o tampo vai de borda a borda na horizontal)
# =====================================================================
BAR_DEFS = ('<radialGradient id="mug" cx=".4" cy=".4"><stop offset="0" stop-color="#f6ecd0"/><stop offset=".7" stop-color="#e0cc98"/><stop offset="1" stop-color="#b89a5a"/></radialGradient>'
            '<radialGradient id="bottle" cx=".38" cy=".35"><stop offset="0" stop-color="#6ab06a"/><stop offset="1" stop-color="#1e4a26"/></radialGradient>'
            '<clipPath id="barL"><polygon points="-5,0 74,0 64,60 80,96 60,130 76,200 -5,200"/></clipPath>'
            '<clipPath id="barR"><polygon points="205,0 140,0 128,50 144,90 124,140 136,200 205,200"/></clipPath>')


def bar_top(items=True):
    out = ('<rect x="-20" y="44" width="240" height="122" fill="#000" opacity=".4" filter="url(#bl8)"/>'
           '<rect x="-2" y="36" width="204" height="128" fill="#4a2c18"/>'
           + planks(-2, 46, 204, 108, 3, "#8a5a30", R=random.Random(301))
           + '<rect x="-2" y="36" width="204" height="12" fill="#6a4322" filter="url(#wd)"/>'
           '<rect x="-2" y="152" width="204" height="12" fill="#6a4322" filter="url(#wd)"/>'
           f'<g stroke="{INK}" stroke-width="3"><line x1="-2" y1="36" x2="202" y2="36"/><line x1="-2" y1="164" x2="202" y2="164"/></g>'
           f'<g stroke="{INK}" stroke-width="1.5" opacity=".7"><line x1="-2" y1="48" x2="202" y2="48"/><line x1="-2" y1="152" x2="202" y2="152"/></g>'
           '<g fill="#2e2e30"><circle cx="20" cy="42" r="2"/><circle cx="100" cy="42" r="2"/><circle cx="180" cy="42" r="2"/>'
           '<circle cx="20" cy="158" r="2"/><circle cx="100" cy="158" r="2"/><circle cx="180" cy="158" r="2"/></g>')
    if items:
        out += ('<circle cx="122" cy="82" r="13" fill="none" stroke="#5a3a1a" stroke-width="2.5" opacity=".45"/>'
                # caneca com espuma
                '<circle cx="60" cy="88" r="17" fill="#000" opacity=".35" filter="url(#bl4)"/>'
                '<rect x="68" y="80" width="14" height="9" rx="4" fill="#6a4a2a" stroke="#2a180a" stroke-width="2"/>'
                '<circle cx="56" cy="84" r="15" fill="#7a5a34" stroke="#2a180a" stroke-width="2.5"/>'
                '<circle cx="56" cy="84" r="11" fill="url(#mug)"/>'
                '<circle cx="52" cy="80" r="3" fill="#fff" opacity=".7"/>'
                # garrafa
                '<circle cx="152" cy="122" r="14" fill="#000" opacity=".35" filter="url(#bl4)"/>'
                '<circle cx="148" cy="116" r="13" fill="url(#bottle)" stroke="#0e2412" stroke-width="2"/>'
                '<circle cx="148" cy="116" r="5" fill="#3a6a3a" stroke="#0e2412" stroke-width="1.5"/>'
                '<circle cx="148" cy="116" r="2.5" fill="#c9a24a"/>'
                '<ellipse cx="143" cy="110" rx="3" ry="5" fill="#d8f0d0" opacity=".5" transform="rotate(-30 143 110)"/>'
                # caneca virada de boca para baixo (fundo)
                '<circle cx="104" cy="128" r="12" fill="#000" opacity=".3" filter="url(#bl4)"/>'
                '<circle cx="101" cy="124" r="11" fill="#8a6a44" stroke="#2a180a" stroke-width="2"/>'
                '<circle cx="101" cy="124" r="6" fill="none" stroke="#5a3a1a" stroke-width="1.5"/>')
    return out


write("balcao", "balcao_inteiro", bar_top(), BAR_DEFS)
R = random.Random(311)
write("balcao", "balcao_chamuscado", bar_top() + scorch(R, 40, 120, 40) + scorch(R, 140, 70, 46) + scorch(R, 100, 140, 30), BAR_DEFS)
R = random.Random(312)
glass = rubble(R, 104, 110, 14, 7, ["#3a7a42", "#2a5a32", "#5a9a5a"], (3, 6), "#0e2412")
broken_bar = ('<ellipse cx="102" cy="108" rx="58" ry="46" fill="url(#ale)"/>'
              + f'<g clip-path="url(#barL)" transform="rotate(4 0 100)">{bar_top(False)}</g>'
              + f'<g clip-path="url(#barR)" transform="rotate(-5 200 100)">{bar_top(False)}</g>'
              + splinters(R, 14, 102, 104, 18) + splinters(R, 5, 102, 104, 20, INK) + glass
              + '<g transform="rotate(70 92 140)"><rect x="80" y="132" width="26" height="16" rx="7" fill="#7a5a34" stroke="#2a180a" stroke-width="2"/></g>')
write("balcao", "balcao_quebrado", broken_bar, BAR_DEFS)
R = random.Random(313)
write("balcao", "balcao_queimando", burning(R, bar_top(), [(50, 110, 30), (150, 105, 30)], 5), BAR_DEFS)
R = random.Random(314)
write("balcao", "balcao_queimado",
      f'<g filter="url(#ch)"><g clip-path="url(#barL)">{bar_top(False)}</g><g clip-path="url(#barR)">{bar_top(False)}</g></g>'
      + soot(R, 100, 100, 70, 8) + charred_bits(R, 100, 100, 18, 6) + embers(R, 100, 100, 90, 50, 12), BAR_DEFS)

# =====================================================================
# Cadeira (1x1)
# =====================================================================


def chair(col="#8a5a30"):
    R = random.Random(401)
    return (shadow(46, 34, 112, 128, 10)
            + '<rect x="52" y="62" width="96" height="98" rx="8" fill="#4a2c18"/>'
            + f'<g clip-path="url(#seat)">{planks(52, 62, 96, 98, 4, col, R=R)}</g>'
            + f'<rect x="52" y="62" width="96" height="98" rx="8" fill="none" stroke="{INK}" stroke-width="3"/>'
            + "".join(f'<circle cx="{x}" cy="{y}" r="1.8" fill="#2e2e30"/>' for x in (60, 140) for y in (74, 98, 122, 146))
            + "".join(f'<rect x="{x-4}" y="52" width="8" height="12" rx="2" fill="{shade(col, .7)}" stroke="{INK}" stroke-width="1.5"/>' for x in (72, 92, 108, 128))
            + f'<rect x="42" y="32" width="116" height="24" rx="11" fill="{shade(col, .82)}" filter="url(#wd)" stroke="{INK}" stroke-width="3"/>'
            + f'<line x1="52" y1="40" x2="148" y2="40" stroke="{shade(col, 1.15)}" stroke-width="2" opacity=".6"/>'
            + f'<circle cx="54" cy="44" r="9" fill="{shade(col, .7)}" stroke="{INK}" stroke-width="2.5"/>'
            + f'<circle cx="146" cy="44" r="9" fill="{shade(col, .7)}" stroke="{INK}" stroke-width="2.5"/>')


CHAIR_DEFS = '<clipPath id="seat"><rect x="52" y="62" width="96" height="98" rx="8"/></clipPath>'
write("cadeira", "cadeira_inteira", chair(), CHAIR_DEFS)


def chair_parts(R, col, burnt=False):
    f = ' filter="url(#ch)"' if burnt else ""
    out = f'<g{f}>'
    out += (f'<g transform="translate(78 108) rotate({R.uniform(-30,-10):.0f})">'
            f'<rect x="-28" y="-26" width="56" height="52" rx="6" fill="#4a2c18"/>'
            + planks(-28, -26, 56, 52, 2, col, R=R) + f'<rect x="-28" y="-26" width="56" height="52" rx="6" fill="none" stroke="{INK}" stroke-width="3"/></g>')
    out += (f'<g transform="translate(132 120) rotate({R.uniform(15,40):.0f})">'
            f'<rect x="-22" y="-24" width="44" height="48" rx="6" fill="#4a2c18"/>'
            + planks(-22, -24, 44, 48, 2, col, R=R) + f'<polygon points="-22,24 22,24 22,-8 14,0 6,-12 -4,-2 -12,-14 -22,-6" fill="none" stroke="{INK}" stroke-width="3"/></g>')
    out += (f'<g transform="translate(96 44) rotate({R.uniform(-14,-4):.0f})">'
            f'<rect x="-56" y="-11" width="112" height="22" rx="10" fill="{shade(col, .82)}" filter="url(#wd)" stroke="{INK}" stroke-width="3"/></g>')
    for _ in range(4):
        x, y, a = R.uniform(40, 160), R.uniform(60, 175), R.uniform(0, 180)
        out += (f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f})"><rect x="-22" y="-5" width="44" height="10" rx="4" '
                f'fill="{shade(col, .75)}" stroke="{INK}" stroke-width="2"/></g>')
    return out + '</g>'


R = random.Random(411)
write("cadeira", "cadeira_quebrada", chair_parts(R, "#8a5a30") + splinters(R, 10, 100, 110, 30), CHAIR_DEFS)
R = random.Random(412)
write("cadeira", "cadeira_queimando", burning(R, chair(), [(100, 112, 30)], 6), CHAIR_DEFS)
R = random.Random(413)
write("cadeira", "cadeira_queimada", soot(R, 100, 104, 72, 8) + charred_bits(R, 100, 104, 26, 8, (24, 46), 11) + embers(R, 100, 104, 50, 40, 8), CHAIR_DEFS)

# =====================================================================
# Poltrona de couro vinho (1x1)
# =====================================================================
ARM_DEFS = ('<linearGradient id="lea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8e2c3a"/><stop offset="1" stop-color="#5e1822"/></linearGradient>'
            '<radialGradient id="cush" cx=".45" cy=".4"><stop offset="0" stop-color="#a23a48"/><stop offset="1" stop-color="#6a1e2a"/></radialGradient>'
            + noise("lt", "0.12", 9, (.18, .04, .06), 1.0, -.4))


def armchair():
    studs = "".join(f'<circle cx="{x}" cy="{y}" r="2" fill="#d8b45a" stroke="#5a4418" stroke-width=".8"/>'
                    for x in (46, 154) for y in range(72, 172, 14))
    tufts = "".join(f'<circle cx="{x}" cy="{y}" r="2.6" fill="#3a0e16"/>'
                    for (x, y) in [(84, 98), (116, 98), (100, 116), (84, 134), (116, 134), (100, 152)])
    creases = ('<g stroke="#4a121c" stroke-width="1.6" opacity=".7" fill="none">'
               '<path d="M84,98 L100,116 L116,98"/><path d="M84,134 L100,116 L116,134"/><path d="M84,134 L100,152 L116,134"/>'
               '<path d="M64,98 L84,98"/><path d="M116,98 L136,98"/><path d="M64,134 L84,134"/><path d="M116,134 L136,134"/></g>')
    return (shadow(26, 24, 150, 156, 26)
            + '<rect x="26" y="24" width="148" height="152" rx="26" fill="#3a2010" stroke="#1a0e08" stroke-width="3"/>'
            '<g filter="url(#lt)">'
            '<rect x="30" y="28" width="140" height="48" rx="22" fill="url(#lea)"/>'
            '<rect x="30" y="56" width="32" height="116" rx="14" fill="url(#lea)"/>'
            '<rect x="138" y="56" width="32" height="116" rx="14" fill="url(#lea)"/>'
            '<rect x="62" y="74" width="76" height="96" rx="12" fill="url(#cush)"/></g>'
            '<g fill="none" stroke="#2a0a10" stroke-width="2.5">'
            '<rect x="30" y="28" width="140" height="48" rx="22"/>'
            '<rect x="30" y="56" width="32" height="116" rx="14"/><rect x="138" y="56" width="32" height="116" rx="14"/>'
            '<rect x="62" y="74" width="76" height="96" rx="12"/></g>'
            '<path d="M44,44 Q100,30 156,44" stroke="#b44a58" stroke-width="3" fill="none" opacity=".6"/>'
            '<g fill="#3a0e16">' + "".join(f'<circle cx="{x}" cy="50" r="2.6"/>' for x in (64, 88, 112, 136)) + '</g>'
            + creases + tufts + studs
            + '<ellipse cx="88" cy="86" rx="14" ry="6" fill="#fff" opacity=".12"/>')


write("poltrona", "poltrona_inteira", armchair(), ARM_DEFS)
R = random.Random(421)
fluff = "".join(f'<circle cx="{100+R.gauss(0,26):.0f}" cy="{118+R.gauss(0,22):.0f}" r="{R.uniform(4,9):.1f}" fill="{R.choice(["#e8e0cc","#d6ccb4","#f2ecdc"])}" stroke="#a89a7a" stroke-width="1"/>' for _ in range(18))
torn = ('<g transform="rotate(-8 100 100)">'
        '<g filter="url(#lt)"><rect x="34" y="26" width="132" height="44" rx="20" fill="url(#lea)" stroke="#2a0a10" stroke-width="2.5"/></g>'
        '<path d="M70,40 L82,56 L92,42 L104,58 L116,40" stroke="#1a0608" stroke-width="3" fill="none"/></g>'
        '<g transform="rotate(-25 46 120)"><rect x="30" y="64" width="32" height="112" rx="14" fill="url(#lea)" stroke="#2a0a10" stroke-width="2.5" filter="url(#lt)"/></g>'
        '<g transform="rotate(18 156 120)"><rect x="140" y="62" width="32" height="112" rx="14" fill="url(#lea)" stroke="#2a0a10" stroke-width="2.5" filter="url(#lt)"/></g>'
        '<g transform="rotate(12 100 124)"><rect x="66" y="82" width="70" height="86" rx="12" fill="url(#cush)" stroke="#2a0a10" stroke-width="2.5"/>'
        '<path d="M76,110 L92,124 L84,140 L104,150 L98,166" stroke="#1a0608" stroke-width="4" fill="none"/></g>')
write("poltrona", "poltrona_quebrada", torn + fluff + splinters(R, 10, 100, 120, 34, "#3a2010"), ARM_DEFS)
R = random.Random(422)
write("poltrona", "poltrona_queimando", burning(R, armchair(), [(100, 112, 34)], 7), ARM_DEFS)
R = random.Random(423)
springs = "".join(f'<g transform="translate({x} {y})"><circle r="9" fill="none" stroke="#5a5a5e" stroke-width="2.2"/><circle r="5" fill="none" stroke="#6a6a6e" stroke-width="1.8"/></g>'
                  for (x, y) in [(82, 100), (118, 100), (82, 136), (118, 136), (100, 118)])
write("poltrona", "poltrona_queimada", soot(R, 100, 104, 80, 8) + charred_bits(R, 100, 104, 30, 7, (30, 60), 13) + springs + embers(R, 100, 104, 50, 46, 8), ARM_DEFS)

# =====================================================================
# Banco comprido (2x1)
# =====================================================================


def bench(col="#8a5a30"):
    R = random.Random(431)
    return (shadow(20, 58, 362, 86, 10)
            + '<rect x="20" y="60" width="360" height="82" rx="10" fill="#4a2c18"/>'
            + f'<g clip-path="url(#bnc)">{planks(20, 60, 360, 82, 2, col, R=R)}</g>'
            + f'<rect x="20" y="60" width="360" height="82" rx="10" fill="none" stroke="{INK}" stroke-width="3"/>'
            + "".join(f'<rect x="{x-7}" y="{y-9}" width="14" height="18" rx="2" fill="{shade(col, .65)}" stroke="{INK}" stroke-width="2"/>'
                      for x in (52, 348) for y in (80, 122))
            + "".join(f'<circle cx="{x}" cy="{y}" r="1.8" fill="#2e2e30"/>' for x in (30, 200, 370) for y in (70, 132))
            + '<ellipse cx="250" cy="80" rx="8" ry="2.5" fill="#3b2412" opacity=".55"/>'
            + '<ellipse cx="130" cy="122" rx="6" ry="2.5" fill="#3b2412" opacity=".55"/>')


BENCH_DEFS = '<clipPath id="bnc"><rect x="20" y="60" width="360" height="82" rx="10"/></clipPath>'
write("banco", "banco_inteiro", bench(), BENCH_DEFS)
R = random.Random(441)
bL = '<clipPath id="bl"><polygon points="0,0 196,0 186,70 204,96 182,120 196,200 0,200"/></clipPath>'
bR = '<clipPath id="brr"><polygon points="400,0 210,0 200,70 216,96 194,120 208,200 400,200"/></clipPath>'
write("banco", "banco_quebrado",
      f'<g transform="rotate(-7 30 100)"><g clip-path="url(#bl)">{bench()}</g></g>'
      f'<g transform="rotate(9 370 100)"><g clip-path="url(#brr)">{bench()}</g></g>'
      + splinters(R, 14, 200, 104, 22) + splinters(R, 5, 200, 104, 22, INK), BENCH_DEFS + bL + bR)
R = random.Random(442)
write("banco", "banco_queimando", burning(R, bench(), [(110, 108, 30), (290, 104, 30)], 5), BENCH_DEFS)
R = random.Random(443)
write("banco", "banco_queimado", soot(R, 120, 102, 70, 6) + soot(R, 280, 102, 70, 6)
      + charred_bits(R, 200, 102, 55, 9, (30, 60), 12) + embers(R, 200, 102, 150, 40, 12), BENCH_DEFS)

# =====================================================================
# Cama simples (1x2)
# =====================================================================
BED_DEFS = ('<linearGradient id="mat" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#c8bc9c"/><stop offset=".5" stop-color="#e2d8bc"/><stop offset="1" stop-color="#c8bc9c"/></linearGradient>'
            '<radialGradient id="pil" cx=".45" cy=".4"><stop offset="0" stop-color="#fbf7ec"/><stop offset="1" stop-color="#d6ccb4"/></radialGradient>'
            + noise("wl", "0.35", 4, (.12, .04, .03), 1.1, -.35))
WOOL = "#8a3a2a"


def bed_frame(col="#6a4322"):
    return (shadow(18, 14, 166, 372, 10)
            + f'<rect x="18" y="14" width="164" height="370" rx="8" fill="{col}" filter="url(#wv)" stroke="{INK}" stroke-width="3"/>'
            + f'<rect x="12" y="10" width="176" height="34" rx="8" fill="{shade(col, .85)}" filter="url(#wd)" stroke="{INK}" stroke-width="3"/>'
            + f'<line x1="22" y1="20" x2="178" y2="20" stroke="{shade(col, 1.2)}" stroke-width="2" opacity=".6"/>'
            + "".join(f'<circle cx="{x}" cy="{y}" r="10" fill="{shade(col, .75)}" stroke="{INK}" stroke-width="2.5"/>' for x in (22, 178) for y in (27,))
            + "".join(f'<circle cx="{x}" cy="376" r="9" fill="{shade(col, .75)}" stroke="{INK}" stroke-width="2.5"/>' for x in (24, 176)))


def blanket_band(y0, y1, x0=28, x1=172):
    return (f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" rx="6" fill="{WOOL}" filter="url(#wl)"/>'
            f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="18" rx="6" fill="{shade(WOOL, 1.25)}" filter="url(#wl)"/>'
            f'<g fill="{shade(WOOL, .7)}"><rect x="{x0}" y="{y0+34}" width="{x1-x0}" height="8"/><rect x="{x0}" y="{y0+48}" width="{x1-x0}" height="4"/>'
            f'<rect x="{x0}" y="{y1-44}" width="{x1-x0}" height="4"/><rect x="{x0}" y="{y1-36}" width="{x1-x0}" height="8"/></g>'
            f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" rx="6" fill="none" stroke="#3a140c" stroke-width="2.5"/>'
            f'<line x1="{x0}" y1="{y0+18}" x2="{x1}" y2="{y0+18}" stroke="#3a140c" stroke-width="1.5" opacity=".7"/>')


def bed(made=True):
    out = bed_frame()
    out += '<rect x="30" y="44" width="140" height="330" rx="8" fill="url(#mat)" stroke="#7a6a4a" stroke-width="2"/>'
    if made:
        out += ('<rect x="46" y="56" width="108" height="58" rx="20" fill="url(#pil)" stroke="#8a7a5a" stroke-width="2"/>'
                '<path d="M60,85 Q100,76 140,85" stroke="#b8ac8c" stroke-width="2" fill="none"/>'
                + blanket_band(140, 374, 26, 174)
                + '<g stroke="#5a2016" stroke-width="1.5" opacity=".5" fill="none"><path d="M60,200 Q66,260 58,330"/><path d="M140,190 Q132,250 142,320"/></g>')
    else:
        out += ('<g stroke="#a89a78" stroke-width="2" fill="none" opacity=".8"><path d="M44,130 Q90,150 150,124"/><path d="M50,170 Q100,190 160,160"/><path d="M60,220 Q96,236 130,214"/></g>'
                '<g transform="rotate(-18 96 86)"><rect x="40" y="58" width="108" height="56" rx="20" fill="url(#pil)" stroke="#8a7a5a" stroke-width="2"/>'
                '<path d="M54,86 Q96,98 136,84" stroke="#b8ac8c" stroke-width="2" fill="none"/></g>'
                f'<path d="M60,250 C40,232 70,214 104,226 C140,206 182,222 188,246 L194,330 C180,368 120,386 80,372 C50,366 34,340 44,300 C30,280 50,262 60,250 Z" fill="{WOOL}" filter="url(#wl)" stroke="#3a140c" stroke-width="2.5"/>'
                f'<path d="M64,250 C80,262 120,240 150,252" stroke="{shade(WOOL, .65)}" stroke-width="7" fill="none"/>'
                f'<path d="M58,310 C90,300 130,320 176,300" stroke="{shade(WOOL, .65)}" stroke-width="7" fill="none"/>'
                '<g stroke="#3a140c" stroke-width="1.8" fill="none" opacity=".7"><path d="M80,280 Q110,268 140,284"/><path d="M70,340 Q110,330 160,346"/><path d="M150,260 Q160,290 150,320"/></g>')
    return out


write("cama", "cama_arrumada", bed(True), BED_DEFS)
write("cama", "cama_desarrumada", bed(False), BED_DEFS)
R = random.Random(451)
broken_bed = ('<g transform="rotate(-4 100 30)">' + bed_frame().replace(shadow(18, 14, 166, 372, 10), "")
              .replace('<rect x="18" y="14" width="164" height="370"', '<rect x="18" y="14" width="164" height="230"') + '</g>'
              + '<g transform="rotate(14 60 260)"><rect x="18" y="244" width="22" height="140" rx="6" fill="#6a4322" filter="url(#wv)" stroke="#2a180a" stroke-width="3"/></g>'
              + '<g transform="rotate(-10 170 260)"><rect x="160" y="244" width="22" height="140" rx="6" fill="#6a4322" filter="url(#wv)" stroke="#2a180a" stroke-width="3"/></g>'
              + '<g transform="rotate(7 100 200)"><rect x="34" y="50" width="134" height="310" rx="10" fill="url(#mat)" stroke="#7a6a4a" stroke-width="2"/>'
              + '<path d="M40,250 Q100,280 162,246" stroke="#8a7a5a" stroke-width="3" fill="none"/>'
              + '<rect x="50" y="62" width="104" height="54" rx="20" fill="url(#pil)" stroke="#8a7a5a" stroke-width="2"/></g>'
              + f'<g transform="rotate(-12 110 320)"><rect x="40" y="270" width="150" height="100" rx="10" fill="{WOOL}" filter="url(#wl)" stroke="#3a140c" stroke-width="2.5"/>'
              + f'<rect x="40" y="300" width="150" height="8" fill="{shade(WOOL, .7)}"/></g>'
              + straw(R, 100, 250, 70, 30, 30, L=(6, 14)) + splinters(R, 12, 100, 250, 40, "#6a4322") + splinters(R, 5, 100, 250, 40, INK))
write("cama", "cama_quebrada", broken_bed, BED_DEFS)
R = random.Random(452)
write("cama", "cama_queimando", burning(R, bed(True), [(100, 130, 34), (96, 250, 36), (104, 340, 30)], 5, 1.1, 54), BED_DEFS)
R = random.Random(453)
write("cama", "cama_queimada",
      '<rect x="34" y="44" width="132" height="322" rx="40" fill="#4a443e" filter="url(#ash)" opacity=".6"/>'
      + soot(R, 100, 110, 80, 6) + soot(R, 100, 210, 80, 6) + soot(R, 100, 310, 80, 6)
      + '<g filter="url(#ch)">'
      + '<rect x="18" y="14" width="18" height="300" rx="6" fill="#6a4322" stroke="#2a180a" stroke-width="2" transform="rotate(2 26 160)"/>'
      + '<rect x="164" y="60" width="18" height="320" rx="6" fill="#6a4322" stroke="#2a180a" stroke-width="2" transform="rotate(-3 172 220)"/>'
      + '<rect x="16" y="12" width="120" height="28" rx="8" fill="#6a4322" stroke="#2a180a" stroke-width="2" transform="rotate(-6 76 26)"/></g>'
      + charred_bits(R, 100, 220, 50, 10, (30, 70), 13) + embers(R, 100, 210, 60, 150, 20),
      BED_DEFS + noise("ash", "0.09", 5, (.2, .19, .18), 1.2, -.35))

# =====================================================================
# Forja (2x2): bloco de pedra, braseiro, chaminé, fole e ferramentas
# =====================================================================
FORGE_DEFS = FIRE_DEFS + ('<linearGradient id="iron" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7a8086"/><stop offset="1" stop-color="#34383c"/></linearGradient>'
                          '<linearGradient id="bel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7a4a2a"/><stop offset=".5" stop-color="#5a3420"/><stop offset="1" stop-color="#3a2014"/></linearGradient>')


def stone_blocks(R, x, y, w, h, rows, base="#6b5e50"):
    out = ""
    rh = h / rows
    for r in range(rows):
        yy = y + r * rh
        xx = x - (R.randint(0, 30) if r % 2 else 0)
        while xx < x + w:
            L = R.randint(46, 78)
            a, b = max(xx, x), min(xx + L, x + w)
            out += f'<rect x="{a+2:.0f}" y="{yy+2:.0f}" width="{b-a-4:.0f}" height="{rh-4:.0f}" rx="4" fill="{shade(base, R.uniform(.82, 1.15))}"/>'
            xx += L
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#2a2420"/><g filter="url(#st)">{out}</g>'


def forge(R, lit=True):
    out = shadow(18, 26, 290, 360, 12)
    out += stone_blocks(R, 20, 28, 286, 352, 8)
    out += '<rect x="20" y="28" width="286" height="352" rx="4" fill="none" stroke="#141210" stroke-width="4"/>'
    # chaminé ao fundo
    out += ('<rect x="104" y="14" width="120" height="86" rx="6" fill="#4a423a" stroke="#141210" stroke-width="4" filter="url(#st)"/>'
            '<rect x="130" y="34" width="68" height="46" rx="4" fill="#0e0c0a" stroke="#2a2420" stroke-width="3"/>')
    # braseiro (fosso de ferro com carvão)
    out += ('<rect x="84" y="138" width="160" height="150" rx="16" fill="#1c1d20" stroke="#0a0a0a" stroke-width="4"/>'
            '<rect x="94" y="148" width="140" height="130" rx="10" fill="#2a2622"/>')
    if lit:
        out += '<ellipse cx="164" cy="213" rx="66" ry="60" fill="url(#coal)"/>'
    coal = ""
    for _ in range(60):
        x, y = R.uniform(102, 226), R.uniform(156, 270)
        r = R.uniform(5, 10)
        k = R.randint(5, 6)
        a0 = R.uniform(0, math.pi)
        pts = " ".join(f"{x+r*R.uniform(.6,1)*math.cos(a0+i*2*math.pi/k):.1f},{y+r*R.uniform(.6,1)*math.sin(a0+i*2*math.pi/k):.1f}" for i in range(k))
        d = math.hypot(x - 164, y - 213)
        if lit and d < 48 and R.random() < .55:
            fill = R.choice(["#ff9a3a", "#ffb04a", "#e8601a"])
        else:
            fill = R.choice(["#1a1816", "#24201c", "#2e2a26", "#141210"])
        coal += f'<polygon points="{pts}" fill="{fill}" stroke="#0a0908" stroke-width="1"/>'
    out += coal
    if not lit:
        out += '<g opacity=".55">' + "".join(f'<circle cx="{R.uniform(104,224):.0f}" cy="{R.uniform(158,268):.0f}" r="{R.uniform(3,8):.1f}" fill="#6a645c"/>' for _ in range(20)) + '</g>'
    # fole à direita, bico apontado para o braseiro
    out += ('<rect x="236" y="206" width="70" height="12" rx="4" fill="url(#iron)" stroke="#141210" stroke-width="2"/>'
            '<path d="M296,170 L386,150 L386,274 L296,254 Z" fill="url(#bel)" stroke="#1a0e08" stroke-width="3"/>'
            '<g stroke="#2a140a" stroke-width="2.5" fill="none" opacity=".8"><path d="M316,166 L316,258"/><path d="M336,162 L336,262"/><path d="M356,157 L356,267"/></g>'
            '<path d="M300,174 L380,158 L380,170 L300,184 Z" fill="#8a6236" stroke="#2a180a" stroke-width="2" filter="url(#wd)"/>'
            '<rect x="372" y="196" width="22" height="32" rx="6" fill="#6a4322" stroke="#2a180a" stroke-width="2.5"/>')
    # ferramentas sobre o bloco: tenaz e martelo
    out += ('<g stroke="#1c1d20" stroke-width="5" stroke-linecap="round"><line x1="44" y1="318" x2="120" y2="350"/><line x1="44" y1="330" x2="120" y2="352"/></g>'
            '<g stroke="#6a7076" stroke-width="2" stroke-linecap="round"><line x1="46" y1="318" x2="118" y2="348"/></g>'
            '<g transform="rotate(-30 246 332)"><rect x="196" y="326" width="74" height="10" rx="4" fill="#8a6236" stroke="#2a180a" stroke-width="2"/>'
            '<rect x="262" y="314" width="20" height="34" rx="3" fill="url(#iron)" stroke="#141210" stroke-width="2.5"/></g>'
            # balde d'água para a têmpera
            '<circle cx="62" cy="76" r="26" fill="#3a2414" stroke="#1a0e08" stroke-width="3"/>'
            '<circle cx="62" cy="76" r="20" fill="#2f5a7e"/><circle cx="62" cy="76" r="26" fill="none" stroke="#2e2e30" stroke-width="3"/>'
            '<ellipse cx="56" cy="70" rx="7" ry="3" fill="#8fc4e8" opacity=".5"/>')
    return out


R = random.Random(501)
f_lit = forge(R, True)
R2 = random.Random(502)
write("forja", "forja_acesa", '<circle cx="164" cy="213" r="190" fill="url(#bigglow)"/>' + f_lit + flames(R2, 164, 222, 34, 7, 1.15), FORGE_DEFS)
R = random.Random(501)
write("forja", "forja_apagada", forge(R, False), FORGE_DEFS)

# =====================================================================
# Bigorna num toco (1x1)
# =====================================================================
ANV_DEFS = ('<linearGradient id="steel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#a8aeb4"/><stop offset=".55" stop-color="#6a7076"/><stop offset="1" stop-color="#3e4246"/></linearGradient>'
            '<radialGradient id="stump" cx=".45" cy=".42"><stop offset="0" stop-color="#b8875a"/><stop offset="1" stop-color="#8a5e38"/></radialGradient>')
ANVIL = ('M38,84 L60,84 L66,74 L136,74 Q160,78 186,100 Q160,122 136,126 L66,126 L60,116 L38,116 Z')


def stump(split=False):
    rings = "".join(f'<circle cx="100" cy="100" r="{r}" fill="none" stroke="#6a4322" stroke-width="1.6" opacity=".45"/>' for r in (14, 28, 42, 56, 66))
    out = ('<circle cx="104" cy="110" r="84" fill="#000" opacity=".4" filter="url(#bl8)"/>'
           '<circle cx="100" cy="100" r="84" fill="#4a2c18" stroke="#1a0e08" stroke-width="3"/>'
           '<circle cx="100" cy="100" r="74" fill="url(#stump)" stroke="#3a2412" stroke-width="2"/>' + rings
           + '<g stroke="#2a180a" stroke-width="2.2" opacity=".55"><line x1="100" y1="26" x2="102" y2="52"/><line x1="160" y1="150" x2="140" y2="134"/></g>'
           + "".join(f'<line x1="{100+84*math.cos(a):.1f}" y1="{100+84*math.sin(a):.1f}" x2="{100+75*math.cos(a):.1f}" y2="{100+75*math.sin(a):.1f}" stroke="#1a0e08" stroke-width="2"/>'
                     for a in [i * math.pi / 9 for i in range(18)]))
    return out


def anvil(rot=0):
    return (f'<g transform="rotate({rot} 110 100)">'
            f'<path d="{ANVIL}" transform="translate(5 8)" fill="#000" opacity=".5" filter="url(#bl4)"/>'
            f'<path d="{ANVIL}" fill="url(#steel)" stroke="#16181a" stroke-width="3"/>'
            '<rect x="70" y="82" width="62" height="36" rx="3" fill="#8a9096" stroke="#3e4246" stroke-width="1.5"/>'
            '<line x1="72" y1="86" x2="130" y2="86" stroke="#d8dde2" stroke-width="2" opacity=".8"/>'
            '<rect x="44" y="94" width="10" height="10" fill="#16181a"/><circle cx="62" cy="100" r="3" fill="#16181a"/>'
            '<path d="M138,90 Q160,94 176,100" stroke="#c8ced4" stroke-width="2" fill="none" opacity=".7"/></g>')


write("bigorna", "bigorna_inteira", stump() + anvil(), ANV_DEFS)
R = random.Random(551)
split = ('<path d="M18,128 L60,118 L92,132 L130,112 L184,122" stroke="#1a0e08" stroke-width="6" fill="none" stroke-linejoin="round"/>'
         '<path d="M18,128 L60,118 L92,132 L130,112 L184,122" stroke="#3a2412" stroke-width="2" fill="none" transform="translate(0 4)"/>')
write("bigorna", "bigorna_rachada",
      stump() + split + anvil(-9)
      + '<g transform="rotate(-9 110 100)">' + crack(R, 96, 76, 4, 1.4, 3.5, "#0e0f10") + crack(R, 150, 82, 3, 2.2, 2.6, "#0e0f10")
      + crack(R, 96, 76, 4, 1.4, 1, "#c8ced4") + '</g>'
      + rubble(R, 120, 150, 30, 6, ["#6a7076", "#4a4e52", "#8a9096"], (3, 6))
      + splinters(R, 6, 110, 160, 30, "#8a5e38"), ANV_DEFS)

# =====================================================================
# Fardo de feno (1x1)
# =====================================================================
HAY_DEFS = ('<clipPath id="bale"><rect x="30" y="44" width="140" height="112" rx="12"/></clipPath>'
            '<linearGradient id="hay" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e4c66a"/><stop offset="1" stop-color="#b8923e"/></linearGradient>'
            + noise("ash", "0.09", 5, (.2, .19, .18), 1.2, -.35))


def bale():
    R = random.Random(601)
    return (shadow(30, 44, 140, 112, 12)
            + '<rect x="30" y="44" width="140" height="112" rx="12" fill="url(#hay)"/>'
            + f'<g clip-path="url(#bale)">{straw(R, 100, 100, 74, 60, 340, L=(10, 24), ang=0, width=2)}</g>'
            + '<rect x="30" y="44" width="140" height="112" rx="12" fill="none" stroke="#6a5020" stroke-width="3"/>'
            + '<g stroke="#5a3a1a" stroke-width="5" fill="none"><path d="M72,40 Q68,100 72,160"/><path d="M128,40 Q132,100 128,160"/></g>'
            + '<g stroke="#8a6a3a" stroke-width="1.6" fill="none"><path d="M72,40 Q68,100 72,160"/><path d="M128,40 Q132,100 128,160"/></g>'
            + straw(R, 100, 100, 82, 66, 22, L=(8, 16), width=1.6))


write("feno", "feno_inteiro", bale(), HAY_DEFS)
R = random.Random(611)
write("feno", "feno_espalhado",
      '<ellipse cx="100" cy="102" rx="90" ry="78" fill="#c9a44a" opacity=".35" filter="url(#bl8)"/>'
      + straw(R, 100, 100, 82, 74, 420, L=(8, 20), width=1.9)
      + '<g stroke="#5a3a1a" stroke-width="4" fill="none" stroke-linecap="round"><path d="M40,60 C70,90 50,130 90,150"/><path d="M130,40 C160,80 120,110 168,148"/></g>', HAY_DEFS)
R = random.Random(612)
write("feno", "feno_queimando", burning(R, bale(), [(100, 104, 40)], 9, 1.15, 60), HAY_DEFS)
R = random.Random(613)
write("feno", "feno_cinzas",
      '<ellipse cx="100" cy="104" rx="80" ry="64" fill="url(#soot)"/>'
      '<ellipse cx="100" cy="102" rx="62" ry="48" fill="#5a5550" filter="url(#ash)"/>'
      '<ellipse cx="96" cy="98" rx="40" ry="28" fill="#7a746c" filter="url(#ash)" opacity=".8"/>'
      + straw(R, 100, 102, 56, 42, 40, colors=("#1c1410", "#2a1e14", "#3a2a1a"), L=(6, 14))
      + embers(R, 100, 102, 50, 38, 16), HAY_DEFS)

# =====================================================================
# Cocho d'água (2x1)
# =====================================================================
TROUGH_DEFS = ('<linearGradient id="wat" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2c5e86"/><stop offset=".5" stop-color="#3a7aa8"/><stop offset="1" stop-color="#24506e"/></linearGradient>'
               '<linearGradient id="ice" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#eaf8ff"/><stop offset=".5" stop-color="#bfe4f6"/><stop offset="1" stop-color="#94c8e4"/></linearGradient>')


def trough(inner):
    R = random.Random(701)
    out = shadow(18, 42, 366, 118, 10)
    out += f'<rect x="18" y="42" width="364" height="116" rx="8" fill="#5a3a22" stroke="{INK}" stroke-width="3"/>'
    out += planks(20, 44, 360, 16, 1, "#7a5232", R=R) + planks(20, 140, 360, 16, 1, "#7a5232", R=R)
    out += planks(20, 60, 16, 80, 1, "#6a4528", False, R, "wv") + planks(364, 60, 16, 80, 1, "#6a4528", False, R, "wv")
    out += inner
    out += f'<rect x="36" y="60" width="328" height="80" fill="none" stroke="{INK}" stroke-width="2.5"/>'
    out += f'<rect x="18" y="42" width="364" height="116" rx="8" fill="none" stroke="{INK}" stroke-width="3"/>'
    out += "".join(f'<rect x="{x}" y="40" width="9" height="22" fill="#2e2e30"/><rect x="{x}" y="138" width="9" height="22" fill="#2e2e30"/>' for x in (110, 282))
    out += "".join(f'<circle cx="{x}" cy="{y}" r="2" fill="#c8ccd0"/>' for x in (114.5, 286.5) for y in (46, 56, 144, 154))
    return out


water = ('<rect x="36" y="60" width="328" height="80" fill="url(#wat)"/>'
         '<g stroke="#9fd0f0" stroke-width="2" fill="none" opacity=".5">'
         '<path d="M70,82 Q90,76 110,82"/><path d="M170,112 Q196,104 222,112"/><path d="M270,86 Q290,80 310,86"/><path d="M120,124 Q136,118 152,124"/></g>'
         '<ellipse cx="230" cy="78" rx="30" ry="5" fill="#d8f0ff" opacity=".25"/>'
         '<rect x="36" y="60" width="328" height="8" fill="#000" opacity=".2"/>')
write("cocho", "cocho_cheio", trough(water), TROUGH_DEFS)
R = random.Random(711)
ice = ('<rect x="36" y="60" width="328" height="80" fill="url(#ice)"/>'
       + crack(R, 80, 64, 5, 1.2, 2, "#ffffff") + crack(R, 200, 136, 6, -1.3, 2, "#ffffff") + crack(R, 300, 66, 5, 2.0, 2, "#ffffff")
       + crack(R, 150, 100, 5, 0, 1.4, "#7ab0d0") + crack(R, 260, 100, 4, 3.0, 1.4, "#7ab0d0")
       + '<g fill="#ffffff" opacity=".7">' + "".join(f'<circle cx="{R.uniform(40,360):.0f}" cy="{R.choice([R.uniform(62,70), R.uniform(130,138)]):.0f}" r="{R.uniform(1.5,3.5):.1f}"/>' for _ in range(40)) + '</g>')
write("cocho", "cocho_congelado",
      trough(ice) + '<g fill="#eaf8ff" opacity=".55">' + "".join(f'<circle cx="{R.uniform(22,378):.0f}" cy="{R.choice([R.uniform(42,58), R.uniform(142,158)]):.0f}" r="{R.uniform(1.5,3):.1f}"/>' for _ in range(30)) + '</g>', TROUGH_DEFS)
R = random.Random(712)
dry = ('<rect x="36" y="60" width="328" height="80" fill="#3a2414"/>'
       + planks(36, 60, 328, 80, 3, "#5a3a22", R=R)
       + '<rect x="36" y="60" width="328" height="80" fill="#1a3a50" opacity=".2"/>')
spill = '<path d="M150,150 C130,170 150,198 200,196 C250,200 300,190 296,168 C290,150 240,156 200,150 Z" fill="url(#puddle)"/>'
cocho_v = (spill + trough(dry)
           + '<polygon points="180,138 204,152 226,138 240,160 166,160" fill="#3a2414"/>'
           + crack(R, 204, 140, 3, 1.6, 4, "#120a06") + crack(R, 120, 62, 4, 1.3, 2.5, "#120a06") + crack(R, 300, 138, 4, -1.8, 2.5, "#120a06")
           + splinters(R, 7, 204, 168, 18, "#7a5232")
           + '<path d="M160,176 Q200,186 250,178" stroke="#9fd0f0" stroke-width="2" fill="none" opacity=".4"/>')
write("cocho", "cocho_vazio", cocho_v, TROUGH_DEFS)

# =====================================================================
# Tear (2x1)
# =====================================================================
LOOM_DEFS = ('<linearGradient id="roll" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6a4322"/><stop offset=".45" stop-color="#b08050"/><stop offset="1" stop-color="#5a3820"/></linearGradient>'
             '<pattern id="weave" width="24" height="12" patternUnits="userSpaceOnUse">'
             '<rect width="24" height="12" fill="#3a5a8a"/><rect y="0" width="24" height="3" fill="#2e4a74"/>'
             '<rect x="0" y="6" width="12" height="3" fill="#c8a040"/><rect x="12" y="6" width="12" height="3" fill="#8a2a2a"/></pattern>')
WARP = range(64, 340, 6)


def loom(cut=False):
    out = shadow(26, 26, 352, 150, 8)
    # laterais
    out += ''.join(f'<rect x="{x}" y="26" width="22" height="150" rx="5" fill="#6a4322" filter="url(#wv)" stroke="{INK}" stroke-width="3"/>' for x in (26, 352))
    # fios do urdume entre o rolo de trás e o pente
    if not cut:
        out += '<g stroke="#ece2c8" stroke-width="1.6">' + "".join(f'<line x1="{x}" y1="48" x2="{x}" y2="94"/>' for x in WARP) + '</g>'
    else:
        R = random.Random(801)
        out += '<g stroke="#ece2c8" stroke-width="1.6" fill="none">'
        for x in WARP:
            if 150 < x < 260:
                out += f'<path d="M{x},48 Q{x+R.uniform(-6,6):.0f},{56+R.uniform(0,6):.0f} {x+R.uniform(-8,8):.0f},{60+R.uniform(0,10):.0f}"/>'
                out += f'<path d="M{x},94 Q{x+R.uniform(-6,6):.0f},{86-R.uniform(0,6):.0f} {x+R.uniform(-8,8):.0f},{80-R.uniform(0,8):.0f}"/>'
            else:
                out += f'<line x1="{x}" y1="48" x2="{x}" y2="94"/>'
        out += '</g>'
    # tecido já feito
    out += '<rect x="60" y="102" width="282" height="48" fill="url(#weave)" filter="url(#cl)" stroke="#1c2a40" stroke-width="2"/>'
    # rolos de trás e da frente
    out += f'<rect x="30" y="30" width="342" height="20" rx="10" fill="url(#roll)" stroke="{INK}" stroke-width="2.5"/>'
    out += f'<rect x="30" y="148" width="342" height="22" rx="11" fill="url(#roll)" stroke="{INK}" stroke-width="2.5"/>'
    out += '<rect x="60" y="146" width="282" height="8" fill="#2e4a74" opacity=".9"/>'
    # pente (batente)
    out += f'<rect x="40" y="90" width="322" height="12" rx="4" fill="#8a6236" filter="url(#wd)" stroke="{INK}" stroke-width="2.5"/>'
    # lançadeira com o fio
    out += ('<path d="M168,126 Q200,114 232,126 Q200,138 168,126 Z" fill="#a87a4a" stroke="#2a180a" stroke-width="2"/>'
            '<rect x="190" y="122" width="20" height="8" rx="3" fill="#c8a040" stroke="#5a4418" stroke-width="1"/>')
    return out


write("tear", "tear_inteiro", loom(), LOOM_DEFS)
R = random.Random(811)
slash = ('<path d="M140,104 L176,124 L156,132 L250,148 L226,128 L264,104 Z" fill="#141210" opacity=".85"/>'
         '<g stroke="#c8a040" stroke-width="1.5" fill="none">' + "".join(f'<path d="M{x:.0f},{y:.0f} q{R.uniform(-8,8):.0f},{R.uniform(4,10):.0f} {R.uniform(-10,10):.0f},{R.uniform(8,16):.0f}"/>'
                                                                       for x, y in [(R.uniform(150, 250), R.uniform(104, 140)) for _ in range(14)]) + '</g>'
         '<g stroke="#ece2c8" stroke-width="1.2" fill="none">' + "".join(f'<path d="M{x:.0f},{y:.0f} q{R.uniform(-8,8):.0f},{R.uniform(4,10):.0f} {R.uniform(-10,10):.0f},{R.uniform(8,16):.0f}"/>'
                                                                         for x, y in [(R.uniform(150, 250), R.uniform(104, 140)) for _ in range(10)]) + '</g>')
write("tear", "tear_cortado", loom(True) + slash, LOOM_DEFS)
R = random.Random(812)
tangle = '<g stroke="#ece2c8" stroke-width="1.4" fill="none" opacity=".9">' + "".join(
    f'<path d="M{R.uniform(60,340):.0f},{R.uniform(40,160):.0f} C{R.uniform(40,360):.0f},{R.uniform(30,170):.0f} {R.uniform(40,360):.0f},{R.uniform(30,170):.0f} {R.uniform(60,340):.0f},{R.uniform(40,160):.0f}"/>' for _ in range(26)) + '</g>'
broken_loom = (shadow(26, 26, 352, 150, 8)
               + '<g transform="rotate(-8 37 100)"><rect x="26" y="26" width="22" height="150" rx="5" fill="#6a4322" filter="url(#wv)" stroke="#2a180a" stroke-width="3"/></g>'
               + '<g transform="rotate(14 363 100)"><rect x="352" y="40" width="22" height="130" rx="5" fill="#6a4322" filter="url(#wv)" stroke="#2a180a" stroke-width="3"/></g>'
               + '<g transform="rotate(5 200 140)"><path d="M70,104 L330,108 L320,150 Q260,170 200,146 Q140,170 76,150 Z" fill="url(#weave)" filter="url(#cl)" stroke="#1c2a40" stroke-width="2"/></g>'
               + '<g transform="rotate(-6 110 40)"><rect x="30" y="30" width="170" height="20" rx="10" fill="url(#roll)" stroke="#2a180a" stroke-width="2.5"/></g>'
               + '<g transform="rotate(10 290 40)"><rect x="214" y="34" width="156" height="20" rx="10" fill="url(#roll)" stroke="#2a180a" stroke-width="2.5"/></g>'
               + '<rect x="30" y="152" width="342" height="22" rx="11" fill="url(#roll)" stroke="#2a180a" stroke-width="2.5"/>'
               + '<g transform="rotate(-22 200 96)"><rect x="80" y="90" width="240" height="12" rx="4" fill="#8a6236" filter="url(#wd)" stroke="#2a180a" stroke-width="2.5"/></g>'
               + tangle + splinters(R, 12, 200, 70, 50, "#6a4322") + splinters(R, 5, 200, 70, 50, INK))
write("tear", "tear_quebrado", broken_loom, LOOM_DEFS)
R = random.Random(813)
write("tear", "tear_queimando", burning(R, loom(), [(120, 116, 32), (280, 112, 32)], 6), LOOM_DEFS)
R = random.Random(814)
write("tear", "tear_queimado",
      soot(R, 120, 100, 80, 6) + soot(R, 280, 100, 80, 6)
      + '<g filter="url(#ch)"><rect x="26" y="40" width="22" height="120" rx="5" fill="#6a4322" transform="rotate(-6 37 100)"/>'
      '<rect x="352" y="50" width="22" height="110" rx="5" fill="#6a4322" transform="rotate(9 363 100)"/>'
      '<rect x="30" y="150" width="300" height="20" rx="10" fill="#6a4322" transform="rotate(2 180 160)"/></g>'
      + charred_bits(R, 200, 100, 50, 9, (26, 56), 11)
      + '<ellipse cx="200" cy="120" rx="110" ry="24" fill="#4a443e" opacity=".6" filter="url(#bl4)"/>'
      + embers(R, 200, 100, 150, 50, 18), LOOM_DEFS)

# =====================================================================
# Casulário (1x1): caixa rasa com folhas de amoreira e casulos
# =====================================================================
SILK_DEFS = ('<radialGradient id="coc" cx=".4" cy=".35"><stop offset="0" stop-color="#fffdf4"/><stop offset="1" stop-color="#d8ccaa"/></radialGradient>'
             '<radialGradient id="cocy" cx=".4" cy=".35"><stop offset="0" stop-color="#fff4c8"/><stop offset="1" stop-color="#d8b85a"/></radialGradient>')


def leaf(x, y, L, a, col):
    w = L * .62
    return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f})">'
            f'<path d="M0,{-L:.0f} C{w:.0f},{-L*.7:.0f} {w*.9:.0f},{L*.4:.0f} 0,{L:.0f} C{-w*.9:.0f},{L*.4:.0f} {-w:.0f},{-L*.7:.0f} 0,{-L:.0f} Z" fill="{col}" stroke="#1e3a14" stroke-width="1.5"/>'
            f'<line x1="0" y1="{-L*.85:.0f}" x2="0" y2="{L+4:.0f}" stroke="#a8c878" stroke-width="1.4"/>'
            f'<g stroke="#a8c878" stroke-width="1" opacity=".7"><line x1="0" y1="{-L*.3:.0f}" x2="{w*.5:.0f}" y2="{-L*.55:.0f}"/><line x1="0" y1="{-L*.3:.0f}" x2="{-w*.5:.0f}" y2="{-L*.55:.0f}"/>'
            f'<line x1="0" y1="{L*.2:.0f}" x2="{w*.55:.0f}" y2="{-L*.05:.0f}"/><line x1="0" y1="{L*.2:.0f}" x2="{-w*.55:.0f}" y2="{-L*.05:.0f}"/></g></g>')


def tray(inner, rot=0):
    return (shadow(24, 32, 152, 136, 8)
            + f'<g transform="rotate({rot} 100 100)">'
            + '<rect x="24" y="32" width="152" height="136" rx="6" fill="#8a6236" stroke="#2a180a" stroke-width="3" filter="url(#wd)"/>'
            + '<rect x="34" y="42" width="132" height="116" rx="3" fill="#4a3a24" stroke="#2a180a" stroke-width="2"/>'
            + inner
            + '<g fill="#2e2e30">' + "".join(f'<circle cx="{x}" cy="{y}" r="2"/>' for x in (29, 171) for y in (37, 163)) + '</g></g>')


def silk_inner(R):
    out = ""
    for _ in range(13):
        out += leaf(R.uniform(46, 154), R.uniform(54, 146), R.uniform(16, 24), R.uniform(0, 360), R.choice(["#4a7a32", "#5f9440", "#3e6a2a", "#6aa048"]))
    for _ in range(10):
        x, y, a = R.uniform(50, 150), R.uniform(58, 142), R.uniform(0, 180)
        g = R.choice(["coc", "coc", "cocy"])
        out += (f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f})"><ellipse rx="10" ry="6.5" fill="url(#{g})" stroke="#9a8a62" stroke-width="1.2"/>'
                '<path d="M-6,-2 Q0,2 6,-2" stroke="#c8b88a" stroke-width=".8" fill="none"/></g>')
    for _ in range(4):
        x, y, a = R.uniform(54, 146), R.uniform(60, 140), R.uniform(0, 360)
        out += (f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f})">'
                + "".join(f'<circle cx="{i*3.6:.1f}" cy="{math.sin(i*.9)*1.6:.1f}" r="{2.8 - abs(i-2)*.3:.1f}" fill="#ece4d0" stroke="#8a8068" stroke-width=".6"/>' for i in range(6))
                + '<circle cx="-1" cy="0" r="1.2" fill="#3a3020"/></g>')
    return out


R = random.Random(901)
write("casulario", "casulario_vivo", tray(silk_inner(R)), SILK_DEFS)
R = random.Random(911)
crushed = ""
for _ in range(10):
    crushed += leaf(R.uniform(40, 160), R.uniform(46, 156), R.uniform(12, 20), R.uniform(0, 360), R.choice(["#3a5a26", "#4a6a2e", "#2e4a1e"]))
for _ in range(9):
    x, y, a = R.uniform(48, 152), R.uniform(54, 146), R.uniform(0, 180)
    crushed += (f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{R.uniform(10,15):.0f}" ry="{R.uniform(5,8):.0f}" fill="#c8b860" opacity=".55" transform="rotate({a:.0f} {x:.0f} {y:.0f})"/>'
                f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f})"><path d="M-11,0 L-6,-3 L0,-1 L5,-4 L11,0 L5,3 L0,1 L-6,4 Z" fill="#e6dcc0" stroke="#8a7a52" stroke-width="1"/></g>')
crushed += '<g fill="#3a2a10" opacity=".5">' + "".join(f'<circle cx="{R.uniform(44,156):.0f}" cy="{R.uniform(50,150):.0f}" r="{R.uniform(1.5,4):.1f}"/>' for _ in range(14)) + '</g>'
write("casulario", "casulario_esmagado",
      tray(crushed + crack(R, 34, 70, 5, .3, 3, "#1a0e06") + crack(R, 166, 140, 4, 3.4, 3, "#1a0e06"), -6)
      + '<g transform="rotate(30 170 60)"><rect x="140" y="52" width="60" height="12" rx="3" fill="#8a6236" stroke="#2a180a" stroke-width="2"/></g>'
      + splinters(R, 8, 100, 110, 50, "#8a6236"), SILK_DEFS)


# =====================================================================
# Definições (fragmento do assets.json)
# =====================================================================
FIRE_LIGHT = {"bright": 10, "dim": 25, "color": "#ff7b2e", "alpha": 0.5, "attenuation": 0.6,
              "animation": {"type": "torch", "speed": 4, "intensity": 4}}
EMBER_LIGHT = {"bright": 0, "dim": 10, "color": "#ff5a1a", "alpha": 0.35, "animation": {"type": "torch", "speed": 1, "intensity": 2}}
FIRE_SOUND = {"src": "tocha/fogo.ogg", "radius": 25, "volume": 0.6}
SFX = "audio/madeira_quebrando.ogg"
WOOD_IMM = ["poison", "psychic"]


def st(asset, sid, name, **kw):
    return {"id": sid, "name": name, "src": f"{asset}/{asset}_{sid}.png", **kw}


def fire_state(asset, dot=2):
    return st(asset, "queimando", "Pegando fogo", burning=True, sticky=True, dot={"damage": dot, "type": "fire"},
              light=FIRE_LIGHT, sound=FIRE_SOUND)


def burnt_state(asset, sid, name):
    return st(asset, sid, name, broken=True, light=EMBER_LIGHT)


def wood_reactions(intact, apagado):
    return [{"types": ["fire", "lightning"], "from": intact, "to": "queimando", "say": "começa a pegar fogo!"},
            {"types": ["cold"], "from": ["queimando"], "to": apagado, "say": "tem o fogo apagado pelo gelo."}]


def wood_zero(queimado, quebrado, say_q="se despedaça!"):
    return [{"state": "queimando", "to": queimado, "say": "vira cinzas!"},
            {"types": ["fire", "lightning"], "to": queimado, "say": "vira cinzas!"},
            {"to": quebrado, "say": say_q}]


def furniture(asset, name, hp, fem, move=True, extra_first=None):
    """Cadeira, poltrona, banco: inteira/quebrada/queimando/queimada."""
    a = "a" if fem else "o"
    first = f"inteir{a}"
    d = {"name": name, "tipo": "movel", "interacao": "jogador", "size": None,
         "actor": {"ac": 10, "hp": hp, "immunities": WOOD_IMM, "resistances": []},
         "player": {"move": True}, "tickSeconds": 6,
         "states": [st(asset, first, f"Inteir{a}"), st(asset, f"quebrad{a}", f"Quebrad{a}", broken=True, sfx=SFX),
                    fire_state(asset), burnt_state(asset, f"queimad{a}", f"Queimad{a}")],
         "reactions": wood_reactions([first], first),
         "onZero": wood_zero(f"queimad{a}", f"quebrad{a}")}
    return d


defs = {}

defs["amplificador"] = {
    "name": "Amplificador geométrico", "tipo": "imovel", "interacao": "mestre", "size": {"w": 1, "h": 1},
    "actor": {"ac": 15, "hp": 10, "immunities": ["poison", "psychic"], "resistances": []},
    "states": [
        st("amplificador", "brilhando", "Brilhando",
           light={"bright": 10, "dim": 25, "color": "#9fd8ff", "alpha": 0.35, "animation": {"type": "energy", "speed": 3, "intensity": 3}}),
        st("amplificador", "rachado", "Rachado",
           light={"bright": 6, "dim": 18, "color": "#9fd8ff", "alpha": 0.3, "animation": {"type": "flame", "speed": 6, "intensity": 6}}),
        st("amplificador", "estilhacado", "Estilhaçado", broken=True,
           colapso={"dc": 15, "damage": "2d6", "type": "bludgeoning"}),
    ],
    "reactions": [{"types": ["bludgeoning", "force", "thunder"], "from": ["brilhando"], "to": "rachado",
                   "say": "racha, e a luz começa a piscar!"}],
    "onZero": [{"to": "estilhacado", "say": "se estilhaça! O espaço extradimensional desaba!"}],
}

defs["fogueira"] = {
    "name": "Fogueira do Hearth", "tipo": "imovel", "interacao": "mestre", "size": {"w": 2, "h": 2},
    "fogoPermitido": True, "actor": {},
    "states": [
        st("fogueira", "acesa", "Acesa", chama=True,
           light={"bright": 15, "dim": 35, "color": "#ff8a3d", "alpha": 0.5, "attenuation": 0.5,
                  "animation": {"type": "torch", "speed": 3, "intensity": 3}},
           sound={"src": "tocha/fogo.ogg", "radius": 25, "volume": 0.6}),
        st("fogueira", "brasas", "Brasas",
           light={"bright": 0, "dim": 12, "color": "#ff5a1a", "alpha": 0.4, "animation": {"type": "torch", "speed": 1, "intensity": 2}}),
    ],
    "reactions": [{"types": ["cold"], "from": ["acesa"], "to": "brasas", "say": "vira brasas por um instante."},
                  {"types": ["fire", "lightning"], "from": ["brasas"], "to": "acesa", "say": "volta a arder."}],
}

defs["balcao"] = {
    "name": "Balcão do bar", "tipo": "imovel", "interacao": "mestre", "size": {"w": 1, "h": 1},
    "actor": {"ac": 13, "hp": 15, "immunities": WOOD_IMM, "resistances": ["piercing"]},
    "tickSeconds": 6,
    "states": [st("balcao", "inteiro", "Inteiro"), st("balcao", "chamuscado", "Chamuscado"),
               st("balcao", "quebrado", "Quebrado", broken=True, sfx=SFX),
               fire_state("balcao"), burnt_state("balcao", "queimado", "Queimado")],
    "reactions": wood_reactions(["inteiro", "chamuscado"], "chamuscado"),
    "onZero": wood_zero("queimado", "quebrado", "se arrebenta, espalhando canecas e cacos!"),
}

defs["cadeira"] = furniture("cadeira", "Cadeira", 3, True)
defs["cadeira"]["size"] = {"w": 1, "h": 1}
defs["poltrona"] = furniture("poltrona", "Poltrona de couro", 5, True)
defs["poltrona"]["size"] = {"w": 1, "h": 1}
defs["banco"] = furniture("banco", "Banco comprido", 5, False)
defs["banco"]["size"] = {"w": 2, "h": 1}

defs["cama"] = {
    "name": "Cama", "tipo": "movel", "interacao": "mestre", "size": {"w": 1, "h": 2},
    "actor": {"ac": 10, "hp": 8, "immunities": WOOD_IMM, "resistances": []},
    "tickSeconds": 6,
    "states": [st("cama", "arrumada", "Arrumada"), st("cama", "desarrumada", "Desarrumada"),
               st("cama", "quebrada", "Quebrada", broken=True, sfx=SFX),
               fire_state("cama"), burnt_state("cama", "queimada", "Queimada")],
    "reactions": wood_reactions(["arrumada", "desarrumada"], "desarrumada"),
    "onZero": wood_zero("queimada", "quebrada", "desaba com um estalo!"),
}

defs["forja"] = {
    "name": "Forja", "tipo": "imovel", "interacao": "mestre", "size": {"w": 2, "h": 2},
    "fogoPermitido": True,
    "actor": {"ac": 17, "hp": 40, "immunities": ["fire", "poison", "psychic"], "resistances": []},
    "states": [
        st("forja", "acesa", "Acesa", chama=True,
           light={"bright": 15, "dim": 30, "color": "#ff7a2a", "alpha": 0.55, "attenuation": 0.5,
                  "animation": {"type": "torch", "speed": 3, "intensity": 4}},
           sound={"src": "tocha/fogo.ogg", "radius": 25, "volume": 0.6}),
        st("forja", "apagada", "Apagada", light={"bright": 0, "dim": 0}),
    ],
    "reactions": [{"types": ["cold"], "from": ["acesa"], "to": "apagada", "say": "tem o braseiro apagado pelo gelo."},
                  {"types": ["fire", "lightning"], "from": ["apagada"], "to": "acesa", "say": "volta a arder."}],
}

defs["bigorna"] = {
    "name": "Bigorna", "tipo": "movel", "interacao": "jogador", "size": {"w": 1, "h": 1},
    "actor": {"ac": 19, "hp": 50, "immunities": ["fire", "poison", "psychic"],
              "resistances": ["bludgeoning", "piercing", "slashing"]},
    "player": {"move": True},
    "states": [st("bigorna", "inteira", "Inteira"), st("bigorna", "rachada", "Rachada", broken=True)],
    "onZero": [{"to": "rachada", "say": "racha ao meio com um estalo metálico!"}],
}

defs["feno"] = {
    "name": "Fardo de feno", "tipo": "movel", "interacao": "jogador", "size": {"w": 1, "h": 1},
    "actor": {"ac": 8, "hp": 4, "immunities": WOOD_IMM, "resistances": []},
    "player": {"move": True}, "tickSeconds": 6,
    "states": [st("feno", "inteiro", "Inteiro"), st("feno", "espalhado", "Espalhado", broken=True),
               fire_state("feno", 3), burnt_state("feno", "cinzas", "Cinzas")],
    "reactions": wood_reactions(["inteiro"], "inteiro"),
    "onZero": [{"state": "queimando", "to": "cinzas", "say": "vira cinzas num instante!"},
               {"types": ["fire", "lightning"], "to": "cinzas", "say": "vira cinzas num instante!"},
               {"to": "espalhado", "say": "se desfaz e espalha palha para todo lado!"}],
}

defs["cocho"] = {
    "name": "Cocho d'água", "tipo": "imovel", "interacao": "mestre", "size": {"w": 2, "h": 1},
    "actor": {"ac": 12, "hp": 10, "immunities": WOOD_IMM, "resistances": []},
    "states": [st("cocho", "cheio", "Cheio", wet=True),
               st("cocho", "congelado", "Congelado", gelo=True,
                  light={"bright": 0, "dim": 8, "color": "#9fdcff", "alpha": 0.3}),
               st("cocho", "vazio", "Vazio", broken=True, sfx=SFX)],
    "reactions": [{"types": ["cold"], "from": ["cheio"], "to": "congelado", "say": "congela!"},
                  {"types": ["fire"], "from": ["congelado"], "to": "cheio", "say": "derrete."}],
    "onZero": [{"to": "vazio", "say": "racha e derrama a água pelo chão!"}],
}

defs["tear"] = {
    "name": "Tear", "tipo": "imovel", "interacao": "mestre", "size": {"w": 2, "h": 1},
    "actor": {"ac": 10, "hp": 6, "immunities": WOOD_IMM, "resistances": []},
    "tickSeconds": 6,
    "states": [st("tear", "inteiro", "Inteiro"), st("tear", "cortado", "Cortado"),
               st("tear", "quebrado", "Quebrado", broken=True, sfx=SFX),
               fire_state("tear"), burnt_state("tear", "queimado", "Queimado")],
    "reactions": wood_reactions(["inteiro", "cortado"], "inteiro")
    + [{"types": ["slashing"], "from": ["inteiro"], "to": "cortado", "say": "tem os fios e o tecido cortados!"}],
    "onZero": wood_zero("queimado", "quebrado", "desmonta num emaranhado de fios!"),
}

defs["casulario"] = {
    "name": "Casulário", "tipo": "movel", "interacao": "jogador", "size": {"w": 1, "h": 1},
    "actor": {"ac": 8, "hp": 2, "immunities": ["psychic"], "resistances": []},
    "player": {"move": True},
    "states": [st("casulario", "vivo", "Vivo"), st("casulario", "esmagado", "Esmagado", broken=True)],
    "onZero": [{"to": "esmagado", "say": "é esmagado, com casulos e tudo."}],
}

frag = ROOT / "tools" / "fragmentos"
frag.mkdir(parents=True, exist_ok=True)
(frag / "oficios.json").write_text(json.dumps(defs, ensure_ascii=False, indent=2) + "\n")

# confere que toda imagem citada existe como SVG
for k, v in defs.items():
    for s in v["states"]:
        p = A / s["src"].replace(".png", ".svg")
        assert p.exists(), p
print("ok", len(defs), "assets")
