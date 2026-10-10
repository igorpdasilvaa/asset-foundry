"""Gera os SVGs das estruturas quebráveis (parede, porta, pilar, barril, caixa) em assets/<nome>/.
1 quadrado = 200 px. Uso:
python3 tools/gen_estruturas.py && NODE_PATH=$(npm root -g) node tools/render.js assets/{parede,porta,pilar,barril,caixa}/*.svg"""
import math, random, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gen_pecas_mapa import noise, shade

A = pathlib.Path(__file__).resolve().parent.parent / "assets"
S = 200

COMMON = (
    '<filter id="bl4" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter>'
    '<filter id="bl8" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="8"/></filter>'
    '<radialGradient id="glow"><stop offset="0" stop-color="#ffb347" stop-opacity=".75"/><stop offset=".6" stop-color="#ff5a1a" stop-opacity=".3"/><stop offset="1" stop-color="#ff5a1a" stop-opacity="0"/></radialGradient>'
    '<radialGradient id="soot"><stop offset="0" stop-color="#0b0908" stop-opacity=".9"/><stop offset=".7" stop-color="#1a1410" stop-opacity=".55"/><stop offset="1" stop-color="#1a1410" stop-opacity="0"/></radialGradient>'
)


def write(folder, name, body, defs=""):
    d = A / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{S//2}" height="{S//2}" viewBox="0 0 {S} {S}">'
        f'<defs>{COMMON}{defs}</defs>{body}</svg>')


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


def soot(R, cx, cy, r):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#soot)"/>' + "".join(
        f'<circle cx="{cx+R.uniform(-r,r)*.7:.0f}" cy="{cy+R.uniform(-r,r)*.7:.0f}" r="{R.uniform(1.5,3.5):.1f}" fill="#ff6a1a" opacity=".8"/>' for _ in range(6))


def rubble(R, cx, cy, spread, n, colors, size=(8, 22)):
    out = ""
    for _ in range(n):
        x, y = cx + R.gauss(0, spread), cy + R.gauss(0, spread)
        r = R.uniform(*size)
        k = R.randint(4, 6)
        a0 = R.uniform(0, math.pi)
        pts = " ".join(f"{x+r*R.uniform(.6,1)*math.cos(a0+i*2*math.pi/k):.1f},{y+r*R.uniform(.6,1)*math.sin(a0+i*2*math.pi/k):.1f}" for i in range(k))
        out += f'<polygon points="{pts}" fill="{R.choice(colors)}" stroke="#1c1b19" stroke-width="1.5"/>'
    return out


def crack(R, x, y, steps, ang, width=2.2):
    d = f"M{x:.0f},{y:.0f}"
    for _ in range(steps):
        ang += R.uniform(-.6, .6)
        L = R.uniform(10, 22)
        x, y = x + L * math.cos(ang), y + L * math.sin(ang)
        d += f" L{x:.0f},{y:.0f}"
    return f'<path d="{d}" stroke="#141210" stroke-width="{width}" fill="none" stroke-linejoin="round"/>'


# ---------------- Parede de pedra (um bloco de 1 quadrado) ----------------
# Fiadas que se repetem a cada 200 px: blocos vizinhos se encaixam sem emenda.
def bricks(R):
    body = ""
    for r in range(4):
        y = r * 50
        xs = [0, 100, 200] if r % 2 == 0 else [0, 50, 150, 200]
        for a, b in zip(xs, xs[1:]):
            body += f'<rect x="{a+2}" y="{y+2}" width="{b-a-4}" height="46" rx="4" fill="{shade("#5c5852", R.uniform(.82, 1.15))}"/>'
    return f'<rect width="200" height="200" fill="#24221f"/><g filter="url(#wl)">{body}</g>'

WALL_DEFS = noise("wl", "0.06", 9, (.14, .13, .12), 1.3, -.4)
R = random.Random(1)
write("parede", "parede_inteira", bricks(R), WALL_DEFS)
R = random.Random(1)
cr = bricks(R)
R = random.Random(5)
cr += crack(R, 40, 10, 9, 1.2) + crack(R, 150, 190, 8, -1.9) + crack(R, 100, 100, 5, .3, 1.6)
cr += rubble(R, 100, 100, 45, 5, ["#3a3632", "#2e2b28"], (3, 7))
write("parede", "parede_rachada", cr, WALL_DEFS)
R = random.Random(7)
ru = ('<rect width="200" height="200" fill="#3d3934" filter="url(#fd)"/>'
      + rubble(R, 100, 100, 45, 14, ["#5c5852", "#6b675f", "#4d4943", "#57534c"], (10, 24))
      + rubble(R, 100, 100, 55, 22, ["#6b675f", "#7a756c", "#4d4943"], (3, 8)))
