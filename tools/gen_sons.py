"""Prepara um áudio gerado no ia-orc (Stable Audio 3 / ACE-Step) para o módulo.

- sfx: corta o silêncio do começo e do fim e leva o pico a -1 dB.
- loop e musica: normaliza e emenda o fim no começo com um crossfade (o loop do Foundry não tem corte).
- cancao: só normaliza (toca do começo ao fim).
Saída em OGG Vorbis: efeitos e ambiências em assets/audio/<nome>.ogg, músicas e canções em mapas/candlekeep/musica/<nome>.ogg.
Os prompts e o tipo de cada som ficam em tools/sons.json.

Uso: python3 tools/gen_sons.py <arquivo gerado> <nome>          (o tipo vem do sons.json)
     python3 tools/gen_sons.py <arquivo> <nome> --tipo sfx --saida assets/audio/x.ogg"""
import argparse, json, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
SONS = json.loads((ROOT / "tools" / "sons.json").read_text())
SECAO = {"sfx": "sfx", "loops": "loop", "musicas": "musica", "cancoes": "cancao"}
ALVO = {"sfx": -16, "loop": -22, "musica": -20, "cancao": -18}  # loudness (LUFS); nos efeitos vale o pico
FADE = {"loop": 3.0, "musica": 6.0}


def duracao(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                                capture_output=True, text=True, check=True).stdout)


def pico_db(src, filtro):
    """Pico (dBFS) do áudio depois do filtro."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af", f"{filtro},volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(r.split("max_volume:")[1].split("dB")[0])


def prepara(src, dst, tipo):
    dst.parent.mkdir(parents=True, exist_ok=True)
    norm = f"loudnorm=I={ALVO[tipo]}:TP=-1.5:LRA=11"
    if tipo == "sfx":
        # corta o silêncio das pontas (com um fade curto nas duas, sem estalo) e leva o pico a -1 dB:
        # o loudnorm não funciona bem em clipes de 1 a 3 segundos
        corta = "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.02"
        filtro = f"{corta},areverse,{corta},afade=t=in:d=0.03,areverse,afade=t=in:d=0.005"
        pico = pico_db(src, filtro)
        cmd = ["-i", str(src), "-af", f"{filtro},volume={-1 - pico:.2f}dB"]
    elif tipo in FADE:
        d, f = duracao(src), FADE[tipo]
        # fim (d-f..d) misturado sobre o começo (0..f), depois o meio: o arquivo termina onde começa
        filtro = (f"[0:a]asplit=3[a][b][c];[a]atrim=0:{f},asetpts=PTS-STARTPTS[ini];"
                  f"[b]atrim={f}:{d - f},asetpts=PTS-STARTPTS[meio];[c]atrim={d - f}:{d},asetpts=PTS-STARTPTS[fim];"
                  f"[fim][ini]acrossfade=d={f}:c1=tri:c2=tri[emenda];[emenda][meio]concat=n=2:v=0:a=1,{norm}[out]")
        cmd = ["-i", str(src), "-filter_complex", filtro, "-map", "[out]"]
    else:
        cmd = ["-i", str(src), "-af", norm]
    subprocess.run(["ffmpeg", "-y", "-v", "error", *cmd, "-ar", "44100", "-c:a", "libvorbis", "-q:a", "5", str(dst)], check=True)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arquivo")
    ap.add_argument("nome")
    ap.add_argument("--tipo", choices=list(ALVO))
    ap.add_argument("--saida")
    a = ap.parse_args()
    tipo = a.tipo or next((SECAO[s] for s in SECAO if a.nome in SONS.get(s, {})), None)
    if not tipo:
        raise SystemExit(f"{a.nome} não está no tools/sons.json; passe --tipo")
    pasta = "assets/audio" if tipo in ("sfx", "loop") else "mapas/candlekeep/musica"
    dst = ROOT / (a.saida or f"{pasta}/{a.nome}.ogg")
    prepara(pathlib.Path(a.arquivo), dst, tipo)
    print(f"{dst.relative_to(ROOT)} ({duracao(dst):.1f} s)")


if __name__ == "__main__":
    main()
