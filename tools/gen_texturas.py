"""Texturas pintadas dos materiais dos mapas (ia-orc / SDXL), emendáveis, em mapas/pecas/texturas/<material>.webp.
O gen_mapa.py usa a textura no lugar do SVG do material quando ela existe.

escolhas.json: material -> { job, variacao_img (0-3), quadrados (lado do ladrilho), variacao (manchas de tom) }.
Uso: python3 tools/gen_texturas.py [material ...]"""
import json, pathlib, sys
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ia_assets import ladrilho, DOWN

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "mapas" / "pecas" / "texturas"
PROMPT = ("seamless tileable texture of {}, seen from directly above, flat even lighting, hand painted 2D fantasy "
          "battlemap texture like Forgotten Adventures, fills the whole image")


def main(nomes):
    esc = json.loads((DIR / "escolhas.json").read_text())
    cfg = {}
    for m, e in esc.items():
        cfg[m] = {"quadrados": e.get("quadrados", 2), "variacao": e.get("variacao", .12)}
        if nomes and m not in nomes:
            continue
        fs = sorted((DOWN / e["job"]).glob("*.png"))
        ladrilho(Image.open(fs[e["variacao_img"]]), 1024).save(DIR / f"{m}.webp", quality=88, method=6)
        print(m)
    (DIR / "texturas.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
