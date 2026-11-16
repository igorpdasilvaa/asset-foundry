"""Animações a partir de vídeos gerados no ia-orc (Wan 2.2, imagem → vídeo).

O primeiro quadro do vídeo é a própria imagem do estado (vista de cima, sobre fundo escuro). Aqui o vídeo vira um WebM
com transparência no tamanho do asset:
- recorte: a transparência do estado parado é aplicada em todos os quadros (o objeto não muda de contorno);
- loop: os últimos quadros se misturam com os primeiros (crossfade), sem pulo ao recomeçar;
- emendavel: cada quadro passa pelo ladrilho (água: os quadrados vizinhos se juntam sem costura);
- opacidade: < 1 deixa o fundo do mapa aparecer (a margem pintada do lago continua visível sob a água animada);
- cor: imagem de referência (em assets/) cuja cor os quadros seguem, quando o vídeo sai com outro tom.
Também salva o PNG do primeiro quadro (miniatura do ator).

As animações ficam em tools/ia_animacoes.json: { "<asset>": { "<estado>": { "job", "emendavel"?, "opacidade"?, "fps"?, "cor"? } } }.
O tools/ia_assets.py respeita: o estado animado aponta para o WebM e não é refeito como imagem parada.

Uso: python3 tools/ia_animacao.py [asset ...]"""
import json, pathlib, subprocess, sys, tempfile
from PIL import Image, ImageChops, ImageStat

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ia_assets import ladrilho, DOWN, S

ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG = ROOT / "tools" / "ia_animacoes.json"


def video_do_job(job):
    fs = sorted(p for p in (DOWN / job).iterdir() if p.suffix in (".mp4", ".webm", ".mov", ".gif"))
    return fs[0]


def quadros(video, tmp):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), f"{tmp}/q%03d.png"], check=True)
    return [Image.open(f).convert("RGB") for f in sorted(pathlib.Path(tmp).glob("q*.png"))]


def loop(fs, k):
    """Crossfade dos k últimos quadros sobre os k primeiros: o fim emenda no começo."""
    n = len(fs)
    k = min(k, n // 3)
    out = []
    for i in range(n - k):
        if i < k:
            out.append(Image.blend(fs[n - k + i], fs[i], i / k))
        else:
            out.append(fs[i])
    return out


def acerta_cor(fs, ref):
    """Leva a cor dos quadros para a da imagem de referência (média e contraste de cada canal, medidos no 1º quadro).
    A mesma conta vale para todos os quadros: a animação não pisca."""
    r = ImageStat.Stat(Image.open(ref).convert("RGB"))
    q = ImageStat.Stat(fs[0])
    tabela = []
    for m0, s0, m1, s1 in zip(q.mean, q.stddev, r.mean, r.stddev):
        k = s1 / max(s0, 1)
        tabela += [max(0, min(255, round((v - m0) * k + m1))) for v in range(256)]
    return [f.point(tabela) for f in fs]


def anima(asset, estado, c, defs):
    d = defs[asset]
    W, H = int(d["size"]["w"] * S), int(d["size"]["h"] * S)
    estado_def = next(s for s in d["states"] if s["id"] == estado)
    parado = ROOT / "assets" / estado_def["src"]
    if parado.suffix == ".webm":
        parado = parado.with_suffix(".png")
    mascara = None if c.get("emendavel") else Image.open(parado).convert("RGBA").getchannel("A").resize((W, H))
    opac = c.get("opacidade", 1.0)
    destino = ROOT / "assets" / asset / f"{asset}_{estado}.webm"
    with tempfile.TemporaryDirectory() as tmp:
        fs = loop(quadros(video_do_job(c["job"]), tmp), c.get("crossfade", 10))
        if c.get("cor"):
            fs = acerta_cor(fs, ROOT / "assets" / c["cor"])
        for i, f in enumerate(fs):
            if c.get("emendavel"):
                f = ladrilho(f)
            f = f.resize((W, H), Image.LANCZOS).convert("RGBA")
            a = mascara if mascara is not None else Image.new("L", (W, H), 255)
            if opac < 1:
                a = a.point(lambda v: int(v * opac))
            f.putalpha(a)
            f.save(f"{tmp}/s{i:03d}.png")
            if i == 0:
                f.save(destino.with_suffix(".png"))
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(c.get("fps", 24)), "-i", f"{tmp}/s%03d.png",
                        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "0", "-crf", str(c.get("crf", 36)),
                        str(destino)], check=True)
    return f"{asset}/{destino.name}"


def main(nomes):
    cfg = json.loads(CFG.read_text())
    pa = ROOT / "assets" / "assets.json"
    defs = json.loads(pa.read_text())
    frags = {f: json.loads(f.read_text()) for f in (ROOT / "tools" / "fragmentos").glob("*.json")}
    for asset, estados in cfg.items():
        if asset.startswith("_") or (nomes and asset not in nomes):
            continue
        for estado, c in estados.items():
            src = anima(asset, estado, c, defs)
            for alvo in [defs] + [fr for fr in frags.values() if asset in fr]:
                for st in alvo[asset]["states"]:
                    if st["id"] == estado:
                        st["src"] = src
            print(asset, estado, src)
    pa.write_text(json.dumps(defs, indent=2, ensure_ascii=False) + "\n")
    for f, fr in frags.items():
        f.write_text(json.dumps(fr, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
