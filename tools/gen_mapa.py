"""Monta um mapa a partir das peças de mapas/pecas/ e de mapas/<nome>/layout.txt + mapa.json.
Gera mapas/<nome>/<nome>.webp (fundo, 200 px por quadrado), cena.json (cena do Foundry com
paredes, portas, luzes e sons) e previa.jpg (fundo com as paredes desenhadas por cima).
Uso: python3 tools/gen_mapa.py taverna"""
import json, os, subprocess, sys, tempfile, pathlib
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parent.parent
PECAS = ROOT / "mapas" / "pecas"
PX = 200  # pixels por quadrado na imagem de fundo

name = sys.argv[1] if len(sys.argv) > 1 else "taverna"
DIR = ROOT / "mapas" / name
cfg = json.loads((DIR / "mapa.json").read_text())
rows = [r for r in (DIR / "layout.txt").read_text().splitlines() if r]
H, W = len(rows), len(rows[0])
assert all(len(r) == W for r in rows), "todas as linhas do layout precisam ter o mesmo tamanho"
G = cfg["grid"]
kind = lambda c: cfg["legend"][c]
SOLID = {"parede", "lareira"}

sys.path.insert(0, str(ROOT / "tools"))
from gen_pecas_mapa import MATERIAIS

# cada material usado é desenhado no tamanho do mapa inteiro (sem emendas entre quadrados)
used = {kind(c) for r in rows for c in r}
tex = {}
with tempfile.TemporaryDirectory() as tmp:
    files = []
    for i, m in enumerate(sorted(used & MATERIAIS.keys())):
        f = pathlib.Path(tmp) / f"{m}.svg"
        f.write_text(MATERIAIS[m](W * PX, H * PX, cfg.get("seed", 1) + i))
        files.append(f)
    env = {**os.environ, "NODE_PATH": subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()}
    subprocess.run(["node", str(ROOT / "tools" / "render.js"), *map(str, files)], check=True, env=env)
    for f in files:
        tex[f.stem] = Image.open(f.with_suffix(".png")).convert("RGBA")

def piece(name):
    return Image.open(PECAS / f"{name}.png").convert("RGBA")

def material(name, x, y):
    return tex[name].crop((x * PX, y * PX, (x + 1) * PX, (y + 1) * PX))

def at(x, y):
    return kind(rows[y][x]) if 0 <= x < W and 0 <= y < H else None

def solid(x, y):
    return at(x, y) in SOLID

N4 = [(0, -1), (1, 0), (0, 1), (-1, 0)]  # cima, direita, baixo, esquerda

