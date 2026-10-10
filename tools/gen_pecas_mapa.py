"""Peças de mapa (1 quadrado = 200 px).

Pisos, grama, terra e parede são *materiais*: o montador (tools/gen_mapa.py) desenha cada
material no tamanho do mapa inteiro e recorta pelos quadrados do layout, assim as tábuas e
os blocos continuam de um quadrado para o outro sem emenda. Aqui também sai uma amostra
de 1 quadrado de cada material em mapas/pecas/ para ver como fica.
Pilar, porta e lareira são peças de 1 quadrado com fundo transparente.

Uso: python3 tools/gen_pecas_mapa.py && NODE_PATH=$(npm root -g) node tools/render.js mapas/pecas/*.svg"""
import random, pathlib
D = pathlib.Path(__file__).resolve().parent.parent / "mapas" / "pecas"
S = 200


def wrap(w, h, body, defs=""):
    # width/height = metade: o render.js usa escala 2, então o PNG sai em tamanho real
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w//2}" height="{h//2}" viewBox="0 0 {w} {h}">'
            f'<defs>{defs}</defs>{body}</svg>')


def svg(name, body, defs=""):
    (D / f"{name}.svg").write_text(wrap(S, S, body, defs))


def noise(fid, freq, seed, rgb, alpha=1.4, off=-0.45, octaves=3):
    r, g, b = rgb
    return (f'<filter id="{fid}" x="0" y="0" width="100%" height="100%" filterUnits="userSpaceOnUse">'
            f'<feTurbulence type="fractalNoise" baseFrequency="{freq}" numOctaves="{octaves}" seed="{seed}" result="n"/>'
            f'<feColorMatrix type="matrix" values="0 0 0 0 {r}  0 0 0 0 {g}  0 0 0 0 {b}  0 0 0 {alpha} {off}" in="n" result="g"/>'
            f'<feComposite in="g" in2="SourceGraphic" operator="in" result="gc"/>'
            f'<feMerge><feMergeNode in="SourceGraphic"/><feMergeNode in="gc"/></feMerge></filter>')


