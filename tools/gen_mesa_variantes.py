"""Gera as variações da mesa (SVG) a partir de assets/mesa/mesa_inteira.svg.
Uso: python3 tools/gen_mesa_variantes.py && NODE_PATH=$(npm root -g) node tools/render.js assets/mesa/mesa_<nome>.svg"""
import re, random, math, pathlib
D = pathlib.Path(__file__).resolve().parent.parent / "assets" / "mesa"
base = re.sub(r"<metadata>.*?</metadata>", "", (D / "mesa_inteira.svg").read_text(), flags=re.S)
base = base.replace(' xmlns:c2pa="http://c2pa.org/manifest"', "")
TOP = '<g filter="url(#shadow)"><use href="#top"/></g>'
CLIP = '<clipPath id="tclip"><rect x="40" y="40" width="360" height="160" rx="5"/></clipPath>'
EXTRA = '''<defs>
<filter id="b2" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2"/></filter>
<filter id="b5" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="5"/></filter>
<filter id="frost"><feTurbulence type="fractalNoise" baseFrequency="0.05" numOctaves="3" seed="2"/><feColorMatrix values="0 0 0 0 0.9  0 0 0 0 0.97  0 0 0 0 1  0 0 0 1.6 -0.55"/></filter>
<filter id="ice" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values=".55 0 0 0 .1  0 .65 0 0 .25  0 .1 .5 0 .5  0 0 0 1 0"/></filter>
<filter id="rot" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values=".35 .3 .1 0 .02  .3 .35 .1 0 .03  .2 .25 .1 0 .01  0 0 0 1 0"/></filter>
<radialGradient id="scorch"><stop offset="0" stop-color="#120804" stop-opacity=".85"/><stop offset=".6" stop-color="#2a1206" stop-opacity=".5"/><stop offset="1" stop-color="#2a1206" stop-opacity="0"/></radialGradient>
<radialGradient id="acid"><stop offset="0" stop-color="#b6ff3a" stop-opacity=".95"/><stop offset=".55" stop-color="#5fbf1a" stop-opacity=".8"/><stop offset="1" stop-color="#2f6a0c" stop-opacity="0"/></radialGradient>
<radialGradient id="hole"><stop offset="0" stop-color="#0d1a05"/><stop offset=".7" stop-color="#1e3a0a" stop-opacity=".8"/><stop offset="1" stop-color="#2f5a10" stop-opacity="0"/></radialGradient>
<radialGradient id="gold"><stop offset="0" stop-color="#fff3b0" stop-opacity=".7"/><stop offset="1" stop-color="#ffd24a" stop-opacity="0"/></radialGradient>
</defs>'''
R = random.Random(11)

def write(name, body, top=TOP):
    s = base.replace(TOP, top + CLIP).replace("</svg>", EXTRA + body + "</svg>")
    (D / f"mesa_{name}.svg").write_text(s)

# 1) cortada: corte reto diagonal, metades afastadas
write("cortada", '''
<clipPath id="ca"><polygon points="0,0 250,0 190,240 0,240"/></clipPath>
<clipPath id="cb"><polygon points="250,0 440,0 440,240 190,240"/></clipPath>''' ,
 top='''<g filter="url(#shadow)" transform="translate(-12 -2) rotate(-3 120 120)"><g clip-path="url(#ca)"><use href="#top"/>
<line x1="250" y1="40" x2="190" y2="200" stroke="#d9a868" stroke-width="5"/></g></g>
<g filter="url(#shadow)" transform="translate(12 3) rotate(3 320 120)"><g clip-path="url(#cb)"><use href="#top"/>
<line x1="250" y1="40" x2="190" y2="200" stroke="#d9a868" stroke-width="5"/></g></g>''')

# 2) congelada: tom azulado + geada + cristais + pingentes
crystals = "".join(
    f'<g transform="translate({R.randint(60,380)} {R.randint(55,185)}) rotate({R.randint(0,60)})" stroke="#f4fbff" stroke-width="1.6" opacity=".85">'
    f'<line x1="-{s}" y1="0" x2="{s}" y2="0"/><line x1="0" y1="-{s}" x2="0" y2="{s}"/><line x1="-{s*.7:.0f}" y1="-{s*.7:.0f}" x2="{s*.7:.0f}" y2="{s*.7:.0f}"/><line x1="-{s*.7:.0f}" y1="{s*.7:.0f}" x2="{s*.7:.0f}" y2="-{s*.7:.0f}"/></g>'
    for s in [R.randint(5, 10) for _ in range(16)])
