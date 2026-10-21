"""Monta um mapa a partir das peças de mapas/pecas/ e de mapas/<nome>/layout.txt + mapa.json.
Gera mapas/<nome>/<nome>.webp (fundo, 200 px por quadrado), cena.json (cena do Foundry com
estruturas quebráveis, objetos, luzes e sons) e previa.jpg (a cena com as paredes calculadas pelo módulo).
Uso: python3 tools/gen_mapa.py taverna"""
import json, os, subprocess, sys, tempfile, pathlib
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent.parent
PECAS = ROOT / "mapas" / "pecas"
PX = 200  # pixels por quadrado na imagem de fundo ("px" no mapa.json: mapas grandes usam menos)

name = sys.argv[1] if len(sys.argv) > 1 else "taverna"
DIR = ROOT / "mapas" / name
cfg = json.loads((DIR / "mapa.json").read_text())
rows = [r for r in (DIR / "layout.txt").read_text().splitlines() if r]
H, W = len(rows), len(rows[0])
assert all(len(r) == W for r in rows), "todas as linhas do layout precisam ter o mesmo tamanho"
G = cfg["grid"]
PX = cfg.get("px", PX)
# Legenda: "c": "nome" ou "c": { "nome", "chao"?, "peca"?, "rot"?, "asset"?, "kind"?, "solido"? }
#   chao: material desenhado no quadrado (padrão: o próprio nome); peca: peça de mapas/pecas/ por cima (girada "rot" graus);
#   asset + kind: o quadrado vira token de estrutura (wall | door | pillar | water); solido: bloqueia (paredes fixas do Foundry).
LEG = {c: (v if isinstance(v, dict) else {"nome": v}) for c, v in cfg["legend"].items()}
PROPS = {v["nome"]: v for v in LEG.values()}
kind = lambda c: LEG[c]["nome"]
SOLID = {"parede", "lareira", "muralha", "telhado_ardosia", "telhado_telha", "vazio"}
SOLID = (SOLID | {n for n, v in PROPS.items() if v.get("solido")}) - {n for n, v in PROPS.items() if v.get("solido") is False}
WET = {"agua", "pier"} | {n for n, v in PROPS.items() if v.get("chao") == "agua"}  # o píer é desenhado por cima da água
chao = lambda n: PROPS.get(n, {}).get("chao", n)
ESCALA = PX / 200  # peças e materiais são desenhados com 200 px por quadrado

sys.path.insert(0, str(ROOT / "tools"))
from gen_pecas_mapa import MATERIAIS
import extras

# cada material usado é desenhado inteiro e recortado por quadrado (sem emendas entre quadrados)
used = {chao(kind(c)) for r in rows for c in r}
used |= {PROPS[n].get("chao", "parede") for n in {kind(c) for r in rows for c in r} if PROPS[n].get("kind") == "door"}
if used & {"porta", "lareira"}:
    used.add("parede")  # a porta e a lareira são desenhadas sobre a parede
if "pier" in used:
    used |= {"agua", "piso_madeira"}
# Mapas grandes ("recorte"): cada material é desenhado só no retângulo onde aparece (com 1 quadrado de folga).
# O Chrome não aguenta os filtros de textura num SVG do tamanho do mapa inteiro (fica lento e corta o fim).
RECORTE = cfg.get("recorte", W * H > 2000)
caixa = {}  # material -> (x0, y0, x1, y1) em quadrados
if RECORTE:
    for y_, r in enumerate(rows):
        for x_, c in enumerate(r):
            n = kind(c)
            ms = {chao(n)}
            if PROPS[n].get("kind") == "door": ms.add(PROPS[n].get("chao", "parede"))
            if n in ("porta", "lareira"): ms.add("parede")
            for m in ms:
                b0 = caixa.get(m, (x_, y_, x_, y_))
                caixa[m] = (min(b0[0], x_), min(b0[1], y_), max(b0[2], x_), max(b0[3], y_))
    caixa = {m: (max(0, a0 - 1), max(0, b0 - 1), min(W - 1, a1 + 1), min(H - 1, b1 + 1)) for m, (a0, b0, a1, b1) in caixa.items()}
