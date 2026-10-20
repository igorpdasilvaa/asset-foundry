"""Gera os SVGs do grupo "construcao" de Candlekeep: muralha, portão e Porta Esmeralda (assets/<id>/).
1 quadrado = 200 px. Todas as peças cobrem o quadrado inteiro e emendam com as vizinhas (lado a lado).
Portão e Porta Esmeralda são tokens de porta: desenho horizontal (o mapa gira 90° em muralhas verticais).
Uso: python3 tools/gen_construcao.py && NODE_PATH=... CHROME_PATH=... node tools/render.js assets/{muralha,portao,porta_esmeralda}/*.svg"""
import json, math, random, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gen_pecas_mapa import noise, shade, wrap

A = pathlib.Path(__file__).resolve().parent.parent / "assets"
FRAG = pathlib.Path(__file__).resolve().parent / "fragmentos" / "construcao.json"
S = 200

COMMON = (
    '<filter id="bl4" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter>'
    '<filter id="bl8" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="8"/></filter>'
)


def write(folder, name, body, defs=""):
    d = A / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.svg").write_text(wrap(S, S, body, COMMON + defs))


# ---------- helpers copiados de gen_estruturas.py ----------
def rubble(R, cx, cy, spread, n, colors, size=(8, 22)):
    out = ""
    for _ in range(n):
        x, y = cx + R.gauss(0, spread), cy + R.gauss(0, spread)
        r = R.uniform(*size)
        k = R.randint(4, 6)
        a0 = R.uniform(0, math.pi)
        pts = " ".join(f"{x+r*R.uniform(.6,1)*math.cos(a0+i*2*math.pi/k):.1f},{y+r*R.uniform(.6,1)*math.sin(a0+i*2*math.pi/k):.1f}" for i in range(k))
        out += f'<polygon points="{pts}" fill="{R.choice(colors)}" stroke="#1c1b19" stroke-width="1.5"/>'
    return out


def crack(R, x, y, steps, ang, width=2.2):
    d = f"M{x:.0f},{y:.0f}"
    for _ in range(steps):
        ang += R.uniform(-.6, .6)
        L = R.uniform(10, 22)
        x, y = x + L * math.cos(ang), y + L * math.sin(ang)
        d += f" L{x:.0f},{y:.0f}"
    return f'<path d="{d}" stroke="#0c0b0a" stroke-width="{width}" fill="none" stroke-linejoin="round"/>'


# ======================= Muralha =======================
# 3 fiadas de blocos grandes; as juntas são periódicas (200 px) e os blocos que passam da borda
# continuam no vizinho. Cintas de ferro em cruz no meio do quadrado, como o material "muralha".
ROWS = [[40, 170], [0, 110], [75, 155]]  # posições das juntas verticais (mod 200) em cada fiada
BH = S / 3
WALL_DEFS = (noise("mu", "0.06", 9, (.12, .11, .1), 1.3, -.4)
             + noise("fe", "0.12", 9, (.24, .13, .08), .6, -.3))


def blocks(R, base="#45423d"):
    out = ""
    for r, js in enumerate(ROWS):
        y = r * BH
        for a, b in zip(js, js[1:] + [js[0] + S]):
            c = shade(base, R.uniform(.8, 1.15))
            for off in (-S, 0, S):
                x0, x1 = a + off, b + off
                if x1 < 0 or x0 > S:
                    continue
                out += f'<rect x="{x0+3}" y="{y+3:.1f}" width="{x1-x0-6}" height="{BH-6:.1f}" rx="5" fill="{c}"/>'
    return f'<rect width="200" height="200" fill="#17161a"/><g filter="url(#mu)">{out}</g>'


def iron(skip=()):
    """Cintas de ferro em cruz (x=100 e y=100) com placa e rebites; skip = rebites que caíram."""
    rv = "".join(f'<circle cx="{c}" cy="100" r="3" fill="#6a6c70"/>' for c in (12, 37, 62, 138, 163, 188) if ("h", c) not in skip)
    rv += "".join(f'<circle cx="100" cy="{c}" r="3" fill="#6a6c70"/>' for c in (12, 37, 62, 138, 163, 188) if ("v", c) not in skip)
    return ('<g fill="#26282c" stroke="#0e0e10" stroke-width="2" filter="url(#fe)">'
            '<rect x="91" y="0" width="18" height="200"/><rect x="0" y="91" width="200" height="18"/></g>'
            '<rect x="84" y="84" width="32" height="32" rx="3" fill="#2a2b2e" stroke="#0e0e10" stroke-width="2"/>'
            + rv + "".join(f'<circle cx="{a}" cy="{b}" r="3.5" fill="#7a7c80"/>' for a in (91, 109) for b in (91, 109)))


