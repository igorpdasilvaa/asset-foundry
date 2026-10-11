"""Gera os SVGs das armadilhas e do pedregulho em assets/armadilhas/ (1 quadrado = 200 px, fundo transparente).
Uso: python3 tools/gen_armadilhas.py && NODE_PATH=$(npm root -g) node tools/render.js assets/armadilhas/*.svg"""
import math, random, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gen_pecas_mapa import noise

D = pathlib.Path(__file__).resolve().parent.parent / "assets" / "armadilhas"
S = 200

COMMON = (
    '<filter id="bl3" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3"/></filter>'
    '<filter id="bl6" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>'
    '<linearGradient id="iron" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#9aa0a4"/><stop offset=".5" stop-color="#5d6367"/><stop offset="1" stop-color="#2f3336"/></linearGradient>'
    '<radialGradient id="hole" cx=".5" cy=".55"><stop offset="0" stop-color="#050403"/><stop offset=".7" stop-color="#140f0a"/><stop offset="1" stop-color="#2b2016"/></radialGradient>'
    '<radialGradient id="rock" cx=".38" cy=".34" r=".75"><stop offset="0" stop-color="#a7a39a"/><stop offset=".55" stop-color="#77736a"/><stop offset="1" stop-color="#46433d"/></radialGradient>'
)


def write(name, body, defs=""):
    D.mkdir(parents=True, exist_ok=True)
    (D / f"{name}.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{S//2}" height="{S//2}" viewBox="0 0 {S} {S}">'
        f'<defs>{COMMON}{defs}</defs>{body}</svg>')


def jaws(closed):
    """Armadilha de urso vista de cima: aro de ferro com dentes, mola, corrente e estaca."""
    R = random.Random(4)
    out = '<ellipse cx="104" cy="108" rx="70" ry="64" fill="#000" opacity=".35" filter="url(#bl6)"/>'
    # corrente até a estaca
    for i in range(6):
        x, y = 40 - i * 5, 150 + i * 6
        out += f'<ellipse cx="{x}" cy="{y}" rx="6" ry="4" fill="none" stroke="#3b3f42" stroke-width="3" transform="rotate({-50 + i * 20} {x} {y})"/>'
    out += '<circle cx="14" cy="186" r="9" fill="#5a3d22" stroke="#2a1a0c" stroke-width="3"/>'
    if closed:
        # mandíbulas fechadas: duas metades encostadas, dentes cruzados
        out += '<path d="M40,100 Q100,60 160,100" fill="none" stroke="url(#iron)" stroke-width="14" stroke-linecap="round"/>'
        out += '<path d="M40,100 Q100,140 160,100" fill="none" stroke="url(#iron)" stroke-width="14" stroke-linecap="round"/>'
        for i in range(9):
            x = 52 + i * 12
            out += f'<path d="M{x},{92} l5,10 l5,-10" fill="#c9ccce" stroke="#2b2e30" stroke-width="1.5"/>'
        out += '<ellipse cx="100" cy="100" rx="22" ry="9" fill="#5b1a14" opacity=".75"/>'
    else:
        out += '<ellipse cx="100" cy="100" rx="64" ry="58" fill="none" stroke="url(#iron)" stroke-width="12"/>'
        for i in range(18):
            a = i / 18 * 2 * math.pi
            x1, y1 = 100 + 58 * math.cos(a), 100 + 52 * math.sin(a)
            x2, y2 = 100 + 44 * math.cos(a), 100 + 39 * math.sin(a)
            l, r = a - .09, a + .09
            out += (f'<path d="M{100+58*math.cos(l):.1f},{100+52*math.sin(l):.1f} L{x2:.1f},{y2:.1f} '
                    f'L{100+58*math.cos(r):.1f},{100+52*math.sin(r):.1f} Z" fill="#c9ccce" stroke="#2b2e30" stroke-width="1.2"/>')
        # prato do gatilho no meio
        out += '<circle cx="100" cy="100" r="18" fill="#4a4f52" stroke="#24272a" stroke-width="3"/><circle cx="100" cy="100" r="6" fill="#2b2e30"/>'
    # molas dos lados
    for x in (26, 174):
        out += f'<rect x="{x-8}" y="88" width="16" height="24" rx="5" fill="#4a4f52" stroke="#1f2224" stroke-width="2"/>'
    # folhas por cima (camuflagem)
    if not closed:
        for _ in range(9):
            x, y, a = R.randint(30, 170), R.randint(30, 170), R.randint(0, 180)
            out += f'<ellipse cx="{x}" cy="{y}" rx="9" ry="4" fill="{R.choice(["#6b5a2a", "#7d6a33", "#556a2a"])}" opacity=".8" transform="rotate({a} {x} {y})"/>'
    return out


