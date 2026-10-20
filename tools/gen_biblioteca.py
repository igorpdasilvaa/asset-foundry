"""Gera os SVGs dos assets de biblioteca e estudo de Candlekeep (vistos de cima) em assets/<id>/.
estante, pilha_livros, atril, escrivaninha, carrinho_livros, vela, lampada, globo, sino, altar, gargula.
1 quadrado = 200 unidades. Uso:
python3 tools/gen_biblioteca.py && NODE_PATH=$(npm root -g) node tools/render.js assets/{estante,pilha_livros,atril,escrivaninha,carrinho_livros,vela,lampada,globo,sino,altar,gargula}/*.svg"""
import math, random, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gen_pecas_mapa import noise, shade, wrap

A = pathlib.Path(__file__).resolve().parent.parent / "assets"
S = 200

# Madeira escura, couro e lombadas (vinho, verde, azul, ocre).
WOOD = "#4a2e1a"
WOOD_D = "#2e1b0e"
LINE = "#1a0f07"
BOOKS = ["#6e1f2a", "#7d2a2a", "#2f5a3a", "#3c6b44", "#2a3f6e", "#34508a", "#b07a2a", "#9a6a22", "#4f2f52"]
GOLD = "#d4af37"
PAPER = "#e9dcbc"
BRASS = "#b8893a"

COMMON = (
    '<filter id="bl3" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3"/></filter>'
    '<filter id="bl4" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter>'
    '<filter id="bl8" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="8"/></filter>'
    '<radialGradient id="glow"><stop offset="0" stop-color="#ffb347" stop-opacity=".75"/><stop offset=".6" stop-color="#ff5a1a" stop-opacity=".3"/><stop offset="1" stop-color="#ff5a1a" stop-opacity="0"/></radialGradient>'
    '<radialGradient id="soot"><stop offset="0" stop-color="#0b0908" stop-opacity=".9"/><stop offset=".7" stop-color="#1a1410" stop-opacity=".55"/><stop offset="1" stop-color="#1a1410" stop-opacity="0"/></radialGradient>'
    '<radialGradient id="wet"><stop offset="0" stop-color="#22466e" stop-opacity=".6"/><stop offset=".7" stop-color="#284f7a" stop-opacity=".35"/><stop offset="1" stop-color="#2d5f92" stop-opacity="0"/></radialGradient>'
    '<radialGradient id="ink"><stop offset="0" stop-color="#05040a" stop-opacity=".95"/><stop offset=".8" stop-color="#0b0a14" stop-opacity=".9"/><stop offset="1" stop-color="#0b0a14" stop-opacity="0"/></radialGradient>'
    + noise("wg", "0.006 0.2", 5, (.12, .06, .02))
    + noise("wgv", "0.2 0.006", 6, (.12, .06, .02))
    + noise("sn", "0.07", 7, (.2, .19, .17), 1.2, -.4)
    + noise("bz", "0.04", 3, (.25, .15, .05), 1.0, -.35)
)


def write(folder, name, W, H, body, defs=""):
    d = A / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{folder}_{name}.svg").write_text(wrap(W * S, H * S, body, COMMON + defs))


# ---------------- helpers (copiados de gen_estruturas.py, com ajustes) ----------------
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


def soot_e(cx, cy, rx, ry, op=1):
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="url(#soot)" opacity="{op}"/>'


def embers(R, cx, cy, sx, sy, n=10):
    return '<g opacity=".8">' + "".join(
        f'<circle cx="{cx+R.uniform(-sx,sx):.0f}" cy="{cy+R.uniform(-sy,sy):.0f}" r="{R.uniform(1,3):.1f}" fill="{R.choice(["#ff7b2e","#ffb347","#ff5a1a"])}"/>' for _ in range(n)) + '</g>'


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


def crack(R, x, y, steps, ang, width=2.2, color="#141210"):
    d = f"M{x:.0f},{y:.0f}"
    for _ in range(steps):
        ang += R.uniform(-.6, .6)
        L = R.uniform(10, 22)
        x, y = x + L * math.cos(ang), y + L * math.sin(ang)
        d += f" L{x:.0f},{y:.0f}"
    return f'<path d="{d}" stroke="{color}" stroke-width="{width}" fill="none" stroke-linejoin="round"/>'


def splinters(R, n, cx, cy, spread, color=WOOD, sy=None):
    out = ""
    sy = sy if sy is not None else spread * .7
    for _ in range(n):
        x, y = cx + R.gauss(0, spread), cy + R.gauss(0, sy)
        L, a = R.uniform(10, 30), R.uniform(0, math.pi)
        out += f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{x+L*math.cos(a):.0f}" y2="{y+L*math.sin(a):.0f}" stroke="{color}" stroke-width="{R.uniform(3,6):.1f}" stroke-linecap="round"/>'
    return out


def ash(R, cx, cy, sx, sy, n=18):
    """Restos de papel queimado: lascas cinzentas com borda alaranjada."""
    out = ""
    for _ in range(n):
        x, y = cx + R.gauss(0, sx), cy + R.gauss(0, sy)
        r = R.uniform(4, 10)
        k = R.randint(4, 6)
        pts = " ".join(f"{x+r*R.uniform(.5,1)*math.cos(i*2*math.pi/k):.1f},{y+r*R.uniform(.5,1)*math.sin(i*2*math.pi/k):.1f}" for i in range(k))
        out += f'<polygon points="{pts}" fill="{R.choice(["#4a4744","#3a3735","#5e5a55","#2a2826"])}" stroke="#ff7b2e" stroke-width=".8" stroke-opacity=".6"/>'
    return out


def wet_blots(R, cx, cy, sx, sy, n=6, rmin=14, rmax=30):
    return "".join(f'<ellipse cx="{cx+R.uniform(-sx,sx):.0f}" cy="{cy+R.uniform(-sy,sy):.0f}" rx="{R.uniform(rmin,rmax):.0f}" ry="{R.uniform(rmin,rmax)*.7:.0f}" fill="url(#wet)"/>' for _ in range(n))


def text_lines(x, y, w, h, n, color="#5a4a35", op=.55):
    gap = h / (n + 1)
    return "".join(f'<line x1="{x:.1f}" y1="{y+gap*(i+1):.1f}" x2="{x+w*(.75 if i == n-1 else 1):.1f}" y2="{y+gap*(i+1):.1f}" stroke="{color}" stroke-width="1.4" opacity="{op}"/>' for i in range(n))


def open_book(cx, cy, w, h, rot=0, cover="#6e1f2a", page=PAPER, ribbon=True, lines=True):
    """Livro aberto visto de cima: capa por baixo, duas páginas e a dobra no meio."""
    pw = w / 2
    out = (f'<g transform="translate({cx} {cy}) rotate({rot})">'
           f'<rect x="{-w/2-5}" y="{-h/2-4}" width="{w+10}" height="{h+8}" rx="4" fill="{cover}" stroke="{LINE}" stroke-width="2"/>'
           f'<path d="M{-w/2},{-h/2+2} Q{-pw/2},{-h/2-3} 0,{-h/2+3} L0,{h/2} Q{-pw/2},{h/2-4} {-w/2},{h/2} Z" fill="{page}" stroke="#7a6a50" stroke-width="1"/>'
           f'<path d="M{w/2},{-h/2+2} Q{pw/2},{-h/2-3} 0,{-h/2+3} L0,{h/2} Q{pw/2},{h/2-4} {w/2},{h/2} Z" fill="{shade(page, .95)}" stroke="#7a6a50" stroke-width="1"/>'
           f'<rect x="-4" y="{-h/2+3}" width="8" height="{h-3}" fill="#000" opacity=".12"/>'
           f'<line x1="0" y1="{-h/2+3}" x2="0" y2="{h/2}" stroke="#6a5a40" stroke-width="1.5"/>')
    if lines:
        out += text_lines(-w/2 + 7, -h/2 + 4, pw - 14, h - 10, max(3, int(h / 11)))
        out += text_lines(7, -h/2 + 4, pw - 14, h - 10, max(3, int(h / 11)))
    if ribbon:
        out += f'<path d="M3,{h/2-2} l-2,{h*.25:.0f} l4,-5 l3,5 l-1,{-h*.25:.0f} Z" fill="#a01c22"/>'
    return out + '</g>'


def closed_book(cx, cy, w, h, rot=0, color="#2a3f6e", corners=True):
    """Livro fechado deitado visto de cima: capa, bordas das páginas num lado e cantoneiras."""
    out = (f'<g transform="translate({cx:.1f} {cy:.1f}) rotate({rot:.1f})">'
           f'<rect x="{-w/2+3}" y="{-h/2+4}" width="{w}" height="{h}" rx="3" fill="#000" opacity=".3" filter="url(#bl3)"/>'
           f'<rect x="{-w/2}" y="{-h/2}" width="{w}" height="{h}" rx="3" fill="{color}" stroke="{LINE}" stroke-width="2"/>'
           f'<rect x="{w/2-6}" y="{-h/2+3}" width="4" height="{h-6}" fill="{PAPER}" opacity=".85"/>'
           f'<rect x="{-w/2}" y="{-h/2}" width="7" height="{h}" rx="2" fill="{shade(color, .7)}"/>'
           f'<rect x="{-w/2+12}" y="{-h/2+8}" width="{w-26}" height="{h-16}" fill="none" stroke="{GOLD}" stroke-width="1.3" opacity=".7"/>')
    if corners:
        for sx in (-1, 1):
            for sy in (-1, 1):
                x, y = sx * (w / 2 - 1), sy * (h / 2 - 1)
                out += f'<path d="M{x},{y} l{-sx*9},0 l{sx*9},{-sy*9} Z" fill="{GOLD}" opacity=".9"/>'
    return out + '</g>'


