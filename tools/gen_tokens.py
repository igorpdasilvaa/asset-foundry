"""Transforma um retrato gerado (ia-orc / SDXL) em token redondo de NPC e registra no assets/npcs.json.

Recorta o quadrado de cima (rosto e ombros), aplica a máscara redonda e a moldura de bronze igual em todos,
e salva em .webp de 400 px.

Uso:
  python3 tools/gen_tokens.py <imagem> --npc kalan_strongbranch --cidade candlekeep
  python3 tools/gen_tokens.py <imagem> --oficio buscador --especie humano --genero f
Os prompts usados para gerar os retratos ficam em tools/tokens_npcs.json."""
import argparse, json, pathlib
from PIL import Image, ImageDraw, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent.parent
NPCS = ROOT / "assets" / "npcs.json"
S = 400          # lado do token
RING = 22        # largura da moldura


def token(src):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    side = min(w, h)
    im = im.crop(((w - side) // 2, 0, (w + side) // 2, side)).resize((S * 2, S * 2), Image.LANCZOS)
    big = S * 2
    mask = Image.new("L", (big, big))
    ImageDraw.Draw(mask).ellipse((RING * 2, RING * 2, big - RING * 2, big - RING * 2), fill=255)
    out = Image.new("RGBA", (big, big))
    out.paste(im, (0, 0), mask)
    # moldura: bronze com brilho em cima e sombra embaixo, contorno escuro dos dois lados
    ring = Image.new("RGBA", (big, big))
    d = ImageDraw.Draw(ring)
    r0, r1 = 4, RING * 2 + 4
    for i in range(r0, r1):
        t = (i - r0) / (r1 - r0)
        c = (int(150 + 60 * (1 - abs(t - .35) * 2)), int(105 + 45 * (1 - abs(t - .35) * 2)), int(50 + 20 * (1 - t)), 255)
        d.ellipse((i, i, big - i, big - i), outline=c, width=2)
    d.ellipse((r0, r0, big - r0, big - r0), outline=(40, 26, 12, 255), width=6)
    d.ellipse((r1, r1, big - r1, big - r1), outline=(40, 26, 12, 255), width=5)
    shade = Image.new("L", (big, big))
    ImageDraw.Draw(shade).pieslice((r0, r0, big - r0, big - r0), 20, 160, fill=70)
    out.alpha_composite(ring)
    dark = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    dark.putalpha(Image.composite(shade.filter(ImageFilter.GaussianBlur(30)), Image.new("L", (big, big)), ring.getchannel("A")))
    out.alpha_composite(dark)
    return out.resize((S, S), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("imagem")
    ap.add_argument("--npc")
    ap.add_argument("--cidade", default="candlekeep")
    ap.add_argument("--oficio")
    ap.add_argument("--especie")
    ap.add_argument("--genero")
    a = ap.parse_args()
    data = json.loads(NPCS.read_text())
    if a.npc:
        rel = f"npcs/{a.cidade}/{a.npc}.webp"
    else:
        lst = data["oficios"][a.oficio]["imgs"]
        n = 1 + sum(1 for i in lst if i["src"].startswith(f"npcs/plebeus/{a.oficio}_{a.especie}_"))
        rel = f"npcs/plebeus/{a.oficio}_{a.especie}_{a.genero or 'x'}{n}.webp"
    dst = ROOT / "assets" / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    token(a.imagem).save(dst, quality=88, method=6)
    if a.npc:
        data["nomeados"][a.npc]["img"] = rel
    else:
        item = {"src": rel, "especie": a.especie, **({"genero": a.genero} if a.genero else {})}
        if item not in lst:
            lst.append(item)
    NPCS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(rel)


if __name__ == "__main__":
    main()
