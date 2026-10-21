"""Jardim do Pátio do Ar: a pintura do chão e os assets poço e estátua, a partir de imagens geradas no ia-orc (SDXL).

- O chão vira mapas/candlekeep_patio/jardim.webp ("pinturas" no mapa.json).
- O poço e a estátua perdem o fundo branco (preenchido a partir das bordas), ganham sombra e os estados de dano são
  desenhados por cima da mesma imagem (rachaduras, entulho, manchas), para combinar com o intacto.
- As definições vão para tools/fragmentos/jardim.json (juntar com tools/juntar_fragmentos.py).

Uso: python3 tools/gen_jardim.py <chão.png> <poço.png> <estátua.png>   (os prompts usados estão em PROMPTS)"""
import json, math, pathlib, random, sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROMPTS = {
    "chao": "top-down orthographic view from directly above of a small walled monastery herb garden, tabletop RPG battle map, "
            "gravel paths forming a cross, flower beds with lavender and herbs, low trimmed hedges, lush grass, stone edging, "
            "small round empty plaza in the center, painted texture, Dungeondraft style, no buildings, no people, no trees",
    "poco": "top-down view from directly above of a round medieval stone well, mossy grey stone rim, dark water inside, small wooden "
            "crank beam across it, tabletop RPG battle map token asset, isolated on plain white background, centered, painted style",
    "estatua": "top-down view from directly above of a stone statue of a robed bearded sage holding an open book and a candle, standing "
               "on a square carved stone plinth, tabletop RPG battle map token asset, isolated on plain white background, centered, painted style",
}
S = 200  # pixels por quadrado nos assets


def sem_fundo(src, tol=38):
    """Tira o fundo claro ligado às bordas (flood fill) e devolve RGBA recortado no conteúdo, quadrado."""
    im = Image.open(src).convert("RGB")
    w, h = im.size
    marca = im.copy()
    for p in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        ImageDraw.floodfill(marca, p, (255, 0, 255), thresh=tol)
    r, g, b = marca.split()
    fundo = ImageChops.multiply(ImageChops.multiply(r.point(lambda v: 255 if v == 255 else 0), b.point(lambda v: 255 if v == 255 else 0)),
                                g.point(lambda v: 255 if v == 0 else 0))
    # come uns pixels da borda: tira o contorno claro que sobra do fundo branco
    alpha = ImageOps.invert(fundo).filter(ImageFilter.MinFilter(11)).filter(ImageFilter.GaussianBlur(2))
    out = im.convert("RGBA")
    out.putalpha(alpha)
    bbox = alpha.point(lambda v: 255 if v > 30 else 0).getbbox()
    out = out.crop(bbox)
    lado = max(out.size)
    q = Image.new("RGBA", (lado, lado))
    q.alpha_composite(out, ((lado - out.width) // 2, (lado - out.height) // 2))
    return q


def com_sombra(obj, lado):
    """Objeto centrado num quadro lado x lado, com 6% de margem e sombra suave deslocada."""
    m = int(lado * .06)
    obj = obj.resize((lado - 2 * m, lado - 2 * m), Image.LANCZOS)
    quadro = Image.new("RGBA", (lado, lado))
    sombra = Image.new("RGBA", obj.size, (0, 0, 0, 0))
    sombra.putalpha(obj.getchannel("A").point(lambda v: int(v * .55)))
    quadro.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(10)), (m + 8, m + 12))
    quadro.alpha_composite(obj, (m, m))
    return quadro


def so_no_objeto(base, camada):
    """Aplica a camada só onde o objeto existe (não pinta a sombra nem o fundo)."""
    a = base.getchannel("A").point(lambda v: 255 if v > 200 else 0)
    c = Image.new("RGBA", base.size)
    c.paste(camada, (0, 0), ImageChops.multiply(camada.getchannel("A"), a))
    out = base.copy()
    out.alpha_composite(c)
    return out