def scroll(cx, cy, L, rot=0, color=PAPER, r=6):
    """Pergaminho enrolado visto de cima (cilindro deitado)."""
    return (f'<g transform="translate({cx} {cy}) rotate({rot})">'
            f'<rect x="{-L/2+2}" y="{-r+3}" width="{L}" height="{2*r}" rx="{r}" fill="#000" opacity=".3" filter="url(#bl3)"/>'
            f'<rect x="{-L/2}" y="{-r}" width="{L}" height="{2*r}" rx="{r*.6}" fill="{color}" stroke="#6a5a40" stroke-width="1.3"/>'
            f'<line x1="{-L/2+3}" y1="{-r*.3}" x2="{L/2-3}" y2="{-r*.3}" stroke="#fff" stroke-width="1.5" opacity=".45"/>'
            f'<ellipse cx="{-L/2}" cy="0" rx="2.5" ry="{r}" fill="{shade(color, .8)}" stroke="#6a5a40" stroke-width="1"/>'
            f'<ellipse cx="{L/2}" cy="0" rx="2.5" ry="{r}" fill="{shade(color, .8)}" stroke="#6a5a40" stroke-width="1"/>'
            f'<rect x="-3" y="{-r-1}" width="6" height="{2*r+2}" fill="#8a1c22"/></g>')


def quill(x, y, L, ang, color="#efeae0"):
    """Pena de escrever: haste e vexilo em forma de folha."""
    return (f'<g transform="translate({x} {y}) rotate({ang})">'
            f'<path d="M0,0 Q{L*.35},{-L*.13} {L},{-L*.03} Q{L*.45},{L*.12} {L*.12},{L*.02} Z" fill="{color}" stroke="#7a7266" stroke-width="1"/>'
            f'<line x1="-6" y1="1" x2="{L}" y2="{-L*.03}" stroke="#8a8070" stroke-width="1.5"/>'
            f'<line x1="-8" y1="1.3" x2="-2" y2="1" stroke="#111" stroke-width="2.2" stroke-linecap="round"/></g>')


def shelf_books(R, x0, x1, y0, y1, palette=BOOKS, k=1.0, scorch=0.0, wet=False):
    """Fileira de livros em pé, vistos de cima: capa colorida, bloco de páginas e lombada na frente (borda de baixo)."""
    out = ""
    x = x0
    while x < x1 - 4:
        w = min(R.uniform(9, 18), x1 - x)
        depth = (y1 - y0) * R.uniform(.72, 1)
        top = y1 - depth
        c = R.choice(palette)
        if scorch and R.random() < scorch:
            c = R.choice(["#1c140e", "#2a1d14", "#140e0a"])
        elif wet:
            c = shade(c, .82)
        c = shade(c, k)
        out += (f'<rect x="{x:.1f}" y="{top:.1f}" width="{w-1.2:.1f}" height="{depth:.1f}" fill="{c}" stroke="{LINE}" stroke-width=".8"/>'
                f'<rect x="{x+1.8:.1f}" y="{top+2:.1f}" width="{max(1, w-4.8):.1f}" height="{depth-10:.1f}" fill="{shade(PAPER, k*.9)}" opacity=".35"/>'
                f'<rect x="{x:.1f}" y="{y1-8:.1f}" width="{w-1.2:.1f}" height="8" fill="{shade(c, .72)}"/>')
        if R.random() < .7:
            out += f'<rect x="{x+.5:.1f}" y="{y1-6:.1f}" width="{w-2.2:.1f}" height="1.6" fill="{GOLD}" opacity="{.8*k:.2f}"/>'
        x += w
    return out


# =====================================================================
# ESTANTE (2 x 1): tampo de madeira escura contra a parede (em cima) e lombadas na frente (embaixo).
# =====================================================================
def estante(wood=WOOD, k=1.0, scorch=0.0, wet=False, seed=101):
    R = random.Random(seed)
    w = shade(wood, k)
    out = ('<rect x="18" y="30" width="372" height="160" rx="4" fill="#000" opacity=".45" filter="url(#bl8)"/>'
           f'<rect x="10" y="16" width="380" height="164" rx="4" fill="{shade(WOOD_D, k)}" stroke="{LINE}" stroke-width="4"/>')
    # Nichos com livros (3 vãos separados por montantes).
    bays = [(22, 140), (146, 262), (268, 378)]
    out += f'<rect x="20" y="104" width="360" height="68" fill="#120a05"/>'
    for a, b in bays:
        out += shelf_books(R, a, b, 106, 170, k=k, scorch=scorch, wet=wet)
    for x in (140, 262):
        out += f'<rect x="{x}" y="100" width="7" height="74" fill="{shade(w, .85)}" stroke="{LINE}" stroke-width="1.5"/>'
    # Tampo (madeira escura, tábuas no comprimento).
    out += (f'<g filter="url(#wg)"><rect x="10" y="16" width="380" height="88" fill="{w}"/></g>'
            f'<g stroke="{LINE}" stroke-width="1.6" opacity=".8"><line x1="10" y1="45" x2="390" y2="45"/><line x1="10" y1="74" x2="390" y2="74"/>'
            '<line x1="128" y1="16" x2="128" y2="45"/><line x1="290" y1="45" x2="290" y2="74"/><line x1="200" y1="74" x2="200" y2="104"/></g>'
            f'<rect x="10" y="98" width="380" height="8" fill="{shade(w, .7)}"/>'
            f'<rect x="10" y="16" width="380" height="4" fill="{shade(w, 1.35)}" opacity=".6"/>'
            f'<rect x="10" y="16" width="380" height="164" rx="4" fill="none" stroke="{LINE}" stroke-width="4"/>'
            f'<rect x="10" y="172" width="380" height="8" fill="{shade(w, .8)}" stroke="{LINE}" stroke-width="1.5"/>')
    out += "".join(f'<circle cx="{x}" cy="{y}" r="2.2" fill="#1a1a1c"/>' for x in (20, 380) for y in (26, 94))
    return out


write("estante", "inteira", 2, 1, estante())
R = random.Random(111)
molhada = (estante(wet=True) + '<rect x="20" y="104" width="360" height="68" fill="#2d5f92" opacity=".22"/>'
           + wet_blots(R, 200, 140, 170, 25, 9, 16, 30) + wet_blots(R, 200, 60, 170, 30, 5, 18, 32)
           + '<ellipse cx="200" cy="188" rx="170" ry="11" fill="#5d8fbf" opacity=".4"/>'
           + "".join(f'<path d="M{x},{176} q-3,8 0,13 q3,-5 0,-13 Z" fill="#7fb0dc" opacity=".8"/>' for x in (48, 96, 170, 236, 300, 352)))
write("estante", "molhada", 2, 1, molhada)
R = random.Random(112)
chamuscada = (estante(k=.62, scorch=.4) + soot_e(110, 120, 70, 40, .9) + soot_e(300, 90, 80, 45, .8) + soot_e(220, 150, 50, 25, .7))
write("estante", "chamuscada", 2, 1, chamuscada)
R = random.Random(113)
queimando = (estante(k=.5, scorch=.6) + soot_e(200, 110, 180, 70, .9)
             + flames(R, 90, 140, 40, 6) + flames(R, 210, 130, 45, 7) + flames(R, 320, 140, 38, 6))
write("estante", "queimando", 2, 1, queimando)
R = random.Random(114)
cinzas = (soot_e(200, 105, 190, 90) + ash(R, 200, 120, 90, 30, 26)
          + "".join(f'<g transform="translate({R.uniform(40,360):.0f} {R.uniform(40,160):.0f}) rotate({R.uniform(-30,30):.0f})">'
                    f'<rect x="-{(L:=R.randint(40,110))/2}" y="-7" width="{L}" height="14" rx="4" fill="{R.choice(["#1c120c","#2a1a10","#120c08"])}"/>'
                    f'<line x1="-{L/2-6}" y1="0" x2="{L/2-6}" y2="0" stroke="#3a2414" stroke-width="1.5" stroke-dasharray="6 5"/></g>' for _ in range(9))
          + embers(R, 200, 110, 160, 60, 18))
write("estante", "cinzas", 2, 1, cinzas)


def spilled_books(R, cx, cy, sx, sy, n, open_n=2):
    out = ""
    for _ in range(n):
        out += closed_book(cx + R.uniform(-sx, sx), cy + R.uniform(-sy, sy), R.uniform(24, 34), R.uniform(17, 24), R.uniform(0, 180), R.choice(BOOKS), corners=False)
    for _ in range(open_n):
        out += open_book(cx + R.uniform(-sx, sx), cy + R.uniform(-sy, sy), 44, 30, R.uniform(-60, 60), R.choice(BOOKS), ribbon=False)
    return out


