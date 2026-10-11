"""Mapa com relevo (altura). Lê mapas/<nome>/layout.txt (terreno, um caractere por quadrado),
altura.txt (um dígito por quadrado, vezes "step" pés) e mapa.json.

Gera:
- <nome>.webp: fundo com sombreado do relevo, linhas de nível, penhascos, árvores, rochas, mato e cascalho;
- cena.json: cena do Foundry com a altura (flags), regiões de terreno difícil, paredes das árvores e rochas
  e os objetos (armadilhas escondidas, pedregulhos, carroça...);
- previa.jpg (o que os jogadores veem) e previa_mestre.jpg (armadilhas, terreno difícil, penhascos e alturas).

Dois quadrados vizinhos com 1 degrau de diferença são encosta (subir custa mais movimento, ver scripts/relevo.js);
com 2 ou mais, penhasco. Mato, cascalho e tronco viram regiões de terreno difícil.
Uso: python3 tools/gen_relevo.py emboscada"""
import json, math, os, random, subprocess, sys, tempfile, pathlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from gen_pecas_mapa import MATERIAIS, wrap, noise as svg_noise, shade

PX = 200       # pixels por quadrado ao desenhar
OUT_PX = 150   # pixels por quadrado no fundo final (mais leve para o canvas)

name = sys.argv[1] if len(sys.argv) > 1 else "emboscada"
DIR = ROOT / "mapas" / name
cfg = json.loads((DIR / "mapa.json").read_text())
rows = [r for r in (DIR / "layout.txt").read_text().splitlines() if r]
alt = [r for r in (DIR / "altura.txt").read_text().splitlines() if r]
H, W = len(rows), len(rows[0])
assert all(len(r) == W for r in rows) and len(alt) == H and all(len(r) == W for r in alt), "layout e altura do mesmo tamanho"
G, STEP = cfg["grid"], cfg.get("step", 5)
SEED = cfg.get("seed", 1)
kind = lambda x, y: cfg["legend"][rows[y][x]]
hg = np.array([[int(c) for c in r] for r in alt], dtype=np.int32)
rng = np.random.default_rng(SEED)
FW, FH = W * PX, H * PX
N4 = [(0, -1), (1, 0), (0, 1), (-1, 0)]


def inside(x, y):
    return 0 <= x < W and 0 <= y < H


# ---------- ruído e desfoque em numpy ----------

def resize(a, w, h, method=Image.BILINEAR):
    return np.asarray(Image.fromarray(a.astype(np.float32), mode="F").resize((w, h), method))


def fnoise(w, h, cells, octaves=4):
    """Ruído suave (0..1) com 'cells' manchas na largura menor."""
    acc = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = max(2, int(cells * 2 ** o))
        grid = rng.random((int(n * h / min(w, h)) + 2, int(n * w / min(w, h)) + 2)).astype(np.float32)
        acc += resize(grid, w, h, Image.BICUBIC) * amp
        tot += amp
        amp *= .5
    acc /= tot
    return (acc - acc.min()) / (acc.max() - acc.min() + 1e-6)


def box(a, r, axis):
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axis, dtype=np.float64)
    hi = [slice(None)] * a.ndim
    lo = [slice(None)] * a.ndim
    hi[axis] = slice(2 * r + 1, None)
    lo[axis] = slice(0, -2 * r - 1)
    return ((c[tuple(hi)] - c[tuple(lo)]) / (2 * r + 1)).astype(np.float32)


def blur(a, sigma):
    r = max(1, int(round(sigma - .5)))
    for _ in range(3):
        a = box(box(a, r, 0), r, 1)
    return a


def smooth(m, n, soft=6.0, amount=.55):
    """Transição orgânica: máscara suave (0..1) + ruído, com borda apertada."""
    return np.clip((m - .5 + (n - .5) * amount) * soft + .5, 0, 1)


# ---------- texturas (SVG renderizado no tamanho do mapa inteiro) ----------