def rachaduras(lado, R, n=6, cor=(20, 18, 16, 235)):
    c = Image.new("RGBA", (lado, lado))
    d = ImageDraw.Draw(c)
    for _ in range(n):
        x, y = R.uniform(.25, .75) * lado, R.uniform(.25, .75) * lado
        ang = R.uniform(0, 2 * math.pi)
        pts = [(x, y)]
        for _ in range(R.randint(5, 9)):
            ang += R.uniform(-.7, .7)
            L = R.uniform(.03, .07) * lado
            x, y = x + L * math.cos(ang), y + L * math.sin(ang)
            pts.append((x, y))
        d.line(pts, fill=cor, width=max(2, lado // 140), joint="curve")
    return c


def entulho(lado, R, n, cores, tam=(.03, .08), espalha=.3):
    c = Image.new("RGBA", (lado, lado))
    d = ImageDraw.Draw(c)
    for _ in range(n):
        cx, cy = lado / 2 + R.gauss(0, espalha * lado), lado / 2 + R.gauss(0, espalha * lado)
        r = R.uniform(*tam) * lado
        k = R.randint(4, 7)
        a0 = R.uniform(0, math.pi)
        pts = [(cx + r * R.uniform(.6, 1) * math.cos(a0 + i * 2 * math.pi / k), cy + r * R.uniform(.6, 1) * math.sin(a0 + i * 2 * math.pi / k)) for i in range(k)]
        d.polygon(pts, fill=R.choice(cores), outline=(28, 26, 24, 255))
    return c


def cacos(base, R, n, espalha=.32, tam=(.06, .14)):
    """Pedaços recortados do próprio objeto, girados e espalhados em volta (entulho com a mesma textura)."""
    lado = base.width
    a = base.getchannel("A")
    out = Image.new("RGBA", base.size)
    for _ in range(n):
        while True:
            cx, cy = R.uniform(.2, .8) * lado, R.uniform(.2, .8) * lado
            if a.getpixel((int(cx), int(cy))) > 200:
                break
        r = R.uniform(*tam) * lado
        k = R.randint(4, 7)
        a0 = R.uniform(0, math.pi)
        pts = [(r + r * R.uniform(.55, 1) * math.cos(a0 + i * 2 * math.pi / k), r + r * R.uniform(.55, 1) * math.sin(a0 + i * 2 * math.pi / k)) for i in range(k)]
        m = Image.new("L", (int(2 * r), int(2 * r)))
        ImageDraw.Draw(m).polygon(pts, fill=255)
        peca = base.crop((int(cx - r), int(cy - r), int(cx - r) + m.width, int(cy - r) + m.height))
        peca.putalpha(ImageChops.multiply(peca.getchannel("A"), m))
        peca = peca.rotate(R.uniform(0, 360), expand=True, resample=Image.BICUBIC)
        x = int(lado / 2 + R.gauss(0, espalha * lado) - peca.width / 2)
        y = int(lado / 2 + R.gauss(0, espalha * lado) - peca.height / 2)
        sombra = Image.new("RGBA", peca.size, (0, 0, 0, 0))
        sombra.putalpha(peca.getchannel("A").point(lambda v: int(v * .5)))
        out.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(4)), (x + 4, y + 6))
        out.alpha_composite(peca, (x, y))
    return out


def tinge(base, cor, forca):
    """Mistura uma cor no objeto (água envenenada, gelo, mancha necrótica)."""
    t = Image.new("RGBA", base.size, cor + (0,))
    t.putalpha(base.getchannel("A").point(lambda v: int(v * forca) if v > 200 else 0))
    out = base.copy()
    out.alpha_composite(t)
    return out


def salva(asset, estado, im):
    d = ROOT / "assets" / asset
    d.mkdir(parents=True, exist_ok=True)
    im.save(d / f"{asset}_{estado}.webp", quality=88, method=6)
    return f"{asset}/{asset}_{estado}.webp"


