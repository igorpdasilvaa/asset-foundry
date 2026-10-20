"""Peças de mapa (1 quadrado = 200 px).

Pisos, grama, terra e parede são *materiais*: o montador (tools/gen_mapa.py) desenha cada
material no tamanho do mapa inteiro e recorta pelos quadrados do layout, assim as tábuas e
os blocos continuam de um quadrado para o outro sem emenda. Aqui também sai uma amostra
de 1 quadrado de cada material em mapas/pecas/ para ver como fica.
Pilar, porta e lareira são peças de 1 quadrado com fundo transparente; a escada cobre o quadrado.

Uso: python3 tools/gen_pecas_mapa.py && NODE_PATH=$(npm root -g) node tools/render.js mapas/pecas/*.svg"""
import math, random, pathlib
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
    return _tabuas(w, h, seed, "#7a5534", "#2a180a", "#3b2412", (.22, .12, .05))


def madeira_escura(w, h, seed=1):
    """Como piso_madeira, mas de madeira escura e nobre (biblioteca)."""
    return _tabuas(w, h, seed, "#4a2e1c", "#140a05", "#1e100a", (.12, .06, .03))


def _tabuas(w, h, seed, cor, junta, no, grao):
    R = random.Random(seed)
    ph = S / 5
    boards, seams, knots = "", "", ""
    for r in range(int(h // ph) + 1):
        y = r * ph
        x = -R.randint(0, 250)
        while x < w:
            L = R.randint(140, 320)
            boards += f'<rect x="{x}" y="{y}" width="{L}" height="{ph}" fill="{shade(cor, R.uniform(.8, 1.12))}"/>'
            e = x + L
            seams += f'<line x1="{e}" y1="{y}" x2="{e}" y2="{y+ph}"/><circle cx="{e-7}" cy="{y+8}" r="1.6"/><circle cx="{e-7}" cy="{y+ph-8}" r="1.6"/><circle cx="{e+7}" cy="{y+8}" r="1.6"/><circle cx="{e+7}" cy="{y+ph-8}" r="1.6"/>'
            if R.random() < .25:
                knots += f'<ellipse cx="{x+R.randint(20,L-20)}" cy="{y+ph/2}" rx="{R.randint(4,8)}" ry="2.5" fill="{no}" opacity=".55"/>'
            x = e
    lines = "".join(f'<line x1="0" y1="{r*ph}" x2="{w}" y2="{r*ph}"/>' for r in range(int(h // ph) + 2))
    body = (f'<g filter="url(#grain)">{boards}</g>'
            f'<g stroke="{junta}" stroke-width="2.5" fill="{junta}" opacity=".85">{lines}{seams}</g>{knots}')
    return wrap(w, h, body, noise("grain", "0.006 0.2", seed, grao))


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


def agua(w, h, seed=1):
    """Água funda: azul-esverdeado com manchas e reflexos de luz (caustics)."""
    R = random.Random(seed)
    glints = "".join(
        f'<path d="M{(x:=R.randint(0,w))},{(y:=R.randint(0,h))} q{(r:=R.randint(8,22))},-{r//3} {2*r},0" stroke="#bfe6f2" stroke-width="2" fill="none" opacity="{R.uniform(.12,.3):.2f}"/>'
        for _ in range(w * h // 2500))
    return wrap(w, h, f'<rect width="{w}" height="{h}" fill="#173f52" filter="url(#ag)"/>'
                f'<rect width="{w}" height="{h}" filter="url(#cau)" opacity=".16"/>{glints}',
                noise("ag", "0.008", seed, (.05, .2, .25), 1.3, -.4, 4)
                + f'<filter id="cau" x="0" y="0" width="100%" height="100%" filterUnits="userSpaceOnUse">'
                  f'<feTurbulence type="turbulence" baseFrequency="0.03" numOctaves="2" seed="{seed}"/>'
                  f'<feColorMatrix type="matrix" values="0 0 0 0 .75  0 0 0 0 .92  0 0 0 0 .95  0 0 0 -2.2 1.1"/></filter>')


def paralelepipedo(w, h, seed=1):
    """Pátio de paralelepípedos cinza-quente, pequenos (3 fiadas de 2 a 3 pedras por quadrado), juntas escuras."""
    R = random.Random(seed)
    bh = S / 3
    body = ""
    for r in range(int(h // bh) + 1):
        y = r * bh
        x = -R.randint(0, 90)
        while x < w:
            L = R.randint(58, 92)
            j = lambda: R.uniform(-3, 3)
            sx, sy, sw, sh_ = x + 3 + j(), y + 3 + j(), L - 6 + j(), bh - 6 + j()
            body += (f'<rect x="{sx:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sh_:.1f}" rx="{R.randint(12,22)}" '
                     f'fill="{shade("#86796a", R.uniform(.78, 1.15))}"/>'
                     f'<rect x="{sx:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sh_:.1f}" rx="{R.randint(12,22)}" fill="url(#ppg)"/>')
            x += L
    return wrap(w, h, f'<rect width="{w}" height="{h}" fill="#2b2622"/><g filter="url(#pp)">{body}</g>',
                '<radialGradient id="ppg" cx=".4" cy=".35" r=".7"><stop offset=".5" stop-color="#000" stop-opacity="0"/>'
                '<stop offset="1" stop-color="#120f0c" stop-opacity=".55"/></radialGradient>'
                + noise("pp", "0.07", seed, (.2, .18, .15), 1.3, -.4))


def marmore(w, h, seed=1):
    """Lajes grandes de mármore claro (2 x 2 por quadrado) com veios suaves."""
    R = random.Random(seed)
    slabs, veins = "", ""
    for i in range(int(w // 100) + 1):
        for k in range(int(h // 100) + 1):
            x0, y0 = i * 100, k * 100
            slabs += f'<rect x="{x0+1.5}" y="{y0+1.5}" width="97" height="97" fill="{shade("#dcd6ca", R.uniform(.93, 1.05))}"/>'
            for _ in range(R.choice((0, 1, 1, 2))):
                ax, ay = x0 + R.uniform(8, 30), y0 + R.uniform(8, 92)
                bx, by = x0 + R.uniform(70, 92), y0 + R.uniform(8, 92)
                veins += (f'<path d="M{ax:.0f},{ay:.0f} C{x0+R.uniform(25,50):.0f},{ay+R.uniform(-25,25):.0f} {x0+R.uniform(50,75):.0f},{by+R.uniform(-25,25):.0f} {bx:.0f},{by:.0f}" '
                          f'stroke="{R.choice(["#9a958c", "#a8a194", "#8e9298"])}" stroke-width="{R.uniform(1.5,3.5):.1f}" opacity="{R.uniform(.25,.45):.2f}"/>')
    return wrap(w, h, f'<rect width="{w}" height="{h}" fill="#8f8a80"/><g filter="url(#mm)">{slabs}</g>'
                f'<rect width="{w}" height="{h}" filter="url(#mv)" opacity=".22"/>'
                f'<g fill="none" stroke-linecap="round" filter="url(#mvb)">{veins}</g>',
                noise("mm", "0.03", seed, (.55, .52, .48), .6, -.2, 4)
                + '<filter id="mvb" x="0" y="0" width="100%" height="100%" filterUnits="userSpaceOnUse"><feGaussianBlur stdDeviation="1.2"/></filter>'
                + f'<filter id="mv" x="0" y="0" width="100%" height="100%" filterUnits="userSpaceOnUse">'
                  f'<feTurbulence type="turbulence" baseFrequency="0.012 0.03" numOctaves="3" seed="{seed}"/>'
                  f'<feColorMatrix type="matrix" values="0 0 0 0 .45  0 0 0 0 .44  0 0 0 0 .42  0 0 0 -3 .9"/></filter>')


def tapete(w, h, seed=1):
    """Tapete vermelho-escuro com trama e um padrão geométrico discreto que se repete (sem borda)."""
    pat = ('<pattern id="tpm" width="100" height="100" patternUnits="userSpaceOnUse">'
           '<g fill="none" stroke="#3e0b10" stroke-width="3" opacity=".75">'
           '<path d="M50,8 L92,50 L50,92 L8,50 Z"/><path d="M50,26 L74,50 L50,74 L26,50 Z"/></g>'
           '<path d="M50,40 L60,50 L50,60 L40,50 Z" fill="#a8823c" opacity=".55"/>'
           '<g fill="#a8823c" opacity=".35"><circle cx="0" cy="0" r="5"/><circle cx="100" cy="0" r="5"/><circle cx="0" cy="100" r="5"/><circle cx="100" cy="100" r="5"/></g>'
           '<g stroke="#8e2a2a" stroke-width="1.5" opacity=".6"><line x1="0" y1="50" x2="8" y2="50"/><line x1="92" y1="50" x2="100" y2="50"/>'
           '<line x1="50" y1="0" x2="50" y2="8"/><line x1="50" y1="92" x2="50" y2="100"/></g></pattern>'
           '<pattern id="tpw" width="4" height="4" patternUnits="userSpaceOnUse">'
           '<rect width="4" height="2" fill="#000" opacity=".12"/><rect x="0" y="0" width="2" height="4" fill="#fff" opacity=".04"/></pattern>')
    return wrap(w, h, f'<rect width="{w}" height="{h}" fill="#5a1519" filter="url(#tp)"/>'
                f'<rect width="{w}" height="{h}" fill="url(#tpm)"/><rect width="{w}" height="{h}" fill="url(#tpw)"/>',
                pat + noise("tp", "0.012 0.4", seed, (.3, .06, .07), 1.2, -.45, 3))


def rocha_vulcanica(w, h, seed=1):
    """Basalto escuro: colunas hexagonais irregulares vistas de cima, cortadas por fissuras."""
    R = random.Random(seed)
    r = 40
    dx, dy = r * 1.732, r * 1.5
    body, cracks = "", ""
    for row in range(int(h // dy) + 2):
        for col in range(int(w // dx) + 2):
            cx = col * dx + (row % 2) * dx / 2 + R.uniform(-5, 5)
            cy = row * dy + R.uniform(-5, 5)
            pts = " ".join(f"{cx+r*R.uniform(.9,1.04)*math.cos(math.pi/6+a*math.pi/3):.1f},{cy+r*R.uniform(.9,1.04)*math.sin(math.pi/6+a*math.pi/3):.1f}" for a in range(6))
            body += f'<polygon points="{pts}" fill="{shade("#3a3634", R.uniform(.6, 1.3))}" stroke="#0e0d0d" stroke-width="3"/>'
    for _ in range(max(1, w * h // 50000)):
        x, y, ang = R.uniform(0, w), R.uniform(0, h), R.uniform(0, 6.3)
        d = f"M{x:.0f},{y:.0f}"
        for _ in range(R.randint(5, 10)):
            ang += R.uniform(-.7, .7)
            L = R.uniform(12, 26)
            x, y = x + L * math.cos(ang), y + L * math.sin(ang)
            d += f" L{x:.0f},{y:.0f}"
        cracks += f'<path d="{d}" stroke-width="{R.uniform(1.5,3):.1f}"/>'
    return wrap(w, h, f'<rect width="{w}" height="{h}" fill="#0e0d0d"/><g filter="url(#rv)">{body}</g>'
                f'<g stroke="#080707" fill="none" stroke-linejoin="round" opacity=".9">{cracks}</g>',
                noise("rv", "0.09", seed, (.12, .11, .11), 1.4, -.45))


def _fiadas(w, h, seed, cor, rh, wmin, wmax):
    """Telhado visto de cima: fiadas horizontais; a borda de baixo de cada fiada faz sombra na de baixo."""
    R = random.Random(seed)
    tiles, joints, shadows = "", "", ""
    for r in range(int(h // rh) + 1):
        y = r * rh
        x = -R.randint(0, wmax)
        while x < w:
            L = R.randint(wmin, wmax)
            c = shade(cor, R.uniform(.82, 1.15))
            tiles += f'<path d="M{x+1},{y} h{L-2} v{rh-4} q-{(L-2)/2:.0f},{R.uniform(2,6):.0f} -{L-2},0 Z" fill="{c}"/>'
            joints += f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y+rh-3}"/>'
            x += L
        shadows += f'<rect x="0" y="{y}" width="{w}" height="{rh*.45:.0f}" fill="url(#fsh)"/>'
    return tiles, joints, shadows


def telhado_ardosia(w, h, seed=1):
    """Ardósia cinza-azulada: fiadas de placas sobrepostas (5 por quadrado), sombra em cada fiada."""
    tiles, joints, shadows = _fiadas(w, h, seed, "#56606c", S / 5, 34, 58)
    return wrap(w, h, f'<rect width="{w}" height="{h}" fill="#1c2026"/><g filter="url(#ta)">{tiles}</g>{shadows}'
                f'<g stroke="#1c2026" stroke-width="2">{joints}</g>',
                '<linearGradient id="fsh" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0c0e12" stop-opacity=".75"/><stop offset="1" stop-color="#0c0e12" stop-opacity="0"/></linearGradient>'
                + noise("ta", "0.05 0.15", seed, (.2, .23, .27), 1.2, -.4))


def telhado_telha(w, h, seed=1):
    """Telhas de barro (canal) avermelhadas: colunas de telhas curvas em fiadas."""
    R = random.Random(seed)
    rh, tw = S / 4, S / 6
    tiles, shadows = "", ""
    for r in range(int(h // rh) + 1):
        y = r * rh
        for c in range(int(w // tw) + 1):
            x = c * tw
            tiles += f'<rect x="{x+1:.1f}" y="{y-6}" width="{tw-2:.1f}" height="{rh+4}" rx="{tw/2-1:.1f}" ry="8" fill="{shade("#a6532f", R.uniform(.8, 1.15))}"/>'
        shadows += f'<rect x="0" y="{y}" width="{w}" height="{rh*.4:.0f}" fill="url(#fsh)"/>'
    return wrap(w, h, f'<rect width="{w}" height="{h}" fill="#3a1a10"/><g filter="url(#tt)">{tiles}</g>'
                f'<rect width="{w}" height="{h}" fill="url(#tcv)"/>{shadows}',
                '<linearGradient id="fsh" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1c0a04" stop-opacity=".65"/><stop offset="1" stop-color="#1c0a04" stop-opacity="0"/></linearGradient>'
                f'<pattern id="tcv" width="{tw:.4f}" height="{S}" patternUnits="userSpaceOnUse">'
                f'<rect width="{tw:.4f}" height="{S}" fill="url(#tcg)"/></pattern>'
                '<linearGradient id="tcg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000" stop-opacity=".45"/>'
                '<stop offset=".4" stop-color="#fff" stop-opacity=".12"/><stop offset=".55" stop-color="#fff" stop-opacity=".18"/><stop offset="1" stop-color="#000" stop-opacity=".5"/></linearGradient>'
                + noise("tt", "0.06", seed, (.3, .14, .08), 1.2, -.4))


def muralha(w, h, seed=1):
    """Muralha: blocos grandes de pedra escura (3 fiadas por quadrado) com cintas de ferro rebitadas."""
    R = random.Random(seed)
    bh = S / 3
    body = ""
    for r in range(int(h // bh) + 1):
        x = -R.randint(0, 120)
        while x < w:
            L = R.randint(100, 170)
            body += f'<rect x="{x+3}" y="{r*bh+3:.1f}" width="{L-6}" height="{bh-6:.1f}" rx="5" fill="{shade("#45423d", R.uniform(.8, 1.15))}"/>'
            x += L
    bands, rivets = "", ""
    for i in range(int(w // S) + 1):
        x = i * S + 100
        bands += f'<rect x="{x-9}" y="0" width="18" height="{h}"/>'
    for k in range(int(h // S) + 1):
        y = k * S + 100
        bands += f'<rect x="0" y="{y-9}" width="{w}" height="18"/>'
    pat = ('<pattern id="mr" width="200" height="200" patternUnits="userSpaceOnUse">'
           '<rect x="84" y="84" width="32" height="32" rx="3" fill="#2a2b2e" stroke="#0e0e10" stroke-width="2"/>'
           + "".join(f'<circle cx="{c}" cy="100" r="3" fill="#6a6c70"/><circle cx="100" cy="{c}" r="3" fill="#6a6c70"/>' for c in (12, 37, 62, 138, 163, 188))
           + "".join(f'<circle cx="{a}" cy="{b}" r="3.5" fill="#7a7c80"/>' for a in (91, 109) for b in (91, 109)) + '</pattern>')
    return wrap(w, h, f'<rect width="{w}" height="{h}" fill="#17161a"/><g filter="url(#mu)">{body}</g>'
                f'<g fill="#26282c" stroke="#0e0e10" stroke-width="2" filter="url(#fe)">{bands}</g>'
                f'<rect width="{w}" height="{h}" fill="url(#mr)"/>',
                pat + noise("mu", "0.06", seed, (.12, .11, .1), 1.3, -.4)
                + noise("fe", "0.12", seed, (.24, .13, .08), .6, -.3))


def vazio(w, h, seed=1):
    """O nada em volta das salas extradimensionais: preto azulado quase liso, com leve névoa."""
    return wrap(w, h, f'<rect width="{w}" height="{h}" fill="#07080d"/>'
                f'<rect width="{w}" height="{h}" filter="url(#vz)"/>',
                f'<filter id="vz" x="0" y="0" width="100%" height="100%" filterUnits="userSpaceOnUse">'
                f'<feTurbulence type="fractalNoise" baseFrequency="0.004" numOctaves="4" seed="{seed}"/>'
                f'<feColorMatrix type="matrix" values="0 0 0 0 .2  0 0 0 0 .24  0 0 0 0 .38  0 0 0 .9 -.38"/></filter>')


def azulejo(w, h, seed=1):
    """Azulejos claros (4 x 4 por quadrado) com detalhes azul-esverdeados, para os banhos."""
    R = random.Random(seed)
    stains = "".join(f'<rect x="{R.randrange(0, w, 50)+1}" y="{R.randrange(0, h, 50)+1}" width="48" height="48" fill="{R.choice(["#c9bc9e", "#f4efe4", "#b9c9c2"])}" opacity=".5"/>'
                     for _ in range(w * h // 12000))
    pat = ('<pattern id="az" width="50" height="50" patternUnits="userSpaceOnUse">'
           '<rect width="50" height="50" fill="#a59d8e"/><rect x="1.2" y="1.2" width="47.6" height="47.6" rx="1.5" fill="#e6dfcf"/>'
           '<g fill="#3f8f8a" opacity=".7">'
           '<path d="M1.2,1.2 H11 A10,10 0 0 1 1.2,11 Z"/><path d="M48.8,1.2 V11 A10,10 0 0 1 39,1.2 Z"/>'
           '<path d="M48.8,48.8 H39 A10,10 0 0 1 48.8,39 Z"/><path d="M1.2,48.8 V39 A10,10 0 0 1 11,48.8 Z"/></g>'
           '<path d="M25,17 L33,25 L25,33 L17,25 Z" fill="#4f9c96" opacity=".55"/>'
           '<circle cx="25" cy="25" r="2.5" fill="#2f6f74" opacity=".7"/></pattern>')
    return wrap(w, h, f'<rect width="{w}" height="{h}" fill="url(#az)"/>{stains}'
                f'<rect width="{w}" height="{h}" filter="url(#azn)" opacity=".5"/>',
                pat + f'<filter id="azn" x="0" y="0" width="100%" height="100%" filterUnits="userSpaceOnUse">'
                f'<feTurbulence type="fractalNoise" baseFrequency="0.02" numOctaves="3" seed="{seed}"/>'
                f'<feColorMatrix type="matrix" values="0 0 0 0 .45  0 0 0 0 .4  0 0 0 0 .3  0 0 0 1.2 -.55"/></filter>')


MATERIAIS = {"piso_madeira": piso_madeira, "piso_pedra": piso_pedra, "grama": grama, "terra": terra, "parede": parede, "agua": agua,
             "paralelepipedo": paralelepipedo, "marmore": marmore, "tapete": tapete, "rocha_vulcanica": rocha_vulcanica,
             "telhado_ardosia": telhado_ardosia, "telhado_telha": telhado_telha, "muralha": muralha, "vazio": vazio,
             "azulejo": azulejo, "madeira_escura": madeira_escura}


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

    # ---------- escada (1 quadrado, cobre o chão): degraus de pedra subindo para cima ----------
    R = random.Random(3)
    sh = S / 6
    steps = ""
    for i in range(6):
        y = i * sh
        k = 1.3 - i * .15  # quanto mais baixo o degrau, mais escuro
        x = -R.randint(20, 80)
        while x < S:
            L = R.randint(110, 170)
            steps += f'<rect x="{x+1}" y="{y:.1f}" width="{L-2}" height="{sh:.1f}" fill="{shade("#77736b", k*R.uniform(.93, 1.06))}"/>'
            x += L
    edges = "".join(f'<rect x="0" y="{i*sh:.1f}" width="200" height="{sh*(.45+i*.08):.1f}" fill="url(#esh)" opacity="{.6+i*.08:.2f}"/>'
                    f'<line x1="0" y1="{i*sh-2:.1f}" x2="200" y2="{i*sh-2:.1f}" stroke="{shade("#b8b3a8", 1.2-i*.1)}" stroke-width="3"/>'
                    f'<line x1="0" y1="{i*sh:.1f}" x2="200" y2="{i*sh:.1f}" stroke="#1c1b19" stroke-width="2.5"/>' for i in range(1, 6))
    svg("escada", f'<rect width="200" height="200" fill="#2a2825"/><g filter="url(#es)">{steps}</g>{edges}'
        '<line x1="0" y1="1.5" x2="200" y2="1.5" stroke="#c8c3b8" stroke-width="3"/>',
        '<linearGradient id="esh" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0d0c0b" stop-opacity=".85"/><stop offset="1" stop-color="#0d0c0b" stop-opacity="0"/></linearGradient>'
        + noise("es", "0.05", 3, (.18, .17, .15), 1.2, -.35))

    print("peças em", D)


if __name__ == "__main__":
    pecas()