# Tombada: caída para frente; vê-se o fundo da estante (tábuas) e os livros espalhados pela frente e pelos lados.
R = random.Random(115)
tomb = spilled_books(R, 200, 172, 175, 18, 9, 1)
tomb += ('<g transform="rotate(2.5 200 110)">'
         '<rect x="22" y="48" width="372" height="132" rx="4" fill="#000" opacity=".45" filter="url(#bl8)"/>'
         f'<g filter="url(#wgv)"><rect x="14" y="36" width="372" height="132" fill="{WOOD}"/></g>'
         + "".join(f'<line x1="{x}" y1="36" x2="{x}" y2="168" stroke="{LINE}" stroke-width="1.8"/>' for x in range(60, 380, 46))
         + f'<rect x="14" y="36" width="372" height="132" fill="none" stroke="{LINE}" stroke-width="4"/>'
         + f'<rect x="14" y="36" width="372" height="12" fill="{shade(WOOD, .75)}" stroke="{LINE}" stroke-width="1.5"/>'
         + f'<rect x="14" y="98" width="372" height="7" fill="{shade(WOOD, .75)}" opacity=".9"/>'
         + "".join(f'<circle cx="{x}" cy="{y}" r="2.2" fill="#1a1a1c"/>' for x in range(37, 380, 46) for y in (42, 101, 160)) + '</g>')
tomb += spilled_books(R, 200, 186, 180, 10, 7, 2) + spilled_books(R, 18, 120, 10, 60, 2, 0) + spilled_books(R, 382, 120, 10, 60, 2, 0)
write("estante", "tombada", 2, 1, tomb)

# Cortada: partida ao meio, as duas metades afastadas e inclinadas, livros caídos no vão.
R = random.Random(116)
base = estante()
cort = (f'<defs><clipPath id="ce"><polygon points="0,0 196,0 188,40 204,80 186,120 202,160 192,200 0,200"/></clipPath>'
        f'<clipPath id="cd"><polygon points="206,0 400,0 400,200 200,200 210,160 194,120 212,80 196,40"/></clipPath></defs>'
        + spilled_books(R, 200, 140, 26, 40, 5, 1)
        + f'<g transform="rotate(-3 20 180) translate(-4 0)" clip-path="url(#ce)">{base}</g>'
        + f'<g transform="rotate(3 380 180) translate(5 0)" clip-path="url(#cd)">{base}</g>'
        + splinters(R, 14, 200, 110, 14, WOOD, 50) + splinters(R, 6, 200, 110, 12, "#6a4428", 45)
        + spilled_books(R, 200, 182, 40, 8, 3, 0))
write("estante", "cortada", 2, 1, cort)

# =====================================================================
# PILHA DE LIVROS (1 x 1)
# =====================================================================
def pilha(k=1.0, wet=False, scorch=False, seed=201):
    R = random.Random(seed)
    cols = ["#6e1f2a", "#2f5a3a", "#b07a2a", "#2a3f6e", "#4f2f52"]
    out = '<ellipse cx="106" cy="112" rx="70" ry="60" fill="#000" opacity=".4" filter="url(#bl8)"/>'
    sizes = [(132, 96, -8), (122, 90, 6), (114, 84, -3), (104, 78, 9), (96, 70, -2)]
    for i, (w, h, rot) in enumerate(sizes):
        c = cols[i]
        if wet:
            c = shade(c, .8)
        if scorch:
            c = R.choice(["#2a1d14", "#1c140e", "#3a2414"])
        c = shade(c, k)
        out += closed_book(100 + R.uniform(-5, 5), 100 + R.uniform(-5, 5) - i * 2, w, h, rot, c, corners=(i == len(sizes) - 1))
    # Detalhe do livro de cima: medalhão dourado.
    out += f'<circle cx="101" cy="91" r="11" fill="none" stroke="{GOLD}" stroke-width="2.4" opacity="{.9*k:.2f}"/><circle cx="101" cy="91" r="4" fill="{GOLD}" opacity="{.9*k:.2f}"/>'
    return out


write("pilha_livros", "inteira", 1, 1, pilha())
R = random.Random(211)
write("pilha_livros", "molhada", 1, 1, '<ellipse cx="102" cy="112" rx="88" ry="74" fill="#5d8fbf" opacity=".35"/>' + pilha(wet=True)
      + wet_blots(R, 100, 100, 40, 35, 6, 14, 26) + '<rect x="30" y="30" width="140" height="140" fill="#2d5f92" opacity=".08"/>')
R = random.Random(212)
esp = spilled_books(R, 100, 100, 60, 55, 5, 0)
esp += open_book(80, 120, 70, 50, -18, "#6e1f2a") + open_book(130, 70, 60, 42, 25, "#2f5a3a", ribbon=False)
esp += "".join(f'<g transform="translate({R.uniform(30,170):.0f} {R.uniform(30,170):.0f}) rotate({R.uniform(0,180):.0f})"><rect x="-12" y="-9" width="24" height="18" fill="{PAPER}" stroke="#7a6a50" stroke-width="1"/>{text_lines(-9,-8,18,16,3)}</g>' for _ in range(4))
write("pilha_livros", "espalhada", 1, 1, esp)
R = random.Random(213)
write("pilha_livros", "queimando", 1, 1, pilha(k=.6, scorch=True) + soot(R, 100, 100, 50) + flames(R, 100, 108, 34, 7))
R = random.Random(214)
write("pilha_livros", "cinzas", 1, 1, soot(R, 100, 100, 72, 0) + ash(R, 100, 100, 32, 28, 24) + embers(R, 100, 100, 45, 40, 12))

# =====================================================================
# ATRIL (1 x 1): pé em cruz, tampo inclinado e um grande livro aberto.
# =====================================================================
def atril(wood=WOOD, k=1.0, page=PAPER, book_k=1.0):
    w = shade(wood, k)
    out = '<rect x="38" y="48" width="134" height="124" rx="10" fill="#000" opacity=".45" filter="url(#bl8)"/>'
    # Pés em cruz que aparecem por baixo do tampo.
    out += "".join(f'<rect x="{x}" y="{y}" width="{ww}" height="{hh}" rx="5" fill="{shade(w, .8)}" stroke="{LINE}" stroke-width="2.5"/>'
                   for x, y, ww, hh in ((14, 92, 172, 16), (92, 150, 16, 40)))
    # Tampo inclinado com moldura e régua para segurar o livro.
    out += (f'<g filter="url(#wg)"><rect x="30" y="34" width="140" height="126" rx="6" fill="{w}"/></g>'
            f'<rect x="30" y="34" width="140" height="126" rx="6" fill="none" stroke="{LINE}" stroke-width="3.5"/>'
            f'<rect x="38" y="40" width="124" height="104" rx="3" fill="{shade(w, .85)}" stroke="{LINE}" stroke-width="1.5"/>'
            f'<rect x="30" y="146" width="140" height="14" rx="4" fill="{shade(w, 1.25)}" stroke="{LINE}" stroke-width="2"/>'
            f'<rect x="30" y="34" width="140" height="6" fill="#000" opacity=".2"/>')
    out += open_book(100, 92, 118, 92, 0, shade("#6e1f2a", book_k * k), page)
    # Iluminura: capitular dourada.
    out += f'<rect x="50" y="56" width="12" height="12" fill="{GOLD}" opacity="{.85*book_k:.2f}"/><rect x="52" y="58" width="8" height="8" fill="#8a1c22" opacity="{.85*book_k:.2f}"/>'
    return out


write("atril", "inteiro", 1, 1, atril())
R = random.Random(311)
write("atril", "chamuscado", 1, 1, atril(k=.6, page="#c8a878", book_k=.7) + soot_e(70, 60, 40, 32, .85) + soot_e(140, 130, 40, 30, .8) + soot_e(110, 90, 22, 18, .6))
R = random.Random(312)
write("atril", "queimando", 1, 1, atril(k=.5, page="#a88a5a", book_k=.6) + soot(R, 100, 96, 56) + flames(R, 100, 104, 34, 7))
R = random.Random(313)
write("atril", "queimado", 1, 1, soot(R, 100, 100, 74, 0)
      + "".join(f'<g transform="translate({100+R.gauss(0,26):.0f} {100+R.gauss(0,26):.0f}) rotate({R.uniform(0,180):.0f})"><rect x="-{(L:=R.randint(26,60))/2}" y="-7" width="{L}" height="14" rx="4" fill="{R.choice(["#1c120c","#2a1a10","#120c08"])}"/></g>' for _ in range(7))
      + ash(R, 100, 100, 26, 22, 18) + embers(R, 100, 100, 50, 50, 12))

# Tombado: o atril caiu de lado (coluna em diagonal, tampo numa ponta) e o livro foi parar no chão.
tomb = ('<g transform="rotate(-32 100 100)">'
        '<rect x="20" y="96" width="166" height="40" rx="8" fill="#000" opacity=".4" filter="url(#bl8)"/>'
        f'<rect x="18" y="80" width="18" height="44" rx="4" fill="{shade(WOOD, .8)}" stroke="{LINE}" stroke-width="2.5"/>'
        f'<g filter="url(#wg)"><rect x="34" y="94" width="86" height="16" fill="{shade(WOOD, 1.1)}"/></g>'
        f'<rect x="34" y="94" width="86" height="16" fill="none" stroke="{LINE}" stroke-width="2.5"/>'
        f'<g filter="url(#wgv)"><polygon points="118,58 152,52 158,150 118,144" fill="{WOOD}"/></g>'
        f'<polygon points="118,58 152,52 158,150 118,144" fill="none" stroke="{LINE}" stroke-width="3"/>'
        f'<rect x="150" y="52" width="10" height="98" fill="{shade(WOOD, 1.25)}" stroke="{LINE}" stroke-width="2"/></g>')