def rocha(w, h, seed=1):
    R = random.Random(seed)
    cracks = "".join(
        f'<path d="M{(x:=R.randint(0,w))},{(y:=R.randint(0,h))} l{R.randint(-30,30)},{R.randint(10,30)} l{R.randint(-24,24)},{R.randint(8,24)}" stroke="#3a3833" stroke-width="2" fill="none" opacity=".55"/>'
        for _ in range(w * h // 9000))
    return wrap(w, h, f'<rect width="{w}" height="{h}" fill="#77736a" filter="url(#ro)"/>{cracks}',
                svg_noise("ro", "0.012", seed, (.42, .4, .36), 1.5, -.5, 5))


def cascalho(w, h, seed=1):
    R = random.Random(seed)
    stones = "".join(
        f'<ellipse cx="{R.randint(0,w)}" cy="{R.randint(0,h)}" rx="{R.randint(3,9)}" ry="{R.randint(2,6)}" fill="{R.choice(["#8a857b","#6f6b63","#a19c91","#5d5a54"])}"/>'
        for _ in range(w * h // 700))
    return wrap(w, h, f'<rect width="{w}" height="{h}" fill="#7d7363" filter="url(#ca)"/>{stones}',
                svg_noise("ca", "0.03", seed, (.38, .34, .28), 1.4, -.5, 4))


def trilha(w, h, seed=1):
    R = random.Random(seed)
    pebbles = "".join(f'<ellipse cx="{R.randint(0,w)}" cy="{R.randint(0,h)}" rx="{R.randint(2,5)}" ry="{R.randint(2,3)}" fill="#8f7f62"/>' for _ in range(w * h // 5000))
    return wrap(w, h, f'<rect width="{w}" height="{h}" fill="#8a7454" filter="url(#tr)"/>{pebbles}',
                svg_noise("tr", "0.025", seed, (.4, .32, .22), 1.4, -.5, 4))


TEX = {"grama": MATERIAIS["grama"], "estrada": MATERIAIS["terra"], "trilha": trilha, "rocha": rocha, "cascalho": cascalho}


def render_svgs(svgs):
    """{nome: svg} → {nome: Image RGBA} usando tools/render.js."""
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        files = []
        for k, s in svgs.items():
            f = pathlib.Path(tmp) / f"{k}.svg"
            f.write_text(s)
            files.append(f)
        env = {**os.environ, "NODE_PATH": subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()}
        subprocess.run(["node", str(ROOT / "tools" / "render.js"), *map(str, files)], check=True, env=env)
        for f in files:
            out[f.stem] = Image.open(f.with_suffix(".png")).convert("RGBA")
    return out


print("texturas...")
# as texturas só mudam com o tamanho e a semente: guarda os PNGs para as próximas rodadas
CACHE = pathlib.Path(tempfile.gettempdir()) / "gen_relevo_cache"
CACHE.mkdir(exist_ok=True)
tex, todo = {}, {}
for i, (k, fn) in enumerate(TEX.items()):
    f = CACHE / f"{k}_{FW}x{FH}_{SEED + i}.png"
    if f.exists():
        tex[k] = Image.open(f).convert("RGBA")
    else:
        todo[k] = fn(FW, FH, SEED + i)
for k, im in render_svgs(todo).items() if todo else []:
    im.save(CACHE / f"{k}_{FW}x{FH}_{SEED + list(TEX).index(k)}.png")
    tex[k] = im
tex = {k: np.asarray(v.convert("RGB"), dtype=np.float32) / 255 for k, v in tex.items()}

# ---------- penhascos (vizinhos com 2 degraus ou mais) ----------
cliffs = []  # (x, y, dx, dy, steps): quadrado alto (x,y), lado baixo na direção (dx,dy)
for y in range(H):
    for x in range(W):
        for dx, dy in N4:
            nx, ny = x + dx, y + dy
            if inside(nx, ny) and hg[y, x] - hg[ny, nx] >= 2:
                cliffs.append((x, y, dx, dy, int(hg[y, x] - hg[ny, nx])))

# ---------- materiais por quadrado ----------
def cell_weights(fn):
    m = np.zeros((H, W), np.float32)
    for y in range(H):
        for x in range(W):
            m[y, x] = fn(x, y)
    return m

road_cols = {x for x in range(W) if all(kind(x, y) in ("estrada", "tronco") for y in range(H))}
wt = {
    "cascalho": cell_weights(lambda x, y: 1 if kind(x, y) == "cascalho" else 0),
    "estrada": cell_weights(lambda x, y: 1 if kind(x, y) == "estrada" or (kind(x, y) == "tronco" and x in road_cols) else 0),
}


def trail_mask():
    """Trilha como uma faixa contínua: liga os quadrados "t" vizinhos (diagonais também) e a ponta à estrada,
    suaviza o caminho e desenha uma linha grossa."""
    ts = {(x, y) for y in range(H) for x in range(W) if kind(x, y) == "trilha"}
    adj = {c: set() for c in ts}
    for x, y in ts:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (x + dx, y + dy)
                if n == (x, y) or n not in ts:
                    continue
                # diagonal só quando não há um caminho reto pelo vizinho comum
                if dx and dy and ((x + dx, y) in ts or (x, y + dy) in ts):
                    continue
                adj[(x, y)].add(n)
    m = Image.new("L", (FW, FH))
    d = ImageDraw.Draw(m)
    seen_e = set()
    for start in sorted(ts, key=lambda c: len(adj[c])):
        for nxt in sorted(adj[start]):
            if frozenset((start, nxt)) in seen_e:
                continue
            path, prev, cur = [start], start, nxt
            seen_e.add(frozenset((start, nxt)))
            while True:
                path.append(cur)
                nx_ = [n for n in adj[cur] if n != prev and frozenset((cur, n)) not in seen_e]
                if len(adj[cur]) != 2 or not nx_:
                    break
                seen_e.add(frozenset((cur, nx_[0])))
                prev, cur = cur, nx_[0]
            pts = [((x + .5) * PX, (y + .5) * PX) for x, y in path]
            # pontas que encostam na estrada entram nela
            for i, (x, y) in ((0, path[0]), (-1, path[-1])):
                for dx, dy in N4:
                    if inside(x + dx, y + dy) and kind(x + dx, y + dy) == "estrada":
                        p = ((x + .5 + dx * .9) * PX, (y + .5 + dy * .9) * PX)
                        pts = [p] + pts if i == 0 else pts + [p]
                        break
            for _ in range(3):  # Chaikin
                pts = [pts[0]] + [q for a, b in zip(pts, pts[1:]) for q in ((a[0] * .75 + b[0] * .25, a[1] * .75 + b[1] * .25),
                                                                           (a[0] * .25 + b[0] * .75, a[1] * .25 + b[1] * .75))] + [pts[-1]]
            d.line(pts, fill=255, width=int(PX * .5), joint="curve")
            for p in (pts[0], pts[-1]):
                d.ellipse((p[0] - PX * .25, p[1] - PX * .25, p[0] + PX * .25, p[1] + PX * .25), fill=255)
    for c in ts:
        if not adj[c]:
            d.ellipse(((c[0] + .2) * PX, (c[1] + .2) * PX, (c[0] + .8) * PX, (c[1] + .8) * PX), fill=255)
    return blur(np.asarray(m, np.float32) / 255, 10)


print("materiais...")
img = tex["grama"].copy()
for k, m in wt.items():
    # o quadrado vira uma mancha que ocupa a área central dele; vizinhos iguais se juntam
    up = resize(np.pad(m, 1, mode="edge"), (W + 2) * PX, (H + 2) * PX)[PX:-PX, PX:-PX]
    n = fnoise(FW, FH, 10 if k == "estrada" else 14)
    a = smooth(up, n, soft=7 if k == "estrada" else 5, amount=.35 if k == "estrada" else .7)
    img = img * (1 - a[..., None]) + tex[k] * a[..., None]
a = smooth(trail_mask(), fnoise(FW, FH, 16), soft=4, amount=.5) * .92
img = img * (1 - a[..., None]) + tex["trilha"] * a[..., None]

# sulcos das rodas na estrada
if road_cols:
    xx = np.arange(FW, dtype=np.float32)[None, :]
    wob = (fnoise(FW, FH, 3, 2) - .5) * 30
    cx = (min(road_cols) + max(road_cols) + 1) / 2 * PX
    road_a = resize(np.pad(wt["estrada"], 1, mode="edge"), (W + 2) * PX, (H + 2) * PX)[PX:-PX, PX:-PX]
    for off in (-52, 52):
        rut = np.clip(1 - np.abs(xx - (cx + off + wob)) / 9, 0, 1) * .28 * np.clip(road_a * 2 - 1, 0, 1)
        img *= 1 - rut[..., None]
    del xx, wob, road_a, rut
del a, n, up

# ---------- penhascos: bordas agrupadas em linhas retas ----------
# chave: (orientação, coordenada da linha, lado baixo) → {índice ao longo: degraus}
lines_ = {}
for x, y, dx, dy, steps in cliffs:
    if dx:
        lines_.setdefault(("v", x + (dx > 0), dx), {})[y] = steps
    else:
        lines_.setdefault(("h", y + (dy > 0), dy), {})[x] = steps


def cliff_profile(cellsteps):
    """Amostras (v, degraus) ao longo da linha: degraus de cada quadrado, transição suave entre quadrados
    e afinando até zero 0,6 quadrado depois das pontas."""
    lo, hi = min(cellsteps), max(cellsteps) + 1
    vs = np.arange((lo - .6) * PX, (hi + .6) * PX + 1, 6, dtype=np.float32)
    raw = np.array([cellsteps.get(int(v // PX), 0) for v in vs], np.float32)
    for i, v in enumerate(vs):
        if v < lo * PX:
            raw[i] = cellsteps[lo] * max(0, 1 - (lo * PX - v) / (.6 * PX))
        elif v >= hi * PX:
            raw[i] = cellsteps[hi - 1] * max(0, 1 - (v - hi * PX) / (.6 * PX))
    k = np.ones(7, np.float32) / 7
    return vs, np.convolve(np.pad(raw, 3, mode="edge"), k, mode="valid")


def jit(v, salt):
    """Recorte irregular (pixels) ao longo de uma borda."""
    return 9 * math.sin(v / 37 + salt) + 6 * math.sin(v / 13 + salt * 2.3) + 3 * math.sin(v / 5.3 + salt * 4.1)


# ---------- relevo: altura suave, sombreado, cor por altura e curvas de nível ----------
print("relevo...")
Q = 50  # pixels por quadrado no cálculo do relevo
Hs = resize(np.pad(hg.astype(np.float32), 1, mode="edge"), (W + 2) * Q, (H + 2) * Q)[Q:-Q, Q:-Q]
Hs = blur(Hs, Q * .12) + (fnoise(W * Q, H * Q, 7, 3) - .5) * .46
# perto dos penhascos o relevo suave vira o desenho do penhasco (sem sombreado nem curvas empilhadas)
near = Image.new("L", (W * Q, H * Q))
nd = ImageDraw.Draw(near)
for (o, c, s), cs in lines_.items():
    a0, a1 = (min(cs) - .3) * Q, (max(cs) + 1.3) * Q
    if o == "v":
        nd.rectangle((c * Q - .45 * Q, a0, c * Q + .45 * Q, a1), fill=255)
    else:
        nd.rectangle((a0, c * Q - .45 * Q, a1, c * Q + .45 * Q), fill=255)
near = blur(np.asarray(near, np.float32) / 255, Q * .08)
gy, gx = np.gradient(Hs)
EXAG = Q * .65  # 1 degrau por quadrado vira uma inclinação suave na luz
nx_, ny_ = -gx * EXAG, -gy * EXAG
L = np.array([-1, -1, 1.6], np.float32)
L /= np.linalg.norm(L)
shade_ = (nx_ * L[0] + ny_ * L[1] + L[2]) / np.sqrt(nx_ ** 2 + ny_ ** 2 + 1)
fac = np.clip(1 + .9 * (shade_ - L[2]), .6, 1.25)
fac = fac * (1 - near) + near
top = max(1, int(hg.max()))
t = np.clip(Hs / top, 0, 1)
fac_full = resize(fac, FW, FH)
img *= fac_full[..., None]
# mais alto = grama mais clara e seca; baixada = mais escura
t_full = resize(t, FW, FH)[..., None]
img *= (1 - t_full) * np.array([.9, .94, .9], np.float32) + t_full * np.array([1.14, 1.1, .88], np.float32)
del fac_full, t_full

# curvas de nível no meio de cada degrau (entre um quadrado e o de cima), finas e com recorte do ruído
g = np.sqrt(gx ** 2 + gy ** 2) + 1e-5
dist = np.abs(Hs - np.floor(Hs) - .5) / g          # pixels (escala Q) até a curva
ok = (1 - near) * np.clip((Hs - .3) * 4, 0, 1)
line_q = resize(dist, FW, FH) * (PX / Q)            # pixels no fundo
lw = 2.8
cont = np.clip(1.3 - line_q / lw, 0, 1) * resize(ok, FW, FH) * .5
img = img * (1 - cont[..., None]) + np.array([.17, .16, .07], np.float32) * cont[..., None]
# realce claro logo acima da curva, como a borda de um degrau
up_ = np.clip(1.3 - np.abs(line_q - 5) / lw, 0, 1) * resize(ok * (Hs - np.floor(Hs) > .5), FW, FH) * .16
img = img * (1 - up_[..., None]) + np.array([.95, .93, .75], np.float32) * up_[..., None]
del Hs, gy, gx, nx_, ny_, shade_, fac, t, g, dist, ok, line_q, cont, up_

# ---------- penhascos: face de rocha no lado baixo, sombra projetada e borda clara no alto ----------
print("penhascos...")
R = random.Random(SEED)
facem = {d: Image.new("L", (FW, FH)) for d in N4}
grad = Image.new("L", (FW, FH))
cast = Image.new("L", (FW, FH))
rim = Image.new("L", (FW, FH))
base_l = Image.new("L", (FW, FH))
facet = Image.new("L", (FW, FH), 128)
crack = Image.new("L", (FW, FH))
fct, crk = ImageDraw.Draw(facet), ImageDraw.Draw(crack)
fd = {d: ImageDraw.Draw(facem[d]) for d in N4}
gd_, cd, rd, bd = ImageDraw.Draw(grad), ImageDraw.Draw(cast), ImageDraw.Draw(rim), ImageDraw.Draw(base_l)
scree = []
for (o, c, s), cs in lines_.items():
    d = (s, 0) if o == "v" else (0, s)
    vs, st = cliff_profile(cs)
    C = c * PX
    salt = C * .013 + (1 if s > 0 else 0)
    width = [(26 + 27 * w if w >= 1 else 53 * w) + jit(v, salt) * min(w, 1) for v, w in zip(vs, st)]
    topj = [3 * math.sin(v / 23 + salt * 3) * min(w, 1) for v, w in zip(vs, st)]
    shadow = [(24 * w if s > 0 else 7 * w) for w in st]

    def P(v, off):
        return (C + s * off, v) if o == "v" else (v, C + s * off)

    top_ = [P(v, j) for v, j in zip(vs, topj)]
    outer = [P(v, j + w_) for v, j, w_ in zip(vs, topj, width)]
    far = [P(v, j + w_ + sh) for v, j, w_, sh in zip(vs, topj, width, shadow)]
    fd[d].polygon(top_ + outer[::-1], fill=255)
    cd.polygon(top_ + far[::-1], fill=150)
    # degradê da face: clara no alto, escura no pé
    for frac, val in ((1, 70), (.66, 140), (.33, 210)):
        gd_.polygon(top_ + [P(v, j + w_ * frac) for v, j, w_ in zip(vs, topj, width)][::-1], fill=val)
    rd.line([P(v, j - 3) for v, j in zip(vs, topj)], fill=255, width=5)
    # facetas: fatias da face com brilho diferente e fendas entre elas
    i = 0
    while i < len(vs) - 1:
        n_ = R.randint(4, 8)
        e = min(i + n_, len(vs) - 1)
        sk = R.uniform(-14, 14)
        poly = top_[i:e + 1] + [P(vs[k_] + sk, topj[k_] + width[k_]) for k_ in range(e, i - 1, -1)]
        fct.polygon(poly, fill=int(128 * R.uniform(.78, 1.2)))
        if st[e] > .5:
            a_, b_ = top_[e], P(vs[e] + sk, topj[e] + width[e] * R.uniform(.5, 1))
            crk.line([a_, b_], fill=255, width=3)
        i = e
    bd.line(outer, fill=255, width=4)
    # pedras soltas no pé do penhasco
    for v, j, w_, ww in zip(vs[::5], topj[::5], width[::5], st[::5]):
        if ww > .6 and R.random() < .8:
            for _ in range(R.randint(1, 3)):
                bx, by = P(v + R.uniform(-15, 15), j + w_ + R.uniform(4, 34))
                scree.append((bx, by, R.uniform(6, 15), R.uniform(4, 10), R.uniform(0, 180)))

cast_a = blur(np.asarray(cast, np.float32) / 255, 12) * .62
img *= (1 - cast_a[..., None])
del cast_a, cast
# luz vem do noroeste: faces viradas para leste/sul ficam na sombra
LIGHT = {(1, 0): .52, (0, 1): .56, (-1, 0): 1.02, (0, -1): .95}
rock = tex["rocha"]
grad_a = blur(np.asarray(grad, np.float32) / 255, 5)
facet_a = blur(np.asarray(facet, np.float32) / 128, 1.5)
crack_a = blur(np.asarray(crack, np.float32) / 255, 1.2)
for d, im_ in facem.items():
    a = blur(np.asarray(im_, np.float32) / 255, 1.5)
    if not a.any():
        continue
    # estrias da rocha correndo junto da borda
    st = fnoise(FW // 10, FH, 30, 3) if d[0] else fnoise(FW, FH // 10, 30, 3)
    st = resize(st, FW, FH)
    col = rock * (LIGHT[d] * facet_a * (.62 + .55 * grad_a) * ((st - .5) * .5 + 1) * (1 - .55 * crack_a))[..., None]
    img = img * (1 - a[..., None]) + col * a[..., None]
del grad_a, facem, grad, facet_a, crack_a, facet, crack
base_a = blur(np.asarray(base_l, np.float32) / 255, 1.5) * .55
img *= (1 - base_a[..., None])
rim_a = blur(np.asarray(rim, np.float32) / 255, 2) * .5
img = img * (1 - rim_a[..., None]) + np.array([.88, .86, .78], np.float32) * rim_a[..., None]
del rim_a, base_a, base_l, rim
img = np.clip(img, 0, 1)

# ---------- árvores, rochas, mato, cascalho e tronco (SVG por cima) ----------
print("detalhes...")
R = random.Random(SEED + 7)
parts, shadows = [], []
cells = [(x, y) for y in range(H) for x in range(W)]
for x, y in cells:
    k = kind(x, y)
    cx, cy = (x + .5) * PX, (y + .5) * PX
    if k == "mato":
        for _ in range(R.randint(6, 9)):
            bx, by, r = cx + R.uniform(-80, 80), cy + R.uniform(-80, 80), R.uniform(22, 40)
            shadows.append(f'<circle cx="{bx+10:.0f}" cy="{by+12:.0f}" r="{r:.0f}"/>')
            parts.append(f'<circle cx="{bx:.0f}" cy="{by:.0f}" r="{r:.0f}" fill="url(#bush)" filter="url(#lf)"/>')
        for _ in range(5):
            bx, by = cx + R.uniform(-85, 85), cy + R.uniform(-85, 85)
            parts.append(f'<path d="M{bx:.0f},{by:.0f} l{R.randint(-14,14)},{R.randint(-14,14)} l{R.randint(-10,10)},{R.randint(-10,10)}" stroke="#2b3a14" stroke-width="2" fill="none"/>')
    elif k == "cascalho":
        for _ in range(R.randint(10, 16)):
            bx, by = cx + R.uniform(-95, 95), cy + R.uniform(-95, 95)
            rx, ry = R.uniform(6, 15), R.uniform(4, 11)
            parts.append(f'<ellipse cx="{bx+3:.0f}" cy="{by+4:.0f}" rx="{rx:.0f}" ry="{ry:.0f}" fill="#000" opacity=".35"/>'
                         f'<ellipse cx="{bx:.0f}" cy="{by:.0f}" rx="{rx:.0f}" ry="{ry:.0f}" fill="{R.choice(["#9b968b","#7d796f","#b0ab9f","#6a665e"])}" stroke="#3c3a35" stroke-width="1.2"/>')
    elif k == "rocha":
        # borda rochosa: alguns blocos de pedra e cascalho miúdo
        for _ in range(R.randint(2, 3)):
            bx, by, rr = cx + R.uniform(-60, 60), cy + R.uniform(-60, 60), R.uniform(22, 38)
            pts = " ".join(f"{bx + (r:=R.uniform(.75, 1.1) * rr) * math.cos(a):.0f},{by + r * .85 * math.sin(a):.0f}" for a in [i / 9 * 2 * math.pi for i in range(9)])
            shadows.append(f'<polygon points="{pts}" transform="translate(8 10)"/>')
            parts.append(f'<polygon points="{pts}" fill="url(#rk)" stroke="#2c2a26" stroke-width="3" filter="url(#rn)"/>')
        for _ in range(R.randint(5, 9)):
            bx, by = cx + R.uniform(-90, 90), cy + R.uniform(-90, 90)
            rx, ry = R.uniform(5, 11), R.uniform(3, 8)
            parts.append(f'<ellipse cx="{bx:.0f}" cy="{by:.0f}" rx="{rx:.0f}" ry="{ry:.0f}" fill="{R.choice(["#9b968b","#7d796f","#b0ab9f"])}" stroke="#3c3a35" stroke-width="1.2"/>')
    elif k == "pedra":
        pts = " ".join(f"{cx + (r:=R.uniform(62, 82)) * math.cos(a):.0f},{cy + r * .9 * math.sin(a):.0f}" for a in [i / 12 * 2 * math.pi for i in range(12)])
        shadows.append(f'<polygon points="{pts}" transform="translate(16 18)"/>')
        parts.append(f'<polygon points="{pts}" fill="url(#rk)" stroke="#2c2a26" stroke-width="4" filter="url(#rn)"/>')
        for _ in range(3):
            bx, by = cx + R.uniform(-40, 40), cy + R.uniform(-40, 40)
            parts.append(f'<path d="M{bx:.0f},{by:.0f} l{R.randint(-24,24)},{R.randint(10,24)}" stroke="#3a3732" stroke-width="2.5" opacity=".7"/>')

for bx, by, rx, ry, ang in scree:
    parts.append(f'<ellipse cx="{bx+3:.0f}" cy="{by+4:.0f}" rx="{rx:.0f}" ry="{ry:.0f}" fill="#000" opacity=".35" transform="rotate({ang:.0f} {bx:.0f} {by:.0f})"/>'
                 f'<ellipse cx="{bx:.0f}" cy="{by:.0f}" rx="{rx:.0f}" ry="{ry:.0f}" fill="{R.choice(["#8d897f","#77736a","#a19c91"])}" stroke="#3c3a35" stroke-width="1.5" transform="rotate({ang:.0f} {bx:.0f} {by:.0f})"/>')

# tronco caído: uma tora só, de ponta a ponta dos quadrados "="
logs = [(x, y) for x, y in cells if kind(x, y) == "tronco"]
if logs:
    y = logs[0][1]
    x0, x1 = min(x for x, _ in logs) * PX + 30, (max(x for x, _ in logs) + 1) * PX - 30
    cy = (y + .5) * PX
    shadows.append(f'<rect x="{x0+14}" y="{cy-34+18}" width="{x1-x0}" height="72" rx="36"/>')
    parts.append(f'<rect x="{x0}" y="{cy-36}" width="{x1-x0}" height="72" rx="34" fill="url(#bark)" stroke="#2a1a0c" stroke-width="5" filter="url(#bk)"/>')
    for i in range(int((x1 - x0) / 46)):
        bx = x0 + 30 + i * 46 + R.randint(-10, 10)
        parts.append(f'<path d="M{bx},{cy-30} q{R.randint(-8,8)},30 0,60" stroke="#3b2614" stroke-width="2.5" fill="none" opacity=".7"/>')
    for bx in (x0 + 140, x0 + 420, x1 - 260):
        parts.append(f'<path d="M{bx},{cy-30} l{R.randint(-30,30)},-60" stroke="#4a3018" stroke-width="12" stroke-linecap="round"/>')
    parts.append(f'<ellipse cx="{x1-6}" cy="{cy}" rx="22" ry="34" fill="#b08a5a" stroke="#4a3018" stroke-width="4"/>'
                 f'<ellipse cx="{x1-6}" cy="{cy}" rx="12" ry="20" fill="none" stroke="#7a5a32" stroke-width="2"/>')

# árvores por último: a copa cobre um pouco os vizinhos
for x, y in cells:
    if kind(x, y) != "arvore":
        continue
    cx, cy = (x + .5) * PX, (y + .5) * PX
    shadows.append(f'<circle cx="{cx+34:.0f}" cy="{cy+40:.0f}" r="135"/>')
    blobs = [(cx + R.uniform(-55, 55), cy + R.uniform(-55, 55), R.uniform(55, 80)) for _ in range(7)]
    parts.append("".join(f'<circle cx="{bx:.0f}" cy="{by:.0f}" r="{r:.0f}" fill="url(#leaf{R.randint(0,1)})" filter="url(#lf)"/>' for bx, by, r in blobs))
    parts.append(f'<circle cx="{cx-28:.0f}" cy="{cy-30:.0f}" r="42" fill="#9fc062" opacity=".22"/>')

defs = ('<filter id="sh" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="14"/></filter>'
        '<radialGradient id="bush" cx=".4" cy=".35"><stop offset="0" stop-color="#6f8f3a"/><stop offset="1" stop-color="#2e4418"/></radialGradient>'
        '<radialGradient id="leaf0" cx=".4" cy=".35"><stop offset="0" stop-color="#5f8a34"/><stop offset=".7" stop-color="#2f5a1e"/><stop offset="1" stop-color="#1d3a12"/></radialGradient>'
        '<radialGradient id="leaf1" cx=".4" cy=".35"><stop offset="0" stop-color="#6e8f2e"/><stop offset=".7" stop-color="#3a5a1a"/><stop offset="1" stop-color="#22380e"/></radialGradient>'
        '<radialGradient id="rk" cx=".38" cy=".34" r=".75"><stop offset="0" stop-color="#a7a39a"/><stop offset=".55" stop-color="#77736a"/><stop offset="1" stop-color="#46433d"/></radialGradient>'
        '<linearGradient id="bark" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7a5532"/><stop offset=".5" stop-color="#5c3d20"/><stop offset="1" stop-color="#3a2512"/></linearGradient>'
        + svg_noise("lf", "0.08", 3, (.12, .2, .06), 1.2, -.45)
        + svg_noise("rn", "0.06", 5, (.36, .35, .32), 1.1, -.4)
        + svg_noise("bk", "0.01 0.2", 8, (.2, .12, .05), 1.3, -.4))
over_svg = wrap(FW, FH, f'<g fill="#000" opacity=".42" filter="url(#sh)">{"".join(shadows)}</g>{"".join(parts)}', defs)
over = render_svgs({"over": over_svg})["over"]

base = Image.fromarray((img * 255).astype(np.uint8), "RGB").convert("RGBA")
del img
base.alpha_composite(over)

# ---------- altura escrita nos platôs ----------
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
draw = ImageDraw.Draw(base)
seen = set()
BUSY = {"arvore", "pedra", "mato", "cascalho", "tronco"}
for y0 in range(H):
    for x0 in range(W):
        if (x0, y0) in seen or hg[y0, x0] < 2:
            continue
        comp, todo = [], [(x0, y0)]
        seen.add((x0, y0))
        while todo:
            x, y = todo.pop()
            comp.append((x, y))
            for dx, dy in N4:
                n = (x + dx, y + dy)
                if inside(*n) and n not in seen and hg[n[1], n[0]] == hg[y0, x0]:
                    seen.add(n)
                    todo.append(n)
        if len(comp) < 6:
            continue
        mx, my = sum(c[0] for c in comp) / len(comp), sum(c[1] for c in comp) / len(comp)
        free = [c for c in comp if kind(*c) not in BUSY] or comp
        x, y = min(free, key=lambda c: (c[0] - mx) ** 2 + (c[1] - my) ** 2)
        draw.text(((x + .5) * PX, (y + .5) * PX), f"{hg[y0, x0] * STEP} pés", font=font, anchor="mm",
                  fill=(250, 246, 232, 230), stroke_width=4, stroke_fill=(30, 24, 16, 220))

bg_name = f"{name}.webp"
final = base.convert("RGB").resize((W * OUT_PX, H * OUT_PX), Image.LANCZOS)
final.save(DIR / bg_name, quality=86, method=6)
print("fundo", final.size)

# ---------- cena ----------
def rects(cellset):
    """Junta quadrados em retângulos: faixas por linha, depois faixas iguais de linhas seguidas."""
    runs = {}
    for y in range(H):
        x = 0
        while x < W:
            if (x, y) in cellset:
                s = x
                while x < W and (x, y) in cellset:
                    x += 1
                runs.setdefault((s, x), []).append(y)
            else:
                x += 1
    out = []
    for (s, e), ys in runs.items():
        ys.sort()
        a = ys[0]
        for i in range(1, len(ys) + 1):
            if i == len(ys) or ys[i] != ys[i - 1] + 1:
                out.append((s, a, e - s, ys[i - 1] - a + 1))
                if i < len(ys):
                    a = ys[i]
    return out

DIFF = cfg.get("difficult", {})
cat = {}
for y in range(H):
    for x in range(W):
        k = kind(x, y)
        if k == "tronco":
            cat[(x, y)] = "tronco"
        elif k == "mato":
            cat[(x, y)] = "mato"
        elif k == "cascalho":
            cat[(x, y)] = "cascalho"
regions = []
for c, info in DIFF.items():
    cs = {p for p, v in cat.items() if v == c}
    if not cs:
        continue
    regions.append({
        "name": info["name"], "color": info.get("color", "#c8a050"), "visibility": 0,
        "shapes": [{"type": "rectangle", "x": x * G, "y": y * G, "width": w * G, "height": h * G, "rotation": 0, "hole": False}
                   for x, y, w, h in rects(cs)],
        "flags": {"interactive-assets": {"terreno": info.get("type", "")}}
    })

def octagon(cx, cy, r):
    pts = [(cx + r * math.cos(math.pi / 8 + i * math.pi / 4), cy + r * math.sin(math.pi / 8 + i * math.pi / 4)) for i in range(8)]
    return [{"c": [round(a[0]), round(a[1]), round(b[0]), round(b[1])], "move": 20, "sight": 0, "light": 0, "sound": 0}
            for a, b in zip(pts, pts[1:] + pts[:1])]

walls = []
for x, y in cells:
    if kind(x, y) == "arvore":
        walls += octagon((x + .5) * G, (y + .5) * G, .22 * G)
    elif kind(x, y) == "pedra":
        walls += octagon((x + .5) * G, (y + .5) * G, .38 * G)

scene = {
    "name": cfg["name"],
    "width": W * G, "height": H * G, "padding": 0,
    "backgroundColor": "#1b1b1b",
    "background": {"src": f"mapas/{name}/{bg_name}"},
    "grid": {"type": 1, "size": G, "distance": STEP, "units": "ft"},
    "tokenVision": True,
    "environment": {"darknessLevel": cfg.get("darkness", 0), "globalLight": {"enabled": True}},
    "lights": cfg.get("lights", []),
    "sounds": [{**s, "walls": True, "easing": True} for s in cfg.get("sounds", [])],
    "walls": walls,
    "regions": regions,
    "flags": {"interactive-assets": {"map": {
        "cols": W, "rows": H, "fixed": [], "structures": [], "objects": cfg.get("objects", []),
        "relevo": {"step": STEP, "height": alt, "climbDC": cfg.get("climbDC", 12),
                   "trail": ["".join("1" if kind(x, y) == "trilha" else "0" for x in range(W)) for y in range(H)]}}}},
}
(DIR / "cena.json").write_text(json.dumps(scene, indent=1, ensure_ascii=False))

# ---------- prévias ----------
ASSETS = json.loads((ROOT / "assets" / "assets.json").read_text())
K = .25
f = PX * K


def put_objects(im, gm):
    for o in cfg.get("objects", []):
        if o.get("hidden") and not gm:
            continue
        d = ASSETS[o["asset"]]
        t = Image.open(ROOT / "assets" / d["states"][0]["src"].replace(".webm", ".png")).convert("RGBA")
        w, h = int(d["size"]["w"] * f), int(d["size"]["h"] * f)
        t = t.resize((w, h))
        if o.get("hidden"):
            t.putalpha(t.getchannel("A").point(lambda v: int(v * .75)))
        im.alpha_composite(t, (int(o["x"] / G * f - w / 2), int(o["y"] / G * f - h / 2)))


small = base.resize((int(FW * K), int(FH * K)), Image.LANCZOS)
prev = small.copy()
put_objects(prev, False)
prev.convert("RGB").save(DIR / "previa.jpg", quality=85)

gm = small.copy()
ov = Image.new("RGBA", gm.size)
od = ImageDraw.Draw(ov)
for r in regions:
    col = tuple(int(r["color"][i:i + 2], 16) for i in (1, 3, 5))
    for s in r["shapes"]:
        x, y, w, h = s["x"] / G * f, s["y"] / G * f, s["width"] / G * f, s["height"] / G * f
        od.rectangle((x, y, x + w - 1, y + h - 1), fill=col + (70,))
        for i in range(int(-h), int(w), 10):  # hachura
            od.line([(x + max(i, 0), y + max(-i, 0)), (x + min(i + h, w), y + min(h, w - i))], fill=col + (120,), width=1)
gm.alpha_composite(ov)
put_objects(gm, True)
gd = ImageDraw.Draw(gm)
for x, y, dx, dy, steps in cliffs:
    if dx:
        X = ((x + 1) if dx > 0 else x) * f
        gd.line([(X, y * f), (X, (y + 1) * f)], fill=(230, 40, 40), width=3)
    else:
        Y = ((y + 1) if dy > 0 else y) * f
        gd.line([(x * f, Y), ((x + 1) * f, Y)], fill=(230, 40, 40), width=3)
small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 11)
for x, y in cells:
    gd.text((x * f + 3, y * f + 2), str(hg[y, x] * STEP), font=small_font, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
for o in cfg.get("objects", []):
    roll = (o.get("flags") or {}).get("roll")
    if roll:
        a = (o["x"] / G * f, o["y"] / G * f)
        b = ((roll["x"] + .5) * f, (roll["y"] + .5) * f)
        gd.line([a, b], fill=(255, 200, 40), width=3)
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        gd.polygon([b, (b[0] - 14 * math.cos(ang - .4), b[1] - 14 * math.sin(ang - .4)),
                    (b[0] - 14 * math.cos(ang + .4), b[1] - 14 * math.sin(ang + .4))], fill=(255, 200, 40))
    link = (o.get("flags") or {}).get("link")
    if link:
        gd.line([(o["x"] / G * f, o["y"] / G * f), ((link["x"] + .5) * f, (link["y"] + .5) * f)], fill=(255, 120, 200), width=2)
gm.convert("RGB").save(DIR / "previa_mestre.jpg", quality=85)
print(f"{name}: {W}x{H} quadrados, {len(cliffs)} bordas de penhasco, {len(regions)} regiões, {len(walls)} paredes")
