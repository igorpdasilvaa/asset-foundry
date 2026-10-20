"""Partes do mapa.json que não são desenho: saídas para outras cenas, NPCs, multidão, notas e proteções.
Usado por gen_mapa.py e gen_relevo.py: copia para a cena (flags) e desenha na prévia."""
import json, math, pathlib
from PIL import ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHAVES = ("saidas", "npcs", "multidao", "notas")


def scene_flags(cfg):
    """O que vai em flags.interactive-assets.map (mesclar) e flags.interactive-assets.protecoes."""
    m = {k: cfg[k] for k in CHAVES if cfg.get(k)}
    p = cfg.get("protecoes")
    if p:
        p = {"ativas": True, "alarme": 1, "dano": 0, "tocado": False, **(p if isinstance(p, dict) else {})}
    return m, p


def musica(cfg, W, H, G):
    """"musica": { "path", "volume"? } vira um som que cobre o mapa inteiro (atravessa paredes): a trilha do lugar."""
    m = cfg.get("musica")
    if not m:
        return []
    raio = math.ceil(math.hypot(W, H) * 5 / 2) + 10  # em pés, do centro até os cantos
    return [{"x": W * G // 2, "y": H * G // 2, "radius": raio, "path": m["path"], "volume": m.get("volume", 0.3),
             "walls": False, "easing": True, "flags": {"interactive-assets": {"musica": True}}}]


def desenha(img, cfg, f, G):
    """Prévia: saídas (azul), chegadas (verde), NPCs nomeados (círculo com a inicial), multidão (laranja).
    f = pixels da prévia por quadrado; G = tamanho do quadrado na cena (as posições dos NPCs são em pixels da cena)."""
    d = ImageDraw.Draw(img, "RGBA")
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 11)
    txt = lambda xy, t, c: d.text(xy, t, font=font, fill=c, stroke_width=2, stroke_fill=(0, 0, 0, 255))
    box = lambda r: (r["x"] * f, r["y"] * f, (r["x"] + r.get("w", 1)) * f - 1, (r["y"] + r.get("h", 1)) * f - 1)
    for s in cfg.get("saidas", []):
        d.rectangle(box(s), fill=(58, 123, 213, 90), outline=(58, 123, 213, 255), width=3)
        txt((s["x"] * f + 4, s["y"] * f + 2), f"→ {s.get('nome', s['para'])}", (255, 255, 255, 255))
        if s.get("pouso"):
            d.rectangle(box(s["pouso"]), fill=(58, 213, 123, 60), outline=(58, 213, 123, 255), width=2)
    for m in cfg.get("multidao", []):
        x, y, w, h = m["area"]
        r = (x * f, y * f, (x + w) * f - 1, (y + h) * f - 1)
        d.rectangle(r, outline=(255, 150, 30, 255), width=2)
        txt((r[0] + 4, r[1] + 2), f"{m.get('n', 1)}x {', '.join(m.get('oficios', ['?']))}", (255, 190, 90, 255))
    nomeados = json.loads((ROOT / "assets" / "npcs.json").read_text())["nomeados"]
    for n in cfg.get("npcs", []):
        cx, cy, r = n["x"] / G * f, n["y"] / G * f, f * .4
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(150, 40, 160, 200), outline=(255, 255, 255, 255), width=2)
        txt((cx - 4, cy - 7), nomeados.get(n["npc"], {}).get("nome", n["npc"])[:1], (255, 255, 255, 255))
    for n in cfg.get("notas", []):
        cx, cy = (n["x"] + .5) * f, (n["y"] + .5) * f
        d.rectangle((cx - 5, cy - 7, cx + 5, cy + 7), fill=(240, 230, 200, 255), outline=(60, 40, 20, 255))