def muralha():
    R = random.Random(1)
    inteira = blocks(R) + iron()
    write("muralha", "muralha_inteira", inteira, WALL_DEFS)

    R = random.Random(1)
    rach = blocks(R)
    R = random.Random(5)
    rach += (crack(R, 30, 8, 9, 1.3, 2.6) + crack(R, 170, 192, 8, -1.8, 2.6) + crack(R, 150, 40, 5, 2.4, 1.8)
             + crack(R, 40, 150, 5, -.4, 1.8))
    rach += iron(skip={("h", 37), ("v", 163), ("h", 188)})
    # cinta de ferro arrebentada num ponto, pontas levantadas
    rach += ('<rect x="40" y="88" width="34" height="24" fill="#17161a"/>'
             '<path d="M40,91 L50,84 L52,98 L40,109 Z" fill="#26282c" stroke="#0e0e10" stroke-width="2"/>'
             '<path d="M74,91 L64,86 L62,100 L74,109 Z" fill="#26282c" stroke="#0e0e10" stroke-width="2"/>')
    rach += rubble(R, 110, 120, 50, 7, ["#35322e", "#2b2926"], (3, 8))
    write("muralha", "muralha_rachada", rach, WALL_DEFS)

    R = random.Random(7)
    bars = "".join(
        f'<g transform="translate({100+R.gauss(0,35):.0f} {100+R.gauss(0,35):.0f}) rotate({R.uniform(0,180):.0f})">'
        f'<path d="M-{(L:=R.randint(30,60))/2:.0f},-6 Q0,{R.randint(-10,10)} {L/2:.0f},-6 L{L/2:.0f},6 Q0,{R.randint(0,16)} -{L/2:.0f},6 Z" fill="#26282c" stroke="#0e0e10" stroke-width="2"/>'
        f'<circle cx="-{L/2-8:.0f}" cy="0" r="2.5" fill="#6a6c70"/></g>' for _ in range(4))
    ru = ('<rect width="200" height="200" fill="#26231f" filter="url(#fd)"/>'
          + rubble(R, 100, 100, 45, 13, ["#45423d", "#3a3733", "#504c46", "#3f3c37"], (14, 30))
          + bars
          + rubble(R, 100, 100, 55, 24, ["#4d4943", "#5a564f", "#3a3733"], (3, 9)))
    write("muralha", "muralha_destruida", ru, noise("fd", "0.08", 3, (.1, .09, .08), 1.3, -.4))


# ======================= Soleira (chão de pedra sob o portão e a Porta Esmeralda) =======================
def soleira(R, base="#4a4741"):
    out = ""
    for i in range(2):
        for k in range(2):
            out += f'<rect x="{i*100+2}" y="{k*100+2}" width="96" height="96" rx="3" fill="{shade(base, R.uniform(.85, 1.1))}"/>'
    return f'<rect width="200" height="200" fill="#1c1b19"/><g filter="url(#so)">{out}</g>'


SOLEIRA_DEFS = noise("so", "0.06", 4, (.15, .14, .13), 1.2, -.4)


# ======================= Portão de metal negro =======================
GOLD = "#a88a42"