def main(chao, poco, estatua):
    Image.open(chao).convert("RGB").save(ROOT / "mapas" / "candlekeep_patio" / "jardim.webp", quality=86, method=6)
    lado = 2 * S
    R = random.Random(7)
    pedras = [(110, 108, 102, 255), (88, 86, 80, 255), (130, 126, 118, 255), (72, 70, 66, 255)]

    p = com_sombra(sem_fundo(poco), lado)
    poco_estados = {
        "inteiro": p,
        "rachado": so_no_objeto(p, rachaduras(lado, R, 7)),
        "desmoronado": Image.alpha_composite(Image.alpha_composite(tinge(p, (30, 26, 22), .55), entulho(lado, R, 30, pedras, (.01, .025), .25)),
                                             cacos(p, R, 14, .2)),
        "envenenado": tinge(p, (70, 170, 40), .35),
        "congelado": tinge(p, (190, 230, 255), .45),
    }
    e = com_sombra(sem_fundo(estatua), lado)
    est_estados = {
        "inteira": e,
        "rachada": so_no_objeto(e, rachaduras(lado, R, 8)),
        "profanada": so_no_objeto(tinge(e, (30, 0, 40), .35), rachaduras(lado, R, 3, (60, 0, 70, 200))),
        "derrubada": Image.alpha_composite(Image.alpha_composite(tinge(e, (30, 28, 24), .55), entulho(lado, R, 34, pedras, (.01, .025), .28)),
                                           cacos(e, R, 16, .22)),
    }
    src = {"poco": {k: salva("poco", k, v) for k, v in poco_estados.items()},
           "estatua_alaundo": {k: salva("estatua_alaundo", k, v) for k, v in est_estados.items()}}

    pedra = {"immunities": ["poison", "psychic"], "resistances": ["piercing", "slashing"]}
    frag = {
        "poco": {
            "name": "Poço de pedra", "tipo": "imovel", "interacao": "mestre", "size": {"w": 2, "h": 2},
            # sem imunidade a veneno: o módulo só aplica as reações quando o golpe tira vida (envenenar a água)
            "actor": {"ac": 15, "hp": 40, "immunities": ["psychic"], "resistances": ["piercing", "slashing"]}, "tickSeconds": 6,
            "states": [
                {"id": "inteiro", "name": "Inteiro", "src": src["poco"]["inteiro"]},
                {"id": "rachado", "name": "Rachado", "src": src["poco"]["rachado"]},
                {"id": "desmoronado", "name": "Desmoronado", "src": src["poco"]["desmoronado"], "broken": True},
                {"id": "envenenado", "name": "Água envenenada", "src": src["poco"]["envenenado"], "ticks": 10, "then": "inteiro"},
                {"id": "congelado", "name": "Água congelada", "src": src["poco"]["congelado"], "sticky": True,
                 "light": {"bright": 0, "dim": 5, "color": "#9fdcff", "alpha": .25}},
            ],
            "reactions": [
                {"types": ["poison", "acid"], "from": ["inteiro", "rachado"], "to": "envenenado", "say": "tem a água envenenada."},
                {"types": ["radiant"], "from": ["envenenado"], "to": "inteiro", "say": "tem a água purificada."},
                {"types": ["cold"], "from": ["inteiro", "rachado", "envenenado"], "to": "congelado", "say": "tem a água congelada."},
                {"types": ["fire"], "from": ["congelado"], "to": "inteiro", "say": "tem o gelo derretido."},
                {"types": ["bludgeoning", "thunder", "force"], "from": ["inteiro"], "to": "rachado", "say": "racha."},
            ],
            "onZero": [{"to": "desmoronado", "say": "desmorona dentro de si mesmo!"}],
        },
        "estatua_alaundo": {
            "name": "Estátua de Alaundo", "tipo": "imovel", "interacao": "mestre", "size": {"w": 2, "h": 2},
            "actor": {"ac": 17, "hp": 60, **pedra}, "conhecimento": True,
            "states": [
                {"id": "inteira", "name": "Inteira", "src": src["estatua_alaundo"]["inteira"]},
                {"id": "rachada", "name": "Rachada", "src": src["estatua_alaundo"]["rachada"]},
                {"id": "profanada", "name": "Profanada", "src": src["estatua_alaundo"]["profanada"]},
                {"id": "derrubada", "name": "Derrubada", "src": src["estatua_alaundo"]["derrubada"], "broken": True},
            ],
            "reactions": [
                {"types": ["necrotic"], "from": ["inteira", "rachada"], "to": "profanada", "say": "fica manchada de sombra."},
                {"types": ["radiant"], "from": ["profanada"], "to": "inteira", "say": "volta a brilhar, purificada."},
                {"types": ["bludgeoning", "thunder", "force"], "from": ["inteira"], "to": "rachada", "say": "racha."},
            ],
            "onZero": [{"to": "derrubada", "say": "tomba e se parte! O sábio de pedra vira entulho."}],
        },
    }
    (ROOT / "tools" / "fragmentos" / "jardim.json").write_text(json.dumps(frag, indent=2, ensure_ascii=False) + "\n")
    print("ok")


if __name__ == "__main__":
    main(*sys.argv[1:4])