tomb += open_book(74, 152, 80, 56, 160, "#6e1f2a")
write("atril", "tombado", 1, 1, tomb)
R = random.Random(314)
quebr = (splinters(R, 14, 100, 100, 34) + splinters(R, 5, 100, 100, 30, "#6a4428")
         + f'<g transform="translate(64 64) rotate(20)"><rect x="-38" y="-30" width="76" height="60" rx="5" fill="{WOOD}" stroke="{LINE}" stroke-width="3"/>'
         f'<polygon points="38,-30 20,-6 38,10 30,30 38,30" fill="#120a05"/></g>'
         + f'<g transform="translate(150 60) rotate(-50)"><rect x="-8" y="-40" width="16" height="80" rx="4" fill="{shade(WOOD, .85)}" stroke="{LINE}" stroke-width="2.5"/></g>'
         + open_book(118, 136, 84, 58, -12, "#6e1f2a")
         + "".join(f'<g transform="translate({R.uniform(40,170):.0f} {R.uniform(110,180):.0f}) rotate({R.uniform(0,180):.0f})"><polygon points="-10,-8 12,-7 9,9 -8,6" fill="{PAPER}" stroke="#7a6a50" stroke-width="1"/></g>' for _ in range(3)))
write("atril", "quebrado", 1, 1, quebr)

# =====================================================================
# ESCRIVANINHA (2 x 1): tinteiro, penas, pergaminhos e vela apagada.
# =====================================================================
DESK_WOOD = "#5a3420"


def desk_top(k=1.0, x=16, y=24, w=368, h=150):
    c = shade(DESK_WOOD, k)
    bh = h / 4
    boards = "".join(f'<rect x="{x}" y="{y+i*bh}" width="{w}" height="{bh}" fill="{shade(c, m)}"/>' for i, m in enumerate([1, .9, 1.06, .94]))
    return (f'<rect x="{x+8}" y="{y+12}" width="{w}" height="{h}" rx="8" fill="#000" opacity=".45" filter="url(#bl8)"/>'
            f'<g filter="url(#wg)">{boards}</g>'
            + "".join(f'<line x1="{x}" y1="{y+i*bh}" x2="{x+w}" y2="{y+i*bh}" stroke="{LINE}" stroke-width="1.8"/>' for i in (1, 2, 3))
            + f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="none" stroke="{shade(c, .6)}" stroke-width="8"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="none" stroke="{LINE}" stroke-width="3.5"/>'
            # Prateleirinha de escaninhos encostada no fundo.
            f'<rect x="{x+6}" y="{y+6}" width="{w-12}" height="26" fill="{shade(c, .75)}" stroke="{LINE}" stroke-width="2"/>'
            + "".join(f'<rect x="{x+10+i*44}" y="{y+10}" width="38" height="18" fill="#140b06"/>' for i in range(8))
            + "".join(f'<rect x="{x+14+i*44}" y="{y+13}" width="{10+(i*7)%20}" height="12" fill="{PAPER if i%3 else BOOKS[i%len(BOOKS)]}" opacity=".85"/>' for i in range(8)))


def inkwell(cx, cy):
    return (f'<circle cx="{cx+3}" cy="{cy+4}" r="15" fill="#000" opacity=".35" filter="url(#bl3)"/>'
            f'<circle cx="{cx}" cy="{cy}" r="15" fill="{BRASS}" stroke="#4a3412" stroke-width="2"/>'
            f'<circle cx="{cx}" cy="{cy}" r="9" fill="#08070c"/><circle cx="{cx-3}" cy="{cy-3}" r="2.5" fill="#fff" opacity=".5"/>')


def candle_unlit(cx, cy):
    return (f'<circle cx="{cx+3}" cy="{cy+4}" r="17" fill="#000" opacity=".35" filter="url(#bl3)"/>'
            f'<circle cx="{cx}" cy="{cy}" r="17" fill="{BRASS}" stroke="#4a3412" stroke-width="2"/>'
            f'<path d="M{cx+15},{cy} q10,-2 12,6 q-6,4 -12,2" fill="{BRASS}" stroke="#4a3412" stroke-width="1.6"/>'
            f'<circle cx="{cx}" cy="{cy}" r="9" fill="#efe6cf" stroke="#9a8f74" stroke-width="1.2"/>'
            f'<path d="M{cx+6},{cy+5} q4,5 1,9" stroke="#e6dcc0" stroke-width="3" fill="none"/>'
            f'<circle cx="{cx}" cy="{cy}" r="2.2" fill="#111"/>')


def parchment(cx, cy, w, h, rot, color=PAPER):
    return (f'<g transform="translate({cx} {cy}) rotate({rot})">'
            f'<rect x="{-w/2+3}" y="{-h/2+4}" width="{w}" height="{h}" fill="#000" opacity=".25" filter="url(#bl3)"/>'
            f'<rect x="{-w/2}" y="{-h/2}" width="{w}" height="{h}" fill="{color}" stroke="#7a6a50" stroke-width="1.2"/>'
            + text_lines(-w/2 + 7, -h/2 + 3, w - 14, h - 8, int(h / 9)) + '</g>')


def escrivaninha(k=1.0, paper=PAPER, ink=True):
    out = desk_top(k)
    out += parchment(196, 112, 96, 74, -6, paper) + parchment(120, 118, 64, 52, 8, paper)
    out += scroll(70, 92, 58, 80, shade(paper, .95)) + scroll(300, 146, 64, -12, shade(paper, .95)) + scroll(312, 128, 54, -4, shade(paper, .95))
    out += closed_book(66, 140, 52, 38, -10, shade("#2f5a3a", k)) + closed_book(70, 136, 46, 34, 6, shade("#6e1f2a", k), corners=False)
    if ink:
        out += inkwell(262, 84)
    out += quill(258, 82, 52, -40) + quill(232, 150, 58, -168, "#d9d2c4")
    out += candle_unlit(350, 84)
    return out


write("escrivaninha", "inteira", 2, 1, escrivaninha())
R = random.Random(411)
blob = ("M262,80 C230,70 214,96 222,118 C206,132 214,152 236,150 C244,170 236,186 252,196 L282,196 "
        "C300,184 292,168 304,156 C326,154 334,132 318,118 C330,98 300,70 262,80 Z")
tinta = (escrivaninha(ink=False)
         + f'<path d="{blob}" fill="#07060c" opacity=".93"/>'
         + f'<path d="{blob}" fill="none" stroke="#1a1830" stroke-width="3" opacity=".7"/>'
         + '<path d="M236,110 q10,-12 26,-10" stroke="#5a5a7a" stroke-width="3" fill="none" opacity=".45" stroke-linecap="round"/>'
         + '<ellipse cx="270" cy="190" rx="40" ry="8" fill="#07060c" opacity=".8"/>'
         + "".join(f'<circle cx="{R.uniform(210,330):.0f}" cy="{R.uniform(60,196):.0f}" r="{R.uniform(2,5):.1f}" fill="#07060c"/>' for _ in range(14))
         # Tinteiro caído de lado.
         + '<g transform="translate(250 92) rotate(-30)"><rect x="-16" y="-11" width="30" height="22" rx="6" fill="#4a3412"/>'
         f'<rect x="-14" y="-9" width="26" height="18" rx="5" fill="{BRASS}"/><ellipse cx="13" cy="0" rx="4" ry="9" fill="#08070c"/></g>')
write("escrivaninha", "tinta_derramada", 2, 1, tinta)
R = random.Random(412)
write("escrivaninha", "chamuscada", 2, 1, escrivaninha(k=.6, paper="#c8a878") + soot_e(120, 110, 90, 50, .85) + soot_e(300, 90, 70, 45, .8) + soot_e(220, 150, 50, 25, .6))
R = random.Random(413)
write("escrivaninha", "queimando", 2, 1, escrivaninha(k=.5, paper="#a88a5a") + soot_e(200, 100, 180, 70, .9)
      + flames(R, 110, 120, 42, 7) + flames(R, 230, 110, 40, 6) + flames(R, 320, 130, 36, 6))
R = random.Random(414)
write("escrivaninha", "queimada", 2, 1, soot_e(200, 100, 190, 92)
      + "".join(f'<g transform="translate({R.uniform(40,360):.0f} {R.uniform(40,160):.0f}) rotate({R.uniform(-40,40):.0f})"><rect x="-{(L:=R.randint(40,110))/2}" y="-8" width="{L}" height="16" rx="4" fill="{R.choice(["#1c120c","#2a1a10","#120c08"])}"/></g>' for _ in range(8))
      + ash(R, 200, 110, 90, 35, 22) + inkwell(250, 120).replace(BRASS, "#4a3a22") + embers(R, 200, 100, 160, 60, 16))