def floor_under(x, y):
    """Piso mais comum em volta (para desenhar embaixo do pilar)."""
    around = [at(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
    around = [k for k in around if k and k not in SOLID | {"pilar", "porta"}]
    return max(set(around), key=around.count) if around else "piso_pedra"

# ---------- imagem de fundo ----------
img = Image.new("RGBA", (W * PX, H * PX))
for y in range(H):
    for x in range(W):
        k = at(x, y)
        pos = (x * PX, y * PX)
        if k == "pilar":
            img.alpha_composite(material(floor_under(x, y), x, y), pos)
            continue  # o pilar entra depois das sombras
        if k in ("porta", "lareira"):
            img.alpha_composite(material("parede", x, y), pos)
        if k == "porta":
            tile = piece("porta")
            if solid(x, y - 1) and solid(x, y + 1):
                tile = tile.rotate(90)
            img.alpha_composite(tile, pos)
        elif k == "lareira":
            tile = piece("lareira")  # desenhada abrindo para baixo
            open_side = next((d for d in N4 if (at(x + d[0], y + d[1]) or "").startswith("piso")), (0, 1))
            tile = tile.rotate({(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): -90}[open_side])
            img.alpha_composite(tile, pos)
        else:
            img.alpha_composite(material(k, x, y), pos)

# sombra das paredes sobre o chão + contorno escuro
shadow = Image.new("RGBA", img.size)
sd = ImageDraw.Draw(shadow)
S = 50
for y in range(H):
    for x in range(W):
        if solid(x, y):
            continue
        X, Y = x * PX, y * PX
        for i in range(S):
            a = int(190 * (1 - i / S) ** 1.6)
            if solid(x, y - 1): sd.line([(X, Y + i), (X + PX, Y + i)], fill=(0, 0, 0, a))
            if solid(x, y + 1): sd.line([(X, Y + PX - 1 - i), (X + PX, Y + PX - 1 - i)], fill=(0, 0, 0, a // 2))
            if solid(x - 1, y): sd.line([(X + i, Y), (X + i, Y + PX)], fill=(0, 0, 0, a))
            if solid(x + 1, y): sd.line([(X + PX - 1 - i, Y), (X + PX - 1 - i, Y + PX)], fill=(0, 0, 0, a // 2))
# a sombra é somada pela maior opacidade, não empilhada
img.alpha_composite(shadow)
od = ImageDraw.Draw(img)
for y in range(H):
    for x in range(W):
        if not solid(x, y):
            continue
        X, Y = x * PX, y * PX
        for (dx, dy), seg in zip(N4, [((X, Y), (X + PX, Y)), ((X + PX, Y), (X + PX, Y + PX)),
                                      ((X, Y + PX), (X + PX, Y + PX)), ((X, Y), (X, Y + PX))]):
            if at(x + dx, y + dy) and not solid(x + dx, y + dy):
                od.line(seg, fill=(20, 18, 16, 255), width=6)

for y in range(H):
    for x in range(W):
        if at(x, y) == "pilar":
            img.alpha_composite(piece("pilar"), (x * PX, y * PX))

bg_name = f"{name}.webp"
img.convert("RGB").save(DIR / bg_name, quality=86, method=6)

# ---------- paredes do Foundry ----------
def merge(segs):
    """segs: {(linha, inicio)} unitários -> segmentos contínuos [(linha, a, b)]"""
    out, by = [], {}
    for line, s in segs:
        by.setdefault(line, []).append(s)
    for line, starts in by.items():
        starts.sort()
        a = prev = starts[0]
        for s in starts[1:]:
            if s != prev + 1:
                out.append((line, a, prev + 1)); a = s
            prev = s
        out.append((line, a, prev + 1))
    return out

hseg, vseg = set(), set()
for y in range(H):
    for x in range(W):
        if not solid(x, y):
            continue
        if at(x, y - 1) and not solid(x, y - 1): hseg.add((y, x))
        if at(x, y + 1) and not solid(x, y + 1): hseg.add((y + 1, x))
        if at(x - 1, y) and not solid(x - 1, y): vseg.add((x, y))
        if at(x + 1, y) and not solid(x + 1, y): vseg.add((x + 1, y))

walls = [{"c": [a * G, line * G, b * G, line * G]} for line, a, b in merge(hseg)]
walls += [{"c": [line * G, a * G, line * G, b * G]} for line, a, b in merge(vseg)]

for y in range(H):
    for x in range(W):
        k = at(x, y)
        if k == "porta":
            if solid(x, y - 1) and solid(x, y + 1):
                c = [(x + .5) * G, y * G, (x + .5) * G, (y + 1) * G]
            else:
                c = [x * G, (y + .5) * G, (x + 1) * G, (y + .5) * G]
            walls.append({"c": c, "door": 1, "ds": 0, "doorSound": "woodBasic"})
        elif k == "pilar":
            import math
            cx, cy, r = (x + .5) * G, (y + .5) * G, .37 * G
            pts = [(cx + r * math.cos(math.pi / 8 + i * math.pi / 4), cy + r * math.sin(math.pi / 8 + i * math.pi / 4)) for i in range(8)]
            for i in range(8):
                (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % 8]
                walls.append({"c": [round(x1), round(y1), round(x2), round(y2)]})

scene = {
    "name": cfg["name"],
    "width": W * G, "height": H * G, "padding": 0,
    "backgroundColor": "#1b1b1b",
    "background": {"src": f"mapas/{name}/{bg_name}"},
    "grid": {"type": 1, "size": G, "distance": 5, "units": "ft"},
    "tokenVision": True,
    "environment": {"darknessLevel": cfg.get("darkness", 0), "globalLight": {"enabled": True}},
    "walls": walls,
    "lights": cfg.get("lights", []),
    "sounds": [{**s, "walls": True, "easing": True} for s in cfg.get("sounds", [])],
    "flags": {"interactive-assets": {"objects": cfg.get("objects", [])}},
}
(DIR / "cena.json").write_text(json.dumps(scene, indent=1, ensure_ascii=False))

# ---------- prévia: fundo + paredes (vermelho), portas (amarelo), objetos ----------
k = 0.25
prev = img.convert("RGB").resize((int(img.width * k), int(img.height * k)), Image.LANCZOS)
pd = ImageDraw.Draw(prev)
f = PX / G * k
for w in walls:
    x1, y1, x2, y2 = [v * f for v in w["c"]]
    pd.line([(x1, y1), (x2, y2)], fill=(255, 210, 0) if w.get("door") else (230, 40, 40), width=4 if w.get("door") else 3)
for o in cfg.get("objects", []):
    x, y = o["x"] * f, o["y"] * f
    pd.ellipse([x - 8, y - 8, x + 8, y + 8], outline=(80, 200, 255), width=3)
prev.save(DIR / "previa.jpg", quality=85)
print(f"{name}: {W}x{H} quadrados, {len(walls)} paredes, fundo {img.width}x{img.height}")