write("parede", "parede_destruida", ru, noise("fd", "0.08", 3, (.12, .11, .1), 1.3, -.4))

# ---------------- Porta dupla de madeira (horizontal; o mapa gira para paredes verticais) ----------------
JAMBS = ('<rect x="0" y="0" width="200" height="200" fill="#6b675f"/>'
         '<g stroke="#3d3a35" stroke-width="2"><line x1="0" y1="45" x2="200" y2="45"/><line x1="0" y1="155" x2="200" y2="155"/><line x1="100" y1="0" x2="100" y2="45"/><line x1="100" y1="155" x2="100" y2="200"/></g>'
         '<rect x="0" y="0" width="30" height="200" fill="#5c5852" stroke="#24221f" stroke-width="4"/>'
         '<rect x="170" y="0" width="30" height="200" fill="#5c5852" stroke="#24221f" stroke-width="4"/>')
DOOR_DEFS = noise("dg", "0.006 0.25", 5, (.22, .12, .05))

def leaf(x, y, w, h, vertical=False, color="#74482a"):
    """Folha da porta vista de cima: tábuas no sentido do comprimento, ferragens nas pontas."""
    lines = ""
    if vertical:
        lines = f'<line x1="{x+w/2}" y1="{y}" x2="{x+w/2}" y2="{y+h}"/>'
        bands = f'<rect x="{x-1}" y="{y+6}" width="{w+2}" height="5"/><rect x="{x-1}" y="{y+h-11}" width="{w+2}" height="5"/>'
    else:
        lines = f'<line x1="{x}" y1="{y+h/2}" x2="{x+w}" y2="{y+h/2}"/>'
        bands = f'<rect x="{x+6}" y="{y-1}" width="5" height="{h+2}"/><rect x="{x+w-11}" y="{y-1}" width="5" height="{h+2}"/>'
    return (f'<g filter="url(#dg)"><rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}"/></g>'
            f'<g stroke="#2a180a" stroke-width="1.5">{lines}</g>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="#2a180a" stroke-width="3"/>'
            f'<g fill="#2e2e30">{bands}</g>')

closed = JAMBS + leaf(30, 88, 70, 24) + leaf(100, 88, 70, 24) + '<circle cx="94" cy="100" r="3.5" fill="#b08a3c"/><circle cx="106" cy="100" r="3.5" fill="#b08a3c"/>'
write("porta", "porta_fechada", closed, DOOR_DEFS)
opened = (JAMBS + '<path d="M30,100 A70,70 0 0 1 100,170" stroke="#3d3a35" stroke-width="1.5" stroke-dasharray="4 4" fill="none" opacity=".6"/>'
          '<path d="M170,100 A70,70 0 0 0 100,170" stroke="#3d3a35" stroke-width="1.5" stroke-dasharray="4 4" fill="none" opacity=".6"/>'
          + leaf(30, 100, 24, 70, True) + leaf(146, 100, 24, 70, True))
write("porta", "porta_aberta", opened, DOOR_DEFS)

R = random.Random(11)
def splinters(R, n, cx, cy, spread, color="#74482a"):
    out = ""
    for _ in range(n):
        x, y = cx + R.gauss(0, spread), cy + R.gauss(0, spread * .7)
        L, a = R.uniform(10, 34), R.uniform(0, math.pi)
        out += f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{x+L*math.cos(a):.0f}" y2="{y+L*math.sin(a):.0f}" stroke="{color}" stroke-width="{R.uniform(3,6):.1f}" stroke-linecap="round"/>'
    return out
broken = (JAMBS + '<g transform="rotate(-25 30 100)">' + leaf(30, 88, 44, 24) + '</g>'
          '<polygon points="30,88 74,88 66,100 74,112 30,112" fill="none"/>'
          + '<g transform="rotate(35 170 100)">' + leaf(132, 88, 38, 24) + '</g>'
          + splinters(R, 16, 100, 110, 28) + splinters(R, 6, 100, 110, 30, "#2a180a"))
write("porta", "porta_quebrada", broken, DOOR_DEFS)
R = random.Random(12)
burning = (closed.replace('#74482a', '#4a2c18') + soot(R, 100, 100, 50) + flames(R, 100, 104, 40, 7))
write("porta", "porta_queimando", burning, DOOR_DEFS)
R = random.Random(13)
burnt = (JAMBS + soot(R, 100, 100, 60) + splinters(R, 18, 100, 105, 26, "#1c120c") + splinters(R, 8, 100, 105, 26, "#3a2414")
         + '<g opacity=".7">' + "".join(f'<circle cx="{R.uniform(50,150):.0f}" cy="{R.uniform(70,140):.0f}" r="{R.uniform(1,2.5):.1f}" fill="#ff7b2e"/>' for _ in range(10)) + '</g>')