# Quebrada: o tampo cede no meio em V, papéis e penas pelo chão.
R = random.Random(415)
half = desk_top()
quebr = ('<defs><clipPath id="qe"><polygon points="0,0 190,0 204,50 186,100 206,150 192,200 0,200"/></clipPath>'
         '<clipPath id="qd"><polygon points="200,0 400,0 400,200 202,200 216,150 196,100 214,50"/></clipPath></defs>'
         + f'<g transform="rotate(4 20 100) scale(.97)" clip-path="url(#qe)">{half}</g>'
         + f'<g transform="rotate(-4 380 100) translate(10 6) scale(.97)" clip-path="url(#qd)">{half}</g>'
         + '<rect x="186" y="10" width="34" height="186" fill="#000" opacity=".35" filter="url(#bl4)"/>'
         + splinters(R, 14, 200, 100, 12, DESK_WOOD, 55) + splinters(R, 6, 200, 100, 14, "#7a4a2c", 50)
         + parchment(150, 160, 70, 50, 20) + parchment(266, 64, 60, 46, -24) + scroll(330, 160, 60, 30) + scroll(80, 70, 54, -50)
         + closed_book(90, 150, 48, 34, 30, "#2f5a3a") + quill(232, 120, 52, 40)
         + '<path d="M246,96 C230,90 224,110 236,120 C232,134 252,140 262,128 C276,130 280,110 266,104 C266,94 254,90 246,96 Z" fill="#07060c" opacity=".9"/>'
         + inkwell(300, 112).replace(BRASS, "#9a7432"))
write("escrivaninha", "quebrada", 2, 1, quebr)

# =====================================================================
# CARRINHO DE LIVROS (1 x 2, vertical): alça em cima, rodinhas dos lados e duas fileiras de livros.
# =====================================================================
def cart_books(R, x0, x1, y0, y1, k=1.0, scorch=0.0):
    """Livros em pé com a lombada para fora (bordas esquerda/direita), espessuras ao longo de y."""
    out = ""
    y = y0
    left = x1 < 100
    while y < y1 - 4:
        t = min(R.uniform(9, 16), y1 - y)
        depth = (x1 - x0) * R.uniform(.75, 1)
        c = R.choice(BOOKS)
        if scorch and R.random() < scorch:
            c = R.choice(["#1c140e", "#2a1d14", "#140e0a"])
        c = shade(c, k)
        bx = x0 if left else x1 - depth
        sx = x0 if left else x1 - 7
        out += (f'<rect x="{bx:.1f}" y="{y:.1f}" width="{depth:.1f}" height="{t-1.2:.1f}" fill="{c}" stroke="{LINE}" stroke-width=".8"/>'
                f'<rect x="{bx+(8 if left else 2):.1f}" y="{y+1.8:.1f}" width="{depth-10:.1f}" height="{max(1, t-4.8):.1f}" fill="{shade(PAPER, k*.9)}" opacity=".35"/>'
                f'<rect x="{sx:.1f}" y="{y:.1f}" width="7" height="{t-1.2:.1f}" fill="{shade(c, .72)}"/>')
        if R.random() < .7:
            gx = sx + (4 if left else 1.4)
            out += f'<rect x="{gx:.1f}" y="{y+.5:.1f}" width="1.6" height="{t-2.2:.1f}" fill="{GOLD}" opacity="{.8*k:.2f}"/>'
        y += t
    return out


def carrinho(k=1.0, scorch=0.0, seed=501, wheels=(True, True, True, True)):
    R = random.Random(seed)
    w = shade(WOOD, k)
    out = '<rect x="46" y="58" width="122" height="310" rx="8" fill="#000" opacity=".45" filter="url(#bl8)"/>'
    # Rodinhas (vistas de cima: aros saindo pelos lados).
    for on, (x, y) in zip(wheels, ((24, 82), (160, 82), (24, 292), (160, 292))):
        if on:
            out += f'<rect x="{x}" y="{y}" width="16" height="36" rx="5" fill="#2b2b2e" stroke="#111" stroke-width="2"/><line x1="{x+2}" y1="{y+18}" x2="{x+14}" y2="{y+18}" stroke="#555" stroke-width="2"/>'
    # Alça.
    out += (f'<rect x="56" y="14" width="10" height="44" fill="{shade(w, 1.1)}" stroke="{LINE}" stroke-width="2"/>'
            f'<rect x="134" y="14" width="10" height="44" fill="{shade(w, 1.1)}" stroke="{LINE}" stroke-width="2"/>'
            f'<rect x="50" y="10" width="100" height="14" rx="7" fill="{shade(w, 1.25)}" stroke="{LINE}" stroke-width="2.5"/>')
    # Caixa do carrinho.
    out += (f'<g filter="url(#wgv)"><rect x="38" y="52" width="124" height="306" rx="6" fill="{w}"/></g>'
            f'<rect x="38" y="52" width="124" height="306" rx="6" fill="none" stroke="{LINE}" stroke-width="4"/>'
            '<rect x="48" y="62" width="104" height="140" fill="#120a05"/><rect x="48" y="210" width="104" height="138" fill="#120a05"/>')
    out += cart_books(R, 49, 97, 63, 201, k, scorch) + cart_books(R, 103, 151, 63, 201, k, scorch)
    out += cart_books(R, 49, 97, 211, 347, k, scorch) + cart_books(R, 103, 151, 211, 347, k, scorch)
    out += (f'<rect x="97" y="58" width="6" height="296" fill="{shade(w, .85)}" stroke="{LINE}" stroke-width="1.5"/>'
            f'<rect x="42" y="201" width="116" height="10" fill="{shade(w, 1.1)}" stroke="{LINE}" stroke-width="2"/>'
            + "".join(f'<rect x="{x}" y="{y}" width="10" height="10" fill="#2e2e30"/>' for x in (38, 152) for y in (52, 348))
            + "".join(f'<circle cx="{x}" cy="{y}" r="1.8" fill="#888"/>' for x in (43, 157) for y in (57, 353)))
    return out


write("carrinho_livros", "inteiro", 1, 2, carrinho())
R = random.Random(511)
quebr = (spilled_books(R, 120, 310, 60, 70, 8, 2)
         + '<g transform="rotate(6 100 200) translate(-6 6) scale(.94)">' + carrinho(wheels=(True, True, True, False)) + '</g>'
         + '<g transform="translate(168 352) rotate(60)"><rect x="-8" y="-18" width="16" height="36" rx="5" fill="#2b2b2e" stroke="#111" stroke-width="2"/></g>'
         + splinters(R, 10, 150, 330, 22, WOOD, 26) + spilled_books(R, 160, 360, 30, 20, 3, 1))
write("carrinho_livros", "quebrado", 1, 2, quebr)
R = random.Random(512)
write("carrinho_livros", "queimando", 1, 2, carrinho(k=.5, scorch=.6) + soot_e(100, 200, 70, 170, .9)
      + flames(R, 100, 130, 36, 6) + flames(R, 100, 280, 36, 6) + flames(R, 90, 210, 26, 4))
R = random.Random(513)
burnt = (soot_e(100, 200, 90, 190)
         + "".join(f'<rect x="{x}" y="{y}" width="16" height="36" rx="5" fill="#1a1a1c" transform="rotate({R.uniform(-30,30):.0f} {x+8} {y+18})"/>' for x, y in ((26, 86), (158, 78), (22, 296), (162, 290)))
         + "".join(f'<g transform="translate({R.uniform(50,150):.0f} {R.uniform(40,360):.0f}) rotate({R.uniform(60,120):.0f})"><rect x="-{(L:=R.randint(50,130))/2}" y="-7" width="{L}" height="14" rx="4" fill="{R.choice(["#1c120c","#2a1a10","#120c08"])}"/></g>' for _ in range(9))
         + ash(R, 100, 200, 40, 110, 26) + embers(R, 100, 200, 60, 160, 18))
write("carrinho_livros", "queimado", 1, 2, burnt)

# =====================================================================
# VELA (1 x 1): candelabro de latão com 3 velas.
# =====================================================================
CANDLES = [(100 + 52 * math.cos(math.radians(a)), 100 + 52 * math.sin(math.radians(a))) for a in (-90, 30, 150)]


def candelabro(lit):
    out = '<circle cx="106" cy="108" r="70" fill="#000" opacity=".3" filter="url(#bl8)"/>'
    out += "".join(f'<line x1="100" y1="100" x2="{x:.0f}" y2="{y:.0f}" stroke="#4a3412" stroke-width="11" stroke-linecap="round"/>'
                   f'<line x1="100" y1="100" x2="{x:.0f}" y2="{y:.0f}" stroke="{BRASS}" stroke-width="7" stroke-linecap="round"/>' for x, y in CANDLES)
    out += (f'<circle cx="100" cy="100" r="24" fill="{BRASS}" stroke="#4a3412" stroke-width="2.5"/>'
            f'<circle cx="100" cy="100" r="15" fill="#d8ac55" stroke="#7a5a22" stroke-width="1.5"/><circle cx="96" cy="96" r="5" fill="#fff3c0" opacity=".6"/>')
    for x, y in CANDLES:
        out += (f'<circle cx="{x:.0f}" cy="{y:.0f}" r="20" fill="{BRASS}" stroke="#4a3412" stroke-width="2.5"/>'
                f'<circle cx="{x:.0f}" cy="{y:.0f}" r="13" fill="#f2ead2" stroke="#a89c7c" stroke-width="1.3"/>'
                f'<path d="M{x+9:.0f},{y+8:.0f} q5,6 1,12" stroke="#ece2c4" stroke-width="3.5" fill="none" stroke-linecap="round"/>'
                f'<circle cx="{x:.0f}" cy="{y:.0f}" r="2.4" fill="#111"/>')
    if lit:
        for x, y in CANDLES:
            out += (f'<circle cx="{x:.0f}" cy="{y:.0f}" r="34" fill="url(#candle)"/>'
                    f'<path d="M{x:.0f},{y-17:.0f} Q{x+9:.0f},{y-3:.0f} {x:.0f},{y+6:.0f} Q{x-9:.0f},{y-3:.0f} {x:.0f},{y-17:.0f} Z" fill="#ff9a2e" opacity=".95"/>'
                    f'<path d="M{x:.0f},{y-10:.0f} Q{x+5:.0f},{y-1:.0f} {x:.0f},{y+4:.0f} Q{x-5:.0f},{y-1:.0f} {x:.0f},{y-10:.0f} Z" fill="#ffe680"/>'
                    f'<circle cx="{x:.0f}" cy="{y:.0f}" r="2.4" fill="#fffbe8"/>')
    else:
        for x, y in CANDLES:
            out += f'<path d="M{x:.0f},{y:.0f} q6,-6 0,-12 q-6,-6 2,-14" stroke="#9a9a9a" stroke-width="2" fill="none" opacity=".45" stroke-linecap="round"/>'
    return out


