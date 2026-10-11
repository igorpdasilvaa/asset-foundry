"""Gera os SVGs da água (1 quadrado), da carroça (2 x 3) e do barco a remo (4 x 2) em assets/<nome>/,
e a animação da água eletrificada (WebM com transparência). 1 quadrado = 200 px.
Uso: python3 tools/gen_agua_veiculos.py && NODE_PATH=$(npm root -g) node tools/render.js assets/{agua,carroca,barco}/*.svg"""
import math, os, random, pathlib, subprocess, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gen_pecas_mapa import noise, shade

ROOT = pathlib.Path(__file__).resolve().parent.parent
A = ROOT / "assets"
S = 200

COMMON = (
    '<filter id="bl4" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter>'
    '<filter id="bl8" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="8"/></filter>'
    '<filter id="bl16" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="16"/></filter>'
    '<radialGradient id="glow"><stop offset="0" stop-color="#ffb347" stop-opacity=".75"/><stop offset=".6" stop-color="#ff5a1a" stop-opacity=".3"/><stop offset="1" stop-color="#ff5a1a" stop-opacity="0"/></radialGradient>'
    '<radialGradient id="soot"><stop offset="0" stop-color="#0b0908" stop-opacity=".9"/><stop offset=".7" stop-color="#1a1410" stop-opacity=".55"/><stop offset="1" stop-color="#1a1410" stop-opacity="0"/></radialGradient>'
)


def svg(w, h, body, defs=""):
    # width/height = metade: o render.js usa escala 2, então o PNG sai com 200 px por quadrado
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w//2}" height="{h//2}" viewBox="0 0 {w} {h}">'
            f'<defs>{COMMON}{defs}</defs>{body}</svg>')


def write(folder, name, w, h, body, defs=""):
    d = A / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.svg").write_text(svg(w, h, body, defs))


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


def embers(R, x0, y0, x1, y1, n=14):
    return '<g opacity=".75">' + "".join(
        f'<circle cx="{R.uniform(x0,x1):.0f}" cy="{R.uniform(y0,y1):.0f}" r="{R.uniform(1.2,3):.1f}" fill="#ff7b2e"/>' for _ in range(n)) + '</g>'


def splinters(R, n, cx, cy, sx, sy, colors=("#74482a",)):
    out = ""
    for _ in range(n):
        x, y = cx + R.gauss(0, sx), cy + R.gauss(0, sy)
        L, a = R.uniform(12, 40), R.uniform(0, math.pi)
        out += f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{x+L*math.cos(a):.0f}" y2="{y+L*math.sin(a):.0f}" stroke="{R.choice(colors)}" stroke-width="{R.uniform(3,7):.1f}" stroke-linecap="round"/>'
    return out


def tiled(n, R, fn):
    """Desenha n elementos e repete os que encostam na borda do outro lado: o quadrado emenda com o vizinho."""
    out = ""
    for _ in range(n):
        x, y = R.uniform(0, S), R.uniform(0, S)
        params = fn(R)
        for dx in (-S, 0, S):
            for dy in (-S, 0, S):
                out += params(x + dx, y + dy)
    return out


# Ruído que se repete a cada 200 px (stitchTiles), para os quadrados de água emendarem sem costura.
def stitched(fid, freq, seed, rgb, alpha, off, octaves=3):
    r, g, b = rgb
    return (f'<filter id="{fid}" x="0" y="0" width="200" height="200" filterUnits="userSpaceOnUse">'
            f'<feTurbulence type="fractalNoise" baseFrequency="{freq}" numOctaves="{octaves}" seed="{seed}" stitchTiles="stitch" result="n"/>'
            f'<feColorMatrix type="matrix" values="0 0 0 0 {r}  0 0 0 0 {g}  0 0 0 0 {b}  0 0 0 {alpha} {off}" in="n"/></filter>')


# ======================= ÁGUA (1 quadrado, por cima da água pintada no fundo do mapa) =======================

def ripple(R):
    rx, op = R.uniform(10, 26), R.uniform(.18, .35)
    return lambda x, y: (f'<path d="M{x-rx:.0f},{y:.0f} Q{x:.0f},{y-rx*.35:.0f} {x+rx:.0f},{y:.0f}" stroke="#e8f6ff" '
                         f'stroke-width="2" fill="none" opacity="{op:.2f}" stroke-linecap="round"/>')


R = random.Random(3)
calma = '<rect width="200" height="200" fill="#2b6f8a" opacity=".08"/>' + tiled(9, R, ripple)
write("agua", "agua_calma", S, S, calma)

