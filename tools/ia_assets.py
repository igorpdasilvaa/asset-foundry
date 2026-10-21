"""Assets a partir de imagens geradas no ia-orc (SDXL): a mesma linha do jardim do Pátio.

Cada asset tem uma imagem-base (o objeto inteiro, vista de cima, fundo branco) e os estados são feitos a partir dela,
para combinar: fogo animado, carvão, cacos com a textura do próprio objeto, rachaduras, gelo, água, ácido...
Estados que mudam a forma (porta aberta, estante tombada, vela apagada) podem ter imagem própria ("img" na receita).

Receitas em tools/ia_assets.json e tools/ia_receitas/*.json (um arquivo por grupo):
  { "<asset>": { "prompt": "...", "jobs": {"base": ["<job>", <índice>], "<extra>": [...]},
                 "estados": { "<estado>": ["efeito", {parâmetros}] ou {"img": "<extra>", "efeitos": [...]} } } }
O tamanho em quadrados vem do assets.json. Saída: assets/<asset>/<asset>_<estado>.webp (ou .webm no fogo animado),
e o "src" de cada estado é atualizado no assets.json (e no fragmento, se o asset vier de um).

Uso: python3 tools/ia_assets.py [asset ...] [--so-imagens]     (sem nomes: todos da receita)"""
import json, math, pathlib, random, subprocess, sys, tempfile, zlib
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTES = ROOT / "tools" / "fontes"
DOWN = pathlib.Path.home() / "Downloads" / "ia-orc"
S = 200  # pixels por quadrado
ESTILO = ("seen from directly above, top-down 2D fantasy battlemap asset, hand painted digital art like Forgotten Adventures, "
          "isolated on plain white background, centered, soft lighting")
NEGATIVO = "side view, front view, perspective, isometric, ground, floor, shadow on background, text, watermark, frame, multiple objects"


# ---------- base ----------

def sem_fundo(src, tol=38, come=11):
    """Tira o fundo claro ligado às bordas (flood fill) e recorta no conteúdo."""
    im = Image.open(src).convert("RGB")
    w, h = im.size
    cantos = [im.getpixel(p) for p in [(2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)]]
    if sum(min(c) > 200 for c in cantos) < 2:  # a imagem não tem fundo claro: o objeto ocupa tudo (tampo de mesa, piso)
        return im.convert("RGBA")
    marca = im.copy()
    for p in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        ImageDraw.floodfill(marca, p, (255, 0, 255), thresh=tol)
    r, g, b = marca.split()
    fundo = ImageChops.multiply(ImageChops.multiply(r.point(lambda v: 255 if v == 255 else 0), b.point(lambda v: 255 if v == 255 else 0)),
                                g.point(lambda v: 255 if v == 0 else 0))
    alpha = ImageOps.invert(fundo)
    # branco quase puro que o flood fill não alcança (dentro de alças, entre pernas de cadeira) também é fundo
    branco = im.convert("L").point(lambda v: 255 if v > 238 else 0)
    alpha = ImageChops.subtract(alpha, branco).filter(ImageFilter.MinFilter(come)).filter(ImageFilter.GaussianBlur(2))
    out = im.convert("RGBA")
    out.putalpha(alpha)
    return out.crop(alpha.point(lambda v: 255 if v > 30 else 0).getbbox())