CANDLE_DEF = '<radialGradient id="candle"><stop offset="0" stop-color="#ffd27a" stop-opacity=".7"/><stop offset=".5" stop-color="#ffb860" stop-opacity=".25"/><stop offset="1" stop-color="#ffb860" stop-opacity="0"/></radialGradient>'
write("vela", "acesa", 1, 1, candelabro(True), CANDLE_DEF)
write("vela", "apagada", 1, 1, candelabro(False), CANDLE_DEF)
R = random.Random(611)
derr = ('<g transform="rotate(-24 100 100)">'
        '<rect x="34" y="94" width="130" height="26" rx="10" fill="#000" opacity=".35" filter="url(#bl4)"/>'
        f'<ellipse cx="44" cy="100" rx="12" ry="30" fill="{BRASS}" stroke="#4a3412" stroke-width="2.5"/>'
        f'<rect x="50" y="94" width="88" height="12" rx="5" fill="{BRASS}" stroke="#4a3412" stroke-width="2"/>'
        f'<circle cx="86" cy="100" r="9" fill="#d8ac55" stroke="#4a3412" stroke-width="2"/>'
        f'<path d="M138,100 L160,72 M138,100 L162,128" stroke="#4a3412" stroke-width="10" stroke-linecap="round"/>'
        f'<path d="M138,100 L160,72 M138,100 L162,128" stroke="{BRASS}" stroke-width="6" stroke-linecap="round"/>'
        + "".join(f'<ellipse cx="{x}" cy="{y}" rx="7" ry="13" fill="{BRASS}" stroke="#4a3412" stroke-width="2" transform="rotate(-40 {x} {y})"/>' for x, y in ((162, 70), (164, 130), (140, 100))) + '</g>')
for x, y, a in ((54, 150, 20), (128, 160, -50), (160, 52, 80)):
    derr += (f'<g transform="translate({x} {y}) rotate({a})"><ellipse cx="6" cy="2" rx="22" ry="12" fill="#f2ead2" opacity=".55"/>'
             f'<rect x="-26" y="-7" width="52" height="14" rx="5" fill="#f2ead2" stroke="#a89c7c" stroke-width="1.3"/>'
             f'<ellipse cx="26" cy="0" rx="3" ry="7" fill="#e2d8b8" stroke="#a89c7c" stroke-width="1"/><line x1="29" y1="0" x2="34" y2="-1" stroke="#111" stroke-width="2"/></g>')
write("vela", "derrubado", 1, 1, derr, CANDLE_DEF)

# =====================================================================
# LÂMPADA DE CHAMA CONTÍNUA (1 x 1): pedestal de latão octogonal e globo com chama mágica imóvel.
# =====================================================================
def octagon(cx, cy, r, rot=22.5):
    return " ".join(f"{cx+r*math.cos(math.radians(rot+i*45)):.1f},{cy+r*math.sin(math.radians(rot+i*45)):.1f}" for i in range(8))


LAMP_DEFS = ('<radialGradient id="lglow"><stop offset="0" stop-color="#fffbe8" stop-opacity=".95"/><stop offset=".35" stop-color="#fff1c9" stop-opacity=".55"/><stop offset="1" stop-color="#fff1c9" stop-opacity="0"/></radialGradient>'
             '<radialGradient id="glass" cx=".4" cy=".38"><stop offset="0" stop-color="#e8eef2" stop-opacity=".55"/><stop offset="1" stop-color="#8a9aa4" stop-opacity=".35"/></radialGradient>'
             '<radialGradient id="brass" cx=".4" cy=".38"><stop offset="0" stop-color="#e8c06a"/><stop offset="1" stop-color="#8a6322"/></radialGradient>')


def pedestal():
    return ('<circle cx="106" cy="108" r="74" fill="#000" opacity=".4" filter="url(#bl8)"/>'
            f'<polygon points="{octagon(100, 100, 74)}" fill="url(#brass)" stroke="#3a2a10" stroke-width="3.5"/>'
            f'<polygon points="{octagon(100, 100, 62)}" fill="none" stroke="#6a4c1a" stroke-width="2"/>'
            + "".join(f'<circle cx="{100+68*math.cos(math.radians(22.5+i*45)):.1f}" cy="{100+68*math.sin(math.radians(22.5+i*45)):.1f}" r="3" fill="#5a4214"/>' for i in range(8))
            + '<circle cx="100" cy="100" r="50" fill="#7a5a22" stroke="#3a2a10" stroke-width="2.5"/>')


lamp_on = (pedestal() + '<circle cx="100" cy="100" r="96" fill="url(#lglow)"/>'
           '<circle cx="100" cy="100" r="40" fill="#fff6dc" stroke="#6a4c1a" stroke-width="3"/>'
           '<circle cx="100" cy="100" r="30" fill="#fffef4"/>'
           '<path d="M100,78 Q114,98 100,116 Q86,98 100,78 Z" fill="#ffe9a8"/>'
           '<path d="M100,88 Q106,99 100,108 Q94,99 100,88 Z" fill="#fff"/>'
           + "".join(f'<line x1="{100+40*math.cos(a):.1f}" y1="{100+40*math.sin(a):.1f}" x2="{100+16*math.cos(a):.1f}" y2="{100+16*math.sin(a):.1f}" stroke="#6a4c1a" stroke-width="3.5" opacity=".75"/>' for a in [i * math.pi / 2 + math.pi / 4 for i in range(4)])
           + '<circle cx="100" cy="100" r="11" fill="none" stroke="#6a4c1a" stroke-width="3" opacity=".75"/>')
write("lampada", "acesa", 1, 1, lamp_on, LAMP_DEFS)
R = random.Random(711)
shards = "".join(f'<polygon points="{(x:=R.uniform(20,180)):.0f},{(y:=R.uniform(20,180)):.0f} {x+R.uniform(4,14):.0f},{y+R.uniform(-6,6):.0f} {x+R.uniform(-4,8):.0f},{y+R.uniform(6,14):.0f}" fill="#cfe0ea" opacity=".75" stroke="#7a8a94" stroke-width=".8"/>' for _ in range(22))
lamp_off = (pedestal() + '<circle cx="100" cy="100" r="40" fill="#2a2620" stroke="#6a4c1a" stroke-width="3"/>'
            '<path d="M70,82 L84,96 L72,112 M128,78 L114,94 L132,104" stroke="#6a4c1a" stroke-width="3.5" fill="none" stroke-linecap="round"/>'
            '<path d="M100,72 L104,90 L94,104 L102,124" stroke="#6a4c1a" stroke-width="3" fill="none"/>'
            '<circle cx="100" cy="100" r="7" fill="#1a1612"/>' + shards)
write("lampada", "quebrada", 1, 1, lamp_off, LAMP_DEFS)

# =====================================================================
# GLOBO FLUTUANTE (1 x 1): esfera de vidro com luz branca; a sombra fica afastada (flutua).
# =====================================================================
GLOBE_DEFS = ('<radialGradient id="gon" cx=".42" cy=".4"><stop offset="0" stop-color="#ffffff"/><stop offset=".55" stop-color="#eef4ff"/><stop offset="1" stop-color="#b8cdf0"/></radialGradient>'
              '<radialGradient id="ghalo"><stop offset="0" stop-color="#f4f8ff" stop-opacity=".9"/><stop offset=".4" stop-color="#dbe8ff" stop-opacity=".35"/><stop offset="1" stop-color="#dbe8ff" stop-opacity="0"/></radialGradient>'
              '<radialGradient id="goff" cx=".4" cy=".38"><stop offset="0" stop-color="#e6ecf2" stop-opacity=".75"/><stop offset=".7" stop-color="#8e9cac" stop-opacity=".6"/><stop offset="1" stop-color="#4e5a68" stop-opacity=".8"/></radialGradient>')
glob_on = ('<ellipse cx="118" cy="134" rx="30" ry="22" fill="#000" opacity=".22" filter="url(#bl8)"/>'
           '<circle cx="96" cy="92" r="92" fill="url(#ghalo)"/>'
           '<circle cx="96" cy="92" r="32" fill="url(#gon)" stroke="#9ab0d8" stroke-width="2"/>'
           '<ellipse cx="86" cy="80" rx="11" ry="7" fill="#fff" transform="rotate(-35 86 80)"/>'
           '<circle cx="96" cy="92" r="40" fill="none" stroke="#fff" stroke-width="1.5" opacity=".5" stroke-dasharray="3 7"/>')
