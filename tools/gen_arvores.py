"""Árvores vistas de cima, montadas com fotos CC0 (tools/fontes/, créditos em mapas/CREDITOS.md).

A copa é feita com várias cópias da foto de um galho com folhas, giradas para fora a partir do centro, em
camadas (as de baixo mais escuras), com luz de cúpula (centro claro, borda escura) e sombra suave em volta.
A luz não tem direção, então o token pode ser girado no mapa para as árvores não ficarem iguais.

Gera assets/arvore_grande/ (3 x 3 quadrados) e assets/arvore_pequena/ (1 x 1), com os estados:
inteira, queimando, chamuscada, queimada (só o tronco e galhos pretos) e derrubada (toco e tronco caído).
Uso: python3 tools/gen_arvores.py"""
import math, pathlib, random
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent.parent
F = ROOT / "tools" / "fontes"
PX = 200  # pixels por quadrado

GALHO = Image.open(F / "galho.png").convert("RGBA")
CASCA = ImageEnhance.Brightness(Image.open(F / "casca.jpg").convert("RGB")).enhance(1.35)


def rgba(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def arr(im):
    return np.asarray(im, dtype=np.float32)


def tint(im, mul, add=(0, 0, 0)):
    """Multiplica e soma por canal (RGB), mantendo o alfa."""
    a = arr(im).copy()
    a[..., :3] = a[..., :3] * np.array(mul, np.float32) + np.array(add, np.float32)
    return rgba(a)


def galho(length, R, mul=(1, 1, 1), thin=1.0):
    """Um galho com a base na esquerda, com 'length' px, cor ajustada e espelhado ao acaso."""
    g = GALHO
    if R.random() < .5:
        g = g.transpose(Image.FLIP_TOP_BOTTOM)
    h = max(4, int(g.height * length / g.width * thin))
    g = g.resize((int(length), h), Image.LANCZOS)
    return tint(g, mul)


def paste_rot(canvas, sprite, cx, cy, ang, base_off):
    """Cola o sprite girado 'ang' graus em volta da base (meio da borda esquerda), com a base em (cx, cy) + base_off na direção."""
    w, h = sprite.size
    big = Image.new("RGBA", (w * 2, w * 2))
    big.alpha_composite(sprite, (w, w - h // 2))
    big = big.rotate(-ang, resample=Image.BICUBIC)
    r = math.radians(ang)
    x = cx + math.cos(r) * base_off - w
    y = cy + math.sin(r) * base_off - w
    canvas.alpha_composite(big, (int(x), int(y)))


def dome(size, radius, strength=.55):
    """Luz de cúpula: 1 no centro, mais escuro na borda (sem direção)."""
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    r = np.sqrt((xx - size / 2) ** 2 + (yy - size / 2) ** 2) / radius
    z = np.sqrt(np.clip(1 - r ** 2, 0, 1))
    return (1 - strength) + strength * z


def with_shadow(canopy, blur, opacity=.55, grow=1.0):
    """Sombra suave e centralizada embaixo da copa (sem direção, para poder girar o token)."""
    a = canopy.getchannel("A")
    if grow != 1.0:
        w, h = a.size
        s = a.resize((int(w * grow), int(h * grow)), Image.BILINEAR)
        a = Image.new("L", (w, h))
        a.paste(s, ((w - s.width) // 2, (h - s.height) // 2))
    a = a.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * opacity))
    sh = Image.new("RGBA", canopy.size, (8, 10, 4, 0))
    sh.putalpha(a)
    sh.alpha_composite(canopy)
    return sh


# a foto do galho é escura (verde de sombra): este ganho leva o tom médio para um verde de folha ao sol
GANHO = (2.3, 2.85, 3.1)


def silhouette(size, radius, R, bumps):
    """Contorno da copa: um círculo com 'bumps' calombos na borda, levemente desfocado."""
    m = Image.new("L", (size, size))
    d = ImageDraw.Draw(m)
    c = size / 2
    r0 = radius * .74
    d.ellipse((c - r0, c - r0, c + r0, c + r0), fill=255)
    for i in range(bumps):
        t = (i + R.uniform(-.3, .3)) / bumps * 2 * math.pi
        rb = radius * R.uniform(.24, .34)
        dist = radius - rb * R.uniform(.95, 1.1)
        x, y = c + math.cos(t) * dist, c + math.sin(t) * dist
        d.ellipse((x - rb, y - rb, x + rb, y + rb), fill=255)
    return m.filter(ImageFilter.GaussianBlur(radius * .02))


def clump(R, diameter, mul):
    """Um tufo de folhas: um pedaço da foto do galho, girado, com luz de cúpula própria (dá o volume)."""
    g = GALHO
    w = int(g.width * R.uniform(.22, .42))
    x0 = R.randint(0, g.width - w)
    piece = g.crop((x0, 0, x0 + w, g.height))
    piece = piece.crop(piece.getbbox() or (0, 0, w, g.height))
    if R.random() < .5:
        piece = piece.transpose(Image.FLIP_LEFT_RIGHT)
    piece = piece.rotate(R.uniform(0, 360), expand=True, resample=Image.BICUBIC)
    s = max(4, int(diameter))
    piece = piece.resize((s, s), Image.LANCZOS)
    a = arr(piece)
    a[..., :3] *= np.array([m * k for m, k in zip(mul, GANHO)], np.float32)
    a[..., :3] *= dome(s, s / 2, .5)[..., None]
    # bordas do tufo um pouco transparentes, para os tufos se misturarem
    a[..., 3] *= np.clip(dome(s, s / 2, 1.0) * 1.6, 0, 1)
    return rgba(a)


def canopy(size, radius, seed, palette, layers, thin=1.0, bumps=9):
    """Copa: 'layers' = [(quantos tufos, tamanho do tufo em fração do raio, brilho)], de baixo para cima.
    Os tufos de cima ficam mais perto do centro de cada calombo, como numa copa de verdade."""
    R = random.Random(seed)
    sil = silhouette(size, radius, R, bumps)
    m = arr(sil) / 255
    ys, xs = np.nonzero(m > .5)
    c = Image.new("RGBA", (size, size))
    # fundo escuro dentro do contorno, para não sobrar buraco
    under = Image.new("RGBA", (size, size), (int(30 * GANHO[0] * .5), int(36 * GANHO[1] * .5), int(13 * GANHO[2] * .5), 255))
    under.putalpha(sil.filter(ImageFilter.GaussianBlur(radius * .03)).point(lambda v: int(v * .95)))
    c.alpha_composite(under)
    for li, (n, frac, bright) in enumerate(layers):
        top = li / max(1, len(layers) - 1)
        for _ in range(int(n)):
            # camadas de cima puxam para o centro
            while True:
                i = R.randrange(len(xs))
                x, y = xs[i], ys[i]
                if math.hypot(x - size / 2, y - size / 2) <= radius * (1 - .45 * top) or R.random() < .15:
                    break
            col = [bright * R.uniform(.85, 1.15) * p for p in R.choice(palette)]
            dia = radius * frac * R.uniform(.75, 1.25) * thin
            t = clump(R, dia, col)
            c.alpha_composite(t, (int(x - t.width / 2), int(y - t.height / 2)))
    a = arr(c)
    # recorta pelo contorno (um pouco maior: as folhas passam da borda)
    grow = arr(sil.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(radius * .03))) / 255
    a[..., 3] *= grow
    a[..., :3] *= dome(size, radius, .25)[..., None]
    return rgba(a)


def trunk_disc(r):
    """Corte do tronco (toco) visto de cima: anéis claros e casca em volta."""
    s = int(r * 2 + 4)
    im = Image.new("RGBA", (s, s))
    d = ImageDraw.Draw(im)
    bark = CASCA.resize((s, s))
    m = Image.new("L", (s, s))
    ImageDraw.Draw(m).ellipse((2, 2, s - 2, s - 2), fill=255)
    im.paste(bark, (0, 0), m)
    k = .78
    d.ellipse((s / 2 - r * k, s / 2 - r * k, s / 2 + r * k, s / 2 + r * k), fill=(176, 138, 92, 255))
    for f in (.62, .44, .26, .1):
        d.ellipse((s / 2 - r * f, s / 2 - r * f, s / 2 + r * f, s / 2 + r * f), outline=(124, 90, 52, 255), width=max(1, int(r * .06)))
    return im


def log(length, width, ang):
    """Tronco caído com textura de casca, sombreado como cilindro, girado 'ang' graus (base na esquerda)."""
    L, W_ = int(length), int(width)
    bark = CASCA.resize((max(L, 64), max(L, 64))).crop((0, 0, L, W_))
    a = arr(bark.convert("RGBA"))
    yy = np.linspace(-1, 1, W_, dtype=np.float32)[:, None]
    a[..., :3] *= (.45 + .75 * np.sqrt(np.clip(1 - yy ** 2, 0, 1)))[..., None]
    im = rgba(a)
    m = Image.new("L", (L, W_))
    ImageDraw.Draw(m).rounded_rectangle((0, 0, L - 1, W_ - 1), radius=W_ // 2, fill=255)
    im.putalpha(m)
    end = trunk_disc(W_ / 2 - 1).resize((int(W_ * .55), W_))  # ponta quebrada (o corte visto de lado)
    im.alpha_composite(end, (0, 0))
    big = Image.new("RGBA", (L * 2, L * 2))
    big.alpha_composite(im, (L, L - W_ // 2))
    return big.rotate(-ang, resample=Image.BICUBIC), L


def fire_on(im, radius, seed, n):
    """Copa pegando fogo: focos de brasa (brilho laranja somado à imagem), chamas do Kenney Particle Pack (CC0)
    pintadas de amarelo a vermelho e um pouco de fumaça."""
    R = random.Random(seed)
    size = im.width
    base = arr(im).copy()
    glow = np.zeros((size, size), np.float32)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    for _ in range(n):
        rr, t = radius * math.sqrt(R.random()) * .85, R.uniform(0, 2 * math.pi)
        x, y = size / 2 + rr * math.cos(t), size / 2 + rr * math.sin(t)
        s = radius * R.uniform(.04, .1)
        glow += np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * s * s)) * R.uniform(.5, .9)
    glow = np.clip(glow, 0, 1.0)[..., None] * .8
    fire = np.array([255, 120, 25], np.float32)
    hot = np.array([255, 230, 150], np.float32)
    col = fire * np.clip(glow * 1.3, 0, 1) + (hot - fire) * np.clip(glow - .6, 0, 1)
    a3 = base[..., 3:4] / 255
    base[..., :3] = 255 - (255 - base[..., :3]) * (1 - np.clip(col / 255, 0, 1) * a3)  # screen
    out = rgba(base)
    fl = [Image.open(F / f).convert("RGBA") for f in ("flame_02.png", "flame_05.png", "fire_01.png")]
    for _ in range(n):
        f = R.choice(fl)
        s = int(radius * R.uniform(.18, .34))
        f = f.resize((s, s)).rotate(R.uniform(0, 360), resample=Image.BICUBIC)
        a = arr(f)
        lum = a[..., 3:4] / 255
        a[..., :3] = np.array([255, 90 + 80 * R.random(), 10], np.float32) * (1 - lum) + np.array([255, 215, 120], np.float32) * lum
        a[..., 3] *= .85
        rr, t = radius * math.sqrt(R.random()) * .8, R.uniform(0, 2 * math.pi)
        out.alpha_composite(rgba(a), (int(size / 2 + rr * math.cos(t) - s / 2), int(size / 2 + rr * math.sin(t) - s / 2)))
    smoke = Image.open(F / "smoke_02.png").convert("RGBA")
    for _ in range(3):
        s = int(radius * R.uniform(.7, 1.0))
        sm = tint(smoke.resize((s, s)), (.2, .19, .18))
        sm.putalpha(sm.getchannel("A").point(lambda v: int(v * .2)))
        out.alpha_composite(sm.rotate(R.uniform(0, 360)), (int(size / 2 + R.uniform(-.4, .4) * radius - s / 2), int(size / 2 + R.uniform(-.4, .4) * radius - s / 2)))
    return out


def burn_tint(im, amount):
    """Escurece e puxa para marrom/laranja (folhas secando no fogo)."""
    a = arr(im).copy()
    lum = a[..., :3].mean(axis=2, keepdims=True)
    brown = np.concatenate([lum * 1.25, lum * .78, lum * .35], axis=2)
    a[..., :3] = a[..., :3] * (1 - amount) + brown * amount
    return rgba(a)


def charred(size, radius, seed, n, thin=.55):
    """Galhos pretos e finos, sem folhas, saindo do tronco."""
    R = random.Random(seed)
    c = Image.new("RGBA", (size, size))
    d = ImageDraw.Draw(c)
    for i in range(n):
        ang = (i + R.random()) / n * 2 * math.pi
        x, y = size / 2, size / 2
        L = radius * R.uniform(.55, .95)
        w = radius * .09
        steps = 6
        for s in range(steps):
            nx = x + math.cos(ang) * L / steps
            ny = y + math.sin(ang) * L / steps
            col = (28 + R.randint(0, 14), 22 + R.randint(0, 10), 18, 255)
            d.line((x, y, nx, ny), fill=col, width=max(1, int(w)))
            if R.random() < .45:  # galhinho
                a2 = ang + R.choice((-1, 1)) * R.uniform(.4, .9)
                d.line((nx, ny, nx + math.cos(a2) * L * .22, ny + math.sin(a2) * L * .22), fill=col, width=max(1, int(w * .5)))
            x, y, w = nx, ny, w * .78
            ang += R.uniform(-.25, .25)
    # folhas queimadas que ficaram, bem escuras
    left = canopy(size, radius * .9, seed + 1, [(.35, .25, .15)], [(n * 2, .3, .45)])
    left.putalpha(left.getchannel("A").point(lambda v: int(v * .45)))
    c = Image.alpha_composite(left, c)
    return c


def scorch(size, radius, seed):
    """Marca de queimado no chão em volta (Kenney scorch, CC0), cinza escuro."""
    s = int(radius * 2.2)
    sc = Image.open(F / "scorch_01.png").convert("RGBA").resize((s, s)).rotate(random.Random(seed).uniform(0, 360))
    sc = tint(sc, (.18, .17, .16))
    sc.putalpha(sc.getchannel("A").point(lambda v: int(v * .8)))
    out = Image.new("RGBA", (size, size))
    out.alpha_composite(sc, ((size - s) // 2, (size - s) // 2))
    return out


TIPOS = {
    "arvore_grande": {
        "cells": 3, "radius": 1.42, "seed": 11, "trunk": .2, "bumps": 10,
        # tons de verde de carvalho, um pouco amarelados no alto
        "palette": [(1.0, 1.0, 1.0), (.95, 1.05, .85), (1.1, 1.05, .8), (.9, .98, 1.05)],
        "layers": [(70, .42, .5), (60, .36, .72), (46, .3, .92), (30, .24, 1.1)],
        "thin": 1.0,
    },
    "arvore_pequena": {
        "cells": 1, "radius": .5, "seed": 23, "trunk": .1, "bumps": 7,
        # verde mais claro e vivo (árvore nova)
        "palette": [(1.1, 1.18, .9), (1.2, 1.2, .8), (1.0, 1.15, 1.0)],
        "layers": [(26, .5, .6), (22, .42, .85), (16, .34, 1.1)],
        "thin": 1.0,
    },
}


def gerar(nome, t):
    size = int(t["cells"] * PX)
    rad = t["radius"] * PX * .96
    out = ROOT / "assets" / nome
    out.mkdir(parents=True, exist_ok=True)
    # a copa é desenhada maior e reduzida, para o galho da foto não ficar enorme na árvore pequena
    blur = rad * .08

    cop = canopy(size, rad * .93, t["seed"], t["palette"], t["layers"], thin=t["thin"], bumps=t["bumps"])
    with_shadow(cop, blur, .6, 1.04).save(out / f"{nome}_inteira.webp", quality=88, method=6)

    ch = burn_tint(cop, .5)
    sc = scorch(size, rad * .8, t["seed"])
    base = Image.alpha_composite(sc, with_shadow(ch, blur, .55, 1.04))
    base.save(out / f"{nome}_chamuscada.webp", quality=88, method=6)

    q = Image.alpha_composite(sc, with_shadow(burn_tint(cop, .45), blur, .55, 1.04))
    q = fire_on(q, rad, t["seed"], 26 if t["cells"] > 1 else 9)
    q.save(out / f"{nome}_queimando.webp", quality=88, method=6)

    dead = Image.alpha_composite(scorch(size, rad * .95, t["seed"] + 3), with_shadow(charred(size, rad * .85, t["seed"], 11 if t["cells"] > 1 else 7), blur * .6, .5))
    r_ = PX * t["trunk"] * t["cells"] ** .5 * .7  # topo do tronco carbonizado (sem o corte com anéis)
    tr = Image.new("RGBA", (int(r_ * 2 + 4),) * 2)
    m = Image.new("L", tr.size)
    ImageDraw.Draw(m).ellipse((2, 2, tr.width - 2, tr.height - 2), fill=255)
    tr.paste(tint(CASCA.resize(tr.size).convert("RGBA"), (.3, .25, .22)), (0, 0), m.filter(ImageFilter.GaussianBlur(1.5)))
    dead.alpha_composite(tr, ((size - tr.width) // 2, (size - tr.height) // 2))
    dead.save(out / f"{nome}_queimada.webp", quality=88, method=6)

    # derrubada: toco no centro e o tronco caído na diagonal, com a copa amassada na ponta
    R = random.Random(t["seed"] + 9)
    fall = Image.new("RGBA", (size, size))
    ang = 38
    tw = PX * t["trunk"] * 2 * t["cells"] ** .5 * .9
    length = size * .44
    lg, L = log(length, tw, ang)
    r = math.radians(ang)
    tip = (size / 2 + math.cos(r) * length, size / 2 + math.sin(r) * length)
    crown = canopy(size, rad * .42, t["seed"] + 5, t["palette"], [(int(t["layers"][0][0] * .5), t["layers"][0][1] * 1.4, .6), (int(t["layers"][1][0] * .4), t["layers"][1][1] * 1.4, .9)], bumps=7)
    crown = with_shadow(burn_tint(crown, .2), blur * .7, .5)
    fall.alpha_composite(crown, (int(tip[0] - size / 2), int(tip[1] - size / 2)))
    sl = tint(lg, (0, 0, 0))
    sl.putalpha(sl.getchannel("A").filter(ImageFilter.GaussianBlur(blur * .4)).point(lambda v: int(v * .5)))
    fall.alpha_composite(sl, (int(size / 2 - L + tw * .12), int(size / 2 - L + tw * .18)))
    fall.alpha_composite(lg, (int(size / 2 - L), int(size / 2 - L)))
    stump = trunk_disc(tw / 2)
    fall.alpha_composite(stump, (int(size / 2 - stump.width / 2), int(size / 2 - stump.height / 2)))
    for _ in range(6 if t["cells"] > 1 else 2):  # lascas
        x, y = size / 2 + R.uniform(-1, 1) * tw * 1.3, size / 2 + R.uniform(-1, 1) * tw * 1.3
        ImageDraw.Draw(fall).polygon([(x, y), (x + R.uniform(4, 12), y + R.uniform(-3, 3)), (x + R.uniform(2, 6), y + R.uniform(4, 8))], fill=(190, 150, 100, 255))
    fall.save(out / f"{nome}_derrubada.webp", quality=88, method=6)
    print(nome, size)


if __name__ == "__main__":
    for nome, t in TIPOS.items():
        gerar(nome, t)