def brasao(cx, cy, k=1.0, rot=0):
    """Pequeno brasão de Candlekeep: castelo com chamas no alto das torres, em dourado gasto."""
    g = (f'<g transform="translate({cx} {cy}) rotate({rot}) scale({k})">'
         '<path d="M-24,-26 H24 V4 Q24,22 0,32 Q-24,22 -24,4 Z" fill="#141318" stroke="' + GOLD + '" stroke-width="3"/>'
         f'<g fill="{GOLD}">'
         '<rect x="-15" y="-2" width="30" height="20"/>'
         '<rect x="-18" y="-12" width="9" height="30"/><rect x="9" y="-12" width="9" height="30"/><rect x="-5" y="-16" width="10" height="34"/>'
         '<path d="M-13.5,-14 q-4,-5 0,-10 q4,5 0,10 Z"/><path d="M13.5,-14 q-4,-5 0,-10 q4,5 0,10 Z"/><path d="M0,-18 q-4.5,-6 0,-11 q4.5,5 0,11 Z"/>'
         '</g><path d="M-4,18 V10 Q0,5 4,10 V18 Z" fill="#141318"/>'
         # desgaste: manchas escuras sobre o dourado
         '<g fill="#141318" opacity=".45"><circle cx="-12" cy="8" r="3"/><circle cx="10" cy="-4" r="2.2"/><circle cx="16" cy="12" r="2.6"/>'
         '<circle cx="-20" cy="-20" r="2"/><circle cx="6" cy="24" r="2.4"/></g></g>')
    return g


PORTAO_DEFS = (SOLEIRA_DEFS
               + '<linearGradient id="mt" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a3842"/><stop offset=".18" stop-color="#24232b"/>'
                 '<stop offset=".8" stop-color="#18171d"/><stop offset="1" stop-color="#0b0b0e"/></linearGradient>'
               + noise("mn", "0.04 0.3", 6, (.16, .14, .2), .8, -.4))


def painel_metal(y0, y1, rivets=True):
    """Painel de metal negro de borda a borda, entre y0 e y1, com frisos e rebites."""
    h = y1 - y0
    out = (f'<rect x="0" y="{y0+6}" width="200" height="{h}" fill="#000" opacity=".5" filter="url(#bl8)"/>'
           f'<rect x="0" y="{y0}" width="200" height="{h}" fill="url(#mt)" filter="url(#mn)"/>'
           f'<line x1="0" y1="{y0+1.5}" x2="200" y2="{y0+1.5}" stroke="#55535f" stroke-width="3"/>'
           f'<line x1="0" y1="{y1-1}" x2="200" y2="{y1-1}" stroke="#050506" stroke-width="2"/>')
    if h > 60:
        for fy in (y0 + 14, y1 - 14):
            out += (f'<line x1="0" y1="{fy-3}" x2="200" y2="{fy-3}" stroke="#4a4854" stroke-width="2"/>'
                    f'<line x1="0" y1="{fy+3}" x2="200" y2="{fy+3}" stroke="#08080a" stroke-width="2"/>')
        if rivets:
            out += "".join(f'<circle cx="{x}" cy="{fy}" r="3.6" fill="#5c5a64" stroke="#08080a" stroke-width="1.2"/>'
                           for x in range(10, 200, 20) for fy in (y0 + 14, y1 - 14))
        # frisos verticais discretos dos dois lados do brasão
        out += "".join(f'<rect x="{x}" y="{y0+24}" width="5" height="{h-48}" fill="#2c2b34" stroke="#08080a" stroke-width="1"/>' for x in (40, 155))
    else:
        out += "".join(f'<circle cx="{x}" cy="{(y0+y1)/2}" r="3" fill="#5c5a64" stroke="#08080a" stroke-width="1"/>' for x in range(10, 200, 20))
    return out