write("globo", "aceso", 1, 1, glob_on, GLOBE_DEFS)
glob_off = ('<ellipse cx="118" cy="134" rx="30" ry="22" fill="#000" opacity=".3" filter="url(#bl8)"/>'
            '<circle cx="96" cy="92" r="32" fill="url(#goff)" stroke="#3e4a58" stroke-width="2.5"/>'
            '<ellipse cx="86" cy="80" rx="10" ry="6" fill="#fff" opacity=".7" transform="rotate(-35 86 80)"/>'
            '<circle cx="104" cy="100" r="9" fill="#5a6676" opacity=".5"/>')
write("globo", "apagado", 1, 1, glob_off, GLOBE_DEFS)
R = random.Random(811)
glob_br = ('<ellipse cx="100" cy="104" rx="56" ry="46" fill="#000" opacity=".12" filter="url(#bl8)"/>'
           + "".join(f'<polygon points="{(x:=100+R.gauss(0,30)):.0f},{(y:=100+R.gauss(0,28)):.0f} {x+R.uniform(6,18):.0f},{y+R.uniform(-8,8):.0f} {x+R.uniform(-6,10):.0f},{y+R.uniform(8,18):.0f}" fill="#d6e2f0" opacity=".8" stroke="#5a6676" stroke-width="1"/>' for _ in range(18))
           + '<path d="M70,96 A30,30 0 0 1 112,70 L106,84 L92,82 L86,98 Z" fill="url(#goff)" stroke="#3e4a58" stroke-width="2"/>'
           + "".join(f'<circle cx="{100+R.gauss(0,40):.0f}" cy="{100+R.gauss(0,40):.0f}" r="1.3" fill="#fff" opacity=".8"/>' for _ in range(16)))
write("globo", "quebrado", 1, 1, glob_br, GLOBE_DEFS)

# =====================================================================
# SINO (1 x 1): sino de bronze pendurado numa trave de madeira, visto de cima.
# =====================================================================
BELL_DEFS = ('<radialGradient id="bell" cx=".42" cy=".4"><stop offset="0" stop-color="#e2a858"/><stop offset=".55" stop-color="#a8682a"/><stop offset="1" stop-color="#5e3812"/></radialGradient>')


def bell(cx=100, cy=100, r=64, tilt=0):
    return (f'<circle cx="{cx+6}" cy="{cy+8}" r="{r+4}" fill="#000" opacity=".4" filter="url(#bl8)"/>'
            f'<g transform="rotate({tilt} {cx} {cy})">'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#bell)" stroke="#2e1a06" stroke-width="3.5"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r-7}" fill="none" stroke="#5e3812" stroke-width="2"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r*.62:.0f}" fill="none" stroke="#c48a3e" stroke-width="2.5" opacity=".7"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r*.38:.0f}" fill="#b47838" stroke="#4a2c0c" stroke-width="2.5"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r*.38:.0f}" fill="url(#bell)" filter="url(#bz)" opacity=".85"/>'
            f'<path d="M{cx-r*.75:.0f},{cy-r*.35:.0f} A{r*.82:.0f},{r*.82:.0f} 0 0 1 {cx-r*.2:.0f},{cy-r*.78:.0f}" stroke="#ffd79a" stroke-width="4" fill="none" opacity=".45" stroke-linecap="round"/></g>')


BEAM = (f'<rect x="0" y="80" width="200" height="40" fill="#000" opacity=".4" filter="url(#bl4)" transform="translate(4 6)"/>'
        f'<g filter="url(#wg)"><rect x="0" y="80" width="200" height="34" fill="{WOOD}"/></g>'
        f'<rect x="0" y="80" width="200" height="34" fill="none" stroke="{LINE}" stroke-width="3"/>'
        f'<line x1="0" y1="97" x2="200" y2="97" stroke="{LINE}" stroke-width="1" opacity=".5"/>'
        '<rect x="74" y="76" width="9" height="42" rx="2" fill="#2e2e30" stroke="#111" stroke-width="1.5"/>'
        '<rect x="117" y="76" width="9" height="42" rx="2" fill="#2e2e30" stroke="#111" stroke-width="1.5"/>'
        + "".join(f'<circle cx="{x}" cy="{y}" r="2" fill="#888"/>' for x in (78.5, 121.5) for y in (84, 110)))
sino = bell() + BEAM
write("sino", "parado", 1, 1, sino, BELL_DEFS)
waves = "".join(f'<circle cx="100" cy="100" r="{r}" fill="none" stroke="#ffe7a8" stroke-width="{w}" opacity="{o}" stroke-dasharray="{d}"/>'
                for r, w, o, d in ((76, 5, .8, "40 14"), (86, 4, .55, "30 18"), (95, 3, .35, "22 22")))
waves += "".join(f'<path d="M{100+70*math.cos(a):.0f},{100+70*math.sin(a):.0f} L{100+96*math.cos(a):.0f},{100+96*math.sin(a):.0f}" stroke="#fff3c8" stroke-width="3" opacity=".7" stroke-linecap="round"/>' for a in [i * math.pi / 4 + .3 for i in range(8)])
write("sino", "tocando", 1, 1, '<circle cx="100" cy="100" r="98" fill="#ffd27a" opacity=".1"/>' + waves + bell(r=64, tilt=8) + BEAM, BELL_DEFS)
R = random.Random(911)
rach = (bell(102, 108, 64, -14) + crack(R, 70, 60, 7, 1.1, 3.5, "#1a0e04") + crack(R, 150, 140, 4, -2.4, 2.5, "#1a0e04")
        + rubble(R, 150, 160, 18, 4, ["#a8682a", "#7a4a1a", "#c48a3e"], (5, 10)) + BEAM)
write("sino", "rachado", 1, 1, rach, BELL_DEFS)

# =====================================================================
# ALTAR (2 x 1): bloco de pedra, toalha azul com borda dourada, livro aberto e o pergaminho dourado de Oghma.
# =====================================================================
CLOTH = "#24345e"


def altar_stone(k=1.0):
    c = shade("#8a857b", k)
    return ('<rect x="30" y="44" width="360" height="140" rx="6" fill="#000" opacity=".45" filter="url(#bl8)"/>'
            f'<rect x="16" y="28" width="368" height="148" rx="6" fill="{shade(c, .7)}" stroke="#1c1b19" stroke-width="4"/>'
            f'<g filter="url(#sn)"><rect x="28" y="40" width="344" height="124" rx="3" fill="{c}"/></g>'
            f'<rect x="28" y="40" width="344" height="124" rx="3" fill="none" stroke="#3a3732" stroke-width="2.5"/>'
            '<g stroke="#4a4741" stroke-width="2" opacity=".7"><line x1="140" y1="40" x2="140" y2="164"/><line x1="260" y1="40" x2="260" y2="164"/><line x1="28" y1="102" x2="140" y2="102"/><line x1="260" y1="102" x2="372" y2="102"/></g>'
            f'<rect x="16" y="28" width="368" height="6" fill="#fff" opacity=".15"/>')


def oghma(cx, cy, s=1.0, op=1.0):
    """Símbolo de Oghma: pergaminho desenrolado dourado."""
    return (f'<g transform="translate({cx} {cy}) scale({s})" opacity="{op}">'
            f'<path d="M-20,-12 L20,-12 Q26,-12 26,-6 Q26,0 20,0 L20,10 Q20,16 14,16 L-20,16 Q-26,16 -26,10 Q-26,4 -20,4 Z" fill="{GOLD}" stroke="#6a4a10" stroke-width="2"/>'
            '<path d="M20,0 Q14,0 14,-6 Q14,-12 20,-12" fill="none" stroke="#6a4a10" stroke-width="1.6"/>'
            '<path d="M-20,4 Q-14,4 -14,10 Q-14,16 -20,16" fill="none" stroke="#6a4a10" stroke-width="1.6"/>'
            '<g stroke="#8a6a1a" stroke-width="1.6"><line x1="-12" y1="-5" x2="12" y2="-5"/><line x1="-12" y1="1" x2="10" y2="1"/><line x1="-10" y1="7" x2="8" y2="7"/></g></g>')


def runner(torn=False):
    if not torn:
        shape = "M150,18 L250,18 L250,186 L150,186 Z"
    else:
        shape = "M150,18 L250,18 L250,70 L236,84 L244,98 L226,112 L232,128 L212,134 L196,124 L184,140 L166,128 L150,138 Z"
    out = (f'<path d="{shape}" fill="#000" opacity=".3" transform="translate(4 4)" filter="url(#bl3)"/>'
           f'<path d="{shape}" fill="{CLOTH}" stroke="#121a30" stroke-width="2"/>'
           '<g fill="none" stroke="' + GOLD + '" stroke-width="3" opacity=".9">'
           f'<line x1="158" y1="18" x2="158" y2="{130 if torn else 186}"/><line x1="242" y1="18" x2="242" y2="{74 if torn else 186}"/></g>')
    if not torn:
        out += "".join(f'<line x1="{x}" y1="186" x2="{x}" y2="194" stroke="{GOLD}" stroke-width="2"/>' for x in range(154, 250, 7))
        out += "".join(f'<line x1="{x}" y1="18" x2="{x}" y2="10" stroke="{GOLD}" stroke-width="2"/>' for x in range(154, 250, 7))
    return out


def altar(k=1.0):
    out = altar_stone(k) + runner()
    out += oghma(200, 158, .9)
    out += open_book(200, 92, 84, 60, 0, "#6e1f2a")
    out += candle_unlit(62, 70) + candle_unlit(338, 70)
    out += f'<circle cx="80" cy="134" r="14" fill="{BRASS}" stroke="#4a3412" stroke-width="2"/><circle cx="80" cy="134" r="9" fill="#5a4214"/>'
    out += scroll(318, 136, 60, -8, GOLD, 7).replace("#8a1c22", "#24345e")
    return out