write("porta", "porta_queimada", burnt, DOOR_DEFS)

# ---------------- Pilar de pedra (transparente, por cima do piso) ----------------
PILLAR_DEFS = ('<radialGradient id="pg" cx=".4" cy=".38"><stop offset="0" stop-color="#9a958b"/><stop offset="1" stop-color="#5a564f"/></radialGradient>'
               + noise("pn", "0.07", 7, (.2, .19, .17), 1.2, -.4))
pillar = ('<circle cx="104" cy="108" r="76" fill="#000" opacity=".45" filter="url(#bl8)"/>'
          '<circle cx="100" cy="100" r="74" fill="#4a4741"/>'
          '<circle cx="100" cy="100" r="66" fill="url(#pg)" filter="url(#pn)"/>'
          '<circle cx="100" cy="100" r="66" fill="none" stroke="#2a2825" stroke-width="3"/>'
          '<circle cx="100" cy="100" r="46" fill="none" stroke="#2a2825" stroke-width="2" opacity=".6"/>'
          '<circle cx="100" cy="100" r="24" fill="none" stroke="#2a2825" stroke-width="1.5" opacity=".5"/>'
          '<circle cx="100" cy="100" r="74" fill="none" stroke="#1c1b19" stroke-width="3"/>')
write("pilar", "pilar_inteiro", pillar, PILLAR_DEFS)
R = random.Random(21)
write("pilar", "pilar_rachado", pillar + crack(R, 60, 50, 6, .9) + crack(R, 150, 120, 5, 2.6) + crack(R, 100, 100, 4, -1.2, 1.5)
      + rubble(R, 100, 100, 70, 6, ["#6b675f", "#5a564f"], (3, 6)), PILLAR_DEFS)
R = random.Random(22)
write("pilar", "pilar_destruido",
      '<circle cx="100" cy="100" r="58" fill="#4a4741" stroke="#1c1b19" stroke-width="3"/>'
      '<circle cx="100" cy="100" r="50" fill="url(#pg)" filter="url(#pn)" opacity=".8"/>'
      + crack(R, 100, 100, 5, 0) + crack(R, 100, 100, 4, 2.2)
      + rubble(R, 100, 100, 36, 14, ["#7a756c", "#6b675f", "#5a564f", "#8a857b"], (9, 20))
      + rubble(R, 100, 100, 50, 18, ["#6b675f", "#8a857b"], (3, 7)), PILLAR_DEFS)

# ---------------- Barril (transparente) ----------------
BARREL_DEFS = ('<radialGradient id="lid" cx=".45" cy=".42"><stop offset="0" stop-color="#9a6a3c"/><stop offset="1" stop-color="#6a4322"/></radialGradient>'
               '<radialGradient id="ale"><stop offset="0" stop-color="#c98a2a" stop-opacity=".85"/><stop offset=".7" stop-color="#a86a1a" stop-opacity=".6"/><stop offset="1" stop-color="#a86a1a" stop-opacity="0"/></radialGradient>'
               + noise("bg", "0.01 0.2", 4, (.22, .12, .05)))

def barrel(color_shift=1.0):
    planks = "".join(f'<line x1="{100+70*math.cos(a):.1f}" y1="{100+70*math.sin(a):.1f}" x2="{100+56*math.cos(a):.1f}" y2="{100+56*math.sin(a):.1f}" stroke="#2a180a" stroke-width="2"/>'
                     for a in [i * math.pi / 8 for i in range(16)])
    lid = "".join(f'<line x1="{x}" y1="{100-math.sqrt(max(0,52**2-(x-100)**2)):.1f}" x2="{x}" y2="{100+math.sqrt(max(0,52**2-(x-100)**2)):.1f}" stroke="#3b2412" stroke-width="2"/>' for x in (74, 100, 126))
    return (f'<circle cx="104" cy="108" r="74" fill="#000" opacity=".4" filter="url(#bl8)"/>'
            f'<circle cx="100" cy="100" r="72" fill="{shade("#7a4d28", color_shift)}" filter="url(#bg)"/>{planks}'
            f'<circle cx="100" cy="100" r="72" fill="none" stroke="#2e2e30" stroke-width="6"/>'
            f'<circle cx="100" cy="100" r="58" fill="none" stroke="#2e2e30" stroke-width="5"/>'
            f'<circle cx="100" cy="100" r="52" fill="url(#lid)"/>{lid}'
            f'<circle cx="100" cy="100" r="52" fill="none" stroke="#2a180a" stroke-width="3"/>'
            f'<circle cx="122" cy="112" r="6" fill="#4a2c18" stroke="#2a180a" stroke-width="2"/>')
