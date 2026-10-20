"""Junta as definições de tools/fragmentos/*.json no assets/assets.json (substitui as entradas de mesmo id,
mantém as outras e a ordem) e aplica os sons de tools/sons.json ("estados": asset → estado → sfx/sound).
Rode depois de um gerador que escreve fragmento (gen_construcao, gen_biblioteca, gen_oficios) ou de mudar os sons.
Uso: python3 tools/juntar_fragmentos.py"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
p = ROOT / "assets" / "assets.json"
d = json.loads(p.read_text())
for f in sorted((ROOT / "tools" / "fragmentos").glob("*.json")):
    d.update(json.loads(f.read_text()))
sons = json.loads((ROOT / "tools" / "sons.json").read_text()).get("estados", {})
for asset, estados in sons.items():
    for st in d.get(asset, {}).get("states", []):
        st.update(estados.get(st["id"], {}))
p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
print(len(d), "assets")