def shade(hexc, k):
    c = [int(hexc[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{max(0, min(255, int(v * k))):02x}" for v in c)


# ---------- materiais: cada função devolve um SVG de w x h pixels ----------

def piso_madeira(w, h, seed=1):
    """Tábuas horizontais (5 por quadrado), comprimentos variados, pregos nas pontas."""
    R = random.Random(seed)
    ph = S / 5
    boards, seams, knots = "", "", ""
    for r in range(int(h // ph) + 1):
        y = r * ph
        x = -R.randint(0, 250)
        while x < w:
            L = R.randint(140, 320)
            boards += f'<rect x="{x}" y="{y}" width="{L}" height="{ph}" fill="{shade("#7a5534", R.uniform(.8, 1.12))}"/>'
            e = x + L
            seams += f'<line x1="{e}" y1="{y}" x2="{e}" y2="{y+ph}"/><circle cx="{e-7}" cy="{y+8}" r="1.6"/><circle cx="{e-7}" cy="{y+ph-8}" r="1.6"/><circle cx="{e+7}" cy="{y+8}" r="1.6"/><circle cx="{e+7}" cy="{y+ph-8}" r="1.6"/>'
            if R.random() < .25:
                knots += f'<ellipse cx="{x+R.randint(20,L-20)}" cy="{y+ph/2}" rx="{R.randint(4,8)}" ry="2.5" fill="#3b2412" opacity=".55"/>'
            x = e
    lines = "".join(f'<line x1="0" y1="{r*ph}" x2="{w}" y2="{r*ph}"/>' for r in range(int(h // ph) + 2))
    body = (f'<g filter="url(#grain)">{boards}</g>'
            f'<g stroke="#2a180a" stroke-width="2.5" fill="#2a180a" opacity=".85">{lines}{seams}</g>{knots}')
    return wrap(w, h, body, noise("grain", "0.006 0.2", seed, (.22, .12, .05)))


def piso_pedra(w, h, seed=1):
    """Lajotas de pedra (2 x 2 por quadrado), levemente tortas, com rachaduras."""
    R = random.Random(seed)
    body, cracks = "", ""
    j = lambda: R.uniform(-2, 2)
    for i in range(int(w // 100) + 1):
        for k in range(int(h // 100) + 1):
            x0, y0 = i * 100, k * 100
            p = f"{x0+4+j():.1f},{y0+4+j():.1f} {x0+96+j():.1f},{y0+4+j():.1f} {x0+96+j():.1f},{y0+96+j():.1f} {x0+4+j():.1f},{y0+96+j():.1f}"
            body += f'<polygon points="{p}" fill="{shade("#77736b", R.uniform(.85, 1.12))}"/>'
            if R.random() < .15:
                cx, cy = x0 + R.randint(20, 80), y0 + R.randint(20, 80)
                cracks += f'<path d="M{cx},{cy} l{R.randint(-18,18)},{R.randint(6,16)} l{R.randint(-12,12)},{R.randint(6,14)}" stroke="#2c2a26" stroke-width="1.2" fill="none" opacity=".6"/>'
    return wrap(w, h, f'<rect width="{w}" height="{h}" fill="#2f2c28"/><g filter="url(#st)">{body}</g>{cracks}',
                noise("st", "0.05", seed, (.18, .17, .15), 1.2, -.35))


def grama(w, h, seed=1):
    R = random.Random(seed)
    tufts = "".join(
        f'<path d="M{(x:=R.randint(0,w))},{(y:=R.randint(0,h))} l-3,-8 M{x},{y} l1,-10 M{x},{y} l4,-7" stroke="{R.choice(["#5d7c35","#4c6a2b","#6f8d3e"])}" stroke-width="1.6" fill="none"/>'
        for _ in range(w * h // 1500))
    return wrap(w, h, f'<rect width="{w}" height="{h}" fill="#3f5a28" filter="url(#gr)"/>{tufts}',
                noise("gr", "0.02", seed, (.16, .26, .1), 1.6, -.5, 4))


def terra(w, h, seed=1):
    R = random.Random(seed)
    pebbles = "".join(f'<ellipse cx="{R.randint(0,w)}" cy="{R.randint(0,h)}" rx="{R.randint(3,6)}" ry="{R.randint(2,4)}" fill="{R.choice(["#7c6d58","#6a5c49","#8a7c66"])}"/>' for _ in range(w * h // 4000))
    return wrap(w, h, f'<rect width="{w}" height="{h}" fill="#6b5338" filter="url(#te)"/>{pebbles}',
                noise("te", "0.02", seed, (.3, .22, .14), 1.5, -.5, 4))


def parede(w, h, seed=1):
    """Blocos de pedra vistos de cima, em fiadas desencontradas."""
    R = random.Random(seed)
    bh = S / 4
    body = ""
    for r in range(int(h // bh) + 1):
        x = -(r % 2) * 50 - R.randint(0, 20)
        while x < w:
            L = R.randint(70, 110)
            body += f'<rect x="{x+2}" y="{r*bh+2}" width="{L-4}" height="{bh-4}" rx="4" fill="{shade("#5c5852", R.uniform(.82, 1.15))}"/>'
            x += L
    return wrap(w, h, f'<rect width="{w}" height="{h}" fill="#24221f"/><g filter="url(#wl)">{body}</g>',
                noise("wl", "0.06", seed, (.14, .13, .12), 1.3, -.4))


MATERIAIS = {"piso_madeira": piso_madeira, "piso_pedra": piso_pedra, "grama": grama, "terra": terra, "parede": parede}


def pecas():
    D.mkdir(parents=True, exist_ok=True)
    for old in D.glob("*_[0-9].*"):
        old.unlink()  # amostras antigas com variações numeradas
    for name, fn in MATERIAIS.items():
        (D / f"{name}.svg").write_text(fn(S, S, 7))

    # ---------- pilar (transparente, por cima do piso) ----------
    svg("pilar", '''
    <circle cx="104" cy="108" r="76" fill="#000" opacity=".45" filter="url(#bl)"/>
    <circle cx="100" cy="100" r="74" fill="#4a4741"/>
    <circle cx="100" cy="100" r="66" fill="url(#pg)" filter="url(#pn)"/>
    <circle cx="100" cy="100" r="66" fill="none" stroke="#2a2825" stroke-width="3"/>
    <circle cx="100" cy="100" r="46" fill="none" stroke="#2a2825" stroke-width="2" opacity=".6"/>
    <circle cx="100" cy="100" r="24" fill="none" stroke="#2a2825" stroke-width="1.5" opacity=".5"/>
    <circle cx="100" cy="100" r="74" fill="none" stroke="#1c1b19" stroke-width="3"/>''',
        '<radialGradient id="pg" cx=".4" cy=".38"><stop offset="0" stop-color="#9a958b"/><stop offset="1" stop-color="#5a564f"/></radialGradient>'
        '<filter id="bl" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="6"/></filter>'
        + noise("pn", "0.07", 7, (.2, .19, .17), 1.2, -.4))

    # ---------- porta (horizontal; o montador gira para paredes verticais) ----------
    planks = "".join(f'<rect x="{30+i*28}" y="74" width="28" height="52" fill="{c}"/>'
                     for i, c in enumerate(["#6e4523", "#7a4d28", "#68411f", "#77492a", "#6c4422"]))
    svg("porta", f'''
    <rect x="0" y="0" width="30" height="200" fill="#5c5852" stroke="#24221f" stroke-width="4"/><rect x="170" y="0" width="30" height="200" fill="#5c5852" stroke="#24221f" stroke-width="4"/>
    <rect x="30" y="0" width="140" height="200" fill="#6b675f"/>
    <g stroke="#3d3a35" stroke-width="2"><line x1="30" y1="45" x2="170" y2="45"/><line x1="30" y1="155" x2="170" y2="155"/><line x1="100" y1="0" x2="100" y2="45"/><line x1="100" y1="155" x2="100" y2="200"/></g>
    <g filter="url(#dg)">{planks}</g>
    <g stroke="#2a180a" stroke-width="2"><line x1="58" y1="74" x2="58" y2="126"/><line x1="86" y1="74" x2="86" y2="126"/><line x1="114" y1="74" x2="114" y2="126"/><line x1="142" y1="74" x2="142" y2="126"/></g>
    <rect x="30" y="74" width="140" height="52" fill="none" stroke="#2a180a" stroke-width="4"/>
    <g fill="#2e2e30"><rect x="34" y="82" width="132" height="6"/><rect x="34" y="112" width="132" height="6"/></g>
    <circle cx="150" cy="100" r="5" fill="#b08a3c" stroke="#3a2c10" stroke-width="1.5"/>''',
        noise("dg", "0.006 0.2", 5, (.22, .12, .05)))

    # ---------- lareira (dentro da parede, abre para baixo) ----------
    svg("lareira", '''
    <rect x="10" y="20" width="180" height="180" rx="6" fill="#4d4943" stroke="#1c1b19" stroke-width="4"/>
    <path d="M40,200 L40,70 Q100,30 160,70 L160,200 Z" fill="#141210"/>
    <ellipse cx="100" cy="160" rx="62" ry="40" fill="url(#fg)"/>
    <g stroke="#3a2210" stroke-width="12" stroke-linecap="round"><line x1="62" y1="168" x2="132" y2="146"/><line x1="70" y1="146" x2="140" y2="170"/></g>
    <path d="M78,160 Q84,120 98,104 Q96,130 110,120 Q118,140 124,160 Z" fill="#ff9b3d"/>
    <path d="M90,160 Q96,134 102,124 Q106,142 112,160 Z" fill="#ffe27a"/>''',
        '<radialGradient id="fg"><stop offset="0" stop-color="#ff7b2e" stop-opacity=".9"/><stop offset=".6" stop-color="#b8361a" stop-opacity=".5"/><stop offset="1" stop-color="#b8361a" stop-opacity="0"/></radialGradient>')

    print("peças em", D)


if __name__ == "__main__":
    pecas()