write("barril", "barril_inteiro", barrel(), BARREL_DEFS)
R = random.Random(31)
staves = "".join(
    f'<g transform="translate({100+R.gauss(0,34):.0f} {100+R.gauss(0,34):.0f}) rotate({R.uniform(0,180):.0f})">'
    f'<rect x="-22" y="-7" width="44" height="14" rx="5" fill="{shade("#7a4d28", R.uniform(.8,1.1))}" stroke="#2a180a" stroke-width="2"/></g>' for _ in range(10))
hoop = '<ellipse cx="96" cy="104" rx="60" ry="48" fill="none" stroke="#2e2e30" stroke-width="5" transform="rotate(-20 96 104)"/>'
write("barril", "barril_quebrado", '<ellipse cx="100" cy="104" rx="90" ry="76" fill="url(#ale)"/>' + hoop + staves, BARREL_DEFS)
R = random.Random(32)
write("barril", "barril_queimando", barrel(.6) + soot(R, 100, 100, 46) + flames(R, 100, 104, 32, 6), BARREL_DEFS)
R = random.Random(33)
charred = "".join(
    f'<g transform="translate({100+R.gauss(0,28):.0f} {100+R.gauss(0,28):.0f}) rotate({R.uniform(0,180):.0f})">'
    f'<rect x="-20" y="-6" width="40" height="12" rx="5" fill="{R.choice(["#1c120c","#2a1a10","#120c08"])}"/></g>' for _ in range(9))
write("barril", "barril_queimado", soot(R, 100, 100, 70) + hoop.replace("#2e2e30", "#1a1a1c") + charred, BARREL_DEFS)

# ---------------- Caixa de madeira (transparente) ----------------
def crate(color="#8a6236"):
    boards = "".join(f'<rect x="34" y="{34+i*33}" width="132" height="33" fill="{shade(color, k)}"/>' for i, k in enumerate([1, .9, 1.05, .93]))
    return (f'<rect x="38" y="40" width="132" height="132" fill="#000" opacity=".4" filter="url(#bl8)"/>'
            f'<g filter="url(#cg)">{boards}</g>'
            f'<g stroke="#2a180a" stroke-width="2"><line x1="34" y1="67" x2="166" y2="67"/><line x1="34" y1="100" x2="166" y2="100"/><line x1="34" y1="133" x2="166" y2="133"/></g>'
            f'<rect x="34" y="34" width="132" height="132" fill="none" stroke="#3b2412" stroke-width="12"/>'
            f'<line x1="40" y1="40" x2="160" y2="160" stroke="{shade(color, .8)}" stroke-width="12"/>'
            f'<line x1="40" y1="40" x2="160" y2="160" stroke="#2a180a" stroke-width="12" fill="none" opacity=".25"/>'
            f'<rect x="34" y="34" width="132" height="132" fill="none" stroke="#2a180a" stroke-width="3"/>'
            + "".join(f'<circle cx="{x}" cy="{y}" r="2.5" fill="#2e2e30"/>' for x in (40, 160) for y in (40, 160)))
CRATE_DEFS = noise("cg", "0.25 0.01", 6, (.22, .12, .05))
write("caixa", "caixa_inteira", crate(), CRATE_DEFS)
R = random.Random(41)
boards = "".join(
    f'<g transform="translate({100+R.gauss(0,30):.0f} {100+R.gauss(0,30):.0f}) rotate({R.uniform(0,180):.0f})">'
    f'<rect x="-{(L:=R.randint(30,66))/2}" y="-8" width="{L}" height="16" fill="{shade("#8a6236", R.uniform(.8,1.1))}" stroke="#2a180a" stroke-width="2"/></g>' for _ in range(9))
straw = "".join(f'<line x1="{(x:=100+R.gauss(0,40)):.0f}" y1="{(y:=100+R.gauss(0,40)):.0f}" x2="{x+R.uniform(-12,12):.0f}" y2="{y+R.uniform(-12,12):.0f}" stroke="#d8b65a" stroke-width="1.6"/>' for _ in range(60))
write("caixa", "caixa_quebrada", straw + boards, CRATE_DEFS)
R = random.Random(42)
write("caixa", "caixa_queimando", crate("#5a3a20") + soot(R, 100, 100, 46) + flames(R, 100, 104, 34, 6), CRATE_DEFS)
R = random.Random(43)
burnt_boards = "".join(
    f'<g transform="translate({100+R.gauss(0,26):.0f} {100+R.gauss(0,26):.0f}) rotate({R.uniform(0,180):.0f})">'
    f'<rect x="-{(L:=R.randint(24,50))/2}" y="-7" width="{L}" height="14" fill="{R.choice(["#1c120c","#2a1a10","#120c08"])}"/></g>' for _ in range(8))
write("caixa", "caixa_queimada", soot(R, 100, 100, 70) + burnt_boards, CRATE_DEFS)

print("ok")