icicles = "".join(f'<path d="M{x},200 l4,{h} l4,-{h} z" fill="#e6f7ff" stroke="#9fd3ef" stroke-width=".8"/>' for x, h in [(R.randint(50, 390), R.randint(6, 14)) for _ in range(14)])
write("congelada", f'''<g clip-path="url(#tclip)"><rect x="40" y="40" width="360" height="160" fill="#bfe6ff" opacity=".15"/>
<rect x="40" y="40" width="360" height="160" filter="url(#frost)" opacity=".4"/></g>{crystals}{icicles}
<rect x="40" y="40" width="360" height="160" rx="5" fill="none" stroke="#e9f8ff" stroke-width="3" opacity=".8"/>''',
 top='<g filter="url(#shadow)"><g filter="url(#ice)"><use href="#top"/></g></g>')

# 3) estilhaçada: muitos cacos gelados espalhados
shards = []
cols, rows = 5, 3
k = 0
for i in range(cols):
    for j in range(rows):
        x0, y0 = 40 + i * 72, 40 + j * 53
        jit = lambda: R.randint(-7, 7)
        a, b, c, d = (x0 + jit(), y0 + jit()), (x0 + 72 + jit(), y0 + jit()), (x0 + 72 + jit(), y0 + 53 + jit()), (x0 + jit(), y0 + 53 + jit())
        for tri in ([a, b, c], [a, c, d]) if (i + j) % 2 else ([a, b, d], [b, c, d]):
            cx, cy = sum(p[0] for p in tri) / 3, sum(p[1] for p in tri) / 3
            dx, dy = (cx - 220) * .16 + R.randint(-5, 5), (cy - 120) * .22 + R.randint(-4, 4)
            poly = " ".join(f"{x},{y}" for x, y in tri)
            shards.append(f'<clipPath id="s{k}"><polygon points="{poly}"/></clipPath>'
                          f'<g filter="url(#shadow)" transform="translate({dx:.0f} {dy:.0f}) rotate({R.randint(-18,18)} {cx:.0f} {cy:.0f})"><g clip-path="url(#s{k})"><g filter="url(#ice)"><use href="#top"/></g></g>'
                          f'<polygon points="{poly}" fill="#dff4ff" opacity=".2" stroke="#f4fbff" stroke-width="1.2"/></g>')
            k += 1
icebits = "".join(f'<polygon points="{x},{y} {x+R.randint(4,9)},{y+R.randint(-3,3)} {x+R.randint(1,5)},{y+R.randint(4,8)}" fill="#e9f8ff" opacity=".85"/>' for x, y in [(R.randint(20, 420), R.randint(15, 225)) for _ in range(40)])
write("estilhacada", icebits, top="".join(shards))