def pit(open_):
    """Fosso: coberto por galhos e folhas, ou aberto com estacas no fundo."""
    R = random.Random(9)
    if open_:
        out = '<rect x="6" y="6" width="188" height="188" rx="26" fill="#3d2c1c"/>'
        out += '<rect x="16" y="16" width="168" height="168" rx="20" fill="url(#hole)"/>'
        for _ in range(7):
            x, y = R.randint(50, 150), R.randint(55, 150)
            out += f'<path d="M{x-5},{y+8} L{x},{y-10} L{x+5},{y+8} Z" fill="#7a5a36" stroke="#2a1a0c" stroke-width="1.5"/>'
        # galhos quebrados caídos para dentro
        for _ in range(5):
            x, y, a = R.randint(20, 180), R.choice([18, 182]), R.randint(-40, 40)
            out += f'<rect x="{x-24}" y="{y-3}" width="48" height="6" rx="3" fill="#5a3f24" transform="rotate({a} {x} {y})"/>'
        out += '<rect x="6" y="6" width="188" height="188" rx="26" fill="none" stroke="#1e150c" stroke-width="5"/>'
        return out
    out = '<rect x="10" y="10" width="180" height="180" rx="24" fill="#5c4a2c" opacity=".9" filter="url(#lv)"/>'
    for _ in range(14):
        x, y, a = R.randint(20, 180), R.randint(20, 180), R.randint(0, 180)
        out += f'<rect x="{x-30}" y="{y-2.5}" width="60" height="5" rx="2.5" fill="#4a3520" transform="rotate({a} {x} {y})"/>'
    for _ in range(40):
        x, y, a = R.randint(14, 186), R.randint(14, 186), R.randint(0, 180)
        out += f'<ellipse cx="{x}" cy="{y}" rx="10" ry="4.5" fill="{R.choice(["#6b5a2a", "#7d6a33", "#556a2a", "#4d5f26"])}" transform="rotate({a} {x} {y})"/>'
    return out


def tripwire(cut):
    """Fio esticado entre duas estacas (com sininhos); cortado depois de disparar."""
    out = ''
    for x in (22, 178):
        out += f'<circle cx="{x+3}" cy="{103}" r="12" fill="#000" opacity=".35" filter="url(#bl3)"/>'
        out += f'<circle cx="{x}" cy="100" r="10" fill="#6a4a2a" stroke="#2a1a0c" stroke-width="3"/><circle cx="{x}" cy="100" r="4" fill="#3b2614"/>'
    if cut:
        out += '<path d="M30,100 Q60,112 84,128" fill="none" stroke="#c8b98a" stroke-width="3"/>'
        out += '<path d="M170,100 Q140,90 118,74" fill="none" stroke="#c8b98a" stroke-width="3"/>'
    else:
        out += '<line x1="30" y1="100" x2="170" y2="100" stroke="#000" stroke-width="3" opacity=".3" transform="translate(3 4)"/>'
        out += '<line x1="30" y1="100" x2="170" y2="100" stroke="#d6c79a" stroke-width="2.5"/>'
        for x in (70, 100, 130):
            out += f'<circle cx="{x}" cy="104" r="5" fill="#b08a3c" stroke="#5a4214" stroke-width="1.5"/>'
    return out


def boulder():
    R = random.Random(2)
    pts = []
    for i in range(14):
        a = i / 14 * 2 * math.pi
        r = R.uniform(70, 86)
        pts.append(f"{100 + r * math.cos(a):.1f},{100 + r * math.sin(a) * .92:.1f}")
    poly = " ".join(pts)
    out = f'<polygon points="{poly}" fill="#000" opacity=".45" filter="url(#bl6)" transform="translate(9 11)"/>'
    out += f'<polygon points="{poly}" fill="url(#rock)" stroke="#2c2a26" stroke-width="4" filter="url(#rn)"/>'
    for _ in range(4):
        x, y = R.randint(60, 140), R.randint(60, 140)
        out += f'<path d="M{x},{y} l{R.randint(-20,20)},{R.randint(8,18)} l{R.randint(-14,14)},{R.randint(6,14)}" stroke="#34312c" stroke-width="2" fill="none" opacity=".7"/>'
    for _ in range(5):
        x, y = R.randint(50, 150), R.randint(110, 165)
        out += f'<ellipse cx="{x}" cy="{y}" rx="{R.randint(8,16)}" ry="{R.randint(4,8)}" fill="#5d7034" opacity=".55"/>'
    return out


def main():
    write("urso_armada", jaws(False))
    write("urso_fechada", jaws(True))
    write("fosso_coberto", pit(False), noise("lv", "0.05", 3, (.32, .26, .14), 1.2, -.35))
    write("fosso_aberto", pit(True))
    write("fio_armado", tripwire(False))
    write("fio_cortado", tripwire(True))
    write("pedregulho", boulder(), noise("rn", "0.06", 5, (.36, .35, .32), 1.1, -.4))
    print("armadilhas em", D)


if __name__ == "__main__":
    main()