# Gelo: placa opaca com geada, rachaduras finas e bolhas presas.
R = random.Random(4)
ice_cracks = ""
for _ in range(4):
    x, y, ang = R.uniform(30, 170), R.uniform(30, 170), R.uniform(0, 2 * math.pi)
    d = f"M{x:.0f},{y:.0f}"
    for _ in range(4):
        ang += R.uniform(-.7, .7)
        L = R.uniform(12, 26)
        x, y = min(max(x + L * math.cos(ang), 4), 196), min(max(y + L * math.sin(ang), 4), 196)
        d += f" L{x:.0f},{y:.0f}"
    ice_cracks += f'<path d="{d}" stroke="#ffffff" stroke-width="1.6" fill="none" opacity=".75"/><path d="{d}" stroke="#5c8fa8" stroke-width=".8" fill="none" opacity=".6" transform="translate(1.2 1.2)"/>'
bubbles = tiled(10, R, lambda R: (lambda r: lambda x, y: f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="#ffffff" opacity=".45"/>')(R.uniform(1.5, 4)))
write("agua", "agua_congelada", S, S,
      '<rect width="200" height="200" fill="#bfe3f2" opacity=".9"/>'
      '<rect width="200" height="200" filter="url(#frost)"/>' + bubbles + ice_cracks,
      stitched("frost", "0.035", 8, (1, 1, 1), 1.6, -.55))

# Vapor: névoa branca que emenda com os vizinhos.
R = random.Random(5)
mist = tiled(7, R, lambda R: (lambda r, op: lambda x, y: f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.0f}" fill="#f4f7f8" opacity="{op:.2f}" filter="url(#bl16)"/>')(R.uniform(40, 70), R.uniform(.3, .5)))
write("agua", "agua_vapor", S, S, '<rect width="200" height="200" fill="#dfe8ea" opacity=".3"/>' + mist)

# Envenenada: verde turvo, manchas e bolhas.
R = random.Random(6)
blobs = tiled(8, R, lambda R: (lambda r: lambda x, y: f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="#a8d84a" opacity=".55" stroke="#3a5a0e" stroke-width="1.2"/>')(R.uniform(2, 6)))
write("agua", "agua_envenenada", S, S,
      '<rect width="200" height="200" fill="#2f4a12" opacity=".6"/>'
      '<rect width="200" height="200" filter="url(#sludge)"/>' + blobs,
      stitched("sludge", "0.04", 9, (.42, .62, .1), 1.3, -.55))


# Eletrificada: raios que mudam a cada quadro (animação) por cima de um brilho azul.
def bolt(R):
    side = R.randint(0, 3)
    pts = {0: (R.uniform(20, 180), 0), 1: (200, R.uniform(20, 180)), 2: (R.uniform(20, 180), 200), 3: (0, R.uniform(20, 180))}
    (x, y), (x2, y2) = pts[side], pts[(side + R.choice([1, 2, 3])) % 4]
    d = f"M{x:.0f},{y:.0f}"
    for i in range(1, 7):
        t = i / 7
        d += f" L{x+(x2-x)*t+R.uniform(-18,18):.0f},{y+(y2-y)*t+R.uniform(-18,18):.0f}"
    d += f" L{x2:.0f},{y2:.0f}"
    return (f'<path d="{d}" stroke="#7fd4ff" stroke-width="7" fill="none" opacity=".55" filter="url(#bl4)"/>'
            f'<path d="{d}" stroke="#ffffff" stroke-width="2.2" fill="none" stroke-linejoin="round"/>')


def zap_frame(seed):
    R = random.Random(seed)
    return ('<rect width="200" height="200" fill="#3fa9e8" opacity=".28"/>'
            + "".join(bolt(R) for _ in range(R.randint(1, 2)))
            + "".join(f'<circle cx="{R.uniform(10,190):.0f}" cy="{R.uniform(10,190):.0f}" r="{R.uniform(1.5,3):.1f}" fill="#e8f8ff"/>' for _ in range(6)))


write("agua", "agua_eletrificada", S, S, zap_frame(100))


def zap_video():
    env = {**os.environ, "NODE_PATH": subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()}
    with tempfile.TemporaryDirectory() as tmp:
        files = []
        for i in range(8):
            f = pathlib.Path(tmp) / f"f{i:02d}.svg"
            f.write_text(svg(S, S, zap_frame(100 + i)))
            files.append(str(f))
        subprocess.run(["node", str(ROOT / "tools" / "render.js"), *files], check=True, env=env)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "12", "-i", f"{tmp}/f%02d.png",
                        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "0", "-crf", "32",
                        str(A / "agua" / "agua_eletrificada.webm")], check=True)


# ======================= CARROÇA (2 x 3 quadrados = 400 x 600, frente para cima) =======================
CW, CH = 400, 600
CART_DEFS = (noise("wg", "0.25 0.008", 6, (.22, .12, .05))
             + '<linearGradient id="tilt" x1="0" x2="1"><stop offset="0" stop-color="#000" stop-opacity=".45"/><stop offset=".6" stop-color="#000" stop-opacity="0"/></linearGradient>')


def wheel(x, y, broken=False):
    if broken:
        return ''
    return (f'<rect x="{x}" y="{y}" width="30" height="104" rx="8" fill="#3b2412" stroke="#1c120c" stroke-width="3"/>'
            f'<rect x="{x-2}" y="{y+4}" width="34" height="8" fill="#4a4a4e"/><rect x="{x-2}" y="{y+92}" width="34" height="8" fill="#4a4a4e"/>'
            + "".join(f'<line x1="{x+3}" y1="{y+yy}" x2="{x+27}" y2="{y+yy}" stroke="#1c120c" stroke-width="2"/>' for yy in (30, 52, 74)))


def cart(color="#7a4d28", broken_wheel=False):
    planks = "".join(f'<rect x="{78+i*41}" y="150" width="41" height="430" fill="{shade(color, k)}"/>'
                     for i, k in enumerate([1, .9, 1.06, .94, 1.02, .9]))
    seams = "".join(f'<line x1="{78+i*41}" y1="150" x2="{78+i*41}" y2="580"/>' for i in range(1, 6))
    w = (wheel(40, 190, broken_wheel) + wheel(330, 190) + wheel(40, 440) + wheel(330, 440))
    return (f'<rect x="60" y="150" width="290" height="440" rx="10" fill="#000" opacity=".45" filter="url(#bl8)"/>'
            # cabeçalho (lança) e balancim para os cavalos
            f'<rect x="191" y="14" width="18" height="150" rx="4" fill="#5a3a20" stroke="#2a180a" stroke-width="3"/>'
            f'<rect x="120" y="38" width="160" height="14" rx="4" fill="#5a3a20" stroke="#2a180a" stroke-width="3"/>'
            f'<circle cx="128" cy="45" r="4" fill="#4a4a4e"/><circle cx="272" cy="45" r="4" fill="#4a4a4e"/>'
            # eixos
            f'<rect x="40" y="236" width="320" height="12" fill="#2e2e30"/><rect x="40" y="486" width="320" height="12" fill="#2e2e30"/>'
            + w +
            f'<g filter="url(#wg)">{planks}</g><g stroke="#2a180a" stroke-width="2.5">{seams}</g>'
            # laterais (bordas da carroceria)
            f'<rect x="70" y="142" width="268" height="446" rx="6" fill="none" stroke="{shade(color, .62)}" stroke-width="16"/>'
            f'<rect x="62" y="134" width="284" height="462" rx="8" fill="none" stroke="#2a180a" stroke-width="3"/>'
            f'<rect x="78" y="150" width="252" height="430" fill="none" stroke="#2a180a" stroke-width="2.5"/>'
            # cantoneiras de ferro e banco do condutor
            + "".join(f'<rect x="{x}" y="{y}" width="22" height="22" fill="none" stroke="#4a4a4e" stroke-width="5"/>' for x in (62, 324) for y in (134, 574))
            + f'<rect x="90" y="168" width="228" height="34" rx="5" fill="{shade(color, 1.15)}" stroke="#2a180a" stroke-width="3"/>')


write("carroca", "carroca_inteira", CW, CH, cart(), CART_DEFS)
R = random.Random(51)
loose = (f'<g transform="translate(18 300) rotate(-28)">{wheel(0, 0)}</g>'
         + splinters(R, 7, 40, 250, 18, 26, ("#3b2412", "#5a3a20")))
write("carroca", "carroca_roda_quebrada", CW, CH,
      cart(broken_wheel=True) + '<rect x="62" y="134" width="284" height="462" rx="8" fill="url(#tilt)"/>' + loose
      + '<path d="M84,190 L120,214 L104,250 L138,282" stroke="#1c120c" stroke-width="3" fill="none"/>', CART_DEFS)
R = random.Random(52)
write("carroca", "carroca_queimando", CW, CH,
      cart("#5a3a20") + soot(R, 200, 300, 110) + soot(R, 220, 470, 90)
      + flames(R, 190, 300, 70, 7, 1.6) + flames(R, 230, 470, 60, 6, 1.4) + flames(R, 160, 180, 30, 3), CART_DEFS)
R = random.Random(53)
holes = "".join(f'<ellipse cx="{R.uniform(110,300):.0f}" cy="{R.uniform(190,560):.0f}" rx="{R.uniform(16,34):.0f}" ry="{R.uniform(20,50):.0f}" fill="#0b0908"/>' for _ in range(5))
write("carroca", "carroca_queimada", CW, CH,
      cart("#2a1a10").replace("#3b2412", "#1a120c").replace("#5a3a20", "#24160e")
      + '<rect x="62" y="134" width="284" height="462" rx="8" fill="#0b0908" opacity=".45"/>' + holes
      + soot(R, 200, 360, 160) + embers(R, 90, 160, 320, 570, 22), CART_DEFS)
R = random.Random(54)
boards = "".join(
    f'<g transform="translate({200+R.gauss(0,90):.0f} {330+R.gauss(0,140):.0f}) rotate({R.uniform(0,180):.0f})">'
    f'<rect x="-{(L:=R.randint(70,180))/2}" y="-18" width="{L}" height="36" fill="{shade("#7a4d28", R.uniform(.8,1.1))}" stroke="#2a180a" stroke-width="3"/></g>'
    for _ in range(9))
lying = "".join(
    f'<g transform="translate({x} {y})"><circle r="52" fill="none" stroke="#3b2412" stroke-width="12"/><circle r="52" fill="none" stroke="#4a4a4e" stroke-width="3"/>'
    + "".join(f'<line x1="0" y1="0" x2="{46*math.cos(a):.0f}" y2="{46*math.sin(a):.0f}" stroke="#3b2412" stroke-width="7"/>' for a in [i * math.pi / 4 + .3 for i in range(8)])
    + '<circle r="11" fill="#4a4a4e" stroke="#1c120c" stroke-width="3"/></g>' for x, y in ((100, 140), (300, 470)))
write("carroca", "carroca_destruida", CW, CH,
      '<rect x="40" y="30" width="320" height="540" rx="40" fill="#000" opacity=".25" filter="url(#bl16)"/>'
      + '<rect x="40" y="236" width="320" height="12" fill="#2e2e30" transform="rotate(14 200 242)"/>'
      + boards + lying + splinters(R, 20, 200, 320, 90, 150, ("#5a3a20", "#7a4d28", "#2a180a")), CART_DEFS)


# ======================= BARCO A REMO (4 x 2 quadrados = 800 x 400, proa à direita) =======================
BW, BH = 800, 400
HULL = "M70,200 C70,110 120,72 260,66 L540,66 C660,66 740,130 778,200 C740,270 660,334 540,334 L260,334 C120,328 70,290 70,200 Z"
INNER = "M92,200 C92,124 134,92 264,88 L536,88 C644,88 712,142 746,200 C712,258 644,312 536,312 L264,312 C134,308 92,276 92,200 Z"
BOAT_DEFS = (f'<clipPath id="in"><path d="{INNER}"/></clipPath><clipPath id="hull"><path d="{HULL}"/></clipPath>'
             + noise("bw", "0.006 0.2", 7, (.22, .12, .05))
             + '<radialGradient id="pool" cx=".3" cy=".5" r=".6"><stop offset="0" stop-color="#2c6f8c" stop-opacity=".85"/><stop offset="1" stop-color="#2c6f8c" stop-opacity=".25"/></radialGradient>')


def oar(x, y, ang):
    return (f'<g transform="translate({x} {y}) rotate({ang})">'
            f'<rect x="-6" y="0" width="12" height="150" rx="5" fill="#9a6a3c" stroke="#2a180a" stroke-width="2.5"/>'
            f'<path d="M-14,120 L14,120 L18,190 Q0,200 -18,190 Z" fill="#a8774a" stroke="#2a180a" stroke-width="2.5"/></g>')


def boat(color="#7a4d28", oars=True, water=0):
    strakes = "".join(f'<rect x="0" y="{60+i*36}" width="800" height="36" fill="{shade(color, k)}"/>'
                      for i, k in enumerate([.92, 1.04, .96, 1.08, .94, 1.02, .9, 1]))
    lines = "".join(f'<line x1="60" y1="{60+i*36}" x2="790" y2="{60+i*36}"/>' for i in range(1, 8))
    ribs = "".join(f'<line x1="{x}" y1="80" x2="{x}" y2="320"/>' for x in range(160, 720, 70))
    pool = f'<g clip-path="url(#in)"><rect x="60" y="60" width="{60+water}" height="300" fill="url(#pool)"/></g>' if water else ""
    thwarts = "".join(f'<rect x="{x}" y="84" width="34" height="232" fill="{shade(color, 1.2)}" stroke="#2a180a" stroke-width="3"/>' for x in (200, 410, 590))
    return (f'<path d="{HULL}" fill="#000" opacity=".4" filter="url(#bl8)" transform="translate(8 12)"/>'
            + (oar(420, 70, 160) + oar(440, 330, 20) if oars else "")
            + f'<path d="{HULL}" fill="{shade(color, .7)}" stroke="#2a180a" stroke-width="4"/>'
            f'<g clip-path="url(#in)"><g filter="url(#bw)">{strakes}</g><g stroke="#2a180a" stroke-width="2">{lines}</g>'
            f'<g stroke="#3b2412" stroke-width="5" opacity=".55">{ribs}</g></g>' + pool + thwarts
            + f'<path d="{INNER}" fill="none" stroke="#2a180a" stroke-width="3"/>'
            '<circle cx="430" cy="78" r="6" fill="#4a4a4e"/><circle cx="430" cy="322" r="6" fill="#4a4a4e"/>'
            '<path d="M746,200 L790,200" stroke="#2a180a" stroke-width="6"/><circle cx="790" cy="200" r="6" fill="#4a4a4e"/>')


write("barco", "barco_inteiro", BW, BH, boat(), BOAT_DEFS)
R = random.Random(61)
breach = ('<path d="M150,250 L176,232 L190,252 L214,240 L222,268 L196,286 L170,280 Z" fill="#0d2430" stroke="#1c120c" stroke-width="3"/>'
          + splinters(R, 8, 186, 262, 22, 16, ("#5a3a20", "#7a4d28")))
write("barco", "barco_avariado", BW, BH, boat(water=260) + breach, BOAT_DEFS)
R = random.Random(62)
write("barco", "barco_queimando", BW, BH,
      boat("#5a3a20") + soot(R, 330, 200, 110) + soot(R, 560, 200, 90)
      + flames(R, 320, 210, 80, 8, 1.6) + flames(R, 560, 210, 60, 6, 1.4), BOAT_DEFS)
R = random.Random(63)
burnt = (boat("#2a1a10", oars=False, water=420).replace("#9a6a3c", "#24160e")
         + f'<path d="{HULL}" fill="#0b0908" opacity=".4"/>'
         + soot(R, 420, 200, 200) + embers(R, 140, 100, 700, 300, 26)
         # bordas comidas pelo fogo
         + "".join(f'<ellipse cx="{x}" cy="{y}" rx="{R.uniform(24,44):.0f}" ry="{R.uniform(10,18):.0f}" fill="#0d2430"/>'
                   for x, y in ((300, 70), (520, 66), (380, 332), (640, 300))))
write("barco", "barco_queimado", BW, BH, burnt, BOAT_DEFS)
R = random.Random(64)
sunk = (f'<g opacity=".38">{boat(oars=False)}</g>'
        f'<path d="{HULL}" fill="#1f5a73" opacity=".55"/>'
        + "".join(f'<ellipse cx="{x}" cy="{y}" rx="{r}" ry="{r*.6:.0f}" fill="none" stroke="#dff3ff" stroke-width="2" opacity=".5"/>'
                  for x, y, r in ((300, 180, 40), (300, 180, 70), (560, 230, 30), (560, 230, 56)))
        + "".join(f'<circle cx="{R.uniform(150,700):.0f}" cy="{R.uniform(110,290):.0f}" r="{R.uniform(2,5):.1f}" fill="#e8f8ff" opacity=".7"/>' for _ in range(16))
        + oar(640, 40, 70) + '<rect x="120" y="300" width="70" height="20" rx="4" fill="#9a6a3c" stroke="#2a180a" stroke-width="2.5" transform="rotate(-12 155 310)"/>')
write("barco", "barco_afundado", BW, BH, sunk, BOAT_DEFS)

if "--sem-video" not in sys.argv:
    zap_video()
print("ok")