# 4) chamuscada: manchas de queimado e fumaça, sem chamas
sc = "".join(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="url(#scorch)"/>' for x, y, rx, ry in [(150,110,70,45),(270,140,80,50),(330,80,50,35),(110,170,45,25),(220,70,55,30)])
smoke = '<g filter="url(#b5)" fill="#8d8d8d" opacity=".3"><ellipse cx="170" cy="95" rx="40" ry="16"/><ellipse cx="285" cy="130" rx="45" ry="18"/></g>'
write("chamuscada", f'<g clip-path="url(#tclip)">{sc}</g>{smoke}')

# 5) corroída: poças de ácido, buracos e bolhas
puddles = [(130,95,34,20),(255,150,44,24),(330,75,24,14),(190,175,22,12)]
acid = "".join(f'<ellipse cx="{x}" cy="{y}" rx="{rx*1.15:.0f}" ry="{ry*1.15:.0f}" fill="url(#hole)"/><ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="url(#acid)"/>' for x, y, rx, ry in puddles)
bubbles = "".join(f'<circle cx="{x+R.randint(-rx//2,rx//2)}" cy="{y+R.randint(-ry//2,ry//2)}" r="{R.choice([1.5,2,2.5,3])}" fill="none" stroke="#e4ffb0" stroke-width="1"/>' for x, y, rx, ry in puddles for _ in range(5))
drips = '<g filter="url(#b5)" fill="#9cff3a" opacity=".25"><ellipse cx="140" cy="85" rx="30" ry="12"/><ellipse cx="260" cy="140" rx="35" ry="14"/></g>'
write("corroida", f'<g clip-path="url(#tclip)">{acid}{bubbles}</g>{drips}')

# 6) flechada: flechas cravadas (vistas de cima)
def arrow(x, y, ang, L=70):
    return (f'<g transform="translate({x} {y}) rotate({ang})" filter="url(#shadow)">'
            f'<circle r="4" fill="#2a1a0b"/><line x1="0" y1="0" x2="{L}" y2="0" stroke="#7a5a32" stroke-width="3.5" stroke-linecap="round"/>'
            f'<path d="M{L-18},0 l14,-8 l6,0 l-10,8 l10,8 l-6,0 z" fill="#c9372c" stroke="#5a1410" stroke-width="1"/>'
            f'<path d="M{L-30},0 l12,-6 l4,0 l-8,6 l8,6 l-4,0 z" fill="#e9e2d0" stroke="#7a7060" stroke-width=".8"/></g>')
write("flechada", arrow(150, 100, -150) + arrow(270, 140, -30) + arrow(210, 170, 160, 60) +
      '<g stroke="#2b1a0b" stroke-width="1.4" opacity=".7"><path d="M150,100 l-10,-6 M150,100 l8,8"/><path d="M270,140 l9,-7 M270,140 l-8,6"/></g>')

# 7) apodrecida: madeira cinza-esverdeada, manchas, rachaduras, cogumelos
spots = "".join(f'<ellipse cx="{R.randint(60,380)}" cy="{R.randint(50,190)}" rx="{R.randint(10,28)}" ry="{R.randint(6,14)}" fill="#1a2210" opacity=".55" filter="url(#b2)"/>' for _ in range(12))
cracks = "".join(f'<path d="M{x},{y} l{R.randint(-15,15)},{R.randint(8,16)} l{R.randint(-12,12)},{R.randint(8,16)} l{R.randint(-10,10)},{R.randint(6,12)}" stroke="#0e130a" stroke-width="1.8" fill="none" opacity=".8"/>' for x, y in [(R.randint(60, 380), R.randint(45, 120)) for _ in range(8)])
def mush(x, y, r):
    return f'<g transform="translate({x} {y})"><circle r="{r+1.5}" fill="#2a1d12"/><circle r="{r}" fill="#c9b48a"/><circle r="{r*.45:.1f}" cx="-{r*.25:.1f}" cy="-{r*.25:.1f}" fill="#efe2c2"/></g>'
mushes = "".join(mush(x, y, r) for x, y, r in [(90,70,6),(98,78,4),(330,175,7),(318,182,4.5),(250,60,5)])
write("apodrecida", f'<g clip-path="url(#tclip)">{spots}{cracks}</g>{mushes}', top='<g filter="url(#shadow)"><g filter="url(#rot)"><use href="#top"/></g></g>')

# 8) radiante: brilho dourado e marcas de luz
rays = "".join(f'<line x1="220" y1="120" x2="{220+math.cos(a)*200:.0f}" y2="{120+math.sin(a)*110:.0f}" stroke="#fff1a8" stroke-width="3" opacity=".35"/>' for a in [i * math.pi / 8 for i in range(16)])
marks = "".join(f'<path d="M{x},{y} l{R.randint(-20,20)},{R.randint(-10,10)} l{R.randint(-20,20)},{R.randint(-10,10)}" stroke="#ffd24a" stroke-width="2.2" fill="none" opacity=".9"/>' for x, y in [(R.randint(70, 370), R.randint(55, 185)) for _ in range(10)])
write("radiante", f'<ellipse cx="220" cy="120" rx="218" ry="118" fill="url(#gold)"/><g clip-path="url(#tclip)" filter="url(#b2)">{rays}</g><g clip-path="url(#tclip)">{marks}</g>'
      '<rect x="40" y="40" width="360" height="160" rx="5" fill="none" stroke="#ffe680" stroke-width="3" opacity=".8"/>')
print("ok")