origem = {}
tex = {}

# Texturas pintadas (ia-orc, emendáveis) em mapas/pecas/texturas/<material>.webp substituem o SVG do material.
# texturas.json: { "<material>": { "quadrados": lado do ladrilho em quadrados, "variacao": 0..1 (manchas de tom) } }
TEXDIR = PECAS / "texturas"
TEXCFG = json.loads((TEXDIR / "texturas.json").read_text()) if (TEXDIR / "texturas.json").exists() else {}
def textura(m, i):
    import random as _r
    x0, y0, x1, y1 = caixa.get(m, (0, 0, W - 1, H - 1))
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    c = TEXCFG.get(m, {})
    lado = int(c.get("quadrados", 2) * PX)
    lad = Image.open(TEXDIR / f"{m}.webp").convert("RGB").resize((lado, lado), Image.LANCZOS)
    out = Image.new("RGB", (bw * PX, bh * PX))
    for yy in range(0, bh * PX, lado):
        for xx in range(0, bw * PX, lado):
            out.paste(lad, (xx, yy))
    var = c.get("variacao", .12)
    if var:  # manchas grandes de tom para a repetição não aparecer
        R_ = _r.Random(cfg.get("seed", 1) + i)
        n = Image.new("L", (max(2, bw // 3 + 2), max(2, bh // 3 + 2)))
        n.putdata([R_.randint(0, 255) for _ in range(n.width * n.height)])
        n = n.resize(out.size, Image.BICUBIC)
        from PIL import ImageChops as _C
        claro = out.point(lambda v: min(255, int(v * (1 + var))))
        escuro = out.point(lambda v: int(v * (1 - var)))
        out = Image.composite(claro, escuro, n)
    origem[m] = (x0, y0)
    return out.convert("RGBA")

with tempfile.TemporaryDirectory() as tmp:
    files = []
    for i, m in enumerate(sorted(used & MATERIAIS.keys())):
        if (TEXDIR / f"{m}.webp").exists():
            tex[m] = textura(m, i)
            continue
        f = pathlib.Path(tmp) / f"{m}.svg"
        x0, y0, x1, y1 = caixa.get(m, (0, 0, W - 1, H - 1))
        bw, bh = x1 - x0 + 1, y1 - y0 + 1
        origem[m] = (x0, y0)
        # desenhado na escala de 200 por quadrado e renderizado com PX por quadrado
        svg_ = MATERIAIS[m](bw * 200, bh * 200, cfg.get("seed", 1) + i)
        svg_ = svg_.replace(f'width="{bw * 100}" height="{bh * 100}"', f'width="{bw * PX // 2}" height="{bh * PX // 2}"', 1)
        f.write_text(svg_)
        files.append(f)
    env = {**os.environ}
    env.setdefault("NODE_PATH", subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip())
    if files:
        subprocess.run(["node", str(ROOT / "tools" / "render.js"), *map(str, files)], check=True, env=env)
    for f in files:
        tex[f.stem] = Image.open(f.with_suffix(".png")).convert("RGBA")

def piece(name):
    im = Image.open(PECAS / f"{name}.png").convert("RGBA")
    return im if im.size == (PX, PX) else im.resize((PX, PX), Image.LANCZOS)

def material(name, x, y):
    ox, oy = origem[name]
    return tex[name].crop(((x - ox) * PX, (y - oy) * PX, (x - ox + 1) * PX, (y - oy + 1) * PX))

def at(x, y):
    return kind(rows[y][x]) if 0 <= x < W and 0 <= y < H else None

def solid(x, y):
    return at(x, y) in SOLID

N4 = [(0, -1), (1, 0), (0, 1), (-1, 0)]  # cima, direita, baixo, esquerda

def floor_under(x, y):
    """Piso mais comum em volta (para desenhar embaixo do pilar)."""
    around = [at(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
    around = [k for k in around if k and k not in SOLID | {"pilar", "porta"} and not PROPS.get(k, {}).get("peca") and not PROPS.get(k, {}).get("kind")]
    return max(set(around), key=around.count) if around else "piso_pedra"

# ---------- imagem de fundo ----------
img = Image.new("RGBA", (W * PX, H * PX))
for y in range(H):
    for x in range(W):
        k = at(x, y)
        pos = (x * PX, y * PX)
        p = PROPS.get(k, {})
        if k == "pilar":
            img.alpha_composite(material(floor_under(x, y), x, y), pos)
            continue  # o pilar entra depois das sombras
        if p.get("peca"):
            img.alpha_composite(material(p["chao"] if "chao" in p else floor_under(x, y), x, y), pos)
            img.alpha_composite(piece(p["peca"]).rotate(-p.get("rot", 0)), pos)
            continue
        if p.get("kind") == "door":  # portão, porta esmeralda: o token cobre o quadrado
            img.alpha_composite(material(p.get("chao", "parede"), x, y), pos)
            continue
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
            img.alpha_composite(material(chao(k), x, y), pos)

# telhados de duas águas: cada bloco de telhado ganha cumeeira no meio (no sentido do lado maior),
# uma água iluminada (de cima/esquerda) e a outra na sombra, com beiral escuro
TELHADOS = {n for n in PROPS if n.startswith("telhado")} | set(cfg.get("telhados", []))
vistos = set()
for y in range(H):
    for x in range(W):
        if at(x, y) not in TELHADOS or (x, y) in vistos:
            continue
        pilha, comp = [(x, y)], []
        vistos.add((x, y))
        while pilha:
            cx, cy = pilha.pop()
            comp.append((cx, cy))
            for dx, dy in N4:
                nx, ny = cx + dx, cy + dy
                if (nx, ny) not in vistos and at(nx, ny) == at(x, y):
                    vistos.add((nx, ny))
                    pilha.append((nx, ny))
        xs, ys = [c[0] for c in comp], [c[1] for c in comp]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs) + 1, max(ys) + 1
        bw, bh = (x1 - x0) * PX, (y1 - y0) * PX
        horiz = bw >= bh  # cumeeira horizontal: águas para cima e para baixo
        lado = bh if horiz else bw
        rampa = Image.new("RGBA", (1, lado) if horiz else (lado, 1))
        for i in range(lado):
            t = i / max(1, lado - 1)
            if t < .5:   # água de cima/esquerda: clareia perto da cumeeira
                cor = (255, 245, 220, int(70 * (t / .5) ** 1.5))
            else:        # água de baixo/direita: sombra
                cor = (0, 0, 10, int(40 + 70 * ((t - .5) / .5)))
            if abs(t - .5) < 6 / lado:
                cor = (30, 25, 20, 150)  # cumeeira
            rampa.putpixel((0, i) if horiz else (i, 0), cor)
        rampa = rampa.resize((bw, bh), Image.BILINEAR)
        m = Image.new("L", (bw, bh), 0)
        dm = ImageDraw.Draw(m)
        for cx, cy in comp:
            dm.rectangle(((cx - x0) * PX, (cy - y0) * PX, (cx - x0 + 1) * PX - 1, (cy - y0 + 1) * PX - 1), fill=255)
        beiral = m.filter(ImageFilter.MinFilter(int(PX * .12) | 1))
        camada = Image.new("RGBA", (bw, bh))
        camada.paste(rampa, (0, 0), m)
        borda = Image.new("RGBA", (bw, bh), (15, 12, 10, 0))
        borda.putalpha(ImageChops.subtract(m, beiral).point(lambda v: int(v * .55)))
        camada.alpha_composite(borda)
        img.alpha_composite(camada, (x0 * PX, y0 * PX))

# pinturas: imagens prontas (ex.: um jardim gerado no ia-orc) sobre o chão de uma área, com a borda esfumada.
# "pinturas": [{ "img": "mapas/<mapa>/x.webp", "x", "y", "w", "h" (quadrados), "borda": fração de quadrado }]
for pt in cfg.get("pinturas", []):
    w_, h_ = pt["w"] * PX, pt["h"] * PX
    pin = Image.open(ROOT / pt["img"]).convert("RGBA").resize((w_, h_), Image.LANCZOS)
    b = int(pt.get("borda", .4) * PX)
    if b:
        from PIL import ImageFilter
        m = Image.new("L", (w_, h_), 0)
        ImageDraw.Draw(m).rectangle((b, b, w_ - b, h_ - b), fill=255)
        pin.putalpha(m.filter(ImageFilter.GaussianBlur(b / 2)))
    img.alpha_composite(pin, (pt["x"] * PX, pt["y"] * PX))

# margem da água: lama e espuma onde a água encosta na terra
water = lambda x, y: at(x, y) in WET
shore = Image.new("RGBA", img.size)
sh = ImageDraw.Draw(shore)
M = int(34 * ESCALA)
for y in range(H):
    for x in range(W):
        if at(x, y) not in WET or at(x, y) == "pier":
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
S = int(50 * ESCALA)
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
                od.line(seg, fill=(20, 18, 16, 255), width=max(2, int(6 * ESCALA)))

bg_name = f"{name}.webp"
img.convert("RGB").save(DIR / bg_name, quality=cfg.get("qualidade", 86), method=6)

# ---------- estruturas quebráveis (tokens) ----------
# Cada bloco de parede, porta e pilar vira um token de asset; as paredes do Foundry
# são calculadas pelo módulo (scripts/mapa.js) a partir do que está de pé.
STRUCT = cfg.get("structures", {"parede": "wall", "porta": "door", "pilar": "pillar", "agua": "water", "muralha": "wall"})
STRUCT = {**STRUCT, **{n: v["kind"] for n, v in PROPS.items() if v.get("kind")}}
structures, fixed = [], []
for y in range(H):
    for x in range(W):
        k = at(x, y)
        # parede encostada no vazio (andares e demiplanos): quebrar não levaria a lugar nenhum, então fica fixa (menos tokens)
        if STRUCT.get(k) == "wall" and cfg.get("vazio_fixo", True) and any(at(x + dx, y + dy) == "vazio" for dx, dy in N4):
            fixed.append(f"{x},{y}")
        elif k in STRUCT:
            s = {"asset": PROPS.get(k, {}).get("asset", k), "x": x, "y": y, "kind": STRUCT[k]}
            if STRUCT[k] == "door":
                # portas largas (portão de 4 quadrados): a porta vizinha conta como batente
                bat = lambda x_, y_: solid(x_, y_) or STRUCT.get(at(x_, y_)) == "door"
                s["dir"] = "v" if bat(x, y - 1) and bat(x, y + 1) and not (bat(x - 1, y) and bat(x + 1, y)) else "h"
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
    "sounds": [{"walls": True, "easing": True, **s} for s in cfg.get("sounds", [])] + extras.musica(cfg, W, H, G),
    "flags": {"interactive-assets": {"map": {
        "cols": W, "rows": H, "fixed": fixed, "structures": structures, "objects": cfg.get("objects", [])}}},
}
_m, _p = extras.scene_flags(cfg)
scene["flags"]["interactive-assets"]["map"].update(_m)
if _p:
    scene["flags"]["interactive-assets"]["protecoes"] = _p
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
    extras.desenha(prev, cfg, f, G)
    prev.save(DIR / out, quality=85)
    return walls

walls = preview("previa.jpg")
if cfg.get("preview_broken"):
    preview("previa_quebrada.jpg", cfg["preview_broken"])
for name_, states_ in cfg.get("preview_states", {}).items():
    preview(name_, states=states_)
print(f"{name}: {W}x{H} quadrados, {len(structures)} estruturas, {len(walls)} paredes, fundo {img.width}x{img.height}")
