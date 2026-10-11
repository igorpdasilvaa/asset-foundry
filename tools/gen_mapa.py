"""Monta um mapa a partir das peças de mapas/pecas/ e de mapas/<nome>/layout.txt + mapa.json.
Gera mapas/<nome>/<nome>.webp (fundo, 200 px por quadrado), cena.json (cena do Foundry com
estruturas quebráveis, objetos, luzes e sons) e previa.jpg (a cena com as paredes calculadas pelo módulo).
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
WET = {"agua", "pier"}  # o píer é desenhado por cima da água

sys.path.insert(0, str(ROOT / "tools"))
from gen_pecas_mapa import MATERIAIS

# cada material usado é desenhado no tamanho do mapa inteiro (sem emendas entre quadrados)
used = {kind(c) for r in rows for c in r}
if "pier" in used:
    used |= {"agua", "piso_madeira"}
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
        if k == "pier":
            img.alpha_composite(material("agua", x, y), pos)
            continue  # o deck entra depois da margem
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

# margem da água: lama e espuma onde a água encosta na terra
water = lambda x, y: at(x, y) in WET
shore = Image.new("RGBA", img.size)
sh = ImageDraw.Draw(shore)
M = 34
for y in range(H):
    for x in range(W):
        if at(x, y) != "agua":
            continue
        X, Y = x * PX, y * PX
        for i in range(M):
            a = int(235 * (1 - i / M) ** 1.2)
            c = (88, 72, 46, a) if i > 3 else (210, 228, 224, 140)
            if at(x, y - 1) and not water(x, y - 1): sh.line([(X, Y + i), (X + PX, Y + i)], fill=c)
            if at(x, y + 1) and not water(x, y + 1): sh.line([(X, Y + PX - 1 - i), (X + PX, Y + PX - 1 - i)], fill=c)
            if at(x - 1, y) and not water(x - 1, y): sh.line([(X + i, Y), (X + i, Y + PX)], fill=c)
            if at(x + 1, y) and not water(x + 1, y): sh.line([(X + PX - 1 - i, Y), (X + PX - 1 - i, Y + PX)], fill=c)
img.alpha_composite(shore)

# píer: tábuas (o piso de madeira) um pouco mais estreitas que o quadrado, com postes nas pontas
for y in range(H):
    for x in range(W):
        if at(x, y) != "pier":
            continue
        X, Y = x * PX, y * PX
        horiz = water(x - 1, y) or water(x + 1, y) or not water(x, y - 1)
        deck = material("piso_madeira", x, y)
        box = (0, 24, PX, PX - 24) if horiz else (24, 0, PX - 24, PX)
        mask = Image.new("L", (PX, PX))
        ImageDraw.Draw(mask).rectangle(box, fill=255)
        shadow_box = Image.new("RGBA", (PX, PX))
        ImageDraw.Draw(shadow_box).rectangle(box, fill=(0, 0, 0, 110))
        img.alpha_composite(shadow_box, (X + 8, Y + 10))
        img.paste(deck, (X, Y), mask)
        od0 = ImageDraw.Draw(img)
        od0.rectangle((X + box[0], Y + box[1], X + box[2] - 1, Y + box[3] - 1), outline=(42, 24, 10, 255), width=4)
        for px_, py_ in ((box[0], box[1]), (box[2], box[1]), (box[0], box[3]), (box[2], box[3])):
            od0.ellipse((X + px_ - 11, Y + py_ - 11, X + px_ + 11, Y + py_ + 11), fill=(74, 52, 32, 255), outline=(30, 18, 8, 255), width=3)

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

bg_name = f"{name}.webp"
img.convert("RGB").save(DIR / bg_name, quality=86, method=6)

# ---------- estruturas quebráveis (tokens) ----------
# Cada bloco de parede, porta e pilar vira um token de asset; as paredes do Foundry
# são calculadas pelo módulo (scripts/mapa.js) a partir do que está de pé.
STRUCT = cfg.get("structures", {"parede": "wall", "porta": "door", "pilar": "pillar", "agua": "water"})
structures, fixed = [], []
for y in range(H):
    for x in range(W):
        k = at(x, y)
        if k in STRUCT:
            s = {"asset": k, "x": x, "y": y, "kind": STRUCT[k]}
            if STRUCT[k] == "door":
                s["dir"] = "v" if solid(x, y - 1) and solid(x, y + 1) else "h"
                s["rotation"] = 90 if s["dir"] == "v" else 0
            structures.append(s)
        elif k in SOLID:
            fixed.append(f"{x},{y}")

scene = {
    "name": cfg["name"],
    "width": W * G, "height": H * G, "padding": 0,
    "backgroundColor": "#1b1b1b",
    "background": {"src": f"mapas/{name}/{bg_name}"},
    "grid": {"type": 1, "size": G, "distance": 5, "units": "ft"},
    "tokenVision": True,
    "environment": {"darknessLevel": cfg.get("darkness", 0), "globalLight": {"enabled": True}},
    "lights": cfg.get("lights", []),
    "sounds": [{**s, "walls": True, "easing": True} for s in cfg.get("sounds", [])],
    "flags": {"interactive-assets": {"map": {
        "cols": W, "rows": H, "fixed": fixed, "structures": structures, "objects": cfg.get("objects", [])}}},
}
(DIR / "cena.json").write_text(json.dumps(scene, indent=1, ensure_ascii=False))

# ---------- prévias: como a cena fica no Foundry, com as paredes calculadas pelo módulo ----------
ASSETS = json.loads((ROOT / "assets" / "assets.json").read_text())

def state_img(asset, idx):
    return Image.open(ROOT / "assets" / ASSETS[asset]["states"][idx]["src"].replace(".webm", ".png")).convert("RGBA")

def preview(out, broken=(), states=()):
    """states: [{"asset", "state", "cells"?}] troca o estado das estruturas (todas daquele asset, ou só "cells")
    e dos objetos daquele asset."""
    broken = {tuple(b) for b in broken}
    override, obj_override = {}, {}
    for st_ in states:
        ids = [s_["id"] for s_ in ASSETS[st_["asset"]]["states"]]
        obj_override[st_["asset"]] = ids.index(st_["state"])
        cells = {tuple(c) for c in st_["cells"]} if st_.get("cells") else None
        for s in structures:
            if s["asset"] == st_["asset"] and (cells is None or (s["x"], s["y"]) in cells):
                override[(s["x"], s["y"])] = ids.index(st_["state"])
    scene_img = img.copy()
    solid_now, doors, pillars = set(fixed), [], []
    for s in structures:
        b = (s["x"], s["y"]) in broken
        states = ASSETS[s["asset"]]["states"]
        idx = next(i for i, st in enumerate(states) if st.get("broken")) if b else override.get((s["x"], s["y"]), 0)
        tile = state_img(s["asset"], idx).rotate(-s.get("rotation", 0))
        scene_img.alpha_composite(tile.resize((PX, PX)), (s["x"] * PX, s["y"] * PX))
        if b:
            continue
        if s["kind"] == "wall": solid_now.add(f'{s["x"]},{s["y"]}')
        elif s["kind"] == "door": doors.append({"x": s["x"], "y": s["y"], "dir": s["dir"]})
        elif s["kind"] == "pillar": pillars.append({"x": s["x"], "y": s["y"]})
    for o in cfg.get("objects", []):
        d = ASSETS[o["asset"]]
        t = state_img(o["asset"], obj_override.get(o["asset"], 0))
        w, h = int(d["size"]["w"] * PX), int(d["size"]["h"] * PX)
        f = PX / G
        scene_img.alpha_composite(t.resize((w, h)), (int(o["x"] * f - w / 2), int(o["y"] * f - h / 2)))
    st = {"cols": W, "rows": H, "solid": sorted(solid_now), "doors": doors, "pillars": pillars}
    walls = json.loads(subprocess.run(["node", str(ROOT / "tools" / "paredes.mjs")], input=json.dumps(st),
                                      capture_output=True, text=True, check=True).stdout)
    k = 0.25
    prev = scene_img.convert("RGB").resize((int(img.width * k), int(img.height * k)), Image.LANCZOS)
    pd = ImageDraw.Draw(prev)
    f = PX * k
    for w in walls:
        x1, y1, x2, y2 = [v * f for v in w["c"]]
        pd.line([(x1, y1), (x2, y2)], fill=(255, 210, 0) if w.get("door") else (230, 40, 40), width=4 if w.get("door") else 3)
    prev.save(DIR / out, quality=85)
    return walls

walls = preview("previa.jpg")
if cfg.get("preview_broken"):
    preview("previa_quebrada.jpg", cfg["preview_broken"])
for name_, states_ in cfg.get("preview_states", {}).items():
    preview(name_, states=states_)
print(f"{name}: {W}x{H} quadrados, {len(structures)} estruturas, {len(walls)} paredes, fundo {img.width}x{img.height}")