def portao():
    R = random.Random(2)
    chao = soleira(R)
    fechado = chao + painel_metal(36, 164) + brasao(100, 100, .95)
    write("portao", "portao_fechado", fechado, PORTAO_DEFS)

    # aberto: painel recolhido na borda de cima; trilho no chão mostra por onde ele corre
    aberto = (chao
              + '<g stroke="#0e0d0c" stroke-width="4" opacity=".7"><line x1="0" y1="96" x2="200" y2="96"/><line x1="0" y1="104" x2="200" y2="104"/></g>'
              + painel_metal(0, 28))
    write("portao", "portao_aberto", aberto, PORTAO_DEFS)

    # arrombado: painel retorcido caído, rebites e chapas soltas
    R = random.Random(3)
    bits = "".join(f'<circle cx="{100+R.gauss(0,45):.0f}" cy="{100+R.gauss(0,40):.0f}" r="3.2" fill="#5c5a64" stroke="#08080a"/>' for _ in range(10))
    shards = "".join(
        f'<polygon points="{(x:=100+R.gauss(0,50)):.0f},{(y:=100+R.gauss(0,45)):.0f} {x+R.uniform(8,18):.0f},{y+R.uniform(-6,6):.0f} {x+R.uniform(0,12):.0f},{y+R.uniform(6,14):.0f}" fill="#1d1c22" stroke="#08080a" stroke-width="1.2"/>'
        for _ in range(7))
    arromb = (chao + rubble(R, 100, 100, 50, 10, ["#3a3733", "#4a4741"], (3, 8))
              + '<g transform="rotate(14 100 112)">'
                '<path d="M-6,62 L60,50 L96,74 L130,54 L206,70 L200,160 L128,150 L98,172 L58,146 L-4,158 Z" fill="#000" opacity=".5" filter="url(#bl8)" transform="translate(4 8)"/>'
                '<path d="M-6,62 L60,50 L96,74 L130,54 L206,70 L200,160 L128,150 L98,172 L58,146 L-4,158 Z" fill="url(#mt)" filter="url(#mn)" stroke="#08080a" stroke-width="3"/>'
                '<g stroke="#4a4854" stroke-width="2" fill="none"><path d="M-4,76 L58,64 L96,88 L130,68 L204,84"/><path d="M-4,144 L58,132 L98,158 L128,136 L201,146"/></g>'
                '<g stroke="#08080a" stroke-width="2.5" fill="none"><path d="M60,50 L58,146"/><path d="M96,74 L98,172"/><path d="M130,54 L128,150"/></g>'
              + brasao(112, 112, .8, -18) + '</g>' + shards + bits)
    write("portao", "portao_arrombado", arromb, PORTAO_DEFS)


# ======================= Porta Esmeralda =======================
ESM_DEFS = (SOLEIRA_DEFS
            + '<linearGradient id="eg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3fae7a"/><stop offset=".15" stop-color="#17704b"/>'
              '<stop offset=".5" stop-color="#1f8a5c"/><stop offset=".85" stop-color="#0f5236"/><stop offset="1" stop-color="#083322"/></linearGradient>'
            + '<linearGradient id="eglow" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7dffc0" stop-opacity="0"/>'
              '<stop offset=".5" stop-color="#7dffc0" stop-opacity=".35"/><stop offset="1" stop-color="#7dffc0" stop-opacity="0"/></linearGradient>'
            + '<radialGradient id="ehalo"><stop offset="0" stop-color="#3fd38a" stop-opacity=".35"/><stop offset="1" stop-color="#3fd38a" stop-opacity="0"/></radialGradient>'
            + noise("en", "0.03 0.08", 11, (.2, .55, .38), .9, -.35)
            + '<filter id="eb" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2"/></filter>')


def veios(y0, y1):
    """Veios claros que entram e saem na mesma altura nas duas bordas (emendam com a vizinha)."""
    R = random.Random(4)
    h = y1 - y0
    out = ""
    for f in (.22, .55, .8):
        y = y0 + h * f
        out += (f'<path d="M0,{y:.0f} C50,{y+R.uniform(-.2,.2)*h:.0f} 90,{y+R.uniform(-.25,.25)*h:.0f} 120,{y+R.uniform(-.15,.15)*h:.0f} S180,{y+R.uniform(-.1,.1)*h:.0f} 200,{y:.0f}" '
                f'stroke="#9dffd0" stroke-width="{R.uniform(1.5,3):.1f}" fill="none" opacity="{R.uniform(.25,.45):.2f}"/>')
    return out


def runas(cy):
    R = random.Random(9)
    out = ""
    for x in range(22, 200, 26):
        p = f"M{x-6},{cy-8}"
        for _ in range(3):
            p += f" L{x+R.choice((-6,0,6))},{cy+R.choice((-8,-2,4,8))}"
        out += f'<path d="{p}"/>'
    return f'<g stroke="#c8ffe4" stroke-width="2" fill="none" stroke-linecap="round" opacity=".4" filter="url(#eb)">{out}</g><g stroke="#c8ffe4" stroke-width="1.2" fill="none" opacity=".45">{out}</g>'