write("altar", "inteiro", 2, 1, altar())
R = random.Random(1011)
prof = (altar_stone() + runner(torn=True)
        + '<path d="M300,150 L352,148 L360,184 L330,192 L310,182 Z" fill="' + CLOTH + '" stroke="#121a30" stroke-width="2"/>'
        + f'<line x1="304" y1="154" x2="350" y2="152" stroke="{GOLD}" stroke-width="2.5"/>'
        + "".join(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{rx*.7:.0f}" fill="#1a0e22" opacity=".55" filter="url(#bl3)"/>' for x, y, rx in ((110, 80, 26), (282, 120, 30), (200, 150, 18), (60, 140, 16)))
        + crack(R, 196, 92, 5, .6, 1.8, "#3a1a3a") + crack(R, 190, 100, 4, 2.8, 1.8, "#3a1a3a")
        + oghma(200, 92, .9, .5) + '<path d="M184,82 L216,104 M214,80 L186,104" stroke="#2a0e2a" stroke-width="3"/>'
        + open_book(96, 174, 70, 44, 172, "#6e1f2a")
        + '<g transform="translate(64 64) rotate(70)"><rect x="-16" y="-8" width="32" height="16" rx="6" fill="' + BRASS + '" stroke="#4a3412" stroke-width="2"/></g>'
        + candle_unlit(338, 70))
write("altar", "profanado", 2, 1, prof)
R = random.Random(1012)
qe = altar_stone()
quebr = ('<defs><clipPath id="ae"><polygon points="0,0 176,0 196,60 170,120 190,200 0,200"/></clipPath>'
         '<clipPath id="ad"><polygon points="186,0 400,0 400,200 204,200 182,120 208,60"/></clipPath></defs>'
         + f'<g transform="rotate(-3 16 176) scale(.97)" clip-path="url(#ae)">{qe}</g>'
         + f'<g transform="rotate(3 384 176) translate(14 4) scale(.97)" clip-path="url(#ad)">{qe}</g>'
         + rubble(R, 196, 110, 22, 12, ["#8a857b", "#7a756c", "#6b675f", "#9a958b"], (8, 18))
         + rubble(R, 200, 120, 40, 18, ["#8a857b", "#6b675f"], (3, 7))
         + crack(R, 60, 60, 6, .5) + crack(R, 330, 150, 5, -2.5)
         + '<path d="M120,120 L170,112 L176,150 L140,164 Z" fill="' + CLOTH + '" stroke="#121a30" stroke-width="2"/>'
         + '<path d="M232,40 L268,36 L262,70 L240,64 Z" fill="' + CLOTH + '" stroke="#121a30" stroke-width="2"/>'
         + open_book(290, 174, 64, 40, -168, "#6e1f2a") + oghma(110, 70, .8, .8))
write("altar", "quebrado", 2, 1, quebr)

# =====================================================================
# GÁRGULA (1 x 1): estátua de pedra agachada no beiral, asas fechadas; a cabeça olha para baixo (para fora do telhado).
# =====================================================================
GARG_DEFS = ('<radialGradient id="gs" cx=".45" cy=".4"><stop offset="0" stop-color="#9a958b"/><stop offset="1" stop-color="#5a564f"/></radialGradient>'
             '<radialGradient id="gd" cx=".45" cy=".4"><stop offset="0" stop-color="#6b675f"/><stop offset="1" stop-color="#3e3b36"/></radialGradient>'
             '<radialGradient id="eye"><stop offset="0" stop-color="#fff2b0"/><stop offset=".35" stop-color="#ffb02e"/><stop offset="1" stop-color="#ff4a1a" stop-opacity="0"/></radialGradient>')


def gargula(awake):
    st = 'fill="url(#gs)" stroke="#1c1b19" stroke-width="2.5"'
    dk = 'fill="url(#gd)" stroke="#1c1b19" stroke-width="2.5"'
    out = ('<rect x="26" y="26" width="156" height="156" rx="6" fill="#000" opacity=".35" filter="url(#bl8)"/>'
           # Pedra do beiral (bloco onde ela está agachada).
           '<g filter="url(#sn)"><rect x="20" y="20" width="160" height="160" rx="5" fill="#8a857b"/></g>'
           '<rect x="20" y="20" width="160" height="160" rx="5" fill="none" stroke="#1c1b19" stroke-width="3"/>'
           '<rect x="28" y="28" width="144" height="144" rx="3" fill="none" stroke="#4a4741" stroke-width="2" opacity=".6"/>'
           '<ellipse cx="106" cy="104" rx="62" ry="70" fill="#000" opacity=".45" filter="url(#bl8)"/>'
           # Cauda enrolada saindo por trás.
           '<path d="M100,70 C104,44 132,40 146,44 C160,48 158,34 150,30" fill="none" stroke="#1c1b19" stroke-width="10" stroke-linecap="round"/>'
           '<path d="M100,70 C104,44 132,40 146,44 C160,48 158,34 150,30" fill="none" stroke="#6b675f" stroke-width="5.5" stroke-linecap="round"/>'
           '<path d="M150,30 l-11,-4 l7,-8 l9,3 Z" fill="#6b675f" stroke="#1c1b19" stroke-width="2"/>')
    # Ancas e braços (por baixo das asas).
    for sx in (-1, 1):
        out += (f'<ellipse cx="{100+sx*44}" cy="128" rx="16" ry="20" {dk}/>'
                f'<path d="M{100+sx*36},140 l{sx*6},16 l{sx*-4},4 l{sx*-8},-14 Z" {dk}/>'
                f'<path d="M{100+sx*14},120 C{100+sx*30},130 {100+sx*32},146 {100+sx*26},164 L{100+sx*14},166 C{100+sx*16},150 {100+sx*12},136 {100+sx*6},128 Z" {st}/>'
                + "".join(f'<path d="M{100+sx*(14+i*5)},164 l{sx*(i-1)*2},9" stroke="#1c1b19" stroke-width="3.2" stroke-linecap="round"/>' for i in range(3)))
    # Asas fechadas: duas membranas que cobrem as costas, com a "munheca" no alto e os dedos descendo.
    for sx in (-1, 1):
        x = lambda v: 100 + sx * v
        out += (f'<path d="M{x(4)},58 C{x(18)},40 {x(30)},30 {x(36)},18 C{x(52)},34 {x(62)},62 {x(60)},96 '
                f'Q{x(54)},104 {x(56)},116 Q{x(46)},112 {x(40)},124 Q{x(30)},116 {x(22)},128 Q{x(12)},118 {x(4)},126 Z" {st}/>'
                f'<g stroke="#2e2c29" stroke-width="2" fill="none" opacity=".85">'
                f'<path d="M{x(36)},20 Q{x(54)},60 {x(56)},112"/><path d="M{x(36)},20 Q{x(44)},70 {x(40)},120"/><path d="M{x(36)},20 Q{x(30)},76 {x(22)},124"/></g>'
                f'<path d="M{x(36)},18 l{sx*-2},-10 l{sx*7},8 Z" fill="#5a564f" stroke="#1c1b19" stroke-width="2"/>')
    # Espinhaço entre as asas.
    out += "".join(f'<path d="M96,{y} L100,{y-9} L104,{y} Z" fill="#5a564f" stroke="#1c1b19" stroke-width="1.5"/>' for y in (66, 82, 98, 114))
    # Cabeça angulosa voltada para fora do telhado, chifres varrendo para trás.
    out += ('<path d="M86,132 C74,124 66,110 70,94 C76,108 84,116 94,122 Z" fill="#4a4741" stroke="#1c1b19" stroke-width="2.5"/>'
            '<path d="M114,132 C126,124 134,110 130,94 C124,108 116,116 106,122 Z" fill="#4a4741" stroke="#1c1b19" stroke-width="2.5"/>'
            f'<path d="M84,126 L116,126 L124,144 L112,170 L88,170 L76,144 Z" {st}/>'
            '<path d="M80,142 L94,138 L100,146 L106,138 L120,142" stroke="#1c1b19" stroke-width="3" fill="none" stroke-linejoin="round"/>'
            '<path d="M92,166 l3,8 l3,-8 M102,166 l3,8 l3,-8" fill="#d8d4c8" stroke="#1c1b19" stroke-width="1.5"/>'
            '<circle cx="96" cy="160" r="1.8" fill="#1c1b19"/><circle cx="104" cy="160" r="1.8" fill="#1c1b19"/>')
    if awake:
        out += ('<circle cx="90" cy="148" r="15" fill="url(#eye)"/><circle cx="110" cy="148" r="15" fill="url(#eye)"/>'
                '<path d="M84,146 L95,148 L86,151 Z" fill="#fff6c0"/><path d="M116,146 L105,148 L114,151 Z" fill="#fff6c0"/>')
    else:
        out += '<path d="M84,146 L95,148 L86,151 Z" fill="#1c1b19"/><path d="M116,146 L105,148 L114,151 Z" fill="#1c1b19"/>'
    return out


write("gargula", "estatua", 1, 1, gargula(False), GARG_DEFS)
write("gargula", "desperta", 1, 1, gargula(True), GARG_DEFS)

print("ok")