def encaixa(obj, w, h, margem=.05, esticar=False, sombra=True):
    """Objeto no quadro de w x h quadrados, com margem e sombra suave. esticar: ocupa o quadro todo (paredes, pisos)."""
    W, H = int(w * S), int(h * S)
    mw, mh = int(W * margem), int(H * margem)
    if esticar:
        obj = obj.resize((W - 2 * mw, H - 2 * mh), Image.LANCZOS)
    else:
        k = min((W - 2 * mw) / obj.width, (H - 2 * mh) / obj.height)
        obj = obj.resize((max(1, int(obj.width * k)), max(1, int(obj.height * k))), Image.LANCZOS)
    q = Image.new("RGBA", (W, H))
    x, y = (W - obj.width) // 2, (H - obj.height) // 2
    if sombra:
        s = Image.new("RGBA", obj.size, (0, 0, 0, 0))
        s.putalpha(obj.getchannel("A").point(lambda v: int(v * .5)))
        q.alpha_composite(s.filter(ImageFilter.GaussianBlur(max(4, W // 60))), (x + W // 70, y + H // 50))
    q.alpha_composite(obj, (x, y))
    return q


def mascara(base, limite=200):
    return base.getchannel("A").point(lambda v: 255 if v > limite else 0)


def so_no_objeto(base, camada):
    c = Image.new("RGBA", base.size)
    c.paste(camada, (0, 0), ImageChops.multiply(camada.getchannel("A"), mascara(base)))
    out = base.copy()
    out.alpha_composite(c)
    return out


def tinge(base, cor, forca):
    t = Image.new("RGBA", base.size, tuple(cor) + (0,))
    t.putalpha(mascara(base).point(lambda v: int(v * forca)))
    out = base.copy()
    out.alpha_composite(t)
    return out


def escurece(base, k):
    rgb = ImageEnhance.Brightness(base.convert("RGB")).enhance(k)
    out = rgb.convert("RGBA")
    out.putalpha(base.getchannel("A"))
    return out


def dessatura(base, k):
    rgb = ImageEnhance.Color(base.convert("RGB")).enhance(k)
    out = rgb.convert("RGBA")
    out.putalpha(base.getchannel("A"))
    return out


def sprite(nome, cor, tam, ang=0, alpha=1.0):
    """Sprite da Kenney (branco em fundo preto) tingido: o brilho vira transparência."""
    im = Image.open(FONTES / f"{nome}.png").convert("RGBA")
    s = ImageChops.multiply(im.getchannel("A"), im.convert("L")).resize((int(tam), int(tam)), Image.LANCZOS)
    out = Image.new("RGBA", s.size, tuple(cor) + (0,))
    out.putalpha(s.point(lambda v: int(v * alpha)))
    return out.rotate(ang, resample=Image.BICUBIC) if ang else out


def pontos_no_objeto(base, R, n, borda=.15):
    m = mascara(base)
    W, H = base.size
    pts = []
    for _ in range(n * 40):
        x, y = R.uniform(borda, 1 - borda) * W, R.uniform(borda, 1 - borda) * H
        if m.getpixel((int(x), int(y))):
            pts.append((x, y))
            if len(pts) == n:
                break
    return pts or [(W / 2, H / 2)]


# ---------- efeitos ----------

def rachaduras(base, R, n=6, cor=(20, 18, 16, 235)):
    W, H = base.size
    lado = min(W, H)
    c = Image.new("RGBA", base.size)
    d = ImageDraw.Draw(c)
    for x, y in pontos_no_objeto(base, R, n):
        ang = R.uniform(0, 2 * math.pi)
        pts = [(x, y)]
        for _ in range(R.randint(5, 9)):
            ang += R.uniform(-.7, .7)
            L = R.uniform(.03, .07) * lado
            x, y = x + L * math.cos(ang), y + L * math.sin(ang)
            pts.append((x, y))
        d.line(pts, fill=tuple(cor), width=max(2, lado // 140), joint="curve")
    return so_no_objeto(base, c)


def cacos(base, R, n=14, espalha=.22, tam=(.06, .14), alongado=1.0):
    """Pedaços recortados do próprio objeto, girados e espalhados (entulho, lascas)."""
    W, H = base.size
    lado = min(W, H)
    out = Image.new("RGBA", base.size)
    for cx, cy in pontos_no_objeto(base, R, n, .1):
        r = R.uniform(*tam) * lado
        k = R.randint(4, 7)
        a0 = R.uniform(0, math.pi)
        pts = [(r * alongado + r * alongado * R.uniform(.55, 1) * math.cos(a0 + i * 2 * math.pi / k), r + r * R.uniform(.55, 1) * math.sin(a0 + i * 2 * math.pi / k)) for i in range(k)]
        m = Image.new("L", (int(2 * r * alongado), int(2 * r)))
        ImageDraw.Draw(m).polygon(pts, fill=255)
        x0, y0 = int(cx - r * alongado), int(cy - r)
        peca = base.crop((x0, y0, x0 + m.width, y0 + m.height))
        peca.putalpha(ImageChops.multiply(peca.getchannel("A"), m))
        peca = peca.rotate(R.uniform(0, 360), expand=True, resample=Image.BICUBIC)
        x = int(W / 2 + R.gauss(0, espalha * W) - peca.width / 2)
        y = int(H / 2 + R.gauss(0, espalha * H) - peca.height / 2)
        s = Image.new("RGBA", peca.size, (0, 0, 0, 0))
        s.putalpha(peca.getchannel("A").point(lambda v: int(v * .5)))
        out.alpha_composite(s.filter(ImageFilter.GaussianBlur(4)), (x + 4, y + 6))
        out.alpha_composite(peca, (x, y))
    return out


def quebrado(base, R, n=16, alongado=1.0, resto=.35):
    """Objeto despedaçado no lugar: um resto escuro onde ele estava, pedaços grandes perto e lascas pequenas em volta."""
    out = Image.new("RGBA", base.size)
    if resto:
        out.alpha_composite(_apaga(escurece(base, .45), resto))
    out.alpha_composite(cacos(base, R, max(4, n // 3), espalha=.1, alongado=alongado, tam=(.12, .2)))
    out.alpha_composite(cacos(base, R, n, espalha=.18, alongado=alongado, tam=(.04, .09)))
    return out


def _apaga(im, k):
    out = im.copy()
    out.putalpha(im.getchannel("A").point(lambda v: int(v * k)))
    return out


def fuligem(base, R, n=5, forca=.8):
    """Marcas de queimado (scorch da Kenney) sobre o objeto."""
    lado = min(base.size)
    c = Image.new("RGBA", base.size)
    for x, y in pontos_no_objeto(base, R, n):
        s = sprite("scorch_01", (12, 9, 7), lado * R.uniform(.5, .85), R.uniform(0, 360), forca)
        c.alpha_composite(s, (int(x - s.width / 2), int(y - s.height / 2)))
    return so_no_objeto(base, c)


def brasas(base, R, n=24):
    lado = min(base.size)
    c = Image.new("RGBA", base.size)
    d = ImageDraw.Draw(c)
    for x, y in pontos_no_objeto(base, R, n, .08):
        r = R.uniform(.004, .012) * lado
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, R.randint(90, 160), 30, 230))
    return Image.alpha_composite(base, c.filter(ImageFilter.GaussianBlur(1)))


def chamas(base, R, fase=0.0, n=None, escala=1.0):
    """Fogo sobre o objeto (sprites da Kenney em amarelo/laranja/vermelho). fase anima o tremor."""
    W, H = base.size
    lado = min(W, H)
    R2 = random.Random(R.random())
    out = base.copy()
    brilho = Image.new("RGBA", base.size)
    ImageDraw.Draw(brilho).ellipse((W * .05, H * .05, W * .95, H * .95), fill=(255, 110, 20, 110))
    out.alpha_composite(brilho.filter(ImageFilter.GaussianBlur(lado / 7)))
    n = n or max(4, round(3 * W * H / (S * S)) + 2)
    for i, (x, y) in enumerate(pontos_no_objeto(base, R2, n)):
        t = fase * 2 * math.pi + i
        tam = lado * R2.uniform(.6, .9) * escala * (1 + .15 * math.sin(t * 1.7))
        for nome, cor, k in (("fire_01", (235, 50, 15), 1.0), ("fire_01", (255, 120, 25), .8), ("flame_02", (255, 175, 45), .6), ("flame_02", (255, 225, 120), .35)):
            s = sprite(nome, cor, tam * k, 8 * math.sin(t + k), 1.0)
            out.alpha_composite(s, (int(x - s.width / 2 + 3 * math.sin(t * 2)), int(y - s.height * .65)))
    return out


def gelo(base, R):
    lado = min(base.size)
    out = tinge(dessatura(base, .5), (200, 235, 255), .45)
    c = Image.new("RGBA", base.size)
    d = ImageDraw.Draw(c)
    for x, y in pontos_no_objeto(base, R, 40, .05):
        a = R.uniform(0, math.pi)
        L = R.uniform(.02, .06) * lado
        for k in range(3):
            aa = a + k * math.pi / 3
            d.line((x - L * math.cos(aa), y - L * math.sin(aa), x + L * math.cos(aa), y + L * math.sin(aa)), fill=(240, 250, 255, 200), width=2)
    return so_no_objeto(out, c.filter(ImageFilter.GaussianBlur(.6)))


def molhado(base, R):
    out = tinge(escurece(base, .8), (40, 70, 110), .25)
    lado = min(base.size)
    c = Image.new("RGBA", base.size)
    d = ImageDraw.Draw(c)
    for x, y in pontos_no_objeto(base, R, 30, .06):
        r = R.uniform(.006, .018) * lado
        d.ellipse((x - r, y - r, x + r, y + r), fill=(200, 230, 255, 160))
    return so_no_objeto(out, c)


def manchas(base, R, cor, n=10, tam=(.08, .2), forca=.7):
    lado = min(base.size)
    c = Image.new("RGBA", base.size)
    d = ImageDraw.Draw(c)
    for x, y in pontos_no_objeto(base, R, n):
        r = R.uniform(*tam) * lado
        d.ellipse((x - r, y - r * R.uniform(.6, 1), x + r, y + r), fill=tuple(cor) + (int(255 * forca),))
    return so_no_objeto(base, c.filter(ImageFilter.GaussianBlur(lado / 60)))


def aura(base, cor, raio=.06, forca=.8):
    lado = min(base.size)
    a = mascara(base).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(lado * raio))
    g = Image.new("RGBA", base.size, tuple(cor) + (0,))
    g.putalpha(a.point(lambda v: int(v * forca)))
    out = g
    out.alpha_composite(base)
    return out


def flechas(base, R, n=4):
    lado = min(base.size)
    c = Image.new("RGBA", base.size)
    d = ImageDraw.Draw(c)
    for x, y in pontos_no_objeto(base, R, n):
        a = R.uniform(0, 2 * math.pi)
        L = .32 * lado
        x2, y2 = x + L * math.cos(a), y + L * math.sin(a)
        d.line((x + 2, y + 4, x2 + 2, y2 + 4), fill=(0, 0, 0, 90), width=max(4, lado // 60))
        d.line((x, y, x2, y2), fill=(110, 76, 40, 255), width=max(4, lado // 70))
        for k in (0, .04, .08):
            px, py = x2 - k * lado * math.cos(a), y2 - k * lado * math.sin(a)
            for s in (-1, 1):
                d.line((px, py, px - .07 * lado * math.cos(a + s * .45), py - .07 * lado * math.sin(a + s * .45)), fill=(235, 230, 215, 255), width=max(3, lado // 90))
        d.ellipse((x - lado * .015, y - lado * .015, x + lado * .015, y + lado * .015), fill=(40, 30, 20, 255))
    return Image.alpha_composite(base, c)


def cortado(base, R, folga=.08):
    """Partido ao meio no sentido do comprimento: as duas metades se afastam e giram um pouco."""
    W, H = base.size
    out = Image.new("RGBA", base.size)
    vertical = W >= H  # corta atravessando o lado maior
    for lado in (0, 1):
        caixa = (0, 0, W // 2, H) if vertical and lado == 0 else (W // 2, 0, W, H) if vertical else (0, 0, W, H // 2) if lado == 0 else (0, H // 2, W, H)
        peca = Image.new("RGBA", base.size)
        peca.paste(base.crop(caixa), caixa[:2])
        d = (-1 if lado == 0 else 1) * folga
        peca = peca.rotate(R.uniform(3, 8) * (-d / abs(d)), resample=Image.BICUBIC, center=(W / 2, H / 2))
        out.alpha_composite(peca, (int(d * W) if vertical else 0, 0 if vertical else int(d * H)))
    return out


def poca(base, R, cor=(150, 95, 30), forca=.75):
    """Líquido derramado embaixo do objeto (cerveja do barril, água do cocho)."""
    W, H = base.size
    c = Image.new("RGBA", base.size)
    d = ImageDraw.Draw(c)
    for _ in range(9):
        cx, cy = W / 2 + R.gauss(0, W * .12), H / 2 + R.gauss(0, H * .12)
        rx, ry = R.uniform(.12, .3) * W, R.uniform(.1, .25) * H
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=tuple(cor) + (int(255 * forca),))
    c = c.filter(ImageFilter.GaussianBlur(min(W, H) / 40))
    c.alpha_composite(base)
    return c


def _job_png(job, i):
    return sorted((DOWN / job).glob("*.png"))[i]


def _caixa_obj(base):
    return mascara(base, 30).getbbox() or (0, 0) + base.size


def _so_borda(src, tol=38, limite=215, come=9):
    """Como o sem_fundo, mas só tira o fundo claro ligado à borda da imagem (flood fill de todo ponto claro da beira)
    e mantém os brancos de dentro (casulos, páginas, lençol)."""
    im = Image.open(src).convert("RGB")
    w, h = im.size
    marca = im.copy()
    for p in [(x, y) for x in range(0, w, 8) for y in (0, h - 1)] + [(x, y) for y in range(0, h, 8) for x in (0, w - 1)]:
        c = marca.getpixel(p)
        if min(c) > limite and c != (255, 0, 255):
            ImageDraw.floodfill(marca, p, (255, 0, 255), thresh=tol)
    r, g, b = marca.split()
    fundo = ImageChops.multiply(ImageChops.multiply(r.point(lambda v: 255 if v == 255 else 0), b.point(lambda v: 255 if v == 255 else 0)),
                                g.point(lambda v: 255 if v == 0 else 0))
    alpha = ImageOps.invert(fundo).filter(ImageFilter.MinFilter(come)).filter(ImageFilter.GaussianBlur(2))
    out = im.convert("RGBA")
    out.putalpha(alpha)
    return out.crop(alpha.point(lambda v: 255 if v > 30 else 0).getbbox())


def outra(base, job, i, girar=0, tol=38, margem=.05, sombra=True, so_borda=False, de=None, escala_y=1.0):
    """Troca a imagem por outra do ia-orc (girada), encaixada no mesmo quadro. Ex.: estante tombada = a frente deitada.
    so_borda: recorte que mantém os brancos de dentro do objeto (ver _so_borda).
    de: frações x0,y0,x1,y1 — usa só esse pedaço da imagem (uma peça de uma folha com várias).
    escala_y: achata (<1) ou estica a peça na vertical antes de encaixar."""
    src = _job_png(job, i)
    with tempfile.TemporaryDirectory() as tmp:
        if de:
            im = Image.open(src).convert("RGB")
            w, h = im.size
            src = pathlib.Path(tmp) / "pedaco.png"
            im.crop((int(de[0] * w), int(de[1] * h), int(de[2] * w), int(de[3] * h))).save(src)
        obj = _so_borda(src, tol) if so_borda else sem_fundo(src, tol)
    if escala_y != 1.0:  # achata/estica na vertical (cadeira vista meio de frente → mais "de cima")
        obj = obj.resize((obj.width, max(1, int(obj.height * escala_y))), Image.LANCZOS)
    if girar:
        obj = obj.rotate(girar, expand=True, resample=Image.BICUBIC)
    return encaixa(obj, base.width / S, base.height / S, margem, False, sombra)


def cola(base, job, i, de, para, girar=0, recorta_fundo=False):
    """Cola um recorte de outra imagem (de: frações x0,y0,x1,y1 da fonte) num retângulo do objeto
    (para: frações da caixa do objeto). Híbridos: lombadas de uma estante vista de frente sobre o tampo visto de cima."""
    fonte = sem_fundo(_job_png(job, i)) if recorta_fundo else Image.open(_job_png(job, i)).convert("RGBA")
    fw, fh = fonte.size
    pedaco = fonte.crop((int(de[0] * fw), int(de[1] * fh), int(de[2] * fw), int(de[3] * fh)))
    if girar:
        pedaco = pedaco.rotate(girar, expand=True, resample=Image.BICUBIC)
    x0, y0, x1, y1 = _caixa_obj(base)
    bw, bh = x1 - x0, y1 - y0
    r = (int(x0 + para[0] * bw), int(y0 + para[1] * bh), int(x0 + para[2] * bw), int(y0 + para[3] * bh))
    pedaco = pedaco.resize((r[2] - r[0], r[3] - r[1]), Image.LANCZOS)
    out = base.copy()
    out.alpha_composite(pedaco, r[:2])
    return out


def faixa_h(base, altura=.62, centro=.5, borda=.045, sombra=.35):
    """Segmento que emenda nas laterais (balcão em fileira): a imagem vira emendável na horizontal e só fica uma faixa
    da altura dada, com friso escuro em cima e embaixo e sombra suave abaixo (uniforme na horizontal, então emenda)."""
    W, H = base.size
    im = base.convert("RGB")
    desl = ImageChops.offset(im, W // 2, 0)
    m = Image.new("L", (W, H))
    d = ImageDraw.Draw(m)
    for x in range(W):  # 255 nas bordas (usa a deslocada, cujas bordas casam), 0 no centro (a original)
        v = abs(x - W / 2) / (W / 2)
        d.line((x, 0, x, H), fill=int(255 * min(1, max(0, (v - .35) / .45))))
    im = Image.composite(desl, im, m)
    y0, y1 = int(H * (centro - altura / 2)), int(H * (centro + altura / 2))
    b = max(2, int(H * borda))
    d = ImageDraw.Draw(im)
    for k in range(b):  # friso: escurece mais perto da beira
        f = 1 - k / b
        for y in (y0 + k, y1 - 1 - k):
            linha = im.crop((0, y, W, y + 1))
            im.paste(ImageEnhance.Brightness(linha).enhance(1 - .55 * f), (0, y))
    for k in range(max(1, H // 150)):  # brilho suave no canto do tampo
        y = y0 + b + k
        im.paste(ImageEnhance.Brightness(im.crop((0, y, W, y + 1))).enhance(1.3), (0, y))
    out = Image.new("RGBA", (W, H))
    if sombra:
        s = Image.new("L", (W, H))
        ImageDraw.Draw(s).rectangle((-10, y0 + H // 40, W + 10, y1 + H // 25), fill=int(255 * sombra))
        s = s.filter(ImageFilter.GaussianBlur(H / 40))
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sh.putalpha(s)
        out.alpha_composite(sh)
    corpo = im.convert("RGBA")
    a = Image.new("L", (W, H))
    ImageDraw.Draw(a).rectangle((0, y0, W, y1 - 1), fill=255)
    corpo.putalpha(a)
    out.alpha_composite(corpo)
    return out


def derrame(base, R, cor=(14, 14, 32), x=.5, y=.5, tam=.22, gotas=14, forca=.95):
    """Líquido derramado sobre o objeto (tinta no tampo): mancha irregular com respingos e um brilho úmido.
    x, y, tam em frações da caixa do objeto."""
    X0, Y0, X1, Y1 = _caixa_obj(base)
    bw, bh = X1 - X0, Y1 - Y0
    cx, cy, r = X0 + x * bw, Y0 + y * bh, tam * min(bw, bh)
    c = Image.new("L", base.size)
    d = ImageDraw.Draw(c)
    for _ in range(3):  # corpo da poça: três escorridos em passeio aleatório, de bolhas que vão afinando
        ang = R.uniform(0, 2 * math.pi)
        px, py = cx, cy
        for k in range(12):
            t = k / 11
            ang += R.uniform(-.6, .6)
            px, py = px + math.cos(ang) * r * .14, py + math.sin(ang) * r * .14
            rr = r * (.45 - .33 * t) * R.uniform(.7, 1.2)
            d.ellipse((px - rr, py - rr, px + rr, py + rr), fill=255)
    d.ellipse((cx - r * .5, cy - r * .45, cx + r * .5, cy + r * .45), fill=255)
    c = c.filter(ImageFilter.GaussianBlur(r / 8)).point(lambda v: 255 if v > 110 else 0)
    d = ImageDraw.Draw(c)
    for _ in range(gotas):  # respingos
        a, dist = R.uniform(0, 2 * math.pi), r * R.uniform(.9, 1.7)
        px, py = cx + math.cos(a) * dist, cy + math.sin(a) * dist
        rr = r * R.uniform(.03, .08)
        d.ellipse((px - rr, py - rr, px + rr, py + rr), fill=255)
    c = c.filter(ImageFilter.GaussianBlur(1))
    tinta = Image.new("RGBA", base.size, tuple(cor) + (0,))
    tinta.putalpha(c.point(lambda v: int(v * forca)))
    brilho = Image.new("L", base.size)
    ImageDraw.Draw(brilho).ellipse((cx - r * .5, cy - r * .55, cx - r * .05, cy - r * .3), fill=110)
    brilho = ImageChops.multiply(brilho.filter(ImageFilter.GaussianBlur(r / 10)), c)
    luz = Image.new("RGBA", base.size, (170, 185, 255, 0))
    luz.putalpha(brilho)
    tinta.alpha_composite(luz)
    return so_no_objeto(base, tinta)


def rasgo(base, R, x=.5, y=.5, larg=.35, alto=.5, fios=26, cor_fio=(235, 228, 205)):
    """Tecido/fios cortados (tear): um talho escuro na trama e fios soltos pendurados. Frações da caixa do objeto."""
    X0, Y0, X1, Y1 = _caixa_obj(base)
    bw, bh = X1 - X0, Y1 - Y0
    cx, cy = X0 + x * bw, Y0 + y * bh
    lw, lh = larg * bw, alto * bh
    c = Image.new("RGBA", base.size)
    d = ImageDraw.Draw(c)
    pts = [(cx - lw / 2 + lw * k / 10, cy + R.uniform(-.12, .12) * lh) for k in range(11)]
    for k in range(10):  # o talho: buraco escuro irregular
        (ax, ay), (bx, by) = pts[k], pts[k + 1]
        g = lh * .18 * math.sin(math.pi * (k + .5) / 10) + 2
        d.polygon([(ax, ay - g), (bx, by - g), (bx, by + g), (ax, ay + g)], fill=(25, 18, 12, 235))
    lado = min(base.size)
    for _ in range(fios):  # fios soltos saindo das bordas do talho
        px, py = R.choice(pts)
        s = R.choice((-1, 1))
        L = R.uniform(.06, .2) * lh * 2
        a = math.pi / 2 * s + R.uniform(-.5, .5)
        meio = (px + math.cos(a) * L / 2 + R.uniform(-6, 6), py + math.sin(a) * L / 2)
        fim = (px + math.cos(a) * L + R.uniform(-10, 10), py + math.sin(a) * L)
        d.line([(px, py), meio, fim], fill=cor_fio + (240,), width=max(1, lado // 220), joint="curve")
    return so_no_objeto(base, c)


def recorta(base, tol=38, limite=215, come=9, margem=.05, sombra=True, tapa_buracos=True):
    """Tira o fundo claro que o sem_fundo deixou (quando o objeto encosta em 3 cantos e ele acha que é tudo objeto):
    flood fill a partir de cada ponto claro da beira do objeto; depois encaixa de novo no quadro, com sombra."""
    W, H = base.size
    rgb = Image.new("RGB", base.size, (255, 255, 255))
    rgb.paste(base.convert("RGB"), (0, 0), base.getchannel("A"))
    x0, y0, x1, y1 = _caixa_obj(base)
    marca = rgb.copy()
    borda = [(x, y) for x in range(x0, x1, 6) for y in (y0 + 1, y1 - 2)] + [(x, y) for y in range(y0, y1, 6) for x in (x0 + 1, x1 - 2)]
    for p in borda:
        c = marca.getpixel(p)
        if min(c) > limite and c != (255, 0, 255):
            ImageDraw.floodfill(marca, p, (255, 0, 255), thresh=tol)
    r, g, b = marca.split()
    fundo = ImageChops.multiply(ImageChops.multiply(r.point(lambda v: 255 if v == 255 else 0), b.point(lambda v: 255 if v == 255 else 0)),
                                g.point(lambda v: 255 if v == 0 else 0))
    a = ImageChops.subtract(mascara(base), fundo)
    if tapa_buracos:  # buracos internos (brilhos brancos que o sem_fundo tirou das páginas, do lençol) voltam a ser objeto
        fora = a.copy()
        ImageDraw.floodfill(fora, (0, 0), 128)
        a = ImageChops.lighter(a, fora.point(lambda v: 255 if v == 0 else 0))
    a = a.filter(ImageFilter.MinFilter(come)).filter(ImageFilter.GaussianBlur(1.5))
    obj = rgb.convert("RGBA")
    obj.putalpha(a)
    obj = obj.crop(a.point(lambda v: 255 if v > 30 else 0).getbbox())
    return encaixa(obj, W / S, H / S, margem, False, sombra)


def recorta_cor(base, sat=.2, valor=.5, come=7, margem=.05, sombra=True):
    """Recorte por cor: fica o que é saturado (palha, madeira, água) ou escuro; sai o papel/sombra pálida em volta.
    Buracos internos voltam; fica só o maior pedaço ligado ao centro. Depois encaixa de novo no quadro."""
    W, H = base.size
    rgb = Image.new("RGB", base.size, (255, 255, 255))
    rgb.paste(base.convert("RGB"), (0, 0), base.getchannel("A"))
    _, s, v = rgb.convert("HSV").split()
    m = ImageChops.lighter(s.point(lambda x: 255 if x > sat * 255 else 0), v.point(lambda x: 255 if x < valor * 255 else 0))
    m = ImageChops.multiply(m, mascara(base, 30))
    m = m.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))  # fecha frestinhas
    fora = m.copy()
    ImageDraw.floodfill(fora, (0, 0), 128)
    m = ImageChops.lighter(m, fora.point(lambda x: 255 if x == 0 else 0))
    m = m.filter(ImageFilter.MinFilter(come)).filter(ImageFilter.MaxFilter(max(1, come - 2)))  # tira fiapos soltos
    a = m.filter(ImageFilter.GaussianBlur(1.5))
    obj = rgb.convert("RGBA")
    obj.putalpha(a)
    obj = obj.crop(a.point(lambda x: 255 if x > 30 else 0).getbbox())
    return encaixa(obj, W / S, H / S, margem, False, sombra)


def esvazia(base, job, i, escuro=.5, sombra_int=.6):
    """Tira a água de dentro do objeto (cocho vazio): os pixels azuis viram tábuas de madeira escura (textura de outro
    job), com sombra interna nas bordas, para parecer o fundo vazio do mesmo cocho."""
    W, H = base.size
    r, g, b = base.convert("RGB").split()
    azul = ImageChops.subtract(b, r)  # água: bem mais azul que vermelha (a madeira é o contrário)
    m = ImageChops.multiply(azul.point(lambda v: 255 if v > 45 else 0), mascara(base))
    m = m.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
    fora = m.copy()
    caixa = m.getbbox()
    if not caixa:
        return base
    tex = Image.open(_job_png(job, i)).convert("RGB")
    cw, ch = caixa[2] - caixa[0], caixa[3] - caixa[1]
    k = max(cw / tex.width, ch / tex.height)
    tex = tex.resize((max(cw, int(tex.width * k)), max(ch, int(tex.height * k))), Image.LANCZOS).crop((0, 0, cw, ch))
    tex = ImageEnhance.Brightness(tex).enhance(escuro)
    fundo = Image.new("RGBA", base.size)
    fundo.paste(tex.convert("RGBA"), caixa[:2])
    # sombra interna: escurece perto da borda da água (a parede do cocho faz sombra no fundo)
    borda = ImageOps.invert(m).filter(ImageFilter.GaussianBlur(min(cw, ch) / 6))
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sh.putalpha(ImageChops.multiply(borda.point(lambda v: int(min(255, v * 2) * sombra_int)), m))
    fundo.alpha_composite(sh)
    fundo.putalpha(ImageChops.multiply(fundo.getchannel("A"), m.filter(ImageFilter.GaussianBlur(1))))
    out = base.copy()
    out.alpha_composite(fundo)
    return out


def desfia(base, R, n=14, fios=90, cor=None):
    """Monte solto e espalhado (feno, palha): contorno irregular de bolhas no lugar do quadrado, e fiapos soltos
    em volta com a cor média do objeto."""
    W, H = base.size
    X0, Y0, X1, Y1 = _caixa_obj(base)
    cx, cy, rx, ry = (X0 + X1) / 2, (Y0 + Y1) / 2, (X1 - X0) / 2, (Y1 - Y0) / 2
    m = Image.new("L", base.size)
    d = ImageDraw.Draw(m)
    d.ellipse((cx - rx * .75, cy - ry * .75, cx + rx * .75, cy + ry * .75), fill=255)
    for _ in range(n):
        a = R.uniform(0, 2 * math.pi)
        dist = R.uniform(.45, .75)
        px, py = cx + math.cos(a) * rx * dist, cy + math.sin(a) * ry * dist
        r = R.uniform(.2, .32) * min(rx, ry)
        d.ellipse((px - r, py - r * R.uniform(.6, 1), px + r, py + r), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(min(W, H) / 120))
    out = base.copy()
    out.putalpha(ImageChops.multiply(base.getchannel("A"), m))
    if cor is None:
        cor = base.convert("RGB").resize((1, 1), Image.BOX, box=(X0, Y0, X1, Y1)).getpixel((0, 0))
    c = Image.new("RGBA", base.size)
    dc = ImageDraw.Draw(c)
    lado = min(W, H)
    for _ in range(fios):
        a = R.uniform(0, 2 * math.pi)
        dist = R.uniform(.75, 1.1)
        px, py = cx + math.cos(a) * rx * dist, cy + math.sin(a) * ry * dist
        L, ang = R.uniform(.04, .12) * lado, R.uniform(0, math.pi)
        k = R.uniform(.75, 1.25)
        tom = tuple(max(0, min(255, int(v * k))) for v in cor[:3])
        dc.line((px - L / 2 * math.cos(ang), py - L / 2 * math.sin(ang), px + L / 2 * math.cos(ang), py + L / 2 * math.sin(ang)),
                fill=tom + (235,), width=max(1, lado // 200))
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sh.putalpha(c.getchannel("A").point(lambda v: int(v * .4)))
    fundo = Image.new("RGBA", base.size)
    fundo.alpha_composite(sh.filter(ImageFilter.GaussianBlur(2)), (2, 3))
    fundo.alpha_composite(c)
    fundo.alpha_composite(out)
    return fundo


def _peca(job, i, de, tol=38, limite=195):
    """Recorta uma peça de uma folha com vários objetos (de: frações x0,y0,x1,y1): tira o fundo pela borda e fica só
    com o pedaço ligado ao centro do recorte (sem as pontas dos vizinhos)."""
    im = Image.open(_job_png(job, i)).convert("RGB")
    w, h = im.size
    with tempfile.TemporaryDirectory() as tmp:
        src = pathlib.Path(tmp) / "peca.png"
        im.crop((int(de[0] * w), int(de[1] * h), int(de[2] * w), int(de[3] * h))).save(src)
        obj = _so_borda(src, tol, limite)
    m = obj.getchannel("A").point(lambda v: 255 if v > 128 else 0)
    ImageDraw.floodfill(m, (m.width // 2, m.height // 2), 128)
    m = m.point(lambda v: 255 if v == 128 else 0).filter(ImageFilter.GaussianBlur(1))
    obj.putalpha(ImageChops.multiply(obj.getchannel("A"), m))
    return obj.crop(m.point(lambda v: 255 if v > 30 else 0).getbbox())


def empilha(base, R, job, i, pecas, escala=.62, espalha=0.0, ang_extra=0):
    """Monta um objeto com peças de uma folha (pilha de livros: cada livro recortado e empilhado, girado).
    pecas: [[x0, y0, x1, y1, ângulo], ...] (frações da folha, a primeira fica embaixo).
    espalha > 0: as mesmas peças espalhadas em volta do centro (livros esparramados), com giro extra aleatório."""
    W, H = base.size
    lado = min(W, H)
    objs = [(_peca(job, i, p[:4]), p[4] if len(p) > 4 else 0) for p in pecas]
    maior = max(max(o.size) for o, _ in objs)
    k = escala * lado / maior
    out = Image.new("RGBA", base.size)
    for n, (o, ang) in enumerate(objs):
        o = o.resize((max(1, int(o.width * k)), max(1, int(o.height * k))), Image.LANCZOS)
        ang += R.uniform(-ang_extra, ang_extra)
        o = o.rotate(ang, expand=True, resample=Image.BICUBIC)
        if espalha:
            a = R.uniform(0, 2 * math.pi) if n else 0
            dist = (R.uniform(.4, 1) * espalha if n else 0)
            cx, cy = W / 2 + math.cos(a) * dist * W, H / 2 + math.sin(a) * dist * H
        else:
            cx, cy = W / 2 + R.gauss(0, .025) * W, H / 2 + R.gauss(0, .025) * H
        x, y = int(cx - o.width / 2), int(cy - o.height / 2)
        s = Image.new("RGBA", o.size, (0, 0, 0, 0))
        s.putalpha(o.getchannel("A").point(lambda v: int(v * .55)))
        out.alpha_composite(s.filter(ImageFilter.GaussianBlur(max(3, lado // 60))), (x + lado // 70, y + lado // 50))
        out.alpha_composite(o, (x, y))
    return out


def espelha(base, horizontal=True):
    return ImageOps.mirror(base) if horizontal else ImageOps.flip(base)


# ---------- pedra: paredes, portas, luzes ----------

def _textura(job, i, W, H, zoom=1.0, emenda=True):
    """Imagem inteira de um job (textura, sem recorte de fundo) no tamanho W x H, emendável com os vizinhos.
    zoom < 1 usa só o meio da imagem (blocos maiores)."""
    im = Image.open(_job_png(job, i)).convert("RGB")
    if zoom < 1:
        w, h = im.size
        cw, ch = int(w * zoom), int(h * zoom)
        im = im.crop(((w - cw) // 2, (h - ch) // 2, (w + cw) // 2, (h + ch) // 2))
    L = 2 * max(W, H)
    im = im.resize((L, L), Image.LANCZOS)
    if emenda:
        im = ladrilho(im)
    return im.resize((W, H), Image.LANCZOS).convert("RGBA")


def textura(base, job, i, zoom=1.0, emenda=True):
    """Troca a imagem por uma textura que cobre o quadro inteiro (parede, muralha): emenda em qualquer direção."""
    return _textura(job, i, base.width, base.height, zoom, emenda)


def _sombra_de(camada, dx, dy, raio, forca=.55):
    s = Image.new("RGBA", camada.size, (0, 0, 0, 0))
    s.putalpha(camada.getchannel("A").point(lambda v: int(v * forca)))
    s = s.filter(ImageFilter.GaussianBlur(raio))
    out = Image.new("RGBA", camada.size)
    out.paste(s, (int(dx), int(dy)))
    return out


def _friso(im, b, k=.5):
    """Escurece as beiradas de cima e de baixo de uma faixa (dá volume à folha da porta)."""
    W, H = im.size
    out = im.copy()
    for j in range(b):
        f = 1 - j / b
        for y in (j, H - 1 - j):
            linha = im.crop((0, y, W, y + 1))
            rgb = ImageEnhance.Brightness(linha.convert("RGB")).enhance(1 - k * f).convert("RGBA")
            rgb.putalpha(linha.getchannel("A"))
            out.paste(rgb, (0, y))
    return out


def porta(base, R, folha=None, aberta=False, piso=None, batente=None, zoom_batente=.6, ombro=.13, esp=.24,
          textura_folha=None, brasao=None, translucida=0.0, brilho=None, arrombada=0, efeitos_folha=()):
    """Token de porta 1x1 desenhado na horizontal (o mapa gira): piso no quadro todo, batentes de pedra nas laterais
    (se `batente`) e a folha cruzando o quadrado no meio. folha: [job, i] de uma folha recortada (porta de madeira);
    textura_folha: [job, i] de uma textura que vira a folha de lado a lado, emendável (portão 4x, porta esmeralda 3x).
    brasao: [job, i] colado no meio da folha. translucida: 0..1 deixa ver o piso. brilho: cor do brilho em volta da folha.
    aberta: a folha recolhida (madeira: duas metades abertas contra os batentes; sem batente: faixa fina na borda de cima).
    arrombada: graus que a folha gira, empurrada para dentro. efeitos_folha: efeitos aplicados só na folha."""
    W, H = base.size
    lado = min(W, H)
    out = _textura(*piso, W, H) if piso else base.copy()
    j = int(W * ombro) if batente else 0
    t = int(H * esp)
    y0 = (H - t) // 2
    # folha horizontal (largura do vão x espessura)
    if folha:
        f = sem_fundo(_job_png(*folha))
        if f.height > f.width:
            f = f.rotate(90, expand=True, resample=Image.BICUBIC)
        f = f.resize((W - 2 * j, t), Image.LANCZOS)
    else:
        f = _textura(*textura_folha, W, W)
        f = f.crop((0, (W - t) // 2, W, (W - t) // 2 + t))
    f = _friso(f, max(2, t // 9))
    if brasao and not aberta:
        b = sem_fundo(_job_png(*brasao))
        k = t * .92 / b.height
        b = b.resize((max(1, int(b.width * k)), max(1, int(b.height * k))), Image.LANCZOS)
        f.alpha_composite(b, ((f.width - b.width) // 2, (t - b.height) // 2))
    if translucida:
        f.putalpha(f.getchannel("A").point(lambda v: int(v * (1 - translucida))))
    camada = Image.new("RGBA", (W, H))
    if not aberta:
        camada.alpha_composite(f, (j, y0))
    elif batente:  # duas metades abertas a 90°, encostadas nos batentes
        meio = f.width // 2
        for k, (x0, x1) in enumerate(((0, meio), (meio, f.width))):
            p = f.crop((x0, 0, x1, t)).rotate(-90 if k == 0 else 90, expand=True, resample=Image.BICUBIC)
            camada.alpha_composite(p, (j if k == 0 else W - j - p.width, y0))
    else:  # recolhida para a borda de cima
        tt = max(6, int(H * .09))
        p = f.resize((W, tt), Image.LANCZOS)
        camada.alpha_composite(p, (0, 0))
    if arrombada:
        camada = camada.rotate(arrombada, resample=Image.BICUBIC, center=(W / 2, H / 2)).transform(
            (W, H), Image.AFFINE, (1, 0, 0, 0, 1, -int(H * .1)), resample=Image.BICUBIC)
    for ef in efeitos_folha:
        camada = aplica(camada, ef[0], R, ef[1] if len(ef) > 1 else {})
    if brilho:
        g = Image.new("RGBA", (W, H), tuple(brilho) + (0,))
        g.putalpha(camada.getchannel("A").filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(lado / 14)).point(lambda v: min(255, int(v * 1.3))))
        out.alpha_composite(g)
    out.alpha_composite(_sombra_de(camada, lado // 60, lado // 30, lado / 40, .6))
    out.alpha_composite(camada)
    if batente:  # batentes de pedra nas laterais, emendando com a parede vizinha
        pedra = _textura(*batente, W, H, zoom_batente)
        bt = Image.new("RGBA", (W, H))
        bt.paste(pedra.crop((0, 0, j, H)), (0, 0))
        bt.paste(pedra.crop((W - j, 0, W, H)), (W - j, 0))
        out.alpha_composite(_sombra_de(bt, 0, 0, lado / 30, .7))
        d = ImageDraw.Draw(bt)
        for x in (j - 1, W - j):
            d.line((x, 0, x, H), fill=(25, 22, 20, 255), width=2)
        out.alpha_composite(bt)
    return out


def olhos(base, pts, cor=(255, 90, 30), r=.025, halo=3.5):
    """Olhos acesos (gárgula desperta): pontos brilhantes com halo. pts em frações da caixa do objeto."""
    X0, Y0, X1, Y1 = _caixa_obj(base)
    lado = min(base.size)
    rr = r * lado
    halo_c = Image.new("RGBA", base.size, tuple(cor) + (0,))
    a = Image.new("L", base.size)
    nucleo = Image.new("RGBA", base.size)
    d, dn = ImageDraw.Draw(a), ImageDraw.Draw(nucleo)
    for px, py in pts:
        x, y = X0 + px * (X1 - X0), Y0 + py * (Y1 - Y0)
        d.ellipse((x - rr * halo, y - rr * halo, x + rr * halo, y + rr * halo), fill=200)
        dn.ellipse((x - rr, y - rr * .7, x + rr, y + rr * .7), fill=tuple(cor) + (255,))
        dn.ellipse((x - rr * .45, y - rr * .3, x + rr * .45, y + rr * .3), fill=(255, 240, 200, 255))
    halo_c.putalpha(a.filter(ImageFilter.GaussianBlur(rr * 1.6)))
    out = base.copy()
    out.alpha_composite(halo_c)
    out.alpha_composite(nucleo.filter(ImageFilter.GaussianBlur(max(1, rr / 5))))
    return out


def chamas_em(base, pts, tam=.14, brilho=(255, 170, 60)):
    """Chamas pequenas paradas em pontos (velas acesas). pts em frações da caixa do objeto."""
    X0, Y0, X1, Y1 = _caixa_obj(base)
    lado = min(base.size)
    out = base.copy()
    g = Image.new("L", base.size)
    dg = ImageDraw.Draw(g)
    for px, py in pts:
        x, y = X0 + px * (X1 - X0), Y0 + py * (Y1 - Y0)
        r = tam * lado * .9
        dg.ellipse((x - r * .7, y - r * .7, x + r * .7, y + r * .7), fill=110)
    luz = Image.new("RGBA", base.size, tuple(brilho) + (0,))
    luz.putalpha(ImageChops.multiply(g.filter(ImageFilter.GaussianBlur(tam * lado / 3)), mascara(base, 30).filter(ImageFilter.MaxFilter(9))))
    out.alpha_composite(luz)
    for px, py in pts:
        x, y = X0 + px * (X1 - X0), Y0 + py * (Y1 - Y0)
        for nome, cor, k in (("flame_02", (200, 60, 10), 1.15), ("flame_02", (255, 120, 25), 1.0), ("flame_02", (255, 190, 60), .7), ("flame_02", (255, 245, 190), .4)):
            s = sprite(nome, cor, tam * lado * k)
            for _ in range(2):  # sprite fraco: duas camadas para a chama aparecer sobre a vela clara
                out.alpha_composite(s, (int(x - s.width / 2), int(y - s.height * .6)))
    return out


def _zona(base, cx, cy, r):
    X0, Y0, X1, Y1 = _caixa_obj(base)
    return X0 + cx * (X1 - X0), Y0 + cy * (Y1 - Y0), r * min(X1 - X0, Y1 - Y0)


def brasas_em(base, R, cx=.5, cy=.5, r=.25, n=40, brilho=(255, 110, 20), forca=.75):
    """Brasas acesas e brilho laranja só numa zona (o leito da forja, o meio da fogueira). Frações da caixa do objeto."""
    x0, y0, rr = _zona(base, cx, cy, r)
    lado = min(base.size)
    g = Image.new("L", base.size)
    ImageDraw.Draw(g).ellipse((x0 - rr, y0 - rr, x0 + rr, y0 + rr), fill=int(255 * forca))
    luz = Image.new("RGBA", base.size, tuple(brilho) + (0,))
    luz.putalpha(g.filter(ImageFilter.GaussianBlur(rr / 2.5)))
    out = base.copy()
    out.alpha_composite(luz)
    c = Image.new("RGBA", base.size)
    d = ImageDraw.Draw(c)
    for _ in range(n):
        a, dist = R.uniform(0, 2 * math.pi), rr * math.sqrt(R.random())
        x, y = x0 + dist * math.cos(a), y0 + dist * math.sin(a)
        e = R.uniform(.004, .011) * lado
        d.ellipse((x - e, y - e, x + e, y + e), fill=(255, R.randint(110, 200), 40, 235))
    out.alpha_composite(c.filter(ImageFilter.GaussianBlur(.8)))
    return out


def balanca(base, ang=7, ondas=3, cor=(255, 225, 150)):
    """Sino tocando: o sino balança (cópias fantasmas giradas) e ondas de som em volta."""
    W, H = base.size
    lado = min(W, H)
    out = Image.new("RGBA", base.size)
    for a in (-ang, ang):
        g = base.rotate(a, resample=Image.BICUBIC, center=(W / 2, H * .2))
        out.alpha_composite(_apaga(g, .3))
    out.alpha_composite(base)
    c = Image.new("RGBA", base.size)
    d = ImageDraw.Draw(c)
    X0, Y0, X1, Y1 = _caixa_obj(base)
    cx, cy, r0 = (X0 + X1) / 2, (Y0 + Y1) / 2, max(X1 - X0, Y1 - Y0) / 2
    for k in range(ondas):
        r = r0 * (.75 + .12 * k)
        if r > lado / 2 - 3:
            r = lado / 2 - 3 - 4 * (ondas - k)
        for a0 in (200, 20, 110, 290):
            d.arc((cx - r, cy - r, cx + r, cy + r), a0 - 28, a0 + 28, fill=tuple(cor) + (int(230 - 50 * k),), width=max(2, lado // 70))
    out.alpha_composite(c.filter(ImageFilter.GaussianBlur(1)))
    return out


def entulho(base, R, n=40, resto=.85, escuro=.4, tam=(.04, .1), espalha=.2):
    """Pedra desmoronada: o resto escurecido onde estava e um monte de blocos angulosos com a textura da própria pedra,
    com aresta clara em cima e sombra embaixo (parede, muralha, pilar, altar destruídos)."""
    W, H = base.size
    lado = min(W, H)
    out = _apaga(escurece(base, escuro), resto) if resto else Image.new("RGBA", base.size)
    X0, Y0, X1, Y1 = _caixa_obj(base)
    cx, cy = (X0 + X1) / 2, (Y0 + Y1) / 2
    m = mascara(base)
    blocos = []
    for _ in range(n):
        r = R.uniform(*tam) * lado
        k = R.randint(5, 8)
        pts = [(r + r * R.uniform(.6, 1) * math.cos(i * 2 * math.pi / k + R.uniform(-.25, .25)),
                r + r * R.uniform(.6, 1) * math.sin(i * 2 * math.pi / k + R.uniform(-.25, .25))) for i in range(k)]
        mk = Image.new("L", (int(2 * r) + 1, int(2 * r) + 1))
        ImageDraw.Draw(mk).polygon(pts, fill=255)
        for _t in range(20):  # textura de um ponto que é objeto
            sx, sy = R.uniform(X0, max(X0 + 1, X1 - 2 * r)), R.uniform(Y0, max(Y0 + 1, Y1 - 2 * r))
            if m.getpixel((min(W - 1, int(sx + r)), min(H - 1, int(sy + r)))):
                break
        peca = base.crop((int(sx), int(sy), int(sx) + mk.width, int(sy) + mk.height)).convert("RGB").convert("RGBA")
        luz = Image.linear_gradient("L").rotate(45, expand=False).resize(mk.size)  # mais claro em cima à esquerda
        peca = Image.composite(ImageEnhance.Brightness(peca).enhance(1.25), ImageEnhance.Brightness(peca).enhance(.7), ImageOps.invert(luz))
        peca.putalpha(mk)
        d = ImageDraw.Draw(peca)
        d.line(pts + [pts[0]], fill=(30, 28, 26, 255), width=max(1, lado // 160))
        x = cx + R.gauss(0, espalha * (X1 - X0)) - r
        y = cy + R.gauss(0, espalha * (Y1 - Y0)) - r
        blocos.append((y, x, peca))
    for y, x, peca in sorted(blocos, key=lambda b: b[0]):
        s = Image.new("RGBA", peca.size, (0, 0, 0, 0))
        s.putalpha(peca.getchannel("A").point(lambda v: int(v * .6)))
        out.alpha_composite(s.filter(ImageFilter.GaussianBlur(3)), (int(x) + 3, int(y) + 5))
        out.alpha_composite(peca, (int(x), int(y)))
    return out


def remendo(base, job, i, de, para, suave=.25):
    """Cola um disco de outra imagem (de: cx, cy, r em frações da fonte) sobre um disco do objeto (para: cx, cy, r em
    frações da caixa do objeto), com borda esfumada. Ex.: carvão apagado por cima do fogo pintado na forja."""
    fonte = Image.open(_job_png(job, i)).convert("RGBA")
    fw, fh = fonte.size
    cx, cy, r = de[0] * fw, de[1] * fh, de[2] * min(fw, fh)
    pedaco = fonte.crop((int(cx - r), int(cy - r), int(cx + r), int(cy + r)))
    x0, y0, rr = _zona(base, *para)
    L = max(2, int(2 * rr))
    pedaco = pedaco.resize((L, L), Image.LANCZOS)
    m = Image.new("L", (L, L))
    ImageDraw.Draw(m).ellipse((L * suave / 2, L * suave / 2, L - L * suave / 2, L - L * suave / 2), fill=255)
    pedaco.putalpha(m.filter(ImageFilter.GaussianBlur(L * suave / 4)))
    out = base.copy()
    out.alpha_composite(pedaco, (int(x0 - L / 2), int(y0 - L / 2)))
    return out


def zona_fogo(base, cx=.5, cy=.5, r=.2):
    """Marca na imagem (base.info) o círculo onde o efeito "fogo" põe as chamas: a ponta da tocha, o leito da forja.
    Use logo antes de "fogo". Frações da caixa do objeto. Sem a marca, nada muda."""
    out = base.copy()
    out.info["zona_fogo"] = _zona(base, cx, cy, r)
    return out


_pontos_no_objeto_todo = pontos_no_objeto


def pontos_no_objeto(base, R, n, borda=.15):  # noqa: F811 — mesma função, só respeita a zona_fogo quando ela existe
    z = getattr(base, "info", {}).get("zona_fogo")
    if not z:
        return _pontos_no_objeto_todo(base, R, n, borda)
    x0, y0, rr = z
    pts = []
    for _ in range(n):
        a, d = R.uniform(0, 2 * math.pi), rr * math.sqrt(R.random())
        pts.append((x0 + d * math.cos(a), y0 + d * math.sin(a)))
    return pts


def tira_claro(base, lim=205, sat=45, margem=.05, sombra=True):
    """Tira o fundo claro e pouco saturado (papel, branco, cinza claro) em qualquer lugar do objeto, não só o ligado
    às bordas (vãos entre o sino e o aro), e encaixa de novo no quadro."""
    rgb = base.convert("RGB")
    r, g, b = rgb.split()
    mx, mn = ImageChops.lighter(ImageChops.lighter(r, g), b), ImageChops.darker(ImageChops.darker(r, g), b)
    claro = mn.point(lambda v: 255 if v > lim else 0)
    neutro = ImageChops.subtract(mx, mn).point(lambda v: 255 if v < sat else 0)
    fundo = ImageChops.multiply(claro, neutro).filter(ImageFilter.MaxFilter(5))
    a = ImageChops.subtract(base.getchannel("A"), fundo).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    obj = base.copy()
    obj.putalpha(a)
    obj = obj.crop(a.point(lambda v: 255 if v > 30 else 0).getbbox())
    return encaixa(obj, base.width / S, base.height / S, margem, False, sombra)


def sobrepoe(base, job, i, de=(0, 0, 1, 1), para=(.5, .5, .8), girar=0, lim=190, sat=45):
    """Põe por cima do objeto outro objeto recortado de outra imagem (híbrido: o tampo da bigorna sobre o toco).
    de: recorte x0,y0,x1,y1 da fonte (frações); o fundo claro dele sai como no tira_claro. para: cx, cy e largura em
    frações da caixa do objeto. girar: graus."""
    fonte = Image.open(_job_png(job, i)).convert("RGBA")
    fw, fh = fonte.size
    peca = fonte.crop((int(de[0] * fw), int(de[1] * fh), int(de[2] * fw), int(de[3] * fh)))
    rgb = peca.convert("RGB")
    r_, g_, b_ = rgb.split()
    mx, mn = ImageChops.lighter(ImageChops.lighter(r_, g_), b_), ImageChops.darker(ImageChops.darker(r_, g_), b_)
    fundo = ImageChops.multiply(mn.point(lambda v: 255 if v > lim else 0),
                                ImageChops.subtract(mx, mn).point(lambda v: 255 if v < sat else 0)).filter(ImageFilter.MaxFilter(5))
    a = ImageOps.invert(fundo).filter(ImageFilter.MinFilter(5)).filter(ImageFilter.GaussianBlur(1.5))
    peca.putalpha(a)
    peca = peca.crop(a.point(lambda v: 255 if v > 30 else 0).getbbox())
    X0, Y0, X1, Y1 = _caixa_obj(base)
    larg = para[2] * (X1 - X0)
    peca = peca.resize((max(1, int(larg)), max(1, int(larg * peca.height / peca.width))), Image.LANCZOS)
    if girar:
        peca = peca.rotate(girar, expand=True, resample=Image.BICUBIC)
    x, y = int(X0 + para[0] * (X1 - X0) - peca.width / 2), int(Y0 + para[1] * (Y1 - Y0) - peca.height / 2)
    out = base.copy()
    lado = min(base.size)
    s = Image.new("RGBA", peca.size, (0, 0, 0, 0))
    s.putalpha(peca.getchannel("A").point(lambda v: int(v * .6)))
    out.alpha_composite(s.filter(ImageFilter.GaussianBlur(lado / 60)), (x + lado // 50, y + lado // 35))
    out.alpha_composite(peca, (x, y))
    return out


def apara(base, l=0, t=0, r=0, b=0, margem=.05, sombra=True):
    """Corta frações das beiradas do objeto (moldura escura que o fundo não tirou) e encaixa de novo no quadro."""
    X0, Y0, X1, Y1 = _caixa_obj(base)
    w, h = X1 - X0, Y1 - Y0
    obj = base.crop((int(X0 + l * w), int(Y0 + t * h), int(X1 - r * w), int(Y1 - b * h)))
    return encaixa(obj, base.width / S, base.height / S, margem, False, sombra)


def oval(base, r=.97, margem=.05, sombra=True, job=None, i=0):
    """Recorta o objeto num círculo/elipse (para imagens redondas cujo fundo não é branco: topo de pilar, orbe).
    job, i: usa a imagem crua do job (quando o recorte de fundo come o brilho de um objeto claro, como o globo)."""
    obj = Image.open(_job_png(job, i)).convert("RGBA") if job else base.crop(_caixa_obj(base))
    w, h = obj.size
    m = Image.new("L", (w * 4, h * 4))
    ImageDraw.Draw(m).ellipse((w * 2 * (1 - r), h * 2 * (1 - r), w * 4 - w * 2 * (1 - r), h * 4 - h * 2 * (1 - r)), fill=255)
    m = m.resize((w, h), Image.LANCZOS)
    obj.putalpha(ImageChops.multiply(obj.getchannel("A"), m))
    obj = obj.crop(m.getbbox())
    return encaixa(obj, base.width / S, base.height / S, margem, False, sombra)


def tombado(base, ang=75, achata=.85, dx=0, dy=0):
    """Objeto caído de lado: girado, um pouco achatado e deslocado. dx, dy em frações do quadro."""
    W, H = base.size
    obj = base.crop(_caixa_obj(base))
    obj = obj.resize((obj.width, max(1, int(obj.height * achata))), Image.LANCZOS).rotate(ang, expand=True, resample=Image.BICUBIC)
    k = min(1, W * .95 / obj.width, H * .95 / obj.height)
    obj = obj.resize((max(1, int(obj.width * k)), max(1, int(obj.height * k))), Image.LANCZOS)
    out = Image.new("RGBA", base.size)
    x, y = int((W - obj.width) / 2 + dx * W), int((H - obj.height) / 2 + dy * H)
    s = Image.new("RGBA", obj.size, (0, 0, 0, 0))
    s.putalpha(obj.getchannel("A").point(lambda v: int(v * .5)))
    out.alpha_composite(s.filter(ImageFilter.GaussianBlur(4)), (x + W // 70, y + H // 50))
    out.alpha_composite(obj, (x, y))
    return out


# ---------- água, veículos e armadilhas (grupo "externos") ----------

def _ciclico(camada, raio):
    """Desfoque que dá a volta nas bordas (o que sai de um lado entra do outro): mantém o ladrilho emendável."""
    W, H = camada.size
    t = Image.new(camada.mode, (3 * W, 3 * H))
    for i in range(3):
        for j in range(3):
            t.paste(camada, (i * W, j * H))
    return t.filter(ImageFilter.GaussianBlur(raio)).crop((W, H, 2 * W, 2 * H))


def _elipse_ciclica(d, W, H, x, y, rx, ry, **kw):
    for dx in (-W, 0, W):
        for dy in (-H, 0, H):
            d.ellipse((x + dx - rx, y + dy - ry, x + dx + rx, y + dy + ry), **kw)


def vapor(base, R, n=16, forca=.8, cor=(232, 238, 242)):
    """Névoa branca densa sobre a água (emendável): véu geral e rolos de vapor mais grossos."""
    W, H = base.size
    m = Image.new("L", base.size, int(255 * .3))
    for _ in range(n):
        c = Image.new("L", base.size)
        x, y, r = R.uniform(0, W), R.uniform(0, H), R.uniform(.12, .32) * W
        _elipse_ciclica(ImageDraw.Draw(c), W, H, x, y, r, r * R.uniform(.5, .9), fill=R.randint(70, 150))
        m = ImageChops.add(m, c)
    m = _ciclico(m, W / 12).point(lambda v: int(min(255, v) * forca))
    nevoa = Image.new("RGBA", base.size, tuple(cor) + (0,))
    nevoa.putalpha(m)
    out = base.copy()
    out.alpha_composite(nevoa)
    return out


def bolhas(base, R, n=16, cor=(150, 200, 60), tam=(.015, .045)):
    """Bolhas com borda escura e brilho (água envenenada, pântano), emendáveis."""
    W, H = base.size
    c = Image.new("RGBA", base.size)
    d = ImageDraw.Draw(c)
    for _ in range(n):
        x, y, r = R.uniform(0, W), R.uniform(0, H), R.uniform(*tam) * W
        _elipse_ciclica(d, W, H, x, y, r, r, fill=tuple(cor) + (170,), outline=(30, 45, 10, 220), width=max(1, W // 160))
        _elipse_ciclica(d, W, H, x - r * .35, y - r * .35, r * .25, r * .25, fill=(240, 255, 210, 220))
    out = base.copy()
    out.alpha_composite(c)
    return out


def raios_quadro(base, R, n=2, brilho=.3, cor=(127, 212, 255)):
    """Um quadro da água eletrificada: tom azul, raios ramificados de borda a borda com brilho e faíscas."""
    W, H = base.size
    out = tinge(base, (60, 160, 235), brilho)
    halo = Image.new("L", base.size)
    nucleo = Image.new("L", base.size)
    dh, dn = ImageDraw.Draw(halo), ImageDraw.Draw(nucleo)

    def ponto(lado):
        t = R.uniform(.1, .9)
        return [(t * W, 0), (W, t * H), (t * W, H), (0, t * H)][lado]

    def risca(a, b, passos, desvio, larg):
        pts = [a]
        for k in range(1, passos):
            t = k / passos
            pts.append((a[0] + (b[0] - a[0]) * t + R.uniform(-desvio, desvio), a[1] + (b[1] - a[1]) * t + R.uniform(-desvio, desvio)))
        pts.append(b)
        dh.line(pts, fill=255, width=larg * 5, joint="curve")
        dn.line(pts, fill=255, width=larg, joint="curve")
        return pts

    for _ in range(n):
        lado = R.randint(0, 3)
        pts = risca(ponto(lado), ponto((lado + R.choice((1, 2, 3))) % 4), 9, W * .09, max(2, W // 80))
        for _ in range(R.randint(1, 3)):  # galhos
            a = R.choice(pts[1:-1])
            ang = R.uniform(0, 2 * math.pi)
            L = R.uniform(.12, .3) * W
            risca(a, (a[0] + L * math.cos(ang), a[1] + L * math.sin(ang)), 4, W * .04, max(1, W // 160))
    g = Image.new("RGBA", base.size, tuple(cor) + (0,))
    g.putalpha(halo.filter(ImageFilter.GaussianBlur(W / 30)).point(lambda v: int(v * .85)))
    out.alpha_composite(g)
    b = Image.new("RGBA", base.size, (245, 252, 255, 0))
    b.putalpha(nucleo.filter(ImageFilter.GaussianBlur(.6)))
    out.alpha_composite(b)
    f = Image.new("RGBA", base.size)
    df = ImageDraw.Draw(f)
    for _ in range(8):
        x, y, r = R.uniform(0, W), R.uniform(0, H), R.uniform(.006, .014) * W
        df.ellipse((x - r, y - r, x + r, y + r), fill=(230, 248, 255, 230))
    out.alpha_composite(f)
    return out


def webm_raios(base, destino, R, quadros=8):
    """Água eletrificada animada: raios que mudam e piscam a cada quadro → WebM VP9 (como o antigo agua_eletrificada.webm)."""
    seed = R.random()
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(quadros):
            Ri = random.Random(seed + i)
            if i % 4 == 3:  # quadro apagado: só o brilho, para piscar
                q = tinge(base, (60, 160, 235), .2)
            else:
                q = raios_quadro(base, Ri, Ri.randint(1, 2), Ri.uniform(.25, .4))
            q.save(f"{tmp}/f{i:02d}.png")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", "12", "-i", f"{tmp}/f%02d.png", "-c:v", "libvpx-vp9",
                        "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "0", "-crf", "32", str(destino)], check=True)
    raios_quadro(base, random.Random(seed), 2).save(destino.with_suffix(".png"))


def raios(base, R, webm=None):
    """Quadro parado dos raios; com webm (caminho em assets/, ex. "agua/agua_eletrificada.webm") grava também a animação."""
    if webm:
        webm_raios(base, ROOT / "assets" / webm, random.Random(R.random()))
    return raios_quadro(base, R)


def arranca(base, R, caixa, n=7, espalha=.6, resto=.0):
    """Arranca um pedaço do objeto (roda da carroça) e espalha os cacos dele ali perto.
    caixa: x0,y0,x1,y1 em frações da caixa do objeto; espalha: distância em tamanhos do pedaço."""
    X0, Y0, X1, Y1 = _caixa_obj(base)
    bw, bh = X1 - X0, Y1 - Y0
    r = (X0 + caixa[0] * bw, Y0 + caixa[1] * bh, X0 + caixa[2] * bw, Y0 + caixa[3] * bh)
    m = Image.new("L", base.size)
    ImageDraw.Draw(m).ellipse(r, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(2))
    a = base.getchannel("A")
    peca = base.copy()
    peca.putalpha(ImageChops.multiply(a, m))
    out = base.copy()
    out.putalpha(ImageChops.subtract(a, m.point(lambda v: int(v * (1 - resto)))))
    cx, cy, pw, ph = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, r[2] - r[0], r[3] - r[1]
    lado = min(pw, ph)
    for _ in range(n):
        rr = R.uniform(.18, .32) * lado
        px, py = R.uniform(r[0] + rr, r[2] - rr), R.uniform(r[1] + rr, r[3] - rr)
        k = R.randint(4, 6)
        a0 = R.uniform(0, math.pi)
        poli = [(rr + rr * R.uniform(.55, 1) * math.cos(a0 + j * 2 * math.pi / k), rr + rr * R.uniform(.55, 1) * math.sin(a0 + j * 2 * math.pi / k)) for j in range(k)]
        mk = Image.new("L", (int(2 * rr), int(2 * rr)))
        ImageDraw.Draw(mk).polygon(poli, fill=255)
        c = peca.crop((int(px - rr), int(py - rr), int(px - rr) + mk.width, int(py - rr) + mk.height))
        c.putalpha(ImageChops.multiply(c.getchannel("A"), mk))
        c = c.rotate(R.uniform(0, 360), expand=True, resample=Image.BICUBIC)
        x = int(cx + R.gauss(0, espalha * pw) - c.width / 2)
        y = int(cy + R.gauss(0, espalha * ph * .7) - c.height / 2)
        s = Image.new("RGBA", c.size, (0, 0, 0, 0))
        s.putalpha(c.getchannel("A").point(lambda v: int(v * .5)))
        out.alpha_composite(s.filter(ImageFilter.GaussianBlur(3)), (x + 3, y + 4))
        out.alpha_composite(c, (x, y))
    return out


def _sem_branco(src, limite=226):
    """Recorte simples por brancura (sem flood fill): para objetos finos que encostam na borda (corda)."""
    im = Image.open(src).convert("RGB")
    a = im.convert("L").point(lambda v: 0 if v > limite else 255).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1))
    out = im.convert("RGBA")
    out.putalpha(a)
    return out.crop(a.point(lambda v: 255 if v > 60 else 0).getbbox())


def fio(base, R, corda, estaca, arrebentado=False, grossura=.045, tam_estaca=.2, queda=22):
    """Fio de tropeço: uma corda esticada entre duas estacas (corda e estaca: [job, índice]).
    arrebentado: a corda partida ao meio, cada metade caída a partir da sua estaca, com a ponta desfiada."""
    W, H = base.size
    c = _sem_branco(_job_png(*corda))
    e = sem_fundo(_job_png(*estaca))
    te = int(W * tam_estaca)
    e = e.resize((te, int(te * e.height / e.width)), Image.LANCZOS)
    xa, xb, y = W * .13, W * .87, H * .5
    L = int(xb - xa)
    c = c.resize((L, max(3, int(H * grossura))), Image.LANCZOS)
    corpo = Image.new("RGBA", base.size)
    if not arrebentado:
        corpo.alpha_composite(c, (int(xa), int(y - c.height / 2)))
    else:
        meio = L // 2 - int(L * .04)
        cor = c.convert("RGB").resize((1, 1)).getpixel((0, 0))
        for lado in (0, 1):
            m = c.crop((0, 0, meio, c.height)) if lado == 0 else c.crop((L - meio, 0, L, c.height))
            p = Image.new("RGBA", base.size)
            x0 = int(xa) if lado == 0 else int(xb) - meio
            p.alpha_composite(m, (x0, int(y - c.height / 2)))
            d = ImageDraw.Draw(p)
            fim = x0 + meio if lado == 0 else x0
            for _ in range(7):  # ponta desfiada
                dx = R.uniform(.02, .06) * W * (1 if lado == 0 else -1)
                d.line((fim, y + R.uniform(-.4, .4) * c.height, fim + dx, y + R.uniform(-1.2, 1.2) * c.height), fill=tuple(cor) + (230,), width=max(1, W // 160))
            ang = (queda + R.uniform(-6, 6)) * (-1 if lado == 0 else 1)
            p = p.rotate(ang, resample=Image.BICUBIC, center=(xa if lado == 0 else xb, y))
            corpo.alpha_composite(p)
    for x in (xa, xb):
        corpo.alpha_composite(e.rotate(R.uniform(0, 360), resample=Image.BICUBIC), (int(x - e.width / 2), int(y - e.height / 2)))
    out = Image.new("RGBA", base.size)
    s = Image.new("RGBA", base.size, (0, 0, 0, 0))
    s.putalpha(corpo.getchannel("A").point(lambda v: int(v * .5)))
    out.alpha_composite(s.filter(ImageFilter.GaussianBlur(3)), (3, 5))
    out.alpha_composite(corpo)
    return out


def recorte(base, job, i, caixa=(0, 0, 1, 1), tol=38, margem=.05, sombra=True, tira_verde=False, girar=0, alarga=1.0, tapa=False):
    """Usa só um pedaço de outra imagem do ia-orc (caixa: frações x0,y0,x1,y1), quando ela veio com vários objetos
    (o barco de cima numa folha com dois). tira_verde: apaga o que for verde (grama que veio em volta da carroça).
    alarga: estica a altura do objeto (barco comprido demais para o quadro 4 x 2).
    tapa: fecha os buracos que o recorte abre nos brilhos brancos de dentro do objeto (pedra com reflexo)."""
    import io
    fonte = Image.open(_job_png(job, i)).convert("RGB")
    fw, fh = fonte.size
    buf = io.BytesIO()
    fonte.crop((int(caixa[0] * fw), int(caixa[1] * fh), int(caixa[2] * fw), int(caixa[3] * fh))).save(buf, "PNG")
    buf.seek(0)
    obj = sem_fundo(buf, tol)
    if tira_verde:
        r, g, b, a = obj.split()
        verde = ImageChops.multiply(ImageChops.subtract(g, r.point(lambda v: v * .97)).point(lambda v: 255 if v > 0 else 0),
                                    ImageChops.subtract(g, b.point(lambda v: v * 1.2)).point(lambda v: 255 if v > 0 else 0))
        a = ImageChops.subtract(a, verde)
        limpa = a.point(lambda v: 255 if v > 128 else 0).filter(ImageFilter.MinFilter(11)).filter(ImageFilter.MaxFilter(11))
        a = ImageChops.multiply(a, limpa).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))  # sem fiapos
        junto = a.point(lambda v: 255 if v > 30 else 0).filter(ImageFilter.MaxFilter(15)).convert("RGB")
        ImageDraw.floodfill(junto, (junto.width // 2, junto.height // 2), (255, 0, 0))  # só a peça do meio (e o que encosta nela)
        a = ImageChops.multiply(a, junto.getchannel("G").point(lambda v: 255 if v == 0 else 0))
        obj.putalpha(a)
        obj = obj.crop(a.point(lambda v: 255 if v > 30 else 0).getbbox())
    if tapa:
        a = obj.getchannel("A")
        fora = a.point(lambda v: 255 if v > 30 else 0).convert("RGB")
        ImageDraw.floodfill(fora, (0, 0), (255, 0, 0))
        for p in [(fora.width - 1, 0), (0, fora.height - 1), (fora.width - 1, fora.height - 1)]:
            if fora.getpixel(p) == (0, 0, 0):
                ImageDraw.floodfill(fora, p, (255, 0, 0))
        dentro = fora.getchannel("G").point(lambda v: 255 if v == 0 else 0).filter(ImageFilter.MaxFilter(3))
        obj.putalpha(ImageChops.lighter(ImageChops.multiply(dentro, ImageChops.invert(fora.getchannel("R").point(lambda v: 255 if v == 255 else 0))), a))
    if girar:
        obj = obj.rotate(girar, expand=True, resample=Image.BICUBIC)
    if alarga != 1:
        obj = obj.resize((obj.width, int(obj.height * alarga)), Image.LANCZOS)
    return encaixa(obj, base.width / S, base.height / S, margem, False, sombra)


def _metal(mascara_l, textura, escuro=.55):
    """Pinta uma forma (máscara L) com a textura de metal e dá volume: brilho em cima à esquerda, sombra embaixo
    à direita e contorno escuro."""
    W, H = mascara_l.size
    k = max(2, W // 160)
    alto = ImageChops.subtract(mascara_l, ImageChops.offset(mascara_l, k, k)).filter(ImageFilter.GaussianBlur(k))
    baixo = ImageChops.subtract(mascara_l, ImageChops.offset(mascara_l, -k, -k)).filter(ImageFilter.GaussianBlur(k))
    rgb = textura.convert("RGB")
    rgb = Image.composite(ImageEnhance.Brightness(rgb).enhance(1.7), rgb, alto)
    rgb = Image.composite(ImageEnhance.Brightness(rgb).enhance(escuro), rgb, baixo)
    borda = ImageChops.subtract(mascara_l, mascara_l.filter(ImageFilter.MinFilter(3)))
    rgb = Image.composite(Image.new("RGB", mascara_l.size, (22, 18, 16)), rgb, borda)
    out = rgb.convert("RGBA")
    out.putalpha(mascara_l)
    return out


def armadilha_urso(base, R, metal, fechada=False, dentes=9):
    """Armadilha de urso desenhada (o SDXL não acerta a vista de cima), pintada com a textura de metal enferrujado
    de uma imagem do ia-orc (metal: [job, índice], usa o miolo dela). Armada: as duas mandíbulas abertas formando um
    anel de dentes em volta do prato; fechada: as mandíbulas em pé, vistas de cima como uma faixa de dentes cruzados."""
    W, H = base.size
    Z = 4  # desenha grande e reduz (bordas lisas)
    L = W * Z
    cx = cy = L / 2
    fonte = Image.open(_job_png(*metal)).convert("RGB")
    fw, fh = fonte.size
    tex = fonte.crop((int(fw * .3), int(fh * .3), int(fw * .7), int(fh * .7))).resize((L, L), Image.LANCZOS)
    # só o detalhe (arranhões, ferrugem) sobre um ferro uniforme: tira as manchas grandes de luz e sombra da foto
    detalhe = ImageChops.subtract(tex, tex.filter(ImageFilter.GaussianBlur(L / 40)), 1, 128)
    tex = ImageChops.add(Image.new("RGB", (L, L), (92, 85, 80)), detalhe, 1, -128)
    tex = ImageEnhance.Contrast(tex).enhance(1.3)
    out = Image.new("RGBA", (L, L))

    def camada(desenho, esc=.55):
        m = Image.new("L", (L, L))
        desenho(ImageDraw.Draw(m))
        out.alpha_composite(_metal(m, tex, esc))

    ro, ri = L * .3, L * .245  # anel das mandíbulas (abertas)
    larg_mola = L * .035
    # molas (feixes em U) saindo das dobradiças para os lados
    def molas(d):
        for s in (-1, 1):
            x0, x1 = cx + s * ro * .92, cx + s * L * .47
            for yy in (cy - L * .045, cy + L * .045):
                d.line((x0, yy, x1 - s * L * .03, yy), fill=255, width=int(larg_mola * .6))
            d.ellipse((min(x1, x1 - s * L * .1), cy - L * .07, max(x1, x1 - s * L * .1), cy + L * .07), outline=255, width=int(larg_mola * .6))
    # corrente e argola de fixação
    def corrente(d):
        x, y = cx + L * .03, (cy + L * .1) if fechada else (cy + ro * .97)
        for i in range(3):
            a = .6 + .15 * i
            w, h = (L * .045, L * .028) if i % 2 == 0 else (L * .028, L * .045)
            d.ellipse((x - w, y - h, x + w, y + h), outline=255, width=int(L * .014))
            x, y = x + L * .045 * math.cos(a), y + L * .045 * math.sin(a)
        d.ellipse((x - L * .05, y - L * .05, x + L * .05, y + L * .05), outline=255, width=int(L * .016))
    camada(corrente, .5)
    camada(molas)
    if not fechada:
        def prato(d):
            d.ellipse((cx - L * .1, cy - L * .1, cx + L * .1, cy + L * .1), fill=255)
            d.line((cx - ro * .95, cy, cx - L * .09, cy), fill=255, width=int(L * .022))  # trava do prato
        camada(prato, .6)
        def mandibulas(d):
            d.ellipse((cx - ro, cy - ro, cx + ro, cy + ro), fill=255)
            d.ellipse((cx - ri, cy - ri, cx + ri, cy + ri), fill=0)
            for meia in (0, math.pi):  # dentes apontando para o centro, cada mandíbula com os seus
                for k in range(dentes):
                    a = meia + math.radians(14) + k * (math.pi - math.radians(28)) / (dentes - 1)
                    da = math.radians(7)
                    p1 = (cx + ri * 1.02 * math.cos(a - da), cy + ri * 1.02 * math.sin(a - da))
                    p2 = (cx + ri * 1.02 * math.cos(a + da), cy + ri * 1.02 * math.sin(a + da))
                    pt = (cx + (ri - L * .06) * math.cos(a), cy + (ri - L * .06) * math.sin(a))
                    d.polygon([p1, pt, p2], fill=255)
            for s in (-1, 1):  # vão das dobradiças
                d.rectangle((cx + s * ro - L * .02, cy - L * .012, cx + s * ro + L * .02, cy + L * .012), fill=0)
        camada(mandibulas)
        def dobradicas(d):
            for s in (-1, 1):
                d.ellipse((cx + s * ro - L * .035, cy - L * .035, cx + s * ro + L * .035, cy + L * .035), fill=255)
        camada(dobradicas, .45)
    else:
        def base_(d):  # a barra de baixo e o prato, quase escondidos sob as mandíbulas
            d.rectangle((cx - ro, cy - L * .025, cx + ro, cy + L * .025), fill=255)
            d.ellipse((cx - L * .08, cy - L * .02, cx + L * .08, cy + L * .12), fill=255)
        camada(base_, .45)
        esp = L * .045
        def aros(d):
            for s in (-1, 1):  # os dois aros, lado a lado
                d.rounded_rectangle((cx - ro, cy + s * esp - L * .024, cx + ro, cy + s * esp + L * .024), radius=L * .02, fill=255)
            for s in (-1, 1):
                d.ellipse((cx + s * ro - L * .04, cy - L * .045, cx + s * ro + L * .04, cy + L * .045), fill=255)
        camada(aros)
        ImageDraw.Draw(out).rectangle((cx - ro * .93, cy - esp + L * .02, cx + ro * .93, cy + esp - L * .02), fill=(20, 16, 14, 255))
        def fechadas(d):
            n = dentes + 3
            for k in range(n):  # dentes cruzados (zigue-zague) entre os aros
                x = cx - ro * .85 + k * (1.7 * ro) / (n - 1)
                s = 1 if k % 2 else -1
                d.polygon([(x - L * .024, cy + s * (esp - L * .02)), (x + L * .024, cy + s * (esp - L * .02)), (x, cy - s * (esp - L * .03))], fill=255)
        camada(fechadas, .4)
    out = out.resize((W, H), Image.LANCZOS)
    sombra = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sombra.putalpha(out.getchannel("A").point(lambda v: int(v * .55)).filter(ImageFilter.GaussianBlur(3)))
    final = Image.new("RGBA", base.size)
    final.alpha_composite(sombra, (3, 4))
    final.alpha_composite(out)
    return final


def _interior(base, encolhe=.12):
    """Máscara do objeto encolhida (o fundo do casco, dentro da borda)."""
    m = mascara(base)
    k = 4
    p = m.resize((max(1, m.width // k), max(1, m.height // k)))
    t = max(3, int(min(p.size) * encolhe) | 1)
    return p.filter(ImageFilter.MinFilter(t)).resize(m.size).filter(ImageFilter.GaussianBlur(2))


def alaga(base, R, cor=(45, 95, 125), forca=.6, n=7, encolhe=.14):
    """Água entrando no barco: poças azuladas no fundo do casco, com reflexos curtos."""
    W, H = base.size
    dentro = _interior(base, encolhe)
    c = Image.new("L", base.size)
    d = ImageDraw.Draw(c)
    for x, y in pontos_no_objeto(base, R, n, .2):
        rx, ry = R.uniform(.08, .16) * W, R.uniform(.15, .3) * H
        d.ellipse((x - rx, y - ry, x + rx, y + ry), fill=255)
    c = ImageChops.multiply(c.filter(ImageFilter.GaussianBlur(min(W, H) / 14)).point(lambda v: min(255, v * 2)), dentro)
    agua = Image.new("RGBA", base.size, tuple(cor) + (0,))
    agua.putalpha(c.point(lambda v: int(v * forca)))
    out = base.copy()
    out.alpha_composite(agua)
    luz = Image.new("RGBA", base.size)
    dl = ImageDraw.Draw(luz)
    for x, y in pontos_no_objeto(base, R, 2 * n, .2):
        if c.getpixel((int(x), int(y))) > 180:
            L = R.uniform(.008, .018) * W
            dl.arc((x - L, y - L / 3, x + L, y + L / 3), 200, 340, fill=(215, 238, 255, 150), width=max(1, H // 200))
    out.alpha_composite(luz.filter(ImageFilter.GaussianBlur(.7)))
    return out


def submerso(base, R, de=1, linha=.6, cor=(30, 70, 95), fundo=.38):
    """Afundado: só uma ponta fica fora d'água (de=1: a da direita; -1: a da esquerda), o resto some azulado
    sob a água, com uma franja de espuma em volta do casco perto da linha d'água."""
    W, H = base.size
    g = Image.new("L", base.size)
    dg = ImageDraw.Draw(g)
    for x in range(W):
        t = x / W if de > 0 else 1 - x / W
        dg.line((x, 0, x, H), fill=int(255 * min(1, max(0, (t - linha) / .1))))
    debaixo = tinge(escurece(dessatura(base, .4), .5), cor, .7)
    debaixo.putalpha(base.getchannel("A").point(lambda v: int(v * fundo)))
    fora = molhado(base, R)
    fora.putalpha(ImageChops.multiply(base.getchannel("A"), g))
    out = debaixo
    out.alpha_composite(fora)
    m = mascara(base, 120)
    k = max(3, (min(W, H) // 25) | 1)
    borda = ImageChops.subtract(m.filter(ImageFilter.MaxFilter(k)), m.filter(ImageFilter.MinFilter(3)))
    perto = Image.new("L", base.size)
    dp = ImageDraw.Draw(perto)
    xl = W * linha if de > 0 else W * (1 - linha)
    for x in range(W):
        dp.line((x, 0, x, H), fill=int(255 * max(0, 1 - abs(x - xl) / (W * .09))))
    linha_agua = Image.new("L", base.size)
    dw = ImageDraw.Draw(linha_agua)
    for y in range(0, H, 3):  # a superfície cortando o casco: faixa de espuma ondulada
        x = xl - de * W * .02 + W * .008 * math.sin(y / H * 18)
        dw.line((x - W * .006, y, x + W * .006, y + 3), fill=170)
    franja = ImageChops.lighter(ImageChops.multiply(borda, perto), ImageChops.multiply(linha_agua, m))
    espuma = Image.new("RGBA", base.size, (225, 240, 248, 0))
    espuma.putalpha(franja.filter(ImageFilter.GaussianBlur(2)).point(lambda v: int(v * .8)))
    out.alpha_composite(espuma)
    bol = Image.new("RGBA", base.size)
    d = ImageDraw.Draw(bol)
    for x, y in pontos_no_objeto(base, R, 10, .1):
        if (x < xl) == (de > 0):
            r = R.uniform(.002, .005) * W
            d.ellipse((x - r, y - r, x + r, y + r), outline=(215, 235, 250, 140), width=1)
    out.alpha_composite(bol)
    return out


# ---------- receitas ----------

def aplica(base, efeito, R, args):
    f = {
        "rachado": lambda: rachaduras(base, R, **args),
        "quebrado": lambda: quebrado(base, R, **args),
        "lascas": lambda: quebrado(base, R, alongado=2.6, **args),
        "chamuscado": lambda: fuligem(base, R, **{"n": 6, "forca": .95, **args}),
        "queimado": lambda: brasas(fuligem(escurece(dessatura(base, .25), .45), R, 8, 1.0), R),
        "cinzas": lambda: brasas(quebrado(fuligem(escurece(dessatura(base, .2), .4), R, 6, 1.0), R, 18, resto=.6), R, 30),
        "gelo": lambda: gelo(base, R),
        "molhado": lambda: molhado(base, R),
        "acido": lambda: manchas(base, R, (140, 190, 40), 9, forca=.55),
        "podre": lambda: manchas(dessatura(base, .4), R, (50, 60, 30), 12, forca=.6),
        "radiante": lambda: aura(base, (255, 230, 140), .07, .9),
        "flechas": lambda: flechas(base, R, **args),
        "escurece": lambda: escurece(base, args.get("k", .6)),
        "tinge": lambda: tinge(base, args["cor"], args.get("forca", .4)),
        "aura": lambda: aura(base, args["cor"], args.get("raio", .06), args.get("forca", .8)),
        "manchas": lambda: manchas(base, R, args["cor"], args.get("n", 10), forca=args.get("forca", .7)),
        "brasas": lambda: brasas(base, R, args.get("n", 24)),
        "cortado": lambda: cortado(base, R),
        "poca": lambda: poca(base, R, **args),
        "outra": lambda: outra(base, **args),
        "cola": lambda: cola(base, **args),
        "faixa_h": lambda: faixa_h(base, **args),
        "derrame": lambda: derrame(base, R, **args),
        "rasgo": lambda: rasgo(base, R, **args),
        "espelha": lambda: espelha(base, **args),
        "recorta": lambda: recorta(base, **args),
        "recorta_cor": lambda: recorta_cor(base, **args),
        "esvazia": lambda: esvazia(base, **args),
        "desfia": lambda: desfia(base, R, **args),
        "empilha": lambda: empilha(base, R, **args),
        "vapor": lambda: vapor(base, R, **args),
        "bolhas": lambda: bolhas(base, R, **args),
        "raios": lambda: raios(base, R, **args),
        "arranca": lambda: arranca(base, R, **args),
        "alaga": lambda: alaga(base, R, **args),
        "submerso": lambda: submerso(base, R, **args),
        "fio": lambda: fio(base, R, **args),
        "recorte": lambda: recorte(base, **args),
        "armadilha_urso": lambda: armadilha_urso(base, R, **args),
        "dessatura": lambda: dessatura(base, args.get("k", .5)),
        "brilho": lambda: escurece(base, args.get("k", 1.1)),
        "textura": lambda: textura(base, **args),
        "porta": lambda: porta(base, R, **args),
        "olhos": lambda: olhos(base, **args),
        "chamas_em": lambda: chamas_em(base, **args),
        "brasas_em": lambda: brasas_em(base, R, **args),
        "balanca": lambda: balanca(base, **args),
        "tombado": lambda: tombado(base, **args),
        "oval": lambda: oval(base, **args),
        "entulho": lambda: entulho(base, R, **args),
        "apara": lambda: apara(base, **args),
        "tira_claro": lambda: tira_claro(base, **args),
        "zona_fogo": lambda: zona_fogo(base, **args),
        "remendo": lambda: remendo(base, **args),
        "sobrepoe": lambda: sobrepoe(base, **args),
    }
    return f[efeito]()


def webm_fogo(base, destino, R, quadros=12, escala=1.0):
    """Fogo animado: quadros PNG com as chamas tremendo → WebM VP9 com transparência (como mesa_queimando.webm)."""
    seed = R.random()
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(quadros):
            chamas(base, random.Random(seed), i / quadros, escala=escala).save(f"{tmp}/f{i:02d}.png")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", "12", "-i", f"{tmp}/f%02d.png", "-c:v", "libvpx-vp9",
                        "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "0", "-crf", "34", str(destino)], check=True)
        chamas(base, random.Random(seed), 0, escala=escala).save(destino.with_suffix(".png"))  # miniatura do ator


def ladrilho(im, tam=None):
    """Torna a imagem emendável (as bordas casam com o lado oposto): mistura com a cópia deslocada pela metade,
    usando uma máscara que esconde a costura do centro. Para paredes, muralha, água e pisos."""
    im = im.convert("RGB")
    if tam:
        im = im.resize((tam, tam), Image.LANCZOS)
    W, H = im.size
    desl = ImageChops.offset(im, W // 2, H // 2)
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    for i in range(W // 2):  # 0 nas bordas (usa a original), 255 no centro (usa a deslocada, que não tem costura ali)
        v = int(255 * (1 - i / (W / 2)))
        d.rectangle((i, i, W - 1 - i, H - 1 - i), outline=255 - v)
    m = m.filter(ImageFilter.GaussianBlur(W / 16))
    return Image.composite(desl, im, ImageOps.invert(m))


def imagem_do_job(jobs, nome):
    job, i = jobs[nome]
    fs = sorted((DOWN / job).glob("*.png"))
    return fs[i]


def gera(asset, rec, defs):
    d = defs[asset]
    w, h = d["size"]["w"], d["size"]["h"]
    R = random.Random(zlib.crc32(asset.encode()))  # determinístico entre execuções
    imgs = {k: encaixa(sem_fundo(imagem_do_job(rec["jobs"], k), rec.get("tol", 38)), w, h, rec.get("margem", .05),
                       rec.get("esticar", False), rec.get("sombra", True)) for k in rec["jobs"]}
    pasta = ROOT / "assets" / asset
    pasta.mkdir(exist_ok=True)
    srcs = {}
    for st in d["states"]:
        r = rec["estados"].get(st["id"], [])
        if isinstance(r, list):
            r = {"efeitos": [r] if r and isinstance(r[0], str) else r}
        im = imgs[r.get("img", "base")]
        fogo = False
        for ef in r.get("efeitos", []):
            nome, args = (ef[0], ef[1] if len(ef) > 1 else {})
            if nome == "fogo":
                fogo = args or True
                continue
            im = aplica(im, nome, R, args)
        if fogo:
            destino = pasta / f"{asset}_{st['id']}.webm"
            webm_fogo(im, destino, R, escala=(fogo.get("escala", 1.0) if isinstance(fogo, dict) else 1.0))
        else:
            destino = pasta / f"{asset}_{st['id']}.webp"
            im.save(destino, quality=88, method=6)
        # efeitos que gravam a própria animação (os raios da água): o estado aponta para o WebM
        anim = next((ef[1]["webm"] for ef in r.get("efeitos", []) if len(ef) > 1 and isinstance(ef[1], dict) and ef[1].get("webm")), None)
        srcs[st["id"]] = anim or f"{asset}/{destino.name}"
    return srcs


def receitas():
    rec = json.loads((ROOT / "tools" / "ia_assets.json").read_text())
    for f in sorted((ROOT / "tools" / "ia_receitas").glob("*.json")):
        rec.update(json.loads(f.read_text()))
    return rec


def main(nomes, aplicar=True):
    rec = receitas()
    pa = ROOT / "assets" / "assets.json"
    defs = json.loads(pa.read_text())
    frags = {f: json.loads(f.read_text()) for f in (ROOT / "tools" / "fragmentos").glob("*.json")}
    for asset in nomes or [k for k in rec if not k.startswith("_")]:
        srcs = gera(asset, rec[asset], defs)
        print(asset, len(srcs), "estados")
        if not aplicar:
            continue
        for alvo in [defs] + [fr for fr in frags.values() if asset in fr]:
            for st in alvo[asset]["states"]:
                st["src"] = srcs[st["id"]]
    if aplicar:
        pa.write_text(json.dumps(defs, indent=2, ensure_ascii=False) + "\n")
        for f, fr in frags.items():
            f.write_text(json.dumps(fr, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    # --so-imagens: gera as imagens sem mexer no assets.json (para vários agentes ao mesmo tempo)
    args = sys.argv[1:]
    main([a for a in args if not a.startswith("--")], aplicar="--so-imagens" not in args)