def painel_esmeralda(y0, y1):
    h = y1 - y0
    out = (f'<rect x="0" y="{y0-10}" width="200" height="{h+20}" fill="url(#ehalo)"/>'
           f'<rect x="0" y="{y0}" width="200" height="{h}" fill="url(#eg)" opacity=".86" filter="url(#en)"/>'
           f'<rect x="0" y="{y0}" width="200" height="{h}" fill="url(#eglow)"/>'
           f'<line x1="0" y1="{y0+1.5}" x2="200" y2="{y0+1.5}" stroke="#a8ffd6" stroke-width="2.5" opacity=".7"/>'
           f'<line x1="0" y1="{y1-1}" x2="200" y2="{y1-1}" stroke="#052016" stroke-width="2"/>')
    out += veios(y0, y1)
    if h > 60:
        out += runas((y0 + y1) / 2)
    return out


def porta_esmeralda():
    R = random.Random(6)
    chao = soleira(R, "#45504a")
    tint = '<rect width="200" height="200" fill="#3fd38a" opacity=".07"/>'
    write("porta_esmeralda", "porta_esmeralda_trancada", chao + tint + painel_esmeralda(40, 160), ESM_DEFS)
    write("porta_esmeralda", "porta_esmeralda_aberta",
          chao + tint + '<rect x="0" y="20" width="200" height="40" fill="url(#ehalo)"/>' + painel_esmeralda(0, 26), ESM_DEFS)


# ======================= Definições (fragmento do assets.json) =======================
# brilho fraco: são 3 quadrados lado a lado, as luzes se somam
LUZ_ESM = {"bright": 0, "dim": 7, "color": "#3fd38a", "alpha": .25, "attenuation": .8, "animation": {"type": "pulse", "speed": 1, "intensity": 2}}

FRAGMENTO = {
    "muralha": {
        "name": "Muralha de Candlekeep",
        "tipo": "imovel", "interacao": "mestre", "size": {"w": 1, "h": 1},
        "actor": {"ac": 19, "hp": 120, "immunities": ["poison", "psychic", "necrotic", "radiant"],
                  "resistances": ["bludgeoning", "piercing", "slashing"]},
        "states": [
            {"id": "inteira", "name": "Inteira", "src": "muralha/muralha_inteira.png"},
            {"id": "rachada", "name": "Rachada", "src": "muralha/muralha_rachada.png"},
            {"id": "destruida", "name": "Destruída", "src": "muralha/muralha_destruida.png", "broken": True},
        ],
        "reactions": [{"types": ["bludgeoning", "thunder", "force"], "from": ["inteira"], "to": "rachada", "say": "racha."}],
        "onZero": [{"to": "destruida", "say": "desmorona e abre uma brecha na muralha!"}],
    },
    "portao": {
        "name": "Portão de Candlekeep",
        "tipo": "imovel", "interacao": "mestre", "size": {"w": 1, "h": 1},
        "doorSound": "metal",
        "actor": {"ac": 20, "hp": 250, "immunities": ["fire", "lightning", "poison", "psychic", "necrotic"],
                  "resistances": ["bludgeoning", "piercing", "slashing"]},
        "states": [
            {"id": "fechado", "name": "Fechado", "src": "portao/portao_fechado.png", "door": "locked"},
            {"id": "aberto", "name": "Aberto", "src": "portao/portao_aberto.png", "door": "open"},
            {"id": "arrombado", "name": "Arrombado", "src": "portao/portao_arrombado.png", "broken": True},
        ],
        "onZero": [{"to": "arrombado", "say": "se retorce e cai!"}],
    },
    "porta_esmeralda": {
        "name": "Porta Esmeralda",
        "tipo": "imovel", "interacao": "mestre", "size": {"w": 1, "h": 1},
        "doorSound": "magicDoor",
        "invulneravel": "não sofre nem um arranhão: a Porta Esmeralda é protegida contra qualquer dano.",
        "actor": {},
        "states": [
            {"id": "trancada", "name": "Trancada", "src": "porta_esmeralda/porta_esmeralda_trancada.png", "door": "locked", "light": LUZ_ESM},
            {"id": "aberta", "name": "Aberta", "src": "porta_esmeralda/porta_esmeralda_aberta.png", "door": "open", "light": LUZ_ESM},
        ],
    },
}


if __name__ == "__main__":
    muralha()
    portao()
    porta_esmeralda()
    FRAG.parent.mkdir(parents=True, exist_ok=True)
    FRAG.write_text(json.dumps(FRAGMENTO, ensure_ascii=False, indent=2) + "\n")
    print("ok:", ", ".join(FRAGMENTO))
